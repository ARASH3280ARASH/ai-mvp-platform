"""Rebuild tracker cache — with date filter + pip-based PnL + score"""
import os, json, time, sys, glob
from datetime import datetime, timezone, timedelta

TRACK_DIR = r"C:\Users\Administrator\Desktop\mvp\track_records"
CACHE_FILE = r"C:\Users\Administrator\Desktop\mvp\data\tracker_cache.json"

# ═══ PIP VALUES (per 1 standard lot) ═══
PIP_SIZE = {
    "XAUUSD": 0.1, "XAGUSD": 0.01, "EURUSD": 0.0001, "GBPUSD": 0.0001,
    "USDJPY": 0.01, "AUDUSD": 0.0001, "USDCAD": 0.0001, "NZDUSD": 0.0001,
    "USDCHF": 0.0001, "BTCUSD": 1.0, "NAS100": 1.0, "US30": 1.0,
}

# PIP_VALUE per 0.01 lot (what tracker uses)
PIP_VALUE_001 = {
    "XAUUSD": 0.10, "XAGUSD": 0.50, "EURUSD": 0.10, "GBPUSD": 0.10,
    "USDJPY": 0.07, "AUDUSD": 0.10, "USDCAD": 0.07, "NZDUSD": 0.10,
    "USDCHF": 0.10, "BTCUSD": 0.01, "NAS100": 0.10, "US30": 0.10,
}

def calc_pips(trade):
    """Calculate PnL in pips from trade data."""
    pnl_pips = trade.get("pnl_pips", 0)
    if pnl_pips and pnl_pips != 0:
        return pnl_pips
    
    # Fallback: calculate from entry/exit prices
    entry = trade.get("entry_price", 0)
    exit_p = trade.get("exit_price", 0)
    symbol = trade.get("symbol", "")
    direction = trade.get("direction", "BUY")
    pip_size = PIP_SIZE.get(symbol, 0.0001)
    
    if entry and exit_p and pip_size:
        if direction == "BUY":
            return round((exit_p - entry) / pip_size, 1)
        else:
            return round((entry - exit_p) / pip_size, 1)
    
    # Last fallback: estimate from pnl_usd
    pnl_usd = trade.get("pnl_usd", 0)
    pip_val = PIP_VALUE_001.get(symbol, 0.10)
    if pnl_usd and pip_val:
        return round(pnl_usd / pip_val, 1)
    
    return 0


