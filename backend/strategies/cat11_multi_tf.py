"""
Whilber-AI MVP - Strategy Cat 11: Multi-Timeframe Confirmation
================================================================
Fetches higher TF data and checks alignment with current TF.
"""

import pandas as pd
from typing import Dict
from backend.strategies.base_strategy import BaseStrategy, StrategyResult, Signal
from backend.mt5.data_fetcher import fetch_bars
from backend.indicators import compute_selective


# Higher TF mapping: for each TF, which HTFs to check
HTF_MAP = {
    "M1": ["M15", "H1"],
    "M5": ["H1", "H4"],
    "M15": ["H1", "H4"],
    "M30": ["H4", "D1"],
    "H1": ["H4", "D1"],
    "H4": ["D1"],
    "D1": [],
}


def analyze_htf(symbol: str, timeframe: str) -> Dict:
    """Fetch higher TF and compute quick trend analysis."""
    df = fetch_bars(symbol, timeframe, use_cache=True)  # Cache OK for HTF
    if df is None or len(df) < 50:
        return {"available": False}

    ind = compute_selective(df, ["ma", "trend"])
    ma = ind.get("ma", {})
    trend = ind.get("trend", {})

    regime = trend.get("regime")
    adx = trend.get("adx")
    stack = ma.get("ma_stack")
    ema50_slope = ma.get("ema_50_slope")

    def safe_last(s):
        if s is None or not hasattr(s, 'iloc'): return None
        v = s.iloc[-1]
        return None if pd.isna(v) else v

    r = safe_last(regime)
    direction = 0
    if r == 1: direction = 1
    elif r == -1: direction = -1

    return {
        "available": True,
        "timeframe": timeframe,
        "direction": direction,
        "adx": round(float(safe_last(adx) or 0), 1),
        "stack": safe_last(stack),
        "slope": safe_last(ema50_slope),
    }


class MultiTFConfirmation(BaseStrategy):
    STRATEGY_ID = "multi_tf"
    STRATEGY_NAME_FA = "تأیید مولتی‌تایم‌فریم"
    STRATEGY_NAME_EN = "Multi-Timeframe Confirmation"
    CATEGORY = "multi_tf"
    REQUIRED_INDICATORS = ["trend", "ma"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        trend = indicators.get("trend", {})
        ma = indicators.get("ma", {})

        regime = self.last(trend.get("regime"))
        adx = self.last(trend.get("adx"))
        stack = self.last(ma.get("ma_stack"))

        if regime is None:
            return self._neutral("داده کافی نیست")

        # Current TF direction
        curr_dir = int(regime) if regime else 0

        # We need symbol and timeframe from metadata
        # The orchestrator sets these on the result after analyze()
        # So we need to detect the symbol from the df
        # WORKAROUND: Use the orchestrator's context that passes symbol info
        # For now, use a class attribute set by orchestrator
        symbol = getattr(self, '_current_symbol', None)
        timeframe = getattr(self, '_current_timeframe', None)

        if not symbol or not timeframe:
            return self._neutral("اطلاعات نماد/تایم‌فریم در دسترس نیست",
                                 "Symbol/TF info not available")

        htf_list = HTF_MAP.get(timeframe, [])
        if not htf_list:
            return self._neutral(
                f"تایم‌فریم {timeframe} بالاترین است، تأیید HTF ندارد",
                f"No higher TF for {timeframe}")

        htf_results = []
        for htf in htf_list:
            r = analyze_htf(symbol, htf)
            if r["available"]:
                htf_results.append(r)

        if not htf_results:
            return self._neutral("داده تایم‌فریم بالاتر در دسترس نیست")

        confidence = 0
        signals = []
        aligned_count = 0

        for htf_r in htf_results:
            tf_name = htf_r["timeframe"]
            htf_dir = htf_r["direction"]

            if htf_dir == curr_dir and curr_dir != 0:
                aligned_count += 1
                dir_fa = "صعودی" if htf_dir == 1 else "نزولی"
                signals.append(f"{tf_name} {dir_fa}")
                confidence += 25

                if htf_r["adx"] > 25:
                    confidence += 10
                if htf_r["stack"] == curr_dir:
                    confidence += 5

            elif htf_dir != 0 and htf_dir != curr_dir:
                signals.append(f"{tf_name} مخالف!")
                confidence -= 15

        if aligned_count > 0 and confidence >= 35:
            sig = Signal.BUY if curr_dir == 1 else Signal.SELL
            dir_fa = "صعودی" if curr_dir == 1 else "نزولی"
            return self._make_result(sig, min(confidence, 85),
                f"تأیید MTF {dir_fa}: {' | '.join(signals)}",
                f"MTF alignment: {aligned_count}/{len(htf_results)} TFs agree",
                {"aligned": aligned_count, "total_htf": len(htf_results),
                 "htf_details": htf_results, "current_dir": curr_dir})

        if aligned_count == 0 and htf_results:
            return self._neutral(
                f"تایم‌فریم‌ها هم‌جهت نیستند: {' | '.join(signals)}",
                "MTF misalignment",
                {"htf_details": htf_results})

        return self._neutral("تأیید مولتی‌تایم‌فریم ضعیف")
