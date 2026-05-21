from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import numpy as np


class Signal:
    def __init__(self, side: Optional[str], confidence: float, entry_price: float, stop_loss: float, take_profit: float, reason: str):
        self.side = side
        self.confidence = confidence
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.reason = reason


class BaseStrategy(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, current_price: float, config: dict) -> Signal:
        pass


class TrendFollowingStrategy(BaseStrategy):
    name = "trend_following"
    description = "Follows EMA crossovers with Supertrend confirmation"

    def generate_signal(self, df: pd.DataFrame, current_price: float, config: dict) -> Signal:
        if len(df) < 50:
            return Signal(None, 0, current_price, 0, 0, "Insufficient data")

        ema_fast = df["ema_9"].iloc[-1]
        ema_slow = df["ema_21"].iloc[-1]
        ema_trend = df["ema_50"].iloc[-1]
        supertrend = df["supertrend"].iloc[-1]
        atr = df["atr_14"].iloc[-1]
        rsi = df["rsi_14"].iloc[-1]

        atr_multiplier = config.get("atr_multiplier", 2.0)
        tp_multiplier = config.get("tp_multiplier", 3.0)

        if ema_fast > ema_slow and ema_fast > ema_trend and supertrend == "BUY" and rsi < 70:
            stop_loss = current_price - (atr * atr_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
            confidence = min(0.9, (ema_fast - ema_slow) / current_price * 100 + 0.5)
            return Signal("BUY", confidence, current_price, stop_loss, take_profit, "Trend following bullish")

        if ema_fast < ema_slow and ema_fast < ema_trend and supertrend == "SELL" and rsi > 30:
            stop_loss = current_price + (atr * atr_multiplier)
            take_profit = current_price - (atr * tp_multiplier)
            confidence = min(0.9, (ema_slow - ema_fast) / current_price * 100 + 0.5)
            return Signal("SELL", confidence, current_price, stop_loss, take_profit, "Trend following bearish")

        return Signal(None, 0, current_price, 0, 0, "No trend signal")


class MeanReversionStrategy(BaseStrategy):
    name = "mean_reversion"
    description = "Trades bounces off Bollinger Bands with RSI confirmation"

    def generate_signal(self, df: pd.DataFrame, current_price: float, config: dict) -> Signal:
        if len(df) < 30:
            return Signal(None, 0, current_price, 0, 0, "Insufficient data")

        bb_upper = df["bb_upper"].iloc[-1]
        bb_lower = df["bb_lower"].iloc[-1]
        bb_middle = df["bb_middle"].iloc[-1]
        rsi = df["rsi_14"].iloc[-1]
        atr = df["atr_14"].iloc[-1]
        stoch_k = df["stoch_k"].iloc[-1]
        stoch_d = df["stoch_d"].iloc[-1]

        atr_multiplier = config.get("atr_multiplier", 1.5)
        tp_multiplier = config.get("tp_multiplier", 2.5)

        if current_price <= bb_lower and rsi < 30 and stoch_k < 20:
            stop_loss = current_price - (atr * atr_multiplier)
            take_profit = bb_middle
            confidence = min(0.85, (30 - rsi) / 30 * 0.5 + 0.3)
            return Signal("BUY", confidence, current_price, stop_loss, take_profit, "Mean reversion bullish")

        if current_price >= bb_upper and rsi > 70 and stoch_k > 80:
            stop_loss = current_price + (atr * atr_multiplier)
            take_profit = bb_middle
            confidence = min(0.85, (rsi - 70) / 30 * 0.5 + 0.3)
            return Signal("SELL", confidence, current_price, stop_loss, take_profit, "Mean reversion bearish")

        return Signal(None, 0, current_price, 0, 0, "No mean reversion signal")


class MomentumBreakoutStrategy(BaseStrategy):
    name = "momentum_breakout"
    description = "Trades breakouts from consolidation with volume confirmation"

    def generate_signal(self, df: pd.DataFrame, current_price: float, config: dict) -> Signal:
        if len(df) < 40:
            return Signal(None, 0, current_price, 0, 0, "Insufficient data")

        high_20 = df["high"].rolling(20).max().iloc[-1]
        low_20 = df["low"].rolling(20).min().iloc[-1]
        atr = df["atr_14"].iloc[-1]
        volume = df["volume"].iloc[-1]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]
        rsi = df["rsi_14"].iloc[-1]
        ema_9 = df["ema_9"].iloc[-1]
        ema_21 = df["ema_21"].iloc[-1]

        atr_multiplier = config.get("atr_multiplier", 1.5)
        tp_multiplier = config.get("tp_multiplier", 3.0)
        volume_threshold = config.get("volume_threshold", 1.5)

        volume_ratio = volume / avg_volume if avg_volume > 0 else 0

        if current_price > high_20 and volume_ratio > volume_threshold and rsi > 50 and ema_9 > ema_21:
            stop_loss = current_price - (atr * atr_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
            confidence = min(0.85, volume_ratio / 3 * 0.4 + 0.4)
            return Signal("BUY", confidence, current_price, stop_loss, take_profit, "Momentum breakout bullish")

        if current_price < low_20 and volume_ratio > volume_threshold and rsi < 50 and ema_9 < ema_21:
            stop_loss = current_price + (atr * atr_multiplier)
            take_profit = current_price - (atr * tp_multiplier)
            confidence = min(0.85, volume_ratio / 3 * 0.4 + 0.4)
            return Signal("SELL", confidence, current_price, stop_loss, take_profit, "Momentum breakout bearish")

        return Signal(None, 0, current_price, 0, 0, "No breakout signal")


class ScalpingStrategy(BaseStrategy):
    name = "scalping"
    description = "Quick trades using Stochastic RSI and short-term EMAs"

    def generate_signal(self, df: pd.DataFrame, current_price: float, config: dict) -> Signal:
        if len(df) < 30:
            return Signal(None, 0, current_price, 0, 0, "Insufficient data")

        stoch_k = df["stoch_k"].iloc[-1]
        stoch_d = df["stoch_d"].iloc[-1]
        stoch_k_prev = df["stoch_k"].iloc[-2]
        stoch_d_prev = df["stoch_d"].iloc[-2]
        ema_9 = df["ema_9"].iloc[-1]
        ema_21 = df["ema_21"].iloc[-1]
        atr = df["atr_14"].iloc[-1]
        rsi = df["rsi_14"].iloc[-1]

        atr_multiplier = config.get("atr_multiplier", 1.0)
        tp_multiplier = config.get("tp_multiplier", 1.5)

        if stoch_k_prev < stoch_d_prev and stoch_k > stoch_d and stoch_k < 30 and ema_9 > ema_21:
            stop_loss = current_price - (atr * atr_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
            confidence = 0.65
            return Signal("BUY", confidence, current_price, stop_loss, take_profit, "Scalp bullish")

        if stoch_k_prev > stoch_d_prev and stoch_k < stoch_d and stoch_k > 70 and ema_9 < ema_21:
            stop_loss = current_price + (atr * atr_multiplier)
            take_profit = current_price - (atr * tp_multiplier)
            confidence = 0.65
            return Signal("SELL", confidence, current_price, stop_loss, take_profit, "Scalp bearish")

        return Signal(None, 0, current_price, 0, 0, "No scalp signal")


class VolatilityExpansionStrategy(BaseStrategy):
    name = "volatility_expansion"
    description = "Trades volatility expansion after contraction periods"

    def generate_signal(self, df: pd.DataFrame, current_price: float, config: dict) -> Signal:
        if len(df) < 50:
            return Signal(None, 0, current_price, 0, 0, "Insufficient data")

        bb_width = df["bb_width"].iloc[-1]
        bb_width_avg = df["bb_width"].rolling(50).mean().iloc[-1]
        bb_width_prev = df["bb_width"].iloc[-2]
        atr = df["atr_14"].iloc[-1]
        atr_avg = df["atr_14"].rolling(50).mean().iloc[-1]
        rsi = df["rsi_14"].iloc[-1]
        macd_hist = df["macd_hist"].iloc[-1]
        macd_hist_prev = df["macd_hist"].iloc[-2]

        atr_multiplier = config.get("atr_multiplier", 2.0)
        tp_multiplier = config.get("tp_multiplier", 3.0)
        contraction_threshold = config.get("contraction_threshold", 0.6)

        is_contracting = bb_width < bb_width_avg * contraction_threshold
        is_expanding = bb_width > bb_width_prev and bb_width > bb_width_avg * 0.8

        if is_contracting and is_expanding and macd_hist > macd_hist_prev and rsi > 50:
            stop_loss = current_price - (atr * atr_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
            confidence = min(0.8, (bb_width / bb_width_avg) * 0.3 + 0.4)
            return Signal("BUY", confidence, current_price, stop_loss, take_profit, "Volatility expansion bullish")

        if is_contracting and is_expanding and macd_hist < macd_hist_prev and rsi < 50:
            stop_loss = current_price + (atr * atr_multiplier)
            take_profit = current_price - (atr * tp_multiplier)
            confidence = min(0.8, (bb_width / bb_width_avg) * 0.3 + 0.4)
            return Signal("SELL", confidence, current_price, stop_loss, take_profit, "Volatility expansion bearish")

        return Signal(None, 0, current_price, 0, 0, "No volatility signal")


class MultiTimeframeStrategy(BaseStrategy):
    name = "multi_timeframe"
    description = "Confirms signals across multiple timeframes"

    def generate_signal(self, df: pd.DataFrame, current_price: float, config: dict) -> Signal:
        if len(df) < 50:
            return Signal(None, 0, current_price, 0, 0, "Insufficient data")

        ema_9 = df["ema_9"].iloc[-1]
        ema_21 = df["ema_21"].iloc[-1]
        ema_50 = df["ema_50"].iloc[-1]
        supertrend = df["supertrend"].iloc[-1]
        rsi = df["rsi_14"].iloc[-1]
        macd_hist = df["macd_hist"].iloc[-1]
        atr = df["atr_14"].iloc[-1]

        atr_multiplier = config.get("atr_multiplier", 2.0)
        tp_multiplier = config.get("tp_multiplier", 3.0)

        bullish_signals = 0
        bearish_signals = 0

        if ema_9 > ema_21:
            bullish_signals += 1
        else:
            bearish_signals += 1

        if ema_21 > ema_50:
            bullish_signals += 1
        else:
            bearish_signals += 1

        if supertrend == "BUY":
            bullish_signals += 1
        else:
            bearish_signals += 1

        if rsi > 50:
            bullish_signals += 1
        else:
            bearish_signals += 1

        if macd_hist > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1

        total = bullish_signals + bearish_signals
        bullish_ratio = bullish_signals / total if total > 0 else 0.5

        if bullish_ratio >= 0.8:
            stop_loss = current_price - (atr * atr_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
            return Signal("BUY", bullish_ratio, current_price, stop_loss, take_profit, "Multi-timeframe bullish")

        if bullish_ratio <= 0.2:
            stop_loss = current_price + (atr * atr_multiplier)
            take_profit = current_price - (atr * tp_multiplier)
            return Signal("SELL", 1 - bullish_ratio, current_price, stop_loss, take_profit, "Multi-timeframe bearish")

        return Signal(None, 0, current_price, 0, 0, "No MTF signal")


STRATEGIES = {
    "trend_following": TrendFollowingStrategy(),
    "mean_reversion": MeanReversionStrategy(),
    "momentum_breakout": MomentumBreakoutStrategy(),
    "scalping": ScalpingStrategy(),
    "volatility_expansion": VolatilityExpansionStrategy(),
    "multi_timeframe": MultiTimeframeStrategy(),
}


def get_strategy(name: str) -> BaseStrategy:
    strategy = STRATEGIES.get(name)
    if not strategy:
        raise ValueError(f"Strategy '{name}' not found. Available: {list(STRATEGIES.keys())}")
    return strategy
