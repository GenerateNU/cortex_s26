import logging
import os

from supabase._async.client import AsyncClient
from supabase._async.client import create_client as acreate_client

logger = logging.getLogger(__name__)

supabase: AsyncClient | None = None


async def get_async_supabase() -> AsyncClient:
    global supabase
    if supabase is None:
        supabase = await acreate_client(
            os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        logger.info("Supabase Initialized")
    return supabase
