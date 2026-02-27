"""
Whilber-AI MVP - Strategy Category 4: Volatility
===================================================
"""

import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


class BBBounce(BaseStrategy):
    STRATEGY_ID = "bb_bounce"
    STRATEGY_NAME_FA = "برگشت از بولینگر"
    STRATEGY_NAME_EN = "Bollinger Bounce"
    CATEGORY = "volatility"
    REQUIRED_INDICATORS = ["vol", "osc", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        vol = indicators.get("vol", {})
        osc = indicators.get("osc", {})
        candle = indicators.get("candle", {})

        bb_pos = self.last(vol.get("bb_position"))
        pct_b = self.last(vol.get("bb_percent_b"))
        rsi = self.last(osc.get("rsi_14"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))
        price = df["close"].iloc[-1]
        bb_lower = self.last(vol.get("bb_lower"))
        bb_upper = self.last(vol.get("bb_upper"))

        if pct_b is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # Bullish: bounce from lower band
        if bb_pos == -2 or (pct_b is not None and pct_b < 10):
            confidence += 30
            signals.append(f"قیمت نزدیک باند پایین (%B={pct_b:.0f})")
            if rsi and rsi < 35:
                confidence += 15
                signals.append("RSI اشباع فروش")
            if pin == 1 or engulf == 1:
                confidence += 20
                signals.append("تأیید کندلی صعودی")
            if confidence >= 40:
                return self._make_result(Signal.BUY, confidence,
                    f"برگشت از باند پایین: {' | '.join(signals)}",
                    f"BB lower bounce: %B={pct_b:.0f}",
                    {"bb_pct_b": round(pct_b, 1), "rsi": round(rsi or 0, 1)})

        # Bearish: rejection from upper band
        if bb_pos == 2 or (pct_b is not None and pct_b > 90):
            confidence = 30
            signals = [f"قیمت نزدیک باند بالا (%B={pct_b:.0f})"]
            if rsi and rsi > 65:
                confidence += 15
                signals.append("RSI اشباع خرید")
            if pin == -1 or engulf == -1:
                confidence += 20
                signals.append("تأیید کندلی نزولی")
            if confidence >= 40:
                return self._make_result(Signal.SELL, confidence,
                    f"رد از باند بالا: {' | '.join(signals)}",
                    f"BB upper rejection: %B={pct_b:.0f}",
                    {"bb_pct_b": round(pct_b, 1)})

        return self._neutral(f"قیمت در میانه بولینگر (%B={pct_b:.0f})")


class SqueezePlay(BaseStrategy):
    STRATEGY_ID = "squeeze_play"
    STRATEGY_NAME_FA = "فشردگی → انفجار"
    STRATEGY_NAME_EN = "Squeeze Play"
    CATEGORY = "volatility"
    REQUIRED_INDICATORS = ["vol", "ma", "trend"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        vol = indicators.get("vol", {})
        ma = indicators.get("ma", {})
        trend = indicators.get("trend", {})

        squeeze = self.last(vol.get("squeeze_on"))
        squeeze_prev = self.prev(vol.get("squeeze_on"))
        squeeze_val = self.last(vol.get("squeeze_val"))
        bb_bw = self.last(vol.get("bb_bandwidth"))
        bb_bw_prev = self.prev(vol.get("bb_bandwidth"), 3)
        slope9 = self.last(ma.get("ema_9_slope"))
        regime = self.last(trend.get("regime"))

        if squeeze is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # Squeeze release
        if squeeze_prev == 1 and squeeze == 0:
            confidence += 40
            signals.append("خروج از فشردگی (Squeeze Release!)")

            if squeeze_val and squeeze_val > 0:
                confidence += 20
                signals.append("مومنتوم صعودی")
                if bb_bw and bb_bw_prev and bb_bw > bb_bw_prev:
                    confidence += 10
                    signals.append("باندویدث در حال افزایش")
                return self._make_result(Signal.BUY, confidence,
                    f"انفجار صعودی: {' | '.join(signals)}",
                    f"Squeeze release bullish",
                    {"squeeze_val": round(squeeze_val, 6), "bandwidth": round(bb_bw or 0, 4)})

            elif squeeze_val and squeeze_val < 0:
                confidence += 20
                signals.append("مومنتوم نزولی")
                return self._make_result(Signal.SELL, confidence,
                    f"انفجار نزولی: {' | '.join(signals)}",
                    f"Squeeze release bearish",
                    {"squeeze_val": round(squeeze_val, 6)})

        # Currently in squeeze (alert)
        if squeeze == 1:
            return self._neutral(
                f"فشردگی فعال — منتظر شکست باشید (BW={bb_bw:.3f})",
                "Squeeze active, waiting for release",
                {"squeeze_on": True, "bandwidth": round(bb_bw or 0, 4)})

        return self._neutral("فشردگی وجود ندارد")


class SuperTrendFollow(BaseStrategy):
    STRATEGY_ID = "supertrend_follow"
    STRATEGY_NAME_FA = "سوپرترند"
    STRATEGY_NAME_EN = "SuperTrend Follow"
    CATEGORY = "volatility"
    REQUIRED_INDICATORS = ["vol", "trend"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        vol = indicators.get("vol", {})
        trend = indicators.get("trend", {})

        st_dir = self.last(vol.get("supertrend_dir"))
        st_flip = self.last(vol.get("supertrend_flip"))
        psar_dir = self.last(vol.get("psar_dir"))
        psar_flip = self.last(vol.get("psar_flip"))
        adx = self.last(trend.get("adx"))

        if st_dir is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # SuperTrend flip
        if st_flip == 1:
            confidence += 35
            signals.append("تغییر سوپرترند به صعودی")
        elif st_flip == -1:
            confidence += 35
            signals.append("تغییر سوپرترند به نزولی")

        # PSAR confirmation
        if st_dir == 1 and psar_dir == 1:
            confidence += 20
            signals.append("تأیید PSAR صعودی")
        elif st_dir == -1 and psar_dir == -1:
            confidence += 20
            signals.append("تأیید PSAR نزولی")

        # PSAR flip
        if psar_flip == st_dir and psar_flip != 0:
            confidence += 10
            signals.append("PSAR هم تغییر کرد")

        # ADX filter
        if adx and adx > 25:
            confidence += 15
            signals.append(f"ADX قوی ({adx:.0f})")

        if confidence >= 40:
            sig = Signal.BUY if st_dir == 1 else Signal.SELL
            return self._make_result(sig, confidence,
                f"سوپرترند {'صعودی' if st_dir == 1 else 'نزولی'}: {' | '.join(signals)}",
                f"SuperTrend {'bullish' if st_dir == 1 else 'bearish'}",
                {"supertrend_dir": st_dir, "psar_dir": psar_dir, "adx": round(adx or 0, 1)})

        return self._neutral(f"سوپرترند {'صعودی' if st_dir == 1 else 'نزولی'} (ضعیف)")
