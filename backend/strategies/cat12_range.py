"""
Whilber-AI MVP - Strategy Cat 12: Range / Channel Trading
============================================================
Detect ranging market and trade bounces off boundaries.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def detect_range(high: pd.Series, low: pd.Series, close: pd.Series,
                 lookback: int = 50, threshold_pct: float = 2.0) -> Dict:
    """
    Detect if market is in a range (channel).
    Returns range boundaries and whether currently ranging.
    """
    recent_h = high.iloc[-lookback:]
    recent_l = low.iloc[-lookback:]
    recent_c = close.iloc[-lookback:]

    range_high = recent_h.max()
    range_low = recent_l.min()
    range_size = (range_high - range_low) / range_low * 100

    # Check if price has been contained
    mid = (range_high + range_low) / 2
    above_mid = (recent_c > mid).sum()
    below_mid = (recent_c <= mid).sum()
    balance = min(above_mid, below_mid) / max(above_mid, below_mid, 1)

    # Count touches near boundaries
    touch_zone = (range_high - range_low) * 0.1
    high_touches = (recent_h > range_high - touch_zone).sum()
    low_touches = (recent_l < range_low + touch_zone).sum()

    is_range = (
        range_size < threshold_pct * 3 and
        balance > 0.3 and
        high_touches >= 2 and
        low_touches >= 2
    )

    return {
        "is_range": is_range,
        "range_high": range_high,
        "range_low": range_low,
        "range_mid": mid,
        "range_size_pct": range_size,
        "balance": balance,
        "high_touches": high_touches,
        "low_touches": low_touches,
    }


class RangeTrading(BaseStrategy):
    STRATEGY_ID = "range_trading"
    STRATEGY_NAME_FA = "معامله رنج"
    STRATEGY_NAME_EN = "Range Trading"
    CATEGORY = "range"
    REQUIRED_INDICATORS = ["trend", "osc", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        h, l, c = df["high"], df["low"], df["close"]
        trend = indicators.get("trend", {})
        osc = indicators.get("osc", {})
        candle = indicators.get("candle", {})

        adx = self.last(trend.get("adx"))
        rsi = self.last(osc.get("rsi_14"))
        stoch_k = self.last(osc.get("stoch_k"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))

        price = c.iloc[-1]

        rng = detect_range(h, l, c, lookback=50)

        if not rng["is_range"]:
            return self._neutral(
                f"بازار در رنج نیست (اندازه: {rng['range_size_pct']:.1f}%)",
                "Market not ranging",
                {"range_size_pct": round(rng["range_size_pct"], 2)})

        range_h = rng["range_high"]
        range_l = rng["range_low"]
        range_size = range_h - range_l
        proximity = range_size * 0.1  # 10% of range

        confidence = 0
        signals = [f"بازار در رنج ({rng['range_size_pct']:.1f}%)"]

        # ADX low = ranging confirmed
        if adx and adx < 25:
            confidence += 15
            signals.append(f"ADX پایین ({adx:.0f})")

        # Near bottom of range → BUY
        if price <= range_l + proximity:
            confidence += 30
            signals.append("قیمت نزدیک کف رنج")

            if rsi and rsi < 35:
                confidence += 10
                signals.append("RSI اشباع فروش")
            if stoch_k and stoch_k < 20:
                confidence += 10
            if pin == 1 or engulf == 1:
                confidence += 15
                signals.append("تأیید کندلی")

            if confidence >= 40:
                return self._make_result(Signal.BUY, min(confidence, 80),
                    f"خرید کف رنج: {' | '.join(signals)}",
                    f"Buy at range bottom: {range_l:.5f}",
                    {"range_high": round(range_h, 5), "range_low": round(range_l, 5),
                     "price_position": "bottom"})

        # Near top of range → SELL
        if price >= range_h - proximity:
            confidence = 30 if adx and adx < 25 else 15
            signals_s = [f"بازار در رنج | قیمت نزدیک سقف رنج"]

            if rsi and rsi > 65:
                confidence += 10
                signals_s.append("RSI اشباع خرید")
            if stoch_k and stoch_k > 80:
                confidence += 10
            if pin == -1 or engulf == -1:
                confidence += 15
                signals_s.append("تأیید کندلی")
            if adx and adx < 25:
                confidence += 15

            if confidence >= 40:
                return self._make_result(Signal.SELL, min(confidence, 80),
                    f"فروش سقف رنج: {' | '.join(signals_s)}",
                    f"Sell at range top: {range_h:.5f}",
                    {"range_high": round(range_h, 5), "range_low": round(range_l, 5),
                     "price_position": "top"})

        return self._neutral(
            f"رنج فعال اما قیمت در میانه ({range_l:.5f} ~ {range_h:.5f})",
            "Ranging but price in middle",
            {"range_high": round(range_h, 5), "range_low": round(range_l, 5),
             "is_range": True})
