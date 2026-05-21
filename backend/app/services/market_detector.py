import pandas as pd
import numpy as np


class MarketConditionDetector:
    @staticmethod
    def detect(df: pd.DataFrame) -> dict:
        if len(df) < 50:
            return {"condition": "unknown", "confidence": 0}

        atr = df["atr_14"].iloc[-1]
        atr_avg = df["atr_14"].rolling(50).mean().iloc[-1]
        bb_width = df["bb_width"].iloc[-1]
        bb_width_avg = df["bb_width"].rolling(50).mean().iloc[-1]
        rsi = df["rsi_14"].iloc[-1]
        ema_9 = df["ema_9"].iloc[-1]
        ema_50 = df["ema_50"].iloc[-1]
        current_price = df["close"].iloc[-1]

        atr_ratio = atr / atr_avg if atr_avg > 0 else 1
        bb_ratio = bb_width / bb_width_avg if bb_width_avg > 0 else 1

        volatility = "high" if atr_ratio > 1.3 or bb_ratio > 1.3 else "low" if atr_ratio < 0.7 or bb_ratio < 0.7 else "normal"

        ema_distance = abs(ema_9 - ema_50) / current_price * 100
        is_trending = ema_distance > 1.0

        rsi_range = df["rsi_14"].rolling(20).max().iloc[-1] - df["rsi_14"].rolling(20).min().iloc[-1]
        is_ranging = rsi_range < 40 and not is_trending

        if is_trending and ema_9 > ema_50:
            trend = "uptrend"
        elif is_trending and ema_9 < ema_50:
            trend = "downtrend"
        elif is_ranging:
            trend = "ranging"
        else:
            trend = "weak_trend"

        if is_trending:
            condition = "trending"
        elif is_ranging:
            condition = "ranging"
        else:
            condition = "transitional"

        return {
            "condition": condition,
            "trend": trend,
            "volatility": volatility,
            "atr_ratio": atr_ratio,
            "bb_ratio": bb_ratio,
            "rsi": rsi,
            "confidence": min(1.0, ema_distance / 2 + 0.3),
        }
