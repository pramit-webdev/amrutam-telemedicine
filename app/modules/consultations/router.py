from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.modules.consultations.schemas import CompleteConsultationRequest, StartConsultationRequest
from app.modules.consultations.service import consultation_service

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.get("")
async def list_consultations(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    role = current_user["role"]
    if role == "patient":
        return await consultation_service.list_for_patient(session, current_user["id"])
    elif role == "doctor":
        return await consultation_service.list_for_doctor(session, current_user["id"])
    return []


@router.get("/{consultation_id}")
async def get_consultation(
    consultation_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await consultation_service.get_by_id(session, UUID(consultation_id))


@router.post("/{consultation_id}/start")
async def start_consultation(
    consultation_id: str,
    body: StartConsultationRequest = StartConsultationRequest(),
    current_user: dict = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
):
    return await consultation_service.start_consultation(
        session, UUID(consultation_id), current_user["id"], body.notes,
    )


@router.post("/{consultation_id}/complete")
async def complete_consultation(
    consultation_id: str,
    body: CompleteConsultationRequest = CompleteConsultationRequest(),
    current_user: dict = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
):
    return await consultation_service.complete_consultation(
        session, UUID(consultation_id), current_user["id"], body.notes,
    )
