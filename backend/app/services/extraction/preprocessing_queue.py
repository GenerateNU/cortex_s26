import asyncio
import logging
from uuid import UUID

from supabase._async.client import AsyncClient

from app.repositories.extraction_repository import ExtractionRepository
from app.services.extraction.csv_strategy import get_csv_extraction_strategy
from app.services.extraction.pdf_strategy import get_pdf_extraction_strategy
from app.services.pattern_recognition_service import PatternRecognitionService
from app.services.preprocess_service import PreprocessService

logger = logging.getLogger(__name__)


class PreprocessingQueue:
    def __init__(self, supabase: AsyncClient):
        self._queue = asyncio.Queue()
        self._worker_task = None
        # Initialize dependencies
        extraction_repo = ExtractionRepository(supabase)
        pdf_strategy = get_pdf_extraction_strategy()
        relationship_service = PatternRecognitionService(supabase)

        csv_strategy = get_csv_extraction_strategy()
        self.service = PreprocessService(
            extraction_repo, pdf_strategy, csv_strategy, relationship_service
        )

    async def start_worker(self):
        """Start background worker"""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        """Process items sequentially"""

        while True:
            extracted_file_id = await self._queue.get()
            try:
                logger.info("Processing %s", extracted_file_id)
                await self.service.process_pdf_upload(extracted_file_id)
                logger.info("Completed %s", extracted_file_id)
            except Exception as e:
                logger.error("Failed %s: %s", extracted_file_id, e)
            finally:
                self._queue.task_done()

    async def enqueue(self, file_upload_id: UUID) -> UUID:
        """Add to queue"""
        extracted_file_id = await self.service.created_queued_extraction(file_upload_id)
        await self._queue.put(extracted_file_id)
        return extracted_file_id


_queue: PreprocessingQueue | None = None


async def init_queue(supabase: AsyncClient):
    global _queue
    _queue = PreprocessingQueue(supabase)
    await _queue.start_worker()
    logger.info("Preprocessing Queue Initialized")


async def shutdown_queue():
    global _queue
    if _queue and _queue._worker_task:
        _queue._worker_task.cancel()
        try:
            await _queue._worker_task
        except asyncio.CancelledError:
            pass
    _queue = None


def get_queue() -> PreprocessingQueue:
    if _queue is None:
        raise RuntimeError("Preprocessing queue not initialized")
    return _queue
