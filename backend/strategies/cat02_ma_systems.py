"""
Whilber-AI MVP - Strategy Category 2: MA Systems
===================================================
"""

import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


class MACrossover(BaseStrategy):
    STRATEGY_ID = "ma_crossover"
    STRATEGY_NAME_FA = "کراس میانگین"
    STRATEGY_NAME_EN = "MA Crossover"
    CATEGORY = "ma_systems"
    REQUIRED_INDICATORS = ["ma", "trend"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        ma = indicators.get("ma", {})
        trend = indicators.get("trend", {})

        cross_9_21 = self.last(ma.get("cross_9_21"))
        cross_50_200 = self.last(ma.get("cross_50_200"))
        cross_21_50 = self.last(ma.get("cross_21_50"))
        adx = self.last(trend.get("adx"))
        ema9 = self.last(ma.get("ema_9"))
        ema21 = self.last(ma.get("ema_21"))
        ema50 = self.last(ma.get("ema_50"))

        if ema9 is None or ema21 is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []
        direction = 0

        # Fast cross (9/21)
        if cross_9_21 == 1:
            confidence += 30
            signals.append("کراس صعودی EMA 9/21")
            direction = 1
        elif cross_9_21 == -1:
            confidence += 30
            signals.append("کراس نزولی EMA 9/21")
            direction = -1

        # Medium cross (21/50)
        if cross_21_50 == 1:
            confidence += 20
            signals.append("کراس صعودی EMA 21/50")
            if direction == 0: direction = 1
        elif cross_21_50 == -1:
            confidence += 20
            signals.append("کراس نزولی EMA 21/50")
            if direction == 0: direction = -1

        # Golden/Death cross (50/200)
        if cross_50_200 == 1:
            confidence += 25
            signals.append("کراس طلایی (Golden Cross)")
            if direction == 0: direction = 1
        elif cross_50_200 == -1:
            confidence += 25
            signals.append("کراس مرگ (Death Cross)")
            if direction == 0: direction = -1

        # No recent cross? Check alignment
        if confidence == 0:
            if ema9 > ema21:
                pos = self.last(ma.get("ema_9_position"))
                if pos == 1:
                    confidence += 20
                    signals.append("EMA9 بالای EMA21 (روند صعودی ادامه‌دار)")
                    direction = 1
            elif ema9 < ema21:
                confidence += 20
                signals.append("EMA9 زیر EMA21 (روند نزولی ادامه‌دار)")
                direction = -1

        # ADX filter
        if adx and adx > 25:
            confidence += 15
            signals.append(f"ADX قوی ({adx:.0f})")
        elif adx and adx < 20:
            confidence -= 10

        if confidence >= 40 and direction != 0:
            sig = Signal.BUY if direction == 1 else Signal.SELL
            return self._make_result(sig, confidence,
                f"سیگنال کراس MA: {' | '.join(signals)}",
                f"MA Cross signal: dir={direction}",
                {"ema9": round(ema9, 5), "ema21": round(ema21, 5)})

        return self._neutral("کراس جدیدی نیست")


class TripleMA(BaseStrategy):
    STRATEGY_ID = "triple_ma"
    STRATEGY_NAME_FA = "سه‌گانه MA"
    STRATEGY_NAME_EN = "Triple MA Ribbon"
    CATEGORY = "ma_systems"
    REQUIRED_INDICATORS = ["ma", "trend"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        ma = indicators.get("ma", {})
        trend = indicators.get("trend", {})

        stack = self.last(ma.get("ma_stack"))
        ema9 = self.last(ma.get("ema_9"))
        ema21 = self.last(ma.get("ema_21"))
        ema50 = self.last(ma.get("ema_50"))
        slope9 = self.last(ma.get("ema_9_slope"))
        slope21 = self.last(ma.get("ema_21_slope"))
        slope50 = self.last(ma.get("ema_50_slope"))
        adx = self.last(trend.get("adx"))

        if ema9 is None or ema50 is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        if stack == 1:
            confidence += 35
            signals.append("MA Stack صعودی (9>21>50)")

            if slope9 and slope9 > 0 and slope21 and slope21 > 0:
                confidence += 15
                signals.append("شیب همه MA‌ها صعودی")

            # Ribbon width (spread between fast and slow)
            spread = abs(ema9 - ema50) / ema50 * 100
            if spread > 0.1:
                confidence += 10
                signals.append("فاصله MA‌ها مناسب")

            if adx and adx > 25:
                confidence += 15

            if confidence >= 45:
                return self._make_result(Signal.BUY, confidence,
                    f"ریبون صعودی: {' | '.join(signals)}", "Bullish ribbon",
                    {"stack": stack, "spread_pct": round(spread, 3)})

        elif stack == -1:
            confidence += 35
            signals.append("MA Stack نزولی (9<21<50)")

            if slope9 and slope9 < 0 and slope21 and slope21 < 0:
                confidence += 15
                signals.append("شیب همه MA‌ها نزولی")

            if adx and adx > 25:
                confidence += 15

            if confidence >= 45:
                return self._make_result(Signal.SELL, confidence,
                    f"ریبون نزولی: {' | '.join(signals)}", "Bearish ribbon",
                    {"stack": stack})

        return self._neutral("MA‌ها هم‌جهت نیستند")


class MADynamicSR(BaseStrategy):
    STRATEGY_ID = "ma_dynamic_sr"
    STRATEGY_NAME_FA = "حمایت/مقاومت MA"
    STRATEGY_NAME_EN = "MA Dynamic S/R"
    CATEGORY = "ma_systems"
    REQUIRED_INDICATORS = ["ma", "trend", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        ma = indicators.get("ma", {})
        trend = indicators.get("trend", {})
        candle = indicators.get("candle", {})

        regime = self.last(trend.get("regime"))
        dist21 = self.last(ma.get("ema_21_distance"))
        dist50 = self.last(ma.get("ema_50_distance"))
        ema21 = self.last(ma.get("ema_21"))
        ema50 = self.last(ma.get("ema_50"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))
        price = df["close"].iloc[-1]
        low = df["low"].iloc[-1]
        high = df["high"].iloc[-1]

        if ema21 is None or ema50 is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # Bullish: price bouncing off MA as support
        if regime == 1:
            # Touch EMA21 from above
            if ema21 and low <= ema21 * 1.002 and price > ema21:
                confidence += 35
                signals.append("تماس با EMA21 به عنوان حمایت")
            elif ema50 and low <= ema50 * 1.003 and price > ema50:
                confidence += 30
                signals.append("تماس با EMA50 به عنوان حمایت")

            if pin == 1 or engulf == 1:
                confidence += 20
                signals.append("تأیید کندلی صعودی")

            if confidence >= 40:
                return self._make_result(Signal.BUY, confidence,
                    f"برگشت از MA حمایتی: {' | '.join(signals)}",
                    "Bounce from MA support",
                    {"ema21": round(ema21, 5), "price": round(price, 5)})

        # Bearish: price rejecting from MA as resistance
        if regime == -1:
            if ema21 and high >= ema21 * 0.998 and price < ema21:
                confidence += 35
                signals.append("رد شدن از EMA21 به عنوان مقاومت")
            elif ema50 and high >= ema50 * 0.997 and price < ema50:
                confidence += 30
                signals.append("رد شدن از EMA50 به عنوان مقاومت")

            if pin == -1 or engulf == -1:
                confidence += 20
                signals.append("تأیید کندلی نزولی")

            if confidence >= 40:
                return self._make_result(Signal.SELL, confidence,
                    f"رد از MA مقاومتی: {' | '.join(signals)}",
                    "Rejection from MA resistance",
                    {"ema21": round(ema21, 5)})

        return self._neutral("تعامل مشخصی با MA وجود ندارد")
