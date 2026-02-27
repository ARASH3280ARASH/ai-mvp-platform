"""
Whilber-AI — Strategy Optimizer
===================================
Grid Search, Walk-Forward, Monte Carlo for parameter optimization.
"""

import numpy as np
import copy
import random
from datetime import datetime

from backend.api.backtest_engine import run_backtest


def _get_param_ranges(strategy):
    """Extract optimizable parameters with ranges."""
    params = []

    # Entry indicator params
    for ci, cond in enumerate(strategy.get("entry_conditions", [])):
        ind_id = cond.get("indicator", "")
        ind_params = cond.get("indicator_params", {})
        for pk, pv in ind_params.items():
            if isinstance(pv, int):
                params.append({
                    "path": f"entry_conditions.{ci}.indicator_params.{pk}",
                    "name": f"{ind_id}.{pk}",
                    "type": "int",
                    "current": pv,
                    "min": max(2, pv - pv // 2),
                    "max": pv + pv // 2 + 1,
                    "step": max(1, pv // 5),
                })
            elif isinstance(pv, float):
                params.append({
                    "path": f"entry_conditions.{ci}.indicator_params.{pk}",
                    "name": f"{ind_id}.{pk}",
                    "type": "float",
                    "current": pv,
                    "min": round(max(0.1, pv * 0.5), 2),
                    "max": round(pv * 2.0, 2),
                    "step": round(max(0.1, pv * 0.2), 2),
                })

        # Compare value
        if cond.get("compare_to") == "fixed_value":
            cv = cond.get("compare_value", 0)
            if isinstance(cv, (int, float)) and cv != 0:
                params.append({
                    "path": f"entry_conditions.{ci}.compare_value",
                    "name": f"{ind_id}.threshold",
                    "type": "float",
                    "current": float(cv),
                    "min": round(float(cv) * 0.5, 2),
                    "max": round(float(cv) * 1.5, 2),
                    "step": round(max(0.5, abs(float(cv)) * 0.1), 2),
                })

    # Exit params
    for ti, tp in enumerate(strategy.get("exit_take_profit", [])):
        for pk, pv in tp.get("params", {}).items():
            if isinstance(pv, (int, float)):
                params.append({
                    "path": f"exit_take_profit.{ti}.params.{pk}",
                    "name": f"TP.{pk}",
                    "type": "float" if isinstance(pv, float) else "int",
                    "current": pv,
                    "min": round(max(0.1, pv * 0.5), 2),
                    "max": round(pv * 2.5, 2),
                    "step": round(max(0.1, pv * 0.2), 2),
                })

    for si, sl in enumerate(strategy.get("exit_stop_loss", [])):
        for pk, pv in sl.get("params", {}).items():
            if isinstance(pv, (int, float)):
                params.append({
                    "path": f"exit_stop_loss.{si}.params.{pk}",
                    "name": f"SL.{pk}",
                    "type": "float" if isinstance(pv, float) else "int",
                    "current": pv,
                    "min": round(max(0.1, pv * 0.5), 2),
                    "max": round(pv * 2.5, 2),
                    "step": round(max(0.1, pv * 0.2), 2),
                })

    return params


def _set_param(strategy, path, value):
    """Set a nested parameter value by dot-separated path."""
    parts = path.split(".")
    obj = strategy
    for p in parts[:-1]:
        if p.isdigit():
            obj = obj[int(p)]
        else:
            obj = obj[p]
    last = parts[-1]
    if last.isdigit():
        obj[int(last)] = value
    else:
        obj[last] = value


def _gen_values(param):
    """Generate range of values for a parameter."""
    if param["type"] == "int":
        vals = list(range(int(param["min"]), int(param["max"]) + 1, int(param["step"])))
        if param["current"] not in vals:
            vals.append(param["current"])
        vals.sort()
        return vals
    else:
        vals = []
        v = param["min"]
        while v <= param["max"] + 0.001:
            vals.append(round(v, 3))
            v += param["step"]
        if param["current"] not in vals:
            vals.append(round(param["current"], 3))
        vals.sort()
        return vals


def grid_search(df, strategy, selected_params=None, max_combos=200):
    """
    Grid search optimization.
    Tests all combinations of selected parameters.
    """
    all_params = _get_param_ranges(strategy)
    if selected_params:
        params = [p for p in all_params if p["name"] in selected_params]
    else:
        params = all_params[:3]  # Limit to 3 params max

    if not params:
        return {"success": False, "error": "No optimizable parameters found"}

    # Generate value ranges
    param_values = []
    for p in params:
        vals = _gen_values(p)
        # Limit each param to 8 values max
        if len(vals) > 8:
            step = len(vals) // 8
            vals = vals[::step]
            if p["current"] not in vals:
                vals.append(p["current"])
            vals.sort()
        param_values.append(vals)

    # Total combinations
    total = 1
    for pv in param_values:
        total *= len(pv)

    # If too many, sample randomly
    if total > max_combos:
        combos = []
        for _ in range(max_combos):
            combo = tuple(random.choice(v) for v in param_values)
            if combo not in combos:
                combos.append(combo)
    else:
        # Generate all combos
        combos = [[]]
        for pv in param_values:
            combos = [c + [v] for c in combos for v in pv]

    # Run backtests
    results = []
    best_pf = -999
    best_combo = None

    for combo in combos:
        s = copy.deepcopy(strategy)
        param_desc = {}
        for i, p in enumerate(params):
            val = combo[i] if isinstance(combo, (list, tuple)) else combo
            _set_param(s, p["path"], val)
            param_desc[p["name"]] = val

        try:
            bt = run_backtest(df, s, initial_balance=10000, spread_pips=2)
            if bt.get("success") and bt.get("stats", {}).get("total", 0) >= 3:
                st = bt["stats"]
                score = _calc_opt_score(st)
                results.append({
                    "params": param_desc,
                    "total_trades": st["total"],
                    "win_rate": st["win_rate"],
                    "profit_factor": st["profit_factor"],
                    "total_pnl": st["total_pnl"],
                    "max_dd": st["max_drawdown_pct"],
                    "sharpe": st["sharpe"],
                    "score": score,
                })
                if score > best_pf:
                    best_pf = score
                    best_combo = param_desc
        except Exception:
            continue

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "success": True,
        "method": "grid_search",
        "total_tested": len(results),
        "total_combos": len(combos),
        "parameters": [{"name": p["name"], "values": _gen_values(p)} for p in params],
        "results": results[:50],  # Top 50
        "best": results[0] if results else None,
        "best_params": best_combo,
    }


def walk_forward(df, strategy, windows=5):
    """
    Walk-Forward optimization.
    Split data into train/test windows. Optimize on train, validate on test.
    """
    n = len(df)
    if n < 200:
        return {"success": False, "error": "Need 200+ bars for walk-forward"}

    window_size = n // windows
    train_pct = 0.7
    train_size = int(window_size * train_pct)
    test_size = window_size - train_size

    all_params = _get_param_ranges(strategy)
    opt_params = all_params[:2]  # Max 2 params for speed

    if not opt_params:
        return {"success": False, "error": "No optimizable parameters"}

    window_results = []
    all_test_trades = 0
    all_test_wins = 0
    all_test_pnl = 0

    for w in range(windows):
        start = w * window_size
        end = min(start + window_size, n)
        if end - start < 50:
            continue

        train_end = start + train_size
        train_df = df.iloc[start:train_end].reset_index(drop=True)
        test_df = df.iloc[train_end:end].reset_index(drop=True)

        if len(train_df) < 30 or len(test_df) < 20:
            continue

        # Optimize on train
        best_score = -999
        best_params_vals = {}

        param_values = [_gen_values(p)[:6] for p in opt_params]
        combos = [[]]
        for pv in param_values:
            combos = [c + [v] for c in combos for v in pv]

        for combo in combos[:100]:
            s = copy.deepcopy(strategy)
            pv = {}
            for i, p in enumerate(opt_params):
                _set_param(s, p["path"], combo[i])
                pv[p["name"]] = combo[i]
            try:
                bt = run_backtest(train_df, s, initial_balance=10000, spread_pips=2)
                if bt.get("success") and bt["stats"]["total"] >= 2:
                    sc = _calc_opt_score(bt["stats"])
                    if sc > best_score:
                        best_score = sc
                        best_params_vals = pv
            except Exception:
                continue

        # Test with best params on test data
        s_test = copy.deepcopy(strategy)
        for i, p in enumerate(opt_params):
            if p["name"] in best_params_vals:
                _set_param(s_test, p["path"], best_params_vals[p["name"]])

        try:
            bt_test = run_backtest(test_df, s_test, initial_balance=10000, spread_pips=2)
            if bt_test.get("success"):
                tst = bt_test["stats"]
                all_test_trades += tst["total"]
                all_test_wins += tst["wins"]
                all_test_pnl += tst["total_pnl"]

                window_results.append({
                    "window": w + 1,
                    "train_bars": len(train_df),
                    "test_bars": len(test_df),
                    "best_params": best_params_vals,
                    "train_score": round(best_score, 1),
                    "test_trades": tst["total"],
                    "test_win_rate": tst["win_rate"],
                    "test_pnl": tst["total_pnl"],
                    "test_pf": tst["profit_factor"],
                    "test_dd": tst["max_drawdown_pct"],
                })
        except Exception:
            continue

    overall_wr = (all_test_wins / all_test_trades * 100) if all_test_trades > 0 else 0

    return {
        "success": True,
        "method": "walk_forward",
        "windows": len(window_results),
        "total_test_trades": all_test_trades,
        "overall_test_win_rate": round(overall_wr, 1),
        "overall_test_pnl": round(all_test_pnl, 2),
        "robust": overall_wr >= 45 and all_test_pnl > 0,
        "window_results": window_results,
    }


def monte_carlo(df, strategy, simulations=500):
    """
    Monte Carlo simulation.
    Shuffle trade outcomes to estimate risk of ruin and confidence intervals.
    """
    # First run normal backtest
    bt = run_backtest(df, strategy, initial_balance=10000, spread_pips=2)
    if not bt.get("success") or not bt.get("trades"):
        return {"success": False, "error": "Need completed backtest first"}

    trades = bt["trades"]
    pnls = [t["pnl"] for t in trades]
    initial = bt["initial_balance"]

    if len(pnls) < 5:
        return {"success": False, "error": "Need 5+ trades for Monte Carlo"}

    # Run simulations
    final_balances = []
    max_dds = []
    ruin_count = 0
    ruin_threshold = initial * 0.5  # 50% loss = ruin

    for _ in range(simulations):
        shuffled = pnls.copy()
        random.shuffle(shuffled)

        balance = initial
        peak = initial
        max_dd = 0

        for pnl in shuffled:
            balance += pnl
            peak = max(peak, balance)
            dd = (peak - balance) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

            if balance <= ruin_threshold:
                ruin_count += 1
                break

        final_balances.append(round(balance, 2))
        max_dds.append(round(max_dd, 1))

    final_balances.sort()
    max_dds.sort()

    n_sim = len(final_balances)

    # Percentiles
    p5 = final_balances[int(n_sim * 0.05)]
    p25 = final_balances[int(n_sim * 0.25)]
    p50 = final_balances[int(n_sim * 0.50)]
    p75 = final_balances[int(n_sim * 0.75)]
    p95 = final_balances[int(n_sim * 0.95)]

    dd_p50 = max_dds[int(n_sim * 0.50)]
    dd_p95 = max_dds[int(n_sim * 0.95)]

    # Distribution for histogram
    hist_bins = 20
    min_b = min(final_balances)
    max_b = max(final_balances)
    bin_width = (max_b - min_b) / hist_bins if max_b > min_b else 1
    histogram = []
    for b in range(hist_bins):
        lo = min_b + b * bin_width
        hi = lo + bin_width
        count = sum(1 for fb in final_balances if lo <= fb < hi)
        histogram.append({
            "range": f"${int(lo)}-${int(hi)}",
            "count": count,
            "pct": round(count / n_sim * 100, 1),
        })

    return {
        "success": True,
        "method": "monte_carlo",
        "simulations": simulations,
        "original_trades": len(pnls),
        "original_pnl": bt["stats"]["total_pnl"],
        "original_balance": bt["final_balance"],
        "risk_of_ruin": round(ruin_count / simulations * 100, 1),
        "percentiles": {
            "p5": p5, "p25": p25, "p50": p50, "p75": p75, "p95": p95,
        },
        "drawdown": {
            "median": dd_p50,
            "worst_95": dd_p95,
        },
        "profitable_pct": round(sum(1 for fb in final_balances if fb > initial) / n_sim * 100, 1),
        "histogram": histogram,
        "min_balance": min(final_balances),
        "max_balance": max(final_balances),
        "avg_balance": round(np.mean(final_balances), 2),
    }


def get_optimizable_params(strategy):
    """Return list of params that can be optimized."""
    return _get_param_ranges(strategy)


def _calc_opt_score(stats):
    """Unified optimization score."""
    s = 0
    wr = stats.get("win_rate", 0)
    pf = stats.get("profit_factor", 0)
    dd = stats.get("max_drawdown_pct", 100)
    pnl = stats.get("total_pnl", 0)
    sharpe = stats.get("sharpe", 0)

    # Profit factor (0-30)
    if pf >= 2.0:
        s += 30
    elif pf >= 1.5:
        s += 22
    elif pf >= 1.2:
        s += 15
    elif pf >= 1.0:
        s += 8

    # Win rate (0-25)
    if wr >= 65:
        s += 25
    elif wr >= 55:
        s += 18
    elif wr >= 45:
        s += 10

    # Drawdown (0-20)
    if dd <= 10:
        s += 20
    elif dd <= 20:
        s += 14
    elif dd <= 30:
        s += 7

    # Profitability (0-15)
    if pnl > 500:
        s += 15
    elif pnl > 200:
        s += 10
    elif pnl > 0:
        s += 5

    # Sharpe (0-10)
    if sharpe >= 2:
        s += 10
    elif sharpe >= 1:
        s += 6
    elif sharpe >= 0.5:
        s += 3

    return min(100, s)
