from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bot, Trade


class RiskEngine:
    MAX_RISK_PER_TRADE = 0.01
    MAX_DAILY_LOSS = 0.03
    MAX_DRAWDOWN = 0.08
    MAX_CONSECUTIVE_LOSSES = 3
    MAX_LEVERAGE = 5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_trade_allowed(self, bot_id: str, account_balance: float, entry_price: float, stop_loss: float) -> dict:
        bot_result = await self.db.execute(select(Bot).where(Bot.id == bot_id))
        bot = bot_result.scalar_one_or_none()
        if not bot:
            return {"allowed": False, "reason": "Bot not found"}

        if bot.status != "running":
            return {"allowed": False, "reason": "Bot is not running"}

        risk_config = bot.risk_config or {}
        max_risk = risk_config.get("max_risk_per_trade", self.MAX_RISK_PER_TRADE)
        max_daily = risk_config.get("max_daily_loss", self.MAX_DAILY_LOSS)
        max_dd = risk_config.get("max_drawdown", self.MAX_DRAWDOWN)
        max_consec = risk_config.get("max_consecutive_losses", self.MAX_CONSECUTIVE_LOSSES)
        max_lev = risk_config.get("max_leverage", self.MAX_LEVERAGE)

        if bot.leverage > max_lev:
            return {"allowed": False, "reason": f"Leverage {bot.leverage}x exceeds maximum {max_lev}x"}

        if bot.consecutive_losses >= max_consec:
            return {"allowed": False, "reason": f"Max consecutive losses ({max_consec}) reached. Trading paused."}

        if bot.daily_loss >= account_balance * max_daily:
            return {"allowed": False, "reason": f"Daily loss limit ({max_daily*100}%) reached"}

        drawdown = self._calculate_drawdown(bot)
        if drawdown >= max_dd:
            return {"allowed": False, "reason": f"Max drawdown ({max_dd*100}%) reached"}

        risk_amount = account_balance * max_risk
        stop_distance = abs(entry_price - stop_loss) / entry_price
        if stop_distance == 0:
            return {"allowed": False, "reason": "Invalid stop loss distance"}

        position_size = risk_amount / stop_distance
        notional_value = position_size * entry_price
        max_position = account_balance * max_lev

        if notional_value > max_position:
            position_size = max_position / entry_price
            risk_amount = position_size * stop_distance * entry_price

        return {
            "allowed": True,
            "position_size": position_size,
            "risk_amount": risk_amount,
            "notional_value": notional_value,
            "leverage_used": bot.leverage,
        }

    async def update_trade_result(self, bot_id: str, pnl: float) -> None:
        bot_result = await self.db.execute(select(Bot).where(Bot.id == bot_id))
        bot = bot_result.scalar_one_or_none()
        if not bot:
            return

        bot.total_pnl += pnl
        bot.total_trades += 1

        if pnl < 0:
            bot.consecutive_losses += 1
            bot.daily_loss += abs(pnl)
        else:
            bot.consecutive_losses = 0

        if bot.total_trades > 0:
            winning = await self.db.execute(
                select(func.count()).where(Trade.bot_id == bot_id, Trade.pnl > 0)
            )
            bot.win_rate = winning.scalar() / bot.total_trades

        await self.db.flush()

    async def check_should_trailing_stop(self, trade: Trade, current_price: float) -> Optional[float]:
        if not trade.trailing_stop or not trade.entry_price:
            return None

        if trade.side == "BUY":
            distance = current_price - trade.entry_price
            if distance > 0:
                new_stop = current_price - (current_price * trade.trailing_stop)
                if new_stop > (trade.stop_loss or 0):
                    return new_stop
        else:
            distance = trade.entry_price - current_price
            if distance > 0:
                new_stop = current_price + (current_price * trade.trailing_stop)
                if trade.stop_loss is None or new_stop < trade.stop_loss:
                    return new_stop

        return None

    async def check_should_move_to_breakeven(self, trade: Trade, current_price: float) -> Optional[float]:
        if not trade.entry_price or trade.stop_loss is None:
            return None

        if trade.side == "BUY":
            profit_distance = current_price - trade.entry_price
            risk_distance = trade.entry_price - trade.stop_loss
            if profit_distance >= risk_distance and trade.stop_loss < trade.entry_price:
                return trade.entry_price
        else:
            profit_distance = trade.entry_price - current_price
            risk_distance = trade.stop_loss - trade.entry_price
            if profit_distance >= risk_distance and trade.stop_loss > trade.entry_price:
                return trade.entry_price

        return None

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        risk_percentage: float = 0.01,
        leverage: int = 1,
    ) -> dict:
        risk_amount = account_balance * risk_percentage
        stop_distance_pct = abs(entry_price - stop_loss) / entry_price

        if stop_distance_pct == 0:
            return {"quantity": 0, "notional": 0, "risk": 0}

        position_size = risk_amount / stop_distance_pct
        notional_value = position_size * entry_price
        max_notional = account_balance * leverage

        if notional_value > max_notional:
            position_size = max_notional / entry_price
            risk_amount = position_size * stop_distance_pct * entry_price

        return {
            "quantity": position_size,
            "notional_value": notional_value,
            "risk_amount": risk_amount,
            "stop_distance_pct": stop_distance_pct * 100,
        }

    def _calculate_drawdown(self, bot: Bot) -> float:
        if bot.total_pnl >= 0:
            return 0.0
        peak_equity = 10000
        current_equity = 10000 + bot.total_pnl
        return abs(bot.total_pnl) / peak_equity

    async def reset_daily_loss(self, bot_id: str) -> None:
        bot_result = await self.db.execute(select(Bot).where(Bot.id == bot_id))
        bot = bot_result.scalar_one_or_none()
        if bot:
            bot.daily_loss = 0.0
            await self.db.flush()
