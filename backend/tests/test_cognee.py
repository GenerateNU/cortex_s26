import cognee
import asyncio

def setup_cognee():
    """Initialize cognee environment."""
    
async def ingest_document(files):
    """Ingest documents"""
    for file in files:
        await cognee.add()

    cognee.cognify()

async def search_knowledge_graph():
    """query the ingested data"""

    results = await cognee.search(
        query_text="What is contained in the files?"
    )
