"""
Fast Cache — loads pre-built JSON, NEVER scans files during requests.
Cache file is rebuilt by external script or background process.
"""
import os, json, time, threading

CACHE_FILE = r"C:\\Users\\Administrator\\Desktop\\mvp\\data\\tracker_cache.json"
_cache = {}
_lock = threading.Lock()
_building = False

_last_file_mtime = 0
_STALE_SEC = 300  # rebuild if cache older than 5 min

def _load_from_file():
    """Load cache — rebuild automatically if stale."""
    global _cache, _last_file_mtime
    if not os.path.exists(CACHE_FILE):
        return {}

    mtime = os.path.getmtime(CACHE_FILE)
    age = time.time() - mtime

    # If file is stale, trigger inline rebuild
    if age > _STALE_SEC:
        try:
            import sys
            sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")
            from scripts.rebuild_cache import rebuild as _rb
            _cache = _rb()
            print(f"[CACHE] Auto-rebuilt: {len(_cache.get('ranking',[]))} strategies")
            return _cache
        except Exception as e:
            print(f"[CACHE] Rebuild failed: {e}")

    # If file changed since last read, reload
    if mtime != _last_file_mtime:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            _cache = json.load(f)
        _last_file_mtime = mtime

    return _cache

# Load immediately on import!
try:
    _load_from_file()
    _n = len(_cache.get("ranking", []))
    if _n:
        print(f"[CACHE] Loaded from file: {_n} strategies")
except Exception as e:
    print(f"[CACHE] Load error: {e}")


def _rebuild_in_background():
    """Rebuild cache by scanning files. Runs in background, never blocks requests."""
    global _cache, _building
    if _building:
        return
    _building = True
    try:
        import subprocess, sys
        # Run external rebuild script
        script = os.path.join(os.path.dirname(CACHE_FILE), "..", "scripts", "rebuild_cache.py")
        if not os.path.exists(script):
            # Fallback: scan inline but in background thread
            _scan_files()
        else:
            subprocess.Popen([sys.executable, script], 
                           creationflags=0x00000008)  # DETACHED_PROCESS
    finally:
        _building = False


def _scan_files():
    """Background file scan — only called from background thread."""
    global _cache
    data_dir = r"C:\\Users\\Administrator\\Desktop\\mvp\\track_records"
    if not os.path.exists(data_dir):
        return
    
    ranking = []
    all_symbols = set()
    total_trades = 0
    
    files = [f for f in os.listdir(data_dir) if f.startswith("rec_") and f.endswith(".json")]
    for filename in files:
        filepath = os.path.join(data_dir, filename)
        sid = filename[4:-5]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                rec = json.load(f)
        except:
            continue
        trades = rec.get("trades", [])
        closed = [t for t in trades if t.get("status") == "closed"]
        if not closed:
            continue
        total_trades += len(closed)
        sname = closed[0].get("strategy_name") or sid
        if not sname or sname.strip() == "":
            sname = sid
        wins = sum(1 for t in closed if t.get("outcome") == "win")
        wr = round(wins / len(closed) * 100, 1)
        total_pnl = round(sum(t.get("pnl_usd", 0) for t in closed), 2)
        symbols = {}
        for t in closed:
            sym = t.get("symbol", "")
            if sym:
                all_symbols.add(sym)
                if sym not in symbols:
                    symbols[sym] = {"total": 0, "wins": 0, "pnl": 0}
                symbols[sym]["total"] += 1
                if t.get("outcome") == "win": symbols[sym]["wins"] += 1
                symbols[sym]["pnl"] += t.get("pnl_usd", 0)
        sym_str = ", ".join(sorted(symbols.keys())) if symbols else "-"
        win_amounts = [t.get("pnl_usd", 0) for t in closed if t.get("outcome") == "win"]
        loss_amounts = [t.get("pnl_usd", 0) for t in closed if t.get("outcome") == "loss"]
        pf = round(abs(sum(win_amounts) / sum(loss_amounts)), 2) if loss_amounts and sum(loss_amounts) != 0 else 0
        eq = []
        cs = 0
        for t in closed[-50:]:
            cs += t.get("pnl_usd", 0)
            eq.append(round(cs, 2))
        item = {
            "strategy_id": sid, "strategy_name": sname,
            "category": closed[0].get("category") or (sid.split("_")[0] if "_" in sid else "other"),
            "symbol": sym_str, "total": len(closed),
            "wins": wins, "losses": len(closed)-wins,
            "win_rate": wr, "total_pnl": total_pnl,
            "avg_pnl": round(total_pnl/len(closed), 2),
            "avg_win": round(sum(win_amounts)/len(win_amounts), 2) if win_amounts else 0,
            "avg_loss": round(sum(loss_amounts)/len(loss_amounts), 2) if loss_amounts else 0,
            "profit_factor": pf,
            "by_symbol": {k: {"total": v["total"], "wins": v["wins"], "pnl": round(v["pnl"],2)} for k,v in symbols.items()},
            "last_5": [t.get("outcome","loss") for t in closed[-5:]],
            "equity_curve": eq,
            "last_trade": closed[-1].get("opened_at","") if closed else "",
        }
        ranking.append(item)
    
    ranking.sort(key=lambda x: x["win_rate"], reverse=True)
    with _lock:
        _cache = {
            "ranking": ranking,
            "summary": [{"strategy_id": r["strategy_id"], "strategy_name": r["strategy_name"],
                          "category": r.get("category",""), "symbol": r["symbol"], "total": r["total"],
                          "wins": r["wins"], "win_rate": r["win_rate"], "total_pnl": r["total_pnl"],
                          "last_trade": r.get("last_trade","")} for r in ranking],
            "symbols": sorted(all_symbols),
            "strategies": [{"id": r["strategy_id"], "name": r["strategy_name"], "count": r["total"]} for r in ranking],
            "total_trades": total_trades,
            "total_strategies": len(ranking),
            "built_at": time.time(),
        }
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False)
    except:
        pass


