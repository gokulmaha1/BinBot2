import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.services.websocket_manager import BinanceWebSocketManager

settings = get_settings()
logger = logging.getLogger(__name__)

ws_manager = BinanceWebSocketManager(ws_url=settings.BINANCE_WS_URL)


async def start_websocket_streams():
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    await ws_manager.subscribe(symbols)
    logger.info(f"Subscribed to WebSocket streams for {len(symbols)} symbols")


async def stop_websocket_streams():
    await ws_manager.stop()
    logger.info("WebSocket streams stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BinBot AI...")
    await start_websocket_streams()
    yield
    logger.info("Shutting down BinBot AI...")
    await stop_websocket_streams()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Binance Futures trading platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


from app.api import auth, users, bots, exchanges, strategies, backtests, analytics, billing, admin, websocket as ws_router

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(bots.router, prefix="/api/bots", tags=["bots"])
app.include_router(exchanges.router, prefix="/api/exchanges", tags=["exchanges"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(backtests.router, prefix="/api/backtests", tags=["backtests"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(ws_router.router, prefix="/api/ws", tags=["websocket"])


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "websocket_connected": ws_manager._ws is not None,
        "subscribed_symbols": list(ws_manager._subscribed_symbols),
    }


@app.get("/api/ws/price/{symbol}")
async def get_realtime_price(symbol: str):
    price = ws_manager.get_current_price(symbol.upper())
    ticker = ws_manager.get_ticker(symbol.upper())
    if price is None:
        return JSONResponse(status_code=404, content={"detail": "Symbol not subscribed"})
    return {
        "symbol": symbol.upper(),
        "price": price,
        "price_change_24h": ticker.price_change if ticker else 0,
        "price_change_percent_24h": ticker.price_change_percent if ticker else 0,
        "volume_24h": ticker.volume_24h if ticker else 0,
    }


@app.get("/api/ws/klines/{symbol}/{interval}")
async def get_realtime_klines(symbol: str, interval: str, limit: int = 100):
    klines = ws_manager.get_klines(symbol.upper(), interval, limit)
    if not klines:
        return JSONResponse(status_code=404, content={"detail": "No kline data"})
    return {"symbol": symbol.upper(), "interval": interval, "klines": klines}


@app.get("/api/ws/orderbook/{symbol}")
async def get_realtime_orderbook(symbol: str):
    ob = ws_manager.get_orderbook(symbol.upper())
    if ob is None:
        return JSONResponse(status_code=404, content={"detail": "No orderbook data"})
    return {
        "symbol": symbol.upper(),
        "bids": ob.bids[:10],
        "asks": ob.asks[:10],
        "spread": ob.asks[0][0] - ob.bids[0][0] if ob.asks and ob.bids else 0,
    }


@app.get("/api/ws/metrics/{symbol}")
async def get_realtime_metrics(symbol: str):
    sym = symbol.upper()
    vwap = ws_manager.get_vwap(sym)
    volume_profile = ws_manager.get_volume_profile(sym)
    buy_sell_ratio = ws_manager.get_buy_sell_ratio(sym)
    volatility_index = ws_manager.get_volatility_index(sym)
    funding_rate = ws_manager.get_funding_rate_trend(sym)
    open_interest = ws_manager.get_open_interest(sym)
    liquidations = ws_manager.get_recent_liquidations(sym, 5)

    return {
        "symbol": sym,
        "vwap": vwap,
        "volume_profile": volume_profile,
        "buy_sell_ratio": buy_sell_ratio,
        "volatility_index": volatility_index,
        "funding_rate": funding_rate,
        "open_interest": open_interest,
        "recent_liquidations": [
            {"side": l.side, "price": l.price, "quantity": l.quantity}
            for l in liquidations
        ],
    }


@app.get("/api/strategies/public")
async def public_strategies():
    from app.services.strategy_engine import STRATEGIES
    return {
        name: {"name": s.name, "description": s.description}
        for name, s in STRATEGIES.items()
    }
