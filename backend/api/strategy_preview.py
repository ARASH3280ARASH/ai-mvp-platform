"""
Whilber-AI — Strategy Preview Engine
========================================
Evaluate strategy on recent data:
- Last N signals with entry/exit points
- Current signal status (what strategy says NOW)
- Quick win rate from recent signals
- Strategy scoring/rating
"""

import numpy as np
from datetime import datetime, timezone

from backend.api.indicator_calc import compute_indicator


def _pip_value(symbol):
    sym = symbol.upper()
    if "JPY" in sym:
        return 0.01
    elif "XAU" in sym or "GOLD" in sym:
        return 0.1
    elif "BTC" in sym:
        return 1.0
    elif "US30" in sym or "NAS" in sym:
        return 1.0
    return 0.0001


def _check_cond(cond_type, val, cmp, prev_val=None, prev_cmp=None):
    if val is None or np.isnan(val):
        return False
    if cmp is None or np.isnan(cmp):
        return False
    if cond_type == "is_above":
        return val > cmp
    elif cond_type == "is_below":
        return val < cmp
    elif cond_type == "crosses_above":
        if prev_val is None or np.isnan(prev_val):
            return False
        return prev_val <= prev_cmp and val > cmp
    elif cond_type == "crosses_below":
        if prev_val is None or np.isnan(prev_val):
            return False
        return prev_val >= prev_cmp and val < cmp
    elif cond_type == "is_rising":
        return prev_val is not None and not np.isnan(prev_val) and val > prev_val
    elif cond_type == "is_falling":
        return prev_val is not None and not np.isnan(prev_val) and val < prev_val
    elif cond_type == "is_overbought":
        return val > (cmp if cmp else 70)
    elif cond_type == "is_oversold":
        return val < (cmp if cmp else 30)
    return False


