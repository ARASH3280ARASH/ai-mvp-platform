import json, os, glob
from datetime import datetime, timezone

TRACK_DIR = os.path.join("C:\\", "Users", "Administrator", "Desktop", "mvp", "track_records")
SPREAD_PTS = 17.00
COMMISSION_PER_LOT = 6.0
SLIPPAGE_PTS = 5.0
LOT_SIZE = 0.01
POINT_VALUE = 0.01

START_DATE = datetime(2026, 2, 21, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime(2026, 2, 25, 0, 0, tzinfo=timezone.utc)

files = glob.glob(os.path.join(TRACK_DIR, "rec_*_BTCUSD_H1.json"))

strategy_results = {}

for fpath in files:
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        continue

    trades = data.get("trades", [])
    if not trades:
        continue

    trade_map = {}
    for t in trades:
        tid = t.get("id", "")
        if not tid:
            continue
        trade_map[tid] = t

    unique_trades = list(trade_map.values())

    for t in unique_trades:
        if t.get("status") != "closed":
            continue

        opened_str = t.get("opened_at", "")
        closed_str = t.get("closed_at", "")
        if not opened_str or not closed_str:
            continue

        try:
            opened = datetime.fromisoformat(opened_str)
            closed = datetime.fromisoformat(closed_str)
        except:
            continue

        if opened < START_DATE or opened >= END_DATE:
            continue
        if closed < START_DATE or closed >= END_DATE:
            continue

        strat_id = t.get("strategy_id", "unknown")
        strat_name = t.get("strategy_name", strat_id)
        direction = t.get("direction", "")
        entry = t.get("entry_price", 0)
        sl = t.get("sl_price", 0)
        tp1 = t.get("tp1_price", 0)
        exit_p = t.get("exit_price", 0)
        pnl_pips = t.get("pnl_pips", 0)
        pnl_usd = t.get("pnl_usd", 0)
        outcome = t.get("outcome", "")
        highest = t.get("highest_price", 0)
        lowest = t.get("lowest_price", 0)
        dur = t.get("duration_minutes", 0)
        exit_reason = t.get("exit_reason", "")

        spread_cost_pips = SPREAD_PTS
        slippage_cost_pips = SLIPPAGE_PTS
        commission_usd = COMMISSION_PER_LOT * LOT_SIZE

        adj_pnl_pips = pnl_pips - spread_cost_pips - slippage_cost_pips
        adj_pnl_usd = pnl_usd - (spread_cost_pips + slippage_cost_pips) * LOT_SIZE - commission_usd

        if direction == "BUY" and sl > 0 and tp1 > 0:
            risk = abs(entry - sl)
            reward = abs(tp1 - entry)
        elif direction == "SELL" and sl > 0 and tp1 > 0:
            risk = abs(sl - entry)
            reward = abs(entry - tp1)
        else:
            risk = 0
            reward = 0
        rr = reward / risk if risk > 0 else 0

        if direction == "BUY":
            dd = entry - lowest if lowest > 0 else 0
        else:
            dd = highest - entry if highest > 0 else 0

        if strat_id not in strategy_results:
            strategy_results[strat_id] = {
                "name": strat_name,
                "trades": [],
                "total_pnl_pips": 0,
                "total_pnl_usd": 0,
                "adj_pnl_pips": 0,
                "adj_pnl_usd": 0,
                "wins": 0,
                "losses": 0,
                "max_dd": 0,
                "rr": rr,
                "total_duration": 0,
            }

        sr = strategy_results[strat_id]
        sr["trades"].append({
            "pnl_pips": pnl_pips,
            "pnl_usd": pnl_usd,
            "adj_pnl_pips": adj_pnl_pips,
            "adj_pnl_usd": adj_pnl_usd,
            "outcome": outcome,
            "dd": dd,
            "dur": dur,
            "direction": direction,
            "entry": entry,
            "exit": exit_p,
            "exit_reason": exit_reason,
            "opened": opened_str[:19],
            "closed": closed_str[:19],
            "rr": rr,
        })
        sr["total_pnl_pips"] += pnl_pips
        sr["total_pnl_usd"] += pnl_usd
        sr["adj_pnl_pips"] += adj_pnl_pips
        sr["adj_pnl_usd"] += adj_pnl_usd
        if outcome == "win":
            sr["wins"] += 1
        else:
            sr["losses"] += 1
        if dd > sr["max_dd"]:
            sr["max_dd"] = dd
        sr["total_duration"] += dur
        if rr > sr["rr"]:
            sr["rr"] = rr

profitable = {k: v for k, v in strategy_results.items() if v["adj_pnl_pips"] > 0}
ranked = sorted(profitable.items(), key=lambda x: x[1]["adj_pnl_pips"], reverse=True)

print("# BTCUSD Strategy Performance Report")
print("# Period: 2026-02-21 to 2026-02-24")
print("# Spread: 17.00 pts | Commission: $6/lot RT | Slippage: 5 pts")
print("# Total strategies with trades: {}".format(len(strategy_results)))
print("# Net profitable strategies: {}".format(len(profitable)))
print("# Net losing strategies: {}".format(len(strategy_results) - len(profitable)))
print()

total_trades_all = sum(len(v["trades"]) for v in strategy_results.values())
total_wins_all = sum(v["wins"] for v in strategy_results.values())
total_losses_all = sum(v["losses"] for v in strategy_results.values())
total_pnl_all = sum(v["adj_pnl_usd"] for v in strategy_results.values())
print("# OVERALL: {} trades | {} wins | {} losses | Net: ${:.2f}".format(total_trades_all, total_wins_all, total_losses_all, total_pnl_all))
print()

print("## Profitable Strategies (Ranked by Net Pips)")
print()
print("| Rank | Strategy ID | Strategy Name | Trades | W/L | Net Pips (adj) | Net USD (adj) | Max DD (pts) | Avg R:R | Win Rate |")
print("|------|-------------|---------------|--------|-----|----------------|---------------|--------------|---------|----------|")

for i, (sid, sr) in enumerate(ranked, 1):
    tc = len(sr["trades"])
    wr = (sr["wins"] / tc * 100) if tc > 0 else 0
    clean_id = sid.replace("_BTCUSD_H1", "")
    name = sr["name"]
    adj_pips = sr["adj_pnl_pips"]
    adj_usd = sr["adj_pnl_usd"]
    mdd = sr["max_dd"]
    r = sr["rr"]
    w = sr["wins"]
    lo = sr["losses"]
    print("| {} | {} | {} | {} | {}/{} | {:.1f} | ${:.2f} | {:.1f} | {:.2f} | {:.0f}% |".format(i, clean_id, name, tc, w, lo, adj_pips, adj_usd, mdd, r, wr))

print()
print("## Top 10 Strategy Trade Details")
print()
for i, (sid, sr) in enumerate(ranked[:10], 1):
    clean_id = sid.replace("_BTCUSD_H1", "")
    name = sr["name"]
    print("### {}. {} - {}".format(i, clean_id, name))
    print("| # | Direction | Entry | Exit | Pips | Adj Pips | USD | Reason | Duration | Opened |")
    print("|---|-----------|-------|------|------|----------|-----|--------|----------|--------|")
    for j, t in enumerate(sr["trades"], 1):
        d = t["direction"]
        en = t["entry"]
        ex = t["exit"]
        pp = t["pnl_pips"]
        ap = t["adj_pnl_pips"]
        au = t["adj_pnl_usd"]
        er = t["exit_reason"]
        du = t["dur"]
        op = t["opened"]
        print("| {} | {} | {:.2f} | {:.2f} | {:.1f} | {:.1f} | ${:.2f} | {} | {:.0f}m | {} |".format(j, d, en, ex, pp, ap, au, er, du, op))
    print()

losing = {k: v for k, v in strategy_results.items() if v["adj_pnl_pips"] <= 0}
losing_ranked = sorted(losing.items(), key=lambda x: x[1]["adj_pnl_pips"])
print("## Losing Strategies (Bottom 10)")
print()
print("| Strategy ID | Strategy Name | Trades | W/L | Net Pips (adj) | Net USD (adj) | Max DD |")
print("|-------------|---------------|--------|-----|----------------|---------------|--------|")
for sid, sr in losing_ranked[:10]:
    tc = len(sr["trades"])
    clean_id = sid.replace("_BTCUSD_H1", "")
    name = sr["name"]
    adj_pips = sr["adj_pnl_pips"]
    adj_usd = sr["adj_pnl_usd"]
    mdd = sr["max_dd"]
    w = sr["wins"]
    lo = sr["losses"]
    print("| {} | {} | {} | {}/{} | {:.1f} | ${:.2f} | {:.1f} |".format(clean_id, name, tc, w, lo, adj_pips, adj_usd, mdd))
