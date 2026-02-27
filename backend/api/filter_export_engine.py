"""
Whilber-AI — Advanced Filter, Compare & Export Engine
========================================================
Multi-criteria filtering across all strategy records.
Side-by-side comparison of 2-5 strategies.
CSV + HTML export of filtered results.
Performance heatmap by hour/day.
"""

import json
import os
import csv
import io
from datetime import datetime, timezone
from collections import defaultdict

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
TRACK_DIR = os.path.join(PROJECT_DIR, "track_records")
EXPORT_DIR = os.path.join(PROJECT_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


# ══════ ADVANCED FILTER ══════

def filter_trades(filters=None):
    """
    Filter all trades across all strategies.
    filters: {
        symbols: [list], categories: [list], timeframes: [list],
        directions: [list], outcomes: [list], exit_reasons: [list],
        date_from: str, date_to: str,
        min_pnl: float, max_pnl: float,
        min_duration: int, max_duration: int,
        min_rr: float, had_be: bool, had_trailing: bool,
        strategy_ids: [list], search: str,
    }
    """
    from backend.api.tracker_engine import get_all_strategy_ids, load_records

    filters = filters or {}
    all_trades = []

    # Load all trades
    target_sids = filters.get("strategy_ids", [])
    sids = target_sids if target_sids else get_all_strategy_ids()

    for sid in sids:
        rec = load_records(sid)
        for t in rec.get("trades", []):
            t["_strategy_id"] = sid
            all_trades.append(t)

    # Apply filters
    result = []
    for t in all_trades:
        # Symbol
        syms = filters.get("symbols", [])
        if syms and t.get("symbol", "") not in syms:
            continue

        # Category
        cats = filters.get("categories", [])
        if cats and t.get("category", "") not in cats:
            continue

        # Timeframe
        tfs = filters.get("timeframes", [])
        if tfs and t.get("timeframe", "") not in tfs:
            continue

        # Direction
        dirs = filters.get("directions", [])
        if dirs and t.get("direction", "") not in dirs:
            continue

        # Outcome
        outs = filters.get("outcomes", [])
        if outs and t.get("outcome", "") not in outs:
            continue

        # Exit reason
        exits = filters.get("exit_reasons", [])
        if exits and t.get("exit_reason", "") not in exits:
            continue

        # Date range
        df = filters.get("date_from", "")
        if df and t.get("opened_at", "") < df:
            continue
        dt = filters.get("date_to", "")
        if dt and t.get("opened_at", "") > dt:
            continue

        # PnL range
        pnl = t.get("pnl_usd", 0)
        if filters.get("min_pnl") is not None and pnl < filters["min_pnl"]:
            continue
        if filters.get("max_pnl") is not None and pnl > filters["max_pnl"]:
            continue

        # Duration
        dur = t.get("duration_minutes", 0)
        if filters.get("min_duration") is not None and dur < filters["min_duration"]:
            continue
        if filters.get("max_duration") is not None and dur > filters["max_duration"]:
            continue

        # BE / Trailing
        if filters.get("had_be") is True and not t.get("sl_moved_to_be"):
            continue
        if filters.get("had_trailing") is True and not t.get("trailing_active"):
            continue

        # Search
        q = (filters.get("search") or "").lower()
        if q:
            searchable = f"{t.get('strategy_name','')} {t.get('symbol','')} {t.get('category','')}".lower()
            if q not in searchable:
                continue

        result.append(t)

    # Sort by date desc
    result.sort(key=lambda x: x.get("opened_at", ""), reverse=True)

    # Compute stats on filtered
    stats = _compute_filtered_stats(result)

    return {
        "trades": result[:500],
        "total_found": len(result),
        "stats": stats,
    }


def _compute_filtered_stats(trades):
    if not trades:
        return {"total": 0}

    wins = sum(1 for t in trades if t.get("outcome") == "win")
    pnls = [t.get("pnl_usd", 0) for t in trades]
    gross_p = sum(p for p in pnls if p > 0)
    gross_l = abs(sum(p for p in pnls if p < 0))

    return {
        "total": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate": round(wins / len(trades) * 100, 1),
        "total_pnl": round(sum(pnls), 2),
        "avg_pnl": round(sum(pnls) / len(trades), 2),
        "best": round(max(pnls), 2),
        "worst": round(min(pnls), 2),
        "profit_factor": round(gross_p / gross_l, 2) if gross_l > 0 else 99.9,
        "strategies_count": len(set(t.get("_strategy_id", "") for t in trades)),
        "symbols_count": len(set(t.get("symbol", "") for t in trades)),
    }


# ══════ SIDE-BY-SIDE COMPARISON ══════

def compare_strategies(strategy_ids):
    """Compare 2-5 strategies side by side."""
    from backend.api.lifecycle_manager import compute_strategy_stats

    if len(strategy_ids) < 2:
        return {"success": False, "error": "حداقل ۲ استراتژی انتخاب کنید"}
    if len(strategy_ids) > 5:
        strategy_ids = strategy_ids[:5]

    comparisons = []
    for sid in strategy_ids:
        try:
            stats = compute_strategy_stats(sid)
            comparisons.append(stats)
        except Exception:
            comparisons.append({"strategy_id": sid, "strategy_name": sid, "total": 0})

    # Determine best in each category
    metrics = [
        {"key": "win_rate", "name_fa": "Win Rate", "higher_better": True},
        {"key": "total_pnl", "name_fa": "سود کل", "higher_better": True},
        {"key": "profit_factor", "name_fa": "Profit Factor", "higher_better": True},
        {"key": "avg_pnl", "name_fa": "میانگین سود", "higher_better": True},
        {"key": "avg_win", "name_fa": "میانگین برد", "higher_better": True},
        {"key": "avg_loss", "name_fa": "میانگین باخت", "higher_better": False},
        {"key": "max_win_streak", "name_fa": "بردهای متوالی", "higher_better": True},
        {"key": "max_loss_streak", "name_fa": "باخت‌های متوالی", "higher_better": False},
        {"key": "max_drawdown", "name_fa": "حداکثر افت", "higher_better": False},
        {"key": "avg_duration_min", "name_fa": "میانگین مدت (دقیقه)", "higher_better": False},
        {"key": "total", "name_fa": "کل معاملات", "higher_better": True},
    ]

    for m in metrics:
        vals = [s.get(m["key"], 0) for s in comparisons]
        if m["higher_better"]:
            best_idx = vals.index(max(vals)) if vals else -1
        else:
            non_zero = [(v, i) for i, v in enumerate(vals) if v != 0]
            best_idx = min(non_zero, key=lambda x: x[0])[1] if non_zero else -1
        m["best_index"] = best_idx
        m["values"] = vals

    return {
        "success": True,
        "strategies": comparisons,
        "metrics": metrics,
        "count": len(comparisons),
    }


# ══════ PERFORMANCE HEATMAP ══════

def performance_heatmap(filters=None):
    """Generate hour x day-of-week performance heatmap."""
    result = filter_trades(filters)
    trades = result.get("trades", [])

    heatmap = {}  # {day: {hour: {count, wins, pnl}}}
    days_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]

    for day_idx in range(7):
        heatmap[day_idx] = {}
        for hour in range(24):
            heatmap[day_idx][hour] = {"count": 0, "wins": 0, "pnl": 0}

    for t in trades:
        try:
            opened = t.get("opened_at", "")
            dt = datetime.fromisoformat(opened.replace("Z", "+00:00"))
            day = dt.weekday()
            hour = dt.hour
            heatmap[day][hour]["count"] += 1
            if t.get("outcome") == "win":
                heatmap[day][hour]["wins"] += 1
            heatmap[day][hour]["pnl"] += t.get("pnl_usd", 0)
        except Exception:
            continue

    # Flatten for frontend
    cells = []
    for day in range(7):
        for hour in range(24):
            info = heatmap[day][hour]
            if info["count"] > 0:
                wr = round(info["wins"] / info["count"] * 100)
                cells.append({
                    "day": day, "day_fa": days_fa[day],
                    "hour": hour,
                    "count": info["count"],
                    "win_rate": wr,
                    "pnl": round(info["pnl"], 2),
                })

    return {"cells": cells, "days": days_fa, "total_trades": len(trades)}