def preview_strategy(df, strategy, max_signals=20):
    """
    Preview strategy on DataFrame.
    Returns recent signals, current status, and quick stats.
    """
    n = len(df)
    if n < 30:
        return {"success": False, "error": "Not enough data (min 30 bars)"}

    c = df["close"].values
    h = df["high"].values
    l = df["low"].values
    times = df["time"].values if "time" in df.columns else list(range(n))
    symbol = strategy.get("symbol", "XAUUSD")
    pip = _pip_value(symbol)
    direction = strategy.get("direction", "both")
    entry_logic = strategy.get("entry_logic", "AND")
    entry_conds = strategy.get("entry_conditions", [])

    # Pre-compute indicators
    ind_cache = {}
    for cond in entry_conds:
        ind_id = cond.get("indicator", "")
        params = cond.get("indicator_params", {})
        key = f"{ind_id}_{hash(str(sorted(params.items())))}"
        if key not in ind_cache and ind_id:
            ind_cache[key] = compute_indicator(df, ind_id, params)
        cond["_ck"] = key
        if cond.get("compare_to") == "indicator":
            cid = cond.get("compare_indicator", "")
            cp = cond.get("compare_indicator_params", {})
            ck2 = f"{cid}_{hash(str(sorted(cp.items())))}"
            if ck2 not in ind_cache and cid:
                ind_cache[ck2] = compute_indicator(df, cid, cp)
            cond["_ck2"] = ck2

    # ATR for TP/SL estimation
    atr = compute_indicator(df, "ATR", {"period": 14})["value"]
    tp_configs = strategy.get("exit_take_profit", [])
    sl_configs = strategy.get("exit_stop_loss", [])

    # Scan for signals
    signals = []
    indicator_values = []

    for i in range(1, n):
        results = []
        cond_details = []

        for cond in entry_conds:
            cache = ind_cache.get(cond.get("_ck", ""), {})
            output = cond.get("output", "value")
            vals = cache.get(output, np.full(n, np.nan))
            v = vals[i] if i < len(vals) else None
            vp = vals[i - 1] if i > 0 and i - 1 < len(vals) else None

            cmp_to = cond.get("compare_to", "fixed_value")
            if cmp_to == "fixed_value":
                cv = float(cond.get("compare_value", 0))
                cvp = cv
            elif cmp_to == "indicator":
                cc = ind_cache.get(cond.get("_ck2", ""), {})
                co = cond.get("compare_output", "value")
                cvs = cc.get(co, np.full(n, np.nan))
                cv = cvs[i] if i < len(cvs) else None
                cvp = cvs[i - 1] if i > 0 and i - 1 < len(cvs) else cv
            elif cmp_to == "price_close":
                cv = c[i]
                cvp = c[i - 1] if i > 0 else c[i]
            else:
                cv = c[i]
                cvp = c[i - 1] if i > 0 else c[i]

            if v is not None and not np.isnan(v) and cv is not None:
                met = _check_cond(cond.get("condition", ""), v, cv, vp, cvp)
            else:
                met = False

            results.append(met)
            cond_details.append({
                "indicator": cond.get("indicator", ""),
                "condition": cond.get("condition", ""),
                "value": round(float(v), 4) if v is not None and not np.isnan(v) else None,
                "compare": round(float(cv), 4) if cv is not None and not np.isnan(cv if isinstance(cv, (int, float)) else 0) else None,
                "met": met,
            })

        if results:
            signal = all(results) if entry_logic == "AND" else any(results)
        else:
            signal = False

        # Save indicator values for current bar
        if i == n - 1:
            indicator_values = cond_details

        if signal:
            # Determine direction
            sma50 = compute_indicator(df, "SMA", {"period": min(50, n - 1)})["value"]
            if direction == "buy_only":
                sig_type = "BUY"
            elif direction == "sell_only":
                sig_type = "SELL"
            else:
                sig_type = "BUY" if (not np.isnan(sma50[i]) and c[i] > sma50[i]) else "SELL"

            # TP/SL estimation
            atr_v = atr[i] if not np.isnan(atr[i]) else pip * 100
            tp_dist = _calc_exit_dist(tp_configs, atr_v, pip, c[i], "tp")
            sl_dist = _calc_exit_dist(sl_configs, atr_v, pip, c[i], "sl")

            if sig_type == "BUY":
                tp_price = c[i] + tp_dist
                sl_price = c[i] - sl_dist
            else:
                tp_price = c[i] - tp_dist
                sl_price = c[i] + sl_dist

            # Check outcome (if enough future bars)
            outcome = "open"
            exit_price = None
            bars_held = 0
            pnl_pips = 0

            for j in range(i + 1, min(i + 50, n)):
                bars_held = j - i
                if sig_type == "BUY":
                    if h[j] >= tp_price:
                        outcome = "win"
                        exit_price = tp_price
                        pnl_pips = tp_dist / pip
                        break
                    if l[j] <= sl_price:
                        outcome = "loss"
                        exit_price = sl_price
                        pnl_pips = -sl_dist / pip
                        break
                else:
                    if l[j] <= tp_price:
                        outcome = "win"
                        exit_price = tp_price
                        pnl_pips = tp_dist / pip
                        break
                    if h[j] >= sl_price:
                        outcome = "loss"
                        exit_price = sl_price
                        pnl_pips = -sl_dist / pip
                        break

            signals.append({
                "bar": i,
                "time": str(times[i]),
                "type": sig_type,
                "price": round(c[i], 5),
                "tp": round(tp_price, 5),
                "sl": round(sl_price, 5),
                "rr": round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0,
                "outcome": outcome,
                "exit_price": round(exit_price, 5) if exit_price else None,
                "pnl_pips": round(pnl_pips, 1),
                "bars_held": bars_held,
                "conditions": cond_details,
            })

    # Last N signals
    recent = signals[-max_signals:] if len(signals) > max_signals else signals

    # Current status
    last_signal = signals[-1] if signals else None
    current_signal = None
    if indicator_values:
        all_met = all(d["met"] for d in indicator_values) if entry_logic == "AND" else any(d["met"] for d in indicator_values)
        if all_met:
            sma50 = compute_indicator(df, "SMA", {"period": min(50, n - 1)})["value"]
            if direction == "buy_only":
                ct = "BUY"
            elif direction == "sell_only":
                ct = "SELL"
            else:
                ct = "BUY" if (not np.isnan(sma50[-1]) and c[-1] > sma50[-1]) else "SELL"
            current_signal = {"type": ct, "price": round(c[-1], 5), "active": True}
        else:
            current_signal = {"type": "NONE", "price": round(c[-1], 5), "active": False}

    # Quick stats
    completed = [s for s in signals if s["outcome"] in ("win", "loss")]
    wins = [s for s in completed if s["outcome"] == "win"]
    losses = [s for s in completed if s["outcome"] == "loss"]
    win_rate = (len(wins) / len(completed) * 100) if completed else 0
    avg_pnl = np.mean([s["pnl_pips"] for s in completed]) if completed else 0
    total_pnl = sum(s["pnl_pips"] for s in completed)

    # Strategy score (0-100)
    score = _calc_score(win_rate, len(completed), avg_pnl, total_pnl)

    return {
        "success": True,
        "signals": recent,
        "total_signals": len(signals),
        "current_signal": current_signal,
        "current_indicators": indicator_values,
        "current_price": round(c[-1], 5),
        "stats": {
            "total": len(completed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 1),
            "avg_pnl_pips": round(avg_pnl, 1),
            "total_pnl_pips": round(total_pnl, 1),
            "score": score,
        },
    }