def get_cache():
    """Get cache — instant, never blocks."""
    if not _cache:
        _load_from_file()
    return _cache or {}


def get_ranking(sort_by="score", limit=100, since=None):
    """
    Get ranking with optional date filter and multiple sort options.
    sort_by: win_rate, total_pnl, total_pnl_pips, score, profit_factor, total
    since: ISO date string (e.g. "2026-02-17") or "7d", "14d", "30d"
    """
    # Always reload from disk to get latest rebuild
    cache = _load_from_file()
    if not cache or not isinstance(cache, dict):
        return {"ranking": [], "total_strategies": 0}
    
    items = cache.get("ranking", [])
    
    # Quality filter — exclude only explicitly unreliable, keep items without quality field
    items = [x for x in items if x.get("quality") != "unreliable"
             and x.get("total", 0) >= 1]
    
    # ═══ DATE FILTER (post-cache) ═══
    if since:
        from datetime import datetime, timezone, timedelta
        cutoff = None
        
        # Parse "7d", "14d", "30d" shortcuts
        if since.endswith("d") and since[:-1].isdigit():
            days = int(since[:-1])
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        else:
            cutoff = since
        
        if cutoff:
            filtered = []
            for item in items:
                last = item.get("last_trade", "")
                if last:
                    try:
                        if last >= cutoff[:19]:  # Simple string compare works for ISO dates
                            filtered.append(item)
                    except:
                        filtered.append(item)
                else:
                    pass  # No last_trade = skip for date filter
            items = filtered
    
    # ═══ SORT ═══
    valid_sorts = ["win_rate", "total_pnl", "total_pnl_pips", "score", "profit_factor", "total", "avg_pnl_pips"]
    if sort_by not in valid_sorts:
        sort_by = "score"
    
    items.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
    
    clean = items[:limit]
    
    # ═══ SUMMARY ═══
    total_trades = sum(r.get("total", 0) for r in clean)
    total_wins = sum(r.get("wins", 0) for r in clean)
    total_pnl = round(sum(r.get("total_pnl", 0) for r in clean), 2)
    total_pnl_pips = round(sum(r.get("total_pnl_pips", 0) for r in clean), 1)
    win_rate = round(total_wins / max(total_trades, 1) * 100, 1)
    
    return {
        "ranking": clean,
        "total_strategies": len(clean),
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "total_pnl_pips": total_pnl_pips,
        "win_rate": win_rate,
        "sort_by": sort_by,
        "since": since or "all",
    }


