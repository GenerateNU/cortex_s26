"""
Tests for storage service (Cloudflare R2).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.storage import get_presigned_url, upload_to_r2


class TestUploadToR2:
    @pytest.mark.asyncio
    @patch("app.services.storage._r2_client")
    async def test_upload_returns_key_on_success(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client

        result = await upload_to_r2("/tmp/file.pdf", "documents/123/file.pdf")

        assert result == "documents/123/file.pdf"
        mock_client.upload_file.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.storage._r2_client")
    async def test_upload_returns_none_when_not_configured(self, mock_client_fn):
        mock_client_fn.return_value = None

        result = await upload_to_r2("/tmp/file.pdf", "documents/123/file.pdf")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.storage._r2_client")
    async def test_upload_returns_none_on_exception(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.upload_file.side_effect = Exception("S3 upload failed")
        mock_client_fn.return_value = mock_client

        result = await upload_to_r2("/tmp/file.pdf", "documents/123/file.pdf")

        assert result is None


class TestGetPresignedUrl:
    @patch("app.services.storage._r2_client")
    def test_returns_url_on_success(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://r2.example.com/signed"
        mock_client_fn.return_value = mock_client

        result = get_presigned_url("documents/123/file.pdf")

        assert result == "https://r2.example.com/signed"
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "cortex-documents", "Key": "documents/123/file.pdf"},
            ExpiresIn=3600,
        )

    @patch("app.services.storage._r2_client")
    def test_returns_none_when_not_configured(self, mock_client_fn):
        mock_client_fn.return_value = None

        result = get_presigned_url("documents/123/file.pdf")

        assert result is None

    @patch("app.services.storage._r2_client")
    def test_returns_none_on_exception(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.side_effect = Exception("Failed")
        mock_client_fn.return_value = mock_client

        result = get_presigned_url("documents/123/file.pdf")

        assert result is None
