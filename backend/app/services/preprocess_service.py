# app/services/preprocess_service.py
from uuid import UUID

from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.services.extraction.embeddings import generate_embedding
from app.services.extraction.csv_excel_strategy import (
    CsvExcelExtractionStrategy,
    get_csv_extraction_strategy,
    get_excel_extraction_strategy,
)
from app.services.extraction.pdf_strategy import PdfExtractionStrategy, get_pdf_extraction_strategy
from app.repositories.extraction_repository import ExtractionRepository
from app.services.product_service import ProductService
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schemas import ProductIngest


class PreprocessService:
    def __init__(
        self,
        extraction_repo: ExtractionRepository,
        pdf_strategy: PdfExtractionStrategy,
        product_service: ProductService,
        csv_strategy: CsvExtractionStrategy,
        excel_strategy: ExcelExtractionStrategy,
        csv_excel_strategy: CsvExcelExtractionStrategy
    ):
        self.extraction_repo = extraction_repo
        self.pdf_strategy = pdf_strategy
        self.csv_strategy = csv_strategy
        self.excel_strategy = excel_strategy
        self.csv_excel_strategy = csv_excel_strategy
        self.product_service = product_service

    async def created_queued_extraction(self, file_upload_id: UUID) -> UUID:
        """
        Created an extracted_files entry with status "queued" and returns the extracted_file_id
        """
        return await self.extraction_repo.create_queued_extraction(file_upload_id)

    async def process_file_upload(self, extracted_file_id: UUID) -> str:
        """
        Full preprocessing pipeline:
        1. Download file from storage
        2. Extract structured data
        3. Generate embedding
        4. Store in extracted_files
        5. Ingest into Product Search Index
        """
        try:
            # Update status to "processing"
            await self.extraction_repo.update_status(extracted_file_id, "processing")

            response_data = await self.extraction_repo.get_extraction_with_file_info(extracted_file_id)

            tenant_id = response_data["file_uploads"]["tenant_id"]
            file_name = response_data["file_uploads"]["name"]
            file_name_lower = file_name.lower()

            # Download PDF
            pdf_bytes = await self.extraction_repo.download_file(tenant_id, file_name)
            print("PDF downloaded", flush=True)

            # Extract data
            extraction_result = await self.pdf_strategy.extract_data(
                pdf_bytes, file_name, file_id=str(extracted_file_id)
            )
            extracted_json = extraction_result.get(
                "extracted_json", extraction_result["result"]
            )
            llm_summary = extraction_result.get("llm_summary")
            doc_file_type = extraction_result.get("file_type")
            output_filename = extraction_result.get("filename", file_name)
            print("Data extracted", flush=True)

            # Generate embedding for whole document
            embedding_vector = await generate_embedding(extracted_json)
            print("Embedding generated", flush=True)

            # Update status to "complete" with extracted data and embedding
            await self.extraction_repo.update_extraction_result(
                extracted_file_id,
                extracted_json,
                embedding_vector,
                filename=output_filename,
                file_type=doc_file_type,
                llm_summary=llm_summary,
            )
            print("Extraction stored", flush=True)
            
            # --- AUTO-INGESTION ---
            try:
                # Attempt to find a suitable ID for the product. 
                # If extraction has 'product_id' or 'id', use it. Otherwise fall back to file name or UUID.
                product_id = extracted_json.get("product_id") or extracted_json.get("id") or file_name
                
                # Create ingestion object
                ingest_data = ProductIngest(
                    product_id=str(product_id),
                    metadata=extracted_json
            # Download file
            file_bytes = await self.extraction_repo.download_file(tenant_id, file_name)
            print("File downloaded", flush=True)

            # Route by file extension
            if file_name_lower.endswith(".pdf"):
                # PDF returns single dict - wrap in list for consistent processing
                extraction_result = await self.pdf_strategy.extract_data(
                    file_bytes, file_name
                )
                extraction_results = [extraction_result]
            elif file_name_lower.endswith((".csv", ".xlsx", ".xls")):
                # CSV/Excel return list of dicts (one per row)
                extraction_results = self.csv_excel_strategy.extract_data(
                    file_bytes, file_name
                )
            else:
                raise ValueError(f"Unsupported file extension for '{file_name}'")

            print(f"Data extracted: {len(extraction_results)} items", flush=True)

            # Process each extracted item
            # For PDF: 1 iteration
            # For CSV/Excel: N iterations (one per row)
            for idx, extraction_result in enumerate(extraction_results, start=1):
                extracted_json = extraction_result["result"]
                
                # Generate embedding for this item
                embedding_vector = await generate_embedding(extracted_json)
                print(f"Embedding generated for item {idx}/{len(extraction_results)}", flush=True)

                # Create extracted_file entry for this item
                await self.extraction_repo.create_extracted_file(
                    source_file_id=response_data["source_file_id"],
                    extracted_data=extracted_json,
                    embedding=embedding_vector,
                )

            # Mark the original queued extraction as complete
            await self.extraction_repo.update_status(extracted_file_id, "complete")

            print(f"Extraction complete: {len(extraction_results)} items stored", flush=True)
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
        get_pdf_extraction_strategy(),
        get_csv_extraction_strategy(),
    )
