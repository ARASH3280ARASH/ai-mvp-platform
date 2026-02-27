"""
Whilber-AI MVP - Strategy Cat 21: Wyckoff Analysis
=====================================================
Detect accumulation/distribution phases, spring, UTAD.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def detect_wyckoff_phase(df: pd.DataFrame, lookback: int = 60) -> Dict:
    """
    Simplified Wyckoff phase detection:
    - Accumulation: range-bound after downtrend, volume declining, spring
    - Distribution: range-bound after uptrend, volume declining, UTAD
    """
    h, l, c, v = df["high"], df["low"], df["close"], df["volume"]

    recent = slice(-lookback, None)
    rh = h[recent]
    rl = l[recent]
    rc = c[recent]
    rv = v[recent]

    # Determine preceding trend (first half vs second half)
    half = lookback // 2
    first_half_close = c.iloc[-lookback:-half].mean()
    second_half_close = c.iloc[-half:].mean()

    preceding_trend = 0
    if first_half_close > second_half_close * 1.005:
        preceding_trend = -1  # Was downtrend → potential accumulation
    elif first_half_close < second_half_close * 0.995:
        preceding_trend = 1   # Was uptrend → potential distribution

    # Range detection
    range_high = rh.max()
    range_low = rl.min()
    range_pct = (range_high - range_low) / range_low * 100

    # Volume trend in range
    vol_first = rv.iloc[:half].mean()
    vol_second = rv.iloc[half:].mean()
    vol_declining = vol_second < vol_first * 0.8

    # Spring: price briefly breaks below range low then closes inside
    spring = False
    utad = False
    curr_low = l.iloc[-1]
    curr_close = c.iloc[-1]
    curr_high = h.iloc[-1]

    # Check last 3 bars for spring/UTAD
    for i in range(-3, 0):
        bar_l = l.iloc[i]
        bar_c = c.iloc[i]
        bar_h = h.iloc[i]

        if bar_l < range_low and bar_c > range_low:
            spring = True
        if bar_h > range_high and bar_c < range_high:
            utad = True

    return {
        "preceding_trend": preceding_trend,
        "range_high": range_high,
        "range_low": range_low,
        "range_pct": range_pct,
        "vol_declining": vol_declining,
        "spring": spring,
        "utad": utad,
        "phase": _classify_phase(preceding_trend, vol_declining, spring, utad),
    }


def _classify_phase(trend, vol_declining, spring, utad) -> str:
    if trend == -1 and spring:
        return "accumulation_spring"
    if trend == -1 and vol_declining:
        return "accumulation"
    if trend == 1 and utad:
        return "distribution_utad"
    if trend == 1 and vol_declining:
        return "distribution"
    return "unknown"


PHASE_FA = {
    "accumulation_spring": "انباشت + اسپرینگ 🟢",
    "accumulation": "انباشت (فاز جمع‌آوری)",
    "distribution_utad": "توزیع + UTAD 🔴",
    "distribution": "توزیع (فاز تخلیه)",
    "unknown": "نامشخص",
}


class WyckoffStrategy(BaseStrategy):
    STRATEGY_ID = "wyckoff"
    STRATEGY_NAME_FA = "وایکاف"
    STRATEGY_NAME_EN = "Wyckoff Analysis"
    CATEGORY = "wyckoff"
    REQUIRED_INDICATORS = ["volume", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        volume = indicators.get("volume", {})
        candle = indicators.get("candle", {})

        price = df["close"].iloc[-1]
        spike = self.last(volume.get("vol_spike"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))

        if len(df) < 60:
            return self._neutral("داده کافی نیست (حداقل ۶۰ کندل)")

        wyck = detect_wyckoff_phase(df, lookback=60)
        phase = wyck["phase"]
        phase_fa = PHASE_FA.get(phase, phase)

        confidence = 0
        signals = [f"فاز وایکاف: {phase_fa}"]

        # ── Accumulation Spring → BUY ───────────────────────
        if phase == "accumulation_spring":
            confidence += 45
            signals.append("اسپرینگ تشخیص داده شد (شکست جعلی کف)")

            if pin == 1 or engulf == 1:
                confidence += 15
                signals.append("تأیید کندلی")
            if spike == 1:
                confidence += 10
                signals.append("جهش حجم در اسپرینگ")

            if confidence >= 45:
                return self._make_result(Signal.BUY, min(confidence, 85),
                    f"وایکاف صعودی: {' | '.join(signals)}",
                    f"Wyckoff accumulation spring",
                    {"phase": phase, "range_low": round(wyck["range_low"], 5),
                     "range_high": round(wyck["range_high"], 5)})

        # ── Accumulation (no spring yet) ────────────────────
        if phase == "accumulation":
            confidence += 25
            if wyck["vol_declining"]:
                confidence += 10
                signals.append("حجم در حال کاهش (جذب بی‌سروصدا)")

            return self._neutral(
                f"وایکاف: {' | '.join(signals)} — منتظر اسپرینگ",
                "Wyckoff accumulation, waiting for spring",
                {"phase": phase, "range": f"{wyck['range_low']:.5f}~{wyck['range_high']:.5f}"})

        # ── Distribution UTAD → SELL ────────────────────────
        if phase == "distribution_utad":
            confidence += 45
            signals.append("UTAD تشخیص داده شد (شکست جعلی سقف)")

            if pin == -1 or engulf == -1:
                confidence += 15
                signals.append("تأیید کندلی")
            if spike == 1:
                confidence += 10

            if confidence >= 45:
                return self._make_result(Signal.SELL, min(confidence, 85),
                    f"وایکاف نزولی: {' | '.join(signals)}",
                    f"Wyckoff distribution UTAD",
                    {"phase": phase, "range_high": round(wyck["range_high"], 5)})

        # ── Distribution ────────────────────────────────────
        if phase == "distribution":
            confidence += 25
            if wyck["vol_declining"]:
                confidence += 10
                signals.append("حجم در حال کاهش")

            return self._neutral(
                f"وایکاف: {' | '.join(signals)} — منتظر UTAD",
                "Wyckoff distribution, waiting for UTAD",
                {"phase": phase})

        return self._neutral(
            f"فاز وایکاف نامشخص | رنج: {wyck['range_pct']:.1f}%",
            "Wyckoff phase unclear",
            {"phase": phase, "range_pct": round(wyck["range_pct"], 2)})
