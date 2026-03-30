"""
Not runnable yet — blocked on TICKET-01 and TICKET-02 being merged.
Replace path/to/test.pdf with a real file before running.

Usage:
    pytest backend/tests/test_ingest.py -v
"""

import pytest
from app.services.ingest import ingest_document


@pytest.mark.asyncio
async def test_ingest_document_success():
    """Test that ingesting a real PDF returns success with structured data."""
    result = await ingest_document(
        file_path="path/to/test.pdf",  # Replace with a real PDF
        dataset_name="test-dataset",
    )

    assert result["status"] == "success"
    assert "summary" in result
    assert "entities" in result
    assert "raw_chunks_count" in result

    # Summary should not be empty
    assert len(result["summary"]) > 0

    # Should extract at least one entity
    assert len(result["entities"]) > 0

    # Should have at least one chunk
    assert result["raw_chunks_count"] > 0


@pytest.mark.asyncio
async def test_ingest_document_bad_file():
    """Test that a non-existent file returns an error status."""
    result = await ingest_document(
        file_path="nonexistent_file.pdf",
        dataset_name="test-dataset",
    )

    assert result["status"] == "error"
    assert "error" in result