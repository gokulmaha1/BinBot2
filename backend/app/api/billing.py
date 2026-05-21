from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.services.billing_service import BillingService

router = APIRouter()


@router.post("/checkout")
async def create_checkout_session(
    plan: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BillingService(db)
    try:
        result = await service.create_checkout_session(str(current_user.id), plan)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BillingService(db)
    try:
        return await service.cancel_subscription(str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plans")
async def get_plans():
    from app.services.billing_service import PLANS
    return PLANS


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    service = BillingService(db)
    try:
        return await service.handle_webhook(payload, stripe_signature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
