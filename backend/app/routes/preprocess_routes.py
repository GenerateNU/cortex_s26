from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.services.extraction.preprocessing_queue import PreprocessingQueue, get_queue

router = APIRouter(prefix="/preprocess", tags=["preprocess"])

@router.post("/{file_id}")
async def preprocess_file(
    file_id: UUID,
    queue: PreprocessingQueue = Depends(get_queue)
):
    """
    Queue a file for preprocessing (Extraction).
    """
    try:
        # Enqueue the file_id directly
        task_id = await queue.enqueue(file_id)
        return {"message": "File queued for preprocessing", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
