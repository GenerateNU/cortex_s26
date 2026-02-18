import asyncio
import json
import httpx

API_URL = "http://localhost:8000"

async def test_hybrid_search():
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as client:
        print("🚀 Testing Hybrid Semantic Search...")

        # 1. Ingest Product
        product_data = {
            "product_id": "TEST-100",
            "metadata": {
                "name": "Wireless Noise Cancelling Headphones",
                "category": "Electronics",
                "description": "Premium over-ear headphones with active noise cancellation and 30-hour battery life.",
                "price": 299.99,
                "color": "Black"
            }
        }
        
        print(f"\n📥 Ingesting product: {product_data['product_id']}...")
        response = await client.post("/products/ingest", json=product_data)
        if response.status_code == 201:
            print("✅ Ingestion successful!")
        else:
            print(f"❌ Ingestion failed: {response.text}")
            return

        # Wait a moment for consistency (though pure Postgres insert is immediate, good practice)
        await asyncio.sleep(1)

        # 2. Exact ID Search
        print("\n🔍 Testing Exact Match (ID)...")
        search_payload = {"query": "TEST-100", "limit": 1}
        response = await client.post("/products/search", json=search_payload)
        results = response.json()
        
        if results and results[0]['product_id'] == "TEST-100":
             print(f"✅ Exact match successful: Found {results[0]['metadata']['name']}")
        else:
             print(f"❌ Exact match failed. Results: {json.dumps(results, indent=2)}")

        # 3. Semantic Search
        print("\n🧠 Testing Semantic Search...")
        # Query that doesn't share many keywords but matches meaning
        queries = [
            "quiet headset for travel",
            "gadgets for listening into music"
        ]
        
        for q in queries:
            print(f"   Query: '{q}'")
            search_payload = {"query": q, "limit": 3}
            response = await client.post("/products/search", json=search_payload)
            results = response.json()
            
            found = False
            for res in results:
                if res['product_id'] == "TEST-100":
                    found = True
                    print(f"   ✅ Found product (Score: {res['score']:.4f})")
                    break
            
            if not found:
                print("   ❌ Semantic search failed to find the product.")

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
