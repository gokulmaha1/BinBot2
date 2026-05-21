import uuid
from datetime import datetime
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Backtest
from app.services.strategy_engine import get_strategy
from app.services.indicators import TechnicalIndicators
from app.services.market_detector import MarketConditionDetector
from app.ml.predictor import ml_predictor


class BacktestEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_backtest(
        self,
        user_id: str,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
        klines: list,
        config: dict = {},
    ) -> dict:
        df = self._klines_to_dataframe(klines)
        if df is None or len(df) < 50:
            return {"error": "Insufficient data for backtest"}

        df = TechnicalIndicators.calculate_all_indicators(df)

        strategy = get_strategy(strategy_name)

        capital = initial_capital
        position = None
        trades = []
        equity_curve = []
        max_drawdown = 0
        peak_equity = capital

        for i in range(50, len(df)):
            current_df = df.iloc[:i+1]
            current_price = df["close"].iloc[i]
            market_condition = MarketConditionDetector.detect(current_df)

            signal = strategy.generate_signal(current_df, current_price, config)

            if position is None and signal.side is not None:
                risk_amount = capital * 0.01
                stop_distance = abs(current_price - signal.stop_loss) / current_price
                if stop_distance > 0:
                    position_size = risk_amount / stop_distance
                    notional = position_size * current_price
                    if notional > capital * 5:
                        position_size = (capital * 5) / current_price

                    position = {
                        "side": signal.side,
                        "entry_price": current_price,
                        "quantity": position_size,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                        "entry_index": i,
                        "entry_time": df.index[i],
                    }

            elif position is not None:
                should_close = False
                exit_reason = ""
                exit_price = current_price

                if position["side"] == "BUY":
                    if current_price <= position["stop_loss"]:
                        should_close = True
                        exit_reason = "stop_loss"
                    elif current_price >= position["take_profit"]:
                        should_close = True
                        exit_reason = "take_profit"
                    elif i - position["entry_index"] > 100:
                        should_close = True
                        exit_reason = "timeout"
                else:
                    if current_price >= position["stop_loss"]:
                        should_close = True
                        exit_reason = "stop_loss"
                    elif current_price <= position["take_profit"]:
                        should_close = True
                        exit_reason = "take_profit"
                    elif i - position["entry_index"] > 100:
                        should_close = True
                        exit_reason = "timeout"

                if should_close:
                    if position["side"] == "BUY":
                        pnl = (exit_price - position["entry_price"]) * position["quantity"]
                    else:
                        pnl = (position["entry_price"] - exit_price) * position["quantity"]

                    capital += pnl
                    trades.append({
                        "side": position["side"],
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "quantity": position["quantity"],
                        "pnl": pnl,
                        "pnl_pct": (pnl / (position["entry_price"] * position["quantity"])) * 100,
                        "exit_reason": exit_reason,
                        "entry_time": str(position["entry_time"]),
                        "exit_time": str(df.index[i]),
                    })
                    position = None

            equity_curve.append({"timestamp": str(df.index[i]), "equity": capital})
            if capital > peak_equity:
                peak_equity = capital
            drawdown = (peak_equity - capital) / peak_equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        total_trades = len(trades)
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] <= 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        total_pnl = capital - initial_capital
        total_return_pct = (total_pnl / initial_capital) * 100

        gross_profit = sum(t["pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["pnl"] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0

        returns = [t["pnl_pct"] for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0

        result = {
            "initial_capital": initial_capital,
            "final_capital": capital,
            "total_pnl": total_pnl,
            "total_return_pct": total_return_pct,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": max((t["pnl"] for t in trades), default=0),
            "largest_loss": min((t["pnl"] for t in trades), default=0),
            "trades": trades[:100],
            "equity_curve": equity_curve[::10],
        }

        backtest = Backtest(
            id=uuid.uuid4(),
            user_id=user_id,
            strategy=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            result=result,
            status="completed",
        )
        self.db.add(backtest)
        await self.db.flush()

        return {
            "backtest_id": str(backtest.id),
            **result,
        }

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
