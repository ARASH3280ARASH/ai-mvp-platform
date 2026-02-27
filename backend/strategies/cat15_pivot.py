"""
Whilber-AI MVP - Strategy Cat 15: Pivot Points
=================================================
Classic, Fibonacci, Camarilla pivot levels.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def calc_classic_pivots(high: float, low: float, close: float) -> Dict[str, float]:
    """Classic pivot points from previous period H/L/C."""
    pp = (high + low + close) / 3
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)
    return {"PP": pp, "R1": r1, "R2": r2, "R3": r3, "S1": s1, "S2": s2, "S3": s3}


def calc_camarilla_pivots(high: float, low: float, close: float) -> Dict[str, float]:
    """Camarilla pivots (tight intraday levels)."""
    diff = high - low
    return {
        "C_R1": close + diff * 1.1 / 12,
        "C_R2": close + diff * 1.1 / 6,
        "C_R3": close + diff * 1.1 / 4,
        "C_R4": close + diff * 1.1 / 2,
        "C_S1": close - diff * 1.1 / 12,
        "C_S2": close - diff * 1.1 / 6,
        "C_S3": close - diff * 1.1 / 4,
        "C_S4": close - diff * 1.1 / 2,
    }


def get_previous_period(df: pd.DataFrame) -> Dict:
    """Get previous day's H/L/C from hourly or sub-hourly data."""
    # Use the data range to estimate daily candle
    # Simple: use last 24 bars for H1, or find max window
    if len(df) < 24:
        return {"high": df["high"].max(), "low": df["low"].min(), "close": df["close"].iloc[-2]}

    # Look at bars before last bar
    prev = df.iloc[-25:-1]
    return {
        "high": prev["high"].max(),
        "low": prev["low"].min(),
        "close": prev["close"].iloc[-1],
    }


class PivotPointStrategy(BaseStrategy):
    STRATEGY_ID = "pivot_points"
    STRATEGY_NAME_FA = "پیوت پوینت"
    STRATEGY_NAME_EN = "Pivot Points"
    CATEGORY = "pivot"
    REQUIRED_INDICATORS = ["candle", "osc"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        candle = indicators.get("candle", {})
        osc = indicators.get("osc", {})

        price = df["close"].iloc[-1]
        prev = get_previous_period(df)
        pivots = calc_classic_pivots(prev["high"], prev["low"], prev["close"])
        cam = calc_camarilla_pivots(prev["high"], prev["low"], prev["close"])

        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))
        rsi = self.last(osc.get("rsi_14"))

        pp = pivots["PP"]
        tolerance = abs(pivots["R1"] - pp) * 0.05  # 5% of R1-PP range

        confidence = 0
        signals = []

        # Price near support levels
        for level_name in ["S1", "S2", "S3"]:
            lvl = pivots[level_name]
            if abs(price - lvl) < tolerance:
                confidence += 25
                signals.append(f"قیمت روی حمایت {level_name} ({lvl:.5f})")

                if pin == 1 or engulf == 1:
                    confidence += 15
                    signals.append("تأیید کندلی")
                if rsi and rsi < 40:
                    confidence += 10

                if confidence >= 35:
                    return self._make_result(Signal.BUY, min(confidence, 80),
                        f"پیوت صعودی: {' | '.join(signals)}",
                        f"Pivot support bounce at {level_name}",
                        {"pivot": round(pp, 5), level_name: round(lvl, 5),
                         "all_pivots": {k: round(v, 5) for k, v in pivots.items()}})

        # Price near resistance levels
        for level_name in ["R1", "R2", "R3"]:
            lvl = pivots[level_name]
            if abs(price - lvl) < tolerance:
                confidence += 25
                signals.append(f"قیمت روی مقاومت {level_name} ({lvl:.5f})")

                if pin == -1 or engulf == -1:
                    confidence += 15
                    signals.append("تأیید کندلی")
                if rsi and rsi > 60:
                    confidence += 10

                if confidence >= 35:
                    return self._make_result(Signal.SELL, min(confidence, 80),
                        f"پیوت نزولی: {' | '.join(signals)}",
                        f"Pivot resistance at {level_name}",
                        {"pivot": round(pp, 5), level_name: round(lvl, 5),
                         "all_pivots": {k: round(v, 5) for k, v in pivots.items()}})

        # General position
        pos = "بالای PP" if price > pp else "زیر PP"
        return self._neutral(
            f"قیمت {pos} ({pp:.5f}) | بین سطوح پیوت",
            f"Price {'above' if price > pp else 'below'} PP",
            {"pivot": round(pp, 5),
             "all_pivots": {k: round(v, 5) for k, v in pivots.items()},
             "camarilla": {k: round(v, 5) for k, v in cam.items()}})
