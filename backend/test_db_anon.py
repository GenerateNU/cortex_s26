import asyncio
from supabase._async.client import create_client

url = "http://127.0.0.1:54321"
key = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"

async def main():
    try:
        supabase = await create_client(url, key)
        res = await supabase.table("relationships").select("*").execute()
        print("RELATIONSHIPS ANON:", res.data)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
