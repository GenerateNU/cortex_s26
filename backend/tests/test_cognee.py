from dotenv import load_dotenv

load_dotenv(override=True)

import asyncio  # noqa: E402

import cognee  # noqa: E402
from cognee.api.v1.search import SearchType  # noqa: E402


async def setup_cognee():
    """Initialize cognee environment."""
    pass

async def ingest_document(files):
    """Ingest documents"""
    for file in files:
        print(f"Ingesting {file}...")
        await cognee.add(
            file,
            dataset_name="smoke-test"
        )
        print(f"Added {file}")

    print("Running cognify with dataset...")
    try:
        await cognee.cognify(datasets=["smoke-test"])
        print("Cognify with dataset completed")
    except Exception as e:
        print(f"Cognify with dataset error: {e}")

async def search_knowledge_graph():
    """query the ingested data"""
    results = {}

    results["chunks"] = await cognee.search(
        query_text="What is contained in the files?",
        query_type=SearchType.CHUNKS,
    )

    results["graph_completion"] = await cognee.search(
        query_text="What is contained in the files?"
    )

    return results

async def main():
    files = ["mock_data/DeepFryer-1.pdf", "mock_data/DeepFryer-2.pdf"]

    await setup_cognee()
    await ingest_document(files)

    print("Waiting for cognify to complete...")
    await asyncio.sleep(5)

    results = await search_knowledge_graph()

    all_passed = True

    for search_type, data in results.items():
        if len(data) > 0:
            print(f"  PASS: {search_type} returned {len(data)} results")
        else:
            print(f"  FAIL: {search_type} returned 0 results")
            all_passed = False

    # --- Summary ---
    if all_passed:
        print("\n SMOKE TEST PASSED")
    else:
        print("\n SMOKE TEST FAILED")

    await cognee.prune.prune_system(graph=True, vector=True, metadata=False)

if __name__ == '__main__':
    asyncio.run(main())
