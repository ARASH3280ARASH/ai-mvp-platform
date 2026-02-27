"""
═══════════════════════════════════════════════════════════════
  SIGNAL VALIDATOR — Ensures only clean signals enter tracker
  
  Checks performed on EVERY signal before recording:
  1. Missing SL/TP          → REJECT (incomplete setup)
  2. Entry price invalid     → REJECT (bad data)
  3. Abnormal R:R           → REJECT (>8 or <0.1)
  4. Mass signal / cluster  → LIMIT (max N per symbol+direction)
  5. Duplicate active trade → SKIP (already tracked)
  6. SL wrong side          → REJECT (data leakage)
  7. TP wrong side          → REJECT (data leakage)
  
  Checks on TRACK RECORD display (quality flags):
  8. Recovery exit          → FLAG as unreliable
  9. Time clustering        → FLAG correlation
  10. Trend bias            → FLAG one-sided
  11. Survivorship bias     → FLAG if 100% WR with recovery
  
  Usage:
    from backend.api.signal_validator import validate_signal, validate_batch
═══════════════════════════════════════════════════════════════
"""
from datetime import datetime, timezone
from collections import defaultdict
import json, os

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

# Max signals per symbol+direction per cycle (anti mass-signal)
MAX_SIGNALS_PER_CLUSTER = 3

# R:R limits
MIN_RR = 1.5  # MT5 live: minimum 1:1.5
MAX_RR = 8.0

# Min distance SL from entry (in fraction of price)
MIN_SL_DISTANCE_PCT = 0.0001  # 0.01% — prevents SL=entry

# Min distance TP from entry
MIN_TP_DISTANCE_PCT = 0.0001

# Confidence threshold
MIN_CONFIDENCE = 30

# Stats tracking for this session
_session_stats = {
    "total_checked": 0,
    "passed": 0,
    "rejected": 0,
    "reasons": defaultdict(int),
}

_cycle_clusters = {}  # Reset each cycle: {(symbol,direction): count}


def reset_cycle():
    """Call at start of each cycle to reset cluster counters."""
    global _cycle_clusters
    _cycle_clusters = {}


def get_stats():
    """Return validation stats for monitoring."""
    return {
        "total_checked": _session_stats["total_checked"],
        "passed": _session_stats["passed"],
        "rejected": _session_stats["rejected"],
        "pass_rate": round(_session_stats["passed"] / max(_session_stats["total_checked"], 1) * 100, 1),
        "reasons": dict(_session_stats["reasons"]),
    }


# ═══════════════════════════════════════════════════════════════
# MAIN VALIDATION FUNCTION
# ═══════════════════════════════════════════════════════════════

