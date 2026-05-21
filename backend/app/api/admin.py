from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models import User, Bot, Trade, AuditLog

router = APIRouter()


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    offset = (page - 1) * limit
    result = await db.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit))
    users = result.scalars().all()

    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()

    return {
        "users": users,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    return {"message": "User disabled"}


@router.post("/users/{user_id}/enable")
async def enable_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    return {"message": "User enabled"}


@router.get("/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    users_count = await db.execute(select(func.count(User.id)))
    bots_count = await db.execute(select(func.count(Bot.id)))
    trades_count = await db.execute(select(func.count(Trade.id)))
    active_bots = await db.execute(select(func.count(Bot.id)).where(Bot.status == "running"))

    return {
        "total_users": users_count.scalar(),
        "total_bots": bots_count.scalar(),
        "total_trades": trades_count.scalar(),
        "active_bots": active_bots.scalar(),
    }


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    offset = (page - 1) * limit
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    logs = result.scalars().all()

    count_result = await db.execute(select(func.count(AuditLog.id)))
    total = count_result.scalar()

    return {"logs": logs, "total": total, "page": page, "limit": limit}
