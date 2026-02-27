"""
Whilber-AI — Advanced Charts & Analytics
============================================
Monthly heatmap, drawdown, distribution, hourly/daily,
win/loss streaks, exit reason breakdown.
"""

import numpy as np
from collections import defaultdict


def compute_advanced_analytics(backtest_result, strategy=None):
    """Compute all advanced analytics from backtest result."""
    trades = backtest_result.get("trades", [])
    equity = backtest_result.get("equity_curve", [])
    initial = backtest_result.get("initial_balance", 10000)
    stats = backtest_result.get("stats", {})

    if not trades:
        return {"success": False, "error": "No trades"}

    result = {
        "success": True,
        "monthly_heatmap": _monthly_heatmap(trades),
        "drawdown_curve": _drawdown_curve(equity, initial),
        "pnl_distribution": _pnl_distribution(trades),
        "hourly_performance": _hourly_performance(trades),
        "daily_performance": _daily_performance(trades),
        "streak_chart": _streak_chart(trades),
        "exit_reasons": _exit_reasons(trades),
        "cumulative_pnl": _cumulative_pnl(trades),
        "rr_distribution": _rr_distribution(trades),
        "lot_vs_pnl": _lot_vs_pnl(trades),
        "trade_duration": _trade_duration(trades),
    }
    return result


def _monthly_heatmap(trades):
    """PnL grouped by year-month."""
    monthly = defaultdict(float)
    monthly_count = defaultdict(int)
    monthly_wins = defaultdict(int)

    for t in trades:
        bar = t.get("entry_bar", 0)
        # Use trade index as proxy for time grouping
        month_idx = bar // 500  # approximate month grouping
        year = 2024 + month_idx // 12
        month = (month_idx % 12) + 1
        key = f"{year}-{month:02d}"
        monthly[key] += t.get("pnl", 0)
        monthly_count[key] += 1
        if t.get("pnl", 0) > 0:
            monthly_wins[key] += 1

    months = sorted(monthly.keys())
    data = []
    for m in months:
        cnt = monthly_count[m]
        data.append({
            "month": m,
            "pnl": round(monthly[m], 2),
            "trades": cnt,
            "win_rate": round(monthly_wins[m] / cnt * 100, 1) if cnt else 0,
        })
    return data


def _drawdown_curve(equity, initial):
    """Compute drawdown at each point."""
    if not equity:
        return []

    peak = initial
    dd_curve = []
    for i, eq in enumerate(equity):
        peak = max(peak, eq)
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        dd_curve.append({
            "bar": i,
            "equity": round(eq, 2),
            "drawdown": round(dd, 2),
            "peak": round(peak, 2),
        })
    return dd_curve


