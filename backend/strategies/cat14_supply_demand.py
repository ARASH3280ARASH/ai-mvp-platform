"""
Whilber-AI MVP - Strategy Cat 14: Supply / Demand Zones
==========================================================
Auto-detect supply/demand zones from explosive moves.
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal


def find_zones(df: pd.DataFrame, lookback: int = 80,
               atr_mult: float = 1.5) -> Dict[str, List[Dict]]:
    """
    Find supply and demand zones.
    Demand zone: consolidation area before explosive bullish move
    Supply zone: consolidation area before explosive bearish move
    """
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    atr = (h - l).rolling(14).mean()

    demand_zones = []
    supply_zones = []

    start = max(-lookback, -len(df) + 15)

    for i in range(start, -2):
        idx = len(df) + i
        if idx < 3 or idx >= len(df) - 1:
            continue

        curr_body = abs(c.iloc[i] - o.iloc[i])
        avg_atr = atr.iloc[i]
        if pd.isna(avg_atr) or avg_atr == 0:
            continue

        # Explosive bullish move
        if c.iloc[i] > o.iloc[i] and curr_body > atr_mult * avg_atr:
            # The zone is the candle(s) before the move (base)
            zone_high = max(o.iloc[i-1], c.iloc[i-1], o.iloc[i])
            zone_low = min(o.iloc[i-1], c.iloc[i-1], l.iloc[i-1])

            # Check zone hasn't been broken
            future = c.iloc[i+1:]
            if len(future) > 0 and future.min() > zone_low * 0.998:
                demand_zones.append({
                    "high": zone_high,
                    "low": zone_low,
                    "strength": curr_body / avg_atr,
                    "bars_ago": abs(i),
                    "fresh": True,
                })

        # Explosive bearish move
        if c.iloc[i] < o.iloc[i] and curr_body > atr_mult * avg_atr:
            zone_high = max(o.iloc[i-1], c.iloc[i-1], h.iloc[i-1])
            zone_low = min(o.iloc[i-1], c.iloc[i-1], o.iloc[i])

            future = c.iloc[i+1:]
            if len(future) > 0 and future.max() < zone_high * 1.002:
                supply_zones.append({
                    "high": zone_high,
                    "low": zone_low,
                    "strength": curr_body / avg_atr,
                    "bars_ago": abs(i),
                    "fresh": True,
                })

    # Sort by strength
    demand_zones.sort(key=lambda x: x["strength"], reverse=True)
    supply_zones.sort(key=lambda x: x["strength"], reverse=True)

    return {
        "demand": demand_zones[:5],  # Top 5
        "supply": supply_zones[:5],
    }


class SupplyDemandStrategy(BaseStrategy):
    STRATEGY_ID = "supply_demand"
    STRATEGY_NAME_FA = "عرضه و تقاضا"
    STRATEGY_NAME_EN = "Supply & Demand Zones"
    CATEGORY = "supply_demand"
    REQUIRED_INDICATORS = ["candle", "osc"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        candle = indicators.get("candle", {})
        osc = indicators.get("osc", {})

        price = df["close"].iloc[-1]
        pin = self.last(candle.get("pin_bar"))
        engulf = self.last(candle.get("engulfing"))
        rsi = self.last(osc.get("rsi_14"))

        zones = find_zones(df, lookback=80)

        demand = zones["demand"]
        supply = zones["supply"]

        confidence = 0
        signals = []

        # Check if price is in a demand zone
        in_demand = None
        for z in demand:
            if z["low"] <= price <= z["high"] * 1.002:
                in_demand = z
                break

        if in_demand:
            confidence += 30
            signals.append(f"قیمت در ناحیه تقاضا ({in_demand['low']:.5f}~{in_demand['high']:.5f})")

            if in_demand["strength"] > 2.0:
                confidence += 10
                signals.append(f"ناحیه قوی (force={in_demand['strength']:.1f}x)")

            if in_demand["fresh"]:
                confidence += 10
                signals.append("ناحیه تازه (هنوز تست نشده)")

            if pin == 1 or engulf == 1:
                confidence += 15
                signals.append("تأیید کندلی صعودی")

            if rsi and rsi < 40:
                confidence += 10

            if confidence >= 40:
                return self._make_result(Signal.BUY, min(confidence, 85),
                    f"ناحیه تقاضا: {' | '.join(signals)}",
                    f"Demand zone entry",
                    {"zone_low": round(in_demand["low"], 5),
                     "zone_high": round(in_demand["high"], 5),
                     "strength": round(in_demand["strength"], 2),
                     "total_demand": len(demand), "total_supply": len(supply)})

        # Check if price is in a supply zone
        in_supply = None
        for z in supply:
            if z["low"] * 0.998 <= price <= z["high"]:
                in_supply = z
                break

        if in_supply:
            confidence = 30
            signals = [f"قیمت در ناحیه عرضه ({in_supply['low']:.5f}~{in_supply['high']:.5f})"]

            if in_supply["strength"] > 2.0:
                confidence += 10
                signals.append(f"ناحیه قوی")

            if in_supply["fresh"]:
                confidence += 10
                signals.append("ناحیه تازه")

            if pin == -1 or engulf == -1:
                confidence += 15
                signals.append("تأیید کندلی نزولی")

            if rsi and rsi > 60:
                confidence += 10

            if confidence >= 40:
                return self._make_result(Signal.SELL, min(confidence, 85),
                    f"ناحیه عرضه: {' | '.join(signals)}",
                    f"Supply zone entry",
                    {"zone_low": round(in_supply["low"], 5),
                     "zone_high": round(in_supply["high"], 5),
                     "total_demand": len(demand), "total_supply": len(supply)})

        # Not in any zone
        # Find nearest zones
        nearest_demand = None
        nearest_supply = None
        for z in demand:
            if price > z["high"]:
                dist = (price - z["high"]) / price * 100
                nearest_demand = {"zone": z, "dist_pct": dist}
                break
        for z in supply:
            if price < z["low"]:
                dist = (z["low"] - price) / price * 100
                nearest_supply = {"zone": z, "dist_pct": dist}
                break

        details = {"total_demand": len(demand), "total_supply": len(supply)}
        msg_parts = [f"تعداد نواحی: {len(demand)} تقاضا، {len(supply)} عرضه"]

        if nearest_demand:
            msg_parts.append(f"نزدیک‌ترین تقاضا: {nearest_demand['dist_pct']:.1f}% پایین")
            details["nearest_demand_dist"] = round(nearest_demand["dist_pct"], 2)
        if nearest_supply:
            msg_parts.append(f"نزدیک‌ترین عرضه: {nearest_supply['dist_pct']:.1f}% بالا")
            details["nearest_supply_dist"] = round(nearest_supply["dist_pct"], 2)

        return self._neutral(
            f"خارج از نواحی S/D | {' | '.join(msg_parts)}",
            "Not in S/D zone",
            details)
