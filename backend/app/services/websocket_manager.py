import asyncio
import json
import time
import logging
from typing import Optional, Callable, Dict, List, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


@dataclass
class KlineData:
    symbol: str
    interval: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_volume: float
    trades: int
    taker_buy_base: float
    taker_buy_quote: float
    is_closed: bool


@dataclass
class TickerData:
    symbol: str
    price: float
    price_change: float
    price_change_percent: float
    high_24h: float
    low_24h: float
    volume_24h: float
    quote_volume_24h: float
    open_interest: float
    funding_rate: float
    timestamp: int


@dataclass
class OrderBookData:
    symbol: str
    bids: List[tuple]
    asks: List[tuple]
    timestamp: int


@dataclass
class TradeData:
    symbol: str
    trade_id: int
    price: float
    quantity: float
    is_buyer_maker: bool
    timestamp: int


@dataclass
class LiquidationData:
    symbol: str
    side: str
    price: float
    quantity: float
    avg_price: float
    status: str
    timestamp: int


class BinanceWebSocketManager:
    def __init__(self, ws_url: str = "wss://fstream.binance.com/ws"):
        self.ws_url = ws_url
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60

        self._kline_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._ticker_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._orderbook_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._trade_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._oi_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._liquidation_handlers: Dict[str, List[Callable]] = defaultdict(list)

        self._kline_cache: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1500)))
        self._ticker_cache: Dict[str, TickerData] = {}
        self._orderbook_cache: Dict[str, OrderBookData] = {}
        self._oi_cache: Dict[str, float] = {}
        self._liquidation_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))

        self._subscribed_symbols: Set[str] = set()
        self._subscribed_intervals: Set[str] = {"1m", "5m", "15m", "1h", "4h"}
        self._ws_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_message_time = 0
        self._heartbeat_timeout = 30

    def on_kline(self, symbol: str, interval: str, handler: Callable):
        key = f"{symbol}_{interval}"
        self._kline_handlers[key].append(handler)

    def on_ticker(self, symbol: str, handler: Callable):
        self._ticker_handlers[symbol].append(handler)

    def on_orderbook(self, symbol: str, handler: Callable):
        self._orderbook_handlers[symbol].append(handler)

    def on_trade(self, symbol: str, handler: Callable):
        self._trade_handlers[symbol].append(handler)

    def on_open_interest(self, symbol: str, handler: Callable):
        self._oi_handlers[symbol].append(handler)

    def on_liquidation(self, symbol: str, handler: Callable):
        self._liquidation_handlers[symbol].append(handler)

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[dict]:
        cache = self._kline_cache.get(symbol, {}).get(interval, deque())
        result = []
        for k in list(cache)[-limit:]:
            result.append({
                "timestamp": k.open_time,
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
                "close_time": k.close_time,
                "quote_volume": k.quote_volume,
                "trades": k.trades,
                "taker_buy_base": k.taker_buy_base,
                "taker_buy_quote": k.taker_buy_quote,
            })
        return result

    def get_ticker(self, symbol: str) -> Optional[TickerData]:
        return self._ticker_cache.get(symbol)

    def get_orderbook(self, symbol: str) -> Optional[OrderBookData]:
        return self._orderbook_cache.get(symbol)

    def get_open_interest(self, symbol: str) -> Optional[float]:
        return self._oi_cache.get(symbol)

    def get_recent_liquidations(self, symbol: str, limit: int = 20) -> List[LiquidationData]:
        cache = self._liquidation_cache.get(symbol, deque())
        return list(cache)[-limit:]

    def get_current_price(self, symbol: str) -> Optional[float]:
        ticker = self._ticker_cache.get(symbol)
        if ticker:
            return ticker.price
        for interval in ["1m", "5m", "15m"]:
            klines = self._kline_cache.get(symbol, {}).get(interval, deque())
            if klines:
                return klines[-1].close
        return None

    def get_vwap(self, symbol: str, interval: str = "5m", period: int = 20) -> Optional[float]:
        klines = self._kline_cache.get(symbol, {}).get(interval, deque())
        if len(klines) < period:
            return None
        recent = list(klines)[-period:]
        total_vp = sum(k.close * k.volume for k in recent)
        total_v = sum(k.volume for k in recent)
        return total_vp / total_v if total_v > 0 else None

    def get_volume_profile(self, symbol: str, interval: str = "5m", period: int = 50) -> dict:
        klines = self._kline_cache.get(symbol, {}).get(interval, deque())
        if len(klines) < period:
            return {"poc": 0, "vah": 0, "val": 0}
        recent = list(klines)[-period:]
        price_volume = defaultdict(float)
        for k in recent:
            price_level = round(k.close / 10) * 10
            price_volume[price_level] += k.volume
        if not price_volume:
            return {"poc": 0, "vah": 0, "val": 0}
        poc = max(price_volume, key=price_volume.get)
        sorted_prices = sorted(price_volume.keys())
        total_volume = sum(price_volume.values())
        cumvol = 0
        vah = sorted_prices[-1]
        val = sorted_prices[0]
        for p in sorted_prices:
            cumvol += price_volume[p]
            if cumvol / total_volume >= 0.7:
                val = p
                break
        cumvol = 0
        for p in reversed(sorted_prices):
            cumvol += price_volume[p]
            if cumvol / total_volume >= 0.7:
                vah = p
                break
        return {"poc": poc, "vah": vah, "val": val}

    def get_funding_rate_trend(self, symbol: str) -> Optional[float]:
        ticker = self._ticker_cache.get(symbol)
        return ticker.funding_rate if ticker else None

    def get_buy_sell_ratio(self, symbol: str, interval: str = "5m", period: int = 20) -> Optional[float]:
        klines = self._kline_cache.get(symbol, {}).get(interval, deque())
        if len(klines) < period:
            return None
        recent = list(klines)[-period:]
        buy_vol = sum(k.taker_buy_base for k in recent)
        sell_vol = sum(k.volume - k.taker_buy_base for k in recent)
        return buy_vol / sell_vol if sell_vol > 0 else float("inf")

    def get_volatility_index(self, symbol: str, interval: str = "5m", period: int = 20) -> Optional[float]:
        klines = self._kline_cache.get(symbol, {}).get(interval, deque())
        if len(klines) < period:
            return None
        recent = list(klines)[-period:]
        returns = []
        for i in range(1, len(recent)):
            if recent[i-1].close > 0:
                returns.append((recent[i].close - recent[i-1].close) / recent[i-1].close)
        if not returns:
            return None
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        return (variance ** 0.5) * (1440 / int(interval.replace("m", "").replace("h", "60")) if "m" in interval else 1440 / (int(interval.replace("h", "")) * 60)) ** 0.5

    async def subscribe(self, symbols: List[str]):
        self._subscribed_symbols.update(symbols)
        if not self._running:
            self._running = True
            self._ws_task = asyncio.create_task(self._run())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

    async def unsubscribe(self, symbols: List[str]):
        self._subscribed_symbols.difference_update(symbols)
        for s in symbols:
            self._kline_cache.pop(s, None)
            self._ticker_cache.pop(s, None)
            self._orderbook_cache.pop(s, None)

    async def stop(self):
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._ws:
            await self._ws.close()

    def _build_streams(self) -> List[str]:
        streams = []
        for symbol in self._subscribed_symbols:
            sym = symbol.lower()
            for interval in self._subscribed_intervals:
                streams.append(f"{sym}@kline_{interval}")
            streams.append(f"{sym}@ticker")
            streams.append(f"{sym}@depth20@100ms")
            streams.append(f"{sym}@trade")
            streams.append(f"{sym}@markPrice")
        streams.append("!forceOrder@arr")
        return streams

    async def _run(self):
        while self._running:
            try:
                streams = self._build_streams()
                if not streams:
                    await asyncio.sleep(1)
                    continue
                stream_path = "/".join(streams)
                url = f"{self.ws_url}/{stream_path}"
                logger.info(f"Connecting to Binance WebSocket: {len(streams)} streams")
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1
                    logger.info("WebSocket connected")
                    async for message in ws:
                        self._last_message_time = time.time()
                        await self._handle_message(message)
            except asyncio.CancelledError:
                break
            except (ConnectionClosed, WebSocketException, OSError) as e:
                logger.warning(f"WebSocket disconnected: {e}. Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self._reconnect_delay)

    async def _heartbeat_monitor(self):
        while self._running:
            await asyncio.sleep(self._heartbeat_timeout)
            if self._last_message_time > 0 and (time.time() - self._last_message_time) > self._heartbeat_timeout:
                logger.warning("WebSocket heartbeat timeout - no messages received")

    async def _handle_message(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        if "e" not in data:
            if isinstance(data, list):
                for item in data:
                    await self._handle_message(json.dumps(item))
            return

        event_type = data.get("e")

        if event_type == "kline":
            await self._handle_kline(data)
        elif event_type == "24hrTicker":
            await self._handle_ticker(data)
        elif event_type == "depthUpdate":
            await self._handle_orderbook(data)
        elif event_type == "trade":
            await self._handle_trade(data)
        elif event_type == "markPrice":
            await self._handle_mark_price(data)
        elif event_type == "forceOrder":
            await self._handle_liquidation(data)

    async def _handle_kline(self, data: dict):
        k = data.get("k", {})
        symbol = data.get("s")
        interval = k.get("i")
        if not symbol or not interval:
            return

        kline = KlineData(
            symbol=symbol,
            interval=interval,
            open_time=k.get("t", 0),
            open=float(k.get("o", 0)),
            high=float(k.get("h", 0)),
            low=float(k.get("l", 0)),
            close=float(k.get("c", 0)),
            volume=float(k.get("v", 0)),
            close_time=k.get("T", 0),
            quote_volume=float(k.get("q", 0)),
            trades=k.get("n", 0),
            taker_buy_base=float(k.get("V", 0)),
            taker_buy_quote=float(k.get("Q", 0)),
            is_closed=k.get("x", False),
        )

        cache = self._kline_cache[symbol][interval]

        if cache and cache[-1].open_time == kline.open_time:
            cache[-1] = kline
        else:
            cache.append(kline)

        key = f"{symbol}_{interval}"
        handlers = self._kline_handlers.get(key, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(kline)
                else:
                    handler(kline)
            except Exception as e:
                logger.error(f"Kline handler error: {e}")

    async def _handle_ticker(self, data: dict):
        symbol = data.get("s")
        if not symbol:
            return

        ticker = TickerData(
            symbol=symbol,
            price=float(data.get("c", 0)),
            price_change=float(data.get("p", 0)),
            price_change_percent=float(data.get("P", 0)),
            high_24h=float(data.get("h", 0)),
            low_24h=float(data.get("l", 0)),
            volume_24h=float(data.get("v", 0)),
            quote_volume_24h=float(data.get("q", 0)),
            open_interest=float(data.get("O", 0)),
            funding_rate=float(data.get("r", 0)),
            timestamp=data.get("E", 0),
        )

        self._ticker_cache[symbol] = ticker

        handlers = self._ticker_handlers.get(symbol, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(ticker)
                else:
                    handler(ticker)
            except Exception as e:
                logger.error(f"Ticker handler error: {e}")

    async def _handle_orderbook(self, data: dict):
        symbol = data.get("s")
        if not symbol:
            return

        bids = [(float(b[0]), float(b[1])) for b in data.get("b", [])]
        asks = [(float(a[0]), float(a[1])) for a in data.get("a", [])]

        if symbol not in self._orderbook_cache:
            self._orderbook_cache[symbol] = OrderBookData(
                symbol=symbol, bids=bids, asks=asks, timestamp=data.get("E", 0)
            )
        else:
            ob = self._orderbook_cache[symbol]
            bid_dict = {b[0]: b[1] for b in ob.bids}
            for price, qty in bids:
                if qty == 0:
                    bid_dict.pop(price, None)
                else:
                    bid_dict[price] = qty
            ask_dict = {a[0]: a[1] for a in ob.asks}
            for price, qty in asks:
                if qty == 0:
                    ask_dict.pop(price, None)
                else:
                    ask_dict[price] = qty
            ob.bids = sorted(bid_dict.items(), key=lambda x: x[0], reverse=True)[:20]
            ob.asks = sorted(ask_dict.items(), key=lambda x: x[0])[:20]
            ob.timestamp = data.get("E", 0)

        handlers = self._orderbook_handlers.get(symbol, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(self._orderbook_cache[symbol])
                else:
                    handler(self._orderbook_cache[symbol])
            except Exception as e:
                logger.error(f"Orderbook handler error: {e}")

    async def _handle_trade(self, data: dict):
        symbol = data.get("s")
        if not symbol:
            return

        trade = TradeData(
            symbol=symbol,
            trade_id=data.get("t", 0),
            price=float(data.get("p", 0)),
            quantity=float(data.get("q", 0)),
            is_buyer_maker=data.get("m", False),
            timestamp=data.get("T", 0),
        )

        handlers = self._trade_handlers.get(symbol, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(trade)
                else:
                    handler(trade)
            except Exception as e:
                logger.error(f"Trade handler error: {e}")

    async def _handle_mark_price(self, data: dict):
        symbol = data.get("s")
        if not symbol:
            return

        self._oi_cache[symbol] = float(data.get("i", 0))

        if symbol in self._ticker_cache:
            self._ticker_cache[symbol].funding_rate = float(data.get("r", 0))

        handlers = self._oi_handlers.get(symbol, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(symbol, float(data.get("i", 0)), float(data.get("r", 0)))
                else:
                    handler(symbol, float(data.get("i", 0)), float(data.get("r", 0)))
            except Exception as e:
                logger.error(f"OI handler error: {e}")

    async def _handle_liquidation(self, data: dict):
        o = data.get("o", {})
        symbol = o.get("s")
        if not symbol:
            return

        liq = LiquidationData(
            symbol=symbol,
            side=o.get("S", ""),
            price=float(o.get("p", 0)),
            quantity=float(o.get("q", 0)),
            avg_price=float(o.get("ap", 0)),
            status=o.get("X", ""),
            timestamp=data.get("E", 0),
        )

        self._liquidation_cache[symbol].append(liq)

        handlers = self._liquidation_handlers.get(symbol, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(liq)
                else:
                    handler(liq)
            except Exception as e:
                logger.error(f"Liquidation handler error: {e}")
