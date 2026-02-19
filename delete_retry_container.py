
import asyncio
import os
from supabase._async.client import create_client

# Local Supabase credentials inside Docker or accessible from within
url = "http://host.docker.internal:54321" 
key = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"

async def main():
    try:
        supabase = await create_client(url, key)
        # Delete the failed entry
        print("Attempting delete...", flush=True)
        response = await supabase.table("extracted_files").delete().eq("file_id", "fe070806-a89c-4903-9ed6-f28161dca5ec").execute()
        print(f"Delete response: {response}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
