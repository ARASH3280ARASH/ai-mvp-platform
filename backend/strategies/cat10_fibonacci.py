"""
Whilber-AI MVP - Strategy Cat 10: Fibonacci Retracement
==========================================================
Auto-detect major swing, check price at key fib levels.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


FIB_LEVELS = {
    "0.236": 0.236,
    "0.382": 0.382,
    "0.500": 0.500,
    "0.618": 0.618,
    "0.786": 0.786,
}

FIB_NAMES_FA = {
    "0.236": "۲۳.۶٪",
    "0.382": "۳۸.۲٪",
    "0.500": "۵۰٪",
    "0.618": "۶۱.۸٪ (طلایی)",
    "0.786": "۷۸.۶٪",
}


def find_major_swing(high: pd.Series, low: pd.Series,
                     lookback: int = 80) -> Dict:
    """Find the most significant swing high and low in recent data."""
    recent_h = high.iloc[-lookback:]
    recent_l = low.iloc[-lookback:]

    swing_high_idx = recent_h.idxmax()
    swing_low_idx = recent_l.idxmin()
    swing_high = recent_h.max()
    swing_low = recent_l.min()

    # Determine if upswing or downswing (which came first)
    high_pos = high.index.get_loc(swing_high_idx)
    low_pos = low.index.get_loc(swing_low_idx)

    if low_pos < high_pos:
        direction = "up"  # Low first, then high → upswing
    else:
        direction = "down"  # High first, then low → downswing

    return {
        "high": swing_high,
        "low": swing_low,
        "direction": direction,
        "range": swing_high - swing_low,
    }


def calc_fib_levels(swing: Dict) -> Dict[str, float]:
    """Calculate fib retracement levels."""
    h, l = swing["high"], swing["low"]
    rng = swing["range"]
    levels = {}

    if swing["direction"] == "up":
        # Retracing down from high
        for name, ratio in FIB_LEVELS.items():
            levels[name] = h - (rng * ratio)
    else:
        # Retracing up from low
        for name, ratio in FIB_LEVELS.items():
            levels[name] = l + (rng * ratio)

    return levels


def price_at_fib(price: float, levels: Dict[str, float],
                 tolerance_pct: float = 0.3) -> str:
    """Check if price is near any fib level. Returns level name or empty."""
    for name, level in levels.items():
        if abs(price - level) / level * 100 < tolerance_pct:
            return name
    return ""


class FibonacciStrategy(BaseStrategy):
    STRATEGY_ID = "fibonacci"
    STRATEGY_NAME_FA = "فیبوناچی"
    STRATEGY_NAME_EN = "Fibonacci Retracement"
    CATEGORY = "fibonacci"
    REQUIRED_INDICATORS = ["trend", "candle", "osc"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        h, l, c = df["high"], df["low"], df["close"]
        trend = indicators.get("trend", {})
        candle = indicators.get("candle", {})
        osc = indicators.get("osc", {})

        price = c.iloc[-1]
        regime = self.last(trend.get("regime"))

        if len(df) < 50:
            return self._neutral("داده کافی نیست")

        swing = find_major_swing(h, l, lookback=80)
        levels = calc_fib_levels(swing)
        at_fib = price_at_fib(price, levels, 0.3)

        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))
        rsi = self.last(osc.get("rsi_14"))

        if not at_fib:
            # Check if between key levels
            closest = None
            closest_dist = float('inf')
            for name, lvl in levels.items():
                dist = abs(price - lvl) / lvl * 100
                if dist < closest_dist:
                    closest_dist = dist
                    closest = name

            return self._neutral(
                f"قیمت روی سطح فیبو نیست | نزدیک‌ترین: {FIB_NAMES_FA.get(closest, closest)} ({closest_dist:.1f}%)",
                f"Price not at fib level, nearest: {closest} ({closest_dist:.1f}%)",
                {"fib_levels": {k: round(v, 5) for k, v in levels.items()},
                 "swing_dir": swing["direction"],
                 "nearest_fib": closest, "nearest_dist": round(closest_dist, 2)})

        confidence = 30
        signals = [f"قیمت روی سطح فیبو {FIB_NAMES_FA.get(at_fib, at_fib)}"]

        # Golden ratio = strongest
        if at_fib == "0.618":
            confidence += 15
            signals.append("سطح طلایی ۶۱.۸٪")
        elif at_fib == "0.500":
            confidence += 10
            signals.append("سطح ۵۰٪")
        elif at_fib == "0.382":
            confidence += 10

        # Candle confirmation
        if swing["direction"] == "up":
            # Upswing retracing down → look for bullish bounce
            if pin == 1 or engulf == 1:
                confidence += 20
                signals.append("تأیید کندلی صعودی")
            if rsi and rsi < 45:
                confidence += 10
                signals.append("RSI پایین")

            if confidence >= 40:
                return self._make_result(Signal.BUY, min(confidence, 85),
                    f"فیبوناچی صعودی: {' | '.join(signals)}",
                    f"Fib bounce at {at_fib} in upswing",
                    {"at_fib": at_fib, "fib_levels": {k: round(v, 5) for k, v in levels.items()},
                     "swing": swing["direction"]})
        else:
            # Downswing retracing up → look for bearish rejection
            if pin == -1 or engulf == -1:
                confidence += 20
                signals.append("تأیید کندلی نزولی")
            if rsi and rsi > 55:
                confidence += 10
                signals.append("RSI بالا")

            if confidence >= 40:
                return self._make_result(Signal.SELL, min(confidence, 85),
                    f"فیبوناچی نزولی: {' | '.join(signals)}",
                    f"Fib rejection at {at_fib} in downswing",
                    {"at_fib": at_fib, "fib_levels": {k: round(v, 5) for k, v in levels.items()},
                     "swing": swing["direction"]})

        return self._neutral(
            f"روی فیبو {FIB_NAMES_FA.get(at_fib, at_fib)} بدون تأیید کندلی",
            f"At fib {at_fib} without candle confirmation",
            {"at_fib": at_fib, "fib_levels": {k: round(v, 5) for k, v in levels.items()}})