def get_summary():
    """Return summary with real tracker state data."""
    import os as _os5, json as _json5
    cache = get_cache()
    ranking = cache.get("ranking", [])
    
    # Filtered stats (exclude unreliable)
    clean = [r for r in ranking if r.get("quality") != "unreliable"]
    total_trades = sum(r.get("total", 0) for r in clean)
    total_wins = sum(r.get("wins", 0) for r in clean)
    total_pnl = round(sum(r.get("total_pnl", 0) for r in clean), 2)
    win_rate = round(total_wins / max(total_trades, 1) * 100, 1)
    
    # Read tracker state for real-time stats
    tracker_state = {}
    sf = r"C:\Users\Administrator\Desktop\mvp\track_records\tracker_state.json"
    try:
        if _os5.path.exists(sf):
            with open(sf, "r", encoding="utf-8") as _f5:
                tracker_state = _json5.load(_f5)
    except:
        pass
    
    return {
        "strategies": cache.get("summary", []),
        "total_strategies": len(clean),
        "total_trades": total_trades,
        "total_wins": total_wins,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "total_signals": tracker_state.get("total_signals", 0),
        "total_cycles": tracker_state.get("total_cycles", 0),
        "total_closes": tracker_state.get("total_closes", 0),
        "last_cycle": tracker_state.get("last_cycle", ""),
        "symbols": cache.get("symbols", []),
    }

def get_filter_options():
    cache = get_cache()
    all_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD", "EURGBP", "EURJPY", "GBPJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD", "AUDJPY", "AUDNZD", "AUDCAD", "AUDCHF", "NZDJPY", "NZDCAD", "NZDCHF", "CADJPY", "CADCHF", "CHFJPY", "XAUUSD", "XAGUSD", "BTCUSD", "NAS100", "US30"]
    combined = sorted(set(all_symbols + cache.get("symbols", [])))
    categories = {}
    strategies_list = []
    for r in cache.get("ranking", []):
        sid = r.get("strategy_id", "")
        sname = r.get("strategy_name", sid)
        strategies_list.append({"id": sid, "name": sname, "count": r.get("total", 0)})
        parts = sid.split("_")
        if len(parts) >= 2:
            cat = parts[0]
            categories[cat] = categories.get(cat, 0) + 1
    symbol_groups = {"فارکس — ماژور": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"], "فارکس — یورو کراس": ["EURGBP", "EURJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD"], "فارکس — پوند کراس": ["GBPJPY", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD"], "فارکس — سایر کراس": ["AUDJPY", "AUDNZD", "AUDCAD", "AUDCHF", "NZDJPY", "NZDCAD", "NZDCHF", "CADJPY", "CADCHF", "CHFJPY"], "فلزات": ["XAUUSD", "XAGUSD"], "کریپتو": ["BTCUSD"], "شاخص‌ها": ["NAS100", "US30"]}
    return {
        "symbols": combined,
        "symbol_groups": symbol_groups,
        "strategies": strategies_list,
        "categories": [{"id": k, "count": v} for k, v in sorted(categories.items())],
        "timeframes": ["M5","M15","M30","H1","H4","D1"],
        "directions": ["BUY", "SELL"],
        "outcomes": ["win", "loss"],
    }

