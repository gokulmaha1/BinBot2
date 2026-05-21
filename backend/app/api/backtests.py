from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Backtest
from app.schemas import BacktestRequest, BacktestResponse

router = APIRouter()


@router.post("/", response_model=dict)
async def run_backtest(
    backtest_data: BacktestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.plan == "free":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Backtesting requires paid plan")

    from app.services.backtest_engine import BacktestEngine
    from app.services.binance_service import BinanceClient

    client = BinanceClient("", "", testnet=True)
    klines = await client.get_historical_klines(
        backtest_data.symbol,
        backtest_data.timeframe,
        int(backtest_data.start_date.timestamp() * 1000),
        int(backtest_data.end_date.timestamp() * 1000),
    )

    engine = BacktestEngine(db)
    result = await engine.run_backtest(
        user_id=str(current_user.id),
        strategy_name=backtest_data.strategy,
        symbol=backtest_data.symbol,
        timeframe=backtest_data.timeframe,
        start_date=backtest_data.start_date,
        end_date=backtest_data.end_date,
        initial_capital=backtest_data.initial_capital,
        klines=klines,
        config=backtest_data.config,
    )

    return result


@router.get("/", response_model=list[BacktestResponse])
async def list_backtests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Backtest).where(Backtest.user_id == current_user.id).order_by(Backtest.created_at.desc()))
    return result.scalars().all()


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Backtest).where(Backtest.id == backtest_id, Backtest.user_id == current_user.id))
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found")
    return backtest