# ══════ CSV EXPORT ══════

def export_csv(filters=None):
    """Export filtered trades to CSV file."""
    result = filter_trades(filters)
    trades = result.get("trades", [])

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Strategy", "Category", "Symbol", "Timeframe", "Direction",
        "Entry Price", "Exit Price", "SL", "TP1",
        "PnL (pips)", "PnL ($)", "Outcome", "Exit Reason",
        "Duration (min)", "BE Used", "Trailing Used", "Partial Closes",
        "Opened At", "Closed At", "Events Count",
    ])

    for t in trades:
        writer.writerow([
            t.get("strategy_name", ""),
            t.get("category", ""),
            t.get("symbol", ""),
            t.get("timeframe", ""),
            t.get("direction", ""),
            t.get("entry_price", 0),
            t.get("exit_price", 0),
            t.get("sl_price", 0),
            t.get("tp1_price", 0),
            t.get("pnl_pips", 0),
            t.get("pnl_usd", 0),
            t.get("outcome", ""),
            t.get("exit_reason", ""),
            round(t.get("duration_minutes", 0), 1),
            "Yes" if t.get("sl_moved_to_be") else "No",
            "Yes" if t.get("trailing_active") else "No",
            len(t.get("partial_closes", [])),
            t.get("opened_at", ""),
            t.get("closed_at", ""),
            len(t.get("events", [])),
        ])

    csv_content = output.getvalue()

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"track_export_{timestamp}.csv"
    filepath = os.path.join(EXPORT_DIR, filename)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        f.write(csv_content)

    return {
        "success": True,
        "filename": filename,
        "filepath": filepath,
        "total_rows": len(trades),
        "stats": result.get("stats", {}),
    }


