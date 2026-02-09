# app/services/preprocess_service.py
from uuid import UUID

from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.repositories.extraction_repository import ExtractionRepository
from app.services.extraction.embeddings import generate_embedding
from app.services.extraction.pdf_strategy import (
    PdfExtractionStrategy,
    get_pdf_extraction_strategy,
)


class PreprocessService:
    def __init__(self, extraction_repo: ExtractionRepository, pdf_strategy: PdfExtractionStrategy):
        self.extraction_repo = extraction_repo
        self.pdf_strategy = pdf_strategy

    async def created_queued_extraction(self, file_upload_id: UUID) -> UUID:
        """
        Created an extracted_files entry with status "queued" and returns the extracted_file_id
        """
        return await self.extraction_repo.create_queued_extraction(file_upload_id)

    async def process_pdf_upload(self, extracted_file_id: UUID) -> str:
        """
        Full preprocessing pipeline:
        1. Download PDF from storage
        2. Extract structured data
        3. Generate embedding
        4. Store in extracted_files
        """
        try:
            # Update status to "processing"
            await self.extraction_repo.update_status(extracted_file_id, "processing")

            response_data = await self.extraction_repo.get_extraction_with_file_info(extracted_file_id)

            tenant_id = response_data["file_uploads"]["tenant_id"]
            file_name = response_data["file_uploads"]["name"]

            # Download PDF
            pdf_bytes = await self.extraction_repo.download_file(tenant_id, file_name)
            print("PDF downloaded", flush=True)

            # Extract data
            extraction_result = await self.pdf_strategy.extract_data(pdf_bytes, file_name)
            extracted_json = extraction_result["result"]
            print("Data extracted", flush=True)

            # Generate embedding for whole document
            embedding_vector = await generate_embedding(extracted_json)
            print("Embedding generated", flush=True)

            # Update status to "complete" with extracted data and embedding
            await self.extraction_repo.update_extraction_result(
                extracted_file_id, extracted_json, embedding_vector
            )

            print("Extraction stored", flush=True)
            return str(extracted_file_id)
        except Exception as e:
            # Update status to "failed" and store error
            await self.extraction_repo.update_status(extracted_file_id, "failed", str(e))
            raise

    async def delete_previous_extraction(self, file_upload_id: UUID):
        """
        Delete Previous extracted data entry if one exists
        """
        await self.extraction_repo.delete_by_source_file(file_upload_id)


def get_preprocess_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> PreprocessService:
    """Instantiates a PreprocessService object in route parameters"""
    print("Created Preprocess Service")
    return PreprocessService(
        ExtractionRepository(supabase),
        get_pdf_extraction_strategy()
    )
