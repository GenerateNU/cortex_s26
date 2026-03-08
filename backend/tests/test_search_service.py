from unittest.mock import AsyncMock

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
                    {"content": "This document describes an industrial robot arm. [Document 1]"},
                )()
            },
        )()
    ]
    service.llm.chat = AsyncMock(return_value=fake_llm_response)

    result = await service.rag_search("What is this document about?")

    assert result["answer"] == "This document describes an industrial robot arm. [Document 1]"
    assert result["sources"] == fake_results
    service.search.assert_awaited_once()
    service.llm.chat.assert_awaited_once()