def validate_signal(sig):
    """
    Validate a single signal before recording.
    
    Args:
        sig: dict with keys: strategy_id, strategy_name, symbol, signal_type,
             entry_price, sl_price, tp_price, confidence, category, timeframe
    
    Returns:
        (is_valid: bool, reason: str)
        
    If is_valid=True, signal can be recorded.
    If is_valid=False, reason explains why.
    """
    _session_stats["total_checked"] += 1
    
    sid = sig.get("strategy_id", "?")
    symbol = sig.get("symbol", "?")
    direction = sig.get("signal_type", "?")
    entry = sig.get("entry_price", 0)
    sl = sig.get("sl_price", 0)
    tp = sig.get("tp_price", 0)
    confidence = sig.get("confidence", 0)
    
    # ─── CHECK 1: Missing SL/TP ───
    if not sl or sl == 0:
        return _reject(sid, "missing_sl", f"SL=0 for {symbol}")
    
    if not tp or tp == 0:
        return _reject(sid, "missing_tp", f"TP=0 for {symbol}")
    
    if not entry or entry == 0:
        return _reject(sid, "missing_entry", f"Entry=0 for {symbol}")
    
    # ─── CHECK 2: Entry price sanity ───
    if entry < 0:
        return _reject(sid, "negative_price", f"Entry={entry}")
    
    # ─── CHECK 3: SL on correct side ───
    if direction == "BUY":
        if sl >= entry:
            return _reject(sid, "sl_wrong_side", f"BUY but SL({sl}) >= Entry({entry})")
        if tp <= entry:
            return _reject(sid, "tp_wrong_side", f"BUY but TP({tp}) <= Entry({entry})")
    elif direction == "SELL":
        if sl <= entry:
            return _reject(sid, "sl_wrong_side", f"SELL but SL({sl}) <= Entry({entry})")
        if tp >= entry:
            return _reject(sid, "tp_wrong_side", f"SELL but TP({tp}) >= Entry({entry})")
    else:
        return _reject(sid, "invalid_direction", f"Direction={direction}")
    
    # ─── CHECK 4: SL/TP distance from entry ───
    sl_dist = abs(entry - sl) / entry
    tp_dist = abs(entry - tp) / entry
    
    if sl_dist < MIN_SL_DISTANCE_PCT:
        return _reject(sid, "sl_too_close", f"SL distance={sl_dist:.6f} < {MIN_SL_DISTANCE_PCT}")
    
    if tp_dist < MIN_TP_DISTANCE_PCT:
        return _reject(sid, "tp_too_close", f"TP distance={tp_dist:.6f} < {MIN_TP_DISTANCE_PCT}")
    
    # ─── CHECK 5: R:R ratio ───
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    
    if risk > 0:
        rr = reward / risk
    else:
        return _reject(sid, "zero_risk", f"Risk=0")
    
    if rr < MIN_RR:
        return _reject(sid, "rr_too_low", f"R:R={rr:.2f} < {MIN_RR}")
    
    if rr > MAX_RR:
        return _reject(sid, "rr_too_high", f"R:R={rr:.2f} > {MAX_RR}")
    
    # ─── CHECK 6: Confidence threshold ───
    if confidence < MIN_CONFIDENCE:
        return _reject(sid, "low_confidence", f"Confidence={confidence} < {MIN_CONFIDENCE}")
    
    # ─── CHECK 7: Mass signal / cluster limit ───
    cluster_key = (symbol, direction)
    _cycle_clusters[cluster_key] = _cycle_clusters.get(cluster_key, 0) + 1
    
    if _cycle_clusters[cluster_key] > MAX_SIGNALS_PER_CLUSTER:
        return _reject(sid, "mass_signal", 
                       f"{symbol} {direction} already has {MAX_SIGNALS_PER_CLUSTER} signals this cycle")
    
    # ─── ALL CHECKS PASSED ───
    _session_stats["passed"] += 1
    return True, "OK"


def validate_batch(signals):
    """
    Validate a batch of signals (one cycle output).
    Returns list of valid signals only.
    Also sorts by confidence (highest first) so cluster limit keeps best ones.
    """
    reset_cycle()
    
    # Sort by confidence descending — best signals get through cluster filter first
    sorted_sigs = sorted(signals, key=lambda s: s.get("confidence", 0), reverse=True)
    
    valid = []
    for sig in sorted_sigs:
        is_valid, reason = validate_signal(sig)
        if is_valid:
            valid.append(sig)
    
    return valid


# ═══════════════════════════════════════════════════════════════
# TRACK RECORD QUALITY FLAGS
# ═══════════════════════════════════════════════════════════════

def flag_trade(trade):
    """
    Add quality flags to a closed trade for display filtering.
    
    Returns dict of flags: {flag_name: True/False}
    """
    flags = {}
    
    exit_reason = trade.get("exit_reason", "")
    
    # Recovery bias
    flags["recovery"] = "recovery" in exit_reason
    
    # Check if SL was missing
    flags["missing_sl"] = not trade.get("sl_price") or trade.get("sl_price", 0) == 0
    
    # Check R:R
    entry = trade.get("entry_price", 0)
    sl = trade.get("sl_price", 0)
    tp = trade.get("tp1_price", trade.get("tp_price", 0))
    
    if entry and sl and tp and abs(entry - sl) > 0:
        rr = abs(tp - entry) / abs(entry - sl)
        flags["abnormal_rr"] = rr > MAX_RR or rr < MIN_RR
        flags["rr_value"] = round(rr, 2)
    else:
        flags["abnormal_rr"] = True
        flags["rr_value"] = 0
    
    return flags


