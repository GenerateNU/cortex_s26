from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load env vars from .env file (looks in current or parent directories)
load_dotenv()

# Fix for local dev: Map VITE_SUPABASE_URL to SUPABASE_URL if not set
if not os.getenv("SUPABASE_URL") and os.getenv("VITE_SUPABASE_URL"):
    os.environ["SUPABASE_URL"] = os.getenv("VITE_SUPABASE_URL")

# Fix for local dev: Map SUPABASE_SERVICE_ROLE_KEY if differently named
if not os.getenv("SUPABASE_SERVICE_ROLE_KEY") and os.getenv("BACKEND_SUPABASE_SERVICE_ROLE_KEY"):
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = os.getenv("BACKEND_SUPABASE_SERVICE_ROLE_KEY")


from app.api import api_router
from app.core.supabase import get_async_supabase
from app.core.webhooks import configure_webhooks
from app.services.extraction.preprocessing_queue import init_queue
from app.services.supabase_check import wait_for_supabase


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("LIFESPAN STARTING", flush=True)
    supabase = await get_async_supabase()

    await wait_for_supabase(supabase)

    await configure_webhooks(supabase)

    await init_queue(supabase)

    yield
    # Shutdown (if needed)


app = FastAPI(title="Cortex ETL API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def read_root():
    return {"message": "Cortex ETL Backend"}
