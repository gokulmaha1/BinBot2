from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bot, Trade


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_analytics(self, user_id: str, days: int = 30) -> dict:
        bots_result = await self.db.execute(select(Bot).where(Bot.user_id == user_id))
        bots = bots_result.scalars().all()
        bot_ids = [str(bot.id) for bot in bots]

        if not bot_ids:
            return self._empty_analytics()

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        trades_result = await self.db.execute(
            select(Trade).where(Trade.bot_id.in_(bot_ids), Trade.entry_timestamp >= cutoff)
        )
        trades = trades_result.scalars().all()

        all_trades_result = await self.db.execute(
            select(Trade).where(Trade.bot_id.in_(bot_ids))
        )
        all_trades = all_trades_result.scalars().all()

        closed_trades = [t for t in all_trades if t.status == "closed"]
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]

        total_pnl = sum(t.pnl for t in closed_trades)
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        returns = [t.pnl_percentage for t in closed_trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0

        max_drawdown = self._calculate_max_drawdown(closed_trades)

        daily_pnl = self._calculate_daily_pnl(closed_trades, days)

        active_positions = [t for t in trades if t.status == "open"]

        return {
            "total_pnl": total_pnl,
            "daily_pnl": daily_pnl,
            "win_rate": win_rate,
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "profit_factor": profit_factor,
            "avg_win": gross_profit / len(winning_trades) if winning_trades else 0,
            "avg_loss": gross_loss / len(losing_trades) if losing_trades else 0,
            "largest_win": max((t.pnl for t in winning_trades), default=0),
            "largest_loss": min((t.pnl for t in losing_trades), default=0),
            "active_positions": active_positions,
            "trade_history": sorted(closed_trades, key=lambda x: x.entry_timestamp, reverse=True)[:50],
        }

    async def get_bot_analytics(self, bot_id: str, days: int = 30) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        trades_result = await self.db.execute(
            select(Trade).where(Trade.bot_id == bot_id, Trade.entry_timestamp >= cutoff)
        )
        trades = trades_result.scalars().all()

        closed_trades = [t for t in trades if t.status == "closed"]
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]

        total_pnl = sum(t.pnl for t in closed_trades)
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        returns = [t.pnl_percentage for t in closed_trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0

        daily_pnl = self._calculate_daily_pnl(closed_trades, days)

        return {
            "total_pnl": total_pnl,
            "daily_pnl": daily_pnl,
            "win_rate": win_rate,
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "avg_win": gross_profit / len(winning_trades) if winning_trades else 0,
            "avg_loss": gross_loss / len(losing_trades) if losing_trades else 0,
        }

    def _calculate_daily_pnl(self, trades: list, days: int) -> list:
        daily = {}
        for trade in trades:
            day = trade.entry_timestamp.strftime("%Y-%m-%d")
            daily[day] = daily.get(day, 0) + trade.pnl

        result = []
        for i in range(days):
            day = (datetime.now(timezone.utc) - timedelta(days=days-1-i)).strftime("%Y-%m-%d")
            result.append({"date": day, "pnl": daily.get(day, 0)})
        return result

    def _calculate_max_drawdown(self, trades: list) -> float:
        if not trades:
            return 0
        equity = 0
        peak = 0
        max_dd = 0
        for trade in sorted(trades, key=lambda x: x.entry_timestamp):
            equity += trade.pnl
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def _empty_analytics(self) -> dict:
        return {
            "total_pnl": 0,
            "daily_pnl": [],
            "win_rate": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "max_drawdown": 0,
            "sharpe_ratio": 0,
            "profit_factor": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "largest_win": 0,
            "largest_loss": 0,
            "active_positions": [],
            "trade_history": [],
        }
