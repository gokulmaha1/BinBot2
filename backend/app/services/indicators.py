import numpy as np
import pandas as pd
from typing import Optional


class TechnicalIndicators:
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        return data.rolling(window=period).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        delta = data.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> dict:
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return {"upper": upper, "middle": sma, "lower": lower}

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1/period, min_periods=period).mean()

    @staticmethod
    def stochastic_rsi(close: pd.Series, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> dict:
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        lowest_rsi = rsi.rolling(window=period).min()
        highest_rsi = rsi.rolling(window=period).max()
        k = 100 * (rsi - lowest_rsi) / (highest_rsi - lowest_rsi)
        d = k.rolling(window=smooth_d).mean()
        return {"k": k, "d": d}

    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0) -> dict:
        atr = TechnicalIndicators.atr(high, low, close, period)
        hl2 = (high + low) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        trend = pd.Series(index=close.index, dtype=object)
        final_upper = pd.Series(index=close.index, dtype=float)
        final_lower = pd.Series(index=close.index, dtype=float)

        final_upper.iloc[0] = upper_band.iloc[0]
        final_lower.iloc[0] = lower_band.iloc[0]
        trend.iloc[0] = "BUY"

        for i in range(1, len(close)):
            final_upper.iloc[i] = upper_band.iloc[i] if upper_band.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1] else final_upper.iloc[i-1]
            final_lower.iloc[i] = lower_band.iloc[i] if lower_band.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1] else final_lower.iloc[i-1]
            trend.iloc[i] = "BUY" if close.iloc[i] > final_upper.iloc[i-1] else "SELL" if close.iloc[i] < final_lower.iloc[i-1] else trend.iloc[i-1]

        return {"trend": trend, "upper": final_upper, "lower": final_lower}

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        tp = (high + low + close) / 3
        return (tp * volume).cumsum() / volume.cumsum()

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        direction = close.diff().apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
        return (direction * volume).cumsum()

    @staticmethod
    def detect_support_resistance(close: pd.Series, window: int = 20) -> dict:
        highs = close.rolling(window=window, center=True).max()
        lows = close.rolling(window=window, center=True).min()
        resistance_levels = []
        support_levels = []
        for i in range(window, len(close) - window):
            if close.iloc[i] == highs.iloc[i]:
                resistance_levels.append((i, close.iloc[i]))
            if close.iloc[i] == lows.iloc[i]:
                support_levels.append((i, close.iloc[i]))
        return {"resistance": resistance_levels[-5:], "support": support_levels[-5:]}

    @staticmethod
    def detect_swings(high: pd.Series, low: pd.Series, window: int = 5) -> dict:
        swing_highs = []
        swing_lows = []
        for i in range(window, len(high) - window):
            if all(high.iloc[i] >= high.iloc[i-j] for j in range(1, window+1)) and \
               all(high.iloc[i] >= high.iloc[i+j] for j in range(1, window+1)):
                swing_highs.append((i, high.iloc[i]))
            if all(low.iloc[i] <= low.iloc[i-j] for j in range(1, window+1)) and \
               all(low.iloc[i] <= low.iloc[i+j] for j in range(1, window+1)):
                swing_lows.append((i, low.iloc[i]))
        return {"swing_highs": swing_highs[-10:], "swing_lows": swing_lows[-10:]}

    @staticmethod
    def detect_break_of_structure(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> str:
        recent_high = high.rolling(window=window).max().iloc[-1]
        recent_low = low.rolling(window=window).min().iloc[-1]
        current = close.iloc[-1]
        if current > recent_high:
            return "bullish_bos"
        elif current < recent_low:
            return "bearish_bos"
        return "none"

    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ema_9"] = TechnicalIndicators.ema(df["close"], 9)
        df["ema_21"] = TechnicalIndicators.ema(df["close"], 21)
        df["ema_50"] = TechnicalIndicators.ema(df["close"], 50)
        df["ema_200"] = TechnicalIndicators.ema(df["close"], 200)
        df["rsi_14"] = TechnicalIndicators.rsi(df["close"], 14)
        macd = TechnicalIndicators.macd(df["close"])
        df["macd"] = macd["macd"]
        df["macd_signal"] = macd["signal"]
        df["macd_hist"] = macd["histogram"]
        bb = TechnicalIndicators.bollinger_bands(df["close"])
        df["bb_upper"] = bb["upper"]
        df["bb_middle"] = bb["middle"]
        df["bb_lower"] = bb["lower"]
        df["bb_width"] = (bb["upper"] - bb["lower"]) / bb["middle"]
        df["atr_14"] = TechnicalIndicators.atr(df["high"], df["low"], df["close"], 14)
        stoch = TechnicalIndicators.stochastic_rsi(df["close"])
        df["stoch_k"] = stoch["k"]
        df["stoch_d"] = stoch["d"]
        st = TechnicalIndicators.supertrend(df["high"], df["low"], df["close"])
        df["supertrend"] = st["trend"]
        df["supertrend_upper"] = st["upper"]
        df["supertrend_lower"] = st["lower"]
        df["vwap"] = TechnicalIndicators.vwap(df["high"], df["low"], df["close"], df["volume"])
        df["obv"] = TechnicalIndicators.obv(df["close"], df["volume"])
        df["sma_20"] = TechnicalIndicators.sma(df["close"], 20)
        df["sma_50"] = TechnicalIndicators.sma(df["close"], 50)
        return df.dropna()
