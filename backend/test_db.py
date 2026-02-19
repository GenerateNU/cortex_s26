import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(dotenv_path="/Users/gordonbie/Documents/cortex_s26/.env")

from supabase._async.client import create_client

url = os.environ.get("SUPABASE_URL")
if not url:
    url = "http://127.0.0.1:54321"

key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

async def main():
    if not key:
        print("Missing SUPABASE_SERVICE_ROLE_KEY env vars.")
        return
        
    supabase = await create_client(url, key)
    res = await supabase.table("relationships").select("*").execute()
    print("RELATIONSHIPS:")
    for r in res.data:
        print(r)
    
    fr = await supabase.table("file_relationships").select("*").execute()
    print("FILE_RELATIONSHIPS count:", len(fr.data))
    if len(fr.data) > 0:
        print("Sample:", fr.data[:2])

if __name__ == "__main__":
    asyncio.run(main())
