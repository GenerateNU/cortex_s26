import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase._async.client import create_client

url = "http://127.0.0.1:54321"
key = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"

async def main():
    try:
        supabase = await create_client(url, key)
        rel_id = '18768a49-7524-495d-91ca-9b5dab083f95'
        res = await supabase.from_('file_relationships').select('''
          *,
          file:raw_files (
            file_name,
            extracted_file:extracted_files (
              file_type
            )
          )
        ''').eq('relationship_id', rel_id).execute()
        
        print("RESULT:")
        print(res.data)
        if hasattr(res, 'error') and res.error:
            print("ERROR", res.error)
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
