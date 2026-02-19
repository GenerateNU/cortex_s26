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
from app.services.pattern_recognition_service import PatternRecognitionService


class PreprocessService:
    def __init__(
        self,
        extraction_repo: ExtractionRepository,
        pdf_strategy: PdfExtractionStrategy,
        relationship_service: PatternRecognitionService
    ):
        self.extraction_repo = extraction_repo
        self.pdf_strategy = pdf_strategy
        self.relationship_service = relationship_service

    async def created_queued_extraction(self, file_id: UUID) -> UUID:
        """
        Created an extracted_files entry with status "queued" and returns the file_id
        """
        return await self.extraction_repo.create_queued_extraction(file_id)

    async def process_pdf_upload(self, file_id: UUID) -> str:
        """
        Full preprocessing pipeline:
        1. Download PDF from storage (using raw_files link)
        2. Extract structured data + Classification + Summary
        3. Generate Vector Embedding
        4. Store in database
        5. Detect & Link Relationships
        """
        try:
            # Update summary to "processing"
            await self.extraction_repo.update_status(file_id, "Processing PDF...")

            response_data = await self.extraction_repo.get_extraction_with_file_info(file_id)

            # New schema: raw_files table
            raw_file = response_data["raw_files"]
            file_name = raw_file["file_name"]
            file_link = raw_file["file_link"]

            # 1. Download PDF
            pdf_bytes = await self.extraction_repo.download_file(file_link)
            print(f"PDF downloaded: {file_name}", flush=True)

            # 2. Extract data (JSON + Type + Summary)
            extraction_result = await self.pdf_strategy.extract_data(pdf_bytes, file_name)

            # 'result' contains: file_type, summary, extracted_json
            extracted_data = extraction_result["result"]
            print("Data extracted & classified", flush=True)

            # 3. Generate Embedding
            # We embed the whole result structure (JSON + Summary) for semantic search
            embedding = await generate_embedding(extracted_data)
            print("Embedding generated", flush=True)

            # 4. Save to Database
            await self.extraction_repo.update_extraction_result(
                file_id, extracted_data, embedding
            )
            print("Extraction saved to DB", flush=True)

            # 5. Relationship Detection
            # We use the summary to infer relationships
            summary = extracted_data.get("summary", "")
            if summary:
                print("Detecting relationships...", flush=True)
                await self.relationship_service.detect_and_link(file_id, summary)
                print("Relationships processed", flush=True)

            return str(file_id)

        except Exception as e:
            # Update status to "failed"
            print(f"Processing failed for {file_id}: {e}", flush=True)
            await self.extraction_repo.update_status(file_id, "Failed", str(e))
            raise

    async def delete_previous_extraction(self, file_id: UUID):
        """
        Delete Previous extracted data entry if one exists
        """
        await self.extraction_repo.delete_by_file_id(file_id)


def get_preprocess_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> PreprocessService:
    """Instantiates a PreprocessService object in route parameters"""
    return PreprocessService(
        ExtractionRepository(supabase),
        get_pdf_extraction_strategy(),
        PatternRecognitionService(supabase)
    )
