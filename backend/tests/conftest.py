"""
Pytest configuration and shared fixtures.

Sets fake env vars at module level so that storage.py's module-level
boto3.client() and supabase.create_client() don't blow up at import time.
"""
import os

os.environ.setdefault("CLOUDFLARE_R2_ENDPOINT", "https://fake.r2.cloudflarestorage.com")
os.environ.setdefault("R2_ACCESS_KEY", "fake-access-key")
os.environ.setdefault("R2_SECRET_KEY", "fake-secret-key")
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-supabase-key")
