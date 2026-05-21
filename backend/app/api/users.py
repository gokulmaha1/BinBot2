from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas import UserUpdate, UserResponse

router = APIRouter()


@router.put("/me", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_data.name:
        current_user.name = user_data.name
    if user_data.email and user_data.email != current_user.email:
        existing = await db.execute(select(User).where(User.email == user_data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        current_user.email = user_data.email
        current_user.is_verified = False
    if user_data.new_password:
        from app.core.security import verify_password, get_password_hash
        if not user_data.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password required")
        if not verify_password(user_data.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password")
        current_user.password_hash = get_password_hash(user_data.new_password)
    return current_user


@router.get("/me/subscription")
async def get_subscription(current_user: User = Depends(get_current_user)):
    from app.services.billing_service import BillingService
    billing = BillingService(db=None)
    plan_info = billing.get_plan_info(current_user.plan)
    return {
        "plan": current_user.plan,
        "status": current_user.subscription_status,
        "features": plan_info["features"],
        "max_bots": plan_info["max_bots"],
    }
