"""
Whilber-AI MVP - Strategy Cat 16: Mean Reversion
===================================================
Statistical mean reversion when price deviates extremely.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def z_score(close: pd.Series, period: int = 20) -> pd.Series:
    """Z-score: how many standard deviations from mean."""
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return (close - ma) / std.replace(0, np.nan)


class MeanReversion(BaseStrategy):
    STRATEGY_ID = "mean_reversion"
    STRATEGY_NAME_FA = "بازگشت به میانگین"
    STRATEGY_NAME_EN = "Mean Reversion"
    CATEGORY = "mean_reversion"
    REQUIRED_INDICATORS = ["ma", "osc", "vol", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        ma_ind = indicators.get("ma", {})
        osc = indicators.get("osc", {})
        vol = indicators.get("vol", {})
        candle = indicators.get("candle", {})

        close = df["close"]
        price = close.iloc[-1]

        z = z_score(close, 20)
        z_val = z.iloc[-1] if not pd.isna(z.iloc[-1]) else 0

        dist50 = self.last(ma_ind.get("ema_50_distance"))
        bb_pct = self.last(vol.get("bb_percent_b"))
        rsi = self.last(osc.get("rsi_14"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))

        confidence = 0
        signals = []

        # ── Oversold / Buy ──────────────────────────────────
        if z_val < -2:
            confidence += 35
            signals.append(f"Z-Score بسیار پایین ({z_val:.2f})")
        elif z_val < -1.5:
            confidence += 20
            signals.append(f"Z-Score پایین ({z_val:.2f})")

        if dist50 and dist50 < -1.5:
            confidence += 15
            signals.append(f"فاصله زیاد از EMA50 ({dist50:.2f}%)")

        if bb_pct is not None and bb_pct < 5:
            confidence += 10
            signals.append("زیر باند پایین بولینگر")

        if rsi and rsi < 25:
            confidence += 10
            signals.append(f"RSI بسیار پایین ({rsi:.0f})")

        if pin == 1 or engulf == 1:
            confidence += 10
            signals.append("تأیید کندلی صعودی")

        if confidence >= 40:
            return self._make_result(Signal.BUY, min(confidence, 85),
                f"بازگشت به میانگین (خرید): {' | '.join(signals)}",
                f"Mean reversion buy: Z={z_val:.2f}",
                {"z_score": round(z_val, 3), "dist_ema50": round(dist50 or 0, 3)})

        # ── Overbought / Sell ───────────────────────────────
        confidence = 0
        signals = []

        if z_val > 2:
            confidence += 35
            signals.append(f"Z-Score بسیار بالا ({z_val:.2f})")
        elif z_val > 1.5:
            confidence += 20
            signals.append(f"Z-Score بالا ({z_val:.2f})")

        if dist50 and dist50 > 1.5:
            confidence += 15
            signals.append(f"فاصله زیاد از EMA50 ({dist50:.2f}%)")

        if bb_pct is not None and bb_pct > 95:
            confidence += 10
            signals.append("بالای باند بالای بولینگر")

        if rsi and rsi > 75:
            confidence += 10
            signals.append(f"RSI بسیار بالا ({rsi:.0f})")

        if pin == -1 or engulf == -1:
            confidence += 10
            signals.append("تأیید کندلی نزولی")

        if confidence >= 40:
            return self._make_result(Signal.SELL, min(confidence, 85),
                f"بازگشت به میانگین (فروش): {' | '.join(signals)}",
                f"Mean reversion sell: Z={z_val:.2f}",
                {"z_score": round(z_val, 3)})

        return self._neutral(
            f"Z-Score نرمال ({z_val:.2f}) — فاصله کافی از میانگین نیست",
            f"Z-score normal: {z_val:.2f}",
            {"z_score": round(z_val, 3)})
