"""
Whilber-AI — Trade Lifecycle Manager
========================================
Full trade lifecycle from signal to close:
  Signal → Confirm → Entry → Monitor → BE → Partial → Trail → Exit → Report
Each step is logged with timestamp and price.
Computes per-strategy stats after each close.
"""

import json
import os
import math
from datetime import datetime, timezone
from collections import defaultdict

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
TRACK_DIR = os.path.join(PROJECT_DIR, "track_records")

PIP_MAP = {
    "XAUUSD": 0.1, "XAGUSD": 0.01, "EURUSD": 0.0001, "GBPUSD": 0.0001,
    "AUDUSD": 0.0001, "USDCAD": 0.0001, "NZDUSD": 0.0001, "USDCHF": 0.0001,
    "USDJPY": 0.01, "BTCUSD": 1.0, "ETHUSD": 0.1, "US30": 1.0, "NAS100": 1.0,
}
TV_MAP = {
    "XAUUSD": 1.0, "XAGUSD": 50.0, "EURUSD": 10.0, "GBPUSD": 10.0,
    "AUDUSD": 10.0, "USDCAD": 10.0, "NZDUSD": 10.0, "USDCHF": 10.0,
    "USDJPY": 6.5, "BTCUSD": 1.0, "ETHUSD": 1.0, "US30": 1.0, "NAS100": 1.0,
}

# ══════ LIFECYCLE STAGES ══════
STAGES = {
    "signal_detected": {"order": 1, "icon": "📡", "fa": "سیگنال شناسایی شد"},
    "entry_confirmed": {"order": 2, "icon": "🟢", "fa": "ورود تأیید شد"},
    "in_loss": {"order": 3, "icon": "🟠", "fa": "در ضرر"},
    "near_be": {"order": 4, "icon": "🟡", "fa": "نزدیک Break Even"},
    "be_activated": {"order": 5, "icon": "💛", "fa": "SL به ورود رفت"},
    "in_profit": {"order": 6, "icon": "🟢", "fa": "در سود"},
    "partial_close_1": {"order": 7, "icon": "💰", "fa": "سیو سود مرحله ۱"},
    "partial_close_2": {"order": 8, "icon": "💰", "fa": "سیو سود مرحله ۲"},
    "trailing_active": {"order": 9, "icon": "🔄", "fa": "تریلینگ فعال"},
    "near_tp": {"order": 10, "icon": "🎯", "fa": "نزدیک TP"},
    "near_sl": {"order": 11, "icon": "🔴", "fa": "نزدیک SL"},
    "closed_tp": {"order": 12, "icon": "✅", "fa": "بسته شد — TP"},
    "closed_sl": {"order": 13, "icon": "❌", "fa": "بسته شد — SL"},
    "closed_trailing": {"order": 14, "icon": "🔄", "fa": "بسته شد — Trailing"},
    "closed_be": {"order": 15, "icon": "🟡", "fa": "بسته شد — Break Even"},
    "closed_manual": {"order": 16, "icon": "✋", "fa": "بسته شد — دستی"},
    "closed_recovery": {"order": 17, "icon": "🔧", "fa": "بسته شد — بازیابی"},
}


