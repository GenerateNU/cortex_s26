"""
Storage service for handling file uploads and downloads.
"""
import os

import boto3

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("CLOUDFLARE_R2_ENDPOINT"),
    aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
    region_name="auto",
)

async def upload_file_cloudflare(file_path, bucket, key) -> str:
    s3.upload_file(file_path, bucket, key)
    return f"s3://{bucket}/{key}"

async def download_file_cloudflare(bucket, key) -> bytes:
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()

from supabase import create_client  # noqa: E402

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

async def upload_file_supabase(file_path, bucket, key) -> str:
    with open(file_path, "rb") as f:
        supabase.storage.from_(bucket).upload(
            path=key,
            file=f,
            file_options={"content-type": "application/octet-stream"},
        )
    return f"{bucket}/{key}"

async def download_file_supabase(bucket, key) -> bytes:
    response = supabase.storage.from_(bucket).download(key)
    return response.read()
