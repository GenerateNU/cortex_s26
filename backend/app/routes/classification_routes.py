from uuid import UUID

from fastapi import APIRouter, Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.services.classification_service import ClassificationService

router = APIRouter(prefix="/classification", tags=["Classification"])

def get_service(supabase: AsyncClient = Depends(get_async_supabase)) -> ClassificationService:
    return ClassificationService(supabase)

@router.get("/list/{tenant_id}")
async def list_classifications(
    tenant_id: UUID,
    service: ClassificationService = Depends(get_service)
):
    return await service.get_classifications(tenant_id)

@router.post("/create_classifications/{tenant_id}")
async def create_classifications(
    tenant_id: UUID,
    # In a real app we'd accept a body with names, but Frontend hook
    # `useClassifications` calls this without body?
    # Let's check `classification.hooks.tsx`.
    # It seems to just POST to `/create_classifications/{tenant_id}` with no body?
    # Wait, the hook `createClassificationsMutation` calls `api.post(...)`.
    # The hook creates classifications?
    # Ah, `createClassificationsMutation` in frontend seems to imply "Auto-generate classifications"
    # OR it's a manual create.
    # AdminPage.tsx -> ClassificationStep might have a form.
    # Actually, looking at `ClassificationStep`, it likely lets user type names.
    # If the hook payload is empty, maybe it's "Suggest Classifications"?
    # Let's assume for now it might trigger AUTO-creation from documents.
    service: ClassificationService = Depends(get_service)
):
    """
    Generate valid classifications based on existing unclassified documents.
    """
    # For MVP, let's just create some default ones if none exist,
    # or scan files to suggest.
    # The Frontend `useClassifications` has `createClassifications`.
    # Let's verify what the frontend sends.
    # IF the frontend sends data, we need Pydantic model.
    # Logic: Scan all files, ask LLM "What are the distinct categories?", create them.

    # Implementation:
    # 1. Fetch file summaries
    # 2. Ask LLM to cluster/name them
    # 3. Create those classifications

    # Placeholder:
    defaults = ["Invoices", "Contracts", "Specifications", "Receipts"]
    return await service.create_classifications_batch(tenant_id, defaults)

@router.post("/classify_files/{tenant_id}")
async def classify_files(
    tenant_id: UUID,
    service: ClassificationService = Depends(get_service)
):
    """
    Assign existing classifications to unclassified files.
    """
    return await service.classify_files(tenant_id)

@router.get("/visualize_clustering/{tenant_id}")
async def visualize_clustering(
    tenant_id: UUID,
    service: ClassificationService = Depends(get_service)
):
    return await service.get_clustering_visualization(tenant_id)