def process_tick(trade, current_price, tick_bid, tick_ask):
    """
    Process one price tick for an active trade.
    Returns: {changed: bool, closed: bool, exit_price, exit_reason, events: []}
    """
    direction = trade.get("direction", "BUY")
    entry = float(trade["entry_price"])
    sl = float(trade["sl_price"])
    tp1 = float(trade.get("tp1_price", 0))
    tp2 = float(trade.get("tp2_price", 0))
    tp3 = float(trade.get("tp3_price", 0))
    symbol = trade.get("symbol", "XAUUSD")
    lot = float(trade.get("lot_size", 0.01))

    pip = PIP_MAP.get(symbol, 0.0001)
    tv = TV_MAP.get(symbol, 10.0)
    cp = float(current_price)

    result = {"changed": False, "closed": False, "exit_price": 0,
              "exit_reason": "", "events": []}
    now = datetime.now(timezone.utc).isoformat()

    # Update tracking prices
    old_high = trade.get("highest_price", entry)
    old_low = trade.get("lowest_price", entry)
    trade["current_price"] = cp
    trade["highest_price"] = max(old_high, cp)
    trade["lowest_price"] = min(old_low, cp)

    # PnL calculation
    if direction == "BUY":
        pnl_pips = (cp - entry) / pip
        sl_dist_pips = (entry - sl) / pip
    else:
        pnl_pips = (entry - cp) / pip
        sl_dist_pips = (sl - entry) / pip

    pnl_usd = pnl_pips * tv * lot
    trade["current_pnl_pips"] = round(pnl_pips, 1)
    trade["current_pnl_usd"] = round(pnl_usd, 2)

    if sl_dist_pips <= 0:
        sl_dist_pips = 50  # fallback

    pct_of_sl = pnl_pips / sl_dist_pips  # 0=entry, 1=R:R=1, -1=SL

    # ── CHECK SL HIT ──
    sl_hit = False
    if sl > 0:
        if direction == "BUY" and tick_bid <= sl:
            sl_hit = True
        elif direction == "SELL" and tick_ask >= sl:
            sl_hit = True

    if sl_hit:
        result["closed"] = True
        result["exit_price"] = sl
        if trade.get("sl_moved_to_be", False) and abs(sl - entry) < pip * 3:
            result["exit_reason"] = "break_even"
            result["events"].append(_event(now, "closed_be", sl,
                f"بسته شد در Break Even @ {sl} | PnL ≈ $0"))
        else:
            result["exit_reason"] = "sl"
            result["events"].append(_event(now, "closed_sl", sl,
                f"SL فعال شد @ {sl} | PnL: {pnl_usd:.2f}$"))
        return result

    # ── CHECK TP1 HIT ──
    if tp1 > 0:
        tp_hit = False
        if direction == "BUY" and tick_bid >= tp1:
            tp_hit = True
        elif direction == "SELL" and tick_ask <= tp1:
            tp_hit = True

        if tp_hit:
            # If has TP2/TP3, do partial close at TP1
            if (tp2 > 0 or tp3 > 0) and not _has_stage(trade, "partial_close_1"):
                result["events"].append(_event(now, "partial_close_1", tp1,
                    f"TP1 رسید @ {tp1} — ⅓ سیو سود | SL→ ورود"))
                trade["sl_price"] = entry
                trade["sl_moved_to_be"] = True
                trade["partial_closes"] = trade.get("partial_closes", [])
                trade["partial_closes"].append({"pct": 33, "price": tp1, "time": now, "level": "TP1"})
                result["changed"] = True
            elif not tp2 and not tp3:
                # Full close at TP1
                result["closed"] = True
                result["exit_price"] = tp1
                result["exit_reason"] = "tp"
                result["events"].append(_event(now, "closed_tp", tp1,
                    f"TP1 رسید — بسته شد @ {tp1} | PnL: {pnl_usd:.2f}$"))
                return result

    # ── CHECK TP2 HIT ──
    if tp2 > 0 and _has_stage(trade, "partial_close_1"):
        tp2_hit = False
        if direction == "BUY" and tick_bid >= tp2:
            tp2_hit = True
        elif direction == "SELL" and tick_ask <= tp2:
            tp2_hit = True

        if tp2_hit and not _has_stage(trade, "partial_close_2"):
            if tp3 > 0:
                result["events"].append(_event(now, "partial_close_2", tp2,
                    f"TP2 رسید @ {tp2} — ⅓ دیگر سیو | SL→ TP1"))
                trade["sl_price"] = tp1
                trade["partial_closes"].append({"pct": 33, "price": tp2, "time": now, "level": "TP2"})
                result["changed"] = True
            else:
                result["closed"] = True
                result["exit_price"] = tp2
                result["exit_reason"] = "tp"
                result["events"].append(_event(now, "closed_tp", tp2,
                    f"TP2 رسید — بسته شد @ {tp2} | PnL: {pnl_usd:.2f}$"))
                return result

    # ── CHECK TP3 HIT ──
    if tp3 > 0 and _has_stage(trade, "partial_close_2"):
        tp3_hit = False
        if direction == "BUY" and tick_bid >= tp3:
            tp3_hit = True
        elif direction == "SELL" and tick_ask <= tp3:
            tp3_hit = True

        if tp3_hit:
            result["closed"] = True
            result["exit_price"] = tp3
            result["exit_reason"] = "tp"
            result["events"].append(_event(now, "closed_tp", tp3,
                f"TP3 رسید — کامل بسته شد @ {tp3} | PnL: {pnl_usd:.2f}$"))
            return result

    # ── TRAILING STOP ──
    trailing = trade.get("trailing_active", False)
    trail_dist = trade.get("trailing_distance", 0)

    # Activate trailing at R:R >= 1.5
    if not trailing and pct_of_sl >= 1.5 and trade.get("sl_moved_to_be", False):
        trail_dist = sl_dist_pips * pip * 0.7  # 70% of SL distance
        trade["trailing_active"] = True
        trade["trailing_distance"] = trail_dist
        result["events"].append(_event(now, "trailing_active", cp,
            f"تریلینگ فعال شد | فاصله: {trail_dist/pip:.0f} pip"))
        result["changed"] = True

    # Update trailing SL
    if trailing and trail_dist > 0:
        if direction == "BUY":
            new_trail_sl = trade["highest_price"] - trail_dist
            if new_trail_sl > trade["sl_price"]:
                trade["sl_price"] = round(new_trail_sl, 6)
                result["changed"] = True
        else:
            new_trail_sl = trade["lowest_price"] + trail_dist
            if new_trail_sl < trade["sl_price"]:
                trade["sl_price"] = round(new_trail_sl, 6)
                result["changed"] = True

        # Trailing SL hit
        if direction == "BUY" and tick_bid <= trade["sl_price"]:
            result["closed"] = True
            result["exit_price"] = trade["sl_price"]
            result["exit_reason"] = "trailing"
            result["events"].append(_event(now, "closed_trailing", trade["sl_price"],
                f"تریلینگ SL فعال شد @ {trade['sl_price']} | PnL: {pnl_usd:.2f}$"))
            return result
        elif direction == "SELL" and tick_ask >= trade["sl_price"]:
            result["closed"] = True
            result["exit_price"] = trade["sl_price"]
            result["exit_reason"] = "trailing"
            result["events"].append(_event(now, "closed_trailing", trade["sl_price"],
                f"تریلینگ SL فعال شد @ {trade['sl_price']} | PnL: {pnl_usd:.2f}$"))
            return result

    # ── STAGE TRACKING (non-critical events) ──
    # Break Even zone
    if not trade.get("sl_moved_to_be", False):
        if pct_of_sl >= 0.5 and not _has_stage(trade, "near_be"):
            result["events"].append(_event(now, "near_be", cp,
                f"۵۰% مسیر SL طی شد — آماده BE"))
            result["changed"] = True

        if pct_of_sl >= 0.6 and not _has_stage(trade, "be_activated"):
            trade["sl_price"] = entry
            trade["sl_moved_to_be"] = True
            result["events"].append(_event(now, "be_activated", entry,
                f"SL به Break Even رفت @ {entry}"))
            result["changed"] = True

    # Near TP notification
    if tp1 > 0 and not _has_stage(trade, "near_tp"):
        if direction == "BUY":
            dist_to_tp = (tp1 - cp) / pip
        else:
            dist_to_tp = (cp - tp1) / pip
        if 0 < dist_to_tp <= 20:
            result["events"].append(_event(now, "near_tp", cp,
                f"نزدیک TP1! فاصله: {dist_to_tp:.0f} پیپ"))
            result["changed"] = True

    # Near SL warning
    if not _has_stage(trade, "near_sl") and pct_of_sl <= -0.8:
        result["events"].append(_event(now, "near_sl", cp,
            f"نزدیک SL! فاصله: {abs(pnl_pips + sl_dist_pips):.0f} پیپ"))
        result["changed"] = True

    # Status transitions
    if pct_of_sl >= 1.0 and not _has_stage(trade, "in_profit"):
        result["events"].append(_event(now, "in_profit", cp,
            f"R:R=1 رسید — در سود {pnl_usd:.2f}$"))
        result["changed"] = True
    elif pct_of_sl < -0.3 and not _has_stage(trade, "in_loss"):
        result["events"].append(_event(now, "in_loss", cp,
            f"در ضرر {pnl_usd:.2f}$"))
        result["changed"] = True

    trade["current_stage"] = _get_current_stage(trade, pct_of_sl)
    return result


