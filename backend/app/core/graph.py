import os 

from functools import lru_cache
from app.repositories.graph_repository import GraphRepository


@lru_cache
def get_graph_repository() -> GraphRepository:
    """
    Creates a single Neo4j driver instance for the whole app.
    lru_cache ensures we don't open a new connection pool per request.
    """
    return GraphRepository(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE"),
    )
