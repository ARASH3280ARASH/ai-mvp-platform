"""
Whilber-AI MVP - Strategy Cat 13: Smart Money Concepts (SMC)
===============================================================
Order Blocks, Fair Value Gaps (FVG), Liquidity Sweeps.
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


# ── Order Block Detection ───────────────────────────────────────

def find_order_blocks(df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
    """
    Order Block: last opposing candle before a strong move.
    Bullish OB: last bearish candle before strong bullish move
    Bearish OB: last bullish candle before strong bearish move
    """
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    obs = []

    atr = (h - l).rolling(14).mean()
    recent = slice(-lookback, None)

    for i in range(-lookback + 3, -1):
        if abs(i) >= len(df):
            continue

        body = abs(c.iloc[i] - o.iloc[i])
        avg_atr = atr.iloc[i] if not pd.isna(atr.iloc[i]) else 0

        if avg_atr == 0:
            continue

        # Strong bullish candle (body > 1.5x ATR)
        if c.iloc[i] > o.iloc[i] and body > 1.5 * avg_atr:
            # Look for bearish candle before
            if c.iloc[i-1] < o.iloc[i-1]:
                obs.append({
                    "type": "bullish",
                    "ob_high": max(o.iloc[i-1], c.iloc[i-1]),
                    "ob_low": min(o.iloc[i-1], c.iloc[i-1]),
                    "bar_idx": len(df) + i - 1,
                    "strength": body / avg_atr,
                })

        # Strong bearish candle
        if c.iloc[i] < o.iloc[i] and body > 1.5 * avg_atr:
            if c.iloc[i-1] > o.iloc[i-1]:
                obs.append({
                    "type": "bearish",
                    "ob_high": max(o.iloc[i-1], c.iloc[i-1]),
                    "ob_low": min(o.iloc[i-1], c.iloc[i-1]),
                    "bar_idx": len(df) + i - 1,
                    "strength": body / avg_atr,
                })

    return obs


# ── Fair Value Gap (FVG / Imbalance) ───────────────────────────

def find_fvg(df: pd.DataFrame, lookback: int = 30) -> List[Dict]:
    """
    FVG: gap between candle 1's high/low and candle 3's low/high
    (candle 2 is the big move candle).
    """
    h, l = df["high"], df["low"]
    fvgs = []

    for i in range(-lookback + 2, -1):
        if abs(i) >= len(df) or abs(i-2) >= len(df):
            continue

        # Bullish FVG: candle 3 low > candle 1 high
        if l.iloc[i] > h.iloc[i-2]:
            fvgs.append({
                "type": "bullish",
                "gap_high": l.iloc[i],
                "gap_low": h.iloc[i-2],
                "bar_idx": len(df) + i - 1,
            })

        # Bearish FVG: candle 3 high < candle 1 low
        if h.iloc[i] < l.iloc[i-2]:
            fvgs.append({
                "type": "bearish",
                "gap_high": l.iloc[i-2],
                "gap_low": h.iloc[i],
                "bar_idx": len(df) + i - 1,
            })

    return fvgs


# ── Liquidity Sweep ─────────────────────────────────────────────

def detect_liquidity_sweep(df: pd.DataFrame, lookback: int = 30) -> Dict:
    """
    Liquidity sweep: price takes out a previous high/low then reverses.
    """
    h, l, c, o = df["high"], df["low"], df["close"], df["open"]

    # Check if latest candle swept a previous high then closed below it
    recent_highs = h.iloc[-lookback:-1]
    recent_lows = l.iloc[-lookback:-1]
    prev_high = recent_highs.max()
    prev_low = recent_lows.min()

    curr_h = h.iloc[-1]
    curr_l = l.iloc[-1]
    curr_c = c.iloc[-1]

    result = {"bull_sweep": False, "bear_sweep": False}

    # Bearish sweep: went above prev high but closed below (stop hunt)
    if curr_h > prev_high and curr_c < prev_high:
        result["bear_sweep"] = True

    # Bullish sweep: went below prev low but closed above (stop hunt)
    if curr_l < prev_low and curr_c > prev_low:
        result["bull_sweep"] = True

    return result


class SmartMoneyStrategy(BaseStrategy):
    STRATEGY_ID = "smart_money"
    STRATEGY_NAME_FA = "اسمارت مانی"
    STRATEGY_NAME_EN = "Smart Money Concepts"
    CATEGORY = "smart_money"
    REQUIRED_INDICATORS = ["structure", "candle"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        struct = indicators.get("structure", {})
        candle = indicators.get("candle", {})

        price = df["close"].iloc[-1]
        bos = self.last(struct.get("bos"))
        choch = self.last(struct.get("choch"))

        # Find SMC elements
        obs = find_order_blocks(df, 50)
        fvgs = find_fvg(df, 30)
        sweep = detect_liquidity_sweep(df, 30)

        confidence = 0
        signals = []

        # ── Bullish SMC ─────────────────────────────────────
        # Bullish OB near price
        bull_obs = [ob for ob in obs if ob["type"] == "bullish"]
        near_bull_ob = None
        for ob in bull_obs:
            if ob["ob_low"] <= price <= ob["ob_high"] * 1.002:
                near_bull_ob = ob
                break

        if near_bull_ob:
            confidence += 25
            signals.append(f"قیمت در اوردر بلاک صعودی ({near_bull_ob['ob_low']:.5f}~{near_bull_ob['ob_high']:.5f})")

        # Bullish FVG
        bull_fvgs = [f for f in fvgs if f["type"] == "bullish"]
        near_bull_fvg = None
        for fvg in bull_fvgs:
            if fvg["gap_low"] <= price <= fvg["gap_high"]:
                near_bull_fvg = fvg
                break

        if near_bull_fvg:
            confidence += 20
            signals.append("قیمت در FVG صعودی")

        if sweep["bull_sweep"]:
            confidence += 25
            signals.append("جمع‌آوری نقدینگی زیر کف (Bull Sweep)")

        if bos == 1:
            confidence += 15
            signals.append("شکست ساختار صعودی")

        if choch == 1:
            confidence += 15
            signals.append("CHoCH صعودی")

        if confidence >= 40:
            return self._make_result(Signal.BUY, min(confidence, 90),
                f"اسمارت مانی صعودی: {' | '.join(signals)}",
                f"SMC bullish: OB+FVG+sweep",
                {"order_blocks": len(bull_obs), "fvgs": len(bull_fvgs),
                 "sweep": sweep["bull_sweep"]})

        # ── Bearish SMC ─────────────────────────────────────
        confidence = 0
        signals = []

        bear_obs = [ob for ob in obs if ob["type"] == "bearish"]
        near_bear_ob = None
        for ob in bear_obs:
            if ob["ob_low"] * 0.998 <= price <= ob["ob_high"]:
                near_bear_ob = ob
                break

        if near_bear_ob:
            confidence += 25
            signals.append(f"قیمت در اوردر بلاک نزولی")

        bear_fvgs = [f for f in fvgs if f["type"] == "bearish"]
        for fvg in bear_fvgs:
            if fvg["gap_low"] <= price <= fvg["gap_high"]:
                confidence += 20
                signals.append("قیمت در FVG نزولی")
                break

        if sweep["bear_sweep"]:
            confidence += 25
            signals.append("جمع‌آوری نقدینگی بالای سقف (Bear Sweep)")

        if bos == -1:
            confidence += 15
            signals.append("شکست ساختار نزولی")

        if choch == -1:
            confidence += 15
            signals.append("CHoCH نزولی")

        if confidence >= 40:
            return self._make_result(Signal.SELL, min(confidence, 90),
                f"اسمارت مانی نزولی: {' | '.join(signals)}",
                f"SMC bearish",
                {"order_blocks": len(bear_obs), "fvgs": len(bear_fvgs),
                 "sweep": sweep["bear_sweep"]})

        return self._neutral(
            "سیگنال اسمارت مانی واضح نیست",
            "No clear SMC signal",
            {"bull_obs": len(bull_obs), "bear_obs": len(bear_obs),
             "bull_fvgs": len(bull_fvgs), "bear_fvgs": len(bear_fvgs)})
