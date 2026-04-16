import asyncio
import logging

from supabase._async.client import AsyncClient

logger = logging.getLogger(__name__)


async def wait_for_supabase(supabase: AsyncClient):
    """
    Waits for Supabase to be ready by attempting simple queries.
    """
    logger.info("Waiting for Supabase...")
    retries = 0
    max_retries = 10

    while retries < max_retries:
        try:
            # Simple query to check connectivity
            await (
                supabase.table("cortex_documents")
                .select("count", count="exact")
                .execute()
            )
            logger.info("Supabase connected!")
            return
        except Exception as e:
            retries += 1
            logger.info(
                "Waiting for Supabase... (%s/%s) Error: %s",
                retries,
                max_retries,
                e,
            )
            # print(f"DEBUG: URL={supabase.supabase_url}, KEY={supabase.supabase_key[:10]}...", flush=True)
            await asyncio.sleep(2)

    logger.warning("thorough Supabase check failed, proceeding anyway...")
