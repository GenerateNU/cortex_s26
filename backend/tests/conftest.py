"""
Pytest configuration and shared fixtures.

Sets fake env vars at module level so that storage.py's module-level
boto3.client() and supabase.create_client() don't blow up at import time.
"""
import os

os.environ.setdefault("CLOUDFLARE_R2_ENDPOINT", "https://fake.r2.cloudflarestorage.com")
os.environ.setdefault("CLOUDFLARE_R2_ACCESS_KEY_ID", "fake-access-key")
os.environ.setdefault("CLOUDFLARE_R2_SECRET_KEY", "fake-secret-key")
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key")

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import api_router  # noqa: E402
from app.core.supabase import get_async_supabase  # noqa: E402


@pytest.fixture()
def app():
    """Full FastAPI app with all routes mounted — no lifespan side effects."""
    test_app = FastAPI()
    test_app.include_router(api_router)

    # Stub the async Supabase dependency used by GET /api/health.
    # The chain is: await supabase.table(...).select(...).execute()
    # Only .execute() is awaited, so use MagicMock for the chain and
    # AsyncMock only for the terminal .execute() call.
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.execute = AsyncMock(
        return_value=MagicMock(count=42),
    )

    async def _fake_supabase():
        return mock_supabase

    test_app.dependency_overrides[get_async_supabase] = _fake_supabase
    yield test_app
    test_app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    """TestClient wired to the full app.  Does not re-raise server errors so
    tests can assert on HTTP status codes instead."""
    return TestClient(app, raise_server_exceptions=False)