def _event(time_str, stage, price, detail):
    info = STAGES.get(stage, {})
    return {
        "time": time_str,
        "type": stage,
        "icon": info.get("icon", "📌"),
        "stage_fa": info.get("fa", stage),
        "price": float(price),
        "detail": detail,
    }


def _has_stage(trade, stage):
    for ev in trade.get("events", []):
        if ev.get("type") == stage:
            return True
    return False


def _get_current_stage(trade, pct_of_sl):
    if trade.get("trailing_active"):
        return "trailing_active"
    if trade.get("sl_moved_to_be"):
        if pct_of_sl >= 1.0:
            return "in_profit"
        return "be_activated"
    if pct_of_sl >= 0.5:
        return "near_be"
    if pct_of_sl < -0.5:
        return "near_sl"
    if pct_of_sl < 0:
        return "in_loss"
    return "entry_confirmed"


# ══════ STATS COMPUTATION ══════

def compute_strategy_stats(strategy_id):
    """Compute comprehensive stats for a strategy."""
    from backend.api.tracker_engine import load_records
    records = load_records(strategy_id)
    trades = records.get("trades", [])

    if not trades:
        return {"total": 0, "strategy_id": strategy_id}

    wins = [t for t in trades if t.get("outcome") == "win"]
    losses = [t for t in trades if t.get("outcome") == "loss"]
    pnls = [t.get("pnl_usd", 0) for t in trades]
    win_pnls = [t.get("pnl_usd", 0) for t in wins]
    loss_pnls = [t.get("pnl_usd", 0) for t in losses]

    # Win/loss streaks
    max_win_streak = 0
    max_loss_streak = 0
    cur_streak = 0
    prev_outcome = None
    for t in reversed(trades):
        out = t.get("outcome", "")
        if out == prev_outcome:
            cur_streak += 1
        else:
            cur_streak = 1
        if out == "win":
            max_win_streak = max(max_win_streak, cur_streak)
        elif out == "loss":
            max_loss_streak = max(max_loss_streak, cur_streak)
        prev_outcome = out

    # By symbol
    by_symbol = defaultdict(lambda: {"total": 0, "wins": 0, "pnl": 0})
    for t in trades:
        sym = t.get("symbol", "")
        by_symbol[sym]["total"] += 1
        if t.get("outcome") == "win":
            by_symbol[sym]["wins"] += 1
        by_symbol[sym]["pnl"] += t.get("pnl_usd", 0)

    symbol_stats = {}
    for sym, info in by_symbol.items():
        symbol_stats[sym] = {
            "total": info["total"],
            "wins": info["wins"],
            "win_rate": round(info["wins"] / info["total"] * 100, 1) if info["total"] else 0,
            "pnl": round(info["pnl"], 2),
        }

    # By exit reason
    by_exit = defaultdict(lambda: {"count": 0, "pnl": 0})
    for t in trades:
        reason = t.get("exit_reason", "unknown")
        by_exit[reason]["count"] += 1
        by_exit[reason]["pnl"] += t.get("pnl_usd", 0)

    exit_stats = {}
    for reason, info in by_exit.items():
        exit_stats[reason] = {
            "count": info["count"],
            "pnl": round(info["pnl"], 2),
            "avg_pnl": round(info["pnl"] / info["count"], 2) if info["count"] else 0,
        }

    # By hour
    by_hour = defaultdict(lambda: {"count": 0, "wins": 0, "pnl": 0})
    for t in trades:
        try:
            opened = t.get("opened_at", "")
            hour = int(opened[11:13])
            by_hour[hour]["count"] += 1
            if t.get("outcome") == "win":
                by_hour[hour]["wins"] += 1
            by_hour[hour]["pnl"] += t.get("pnl_usd", 0)
        except Exception:
            pass

    hour_stats = {}
    for h in range(24):
        info = by_hour[h]
        if info["count"] > 0:
            hour_stats[str(h)] = {
                "count": info["count"],
                "win_rate": round(info["wins"] / info["count"] * 100, 1),
                "pnl": round(info["pnl"], 2),
            }

    # Durations
    durations = [t.get("duration_minutes", 0) for t in trades if t.get("duration_minutes", 0) > 0]

    # Profit Factor
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.9 if gross_profit > 0 else 0)

    # Equity curve
    equity = []
    running = 0
    for t in reversed(trades):
        running += t.get("pnl_usd", 0)
        equity.append(round(running, 2))

    # Max drawdown
    peak = 0
    max_dd = 0
    for eq in equity:
        peak = max(peak, eq)
        dd = peak - eq
        max_dd = max(max_dd, dd)

    return {
        "strategy_id": strategy_id,
        "strategy_name": trades[0].get("strategy_name", strategy_id) if trades else strategy_id,
        "category": trades[0].get("category", "") if trades else "",
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "total_pnl": round(sum(pnls), 2),
        "avg_pnl": round(sum(pnls) / len(trades), 2),
        "avg_win": round(sum(win_pnls) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(loss_pnls) / len(losses), 2) if losses else 0,
        "best_trade": round(max(pnls), 2) if pnls else 0,
        "worst_trade": round(min(pnls), 2) if pnls else 0,
        "profit_factor": pf,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "avg_duration_min": round(sum(durations) / len(durations), 1) if durations else 0,
        "max_drawdown": round(max_dd, 2),
        "equity_curve": equity[-100:],  # Last 100 points
        "by_symbol": symbol_stats,
        "by_exit_reason": exit_stats,
        "by_hour": hour_stats,
        "last_5": [
            {"outcome": t.get("outcome", ""), "pnl": t.get("pnl_usd", 0),
             "symbol": t.get("symbol", ""), "date": t.get("closed_at", "")[:10]}
            for t in trades[:5]
        ],
        "first_trade": trades[-1].get("opened_at", "") if trades else "",
        "last_trade": trades[0].get("closed_at", "") if trades else "",
    }


