"""
Tests for storage service.
"""
from unittest.mock import ANY, MagicMock, mock_open, patch

import pytest

from app.services.storage import (
    download_file_cloudflare,
    download_file_supabase,
    upload_file_cloudflare,
    upload_file_supabase,
)

# ── Cloudflare R2 Tests ────────────────────────────────────────────────────────

class TestUploadFileCloudflare:
    @pytest.mark.asyncio
    @patch("app.services.storage.s3")
    async def test_upload_returns_s3_uri(self, mock_s3):
        mock_s3.upload_file.return_value = None
        result = await upload_file_cloudflare("local/file.txt", "my-bucket", "folder/file.txt")

        assert result == "s3://my-bucket/folder/file.txt"

    @pytest.mark.asyncio
    @patch("app.services.storage.s3")
    async def test_upload_calls_s3_with_correct_args(self, mock_s3):
        mock_s3.upload_file.return_value = None

        await upload_file_cloudflare("local/file.txt", "my-bucket", "folder/file.txt")

        mock_s3.upload_file.assert_called_once_with("local/file.txt", "my-bucket", "folder/file.txt")

    @pytest.mark.asyncio
    @patch("app.services.storage.s3")
    async def test_upload_propagates_s3_exception(self, mock_s3):
        mock_s3.upload_file.side_effect = Exception("S3 upload failed")

        with pytest.raises(Exception, match="S3 upload failed"):
            await upload_file_cloudflare("local/file.txt", "my-bucket", "folder/file.txt")


class TestDownloadFileCloudflare:
    @pytest.mark.asyncio
    @patch("app.services.storage.s3")
    async def test_download_returns_bytes(self, mock_s3):
        mock_body = MagicMock()
        mock_body.read.return_value = b"file content"
        mock_s3.get_object.return_value = {"Body": mock_body}

        result = await download_file_cloudflare("my-bucket", "folder/file.txt")

        assert result == b"file content"

    @pytest.mark.asyncio
    @patch("app.services.storage.s3")
    async def test_download_calls_get_object_with_correct_args(self, mock_s3):
        mock_body = MagicMock()
        mock_body.read.return_value = b""
        mock_s3.get_object.return_value = {"Body": mock_body}

        await download_file_cloudflare("my-bucket", "folder/file.txt")

        mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="folder/file.txt")

    @pytest.mark.asyncio
    @patch("app.services.storage.s3")
    async def test_download_propagates_s3_exception(self, mock_s3):
        mock_s3.get_object.side_effect = Exception("Key not found")

        with pytest.raises(Exception, match="Key not found"):
            await download_file_cloudflare("my-bucket", "folder/file.txt")


# ── Supabase Tests ─────────────────────────────────────────────────────────────

class TestUploadFileSupabase:
    @pytest.mark.asyncio
    @patch("builtins.open", mock_open(read_data=b"file content"))
    @patch("app.services.storage.supabase")
    async def test_upload_returns_bucket_key_path(self, mock_supabase):
        mock_supabase.storage.from_().upload.return_value = None

        result = await upload_file_supabase("local/file.txt", "my-bucket", "folder/file.txt")

        assert result == "my-bucket/folder/file.txt"

    @pytest.mark.asyncio
    @patch("builtins.open", mock_open(read_data=b"file content"))
    @patch("app.services.storage.supabase")
    async def test_upload_calls_storage_with_correct_args(self, mock_supabase):
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage

        await upload_file_supabase("local/file.txt", "my-bucket", "folder/file.txt")

        mock_supabase.storage.from_.assert_called_once_with("my-bucket")
        mock_storage.upload.assert_called_once_with(
            path="folder/file.txt",
            file=ANY,
            file_options={"content-type": "application/octet-stream"},
        )

    @pytest.mark.asyncio
    @patch("builtins.open", mock_open(read_data=b"file content"))
    @patch("app.services.storage.supabase")
    async def test_upload_propagates_storage_exception(self, mock_supabase):
        mock_supabase.storage.from_().upload.side_effect = Exception("Upload failed")

        with pytest.raises(Exception, match="Upload failed"):
            await upload_file_supabase("local/file.txt", "my-bucket", "folder/file.txt")


class TestDownloadFileSupabase:
    @pytest.mark.asyncio
    @patch("app.services.storage.supabase")
    async def test_download_returns_bytes(self, mock_supabase):
        mock_supabase.storage.from_().download.return_value = b"file content"

        result = await download_file_supabase("my-bucket", "folder/file.txt")

        assert result == b"file content"

    @pytest.mark.asyncio
    @patch("app.services.storage.supabase")
    async def test_download_calls_storage_with_correct_args(self, mock_supabase):
        mock_storage = MagicMock()
        mock_storage.download.return_value = b""
        mock_supabase.storage.from_.return_value = mock_storage

        await download_file_supabase("my-bucket", "folder/file.txt")

        mock_supabase.storage.from_.assert_called_once_with("my-bucket")
        mock_storage.download.assert_called_once_with("folder/file.txt")

    @pytest.mark.asyncio
    @patch("app.services.storage.supabase")
    async def test_download_propagates_storage_exception(self, mock_supabase):
        mock_supabase.storage.from_().download.side_effect = Exception("File not found")

        with pytest.raises(Exception, match="File not found"):
            await download_file_supabase("my-bucket", "folder/file.txt")
