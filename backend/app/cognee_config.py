import os

import cognee

_cognee_initialized: bool = False


async def setup_cognee() -> None:
    global _cognee_initialized

    if _cognee_initialized:
        return

    # LLM
    llm_provider = os.getenv("LLM_PROVIDER")
    llm_model = os.getenv("LLM_MODEL")
    llm_api_key = os.getenv("LLM_API_KEY")

    # Embeddings
    embedding_provider = os.getenv("EMBEDDING_PROVIDER")
    embedding_model = os.getenv("EMBEDDING_MODEL")
    embedding_api_key = os.getenv("EMBEDDING_API_KEY")

    # Vector DB
    vector_db_provider = os.getenv("VECTOR_DB_PROVIDER")
    vector_db_url = os.getenv("VECTOR_DB_URL")

    # Relational DB
    db_provider = os.getenv("DB_PROVIDER")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if llm_provider:
        await cognee.config.set_llm_config(
            {
                "provider": llm_provider,
                "model": llm_model,
                "api_key": llm_api_key,
            }
        )

    if embedding_provider:
        await cognee.config.set_embedding_config(
            {
                "provider": embedding_provider,
                "model": embedding_model,
                "api_key": embedding_api_key,
            }
        )

    if vector_db_provider:
        await cognee.config.set_vector_db_config(
            {
                "provider": vector_db_provider,
                "url": vector_db_url,
            }
        )

    if db_provider:
        await cognee.config.set_relational_db_config(
            {
                "provider": db_provider,
                "host": db_host,
                "port": db_port,
                "database": db_name,
                "user": db_user,
                "password": db_password,
            }
        )

    _cognee_initialized = True
