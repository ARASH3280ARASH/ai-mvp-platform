"""
Whilber-AI — Whitelist Manager
================================
Generates whitelist from ranking data.
Only top-performing strategies go to live trading.

Criteria:
- Win Rate >= 55%
- Total trades >= 20
- Profit Factor >= 1.5
- Max drawdown < 15%
- Net PnL > 0
"""

import json
import os
from datetime import datetime, timezone

PROJECT = r"C:\Users\Administrator\Desktop\mvp"
RANKING_CACHE = os.path.join(PROJECT, "track_records", "ranking_cache.json")
WHITELIST_PATH = os.path.join(PROJECT, "data", "analysis", "whitelist.json")


def generate_whitelist(min_wr=55, min_trades=20, min_pf=1.5, max_dd=15, top_n=43):
    """
    Generate whitelist from ranking data.
    Returns list of approved strategy IDs.
    """
    # Load ranking
    if not os.path.exists(RANKING_CACHE):
        print("[WL] No ranking_cache.json found")
        return []

    with open(RANKING_CACHE, "r", encoding="utf-8") as f:
        ranking = json.load(f)

    strategies = ranking.get("strategies", [])
    if not strategies:
        print("[WL] No strategies in ranking")
        return []

    # Filter
    approved = []
    for s in strategies:
        wr = s.get("win_rate", 0)
        total = s.get("total_trades", 0)
        pf = s.get("profit_factor", 0)
        dd = s.get("max_drawdown_pct", 100)
        pnl = s.get("total_pnl_pips", s.get("net_pnl", 0))

        if wr >= min_wr and total >= min_trades and pf >= min_pf and dd < max_dd and pnl > 0:
            approved.append({
                "strategy_id": s.get("strategy_id", ""),
                "strategy_name": s.get("strategy_name", ""),
                "category": s.get("category", ""),
                "win_rate": wr,
                "total_trades": total,
                "profit_factor": pf,
                "net_pnl": pnl,
                "score": round(wr * pnl / 100, 2) if pnl > 0 else 0,
            })

    # Sort by score, take top N
    approved.sort(key=lambda x: x["score"], reverse=True)
    approved = approved[:top_n]

    # Save
    whitelist = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "criteria": {
            "min_win_rate": min_wr,
            "min_trades": min_trades,
            "min_profit_factor": min_pf,
            "max_drawdown": max_dd,
        },
        "total_ranked": len(strategies),
        "total_approved": len(approved),
        "strategies": approved,
    }

    os.makedirs(os.path.dirname(WHITELIST_PATH), exist_ok=True)
    with open(WHITELIST_PATH, "w", encoding="utf-8") as f:
        json.dump(whitelist, f, ensure_ascii=False, indent=2)

    print(f"[WL] Whitelist: {len(approved)}/{len(strategies)} strategies approved")
    return approved


if __name__ == "__main__":
    result = generate_whitelist()
    for s in result:
        print(f"  {s['strategy_id']:30s} WR={s['win_rate']:.0f}% PF={s['profit_factor']:.1f} PnL={s['net_pnl']}")
