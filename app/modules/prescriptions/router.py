from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.modules.prescriptions.schemas import PrescriptionCreate
from app.modules.prescriptions.service import prescription_service

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.post("")
async def create_prescription(
    body: PrescriptionCreate,
    current_user: dict = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
):
    return await prescription_service.create(
        session, current_user["id"], body.model_dump()
    )


@router.get("/consultation/{consultation_id}")
async def list_prescriptions(
    consultation_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await prescription_service.list_for_consultation(
        session, UUID(consultation_id)
    )
