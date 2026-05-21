import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bot, Trade
from app.services.binance_service import BinanceClient, get_binance_client
from app.services.risk_engine import RiskEngine
from app.services.strategy_engine import get_strategy, Signal
from app.services.indicators import TechnicalIndicators
from app.services.market_detector import MarketConditionDetector
from app.ml.predictor import ml_predictor

import pandas as pd


class TradingEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.risk_engine = RiskEngine(db)

    async def execute_bot_cycle(self, bot: Bot, klines: list, current_price: float, exchange_account) -> Optional[dict]:
        if bot.status != "running":
            return None

        df = self._klines_to_dataframe(klines)
        if df is None or len(df) < 50:
            return None

        df = TechnicalIndicators.calculate_all_indicators(df)

        market_condition = MarketConditionDetector.detect(df)

        strategy = get_strategy(bot.strategy)
        signal = strategy.generate_signal(df, current_price, bot.config or {})

        if signal.side is None:
            return None

        ml_result = None
        if ml_predictor.model is not None:
            ml_result = ml_predictor.predict(df, bot.symbol)
            if ml_result and ml_result["prediction"] != signal.side:
                if ml_result["confidence"] > 0.7:
                    return None

        balance_result = await exchange_account.get_balance()
        account_balance = float(balance_result.get("availableBalance", 0))

        risk_check = await self.risk_engine.check_trade_allowed(
            str(bot.id), account_balance, signal.entry_price, signal.stop_loss
        )

        if not risk_check["allowed"]:
            return None

        client = get_binance_client(
            exchange_account.api_key_encrypted,
            exchange_account.api_secret_encrypted,
            exchange_account.testnet,
        )

        if bot.live_mode:
            return await self._execute_live_trade(bot, signal, risk_check, client, ml_result, market_condition)
        else:
            return await self._execute_paper_trade(bot, signal, risk_check, ml_result, market_condition)

    async def _execute_live_trade(self, bot: Bot, signal: Signal, risk_check: dict, client: BinanceClient, ml_result: dict, market_condition: dict) -> dict:
        quantity = risk_check["position_size"]

        side = "BUY" if signal.side == "BUY" else "SELL"

        order = await client.place_market_order(bot.symbol, side, quantity)

        trade = Trade(
            id=uuid.uuid4(),
            bot_id=bot.id,
            symbol=bot.symbol,
            side=side,
            entry_price=float(order.get("fills", [{}])[0].get("price", signal.entry_price)),
            quantity=quantity,
            leverage=bot.leverage,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            take_profit_levels=[
                {"price": signal.take_profit, "percentage": 0.5},
                {"price": signal.take_profit * 1.5, "percentage": 0.3},
                {"price": signal.take_profit * 2, "percentage": 0.2},
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
        except Exception:
            pass

        return {
            "trade_id": str(trade.id),
            "action": "open",
            "side": side,
            "entry_price": trade.entry_price,
            "quantity": quantity,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
        }

    async def _execute_paper_trade(self, bot: Bot, signal: Signal, risk_check: dict, ml_result: dict, market_condition: dict) -> dict:
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
                {"price": signal.take_profit * 1.5, "percentage": 0.3},
                {"price": signal.take_profit * 2, "percentage": 0.2},
            ],
            trailing_stop=0.01,
            status="open",
            strategy_used=bot.strategy,
            ml_confidence=ml_result["confidence"] if ml_result else None,
            market_condition=market_condition["condition"],
        )
        self.db.add(trade)
        await self.db.flush()

        return {
            "trade_id": str(trade.id),
            "action": "paper_open",
            "side": signal.side,
            "entry_price": signal.entry_price,
            "quantity": risk_check["position_size"],
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
        }

    async def check_open_trades(self, bot: Bot, current_price: float, exchange_account) -> list:
        result = await self.db.execute(select(Trade).where(Trade.bot_id == bot.id, Trade.status == "open"))
        open_trades = result.scalars().all()
        closed = []

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

            breakeven_price = await self.risk_engine.check_should_move_to_breakeven(trade, current_price)
            if breakeven_price:
                trade.stop_loss = breakeven_price

            if should_close:
                trade.exit_price = current_price
                trade.pnl = pnl
                trade.pnl_percentage = (pnl / (trade.entry_price * trade.quantity)) * 100
                trade.status = "closed"
                trade.exit_reason = exit_reason
                trade.exit_timestamp = datetime.now(timezone.utc)

                if bot.live_mode:
                    client = get_binance_client(
                        exchange_account.api_key_encrypted,
                        exchange_account.api_secret_encrypted,
                        exchange_account.testnet,
                    )
                    try:
                        close_side = "SELL" if trade.side == "BUY" else "BUY"
                        await client.place_market_order(bot.symbol, close_side, trade.quantity, reduce_only=True)
                    except Exception:
                        pass

                await self.risk_engine.update_trade_result(str(bot.id), pnl)
                closed.append({
                    "trade_id": str(trade.id),
                    "action": "close",
                    "exit_reason": exit_reason,
                    "pnl": pnl,
                    "exit_price": current_price,
                })

        return closed

    def _klines_to_dataframe(self, klines: list) -> Optional[pd.DataFrame]:
        if not klines:
            return None
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