def export_html_report(filters=None):
    """Export filtered trades to HTML report."""
    result = filter_trades(filters)
    trades = result.get("trades", [])
    stats = result.get("stats", {})
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8">
<title>Whilber-AI Track Record Report — {now}</title>
<style>
body{{font-family:Tahoma,sans-serif;background:#f5f5f5;color:#222;padding:20px;direction:rtl;}}
h1{{color:#0369a1;margin-bottom:4px;}}
.sub{{color:#666;font-size:13px;margin-bottom:16px;}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;}}
.stat{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px 16px;text-align:center;min-width:100px;}}
.stat .v{{font-size:22px;font-weight:800;}}.stat .l{{font-size:11px;color:#666;}}
table{{width:100%;border-collapse:collapse;font-size:11px;background:#fff;}}
th{{background:#f0f0f0;padding:6px 8px;text-align:right;border-bottom:2px solid #ddd;}}
td{{padding:5px 8px;border-bottom:1px solid #eee;}}
tr:hover{{background:#f9f9f9;}}
.win{{color:#16a34a;font-weight:700;}}.loss{{color:#dc2626;font-weight:700;}}
@media print{{body{{padding:0;}}}}
</style></head><body>
<h1>📜 Whilber-AI — گزارش سوابق معاملاتی</h1>
<div class="sub">تاریخ تولید: {now} | کل معاملات: {stats.get('total',0)} | Win Rate: {stats.get('win_rate',0)}%</div>
<div class="stats">
<div class="stat"><div class="v">{stats.get('total',0)}</div><div class="l">معاملات</div></div>
<div class="stat"><div class="v" style="color:{'#16a34a' if stats.get('win_rate',0)>=50 else '#dc2626'};">{stats.get('win_rate',0)}%</div><div class="l">Win Rate</div></div>
<div class="stat"><div class="v" style="color:{'#16a34a' if stats.get('total_pnl',0)>=0 else '#dc2626'};">${stats.get('total_pnl',0)}</div><div class="l">سود کل</div></div>
<div class="stat"><div class="v">{stats.get('profit_factor',0)}</div><div class="l">Profit Factor</div></div>
<div class="stat"><div class="v" style="color:#16a34a;">${stats.get('best',0)}</div><div class="l">بهترین</div></div>
<div class="stat"><div class="v" style="color:#dc2626;">${stats.get('worst',0)}</div><div class="l">بدترین</div></div>
</div>
<table><thead><tr>
<th>#</th><th>استراتژی</th><th>نماد</th><th>جهت</th><th>ورود</th><th>خروج</th>
<th>PnL ($)</th><th>PnL (pip)</th><th>نتیجه</th><th>دلیل</th><th>مدت</th><th>تاریخ</th>
</tr></thead><tbody>"""

    for i, t in enumerate(trades[:200]):
        cls = "win" if t.get("outcome") == "win" else "loss"
        pnl = t.get("pnl_usd", 0)
        html += f"""<tr>
<td>{i+1}</td><td>{t.get('strategy_name','')}</td><td>{t.get('symbol','')}</td>
<td>{t.get('direction','')}</td><td>{t.get('entry_price',0)}</td><td>{t.get('exit_price',0)}</td>
<td class="{cls}">{'+' if pnl>=0 else ''}{pnl}</td><td>{t.get('pnl_pips',0)}</td>
<td class="{cls}">{'✅' if t.get('outcome')=='win' else '❌'}</td>
<td>{t.get('exit_reason','')}</td><td>{round(t.get('duration_minutes',0))}m</td>
<td>{(t.get('opened_at',''))[:16]}</td></tr>"""

    html += """</tbody></table>
<div style="margin-top:16px;text-align:center;color:#999;font-size:11px;">
Generated by Whilber-AI Signal Tracker</div></body></html>"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"track_report_{timestamp}.html"
    filepath = os.path.join(EXPORT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "success": True,
        "filename": filename,
        "filepath": filepath,
        "total_rows": min(len(trades), 200),
    }


# ══════ AVAILABLE FILTER OPTIONS ══════

def get_filter_options():
    """Return all available filter values."""
    from backend.api.tracker_engine import get_all_strategy_ids, load_records

    symbols = set()
    categories = set()
    timeframes = set()
    strategies = []

    for sid in get_all_strategy_ids():
        rec = load_records(sid)
        trades = rec.get("trades", [])
        if not trades:
            continue
        name = trades[0].get("strategy_name", sid)
        cat = trades[0].get("category", "")
        strategies.append({"id": sid, "name": name, "category": cat, "count": len(trades)})
        for t in trades:
            symbols.add(t.get("symbol", ""))
            if t.get("category"):
                categories.add(t["category"])
            if t.get("timeframe"):
                timeframes.add(t["timeframe"])

    return {
        "symbols": sorted(symbols),
        "categories": sorted(categories),
        "timeframes": sorted(timeframes),
        "strategies": sorted(strategies, key=lambda x: -x["count"]),
        "directions": ["BUY", "SELL"],
        "outcomes": ["win", "loss"],
        "exit_reasons": ["tp", "sl", "trailing", "break_even", "manual", "tp_recovery", "sl_recovery"],
    }
