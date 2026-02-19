import asyncio

from supabase._async.client import AsyncClient


async def wait_for_supabase(supabase: AsyncClient):
    """
    Waits for Supabase to be ready by attempting simple queries.
    """
    print("Waiting for Supabase...", flush=True)
    retries = 0
    max_retries = 10

    while retries < max_retries:
        try:
            # Simple query to check connectivity
            await supabase.table("raw_files").select("count", count="exact").execute()
            print("Supabase Connected!", flush=True)
            return
        except Exception as e:
            retries += 1
            print(f"Waiting for Supabase... ({retries}/{max_retries}) Error: {e}", flush=True)
            # print(f"DEBUG: URL={supabase.supabase_url}, KEY={supabase.supabase_key[:10]}...", flush=True)
            await asyncio.sleep(2)

    print("WARNING: thorough Supabase check failed, proceeding anyway...", flush=True)
