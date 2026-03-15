from unittest.mock import AsyncMock, MagicMock, patch

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
            "extracted_json": {"manufacturer": "FANUC","payload": "25kg"},
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
    service.rag_llm.chat = AsyncMock(return_value=fake_llm_response)

    result = await service.rag_search("What is this document about?")

    assert (
        result["answer"]
        == "This document describes an industrial robot arm. [Document 1]"
    )
    assert result["sources"] == fake_results
    service.search.assert_awaited_once()
    service.rag_llm.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_sql_search_calls_execute_sql_rpc():
    """SQL search calls execute_sql RPC with generated SQL query"""

    # ARRANGE
    mock_supabase = AsyncMock()

    mock_execute_result = MagicMock()
    mock_execute_result.data = []

    mock_rpc_result = MagicMock()
    mock_rpc_result.execute = AsyncMock(return_value=mock_execute_result)

    mock_supabase.rpc = MagicMock(return_value=mock_rpc_result)

    service = SearchService(supabase=mock_supabase)

    fake_sql = "SELECT * FROM extracted_files LIMIT 5"

    mock_llm_response = MagicMock()
    mock_llm_response.choices = [
        MagicMock(message=MagicMock(content=fake_sql))
    ]

    # ACT
    with patch.object(
        service.sql_generation_llm,
        "chat",
        new_callable=AsyncMock,
        return_value=mock_llm_response
    ):
        await service.search("find documents about fryers")

    # ASSERT
    mock_supabase.rpc.assert_called_once()

    call_args, call_kwargs = mock_supabase.rpc.call_args

    # Check RPC function name
    assert call_args[0] == "execute_sql"

    # Check parameters
    params = call_args[1] if len(call_args) > 1 else call_kwargs

    assert "query" in params
    assert params["query"] == fake_sql