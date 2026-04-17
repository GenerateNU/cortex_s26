"""
Storage service — Cloudflare R2 (S3-compatible).

Gracefully returns None when R2 is not configured so the pipeline
continues without object storage.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_cached_r2_client = None
_r2_client_checked = False


def _r2_bucket() -> str:
    return os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "cortex-documents")


def _r2_client():
    """Lazy, cached R2 client — returns None if any credential is missing."""
    global _cached_r2_client, _r2_client_checked
    if _r2_client_checked:
        return _cached_r2_client

    endpoint = os.getenv("CLOUDFLARE_R2_ENDPOINT", "").rstrip("/")
    access_key = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
    secret_key = os.getenv("CLOUDFLARE_R2_SECRET_KEY", "")

    _r2_client_checked = True

    if not all([endpoint, access_key, secret_key]):
        return None

    try:
        import boto3

        _cached_r2_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        return _cached_r2_client
    except Exception as exc:
        logger.warning("Failed to create R2 client: %s", exc)
        return None


async def upload_to_r2(file_path: str, key: str) -> str | None:
    """
    Upload a file to R2. Returns the key on success, None if R2 is not
    configured or the upload fails.
    """
    client = _r2_client()
    if client is None:
        logger.debug("R2 not configured — skipping upload for %s", file_path)
        return None
    try:
        client.upload_file(file_path, _r2_bucket(), key)
        logger.info("Uploaded %s → R2 key %s", file_path, key)
        return key
    except Exception as exc:
        logger.warning("R2 upload failed for %s: %s", file_path, exc)
        return None


def get_presigned_url(key: str, expires: int = 3600) -> str | None:
    """
    Generate a pre-signed GET URL for an R2 object (valid for *expires* seconds).
    Returns None if R2 is not configured or the call fails.
    """
    client = _r2_client()
    if client is None:
        return None
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _r2_bucket(), "Key": key},
            ExpiresIn=expires,
        )
    except Exception as exc:
        logger.warning("Failed to generate pre-signed URL for %s: %s", key, exc)
        return None
