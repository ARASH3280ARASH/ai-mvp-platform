"""
Whilber-AI MVP - Strategy Categories 5, 6, 7
===============================================
Cat 5: Volume Analysis
Cat 6: S/R Levels
Cat 7: Candlestick Confluence
"""

import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


# ═══════════════════════════════════════════════════════════════
# CATEGORY 5: VOLUME
# ═══════════════════════════════════════════════════════════════

class VolumeConfirmation(BaseStrategy):
    STRATEGY_ID = "volume_confirmation"
    STRATEGY_NAME_FA = "تأیید حجم"
    STRATEGY_NAME_EN = "Volume Confirmation"
    CATEGORY = "volume"
    REQUIRED_INDICATORS = ["volume", "trend", "ma"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        volume = indicators.get("volume", {})
        trend = indicators.get("trend", {})
        ma = indicators.get("ma", {})

        obv_trend = self.last(volume.get("obv_trend"))
        mfi = self.last(volume.get("mfi_14"))
        mfi_zone = self.last(volume.get("mfi_zone"))
        cmf = self.last(volume.get("cmf_20"))
        spike = self.last(volume.get("vol_spike"))
        climax = self.last(volume.get("vol_climax"))
        vwap_pos = self.last(volume.get("vwap_position"))
        regime = self.last(trend.get("regime"))

        if mfi is None:
            return self._neutral("داده کافی نیست")

        bull_score = 0
        bear_score = 0
        signals_b = []
        signals_s = []

        if obv_trend == 1:
            bull_score += 1; signals_b.append("OBV صعودی")
        elif obv_trend == -1:
            bear_score += 1; signals_s.append("OBV نزولی")

        if cmf and cmf > 0.1:
            bull_score += 1; signals_b.append(f"CMF مثبت ({cmf:.2f})")
        elif cmf and cmf < -0.1:
            bear_score += 1; signals_s.append(f"CMF منفی ({cmf:.2f})")

        if mfi_zone == -1:
            bull_score += 1; signals_b.append("MFI اشباع فروش")
        elif mfi_zone == 1:
            bear_score += 1; signals_s.append("MFI اشباع خرید")

        if vwap_pos == 1:
            bull_score += 1; signals_b.append("قیمت بالای VWAP")
        elif vwap_pos == -1:
            bear_score += 1; signals_s.append("قیمت زیر VWAP")

        if spike == 1:
            if regime == 1: bull_score += 1; signals_b.append("جهش حجم صعودی")
            elif regime == -1: bear_score += 1; signals_s.append("جهش حجم نزولی")

        if climax == -1:
            bull_score += 1; signals_b.append("حجم نقطه اوج (فروش تمام شده؟)")
        elif climax == 1:
            bear_score += 1; signals_s.append("حجم نقطه اوج (خرید تمام شده؟)")

        if bull_score >= 3:
            return self._make_result(Signal.BUY, min(bull_score * 18, 80),
                f"تأیید حجم صعودی ({bull_score} سیگنال): {' | '.join(signals_b)}",
                f"Volume bullish: {bull_score} signals",
                {"mfi": round(mfi, 1), "cmf": round(cmf or 0, 3), "obv_trend": obv_trend})

        if bear_score >= 3:
            return self._make_result(Signal.SELL, min(bear_score * 18, 80),
                f"تأیید حجم نزولی ({bear_score} سیگنال): {' | '.join(signals_s)}",
                f"Volume bearish: {bear_score} signals",
                {"mfi": round(mfi, 1), "cmf": round(cmf or 0, 3)})

        return self._neutral("حجم سیگنال واضحی نمی‌دهد")


# ═══════════════════════════════════════════════════════════════
# CATEGORY 6: S/R LEVELS
# ═══════════════════════════════════════════════════════════════

class SRBounce(BaseStrategy):
    STRATEGY_ID = "sr_bounce"
    STRATEGY_NAME_FA = "برگشت از S/R"
    STRATEGY_NAME_EN = "S/R Bounce"
    CATEGORY = "sr_levels"
    REQUIRED_INDICATORS = ["structure", "candle", "osc"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        struct = indicators.get("structure", {})
        candle = indicators.get("candle", {})
        osc = indicators.get("osc", {})

        sr_interact = self.last(struct.get("sr_interaction"))
        sr_levels = struct.get("sr_levels", {})
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))
        doji = self.last(candle.get("doji"))
        rsi = self.last(osc.get("rsi_14"))
        price = df["close"].iloc[-1]

        confidence = 0
        signals = []

        # Bounce from support
        if sr_interact == 1:
            confidence += 35
            signals.append("برگشت از سطح حمایت")
            if pin == 1 or engulf == 1:
                confidence += 20
                signals.append("تأیید کندلی")
            if rsi and rsi < 40:
                confidence += 10
                signals.append("RSI پایین")
            if confidence >= 40:
                return self._make_result(Signal.BUY, confidence,
                    f"برگشت از حمایت: {' | '.join(signals)}",
                    "Support bounce",
                    {"price": round(price, 5), "sr_interaction": sr_interact})

        # Rejection from resistance
        if sr_interact == -1:
            confidence = 35
            signals = ["رد از سطح مقاومت"]
            if pin == -1 or engulf == -1:
                confidence += 20
                signals.append("تأیید کندلی")
            if rsi and rsi > 60:
                confidence += 10
            if confidence >= 40:
                return self._make_result(Signal.SELL, confidence,
                    f"رد از مقاومت: {' | '.join(signals)}",
                    "Resistance rejection",
                    {"price": round(price, 5)})

        # Break above resistance
        if sr_interact == 2:
            confidence = 40
            signals = ["شکست مقاومت (Breakout)"]
            return self._make_result(Signal.BUY, confidence,
                f"شکست صعودی: {' | '.join(signals)}",
                "Resistance breakout",
                {"price": round(price, 5)})

        # Break below support
        if sr_interact == -2:
            confidence = 40
            signals = ["شکست حمایت (Breakdown)"]
            return self._make_result(Signal.SELL, confidence,
                f"شکست نزولی: {' | '.join(signals)}",
                "Support breakdown",
                {"price": round(price, 5)})

        return self._neutral("تعامل مشخصی با سطوح S/R نیست")


