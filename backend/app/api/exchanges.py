import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.encryption import encrypt_value
from app.models import User, ExchangeAccount
from app.schemas import ExchangeAccountCreate, ExchangeAccountResponse

router = APIRouter()


@router.post("/", response_model=ExchangeAccountResponse)
async def create_exchange_account(
    account_data: ExchangeAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.binance_service import BinanceClient

    client = BinanceClient(account_data.api_key, account_data.api_secret, account_data.testnet)
    try:
        await client.get_account()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API credentials")

    account = ExchangeAccount(
        id=uuid.uuid4(),
        user_id=current_user.id,
        exchange=account_data.exchange,
        api_key_encrypted=encrypt_value(account_data.api_key),
        api_secret_encrypted=encrypt_value(account_data.api_secret),
        testnet=account_data.testnet,
        is_active=True,
    )
    db.add(account)
    await db.flush()
    return account


@router.get("/", response_model=list[ExchangeAccountResponse])
async def list_exchange_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ExchangeAccount).where(ExchangeAccount.user_id == current_user.id))
    return result.scalars().all()


@router.delete("/{account_id}")
async def delete_exchange_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ExchangeAccount).where(ExchangeAccount.id == account_id, ExchangeAccount.user_id == current_user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    await db.delete(account)
    return {"message": "Exchange account deleted"}


@router.post("/{account_id}/test")
async def test_exchange_connection(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ExchangeAccount).where(ExchangeAccount.id == account_id, ExchangeAccount.user_id == current_user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    from app.services.binance_service import get_binance_client
    client = get_binance_client(account.api_key_encrypted, account.api_secret_encrypted, account.testnet)
    try:
        account_info = await client.get_account()
        return {
            "status": "connected",
            "testnet": account.testnet,
            "total_balance": account_info.get("totalWalletBalance", "0"),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Connection failed: {str(e)}")
