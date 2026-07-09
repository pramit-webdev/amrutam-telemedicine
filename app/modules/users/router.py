from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.modules.users.schemas import ProfileUpdate
from app.modules.users.service import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await user_service.get_profile(session, current_user["id"])


@router.put("/me")
async def update_my_profile(
    body: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await user_service.update_profile(
        session, current_user["id"], body.model_dump(exclude_none=True)
    )
