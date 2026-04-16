import logging
import os

import cognee

from app.services.ingest import check_cognee_storage

logger = logging.getLogger(__name__)

_cognee_initialized: bool = False


async def setup_cognee() -> None:
    global _cognee_initialized

    if _cognee_initialized:
        return

    # Fail fast if critical env vars are missing
    required_vars = {
        "LLM_API_KEY": os.getenv("LLM_API_KEY"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    }
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    llm_provider = os.getenv("LLM_PROVIDER")
    llm_model = os.getenv("LLM_MODEL")
    llm_api_key = os.getenv("LLM_API_KEY")

    embedding_provider = os.getenv("EMBEDDING_PROVIDER")
    embedding_model = os.getenv("EMBEDDING_MODEL")
    embedding_api_key = os.getenv("EMBEDDING_API_KEY")

    if llm_provider:
        cognee.config.set_llm_config(
            {
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_api_key": llm_api_key,
            }
        )

    if embedding_provider:
        cognee.config.set_embedding_config(
            {
                "embedding_provider": embedding_provider,
                "embedding_model": embedding_model,
                "embedding_api_key": embedding_api_key,
            }
        )

    cognee.config.set_graph_db_config(
        {
            "graph_database_provider": "kuzu",
        }
    )

    cognee.config.set_vector_db_config(
        {
            "vector_db_provider": "pgvector",
            "vector_db_url": os.getenv("VECTOR_DB_URL", ""),
        }
    )
    cognee.config.set_relational_db_config(
        {
            "db_path": "",
            "db_provider": "postgres",
            "db_host": os.getenv("DB_HOST"),
            "db_port": os.getenv("DB_PORT", "5432"),
            "db_name": os.getenv("DB_NAME"),
            "db_username": os.getenv("DB_USER"),
            "db_password": os.getenv("DB_PASSWORD"),
        }
    )

    _cognee_initialized = True

    # Verify Cognee's local storage directory is writable before any request
    # arrives. Raises RuntimeError with a clear message if not.
    try:
        check_cognee_storage()
    except RuntimeError:
        logger.exception("Cognee storage check failed on startup")
        raise
