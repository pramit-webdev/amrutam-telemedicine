from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.modules.doctors.schemas import DoctorCreate, SlotBatchCreate
from app.modules.doctors.service import doctor_service

router = APIRouter(tags=["doctors"])


@router.post("/doctors/profile")
async def create_doctor_profile(
    request: Request,
    body: DoctorCreate,
    current_user: dict = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await doctor_service.create_or_update_profile(
        session, current_user["id"], body.model_dump(),
        ip_address=ip_address, user_agent=user_agent,
    )


@router.get("/doctors/profile")
async def get_doctor_profile(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await doctor_service.get_profile(session, current_user["id"])


@router.get("/doctors/search")
async def search_doctors(
    specialization: str | None = Query(None),
    min_rating: float | None = Query(None, ge=0, le=5),
    max_fee: float | None = Query(None, ge=0),
    available_only: bool = Query(False),
    query: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return await doctor_service.search(session, specialization, min_rating, max_fee, available_only, query, page, size)


@router.get("/doctors/{doctor_id}")
async def get_doctor(
    doctor_id: str,
    session: AsyncSession = Depends(get_session),
):
    from uuid import UUID
    return await doctor_service.get_doctor_by_id(session, UUID(doctor_id))


@router.post("/doctors/slots")
async def add_slots(
    request: Request,
    body: SlotBatchCreate,
    current_user: dict = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    slots_data = [{"start_time": s.start_time, "end_time": s.end_time} for s in body.slots]
    return await doctor_service.add_slots(
        session, current_user["id"], slots_data,
        ip_address=ip_address, user_agent=user_agent,
    )


@router.get("/doctors/{doctor_id}/slots")
async def get_doctor_slots(
    doctor_id: str,
    date: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    from uuid import UUID
    return await doctor_service.get_slots(session, UUID(doctor_id), date)