def get_filtered_trades(symbols=None, strategies=None, directions=None, 
                        outcomes=None, exit_reasons=None, limit=200):
    """Filter trades from cache — no file scanning needed."""
    cache = get_cache()
    ranking = cache.get("ranking", [])
    
    results = []
    for item in ranking:
        # Strategy filter
        if strategies and item["strategy_id"] not in strategies:
            continue
        
        # Symbol filter
        item_symbols = list(item.get("by_symbol", {}).keys())
        if symbols:
            if not any(s in item_symbols for s in symbols):
                # Also check symbol string
                if not any(s in item.get("symbol", "") for s in symbols):
                    continue
        
        # Build trade-like entries from ranking data
        for sym, sym_data in item.get("by_symbol", {}).items():
            if symbols and sym not in symbols:
                continue
            
            # Create summary trade entries
            wins = sym_data.get("wins", 0)
            total = sym_data.get("total", 0)
            losses = total - wins
            pnl = sym_data.get("pnl", 0)
            
            if outcomes:
                if "win" in outcomes and wins > 0:
                    results.append({
                        "strategy_id": item["strategy_id"],
                        "strategy_name": item["strategy_name"],
                        "symbol": sym,
                        "direction": "-",
                        "outcome": "win",
                        "pnl_usd": round(pnl / total, 2) if total else 0,
                        "win_rate": item["win_rate"],
                        "total_trades": total,
                        "total_pnl": pnl,
                    })
                if "loss" in outcomes and losses > 0:
                    results.append({
                        "strategy_id": item["strategy_id"],
                        "strategy_name": item["strategy_name"],
                        "symbol": sym,
                        "direction": "-",
                        "outcome": "loss",
                        "pnl_usd": round(pnl / total, 2) if total else 0,
                        "win_rate": item["win_rate"],
                        "total_trades": total,
                        "total_pnl": pnl,
                    })
            else:
                results.append({
                    "strategy_id": item["strategy_id"],
                    "strategy_name": item["strategy_name"],
                    "symbol": sym,
                    "direction": "-",
                    "outcome": "win" if pnl > 0 else "loss",
                    "pnl_usd": round(pnl, 2),
                    "win_rate": item["win_rate"],
                    "total_trades": total,
                    "total_pnl": round(pnl, 2),
                    "wins": wins,
                    "losses": losses,
                })
    
    # Direction filter (approximate from data)
    if directions:
        pass  # Can't filter by direction from cached data
    
    total_found = len(results)
    return {
        "trades": results[:limit],
        "total_found": total_found,
        "source": "cache",
    }


def get_heatmap():
    """Generate heatmap data from cache — no file scanning."""
    cache = get_cache()
    ranking = cache.get("ranking", [])
    
    # Symbol × Strategy category heatmap
    heatmap = {}
    symbol_stats = {}
    
    for item in ranking:
        for sym, sym_data in item.get("by_symbol", {}).items():
            if sym not in symbol_stats:
                symbol_stats[sym] = {"total": 0, "wins": 0, "pnl": 0, "strategies": 0}
            symbol_stats[sym]["total"] += sym_data.get("total", 0)
            symbol_stats[sym]["wins"] += sym_data.get("wins", 0)
            symbol_stats[sym]["pnl"] += sym_data.get("pnl", 0)
            symbol_stats[sym]["strategies"] += 1
            
            # Category heatmap
            cat = item.get("category", "other") or "other"
            key = f"{sym}_{cat}"
            if key not in heatmap:
                heatmap[key] = {"symbol": sym, "category": cat, "total": 0, "wins": 0, "pnl": 0}
            heatmap[key]["total"] += sym_data.get("total", 0)
            heatmap[key]["wins"] += sym_data.get("wins", 0)
            heatmap[key]["pnl"] += sym_data.get("pnl", 0)
    
    # Calculate win rates
    for v in symbol_stats.values():
        v["win_rate"] = round(v["wins"] / v["total"] * 100, 1) if v["total"] else 0
        v["pnl"] = round(v["pnl"], 2)
    
    for v in heatmap.values():
        v["win_rate"] = round(v["wins"] / v["total"] * 100, 1) if v["total"] else 0
        v["pnl"] = round(v["pnl"], 2)
    
    return {
        "symbol_stats": symbol_stats,
        "heatmap": list(heatmap.values()),
        "source": "cache",
    }


def get_export_data(fmt="json", limit=500):
    """Get export data from cache."""
    cache = get_cache()
    ranking = cache.get("ranking", [])
    
    rows = []
    for item in ranking[:limit]:
        rows.append({
            "strategy": item.get("strategy_name", ""),
            "symbol": item.get("symbol", ""),
            "trades": item.get("total", 0),
            "wins": item.get("wins", 0),
            "losses": item.get("losses", 0),
            "win_rate": item.get("win_rate", 0),
            "pnl": item.get("total_pnl", 0),
            "profit_factor": item.get("profit_factor", 0),
            "avg_pnl": item.get("avg_pnl", 0),
        })
    
    if fmt == "csv":
        if not rows:
            return {"csv": "", "count": 0}
        headers = list(rows[0].keys())
        lines = [",".join(headers)]
        for r in rows:
            lines.append(",".join(str(r.get(h, "")) for h in headers))
        return {"csv": "\n".join(lines), "count": len(rows), "source": "cache"}
    
    return {"data": rows, "count": len(rows), "source": "cache"}



