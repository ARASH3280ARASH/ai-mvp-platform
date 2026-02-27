"""
Whilber-AI MVP - Strategy Category 3: Momentum & Oscillators
===============================================================
"""

import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


class RSIExtremes(BaseStrategy):
    STRATEGY_ID = "rsi_extremes"
    STRATEGY_NAME_FA = "اشباع RSI"
    STRATEGY_NAME_EN = "RSI Extremes"
    CATEGORY = "momentum"
    REQUIRED_INDICATORS = ["osc", "trend", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        osc = indicators.get("osc", {})
        trend = indicators.get("trend", {})
        candle = indicators.get("candle", {})

        rsi = self.last(osc.get("rsi_14"))
        rsi_prev = self.prev(osc.get("rsi_14"))
        rsi_rev = self.last(osc.get("rsi_reversal"))
        regime = self.last(trend.get("regime"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))

        if rsi is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # Bullish: RSI exiting oversold
        if rsi_rev == 1 or (rsi_prev and rsi_prev < 30 and rsi > 30):
            confidence += 35
            signals.append(f"RSI از اشباع فروش خارج شد ({rsi:.0f})")

            if pin == 1 or engulf == 1:
                confidence += 20
                signals.append("تأیید کندلی")
            if regime != -1:
                confidence += 10

            if confidence >= 40:
                return self._make_result(Signal.BUY, confidence,
                    f"سیگنال RSI صعودی: {' | '.join(signals)}",
                    f"RSI bullish reversal from {rsi_prev:.0f} to {rsi:.0f}",
                    {"rsi": round(rsi, 1)})

        # Bearish: RSI exiting overbought
        if rsi_rev == -1 or (rsi_prev and rsi_prev > 70 and rsi < 70):
            confidence = 35
            signals = [f"RSI از اشباع خرید خارج شد ({rsi:.0f})"]

            if pin == -1 or engulf == -1:
                confidence += 20
                signals.append("تأیید کندلی")
            if regime != 1:
                confidence += 10

            if confidence >= 40:
                return self._make_result(Signal.SELL, confidence,
                    f"سیگنال RSI نزولی: {' | '.join(signals)}",
                    f"RSI bearish reversal",
                    {"rsi": round(rsi, 1)})

        return self._neutral(f"RSI خنثی ({rsi:.0f})")


class StochasticCross(BaseStrategy):
    STRATEGY_ID = "stochastic_cross"
    STRATEGY_NAME_FA = "کراس استوکاستیک"
    STRATEGY_NAME_EN = "Stochastic Cross"
    CATEGORY = "momentum"
    REQUIRED_INDICATORS = ["osc", "trend"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        osc = indicators.get("osc", {})
        trend = indicators.get("trend", {})

        k = self.last(osc.get("stoch_k"))
        d = self.last(osc.get("stoch_d"))
        cross = self.last(osc.get("stoch_cross"))
        zone = self.last(osc.get("stoch_zone"))
        rev = self.last(osc.get("stoch_reversal"))
        regime = self.last(trend.get("regime"))

        if k is None or d is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # Bullish: cross up in oversold
        if cross == 1 and zone == -1:
            confidence += 45
            signals.append(f"کراس صعودی در اشباع فروش (K={k:.0f})")
        elif cross == 1:
            confidence += 25
            signals.append(f"کراس صعودی (K={k:.0f})")
        elif rev == 1:
            confidence += 30
            signals.append("خروج از اشباع فروش")

        if regime == 1 and confidence > 0:
            confidence += 15
            signals.append("همسو با روند صعودی")

        if confidence >= 40:
            return self._make_result(Signal.BUY, confidence,
                f"استوکاستیک صعودی: {' | '.join(signals)}",
                f"Stoch bullish: K={k:.0f}, D={d:.0f}",
                {"stoch_k": round(k, 1), "stoch_d": round(d, 1)})

        # Bearish
        confidence = 0
        signals = []

        if cross == -1 and zone == 1:
            confidence += 45
            signals.append(f"کراس نزولی در اشباع خرید (K={k:.0f})")
        elif cross == -1:
            confidence += 25
            signals.append(f"کراس نزولی (K={k:.0f})")
        elif rev == -1:
            confidence += 30
            signals.append("خروج از اشباع خرید")

        if regime == -1 and confidence > 0:
            confidence += 15

        if confidence >= 40:
            return self._make_result(Signal.SELL, confidence,
                f"استوکاستیک نزولی: {' | '.join(signals)}",
                f"Stoch bearish",
                {"stoch_k": round(k, 1), "stoch_d": round(d, 1)})

        return self._neutral(f"استوکاستیک خنثی (K={k:.0f})")


class MACDSignal(BaseStrategy):
    STRATEGY_ID = "macd_signal"
    STRATEGY_NAME_FA = "سیگنال MACD"
    STRATEGY_NAME_EN = "MACD Signal"
    CATEGORY = "momentum"
    REQUIRED_INDICATORS = ["macd", "trend"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        macd = indicators.get("macd", {})
        trend = indicators.get("trend", {})

        cross = self.last(macd.get("macd_cross"))
        zero_cross = self.last(macd.get("macd_zero_cross"))
        hist = self.last(macd.get("macd_hist"))
        hist_trend = self.last(macd.get("macd_hist_trend"))
        macd_line = self.last(macd.get("macd_line"))
        regime = self.last(trend.get("regime"))

        if macd_line is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # Bullish
        if cross == 1:
            confidence += 35
            signals.append("کراس صعودی MACD/Signal")
        if zero_cross == 1:
            confidence += 20
            signals.append("عبور MACD از خط صفر (صعودی)")
        if hist_trend == -2:  # Shrinking negative = weakening bears
            confidence += 10
            signals.append("هیستوگرام در حال تضعیف نزولی")
        if hist and hist > 0 and hist_trend == 1:
            confidence += 15
            signals.append("هیستوگرام مثبت و رو به رشد")
        if regime == 1:
            confidence += 10

        if confidence >= 40:
            return self._make_result(Signal.BUY, confidence,
                f"MACD صعودی: {' | '.join(signals)}",
                f"MACD bullish: line={macd_line:.6f}",
                {"macd_line": round(macd_line, 6), "histogram": round(hist or 0, 6)})

        # Bearish
        confidence = 0
        signals = []

        if cross == -1:
            confidence += 35
            signals.append("کراس نزولی MACD/Signal")
        if zero_cross == -1:
            confidence += 20
            signals.append("عبور MACD از خط صفر (نزولی)")
        if hist_trend == 2:  # Shrinking positive = weakening bulls
            confidence += 10
            signals.append("هیستوگرام در حال تضعیف صعودی")
        if hist and hist < 0 and hist_trend == -1:
            confidence += 15
            signals.append("هیستوگرام منفی و رو به رشد")
        if regime == -1:
            confidence += 10

        if confidence >= 40:
            return self._make_result(Signal.SELL, confidence,
                f"MACD نزولی: {' | '.join(signals)}",
                f"MACD bearish",
                {"macd_line": round(macd_line, 6)})

        return self._neutral(f"MACD خنثی")


class MultiOscillator(BaseStrategy):
    STRATEGY_ID = "multi_oscillator"
    STRATEGY_NAME_FA = "تلاقی نوسانگرها"
    STRATEGY_NAME_EN = "Multi-Oscillator Confluence"
    CATEGORY = "momentum"
    REQUIRED_INDICATORS = ["osc", "macd"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        osc = indicators.get("osc", {})
        macd = indicators.get("macd", {})

        rsi = self.last(osc.get("rsi_14"))
        stoch_k = self.last(osc.get("stoch_k"))
        cci = self.last(osc.get("cci_20"))
        wr = self.last(osc.get("williams_r"))
        macd_hist = self.last(macd.get("macd_hist"))
        mfi = self.last(osc.get("mfi_14")) if "mfi_14" in osc else None

        if rsi is None or stoch_k is None:
            return self._neutral("داده کافی نیست")

        bull_count = 0
        bear_count = 0
        signals_bull = []
        signals_bear = []

        # RSI
        if rsi < 30:
            bull_count += 1; signals_bull.append(f"RSI اشباع فروش ({rsi:.0f})")
        elif rsi > 70:
            bear_count += 1; signals_bear.append(f"RSI اشباع خرید ({rsi:.0f})")

        # Stochastic
        if stoch_k < 20:
            bull_count += 1; signals_bull.append("استوکاستیک اشباع فروش")
        elif stoch_k > 80:
            bear_count += 1; signals_bear.append("استوکاستیک اشباع خرید")

        # CCI
        if cci and cci < -100:
            bull_count += 1; signals_bull.append("CCI اشباع فروش")
        elif cci and cci > 100:
            bear_count += 1; signals_bear.append("CCI اشباع خرید")

        # Williams %R
        if wr and wr < -80:
            bull_count += 1; signals_bull.append("Williams %R اشباع فروش")
        elif wr and wr > -20:
            bear_count += 1; signals_bear.append("Williams %R اشباع خرید")

        # MACD histogram
        if macd_hist and macd_hist > 0:
            bull_count += 1
        elif macd_hist and macd_hist < 0:
            bear_count += 1

        # Confluence scoring
        if bull_count >= 3:
            conf = min(bull_count * 20, 85)
            return self._make_result(Signal.BUY, conf,
                f"تلاقی {bull_count} نوسانگر صعودی: {' | '.join(signals_bull)}",
                f"{bull_count} oscillators bullish confluence",
                {"bull_count": bull_count, "rsi": round(rsi, 1), "stoch_k": round(stoch_k, 1)})

        if bear_count >= 3:
            conf = min(bear_count * 20, 85)
            return self._make_result(Signal.SELL, conf,
                f"تلاقی {bear_count} نوسانگر نزولی: {' | '.join(signals_bear)}",
                f"{bear_count} oscillators bearish confluence",
                {"bear_count": bear_count, "rsi": round(rsi, 1)})

        return self._neutral("تلاقی کافی نیست")
