"""
Daily Snapshot — Saves a summary of all strategy performance each day.
Run once per day (or after server restart) to maintain long-term history.
Stored as: daily_snapshots/YYYY-MM-DD.json
"""
import os, json, glob, time
from datetime import datetime, timezone

TRACK_DIR = r"C:\\Users\\Administrator\\Desktop\\mvp\\track_records"
SNAPSHOT_DIR = r"C:\\Users\\Administrator\\Desktop\\mvp\\data\\daily_snapshots"
CACHE_FILE = r"C:\\Users\\Administrator\\Desktop\\mvp\\data\\tracker_cache.json"

def take_snapshot():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snap_file = os.path.join(SNAPSHOT_DIR, f"{today}.json")
    
    # Don't overwrite if already exists today
    if os.path.exists(snap_file):
        return {"status": "already_exists", "date": today}
    
    # Read from cache (fast)
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
    else:
        return {"status": "no_cache", "date": today}
    
    # Build snapshot: per-strategy summary
    ranking = cache.get("ranking", [])
    snapshot = {
        "date": today,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_strategies": len(ranking),
        "total_trades": cache.get("total_trades", 0),
        "symbols": cache.get("symbols", []),
        "strategies": []
    }
    
    for r in ranking:
        snapshot["strategies"].append({
            "id": r.get("strategy_id", ""),
            "name": r.get("strategy_name", ""),
            "category": r.get("category", ""),
            "symbol": r.get("symbol", ""),
            "total": r.get("total", 0),
            "wins": r.get("wins", 0),
            "win_rate": r.get("win_rate", 0),
            "total_pnl": r.get("total_pnl", 0),
            "profit_factor": r.get("profit_factor", 0),
            "avg_pnl": r.get("avg_pnl", 0),
            "last_trade": r.get("last_trade", ""),
        })
    
    # Count active trades
    active_file = os.path.join(TRACK_DIR, "active_tracks.json")
    if os.path.exists(active_file):
        try:
            with open(active_file, "r", encoding="utf-8") as f:
                ad = json.load(f)
            snapshot["active_trades"] = len(ad.get("active", []))
        except:
            snapshot["active_trades"] = 0
    
    with open(snap_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=1)
    
    # Cleanup old snapshots (keep 365 days)
    snaps = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    while len(snaps) > 365:
        os.remove(snaps.pop(0))
    
    return {"status": "created", "date": today, "strategies": len(ranking)}


def get_history(days=30):
    """Get historical snapshots for trend analysis."""
    snaps = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    snaps = snaps[-days:]
    history = []
    for sf in snaps:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                history.append(json.load(f))
        except:
            continue
    return history


def get_strategy_history(strategy_id, days=30):
    """Get performance history for a specific strategy over time."""
    history = get_history(days)
    result = []
    for snap in history:
        for s in snap.get("strategies", []):
            if s.get("id") == strategy_id:
                result.append({
                    "date": snap["date"],
                    "total": s.get("total", 0),
                    "wins": s.get("wins", 0),
                    "win_rate": s.get("win_rate", 0),
                    "total_pnl": s.get("total_pnl", 0),
                    "profit_factor": s.get("profit_factor", 0),
                })
                break
    return result


if __name__ == "__main__":
    result = take_snapshot()
    print(f"Snapshot: {result}")