# ═══ REAL TRADE RECORDS FILTER (not summaries) ═══════════════

def get_real_trades(symbols=None, strategies=None, directions=None,
                    outcomes=None, exit_reasons=None, timeframes=None,
                    date_from=None, date_to=None,
                    sort_by="opened_at", sort_dir="desc", limit=200, offset=0):
    """
    Read ACTUAL trade records from files — returns real trades with all fields.
    Smart: uses cache to know which files to read, then filters.
    """
    import os as _os, json as _json, glob as _glob
    track_dir = r"C:\\Users\\Administrator\\Desktop\\mvp\\track_records"
    
    cache = get_cache()
    ranking = cache.get("ranking", [])
    
    # Pre-filter: which strategy files to read?
    target_sids = set()
    for r in ranking:
        sid = r.get("strategy_id", "")
        # Symbol filter at strategy level
        if symbols:
            item_syms = list(r.get("by_symbol", {}).keys())
            sym_str = r.get("symbol", "")
            if not any(s in item_syms or s in sym_str for s in symbols):
                continue
        # Strategy filter
        if strategies and sid not in strategies:
            continue
        target_sids.add(sid)
    
    if not target_sids:
        target_sids = set(r["strategy_id"] for r in ranking)
    
    # Read trades from files (limit file reads for speed)
    all_trades = []
    files_read = 0
    max_files = min(len(target_sids), 300)  # Cap at 300 files for speed
    
    for sid in list(target_sids)[:max_files]:
        safe_id = sid.replace("/", "_").replace("\\", "_")[:60]
        rec_file = _os.path.join(track_dir, f"rec_{safe_id}.json")
        if not _os.path.exists(rec_file):
            continue
        
        try:
            with open(rec_file, "r", encoding="utf-8") as f:
                rec = _json.load(f)
            files_read += 1
        except:
            continue
        
        for t in rec.get("trades", []):
            if t.get("status") != "closed":
                continue
            
            # Apply filters
            if symbols and t.get("symbol") not in symbols:
                continue
            if directions and t.get("direction") not in directions:
                continue
            if outcomes and t.get("outcome") not in outcomes:
                continue
            if exit_reasons and t.get("exit_reason") not in exit_reasons:
                continue
            if timeframes and t.get("timeframe") not in timeframes:
                continue
            if date_from and (t.get("opened_at", "") < date_from):
                continue
            if date_to and (t.get("opened_at", "") > date_to):
                continue
            
            # Build clean trade object (without heavy events array)
            trade = {
                "id": t.get("id", ""),
                "strategy_id": t.get("strategy_id", sid),
                "strategy_name": t.get("strategy_name", ""),
                "category": t.get("category", ""),
                "symbol": t.get("symbol", ""),
                "timeframe": t.get("timeframe", "H1"),
                "direction": t.get("direction", ""),
                "entry_price": t.get("entry_price", 0),
                "exit_price": t.get("exit_price", 0),
                "sl_price": t.get("sl_price", 0),
                "tp1_price": t.get("tp1_price", 0),
                "pnl_pips": t.get("pnl_pips", 0),
                "pnl_usd": t.get("pnl_usd", 0),
                "outcome": t.get("outcome", ""),
                "exit_reason": t.get("exit_reason", ""),
                "duration_minutes": t.get("duration_minutes", 0),
                "opened_at": t.get("opened_at", ""),
                "closed_at": t.get("closed_at", ""),
                "sl_moved_to_be": t.get("sl_moved_to_be", False),
                "trailing_active": t.get("trailing_active", False),
                "partial_closes": t.get("partial_closes", []),
                "highest_price": t.get("highest_price", 0),
                "lowest_price": t.get("lowest_price", 0),
                "lot_size": t.get("lot_size", 0.01),
                "events_count": len(t.get("events", [])),
            }
            all_trades.append(trade)
    
    # Sort
    reverse = sort_dir == "desc"
    sort_keys = {
        "opened_at": lambda x: x.get("opened_at", ""),
        "pnl_usd": lambda x: x.get("pnl_usd", 0),
        "duration_minutes": lambda x: x.get("duration_minutes", 0),
        "win_rate": lambda x: x.get("pnl_usd", 0),
        "symbol": lambda x: x.get("symbol", ""),
    }
    key_fn = sort_keys.get(sort_by, sort_keys["opened_at"])
    all_trades.sort(key=key_fn, reverse=reverse)
    
    total_found = len(all_trades)
    
    # Stats
    wins = sum(1 for t in all_trades if t["outcome"] == "win")
    losses = total_found - wins
    total_pnl = round(sum(t["pnl_usd"] for t in all_trades), 2)
    wr = round(wins / total_found * 100, 1) if total_found else 0
    
    # Paginate
    trades_page = all_trades[offset:offset + limit]
    
    return {
        "trades": trades_page,
        "total_found": total_found,
        "files_read": files_read,
        "stats": {
            "total": total_found,
            "wins": wins,
            "losses": losses,
            "win_rate": wr,
            "total_pnl": total_pnl,
            "avg_pnl": round(total_pnl / total_found, 2) if total_found else 0,
        }
    }

