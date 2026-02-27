"""
Whilber-AI MVP - Strategy Cat 19: Gap Trading
================================================
Detect gaps and trade gap-fill or gap-continuation.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def detect_gap(df: pd.DataFrame, min_gap_atr: float = 0.5) -> Dict:
    """Detect gap between previous close and current open."""
    if len(df) < 15:
        return {"has_gap": False}

    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    atr = (h - l).rolling(14).mean()
    avg_atr = atr.iloc[-2]
    if pd.isna(avg_atr) or avg_atr == 0:
        return {"has_gap": False}

    prev_close = c.iloc[-2]
    curr_open = o.iloc[-1]
    gap = curr_open - prev_close
    gap_pct = abs(gap) / prev_close * 100
    gap_atr = abs(gap) / avg_atr

    if gap_atr < min_gap_atr:
        return {"has_gap": False}

    curr_close = c.iloc[-1]
    filled = False
    if gap > 0:  # Gap up
        filled = curr_close <= prev_close
    else:  # Gap down
        filled = curr_close >= prev_close

    filling = False
    if gap > 0 and not filled:
        filling = curr_close < curr_open  # Moving back toward fill
    elif gap < 0 and not filled:
        filling = curr_close > curr_open

    return {
        "has_gap": True,
        "direction": "up" if gap > 0 else "down",
        "gap_size": gap,
        "gap_pct": gap_pct,
        "gap_atr": gap_atr,
        "prev_close": prev_close,
        "curr_open": curr_open,
        "filled": filled,
        "filling": filling,
    }


class GapTrading(BaseStrategy):
    STRATEGY_ID = "gap_trading"
    STRATEGY_NAME_FA = "معامله گپ"
    STRATEGY_NAME_EN = "Gap Trading"
    CATEGORY = "gap"
    REQUIRED_INDICATORS = ["trend", "volume"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        trend = indicators.get("trend", {})
        volume = indicators.get("volume", {})

        price = df["close"].iloc[-1]
        regime = self.last(trend.get("regime"))
        spike = self.last(volume.get("vol_spike"))

        gap = detect_gap(df)

        if not gap["has_gap"]:
            return self._neutral("گپ قیمتی وجود ندارد")

        confidence = 0
        signals = []
        dir_fa = "بالا" if gap["direction"] == "up" else "پایین"
        signals.append(f"گپ {dir_fa} ({gap['gap_pct']:.2f}%، {gap['gap_atr']:.1f}x ATR)")

        if gap["filled"]:
            return self._neutral(
                f"گپ {dir_fa} پر شده | {gap['gap_pct']:.2f}%",
                "Gap already filled",
                {"gap": gap})

        # Gap fill strategy (fade the gap)
        if gap["filling"]:
            confidence += 25
            signals.append("در حال پر شدن")

        if gap["direction"] == "up" and gap["filling"]:
            # Gap up, price coming back down → sell to fill
            confidence += 20
            if gap["gap_atr"] > 1.0:
                confidence += 10
                signals.append("گپ بزرگ")
            if regime != 1:
                confidence += 10

            if confidence >= 40:
                return self._make_result(Signal.SELL, min(confidence, 75),
                    f"پر شدن گپ بالا: {' | '.join(signals)}",
                    f"Gap up fill: {gap['gap_pct']:.2f}%",
                    {"gap_direction": "up", "target": round(gap["prev_close"], 5)})

        elif gap["direction"] == "down" and gap["filling"]:
            confidence += 20
            if gap["gap_atr"] > 1.0:
                confidence += 10
            if regime != -1:
                confidence += 10

            if confidence >= 40:
                return self._make_result(Signal.BUY, min(confidence, 75),
                    f"پر شدن گپ پایین: {' | '.join(signals)}",
                    f"Gap down fill: {gap['gap_pct']:.2f}%",
                    {"gap_direction": "down", "target": round(gap["prev_close"], 5)})

        # Gap continuation (trend follows gap)
        if gap["direction"] == "up" and not gap["filling"]:
            if spike == 1 and regime == 1:
                return self._make_result(Signal.BUY, 50,
                    f"ادامه گپ صعودی + حجم: {' | '.join(signals)}",
                    "Gap up continuation",
                    {"gap": gap})

        if gap["direction"] == "down" and not gap["filling"]:
            if spike == 1 and regime == -1:
                return self._make_result(Signal.SELL, 50,
                    f"ادامه گپ نزولی + حجم: {' | '.join(signals)}",
                    "Gap down continuation",
                    {"gap": gap})

        return self._neutral(
            f"گپ {dir_fa} فعال ({gap['gap_pct']:.2f}%) — منتظر تأیید",
            "Gap detected, waiting for confirmation",
            {"gap": gap})
