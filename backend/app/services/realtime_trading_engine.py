import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bot, Trade, ExchangeAccount
from app.services.binance_service import get_binance_client
from app.services.risk_engine import RiskEngine
from app.services.strategy_engine import get_strategy, Signal
from app.services.indicators import TechnicalIndicators
from app.services.market_detector import MarketConditionDetector
from app.services.websocket_manager import BinanceWebSocketManager, KlineData
from app.ml.predictor import ml_predictor

logger = logging.getLogger(__name__)


class RealtimeTradingEngine:
    def __init__(self, db: AsyncSession, ws_manager: BinanceWebSocketManager):
        self.db = db
        self.ws_manager = ws_manager
        self.risk_engine = RiskEngine(db)
        self._running_bots: Dict[str, asyncio.Task] = {}

    async def start_bot(self, bot: Bot, exchange_account: ExchangeAccount):
        bot_id = str(bot.id)
        if bot_id in self._running_bots:
            return

        self.ws_manager._subscribed_symbols.add(bot.symbol)

        self.ws_manager.on_kline(bot.symbol, "5m", lambda k: self._on_kline(bot, exchange_account, k))
        self.ws_manager.on_ticker(bot.symbol, lambda t: self._on_ticker(bot, exchange_account, t))

        task = asyncio.create_task(self._bot_loop(bot, exchange_account))
        self._running_bots[bot_id] = task

        logger.info(f"Started real-time bot: {bot.name} ({bot.symbol})")

    async def stop_bot(self, bot_id: str):
        task = self._running_bots.pop(bot_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped bot: {bot_id}")

    async def _bot_loop(self, bot: Bot, exchange_account: ExchangeAccount):
        check_interval = 5
        while True:
            try:
                await self._process_bot_cycle(bot, exchange_account)
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Bot {bot.id} cycle error: {e}")
                await asyncio.sleep(check_interval)

    async def _process_bot_cycle(self, bot: Bot, exchange_account: ExchangeAccount):
        if bot.status != "running":
            return

        klines = self.ws_manager.get_klines(bot.symbol, "5m", limit=200)
        if len(klines) < 50:
            return

        current_price = self.ws_manager.get_current_price(bot.symbol)
        if current_price is None:
            return

        df = self._klines_to_dataframe(klines)
        df = TechnicalIndicators.calculate_all_indicators(df)

        market_condition = MarketConditionDetector.detect(df)

        vwap = self.ws_manager.get_vwap(bot.symbol, "5m", 20)
        if vwap and "vwap" in df.columns:
            pass

        volume_profile = self.ws_manager.get_volume_profile(bot.symbol, "5m", 50)
        buy_sell_ratio = self.ws_manager.get_buy_sell_ratio(bot.symbol, "5m", 20)
        volatility_index = self.ws_manager.get_volatility_index(bot.symbol, "5m", 20)

        orderbook = self.ws_manager.get_orderbook(bot.symbol)
        if orderbook and orderbook.bids and orderbook.asks:
            bid_volume = sum(b[1] for b in orderbook.bids[:5])
            ask_volume = sum(a[1] for a in orderbook.asks[:5])
            orderbook_imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0
        else:
            orderbook_imbalance = 0

        strategy = get_strategy(bot.strategy)
        signal = strategy.generate_signal(df, current_price, bot.config or {})

        if signal.side is None:
            return

        if buy_sell_ratio is not None:
            if signal.side == "BUY" and buy_sell_ratio < 0.8:
                return
            if signal.side == "SELL" and buy_sell_ratio > 1.2:
                return

        if volatility_index is not None:
            if volatility_index < 0.5 and bot.strategy not in ["mean_reversion", "scalping"]:
                return

        ml_result = None
        if ml_predictor.model is not None:
            ml_result = ml_predictor.predict(df, bot.symbol)
            if ml_result and ml_result["prediction"] != signal.side:
                if ml_result["confidence"] > 0.7:
                    return

        liquidations = self.ws_manager.get_recent_liquidations(bot.symbol, 10)
        if liquidations:
            recent_liq = liquidations[-1]
            if recent_liq.side == "BUY" and signal.side == "BUY":
                signal.confidence *= 0.8
            elif recent_liq.side == "SELL" and signal.side == "SELL":
                signal.confidence *= 0.8

        balance_result = await exchange_account.get_balance()
        account_balance = float(balance_result.get("availableBalance", 0))

        risk_check = await self.risk_engine.check_trade_allowed(
            str(bot.id), account_balance, signal.entry_price, signal.stop_loss
        )

        if not risk_check["allowed"]:
            logger.warning(f"Risk check failed for bot {bot.id}: {risk_check['reason']}")
            return

        client = get_binance_client(
            exchange_account.api_key_encrypted,
            exchange_account.api_secret_encrypted,
            exchange_account.testnet,
        )

        if bot.live_mode:
            await self._execute_live_trade(bot, signal, risk_check, client, ml_result, market_condition)
        else:
            await self._execute_paper_trade(bot, signal, risk_check, ml_result, market_condition)

        await self._check_open_trades(bot, current_price, exchange_account, client if bot.live_mode else None)

    async def _on_kline(self, bot: Bot, exchange_account: ExchangeAccount, kline: KlineData):
        if kline.is_closed and bot.status == "running":
            asyncio.create_task(self._process_bot_cycle(bot, exchange_account))

    async def _on_ticker(self, bot: Bot, exchange_account: ExchangeAccount, ticker):
        if bot.status == "running":
            await self._check_open_trades(bot, ticker.price, exchange_account, None)

    async def _execute_live_trade(self, bot: Bot, signal: Signal, risk_check: dict, client, ml_result: dict, market_condition: dict):
        quantity = risk_check["position_size"]
        side = "BUY" if signal.side == "BUY" else "SELL"

        order = await client.place_market_order(bot.symbol, side, quantity)

        fills = order.get("fills", [{}])
        fill_price = float(fills[0].get("price", signal.entry_price))

        trade = Trade(
            id=uuid.uuid4(),
            bot_id=bot.id,
            symbol=bot.symbol,
            side=side,
            entry_price=fill_price,
            quantity=quantity,
            leverage=bot.leverage,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            take_profit_levels=[
                {"price": signal.take_profit, "percentage": 0.5},
                {"price": signal.take_profit * 1.5 if signal.side == "BUY" else signal.take_profit * 0.5, "percentage": 0.3},
                {"price": signal.take_profit * 2 if signal.side == "BUY" else signal.take_profit * 0.3, "percentage": 0.2},
            ],
            trailing_stop=0.01,
            status="open",
            strategy_used=bot.strategy,
            ml_confidence=ml_result["confidence"] if ml_result else None,
            market_condition=market_condition["condition"],
        )
        self.db.add(trade)
        await self.db.flush()

        stop_side = "SELL" if side == "BUY" else "BUY"
        try:
            await client.place_stop_market_order(bot.symbol, stop_side, quantity, signal.stop_loss, reduce_only=True)
        except Exception as e:
            logger.error(f"Failed to place stop loss: {e}")

        logger.info(f"LIVE TRADE OPEN: {side} {bot.symbol} @ {fill_price} | SL: {signal.stop_loss} | TP: {signal.take_profit}")

        return {"trade_id": str(trade.id), "action": "open", "side": side, "entry_price": fill_price}

    async def _execute_paper_trade(self, bot: Bot, signal: Signal, risk_check: dict, ml_result: dict, market_condition: dict):
        trade = Trade(
            id=uuid.uuid4(),
            bot_id=bot.id,
            symbol=bot.symbol,
            side=signal.side,
            entry_price=signal.entry_price,
            quantity=risk_check["position_size"],
            leverage=bot.leverage,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            take_profit_levels=[
                {"price": signal.take_profit, "percentage": 0.5},
                {"price": signal.take_profit * 1.5 if signal.side == "BUY" else signal.take_profit * 0.5, "percentage": 0.3},
                {"price": signal.take_profit * 2 if signal.side == "BUY" else signal.take_profit * 0.3, "percentage": 0.2},
            ],
            trailing_stop=0.01,
            status="open",
            strategy_used=bot.strategy,
            ml_confidence=ml_result["confidence"] if ml_result else None,
            market_condition=market_condition["condition"],
        )
        self.db.add(trade)
        await self.db.flush()

        logger.info(f"PAPER TRADE OPEN: {signal.side} {bot.symbol} @ {signal.entry_price}")

        return {"trade_id": str(trade.id), "action": "paper_open"}

    async def _check_open_trades(self, bot: Bot, current_price: float, exchange_account, client):
        result = await self.db.execute(select(Trade).where(Trade.bot_id == bot.id, Trade.status == "open"))
        open_trades = result.scalars().all()

        for trade in open_trades:
            should_close = False
            exit_reason = None
            pnl = 0

            if trade.side == "BUY":
                if trade.stop_loss and current_price <= trade.stop_loss:
                    should_close = True
                    exit_reason = "stop_loss"
                    pnl = (current_price - trade.entry_price) * trade.quantity
                elif trade.take_profit and current_price >= trade.take_profit:
                    should_close = True
                    exit_reason = "take_profit"
                    pnl = (current_price - trade.entry_price) * trade.quantity
            else:
                if trade.stop_loss and current_price >= trade.stop_loss:
                    should_close = True
                    exit_reason = "stop_loss"
                    pnl = (trade.entry_price - current_price) * trade.quantity
                elif trade.take_profit and current_price <= trade.take_profit:
                    should_close = True
                    exit_reason = "take_profit"
                    pnl = (trade.entry_price - current_price) * trade.quantity

            trailing_stop_price = await self.risk_engine.check_should_trailing_stop(trade, current_price)
            if trailing_stop_price:
                trade.stop_loss = trailing_stop_price
                await self.db.flush()

            breakeven_price = await self.risk_engine.check_should_move_to_breakeven(trade, current_price)
            if breakeven_price:
                if trade.side == "BUY" and trade.stop_loss < breakeven_price:
                    trade.stop_loss = breakeven_price
                elif trade.side == "SELL" and trade.stop_loss > breakeven_price:
                    trade.stop_loss = breakeven_price
                await self.db.flush()

            if trade.take_profit_levels:
                for level in trade.take_profit_levels:
                    tp_price = level["price"]
                    if trade.side == "BUY" and current_price >= tp_price:
                        partial_qty = trade.quantity * level["percentage"]
                        pnl += (tp_price - trade.entry_price) * partial_qty
                    elif trade.side == "SELL" and current_price <= tp_price:
                        partial_qty = trade.quantity * level["percentage"]
                        pnl += (trade.entry_price - tp_price) * partial_qty

            if should_close:
                trade.exit_price = current_price
                trade.pnl = pnl
                trade.pnl_percentage = (pnl / (trade.entry_price * trade.quantity)) * 100 if (trade.entry_price * trade.quantity) > 0 else 0
                trade.status = "closed"
                trade.exit_reason = exit_reason
                trade.exit_timestamp = datetime.now(timezone.utc)

                if client and bot.live_mode:
                    try:
                        close_side = "SELL" if trade.side == "BUY" else "BUY"
                        await client.place_market_order(bot.symbol, close_side, trade.quantity, reduce_only=True)
                    except Exception as e:
                        logger.error(f"Failed to close live trade: {e}")

                await self.risk_engine.update_trade_result(str(bot.id), pnl)

                logger.info(f"TRADE CLOSED: {trade.side} {bot.symbol} | PnL: {pnl:.2f} | Reason: {exit_reason}")

                await self.db.flush()

    def _klines_to_dataframe(self, klines: list):
        import pandas as pd
        df = pd.DataFrame(klines)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
