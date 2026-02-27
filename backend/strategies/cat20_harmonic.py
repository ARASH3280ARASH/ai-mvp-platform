"""
Whilber-AI MVP - Strategy Cat 20: Harmonic Patterns
======================================================
Detect harmonic patterns via swing point fib ratios.
Simplified: ABCD + Gartley-like detection.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def _get_swings(high: pd.Series, low: pd.Series, left: int = 5, right: int = 3,
                count: int = 5) -> List[Dict]:
    """Get recent alternating swing highs and lows."""
    swings = []
    for i in range(left, len(high) - right):
        h_window = high.iloc[i-left:i+right+1]
        l_window = low.iloc[i-left:i+right+1]

        if high.iloc[i] == h_window.max():
            swings.append({"type": "high", "price": high.iloc[i], "idx": i})
        if low.iloc[i] == l_window.min():
            swings.append({"type": "low", "price": low.iloc[i], "idx": i})

    # Deduplicate: keep alternating
    if not swings:
        return []

    swings.sort(key=lambda x: x["idx"])
    filtered = [swings[0]]
    for s in swings[1:]:
        if s["type"] != filtered[-1]["type"]:
            filtered.append(s)

    return filtered[-count:]


def detect_abcd(swings: List[Dict], tolerance: float = 0.15) -> Optional[Dict]:
    """
    ABCD pattern: 4 swing points where:
    BC = 38.2%-78.6% of AB
    CD = 127.2%-161.8% of BC (or equal to AB)
    """
    if len(swings) < 4:
        return None

    a, b, c, d = [s["price"] for s in swings[-4:]]
    types = [s["type"] for s in swings[-4:]]

    ab = abs(b - a)
    bc = abs(c - b)
    cd = abs(d - c)

    if ab == 0 or bc == 0:
        return None

    bc_ratio = bc / ab
    cd_ratio = cd / bc

    # BC should retrace 38.2%-78.6% of AB
    if not (0.382 - tolerance <= bc_ratio <= 0.786 + tolerance):
        return None

    # CD should be 1.0-1.618x BC or close to AB
    ab_cd_ratio = cd / ab
    valid_cd = (1.0 - tolerance <= cd_ratio <= 1.618 + tolerance) or \
               (0.85 <= ab_cd_ratio <= 1.15)

    if not valid_cd:
        return None

    # Determine direction
    if types[-4] == "low":  # A=low → bullish ABCD
        direction = "bullish"
    else:
        direction = "bearish"

    return {
        "pattern": "ABCD",
        "direction": direction,
        "bc_ratio": bc_ratio,
        "cd_ratio": cd_ratio,
        "ab_cd_ratio": ab_cd_ratio,
        "a": a, "b": b, "c": c, "d": d,
    }


class HarmonicStrategy(BaseStrategy):
    STRATEGY_ID = "harmonic"
    STRATEGY_NAME_FA = "هارمونیک"
    STRATEGY_NAME_EN = "Harmonic Patterns"
    CATEGORY = "harmonic"
    REQUIRED_INDICATORS = ["osc", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        h, l, c = df["high"], df["low"], df["close"]
        osc = indicators.get("osc", {})
        candle = indicators.get("candle", {})

        price = c.iloc[-1]
        rsi = self.last(osc.get("rsi_14"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))

        if len(df) < 40:
            return self._neutral("داده کافی نیست")

        swings = _get_swings(h, l, left=5, right=3, count=6)
        abcd = detect_abcd(swings)

        if not abcd:
            return self._neutral(
                "الگوی هارمونیک یافت نشد",
                "No harmonic pattern",
                {"swings_found": len(swings)})

        confidence = 35
        signals = [f"الگوی {abcd['pattern']} {abcd['direction']}"]
        signals.append(f"BC={abcd['bc_ratio']:.2f} | CD/BC={abcd['cd_ratio']:.2f}")

        # Quality bonus
        if 0.55 <= abcd["bc_ratio"] <= 0.70:
            confidence += 10
            signals.append("نسبت BC ایده‌آل")

        if 0.90 <= abcd["ab_cd_ratio"] <= 1.10:
            confidence += 10
            signals.append("AB≈CD متقارن")

        if abcd["direction"] == "bullish":
            if pin == 1 or engulf == 1:
                confidence += 15
                signals.append("تأیید کندلی")
            if rsi and rsi < 40:
                confidence += 10

            if confidence >= 40:
                return self._make_result(Signal.BUY, min(confidence, 80),
                    f"هارمونیک صعودی: {' | '.join(signals)}",
                    f"Bullish ABCD: BC={abcd['bc_ratio']:.2f}",
                    {"pattern": abcd})

        elif abcd["direction"] == "bearish":
            if pin == -1 or engulf == -1:
                confidence += 15
                signals.append("تأیید کندلی")
            if rsi and rsi > 60:
                confidence += 10

            if confidence >= 40:
                return self._make_result(Signal.SELL, min(confidence, 80),
                    f"هارمونیک نزولی: {' | '.join(signals)}",
                    f"Bearish ABCD",
                    {"pattern": abcd})

        return self._neutral(
            f"الگوی ABCD یافت شد اما تأیید ضعیف",
            "ABCD found but weak confirmation",
            {"pattern": abcd})
