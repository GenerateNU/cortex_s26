import os

import cognee

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

    _cognee_initialized = True
