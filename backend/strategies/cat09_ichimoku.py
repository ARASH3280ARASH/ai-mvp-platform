"""
Whilber-AI MVP - Strategy Cat 9: Ichimoku Cloud
==================================================
Full Ichimoku: Tenkan/Kijun cross, Kumo breakout,
Chikou span, cloud twist, trend-with-cloud.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def calc_ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
                  tenkan_p: int = 9, kijun_p: int = 26,
                  senkou_b_p: int = 52) -> Dict[str, pd.Series]:
    """Calculate all Ichimoku components."""

    def donchian_mid(h, l, p):
        return (h.rolling(p, min_periods=p).max() + l.rolling(p, min_periods=p).min()) / 2

    tenkan = donchian_mid(high, low, tenkan_p)
    kijun = donchian_mid(high, low, kijun_p)

    senkou_a = ((tenkan + kijun) / 2).shift(kijun_p)
    senkou_b = donchian_mid(high, low, senkou_b_p).shift(kijun_p)

    chikou = close.shift(-kijun_p)

    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
    }


class IchimokuStrategy(BaseStrategy):
    STRATEGY_ID = "ichimoku"
    STRATEGY_NAME_FA = "ایچیموکو"
    STRATEGY_NAME_EN = "Ichimoku Cloud"
    CATEGORY = "ichimoku"
    REQUIRED_INDICATORS = ["trend"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        h, l, c = df["high"], df["low"], df["close"]
        price = c.iloc[-1]

        if len(df) < 60:
            return self._neutral("داده کافی نیست (حداقل ۶۰ کندل)")

        ich = calc_ichimoku(h, l, c)
        tenkan = ich["tenkan"].iloc[-1]
        kijun = ich["kijun"].iloc[-1]
        sa = ich["senkou_a"].iloc[-1]
        sb = ich["senkou_b"].iloc[-1]

        if any(pd.isna(v) for v in [tenkan, kijun, sa, sb]):
            return self._neutral("داده ایچیموکو ناقص")

        # TK cross
        tk_prev_above = ich["tenkan"].iloc[-2] > ich["kijun"].iloc[-2]
        tk_now_above = tenkan > kijun
        tk_cross_bull = not tk_prev_above and tk_now_above
        tk_cross_bear = tk_prev_above and not tk_now_above

        cloud_top = max(sa, sb)
        cloud_bot = min(sa, sb)
        above_cloud = price > cloud_top
        below_cloud = price < cloud_bot
        in_cloud = not above_cloud and not below_cloud

        bullish_cloud = sa > sb
        chikou_26 = ich["chikou"]
        chikou_ok_bull = False
        chikou_ok_bear = False
        if len(c) > 52:
            ch_idx = -27
            if abs(ch_idx) < len(c):
                chikou_ok_bull = c.iloc[-1] > c.iloc[ch_idx] if not pd.isna(c.iloc[ch_idx]) else False
                chikou_ok_bear = c.iloc[-1] < c.iloc[ch_idx] if not pd.isna(c.iloc[ch_idx]) else False

        confidence = 0
        signals = []

        # ── Bullish ─────────────────────────────────────
        if above_cloud:
            confidence += 25
            signals.append("قیمت بالای ابر")

        if tk_cross_bull:
            confidence += 20
            signals.append("کراس صعودی تنکان/کیجون")
        elif tenkan > kijun:
            confidence += 10
            signals.append("تنکان بالای کیجون")

        if bullish_cloud:
            confidence += 10
            signals.append("ابر صعودی (سنکو A > B)")

        if chikou_ok_bull:
            confidence += 10
            signals.append("چیکو بالای قیمت ۲۶ کندل قبل")

        if price > kijun and above_cloud:
            confidence += 10

        if confidence >= 40:
            return self._make_result(Signal.BUY, min(confidence, 90),
                f"ایچیموکو صعودی: {' | '.join(signals)}",
                f"Ichimoku bullish: price above cloud, TK cross",
                {"tenkan": round(tenkan, 5), "kijun": round(kijun, 5),
                 "cloud_top": round(cloud_top, 5), "cloud_bot": round(cloud_bot, 5)})

        # ── Bearish ─────────────────────────────────────
        confidence = 0
        signals = []

        if below_cloud:
            confidence += 25
            signals.append("قیمت زیر ابر")

        if tk_cross_bear:
            confidence += 20
            signals.append("کراس نزولی تنکان/کیجون")
        elif tenkan < kijun:
            confidence += 10
            signals.append("تنکان زیر کیجون")

        if not bullish_cloud:
            confidence += 10
            signals.append("ابر نزولی (سنکو B > A)")

        if chikou_ok_bear:
            confidence += 10
            signals.append("چیکو زیر قیمت ۲۶ کندل قبل")

        if price < kijun and below_cloud:
            confidence += 10

        if confidence >= 40:
            return self._make_result(Signal.SELL, min(confidence, 90),
                f"ایچیموکو نزولی: {' | '.join(signals)}",
                f"Ichimoku bearish",
                {"tenkan": round(tenkan, 5), "kijun": round(kijun, 5)})

        # In cloud = uncertain
        if in_cloud:
            return self._neutral(
                f"قیمت داخل ابر ایچیموکو — عدم قطعیت (ابر: {cloud_bot:.5f}~{cloud_top:.5f})",
                "Price inside Ichimoku cloud",
                {"in_cloud": True, "cloud_top": round(cloud_top, 5), "cloud_bot": round(cloud_bot, 5)})

        return self._neutral("سیگنال ایچیموکو ضعیف")
