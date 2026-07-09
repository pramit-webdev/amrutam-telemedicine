from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import require_role
from app.modules.analytics.service import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/consultations")
async def consultation_stats(
    days: int = Query(30, ge=1, le=365),
    _: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    return await analytics_service.get_consultation_stats(session, days)


@router.get("/revenue")
async def revenue_stats(
    days: int = Query(30, ge=1, le=365),
    _: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    return await analytics_service.get_revenue_stats(session, days)


@router.get("/top-doctors")
async def top_doctors(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    _: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    return await analytics_service.get_top_doctors(session, days, limit)
