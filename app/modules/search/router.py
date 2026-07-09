from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.doctors.service import doctor_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/doctors")
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