# ═══════════════════════════════════════════════════════════════
# CATEGORY 7: CANDLESTICK CONFLUENCE
# ═══════════════════════════════════════════════════════════════

class CandleConfluence(BaseStrategy):
    STRATEGY_ID = "candle_confluence"
    STRATEGY_NAME_FA = "تلاقی کندلی"
    STRATEGY_NAME_EN = "Candlestick Confluence"
    CATEGORY = "candlestick"
    REQUIRED_INDICATORS = ["candle", "osc", "vol"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        candle = indicators.get("candle", {})
        osc = indicators.get("osc", {})
        vol = indicators.get("vol", {})

        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))
        mstar = self.last(candle.get("morning_star"))
        estar = self.last(candle.get("evening_star"))
        marubozu = self.last(candle.get("marubozu"))
        inside = self.last(candle.get("inside_bar"))
        doji = self.last(candle.get("doji"))
        body_pct = self.last(candle.get("candle_body_pct"))
        rsi = self.last(osc.get("rsi_14"))
        bb_pos = self.last(vol.get("bb_position"))

        confidence = 0
        signals = []
        direction = 0

        # Strong bullish patterns
        if mstar == 1:
            confidence += 40; signals.append("ستاره صبحگاهی"); direction = 1
        if engulf == 1:
            confidence += 30; signals.append("اینگالف صعودی"); direction = 1
        if pin == 1:
            confidence += 25; signals.append("پین بار صعودی"); direction = 1
        if marubozu == 1:
            confidence += 20; signals.append("ماروبوزو صعودی"); direction = 1

        # Strong bearish patterns
        if estar == -1:
            confidence += 40; signals.append("ستاره عصرگاهی"); direction = -1
        if engulf == -1:
            confidence += 30; signals.append("اینگالف نزولی"); direction = -1
        if pin == -1:
            confidence += 25; signals.append("پین بار نزولی"); direction = -1
        if marubozu == -1:
            confidence += 20; signals.append("ماروبوزو نزولی"); direction = -1

        # Context (BB position, RSI)
        if direction == 1 and bb_pos and bb_pos <= -1:
            confidence += 10; signals.append("نزدیک باند پایین بولینگر")
        if direction == -1 and bb_pos and bb_pos >= 1:
            confidence += 10; signals.append("نزدیک باند بالای بولینگر")

        if direction == 1 and rsi and rsi < 40:
            confidence += 10
        elif direction == -1 and rsi and rsi > 60:
            confidence += 10

        if confidence >= 35 and direction != 0:
            sig = Signal.BUY if direction == 1 else Signal.SELL
            return self._make_result(sig, min(confidence, 90),
                f"الگوی کندلی: {' | '.join(signals)}",
                f"Candle pattern: {direction}",
                {"patterns": signals, "rsi": round(rsi or 0, 1)})

        # Inside bar alert
        if inside == 1:
            return self._neutral(
                "Inside Bar — منتظر شکست باشید",
                "Inside bar, waiting for breakout",
                {"inside_bar": True})

        return self._neutral("الگوی کندلی مشخصی نیست")