def rebuild(since_date=None):
    """
    Rebuild cache with optional date filter.
    since_date: ISO string or None for all trades
    """
    t0 = time.time()
    
    # Parse since_date
    cutoff = None
    if since_date:
        try:
            cutoff = datetime.fromisoformat(since_date.replace("Z", "+00:00"))
        except:
            cutoff = None
    
    files = [f for f in os.listdir(TRACK_DIR) if f.startswith("rec_") and f.endswith(".json")]
    ranking = []
    all_symbols = set()
    total_trades = 0
    
    for filename in files:
        filepath = os.path.join(TRACK_DIR, filename)
        sid = filename[4:-5]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                rec = json.load(f)
        except:
            continue
        
        trades = rec.get("trades", [])
        closed = [t for t in trades if t.get("status") == "closed"]
        
        # ═══ DATE FILTER ═══
        if cutoff:
            filtered = []
            for t in closed:
                opened = t.get("opened_at", "") or t.get("closed_at", "")
                if opened:
                    try:
                        dt = datetime.fromisoformat(opened.replace("Z", "+00:00"))
                        if dt >= cutoff:
                            filtered.append(t)
                    except:
                        pass
            closed = filtered
        
        if not closed:
            continue
        
        total_trades += len(closed)
        sname = closed[0].get("strategy_name", sid)
        wins = sum(1 for t in closed if t.get("outcome") == "win")
        wr = round(wins / len(closed) * 100, 1)
        
        # ═══ USD PnL ═══
        total_pnl = round(sum(t.get("pnl_usd", 0) for t in closed), 2)
        
        # ═══ PIP PnL (normalized) ═══
        pip_pnls = [calc_pips(t) for t in closed]
        total_pnl_pips = round(sum(pip_pnls), 1)
        avg_pnl_pips = round(total_pnl_pips / len(closed), 1) if closed else 0
        
        win_pips = [p for p in pip_pnls if p > 0]
        loss_pips = [p for p in pip_pnls if p < 0]
        avg_win_pips = round(sum(win_pips) / len(win_pips), 1) if win_pips else 0
        avg_loss_pips = round(sum(loss_pips) / len(loss_pips), 1) if loss_pips else 0
        
        # ═══ SCORE (normalized: WR × avg_pips) ═══
        # Higher = better. Combines win rate AND average profit in pips
        score = round((wr / 100) * avg_pnl_pips, 2) if avg_pnl_pips > 0 else round((wr / 100) * avg_pnl_pips * 0.5, 2)
        
        # ═══ SYMBOL STATS ═══
        symbols = {}
        for t in closed:
            sym = t.get("symbol", "")
            if sym:
                all_symbols.add(sym)
                if sym not in symbols:
                    symbols[sym] = {"total": 0, "wins": 0, "pnl": 0, "pnl_pips": 0}
                symbols[sym]["total"] += 1
                if t.get("outcome") == "win":
                    symbols[sym]["wins"] += 1
                symbols[sym]["pnl"] += t.get("pnl_usd", 0)
                symbols[sym]["pnl_pips"] += calc_pips(t)
        
        sym_str = ", ".join(sorted(symbols.keys())) if symbols else "-"
        
        # ═══ USD stats ═══
        wa = [t.get("pnl_usd", 0) for t in closed if t.get("outcome") == "win"]
        la = [t.get("pnl_usd", 0) for t in closed if t.get("outcome") == "loss"]
        pf = round(abs(sum(wa) / sum(la)), 2) if la and sum(la) != 0 else 0
        
        eq = []
        cs = 0
        for t in closed[-50:]:
            cs += calc_pips(t)  # equity curve in pips now
            eq.append(round(cs, 1))
        
        ranking.append({
            "strategy_id": sid,
            "strategy_name": sname,
            "category": closed[0].get("category", ""),
            "symbol": sym_str,
            "total": len(closed),
            "wins": wins,
            "losses": len(closed) - wins,
            "win_rate": wr,
            # USD (original)
            "total_pnl": total_pnl,
            "avg_pnl": round(total_pnl / len(closed), 2),
            "avg_win": round(sum(wa) / len(wa), 2) if wa else 0,
            "avg_loss": round(sum(la) / len(la), 2) if la else 0,
            "profit_factor": pf,
            # PIP (normalized) — NEW
            "total_pnl_pips": total_pnl_pips,
            "avg_pnl_pips": avg_pnl_pips,
            "avg_win_pips": avg_win_pips,
            "avg_loss_pips": avg_loss_pips,
            # SCORE (combined) — NEW
            "score": score,
            # Meta
            "by_symbol": {k: {"total": v["total"], "wins": v["wins"],
                              "pnl": round(v["pnl"], 2), "pnl_pips": round(v["pnl_pips"], 1)}
                          for k, v in symbols.items()},
            "last_5": [t.get("outcome", "loss") for t in closed[-5:]],
            "equity_curve": eq,
            "last_trade": closed[-1].get("opened_at", "") if closed else "",
        })
    
    # ═══ QUALITY FLAGS ═══
    try:
        sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")
        from backend.api.signal_validator import flag_strategy_record as _fsr
        
        for item in ranking:
            sid = item["strategy_id"]
            rec_path = os.path.join(TRACK_DIR, f"rec_{sid}.json")
            try:
                with open(rec_path, "r", encoding="utf-8") as f:
                    rd = json.load(f)
                cl = [t for t in rd.get("trades", []) if t.get("status") == "closed"]
                if len(cl) >= 3:
                    q = _fsr(cl)
                    item["quality"] = q.get("quality", "unknown")
                    item["flags"] = q.get("flags", {})
                else:
                    item["quality"] = "unknown"
            except:
                item["quality"] = "unknown"
    except Exception as e:
        print(f"[REBUILD] Quality flag error: {e}")
    
    # Sort by score (default)
    ranking.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # ═══ SAVE ═══
    cache = {
        "ranking": ranking,
        "total_strategies": len(ranking),
        "total_trades": total_trades,
        "symbols": sorted(all_symbols),
        "rebuilt_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "since": since_date or "all",
    }
    
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    
    elapsed = round(time.time() - t0, 1)
    print(f"[REBUILD] {len(ranking)} strategies, {total_trades} trades, {elapsed}s")
    print(f"[REBUILD] Since: {since_date or 'all'}")
    return cache


if __name__ == "__main__":
    # Support command-line date filter
    since = None
    if len(sys.argv) > 1:
        since = sys.argv[1]
    rebuild(since)
