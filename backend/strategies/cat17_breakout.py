"""
Whilber-AI MVP - Strategy Cat 17: Momentum Breakout
======================================================
Volatility expansion breakout from tight consolidation.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


class MomentumBreakout(BaseStrategy):
    STRATEGY_ID = "momentum_breakout"
    STRATEGY_NAME_FA = "شکست مومنتومی"
    STRATEGY_NAME_EN = "Momentum Breakout"
    CATEGORY = "breakout"
    REQUIRED_INDICATORS = ["vol", "volume", "ma", "trend"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        vol = indicators.get("vol", {})
        volume = indicators.get("volume", {})
        ma_ind = indicators.get("ma", {})
        trend = indicators.get("trend", {})

        h, l, c = df["high"], df["low"], df["close"]
        price = c.iloc[-1]

        atr = self.last(vol.get("atr_14"))
        atr_pct = self.last(vol.get("atr_percent"))
        bb_bw = self.last(vol.get("bb_bandwidth"))
        dc_upper = self.last(vol.get("dc_upper"))
        dc_lower = self.last(vol.get("dc_lower"))
        dc_break = self.last(vol.get("dc_breakout"))
        spike = self.last(volume.get("vol_spike"))
        adx = self.last(trend.get("adx"))
        slope9 = self.last(ma_ind.get("ema_9_slope"))

        if atr is None or dc_upper is None:
            return self._neutral("داده کافی نیست")

        # Check if previous bars were tight (low volatility consolidation)
        prev_bw = vol.get("bb_bandwidth")
        was_tight = False
        if prev_bw is not None and len(prev_bw) > 5:
            avg_bw = prev_bw.iloc[-10:-1].mean()
            curr_bw = prev_bw.iloc[-1]
            if not pd.isna(avg_bw) and not pd.isna(curr_bw):
                was_tight = curr_bw > avg_bw * 1.3  # Expanding now

        # Current bar range vs ATR
        curr_range = h.iloc[-1] - l.iloc[-1]
        range_ratio = curr_range / atr if atr > 0 else 0

        confidence = 0
        signals = []

        # ── Bullish Breakout ────────────────────────────────
        if dc_break == 1:
            confidence += 30
            signals.append("شکست سقف دونچیان")

        if was_tight:
            confidence += 15
            signals.append("توسعه از فشردگی")

        if range_ratio > 1.5:
            confidence += 15
            signals.append(f"کندل بزرگ ({range_ratio:.1f}x ATR)")

        if spike == 1:
            confidence += 15
            signals.append("جهش حجم")

        if slope9 and slope9 > 0:
            confidence += 10

        if c.iloc[-1] > c.iloc[-2] and confidence > 0:
            if confidence >= 40:
                return self._make_result(Signal.BUY, min(confidence, 85),
                    f"شکست صعودی: {' | '.join(signals)}",
                    f"Bullish breakout: Donchian+expansion",
                    {"range_ratio": round(range_ratio, 2), "dc_upper": round(dc_upper, 5)})

        # ── Bearish Breakout ────────────────────────────────
        confidence = 0
        signals = []

        if dc_break == -1:
            confidence += 30
            signals.append("شکست کف دونچیان")

        if was_tight:
            confidence += 15
            signals.append("توسعه از فشردگی")

        if range_ratio > 1.5:
            confidence += 15
            signals.append(f"کندل بزرگ ({range_ratio:.1f}x ATR)")

        if spike == 1:
            confidence += 15
            signals.append("جهش حجم")

        if slope9 and slope9 < 0:
            confidence += 10

        if c.iloc[-1] < c.iloc[-2] and confidence > 0:
            if confidence >= 40:
                return self._make_result(Signal.SELL, min(confidence, 85),
                    f"شکست نزولی: {' | '.join(signals)}",
                    f"Bearish breakout",
                    {"range_ratio": round(range_ratio, 2), "dc_lower": round(dc_lower, 5)})

        return self._neutral(
            f"شکست مومنتومی یافت نشد (range ratio={range_ratio:.1f}x)",
            f"No breakout: range_ratio={range_ratio:.1f}")
