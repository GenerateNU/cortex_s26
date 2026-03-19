import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.preprocess_service import PreprocessService


async def test_preprocess_flow():
    # Mock dependencies
    mock_repo = AsyncMock()
    mock_pdf_strategy = AsyncMock()
    mock_relationship_service = AsyncMock()

    # Setup mocks
    file_id = uuid4()
    file_name = "test_document.pdf"

    # Mock get_extraction_with_file_info return
    mock_repo.get_extraction_with_file_info.return_value = {
        "raw_files": {"file_name": file_name, "file_link": "path/to/test_document.pdf"}
    }

    # Mock download
    mock_repo.download_file.return_value = b"fake pdf content"

    # Mock extraction result
    mock_pdf_strategy.extract_data.return_value = {
        "result": {
            "file_type": "RFQ",
            "summary": "A test summary",
            "extracted_json": {"foo": "bar"},
        }
    }

    # Instantiate service
    service = PreprocessService(mock_repo, mock_pdf_strategy, mock_relationship_service)

    # Run method with patched generate_embedding
    try:
        with patch(
            "app.services.preprocess_service.generate_embedding", new_callable=AsyncMock
        ) as mock_embedding:
            mock_embedding.return_value = [0.1, 0.2, 0.3]
            await service.process_pdf_upload(file_id)
            print("Service method executed successfully")
    except Exception as e:
        print(f"Service method failed: {e}")

    # Verify update_extraction_result was called with file_name
    # args: file_id, extracted_data, embedding, file_name
    call_args = mock_repo.update_extraction_result.call_args
    if call_args:
        args, _ = call_args
        passed_file_name = args[3]  # 4th argument
        if passed_file_name == file_name:
            print(
                f"SUCCESS: file_name '{passed_file_name}' was passed to update_extraction_result"
            )
        else:
            print(
                f"FAILURE: Expected file_name '{file_name}', got '{passed_file_name}'"
            )
    else:
        print("FAILURE: update_extraction_result was not called")


if __name__ == "__main__":
    asyncio.run(test_preprocess_flow())
