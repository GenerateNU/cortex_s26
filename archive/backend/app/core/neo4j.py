# app/core/neo4j.py
import os
from app.repositories.graph_repository import GraphRepository

_graph_repo: GraphRepository 


def get_graph_repo() -> GraphRepository | None:
    """
    Returns a shared GraphRepository singleton.
    Connection is created once on first call, reused after that.
    Returns None if Neo4j is not configured or unreachable.
    """
    global _graph_repo

    if _graph_repo is not None:
        return _graph_repo

    try:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        database = os.getenv("NEO4J_DATABASE", None)

        _graph_repo = GraphRepository(uri, user, password, database)
        print("Neo4j connection established", flush=True)
        return _graph_repo
    except Exception as e:
        print(f"Neo4j not available: {e}", flush=True)
        return None