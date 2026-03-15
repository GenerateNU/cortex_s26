from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.search_service import SearchService


@pytest.mark.asyncio
async def test_rag_search_returns_answer_and_sources():
    service = SearchService(supabase=AsyncMock())

    fake_results = [
        {
            "file_id": "11111111-1111-1111-1111-111111111111",
            "file_name": "robot_spec.pdf",
            "file_type": "Product Spec",
            "summary": "Spec for an industrial robot arm.",
            "extracted_json": {"manufacturer": "FANUC", "payload": "25kg"},
            "similarity": 0.91,
        }
    ]

    service.search = AsyncMock(return_value=fake_results)

    fake_llm_response = AsyncMock()
    fake_llm_response.choices = [
        type(
            "Choice",
            (),
            {
                "message": type(
                    "Message",
                    (),
                    {
                        "content": "This document describes an industrial robot arm. [Document 1]"
                    },
                )()
            },
        )()
    ]
    service.llm.chat = AsyncMock(return_value=fake_llm_response)

    result = await service.rag_search("What is this document about?")

    assert (
        result["answer"]
        == "This document describes an industrial robot arm. [Document 1]"
    )
    assert result["sources"] == fake_results
    service.search.assert_awaited_once()
    service.llm.chat.assert_awaited_once()

#### Testing Idea 3 - Hybrid NLP Search Engine

@pytest.mark.asyncio
async def test_hybrid_search_calls_hybrid_function():
    """Hybrid search calls hybrid_search RPC with query_text parameter"""
    # ARRANGE
    mock_supabase = AsyncMock()

    mock_execute_result = MagicMock()
    mock_execute_result.data = []

    mock_rpc_result = MagicMock()
    mock_rpc_result.execute = AsyncMock(return_value=mock_execute_result)

    mock_supabase.rpc = MagicMock(return_value=mock_rpc_result)

    service = SearchService(supabase=mock_supabase)

    fake_embedding = [0.1] * 768

    # ACT
    with patch('app.services.search_service.generate_embedding', new_callable=AsyncMock, return_value=fake_embedding):
        await service.search("TechVision", limit=5, threshold=0.3)

    # ASSERT
    mock_supabase.rpc.assert_called_once()

    # Get the actual call arguments
    call_args, call_kwargs = mock_supabase.rpc.call_args

    # Check function name (first positional argument)
    assert call_args[0] == "hybrid_search"

    # Check parameters (second positional argument or kwargs)
    params = call_args[1] if len(call_args) > 1 else call_kwargs

    assert "query_text" in params
    assert params["query_text"] == "TechVision"
    assert "query_embedding" in params
    assert params["query_embedding"] == fake_embedding
