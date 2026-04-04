"""
Tests for the ingest service error-handling paths.

Each test deliberately triggers one of the known failure modes and asserts
the correct error_type is returned without raising an unhandled exception.

Usage:
    pytest tests/test_ingest.py -v
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingest import ingest_document

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(entities=None):
    chunk = MagicMock()
    chunk.entities = entities or []
    return chunk


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_document_success():
    """Successful ingest returns structured data."""
    fake_chunk = _make_chunk(entities=["EntityA"])

    with (
        patch("app.services.ingest.cognee.add", new_callable=AsyncMock),
        patch("app.services.ingest.cognee.cognify", new_callable=AsyncMock),
        patch(
            "app.services.ingest.cognee.search",
            new_callable=AsyncMock,
            side_effect=[["mock summary"], [fake_chunk]],
        ),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="test-dataset",
            document_id="doc-123",
        )

    assert result["status"] == "success"
    assert result["document_id"] == "doc-123"
    assert result["summary"] == "mock summary"
    assert result["entities"] == ["EntityA"]
    assert result["raw_chunks_count"] == 1


# ---------------------------------------------------------------------------
# Empty search results — NOT an error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_search_results_returns_success():
    """Empty Cognee search results are not an error — return 200 with zeros."""
    with (
        patch("app.services.ingest.cognee.add", new_callable=AsyncMock),
        patch("app.services.ingest.cognee.cognify", new_callable=AsyncMock),
        patch(
            "app.services.ingest.cognee.search",
            new_callable=AsyncMock,
            side_effect=[[], []],
        ),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="empty-dataset",
        )

    assert result["status"] == "success"
    assert result["summary"] == ""
    assert result["entities"] == []
    assert result["raw_chunks_count"] == 0


# ---------------------------------------------------------------------------
# Kuzu storage failure (PermissionError during add)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kuzu_permission_error_during_add():
    """PermissionError on add() → error_type kuzu_storage."""
    with patch(
        "app.services.ingest.cognee.add",
        new_callable=AsyncMock,
        side_effect=PermissionError("Permission denied: .cognee_system/"),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="test-dataset",
        )

    assert result["status"] == "error"
    assert result["error_type"] == "kuzu_storage"
    assert ".cognee_system" in result["error"] or "writable" in result["error"]


# ---------------------------------------------------------------------------
# Kuzu storage failure (disk full during cognify)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kuzu_disk_full_during_cognify():
    """ENOSPC OSError on cognify() → error_type kuzu_storage with helpful message."""
    import errno

    disk_full = OSError("No space left on device")
    disk_full.errno = errno.ENOSPC

    with (
        patch("app.services.ingest.cognee.add", new_callable=AsyncMock),
        patch(
            "app.services.ingest.cognee.cognify",
            new_callable=AsyncMock,
            side_effect=disk_full,
        ),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="test-dataset",
        )

    assert result["status"] == "error"
    assert result["error_type"] == "kuzu_storage"
    assert "full" in result["error"].lower() or "space" in result["error"].lower()


# ---------------------------------------------------------------------------
# Gemini / LLM API error during cognify
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_api_error_during_cognify():
    """LLM API error during cognify() → error_type llm_api."""

    class FakeLiteLLMError(Exception):
        pass

    FakeLiteLLMError.__module__ = "litellm.exceptions"

    with (
        patch("app.services.ingest.cognee.add", new_callable=AsyncMock),
        patch(
            "app.services.ingest.cognee.cognify",
            new_callable=AsyncMock,
            side_effect=FakeLiteLLMError("Invalid API key for Gemini"),
        ),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="test-dataset",
        )

    assert result["status"] == "error"
    assert result["error_type"] == "llm_api"
    assert "cognify" in result["error"].lower()


@pytest.mark.asyncio
async def test_llm_api_error_keyword_fallback():
    """Even a plain Exception with 'api key' in the message is treated as LLM error."""
    with (
        patch("app.services.ingest.cognee.add", new_callable=AsyncMock),
        patch(
            "app.services.ingest.cognee.cognify",
            new_callable=AsyncMock,
            side_effect=Exception("Gemini quota exceeded: rate limit hit"),
        ),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="test-dataset",
        )

    assert result["status"] == "error"
    assert result["error_type"] == "llm_api"


# ---------------------------------------------------------------------------
# Vector dimension mismatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vector_dimension_mismatch_during_cognify():
    """Dimension mismatch error → error_type vector_dimension_mismatch with fix hint."""
    with (
        patch("app.services.ingest.cognee.add", new_callable=AsyncMock),
        patch(
            "app.services.ingest.cognee.cognify",
            new_callable=AsyncMock,
            side_effect=Exception(
                "Vector dimension mismatch: expected 1536, got 768"
            ),
        ),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="test-dataset",
        )

    assert result["status"] == "error"
    assert result["error_type"] == "vector_dimension_mismatch"
    assert ".cognee_system" in result["error"]
    assert "re-ingest" in result["error"].lower() or "delete" in result["error"].lower()


@pytest.mark.asyncio
async def test_vector_dimension_mismatch_during_search():
    """Dimension mismatch can also surface during search() after cognify succeeds."""
    with (
        patch("app.services.ingest.cognee.add", new_callable=AsyncMock),
        patch("app.services.ingest.cognee.cognify", new_callable=AsyncMock),
        patch(
            "app.services.ingest.cognee.search",
            new_callable=AsyncMock,
            side_effect=Exception("wrong number of dimensions: expected 1536"),
        ),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="test-dataset",
        )

    assert result["status"] == "error"
    assert result["error_type"] == "vector_dimension_mismatch"


# ---------------------------------------------------------------------------
# cognify() called without prior add() (empty dataset)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cognify_without_add():
    """cognify() on empty dataset → error_type no_data_added."""
    with (
        patch("app.services.ingest.cognee.add", new_callable=AsyncMock),
        patch(
            "app.services.ingest.cognee.cognify",
            new_callable=AsyncMock,
            side_effect=Exception("No data added to dataset before cognify"),
        ),
    ):
        result = await ingest_document(
            file_path="fake.pdf",
            dataset_name="test-dataset",
        )

    assert result["status"] == "error"
    assert result["error_type"] == "no_data_added"
    assert "add()" in result["error"]


# ---------------------------------------------------------------------------
# Non-existent file (basic smoke test — no mocks)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_document_bad_file():
    """A non-existent file path should return an error status, not raise."""
    with (
        patch(
            "app.services.ingest.cognee.add",
            new_callable=AsyncMock,
            side_effect=FileNotFoundError("No such file: nonexistent.pdf"),
        ),
    ):
        result = await ingest_document(
            file_path="nonexistent_file.pdf",
            dataset_name="test-dataset",
        )

    # FileNotFoundError is an OSError subclass → kuzu_storage bucket
    assert result["status"] == "error"
    assert "error" in result
