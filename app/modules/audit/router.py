from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import require_role
from app.modules.audit.service import audit_service

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
async def get_audit_logs(
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    action: str | None = Query(None),
    user_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    _: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    uid = UUID(user_id) if user_id else None
    return await audit_service.get_logs(
        session, entity_type, entity_id, action, uid, page, size,
    )
