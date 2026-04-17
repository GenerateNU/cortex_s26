"""
Integration tests — exercise full HTTP request → route → service → response chain.

External services (Cognee, Supabase, R2) are mocked at the SDK boundary so these
tests run without any infrastructure.  What IS tested: routing, request validation,
Pydantic serialization, service orchestration, error handling, and HTTP status codes.

Usage:
    cd backend && pytest tests/test_integration.py -v
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_async_sb(data=None):
    """Build a mock async Supabase client.

    The chain ``sb.table(...).select(...).eq(...).execute()`` uses regular
    (synchronous) calls except for ``.execute()`` which is awaited.
    """
    sb = MagicMock()
    result = MagicMock(data=data if data is not None else [])
    chain = sb.table.return_value
    for method in (
        "select", "eq", "order", "limit", "insert", "update", "maybe_single", "lt",
    ):
        getattr(chain, method).return_value = chain
    chain.execute = AsyncMock(return_value=result)
    return sb


def _mock_async_sb_single(data):
    """Mock for maybe_single() queries — data is a dict or None."""
    return _mock_async_sb(data=data)


def _fake_get_async_supabase(sb_mock):
    """Return an async function that yields *sb_mock*."""
    async def _get():
        return sb_mock
    return _get


# ===========================================================================
# Health check  GET /api/health
# ===========================================================================


class TestHealthCheck:

    def test_healthy(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ===========================================================================
# Upload  POST /api/documents/upload
# ===========================================================================


class TestUploadDocuments:

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_single_pdf(self, mock_get_sb, mock_pipeline, client):
        mock_get_sb.return_value = _mock_async_sb()

        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("report.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf"))],
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["uploaded"]) == 1
        assert body["uploaded"][0]["filename"] == "report.pdf"
        assert len(body["uploaded"][0]["id"]) == 36  # UUID
        mock_pipeline.assert_called_once()

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_multiple_files(self, mock_get_sb, mock_pipeline, client):
        mock_get_sb.return_value = _mock_async_sb()

        files = [
            ("files", ("a.pdf", io.BytesIO(b"%PDF"), "application/pdf")),
            ("files", ("b.csv", io.BytesIO(b"col1,col2"), "text/csv")),
            ("files", ("c.txt", io.BytesIO(b"hello"), "text/plain")),
        ]
        resp = client.post("/api/documents/upload", files=files)

        assert resp.status_code == 200
        assert len(resp.json()["uploaded"]) == 3
        assert mock_pipeline.call_count == 3

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_all_allowed_extensions(self, mock_get_sb, mock_pipeline, client):
        mock_get_sb.return_value = _mock_async_sb()

        for ext, content_type in [
            (".pdf", "application/pdf"),
            (".csv", "text/csv"),
            (".txt", "text/plain"),
        ]:
            resp = client.post(
                "/api/documents/upload",
                files=[("files", (f"test{ext}", io.BytesIO(b"data"), content_type))],
            )
            assert resp.status_code == 200, f"Extension {ext} should be accepted"

    def test_rejects_unsupported_extension(self, client):
        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("image.png", io.BytesIO(b"fake"), "image/png"))],
        )
        assert resp.status_code == 400
        assert "unsupported extension" in resp.json()["detail"].lower()

    def test_rejects_more_than_5_files(self, client):
        files = [
            ("files", (f"f{i}.pdf", io.BytesIO(b"%PDF"), "application/pdf"))
            for i in range(6)
        ]
        resp = client.post("/api/documents/upload", files=files)
        assert resp.status_code == 400
        assert "maximum" in resp.json()["detail"].lower()

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_pipeline_receives_correct_args(self, mock_get_sb, mock_pipeline, client):
        mock_get_sb.return_value = _mock_async_sb()

        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("data.csv", io.BytesIO(b"a,b,c"), "text/csv"))],
        )

        assert resp.status_code == 200
        args, _kwargs = mock_pipeline.call_args
        temp_path, doc_id, original_filename = args
        assert str(temp_path).endswith(".csv")
        assert len(doc_id) == 36
        assert original_filename == "data.csv"


# ===========================================================================
# Deduplication  POST /api/documents/upload
# ===========================================================================


class TestUploadDeduplication:

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.routes.documents.create_document", new_callable=AsyncMock)
    @patch("app.routes.documents.find_document_by_hash", new_callable=AsyncMock)
    def test_duplicate_returns_existing_doc(
        self, mock_find, mock_create, mock_pipeline, client
    ):
        """When an identical file already exists, return it without re-processing."""
        mock_find.return_value = {
            "id": "existing-doc-id",
            "original_filename": "report.pdf",
            "status": "completed",
            "insights": [],
            "entities": [],
            "file_url": None,
        }

        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("report.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf"))],
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["uploaded"]) == 1
        assert body["uploaded"][0]["duplicate"] is True
        assert body["uploaded"][0]["existing_doc_id"] == "existing-doc-id"
        assert body["uploaded"][0]["id"] == "existing-doc-id"
        # Pipeline should NOT have been triggered
        mock_pipeline.assert_not_called()
        # No new document should have been created
        mock_create.assert_not_called()

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    @patch("app.routes.documents.find_document_by_hash", new_callable=AsyncMock)
    def test_new_file_proceeds_to_pipeline(
        self, mock_find, mock_get_sb, mock_pipeline, client
    ):
        """When no duplicate exists, create doc and run the pipeline."""
        mock_find.return_value = None
        mock_get_sb.return_value = _mock_async_sb()

        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("new.pdf", io.BytesIO(b"%PDF-new"), "application/pdf"))],
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["uploaded"]) == 1
        assert body["uploaded"][0]["duplicate"] is False
        assert body["uploaded"][0]["existing_doc_id"] is None
        mock_pipeline.assert_called_once()

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    @patch("app.routes.documents.find_document_by_hash", new_callable=AsyncMock)
    def test_hash_passed_to_create_document(
        self, mock_find, mock_get_sb, mock_pipeline, client
    ):
        """create_document receives the content_hash for storage."""
        import hashlib

        mock_find.return_value = None
        mock_get_sb.return_value = _mock_async_sb()
        content = b"unique-file-content"
        expected_hash = hashlib.sha256(content).hexdigest()

        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("file.txt", io.BytesIO(content), "text/plain"))],
        )

        assert resp.status_code == 200
        # Verify find_document_by_hash was called with the correct hash
        mock_find.assert_called_once_with(expected_hash)

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.routes.documents.create_document", new_callable=AsyncMock)
    @patch("app.routes.documents.find_document_by_hash", new_callable=AsyncMock)
    def test_mixed_new_and_duplicate_files(
        self, mock_find, mock_create, mock_pipeline, client
    ):
        """A batch with both new and duplicate files handles each correctly."""
        import hashlib

        new_content = b"brand-new"
        dup_content = b"already-exists"
        dup_hash = hashlib.sha256(dup_content).hexdigest()

        def _find_side_effect(content_hash):
            if content_hash == dup_hash:
                return {
                    "id": "dup-doc-id",
                    "original_filename": "old.csv",
                    "status": "completed",
                    "insights": [],
                    "entities": [],
                    "file_url": None,
                }
            return None

        mock_find.side_effect = _find_side_effect
        mock_create.return_value = "new-doc-id"

        resp = client.post(
            "/api/documents/upload",
            files=[
                ("files", ("new.txt", io.BytesIO(new_content), "text/plain")),
                ("files", ("dup.csv", io.BytesIO(dup_content), "text/csv")),
            ],
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["uploaded"]) == 2

        new_file = body["uploaded"][0]
        assert new_file["duplicate"] is False
        assert new_file["filename"] == "new.txt"

        dup_file = body["uploaded"][1]
        assert dup_file["duplicate"] is True
        assert dup_file["existing_doc_id"] == "dup-doc-id"

        # Only the new file triggers the pipeline
        mock_pipeline.assert_called_once()
        mock_create.assert_called_once()

    @patch("app.routes.documents.run_pipeline", new_callable=AsyncMock)
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    @patch("app.routes.documents.find_document_by_hash", new_callable=AsyncMock)
    def test_same_filename_different_content_not_duplicate(
        self, mock_find, mock_get_sb, mock_pipeline, client
    ):
        """Same filename but different content should NOT be treated as a duplicate."""
        mock_find.return_value = None
        mock_get_sb.return_value = _mock_async_sb()

        resp = client.post(
            "/api/documents/upload",
            files=[
                ("files", ("report.pdf", io.BytesIO(b"version-1"), "application/pdf")),
                ("files", ("report.pdf", io.BytesIO(b"version-2"), "application/pdf")),
            ],
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["uploaded"]) == 2
        assert all(f["duplicate"] is False for f in body["uploaded"])
        assert mock_pipeline.call_count == 2


# ===========================================================================
# Search  GET /api/documents/search
# ===========================================================================


class TestSearchDocuments:

    @patch("app.core.supabase.get_async_supabase", new_callable=AsyncMock)
    @patch("app.services.cognee_service.cognee")
    def test_returns_results_with_sources(self, mock_cognee, mock_get_sb, client):
        mock_cognee.search = AsyncMock(
            return_value=[
                {"search_result": "Deep fryer safety guide", "dataset_name": "fast-food"},
            ]
        )
        mock_get_sb.return_value = _mock_async_sb(
            data=[
                {
                    "id": "doc-1",
                    "original_filename": "fryer.pdf",
                    "document_type": "RFQ",
                    "dataset_name": "fast-food",
                }
            ]
        )

        resp = client.get("/api/documents/search?q=fryer+safety")

        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "fryer safety"
        assert body["total"] == 1
        assert "fryer" in body["results"][0]["text"].lower()
        assert len(body["results"][0]["sources"]) >= 1

    @patch("app.core.supabase.get_async_supabase", new_callable=AsyncMock)
    @patch("app.services.cognee_service.cognee")
    def test_empty_results(self, mock_cognee, mock_get_sb, client):
        mock_cognee.search = AsyncMock(return_value=[])
        mock_get_sb.return_value = _mock_async_sb()

        resp = client.get("/api/documents/search?q=nonexistent")

        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["results"] == []

    def test_missing_query_param_returns_422(self, client):
        resp = client.get("/api/documents/search")
        assert resp.status_code == 422

    @patch("app.core.supabase.get_async_supabase", new_callable=AsyncMock)
    @patch("app.services.cognee_service.cognee")
    def test_dataset_filter(self, mock_cognee, mock_get_sb, client):
        mock_cognee.search = AsyncMock(
            return_value=[{"search_result": "result", "dataset_name": "acme"}]
        )
        mock_get_sb.return_value = _mock_async_sb(
            data=[
                {
                    "id": "doc-2",
                    "original_filename": "acme.pdf",
                    "document_type": None,
                    "dataset_name": "acme",
                }
            ]
        )

        resp = client.get("/api/documents/search?q=test&dataset=acme")

        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        # Verify cognee was called with the dataset filter
        call_kwargs = mock_cognee.search.call_args.kwargs
        assert call_kwargs.get("datasets") == ["acme"]

    @patch("app.core.supabase.get_async_supabase", new_callable=AsyncMock)
    @patch("app.services.cognee_service.cognee")
    def test_cognee_failure_returns_500(self, mock_cognee, mock_get_sb, client):
        mock_cognee.search = AsyncMock(side_effect=Exception("Cognee connection lost"))
        mock_get_sb.return_value = _mock_async_sb()

        resp = client.get("/api/documents/search?q=test")

        assert resp.status_code == 500
        assert "search failed" in resp.json()["detail"].lower()


# ===========================================================================
# Graph  GET /api/documents/graph
# ===========================================================================


class TestGraphEndpoint:

    @patch("cognee.infrastructure.databases.graph.get_graph_engine", new_callable=AsyncMock)
    def test_returns_d3_format(self, mock_get_engine, client):
        mock_engine = AsyncMock()
        mock_engine.get_graph_data.return_value = (
            [
                ("n1", {"name": "Acme Corp", "type": "Company"}),
                ("n2", {"name": "Safety Manual", "type": "Document"}),
            ],
            [("n1", "n2", "mentions", {})],
        )
        mock_get_engine.return_value = mock_engine

        resp = client.get("/api/documents/graph")

        assert resp.status_code == 200
        body = resp.json()
        assert "nodes" in body
        assert "links" in body
        assert len(body["nodes"]) == 2
        assert len(body["links"]) == 1
        assert body["links"][0]["source"] == "n1"
        assert body["links"][0]["target"] == "n2"
        assert body["links"][0]["label"] == "mentions"

    @patch("cognee.infrastructure.databases.graph.get_graph_engine", new_callable=AsyncMock)
    def test_empty_graph(self, mock_get_engine, client):
        mock_engine = AsyncMock()
        mock_engine.get_graph_data.return_value = ([], [])
        mock_get_engine.return_value = mock_engine

        resp = client.get("/api/documents/graph")

        assert resp.status_code == 200
        assert resp.json() == {"nodes": [], "links": []}

    @patch(
        "cognee.infrastructure.databases.graph.get_graph_engine",
        new_callable=AsyncMock,
        side_effect=Exception("KuzuDB unavailable"),
    )
    def test_engine_failure_returns_empty_graph(self, _mock, client):
        """graph_service catches exceptions and returns an empty graph."""
        resp = client.get("/api/documents/graph")

        assert resp.status_code == 200
        assert resp.json() == {"nodes": [], "links": []}


# ===========================================================================
# List documents  GET /api/documents/
# ===========================================================================


class TestListDocuments:

    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_returns_all_documents(self, mock_get_sb, client):
        mock_get_sb.return_value = _mock_async_sb(
            data=[
                {
                    "id": "d1",
                    "original_filename": "a.pdf",
                    "status": "completed",
                    "insights": None,
                    "entities": None,
                },
                {
                    "id": "d2",
                    "original_filename": "b.csv",
                    "status": "processing",
                    "insights": "[]",
                    "entities": '["EntityA"]',
                },
            ]
        )

        resp = client.get("/api/documents/")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        # _normalize converts JSON strings → lists and None → []
        assert body[0]["insights"] == []
        assert body[0]["entities"] == []
        assert body[1]["entities"] == ["EntityA"]

    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_empty_list(self, mock_get_sb, client):
        mock_get_sb.return_value = _mock_async_sb(data=[])

        resp = client.get("/api/documents/")

        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# Single document  GET /api/documents/{doc_id}
# ===========================================================================


class TestGetDocument:

    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_existing_document(self, mock_get_sb, client):
        mock_get_sb.return_value = _mock_async_sb_single(
            {
                "id": "doc-abc",
                "original_filename": "report.pdf",
                "status": "completed",
                "insights": '["insight1"]',
                "entities": '["entity1"]',
            }
        )

        resp = client.get("/api/documents/doc-abc")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "doc-abc"
        # _normalize deserialises JSON strings
        assert body["insights"] == ["insight1"]
        assert body["entities"] == ["entity1"]
        # _normalize ensures file_url is present
        assert "file_url" in body

    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_not_found(self, mock_get_sb, client):
        mock_get_sb.return_value = _mock_async_sb_single(None)

        resp = client.get("/api/documents/nonexistent")

        assert resp.status_code == 404


# ===========================================================================
# File URL  GET /api/documents/{doc_id}/file-url
# ===========================================================================


class TestGetFileUrl:

    @patch("app.services.storage._r2_client")
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_returns_presigned_url(self, mock_get_sb, mock_r2_client, client):
        mock_get_sb.return_value = _mock_async_sb_single(
            {
                "id": "doc-1",
                "original_filename": "report.pdf",
                "file_url": "documents/doc-1/report.pdf",
                "status": "completed",
                "insights": None,
                "entities": None,
            }
        )
        r2 = MagicMock()
        r2.generate_presigned_url.return_value = "https://r2.example.com/signed?token=abc"
        mock_r2_client.return_value = r2

        resp = client.get("/api/documents/doc-1/file-url")

        assert resp.status_code == 200
        body = resp.json()
        assert body["url"] == "https://r2.example.com/signed?token=abc"
        assert body["filename"] == "report.pdf"

    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_document_not_found(self, mock_get_sb, client):
        mock_get_sb.return_value = _mock_async_sb_single(None)

        resp = client.get("/api/documents/nonexistent/file-url")

        assert resp.status_code == 404

    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_no_file_stored(self, mock_get_sb, client):
        mock_get_sb.return_value = _mock_async_sb_single(
            {
                "id": "doc-1",
                "original_filename": "report.pdf",
                "file_url": None,
                "status": "completed",
                "insights": None,
                "entities": None,
            }
        )

        resp = client.get("/api/documents/doc-1/file-url")

        assert resp.status_code == 404
        assert "no raw file" in resp.json()["detail"].lower()

    @patch("app.services.storage._r2_client")
    @patch("app.services.document_metadata_service.get_async_supabase", new_callable=AsyncMock)
    def test_r2_not_configured(self, mock_get_sb, mock_r2_client, client):
        mock_get_sb.return_value = _mock_async_sb_single(
            {
                "id": "doc-1",
                "original_filename": "report.pdf",
                "file_url": "documents/doc-1/report.pdf",
                "status": "completed",
                "insights": None,
                "entities": None,
            }
        )
        mock_r2_client.return_value = None  # R2 credentials missing

        resp = client.get("/api/documents/doc-1/file-url")

        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()