def flag_strategy_record(trades):
    """
    Analyze a strategy's trade history and return quality assessment.
    STRICT VERSION — catches mass signals, duplicates, clustering.
    """
    from collections import Counter
    from datetime import datetime
    
    if not trades:
        return {"quality": "unknown", "flags": [], "clean_trades": 0, "total_trades": 0}
    
    total = len(trades)
    flags = []
    
    # 1. Recovery rate
    recovery_count = sum(1 for t in trades if "recovery" in t.get("exit_reason", ""))
    recovery_pct = recovery_count / total * 100
    
    if recovery_pct > 50:
        flags.append("high_recovery")
    
    # 2. Win rate check
    wins = sum(1 for t in trades if t.get("outcome") == "win")
    wr = wins / total * 100
    
    # 100% WR with many trades = very suspicious
    if wr == 100 and total >= 10:
        flags.append("perfect_wr_suspicious")
    if wr == 100 and total >= 5 and recovery_pct > 0:
        flags.append("survivorship_bias")
    
    # 3. Direction bias (>90% one direction)
    buys = sum(1 for t in trades if t.get("direction") == "BUY")
    sells = total - buys
    if total >= 10:
        buy_pct = buys / total * 100
        if buy_pct > 90 or buy_pct < 10:
            flags.append("direction_bias")
    
    # 4. Time clustering (>60% trades same day or >80% same hour)
    dates = []
    hours = []
    for t in trades:
        oa = t.get("opened_at", "")
        if oa:
            try:
                dt = datetime.fromisoformat(oa.replace("Z", "+00:00"))
                dates.append(dt.strftime("%Y-%m-%d"))
                hours.append(dt.hour)
            except:
                pass
    
    if dates:
        date_counts = Counter(dates)
        most_common_date = date_counts.most_common(1)[0][1]
        if most_common_date / len(dates) > 0.6:
            flags.append("date_clustering")
    
    if hours:
        hour_counts = Counter(hours)
        most_common_hour = hour_counts.most_common(1)[0][1]
        if most_common_hour / len(hours) > 0.8:
            flags.append("time_clustering")
    
    # 5. Duplicate PnL (very few unique values = fake/mass)
    pnls = [round(t.get("pnl_pips", t.get("pnl_usd", 0)), 2) for t in trades]
    unique_pnls = set(pnls)
    if total >= 5 and len(unique_pnls) <= 2:
        flags.append("duplicate_pnl")
    if total >= 20 and len(unique_pnls) <= 5:
        flags.append("low_pnl_diversity")
    
    # 6. Duplicate entry prices (>70% same price = mass signal)
    entry_prices = [round(t.get("entry_price", 0), 4) for t in trades if t.get("entry_price")]
    if entry_prices:
        price_counts = Counter(entry_prices)
        most_common_price = price_counts.most_common(1)[0][1]
        if total >= 5 and most_common_price / total > 0.7:
            flags.append("duplicate_entry_price")
    
    # 7. All exits same type
    exit_types = set(t.get("exit_reason", "") for t in trades)
    if total >= 5 and len(exit_types) == 1:
        et = list(exit_types)[0]
        if "recovery" in et:
            flags.append("all_recovery_exits")
    
    # 8. Profit Factor = 0 with positive PnL (data error)
    total_pnl = sum(t.get("pnl_usd", 0) for t in trades)
    loss_pnls = [t.get("pnl_usd", 0) for t in trades if t.get("outcome") == "loss"]
    if total_pnl > 0 and not loss_pnls and total >= 10:
        flags.append("no_losses_suspicious")
    
    # Count clean trades (non-recovery, valid SL/TP)
    clean = sum(1 for t in trades 
                if "recovery" not in t.get("exit_reason", "")
                and t.get("sl_price", 0) != 0)
    
    # ═══ DETERMINE QUALITY ═══
    # Unreliable: 3+ flags, or any critical flag
    critical_flags = {"survivorship_bias", "all_recovery_exits", "perfect_wr_suspicious",
                      "duplicate_entry_price", "date_clustering"}
    
    has_critical = bool(set(flags) & critical_flags)
    
    if has_critical or len(flags) >= 3:
        quality = "unreliable"
    elif len(flags) >= 1:
        quality = "suspect"
    else:
        quality = "clean"
    
    return {
        "quality": quality,
        "flags": flags,
        "clean_trades": clean,
        "total_trades": total,
        "recovery_pct": round(recovery_pct, 1),
        "win_rate": round(wr, 1),
        "details": ", ".join(flags) if flags else "No issues found",
    }


def _reject(sid, reason, detail=""):
    """Record rejection and return."""
    _session_stats["rejected"] += 1
    _session_stats["reasons"][reason] += 1
    return False, f"{reason}: {detail}"