def compute_category_comparison():
    """Compare all strategy categories."""
    from backend.api.tracker_engine import get_all_strategy_ids, load_records

    by_cat = defaultdict(lambda: {"total": 0, "wins": 0, "pnl": 0, "strategies": 0})
    by_sym = defaultdict(lambda: {"total": 0, "wins": 0, "pnl": 0, "strategies": set()})

    for sid in get_all_strategy_ids():
        rec = load_records(sid)
        trades = rec.get("trades", [])
        if not trades:
            continue

        cat = trades[0].get("category", "") or "other"
        by_cat[cat]["total"] += len(trades)
        by_cat[cat]["strategies"] += 1
        by_cat[cat]["wins"] += sum(1 for t in trades if t.get("outcome") == "win")
        by_cat[cat]["pnl"] += sum(t.get("pnl_usd", 0) for t in trades)

        for t in trades:
            sym = t.get("symbol", "")
            by_sym[sym]["total"] += 1
            if t.get("outcome") == "win":
                by_sym[sym]["wins"] += 1
            by_sym[sym]["pnl"] += t.get("pnl_usd", 0)
            by_sym[sym]["strategies"].add(sid)

    cats = []
    for cat, info in sorted(by_cat.items(), key=lambda x: -x[1]["pnl"]):
        cats.append({
            "category": cat,
            "strategies": info["strategies"],
            "total_trades": info["total"],
            "wins": info["wins"],
            "win_rate": round(info["wins"] / info["total"] * 100, 1) if info["total"] else 0,
            "total_pnl": round(info["pnl"], 2),
        })

    syms = []
    for sym, info in sorted(by_sym.items(), key=lambda x: -x[1]["pnl"]):
        syms.append({
            "symbol": sym,
            "strategies": len(info["strategies"]),
            "total_trades": info["total"],
            "wins": info["wins"],
            "win_rate": round(info["wins"] / info["total"] * 100, 1) if info["total"] else 0,
            "total_pnl": round(info["pnl"], 2),
        })

    return {"by_category": cats, "by_symbol": syms}


