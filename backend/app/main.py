import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# Load env vars from .env file (looks in current or parent directories)
load_dotenv()  # noqa: E402

# Fix for local dev: Map VITE_SUPABASE_URL to SUPABASE_URL if not set
if not os.getenv("SUPABASE_URL") and os.getenv("VITE_SUPABASE_URL"):
    os.environ["SUPABASE_URL"] = os.getenv("VITE_SUPABASE_URL")

# Fix for local dev: Map SUPABASE_SERVICE_ROLE_KEY if differently named
if not os.getenv("SUPABASE_SERVICE_ROLE_KEY") and os.getenv(
    "BACKEND_SUPABASE_SERVICE_ROLE_KEY"
):
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = os.getenv(
        "BACKEND_SUPABASE_SERVICE_ROLE_KEY"
    )


from app.api import api_router  # noqa: E402
from app.cognee_config import setup_cognee  # noqa: E402
from app.core.supabase import get_async_supabase  # noqa: E402
from app.core.webhooks import configure_webhooks  # noqa: E402
from app.services.extraction.preprocessing_queue import init_queue  # noqa: E402
from app.services.supabase_check import wait_for_supabase  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.document_metadata_service import recover_stale_documents
    from app.services.extraction.preprocessing_queue import shutdown_queue

    logger.info("Lifespan starting")
    try:
        supabase = await get_async_supabase()
        await wait_for_supabase(supabase)
        await configure_webhooks(supabase)
        await init_queue(supabase)
        await setup_cognee()
        await recover_stale_documents()
    except Exception:
        logger.exception("Startup failed")
        raise

    yield

    # Shutdown
    await shutdown_queue()


app = FastAPI(title="Cortex ETL API", lifespan=lifespan)

_allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router)


@app.get("/")
def read_root():
    return {"message": "Cortex ETL Backend"}
