from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "binbot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="send_email")
def send_email_task(to: str, subject: str, body: str):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        raise e


@celery_app.task(name="reset_daily_loss")
def reset_daily_loss_task(bot_id: str):
    import asyncio
    from app.core.database import async_session
    from app.services.risk_engine import RiskEngine

    async def run():
        async with async_session() as db:
            engine = RiskEngine(db)
            await engine.reset_daily_loss(bot_id)
            await db.commit()

    asyncio.run(run())


@celery_app.task(name="train_ml_model")
def train_ml_model_task(symbol: str, interval: str = "5m", days: int = 90):
    import asyncio
    import pandas as pd
    from app.ml.predictor import ml_predictor
    from app.services.binance_service import BinanceClient
    from app.services.indicators import TechnicalIndicators
    import time

    async def run():
        client = BinanceClient("", "", testnet=True)
        end_time = int(time.time() * 1000)
        start_time = end_time - (days * 24 * 60 * 60 * 1000)

        klines = await client.get_historical_klines(symbol, interval, start_time, end_time)

        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        df = TechnicalIndicators.calculate_all_indicators(df)

        result = ml_predictor.train_model(df, symbol)
        return result

    return asyncio.run(run())


@celery_app.task(name="run_bot_cycle")
def run_bot_cycle_task(bot_id: str):
    import asyncio
    from app.core.database import async_session
    from sqlalchemy import select
    from app.models import Bot, ExchangeAccount
    from app.services.realtime_trading_engine import RealtimeTradingEngine
    from app.main import ws_manager

    async def run():
        async with async_session() as db:
            result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.status == "running"))
            bot = result.scalar_one_or_none()
            if not bot:
                return

            exchange_result = await db.execute(select(ExchangeAccount).where(ExchangeAccount.user_id == bot.user_id, ExchangeAccount.is_active))
            exchange_account = exchange_result.scalar_one_or_none()
            if not exchange_account:
                return

            engine = RealtimeTradingEngine(db, ws_manager)
            await engine._process_bot_cycle(bot, exchange_account)
            await db.commit()

    asyncio.run(run())