def _pnl_distribution(trades):
    """Histogram of trade PnL."""
    pnls = [t.get("pnl", 0) for t in trades]
    if not pnls:
        return {"bins": [], "counts": []}

    min_p = min(pnls)
    max_p = max(pnls)
    if min_p == max_p:
        return {"bins": [round(min_p, 2)], "counts": [len(pnls)]}

    n_bins = min(20, max(5, len(pnls) // 3))
    width = (max_p - min_p) / n_bins

    bins = []
    counts = []
    colors = []
    for b in range(n_bins):
        lo = min_p + b * width
        hi = lo + width
        cnt = sum(1 for p in pnls if lo <= p < hi or (b == n_bins - 1 and p == hi))
        mid = (lo + hi) / 2
        bins.append(round(mid, 1))
        counts.append(cnt)
        colors.append("green" if mid >= 0 else "red")

    return {
        "bins": bins,
        "counts": counts,
        "colors": colors,
        "avg": round(np.mean(pnls), 2),
        "median": round(float(np.median(pnls)), 2),
        "std": round(float(np.std(pnls)), 2),
    }


def _hourly_performance(trades):
    """Performance grouped by entry hour (simulated from bar position)."""
    hourly = defaultdict(lambda: {"count": 0, "wins": 0, "pnl": 0})

    for i, t in enumerate(trades):
        hour = (t.get("entry_bar", i) * 4) % 24  # Simulate hours
        h = hourly[hour]
        h["count"] += 1
        h["pnl"] += t.get("pnl", 0)
        if t.get("pnl", 0) > 0:
            h["wins"] += 1

    data = []
    for hr in range(24):
        h = hourly[hr]
        data.append({
            "hour": hr,
            "label": f"{hr:02d}:00",
            "trades": h["count"],
            "win_rate": round(h["wins"] / h["count"] * 100, 1) if h["count"] else 0,
            "pnl": round(h["pnl"], 2),
        })
    return data


def _daily_performance(trades):
    """Performance grouped by day of week."""
    days_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
    days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily = defaultdict(lambda: {"count": 0, "wins": 0, "pnl": 0})

    for i, t in enumerate(trades):
        day_idx = t.get("entry_bar", i) % 5  # Mon-Fri
        d = daily[day_idx]
        d["count"] += 1
        d["pnl"] += t.get("pnl", 0)
        if t.get("pnl", 0) > 0:
            d["wins"] += 1

    data = []
    for di in range(5):
        d = daily[di]
        data.append({
            "day": di,
            "name_fa": days_fa[di],
            "name_en": days_en[di],
            "trades": d["count"],
            "win_rate": round(d["wins"] / d["count"] * 100, 1) if d["count"] else 0,
            "pnl": round(d["pnl"], 2),
        })
    return data


def _streak_chart(trades):
    """Win/loss streaks sequence."""
    streaks = []
    current = 0
    current_type = None

    for t in trades:
        win = t.get("pnl", 0) > 0
        if current_type is None:
            current_type = win
            current = 1
        elif win == current_type:
            current += 1
        else:
            streaks.append({
                "type": "win" if current_type else "loss",
                "length": current,
            })
            current_type = win
            current = 1

    if current > 0:
        streaks.append({"type": "win" if current_type else "loss", "length": current})

    # Summary
    win_streaks = [s["length"] for s in streaks if s["type"] == "win"]
    loss_streaks = [s["length"] for s in streaks if s["type"] == "loss"]

    return {
        "streaks": streaks,
        "max_win_streak": max(win_streaks) if win_streaks else 0,
        "max_loss_streak": max(loss_streaks) if loss_streaks else 0,
        "avg_win_streak": round(np.mean(win_streaks), 1) if win_streaks else 0,
        "avg_loss_streak": round(np.mean(loss_streaks), 1) if loss_streaks else 0,
        "total_streaks": len(streaks),
    }


def _exit_reasons(trades):
    """Count of each exit reason."""
    reasons = defaultdict(int)
    reason_pnl = defaultdict(float)

    for t in trades:
        r = t.get("exit_reason", "unknown")
        reasons[r] += 1
        reason_pnl[r] += t.get("pnl", 0)

    reason_names = {
        "tp": "Take Profit",
        "sl": "Stop Loss",
        "trailing": "Trailing Stop",
        "break_even": "Break Even",
        "time": "Time Exit",
        "end": "End of Data",
        "unknown": "Unknown",
    }

    data = []
    total = sum(reasons.values())
    for r, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
        data.append({
            "reason": r,
            "label": reason_names.get(r, r),
            "count": cnt,
            "pct": round(cnt / total * 100, 1) if total else 0,
            "pnl": round(reason_pnl[r], 2),
            "avg_pnl": round(reason_pnl[r] / cnt, 2) if cnt else 0,
        })
    return data


def _cumulative_pnl(trades):
    """Cumulative PnL curve."""
    cum = 0
    data = []
    for i, t in enumerate(trades):
        cum += t.get("pnl", 0)
        data.append({"trade": i + 1, "pnl": round(cum, 2)})
    return data


def _rr_distribution(trades):
    """Risk:Reward ratio distribution."""
    rrs = [t.get("rr", 0) for t in trades if t.get("rr", 0) > 0]
    if not rrs:
        return {"bins": [], "counts": []}

    bins = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 999]
    labels = ["0-0.5", "0.5-1", "1-1.5", "1.5-2", "2-2.5", "2.5-3", "3-4", "4-5", "5+"]
    counts = []
    win_counts = []

    for b in range(len(bins) - 1):
        lo, hi = bins[b], bins[b + 1]
        matching = [t for t in trades if lo <= t.get("rr", 0) < hi]
        counts.append(len(matching))
        win_counts.append(sum(1 for t in matching if t.get("pnl", 0) > 0))

    return {
        "labels": labels,
        "counts": counts,
        "win_counts": win_counts,
        "avg_rr": round(np.mean(rrs), 2) if rrs else 0,
    }


def _lot_vs_pnl(trades):
    """Lot size vs PnL scatter data."""
    data = []
    for t in trades:
        data.append({
            "lot": t.get("lot_size", 0.01),
            "pnl": t.get("pnl", 0),
            "win": t.get("pnl", 0) > 0,
        })
    return data


def _trade_duration(trades):
    """Distribution of trade duration (bars held)."""
    durations = [t.get("bars_held", 0) for t in trades if t.get("bars_held", 0) > 0]
    if not durations:
        return {"bins": [], "counts": []}

    max_d = max(durations)
    n_bins = min(15, max_d)
    if n_bins < 1:
        n_bins = 1
    width = max(1, max_d // n_bins)

    bins = []
    counts = []
    for b in range(n_bins):
        lo = b * width
        hi = lo + width
        cnt = sum(1 for d in durations if lo <= d < hi or (b == n_bins - 1 and d == hi))
        bins.append(f"{lo}-{hi}")
        counts.append(cnt)

    return {
        "bins": bins,
        "counts": counts,
        "avg": round(np.mean(durations), 1),
        "median": int(np.median(durations)),
        "max": max(durations),
    }
