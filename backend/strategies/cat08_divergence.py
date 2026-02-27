"""
Whilber-AI MVP - Strategy Cat 8: Divergence
==============================================
Regular + Hidden divergence on RSI and MACD.
"""

import numpy as np
import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def _swing_highs(s: pd.Series, left: int = 5, right: int = 5) -> pd.Series:
    r = pd.Series(np.nan, index=s.index)
    for i in range(left, len(s) - right):
        w = s.iloc[i - left:i + right + 1]
        if s.iloc[i] == w.max():
            r.iloc[i] = s.iloc[i]
    return r


def _swing_lows(s: pd.Series, left: int = 5, right: int = 5) -> pd.Series:
    r = pd.Series(np.nan, index=s.index)
    for i in range(left, len(s) - right):
        w = s.iloc[i - left:i + right + 1]
        if s.iloc[i] == w.min():
            r.iloc[i] = s.iloc[i]
    return r


def detect_divergence(price: pd.Series, osc: pd.Series,
                      left: int = 5, right: int = 3,
                      lookback: int = 60) -> Dict[str, int]:
    """
    Regular Bullish:  Price LL + Osc HL → reversal up
    Regular Bearish:  Price HH + Osc LH → reversal down
    Hidden Bullish:   Price HL + Osc LL → continuation up
    Hidden Bearish:   Price LH + Osc HH → continuation down
    """
    result = {"reg_bull": 0, "reg_bear": 0, "hid_bull": 0, "hid_bear": 0}

    sl = slice(-lookback, None)
    p_lows = _swing_lows(price, left, right)[sl].dropna()
    o_lows = _swing_lows(osc, left, right)[sl].dropna()
    p_highs = _swing_highs(price, left, right)[sl].dropna()
    o_highs = _swing_highs(osc, left, right)[sl].dropna()

    if len(p_lows) >= 2 and len(o_lows) >= 2:
        pl1, pl2 = p_lows.iloc[-2], p_lows.iloc[-1]
        ol1, ol2 = o_lows.iloc[-2], o_lows.iloc[-1]
        if pl2 < pl1 and ol2 > ol1:
            result["reg_bull"] = 1
        if pl2 > pl1 and ol2 < ol1:
            result["hid_bull"] = 1

    if len(p_highs) >= 2 and len(o_highs) >= 2:
        ph1, ph2 = p_highs.iloc[-2], p_highs.iloc[-1]
        oh1, oh2 = o_highs.iloc[-2], o_highs.iloc[-1]
        if ph2 > ph1 and oh2 < oh1:
            result["reg_bear"] = 1
        if ph2 < ph1 and oh2 > oh1:
            result["hid_bear"] = 1

    return result


class DivergenceStrategy(BaseStrategy):
    STRATEGY_ID = "divergence"
    STRATEGY_NAME_FA = "واگرایی"
    STRATEGY_NAME_EN = "Divergence"
    CATEGORY = "divergence"
    REQUIRED_INDICATORS = ["osc", "macd"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        osc = indicators.get("osc", {})
        macd_ind = indicators.get("macd", {})
        close = df["close"]

        rsi_s = osc.get("rsi_14")
        macd_h = macd_ind.get("macd_hist")

        if rsi_s is None:
            return self._neutral("داده کافی نیست")

        confidence = 0
        signals = []

        # RSI divergence
        rsi_div = detect_divergence(close, rsi_s)

        if rsi_div["reg_bull"]:
            confidence += 40
            signals.append("واگرایی معمولی صعودی RSI (قیمت کف پایین‌تر، RSI کف بالاتر)")
        if rsi_div["reg_bear"]:
            confidence += 40
            signals.append("واگرایی معمولی نزولی RSI (قیمت سقف بالاتر، RSI سقف پایین‌تر)")
        if rsi_div["hid_bull"]:
            confidence += 25
            signals.append("واگرایی مخفی صعودی RSI (ادامه روند بالا)")
        if rsi_div["hid_bear"]:
            confidence += 25
            signals.append("واگرایی مخفی نزولی RSI (ادامه روند پایین)")

        # MACD divergence
        if macd_h is not None:
            macd_div = detect_divergence(close, macd_h)
            if macd_div["reg_bull"]:
                confidence += 30
                signals.append("واگرایی معمولی صعودی MACD")
            if macd_div["reg_bear"]:
                confidence += 30
                signals.append("واگرایی معمولی نزولی MACD")
            if macd_div["hid_bull"]:
                confidence += 20
                signals.append("واگرایی مخفی صعودی MACD")
            if macd_div["hid_bear"]:
                confidence += 20
                signals.append("واگرایی مخفی نزولی MACD")

        if not signals:
            return self._neutral("واگرایی یافت نشد")

        # Determine direction
        bull_score = (rsi_div["reg_bull"] * 40 + rsi_div["hid_bull"] * 25 +
                      (30 if macd_h is not None and detect_divergence(close, macd_h)["reg_bull"] else 0) +
                      (20 if macd_h is not None and detect_divergence(close, macd_h)["hid_bull"] else 0))
        bear_score = (rsi_div["reg_bear"] * 40 + rsi_div["hid_bear"] * 25 +
                      (30 if macd_h is not None and detect_divergence(close, macd_h)["reg_bear"] else 0) +
                      (20 if macd_h is not None and detect_divergence(close, macd_h)["hid_bear"] else 0))

        if bull_score > bear_score and bull_score >= 25:
            return self._make_result(Signal.BUY, min(bull_score, 90),
                f"واگرایی صعودی: {' | '.join(signals)}",
                f"Bullish divergence detected",
                {"rsi_div": rsi_div})

        if bear_score > bull_score and bear_score >= 25:
            return self._make_result(Signal.SELL, min(bear_score, 90),
                f"واگرایی نزولی: {' | '.join(signals)}",
                f"Bearish divergence detected",
                {"rsi_div": rsi_div})

        return self._neutral(f"واگرایی ضعیف: {' | '.join(signals)}")