def compare_strategies(df, strategy1, strategy2):
    """Compare two strategies on same data."""
    r1 = preview_strategy(df, strategy1, max_signals=50)
    r2 = preview_strategy(df, strategy2, max_signals=50)
    return {
        "success": True,
        "strategy1": {
            "name": strategy1.get("name", "Strategy 1"),
            "stats": r1.get("stats", {}),
            "total_signals": r1.get("total_signals", 0),
            "current_signal": r1.get("current_signal"),
        },
        "strategy2": {
            "name": strategy2.get("name", "Strategy 2"),
            "stats": r2.get("stats", {}),
            "total_signals": r2.get("total_signals", 0),
            "current_signal": r2.get("current_signal"),
        },
    }


def _calc_exit_dist(configs, atr_v, pip, price, exit_type):
    if not configs:
        return 2.0 * atr_v if exit_type == "tp" else 1.5 * atr_v
    cfg = configs[0]
    t = cfg.get("type", "")
    p = cfg.get("params", {})
    if "atr" in t:
        return p.get("multiplier", 2.0 if exit_type == "tp" else 1.5) * atr_v
    elif "fixed" in t:
        return p.get("pips", 50 if exit_type == "tp" else 30) * pip
    elif "percent" in t:
        return price * p.get("percent", 1.0) / 100
    elif "swing" in t:
        return p.get("lookback", 10) * pip * 5
    return 2.0 * atr_v if exit_type == "tp" else 1.5 * atr_v


def _calc_score(win_rate, total, avg_pnl, total_pnl):
    """Score 0-100 based on strategy quality."""
    if total < 3:
        return 0
    s = 0
    # Win rate component (0-35)
    if win_rate >= 70:
        s += 35
    elif win_rate >= 60:
        s += 28
    elif win_rate >= 50:
        s += 20
    elif win_rate >= 40:
        s += 10
    # Profitability (0-30)
    if total_pnl > 0:
        s += min(30, int(total_pnl / 10))
    # Average PnL (0-20)
    if avg_pnl > 5:
        s += 20
    elif avg_pnl > 2:
        s += 15
    elif avg_pnl > 0:
        s += 8
    # Sample size (0-15)
    if total >= 20:
        s += 15
    elif total >= 10:
        s += 10
    elif total >= 5:
        s += 5
    return min(100, s)