def get_trade_timeline(strategy_id, trade_id):
    """Get full event timeline for a specific trade."""
    from backend.api.tracker_engine import load_records
    rec = load_records(strategy_id)
    for t in rec.get("trades", []):
        if t.get("id") == trade_id:
            events = t.get("events", [])
            for e in events:
                stage_info = STAGES.get(e.get("type", ""), {})
                e["icon"] = stage_info.get("icon", "📌")
                e["stage_fa"] = stage_info.get("fa", e.get("type", ""))
            return {
                "trade": t,
                "events": events,
                "total_events": len(events),
            }
    return {"trade": None, "events": [], "total_events": 0}


# ═══ ENHANCED EVENT LOGGING (added by audit fix) ═══════════

def log_trade_event(trade, event_type, price, detail="", extra=None):
    """Universal event logger — ensures every trade change is recorded."""
    from datetime import datetime, timezone
    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "price": price,
        "detail": detail,
    }
    if extra:
        event.update(extra)
    trade.setdefault("events", []).append(event)
    
    # Update trade metadata
    if event_type == "price_update":
        direction = trade.get("direction", "BUY")
        entry = trade.get("entry_price", 0)
        pip = _get_pip_for_symbol(trade.get("symbol", "XAUUSD"))
        if direction == "BUY":
            pnl_pips = (price - entry) / pip if pip else 0
        else:
            pnl_pips = (entry - price) / pip if pip else 0
        
        # Track max profit / max drawdown
        current_max = trade.get("max_profit_pips", 0)
        current_dd = trade.get("max_drawdown_pips", 0)
        if pnl_pips > current_max:
            trade["max_profit_pips"] = round(pnl_pips, 1)
            trade["max_profit_price"] = price
        if pnl_pips < current_dd:
            trade["max_drawdown_pips"] = round(pnl_pips, 1)
            trade["max_drawdown_price"] = price
        
        # Update highest/lowest
        if direction == "BUY":
            trade["highest_price"] = max(trade.get("highest_price", 0), price)
            trade["lowest_price"] = min(trade.get("lowest_price", float("inf")), price)
        else:
            trade["highest_price"] = max(trade.get("highest_price", 0), price)
            trade["lowest_price"] = min(trade.get("lowest_price", float("inf")), price)
    
    return event


def _get_pip_for_symbol(symbol):
    """Get pip value for a symbol."""
    pips = {
        "XAUUSD": 0.1, "XAGUSD": 0.01,
        "EURUSD": 0.0001, "GBPUSD": 0.0001, "AUDUSD": 0.0001,
        "USDCAD": 0.0001, "NZDUSD": 0.0001, "USDCHF": 0.0001,
        "USDJPY": 0.01, "BTCUSD": 1.0,
        "US30": 1.0, "NAS100": 1.0,
    }
    return pips.get(symbol, 0.0001)

# ═══ END ENHANCED EVENT LOGGING ══════════════════════════════
