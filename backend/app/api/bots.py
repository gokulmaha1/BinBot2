import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Bot, Trade, ExchangeAccount
from app.schemas import BotCreate, BotUpdate, BotResponse, TradeResponse
from app.services.billing_service import BillingService

router = APIRouter()


@router.post("/", response_model=BotResponse)
async def create_bot(
    bot_data: BotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bots_result = await db.execute(select(Bot).where(Bot.user_id == current_user.id))
    bot_count = len(bots_result.scalars().all())

    billing = BillingService(db)
    if not billing.can_create_bot(current_user.plan, bot_count):
        plan_info = billing.get_plan_info(current_user.plan)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan limit reached. Max bots: {plan_info['max_bots']}",
        )

    if bot_data.live_mode and current_user.plan == "free":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Live trading requires paid plan")

    bot = Bot(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=bot_data.name,
        strategy=bot_data.strategy,
        symbol=bot_data.symbol.upper(),
        leverage=min(bot_data.leverage, 5),
        status="stopped",
        live_mode=bot_data.live_mode,
        config=bot_data.config,
        risk_config=bot_data.risk_config or {
            "max_risk_per_trade": 0.01,
            "max_daily_loss": 0.03,
            "max_drawdown": 0.08,
            "max_consecutive_losses": 3,
            "max_leverage": 5,
        },
    )
    db.add(bot)
    await db.flush()
    return bot


@router.get("/", response_model=list[BotResponse])
async def list_bots(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Bot).where(Bot.user_id == current_user.id))
    return result.scalars().all()


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.user_id == current_user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    return bot


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: str,
    bot_data: BotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.user_id == current_user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    if bot_data.name:
        bot.name = bot_data.name
    if bot_data.strategy:
        bot.strategy = bot_data.strategy
    if bot_data.leverage is not None:
        bot.leverage = min(bot_data.leverage, 5)
    if bot_data.status:
        bot.status = bot_data.status
    if bot_data.config is not None:
        bot.config = bot_data.config
    if bot_data.risk_config is not None:
        bot.risk_config = bot_data.risk_config

    return bot


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.user_id == current_user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    await db.delete(bot)
    return {"message": "Bot deleted"}


@router.post("/{bot_id}/start")
async def start_bot(
    bot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.user_id == current_user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    exchange_result = await db.execute(select(ExchangeAccount).where(ExchangeAccount.user_id == current_user.id, ExchangeAccount.is_active))
    exchange_account = exchange_result.scalar_one_or_none()
    if not exchange_account:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active exchange account")

    from app.main import ws_manager
    from app.services.realtime_trading_engine import RealtimeTradingEngine

    ws_manager._subscribed_symbols.add(bot.symbol)
    ws_manager.on_kline(bot.symbol, "5m", lambda k: None)
    ws_manager.on_ticker(bot.symbol, lambda t: None)

    engine = RealtimeTradingEngine(db, ws_manager)
    await engine.start_bot(bot, exchange_account)

    bot.status = "running"
    return {"message": "Bot started with real-time WebSocket", "bot_id": str(bot.id)}


@router.post("/{bot_id}/stop")
async def stop_bot(
    bot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.user_id == current_user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    from app.main import ws_manager
    from app.services.realtime_trading_engine import RealtimeTradingEngine

    engine = RealtimeTradingEngine(db, ws_manager)
    await engine.stop_bot(bot_id)

    bot.status = "stopped"
    return {"message": "Bot stopped"}


@router.get("/{bot_id}/trades", response_model=list[TradeResponse])
async def get_bot_trades(
    bot_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.user_id == current_user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    trades_result = await db.execute(
        select(Trade).where(Trade.bot_id == bot_id).order_by(Trade.entry_timestamp.desc()).limit(limit)
    )
    return trades_result.scalars().all()
