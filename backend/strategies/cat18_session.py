"""
Whilber-AI MVP - Strategy Cat 18: Session Analysis
=====================================================
Trading session patterns (Asian, London, New York).
"""

import numpy as np
import pandas as pd
from typing import Dict
from datetime import datetime
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


# Session times (MT5 server time is usually UTC+2 or UTC+3)
SESSIONS = {
    "asian":  {"start": 0,  "end": 8},    # 00:00-08:00 server
    "london": {"start": 8,  "end": 16},   # 08:00-16:00
    "newyork":{"start": 13, "end": 21},   # 13:00-21:00
}

SESSION_FA = {
    "asian": "آسیا",
    "london": "لندن",
    "newyork": "نیویورک",
}


def detect_session_range(df: pd.DataFrame, session: str,
                         lookback_days: int = 3) -> Dict:
    """Calculate average session range and key levels."""
    s = SESSIONS[session]
    times = pd.to_datetime(df["time"])
    hours = times.dt.hour

    session_mask = (hours >= s["start"]) & (hours < s["end"])
    session_bars = df[session_mask]

    if len(session_bars) < 5:
        return {"available": False}

    # Recent session high/low
    recent = session_bars.tail(20)
    session_high = recent["high"].max()
    session_low = recent["low"].min()
    avg_range = (recent["high"] - recent["low"]).mean()

    return {
        "available": True,
        "high": session_high,
        "low": session_low,
        "avg_range": avg_range,
    }


def get_current_session(hour: int) -> str:
    """Determine current session from hour."""
    for name, times in SESSIONS.items():
        if times["start"] <= hour < times["end"]:
            return name
    return "off_hours"


class SessionAnalysis(BaseStrategy):
    STRATEGY_ID = "session_analysis"
    STRATEGY_NAME_FA = "تحلیل سشن"
    STRATEGY_NAME_EN = "Session Analysis"
    CATEGORY = "session"
    REQUIRED_INDICATORS = ["trend", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        trend = indicators.get("trend", {})
        candle = indicators.get("candle", {})

        price = df["close"].iloc[-1]
        last_time = pd.to_datetime(df["time"].iloc[-1])
        current_hour = last_time.hour

        current_session = get_current_session(current_hour)
        regime = self.last(trend.get("regime"))
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))

        # Get Asian session range (for London/NY breakout)
        asian = detect_session_range(df, "asian")

        if not asian.get("available"):
            return self._neutral("داده سشن آسیا کافی نیست")

        confidence = 0
        signals = []
        session_fa = SESSION_FA.get(current_session, current_session)
        signals.append(f"سشن فعلی: {session_fa}")

        # London/NY breakout of Asian range
        if current_session in ("london", "newyork") and asian["available"]:
            asian_h = asian["high"]
            asian_l = asian["low"]

            # Bullish: break above Asian high
            if price > asian_h:
                confidence += 30
                signals.append(f"شکست بالای رنج آسیا ({asian_h:.5f})")

                if regime == 1:
                    confidence += 15
                    signals.append("همسو با روند صعودی")
                if pin == 1 or engulf == 1:
                    confidence += 10

                if confidence >= 40:
                    return self._make_result(Signal.BUY, min(confidence, 80),
                        f"شکست سشن صعودی: {' | '.join(signals)}",
                        f"Bullish session breakout above Asian range",
                        {"session": current_session, "asian_high": round(asian_h, 5),
                         "asian_low": round(asian_l, 5)})

            # Bearish: break below Asian low
            if price < asian_l:
                confidence = 30
                signals_b = [f"سشن: {session_fa}", f"شکست زیر رنج آسیا ({asian_l:.5f})"]

                if regime == -1:
                    confidence += 15
                    signals_b.append("همسو با روند نزولی")
                if pin == -1 or engulf == -1:
                    confidence += 10

                if confidence >= 40:
                    return self._make_result(Signal.SELL, min(confidence, 80),
                        f"شکست سشن نزولی: {' | '.join(signals_b)}",
                        f"Bearish session breakout below Asian range",
                        {"session": current_session, "asian_high": round(asian_h, 5),
                         "asian_low": round(asian_l, 5)})

            # Inside Asian range
            return self._neutral(
                f"سشن {session_fa} | داخل رنج آسیا ({asian_l:.5f}~{asian_h:.5f})",
                f"{current_session} session, inside Asian range",
                {"session": current_session, "asian_high": round(asian_h, 5),
                 "asian_low": round(asian_l, 5), "position": "inside"})

        return self._neutral(
            f"سشن {session_fa} | رنج آسیا: {asian['avg_range']:.5f}",
            f"Session: {current_session}",
            {"session": current_session})
