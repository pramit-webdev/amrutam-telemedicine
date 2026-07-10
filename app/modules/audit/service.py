from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.audit.models import AuditLog


class AuditService:
    async def log_action(
        self, session: AsyncSession, *,
        user_id: UUID | None = None,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(entry)
        await session.flush()
        return entry
    async def get_logs(
        self, session: AsyncSession,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        page: int = 1,
        size: int = 50,
    ) -> dict:
        stmt = select(AuditLog)
        conditions = []
        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)
        if entity_id:
            conditions.append(AuditLog.entity_id == entity_id)
        if action:
            conditions.append(AuditLog.action == action)
        if user_id:
            conditions.append(AuditLog.user_id == user_id)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        pagination = PaginationParams(page, size)
        stmt = stmt.offset(pagination.offset).limit(pagination.limit).order_by(AuditLog.created_at.desc())

        result = await session.execute(stmt)
        logs = result.scalars().all()

        items = [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

        paginated = PaginatedResponse(items, total, pagination)
        return paginated.dict()


audit_service = AuditService()
