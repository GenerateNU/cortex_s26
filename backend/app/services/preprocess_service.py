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
from app.services.extraction.csv_strategy import (
    CsvExtractionStrategy,
    get_csv_extraction_strategy,
)
from app.services.pattern_recognition_service import PatternRecognitionService


class PreprocessService:
    def __init__(
        self,
        extraction_repo: ExtractionRepository,
        pdf_strategy: PdfExtractionStrategy,
        csv_strategy: CsvExtractionStrategy,
        relationship_service: PatternRecognitionService
    ):
        self.extraction_repo = extraction_repo
        self.pdf_strategy = pdf_strategy
        self.csv_strategy = csv_strategy
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

            # 1. Download File
            file_bytes = await self.extraction_repo.download_file(file_link)
            print(f"File downloaded: {file_name}", flush=True)

            # 2. Determine Strategy and Extract
            if file_name.lower().endswith('.csv'):
                print("Processing as CSV", flush=True)
                # Returns list of dicts
                extraction_results = await self.csv_strategy.extract_data(file_bytes, file_name)
                
                # Delete the initial "Queued" placeholder if it exists (since we will create N new entries)
                # Or we can update the first one and insert the rest.
                # Simpler to delete the placeholder and insert all new rows? 
                # Or just keep the placeholder as a "File Record" and insert rows?
                # User wants "every single row is its own document".
                # Let's delete the initial "Queued" entry created by create_queued_extraction
                # to avoid a "Processing..." ghost item.
                await self.extraction_repo.delete_by_file_id(file_id)
                
            else:
                print("Processing as PDF", flush=True)
                # Returns single dict result wrapped in list for uniform processing
                single_result = await self.pdf_strategy.extract_data(file_bytes, file_name)
                # Emulate the structure from CSV strategy for consistency
                extraction_results = [{
                    "file_name": file_name,
                    "result": single_result["result"],
                     # We reuse the original file_id for the single PDF case
                    "use_existing_id": True 
                }]

            # 3. Process Results
            for item in extraction_results:
                row_name = item["file_name"]
                extracted_data = item["result"]
                use_existing = item.get("use_existing_id", False)
                row_index = item.get("row_index", None)
                
                print(f"Processing item: {row_name}", flush=True)

                # Generate Embedding
                embedding = await generate_embedding(extracted_data)
                
                # Save to DB
                if use_existing:
                    # Update the existing record (PDF case)
                    # Use existing file_id
                    await self.extraction_repo.update_extraction_result(
                        file_id, extracted_data, embedding, row_name
                    )
                    current_id = file_id
                else:
                    # Insert new record (CSV Row case)
                    current_id = await self.extraction_repo.create_extraction_entry(
                        file_id=file_id, # FK to raw file
                        file_name=row_name,
                        extracted_data=extracted_data,
                        embedding=embedding,
                        row_index=row_index
                    )

                # Relationship Detection
                summary = extracted_data.get("summary", "")
                if summary:
                    # Pass the correct file_id (raw_file ID), not the current_id (extracted_file ID for CSV rows)
                    # This obeys the file_relationships.file_id foreign key constraint to raw_files
                    
                    # Also wrap in try-except so a 429 RateLimitError won't break the entire extraction queue
                    try:
                        await self.relationship_service.detect_and_link(file_id, summary)
                    except Exception as rel_err:
                        print(f"Non-fatal relationship detection error for {row_name}: {rel_err}")

            print("All items processed", flush=True)
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
        get_csv_extraction_strategy(),
        PatternRecognitionService(supabase)
    )
