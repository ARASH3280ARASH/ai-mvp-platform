"""
Whilber-AI MVP - Strategy Category 1: Trend & Structure
==========================================================
5 strategy modules covering trend analysis.
"""

import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


# ═══════════════════════════════════════════════════════════════
# 1.1 TREND FOLLOWING
# ═══════════════════════════════════════════════════════════════

class TrendFollowing(BaseStrategy):
    """
    Riding the trend: identifies strong trends and signals
    entry in trend direction with ADX and MA confirmation.
    """
    STRATEGY_ID = "trend_following"
    STRATEGY_NAME_FA = "روند‌یاب"
    STRATEGY_NAME_EN = "Trend Following"
    CATEGORY = "trend_structure"
    REQUIRED_INDICATORS = ["ma", "trend", "vol"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        ma = indicators.get("ma", {})
        trend = indicators.get("trend", {})
        vol = indicators.get("vol", {})

        # Core checks
        adx = self.last(trend.get("adx"))
        plus_di = self.last(trend.get("plus_di"))
        minus_di = self.last(trend.get("minus_di"))
        regime = self.last(trend.get("regime"))

        ema9 = self.last(ma.get("ema_9"))
        ema21 = self.last(ma.get("ema_21"))
        ema50 = self.last(ma.get("ema_50"))
        stack = self.last(ma.get("ma_stack"))
        slope50 = self.last(ma.get("ema_50_slope"))

        st_dir = self.last(vol.get("supertrend_dir"))
        price = df["close"].iloc[-1]

        if any(v is None for v in [adx, ema9, ema21, ema50]):
            return self._neutral("داده کافی نیست", "Insufficient data")

        confidence = 0
        signals = []

        # ── Bullish Trend ───────────────────────────────────
        if adx > 25 and plus_di > minus_di:
            confidence += 25
            signals.append("ADX قوی + DI مثبت غالب")

        if stack == 1:  # Bullish stack
            confidence += 20
            signals.append("MA‌ها صعودی چیده شده")

        if slope50 is not None and slope50 > 0:
            confidence += 15
            signals.append("شیب MA50 صعودی")

        if st_dir == 1:
            confidence += 15
            signals.append("سوپرترند صعودی")

        if price > ema9 > ema21:
            confidence += 15
            signals.append("قیمت بالای MA کوتاه و میان‌مدت")

        if regime == 1:
            confidence += 10

        if confidence >= 50:
            return self._make_result(
                Signal.BUY, confidence,
                f"روند صعودی قوی: {' | '.join(signals)}",
                f"Strong uptrend: ADX={adx:.0f}, stack={stack}",
                {"adx": round(adx, 1), "ema9": round(ema9, 5),
                 "ema50": round(ema50, 5), "supertrend": st_dir}
            )

        # ── Bearish Trend ───────────────────────────────────
        confidence = 0
        signals = []

        if adx > 25 and minus_di > plus_di:
            confidence += 25
            signals.append("ADX قوی + DI منفی غالب")

        if stack == -1:
            confidence += 20
            signals.append("MA‌ها نزولی چیده شده")

        if slope50 is not None and slope50 < 0:
            confidence += 15
            signals.append("شیب MA50 نزولی")

        if st_dir == -1:
            confidence += 15
            signals.append("سوپرترند نزولی")

        if price < ema9 < ema21:
            confidence += 15
            signals.append("قیمت زیر MA کوتاه و میان‌مدت")

        if regime == -1:
            confidence += 10

        if confidence >= 50:
            return self._make_result(
                Signal.SELL, confidence,
                f"روند نزولی قوی: {' | '.join(signals)}",
                f"Strong downtrend: ADX={adx:.0f}, stack={stack}",
                {"adx": round(adx, 1), "ema9": round(ema9, 5),
                 "ema50": round(ema50, 5), "supertrend": st_dir}
            )

        return self._neutral(
            f"روند ضعیف یا خنثی (ADX={adx:.0f})",
            f"Weak/no trend: ADX={adx:.0f}"
        )


# ═══════════════════════════════════════════════════════════════
# 1.2 TREND PULLBACK
# ═══════════════════════════════════════════════════════════════

class TrendPullback(BaseStrategy):
    """
    Entry on pullback to MA or trendline during established trend.
    """
    STRATEGY_ID = "trend_pullback"
    STRATEGY_NAME_FA = "پولبک روند"
    STRATEGY_NAME_EN = "Trend Pullback"
    CATEGORY = "trend_structure"
    REQUIRED_INDICATORS = ["ma", "trend", "osc", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        ma = indicators.get("ma", {})
        trend = indicators.get("trend", {})
        osc = indicators.get("osc", {})
        candle = indicators.get("candle", {})

        adx = self.last(trend.get("adx"))
        regime = self.last(trend.get("regime"))
        ema21 = self.last(ma.get("ema_21"))
        ema50 = self.last(ma.get("ema_50"))
        dist21 = self.last(ma.get("ema_21_distance"))
        rsi = self.last(osc.get("rsi_14"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))
        price = df["close"].iloc[-1]
        low = df["low"].iloc[-1]
        high = df["high"].iloc[-1]

        if any(v is None for v in [adx, ema21, ema50, rsi]):
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # ── Bullish Pullback ────────────────────────────────
        if regime == 1 and adx > 20:
            # Price pulled back near EMA 21 or 50
            if dist21 is not None and -0.5 < dist21 < 0.3:
                confidence += 30
                signals.append("پولبک به EMA21")
            elif ema50 and abs(price - ema50) / ema50 * 100 < 0.3:
                confidence += 25
                signals.append("پولبک به EMA50")

            if rsi and 35 < rsi < 55:
                confidence += 15
                signals.append("RSI در ناحیه پولبک")

            if pin == 1:
                confidence += 20
                signals.append("پین بار صعودی")
            elif engulf == 1:
                confidence += 20
                signals.append("اینگالف صعودی")

            if adx > 30:
                confidence += 10

            if confidence >= 45:
                return self._make_result(
                    Signal.BUY, confidence,
                    f"پولبک صعودی: {' | '.join(signals)}",
                    f"Bullish pullback to MA",
                    {"rsi": round(rsi, 1), "dist_ema21": round(dist21 or 0, 3)}
                )

        # ── Bearish Pullback ────────────────────────────────
        confidence = 0
        signals = []

        if regime == -1 and adx > 20:
            if dist21 is not None and -0.3 < dist21 < 0.5:
                confidence += 30
                signals.append("پولبک به EMA21")

            if rsi and 45 < rsi < 65:
                confidence += 15
                signals.append("RSI در ناحیه پولبک")

            if pin == -1:
                confidence += 20
                signals.append("پین بار نزولی")
            elif engulf == -1:
                confidence += 20
                signals.append("اینگالف نزولی")

            if adx > 30:
                confidence += 10

            if confidence >= 45:
                return self._make_result(
                    Signal.SELL, confidence,
                    f"پولبک نزولی: {' | '.join(signals)}",
                    f"Bearish pullback to MA",
                    {"rsi": round(rsi, 1)}
                )

        return self._neutral("شرایط پولبک مناسب نیست")


# ═══════════════════════════════════════════════════════════════
# 1.3 TREND CONTINUATION
# ═══════════════════════════════════════════════════════════════

class TrendContinuation(BaseStrategy):
    """
    Break & hold, flag/pennant, compression→expansion in trend.
    """
    STRATEGY_ID = "trend_continuation"
    STRATEGY_NAME_FA = "ادامه روند"
    STRATEGY_NAME_EN = "Trend Continuation"
    CATEGORY = "trend_structure"
    REQUIRED_INDICATORS = ["ma", "trend", "vol", "structure"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        ma = indicators.get("ma", {})
        trend = indicators.get("trend", {})
        vol = indicators.get("vol", {})
        struct = indicators.get("structure", {})

        regime = self.last(trend.get("regime"))
        adx = self.last(trend.get("adx"))
        bos = self.last(struct.get("bos"))
        squeeze = self.last(vol.get("squeeze_on"))
        squeeze_prev = self.prev(vol.get("squeeze_on"))
        bb_bw = self.last(vol.get("bb_bandwidth"))
        bb_bw_prev = self.prev(vol.get("bb_bandwidth"), 3)
        stack = self.last(ma.get("ma_stack"))

        price = df["close"].iloc[-1]

        if adx is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # Squeeze release (compression → expansion)
        if squeeze_prev == 1 and squeeze == 0:
            confidence += 25
            signals.append("خروج از فشردگی (Squeeze Release)")

        # BOS in trend direction
        if bos == 1 and regime == 1:
            confidence += 25
            signals.append("شکست ساختار صعودی (BOS)")
        elif bos == -1 and regime == -1:
            confidence += 25
            signals.append("شکست ساختار نزولی (BOS)")

        # MA stack confirms
        if stack == regime and regime != 0:
            confidence += 15
            signals.append("تأیید MA Stack")

        # ADX rising
        adx_prev = self.prev(trend.get("adx"), 3)
        if adx_prev and adx > adx_prev:
            confidence += 10
            signals.append("ADX در حال افزایش")

        # Bandwidth expanding
        if bb_bw and bb_bw_prev and bb_bw > bb_bw_prev:
            confidence += 10
            signals.append("باندویدث در حال افزایش")

        if confidence >= 45:
            sig = Signal.BUY if regime == 1 or bos == 1 else Signal.SELL if regime == -1 or bos == -1 else Signal.NEUTRAL
            if sig != Signal.NEUTRAL:
                return self._make_result(
                    sig, confidence,
                    f"ادامه روند: {' | '.join(signals)}",
                    f"Trend continuation: BOS={bos}, squeeze_release",
                    {"adx": round(adx, 1), "bos": bos, "squeeze": squeeze}
                )

        return self._neutral("الگوی ادامه روند یافت نشد")


# ═══════════════════════════════════════════════════════════════
# 1.4 TREND REVERSAL
# ═══════════════════════════════════════════════════════════════

class TrendReversal(BaseStrategy):
    """
    Structure flip detection: HH/HL → LH/LL or vice versa.
    """
    STRATEGY_ID = "trend_reversal"
    STRATEGY_NAME_FA = "برگشت روند"
    STRATEGY_NAME_EN = "Trend Reversal"
    CATEGORY = "trend_structure"
    REQUIRED_INDICATORS = ["ma", "trend", "structure", "osc", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        struct = indicators.get("structure", {})
        trend = indicators.get("trend", {})
        osc = indicators.get("osc", {})
        ma = indicators.get("ma", {})
        candle = indicators.get("candle", {})

        choch = self.last(struct.get("choch"))
        struct_trend = self.last(struct.get("structure_trend"))
        rsi = self.last(osc.get("rsi_14"))
        rsi_rev = self.last(osc.get("rsi_reversal"))
        cross_9_21 = self.last(ma.get("cross_9_21"))
        engulf = self.last(candle.get("engulfing"))
        pin = self.last(candle.get("pin_bar"))

        if choch is None and rsi is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # ── Bullish Reversal ────────────────────────────────
        if choch == 1:
            confidence += 35
            signals.append("تغییر ساختار صعودی (CHoCH)")

        if rsi_rev == 1:
            confidence += 15
            signals.append("خروج RSI از اشباع فروش")

        if cross_9_21 == 1:
            confidence += 15
            signals.append("کراس صعودی MA 9/21")

        if engulf == 1 or pin == 1:
            confidence += 15
            signals.append("الگوی کندلی صعودی")

        if confidence >= 45:
            return self._make_result(
                Signal.BUY, confidence,
                f"برگشت صعودی: {' | '.join(signals)}",
                f"Bullish reversal: CHoCH={choch}",
                {"choch": choch, "rsi": round(rsi or 0, 1)}
            )

        # ── Bearish Reversal ────────────────────────────────
        confidence = 0
        signals = []

        if choch == -1:
            confidence += 35
            signals.append("تغییر ساختار نزولی (CHoCH)")

        if rsi_rev == -1:
            confidence += 15
            signals.append("خروج RSI از اشباع خرید")

        if cross_9_21 == -1:
            confidence += 15
            signals.append("کراس نزولی MA 9/21")

        if engulf == -1 or pin == -1:
            confidence += 15
            signals.append("الگوی کندلی نزولی")

        if confidence >= 45:
            return self._make_result(
                Signal.SELL, confidence,
                f"برگشت نزولی: {' | '.join(signals)}",
                f"Bearish reversal: CHoCH={choch}",
                {"choch": choch, "rsi": round(rsi or 0, 1)}
            )

        return self._neutral("سیگنال برگشت واضح نیست")


# ═══════════════════════════════════════════════════════════════
# 1.5 STAIR-STEP
# ═══════════════════════════════════════════════════════════════

class StairStep(BaseStrategy):
    """
    Stair-step pattern: orderly HH/HL or LH/LL progression.
    """
    STRATEGY_ID = "stair_step"
    STRATEGY_NAME_FA = "پله‌ای"
    STRATEGY_NAME_EN = "Stair-Step"
    CATEGORY = "trend_structure"
    REQUIRED_INDICATORS = ["structure", "trend", "ma"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        struct = indicators.get("structure", {})
        trend = indicators.get("trend", {})
        ma = indicators.get("ma", {})

        struct_trend = self.last(struct.get("structure_trend"))
        adx = self.last(trend.get("adx"))
        slope21 = self.last(ma.get("ema_21_slope"))

        sh = struct.get("swing_high")
        sl = struct.get("swing_low")

        if sh is None or sl is None:
            return self._neutral("داده کافی نیست")

        # Count recent consecutive HH/HL or LH/LL
        high_labels = struct.get("high_label", pd.Series())
        low_labels = struct.get("low_label", pd.Series())

        recent_highs = high_labels[high_labels != ""].tail(4).tolist()
        recent_lows = low_labels[low_labels != ""].tail(4).tolist()

        # Bullish stair: HH + HL sequence
        hh_count = sum(1 for x in recent_highs if x == "HH")
        hl_count = sum(1 for x in recent_lows if x == "HL")

        # Bearish stair: LH + LL sequence
        lh_count = sum(1 for x in recent_highs if x == "LH")
        ll_count = sum(1 for x in recent_lows if x == "LL")

        confidence = 0
        signals = []

        if hh_count >= 2 and hl_count >= 2:
            confidence += 40
            signals.append(f"{hh_count} سقف بالاتر + {hl_count} کف بالاتر")
            if adx and adx > 25:
                confidence += 20
                signals.append("ADX قوی")
            if slope21 and slope21 > 0:
                confidence += 15

            if confidence >= 45:
                return self._make_result(
                    Signal.BUY, confidence,
                    f"الگوی پله‌ای صعودی: {' | '.join(signals)}",
                    f"Bullish stair: {hh_count}HH+{hl_count}HL",
                    {"hh": hh_count, "hl": hl_count, "adx": round(adx or 0, 1)}
                )

        if lh_count >= 2 and ll_count >= 2:
            confidence = 40
            signals = [f"{lh_count} سقف پایین‌تر + {ll_count} کف پایین‌تر"]
            if adx and adx > 25:
                confidence += 20
            if slope21 and slope21 < 0:
                confidence += 15

            if confidence >= 45:
                return self._make_result(
                    Signal.SELL, confidence,
                    f"الگوی پله‌ای نزولی: {' | '.join(signals)}",
                    f"Bearish stair: {lh_count}LH+{ll_count}LL",
                    {"lh": lh_count, "ll": ll_count}
                )

        return self._neutral("الگوی پله‌ای واضح نیست")
