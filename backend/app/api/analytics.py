from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/")
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AnalyticsService(db)
    return await service.get_user_analytics(str(current_user.id), days)


@router.get("/bot/{bot_id}")
async def get_bot_analytics(
    bot_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models import Bot
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.user_id == current_user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Bot not found")

    service = AnalyticsService(db)
    return await service.get_bot_analytics(bot_id, days)
