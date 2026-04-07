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

    # Force LanceDB to use a local file path. Without this, Cognee picks up
    # VECTOR_DB_URL (a PostgreSQL URL) from the environment and passes it to
    # LanceDB, which only supports file/S3/GCS paths — causing a startup crash.
    cognee.config.set_vector_db_config(
        {
            "vector_db_provider": "lancedb",
            "vector_db_url": "/app/.cognee_system/lancedb",
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