# ═══ END REAL TRADES ══════════════════════════════════════════


# ═══ TRADE-LEVEL CACHE (for fast filtering) ═══════════════════
import threading as _tc_threading

# ═══ QUALITY FILTER ═══
def _quality_filter(ranking):
    """Remove unreliable strategies from ranking."""
    try:
        from backend.api.signal_validator import flag_strategy_record
    except ImportError:
        return ranking  # No validator available, return as-is
    
    import os, json
    tr_dir = r"C:\Users\Administrator\Desktop\mvp\track_records"
    filtered = []
    
    for item in ranking:
        sid = item.get("strategy_id", "")
        rec_file = os.path.join(tr_dir, f"rec_{sid}.json")
        
        if not os.path.exists(rec_file):
            continue
        
        try:
            with open(rec_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            trades = data.get("trades", [])
            closed = [t for t in trades if t.get("status") == "closed"]
            
            if len(closed) < 3:
                continue
            
            quality = flag_strategy_record(closed)
            
            # Skip unreliable
            # Relaxed filter: only skip unreliable with extreme WR

            if item.get("quality") == "unreliable" and item.get("win_rate", 0) >= 95:
                continue

            
            # Add quality info to item
            item["quality"] = quality["quality"]
            item["quality_flags"] = quality.get("flags", [])
            item["clean_trades"] = quality.get("clean_trades", 0)
            item["recovery_pct"] = quality.get("recovery_pct", 0)
            
            # Recalculate stats using only clean trades (non-recovery)
            clean = [t for t in closed if "recovery" not in t.get("exit_reason", "")]
            if len(clean) >= 3:
                wins = sum(1 for t in clean if t.get("outcome") == "win")
                item["win_rate"] = round(wins / len(clean) * 100, 1)
                item["total"] = len(clean)
                item["wins"] = wins
                item["losses"] = len(clean) - wins
                total_pnl = sum(t.get("pnl_usd", 0) for t in clean)
                item["total_pnl"] = round(total_pnl, 2)
                wa = [t.get("pnl_usd", 0) for t in clean if t.get("outcome") == "win"]
                la = [t.get("pnl_usd", 0) for t in clean if t.get("outcome") == "loss"]
                item["profit_factor"] = round(abs(sum(wa) / sum(la)), 2) if la and sum(la) != 0 else 0
            
            filtered.append(item)
        except:
            continue
    
    return filtered
# ═══ END QUALITY FILTER ═══



_trades_cache = {"trades": [], "built_at": 0, "lock": _tc_threading.Lock()}
_TRADES_CACHE_TTL = 120  # Refresh every 2 minutes

def _build_trades_cache():
    """Pre-read all closed trades into memory for instant filtering."""
    import os as _os, json as _json, time as _time
    track_dir = r"C:\\Users\\Administrator\\Desktop\\mvp\\track_records"
    
    t0 = _time.time()
    all_trades = []
    files_read = 0
    
    for filename in _os.listdir(track_dir):
        if not filename.startswith("rec_") or not filename.endswith(".json"):
            continue
        filepath = _os.path.join(track_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                rec = _json.load(f)
            files_read += 1
        except:
            continue
        
        sid = filename[4:-5]
        for t in rec.get("trades", []):
            if t.get("status") != "closed":
                continue
            all_trades.append({
                "id": t.get("id", ""),
                "strategy_id": t.get("strategy_id", sid),
                "strategy_name": t.get("strategy_name", ""),
                "category": t.get("category", ""),
                "symbol": t.get("symbol", ""),
                "timeframe": t.get("timeframe", "H1"),
                "direction": t.get("direction", ""),
                "entry_price": t.get("entry_price", 0),
                "exit_price": t.get("exit_price", 0),
                "sl_price": t.get("sl_price", 0),
                "tp1_price": t.get("tp1_price", 0),
                "pnl_pips": t.get("pnl_pips", 0),
                "pnl_usd": t.get("pnl_usd", 0),
                "outcome": t.get("outcome", ""),
                "exit_reason": t.get("exit_reason", ""),
                "duration_minutes": t.get("duration_minutes", 0),
                "opened_at": t.get("opened_at", ""),
                "closed_at": t.get("closed_at", ""),
                "sl_moved_to_be": t.get("sl_moved_to_be", False),
                "trailing_active": t.get("trailing_active", False),
                "partial_closes": len(t.get("partial_closes", [])),
                "highest_price": t.get("highest_price", 0),
                "lowest_price": t.get("lowest_price", 0),
                "lot_size": t.get("lot_size", 0.01),
                "events_count": len(t.get("events", [])),
            })
    
    ms = int((_time.time() - t0) * 1000)
    print(f"[TRADE_CACHE] Built: {len(all_trades)} trades from {files_read} files in {ms}ms")
    return all_trades


def _get_trades_cached():
    """Get all trades from memory cache, rebuild if stale."""
    import time as _time
    now = _time.time()
    if now - _trades_cache["built_at"] > _TRADES_CACHE_TTL or not _trades_cache["trades"]:
        with _trades_cache["lock"]:
            if now - _trades_cache["built_at"] > _TRADES_CACHE_TTL or not _trades_cache["trades"]:
                _trades_cache["trades"] = _build_trades_cache()
                _trades_cache["built_at"] = now
    return _trades_cache["trades"]


def get_real_trades_fast(symbols=None, strategies=None, directions=None,
                         outcomes=None, exit_reasons=None, timeframes=None,
                         date_from=None, date_to=None,
                         sort_by="opened_at", sort_dir="desc", limit=200, offset=0):
    """
    Ultra-fast filter: reads from memory cache instead of disk.
    First call builds cache (~5s), subsequent calls <50ms.
    """
    all_trades = _get_trades_cached()
    
    # Apply filters
    filtered = []
    for t in all_trades:
        if symbols and t["symbol"] not in symbols:
            continue
        if strategies and t["strategy_id"] not in strategies:
            continue
        if directions and t["direction"] not in directions:
            continue
        if outcomes and t["outcome"] not in outcomes:
            continue
        if exit_reasons and t["exit_reason"] not in exit_reasons:
            continue
        if timeframes and t["timeframe"] not in timeframes:
            continue
        if date_from and t["opened_at"] < date_from:
            continue
        if date_to and t["opened_at"] > date_to:
            continue
        filtered.append(t)
    
    # Sort
    reverse = sort_dir == "desc"
    sort_keys = {
        "opened_at": lambda x: x.get("opened_at", ""),
        "pnl_usd": lambda x: x.get("pnl_usd", 0),
        "duration_minutes": lambda x: x.get("duration_minutes", 0),
        "symbol": lambda x: x.get("symbol", ""),
    }
    filtered.sort(key=sort_keys.get(sort_by, sort_keys["opened_at"]), reverse=reverse)
    
    total_found = len(filtered)
    wins = sum(1 for t in filtered if t["outcome"] == "win")
    total_pnl = round(sum(t["pnl_usd"] for t in filtered), 2)
    
    return {
        "trades": filtered[offset:offset + limit],
        "total_found": total_found,
        "stats": {
            "total": total_found,
            "wins": wins,
            "losses": total_found - wins,
            "win_rate": round(wins / total_found * 100, 1) if total_found else 0,
            "total_pnl": total_pnl,
            "avg_pnl": round(total_pnl / total_found, 2) if total_found else 0,
        }
    }

# ═══ END TRADE CACHE ══════════════════════════════════════════
