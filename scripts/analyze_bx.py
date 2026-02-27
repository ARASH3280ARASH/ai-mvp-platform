"""Analyze BTCUSD + XAUUSD track records for bit.md report."""
import json, glob, os, sys
from datetime import datetime, timezone
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE = r'C:\Users\Administrator\Desktop\mvp\track_records'
START = datetime(2026, 2, 21, 0, 0, 0, tzinfo=timezone.utc)
NOW = datetime.now(timezone.utc)

COSTS = {
    'BTCUSD': {'spread_pts': 17.0, 'slippage_pts': 5.0, 'comm': 6.0},
    'XAUUSD': {'spread_pts': 0.12, 'slippage_pts': 0.05, 'comm': 6.0},
}

all_trades = {}
file_count = {'BTCUSD': 0, 'XAUUSD': 0}

for symbol in ['BTCUSD', 'XAUUSD']:
    pattern = os.path.join(BASE, f'rec_*_{symbol}_*.json')
    files = glob.glob(pattern)
    file_count[symbol] = len(files)
    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for t in data.get('trades', []):
                tid = t.get('id', '')
                if tid:
                    all_trades[tid] = t
        except Exception:
            pass

# Filter: opened AND closed in window
results = []
for tid, t in all_trades.items():
    if t.get('status') != 'closed':
        continue
    opened = t.get('opened_at', '')
    closed = t.get('closed_at', '')
    if not opened or not closed:
        continue
    try:
        odt = datetime.fromisoformat(opened)
        cdt = datetime.fromisoformat(closed)
    except Exception:
        continue
    if odt < START or odt > NOW or cdt > NOW:
        continue
    results.append(t)

btc_trades = [t for t in results if t.get('symbol') == 'BTCUSD']
xau_trades = [t for t in results if t.get('symbol') == 'XAUUSD']
print(f"Files: BTC={file_count['BTCUSD']}, XAU={file_count['XAUUSD']}", file=sys.stderr)
print(f"Deduped total: {len(all_trades)}", file=sys.stderr)
print(f"In window: {len(results)} (BTC={len(btc_trades)}, XAU={len(xau_trades)})", file=sys.stderr)


def check_no_overlap(trades):
    sorted_t = sorted(trades, key=lambda x: x.get('opened_at', ''))
    for i in range(1, len(sorted_t)):
        prev_closed = sorted_t[i - 1].get('closed_at', '')
        curr_opened = sorted_t[i].get('opened_at', '')
        if curr_opened < prev_closed:
            return False
    return True


def analyze_strategies(trades_list, symbol):
    costs = COSTS[symbol]
    spread = costs['spread_pts']
    slip = costs['slippage_pts']
    comm = costs['comm']
    cost_pips = spread + slip

    strats = defaultdict(list)
    for t in trades_list:
        sid = t.get('strategy_id', 'UNKNOWN')
        strats[sid].append(t)

    output = []
    for sid, trades in strats.items():
        strategy_name = trades[0].get('strategy_name', sid)
        category = trades[0].get('category', '')
        no_overlap = check_no_overlap(trades)

        total_raw_pips = 0
        total_raw_usd = 0
        adj_pnl_pips = 0
        adj_pnl_usd = 0
        wins = 0
        losses = 0
        max_dd = 0
        trade_details = []

        for t in sorted(trades, key=lambda x: x.get('opened_at', '')):
            pips = t.get('pnl_pips', 0) or 0
            usd = t.get('pnl_usd', 0) or 0
            lot = t.get('lot_size', 0.01) or 0.01
            outcome = t.get('outcome', '')

            pip_value = 0.01 * (lot / 0.01)
            cost_usd = (cost_pips * pip_value) + (comm * lot)
            a_pips = pips - cost_pips
            a_usd = usd - cost_usd

            total_raw_pips += pips
            total_raw_usd += usd
            adj_pnl_pips += a_pips
            adj_pnl_usd += a_usd

            if outcome == 'win':
                wins += 1
            elif outcome == 'loss':
                losses += 1

            entry = t.get('entry_price', 0)
            direction = t.get('direction', '')
            highest = t.get('highest_price', 0) or entry
            lowest = t.get('lowest_price', 0) or entry
            if direction == 'BUY':
                dd = entry - lowest
            else:
                dd = highest - entry
            if dd > max_dd:
                max_dd = dd

            trade_details.append({
                'id': t.get('id', ''),
                'dir': direction,
                'open': t.get('opened_at', '')[:19],
                'close': t.get('closed_at', '')[:19],
                'exit': t.get('exit_reason', ''),
                'raw_pips': round(pips, 1),
                'adj_pips': round(a_pips, 1),
                'raw_usd': round(usd, 2),
                'adj_usd': round(a_usd, 2),
                'outcome': outcome,
                'dur': round(t.get('duration_minutes', 0) or 0, 1),
                'lot': lot
            })

        n = len(trades)
        wr = round((wins / n * 100), 1) if n > 0 else 0

        win_pips = [t.get('pnl_pips', 0) for t in trades if t.get('outcome') == 'win']
        loss_pips = [abs(t.get('pnl_pips', 0)) for t in trades if t.get('outcome') == 'loss']
        avg_w = sum(win_pips) / len(win_pips) if win_pips else 0
        avg_l = sum(loss_pips) / len(loss_pips) if loss_pips else 0
        rr = round(avg_w / avg_l, 2) if avg_l > 0 else (99.0 if avg_w > 0 else 0)

        output.append({
            'sid': sid, 'name': strategy_name, 'cat': category,
            'sym': symbol, 'n': n, 'w': wins, 'l': losses,
            'wr': wr, 'raw_pips': round(total_raw_pips, 1),
            'adj_pips': round(adj_pnl_pips, 1),
            'raw_usd': round(total_raw_usd, 2),
            'adj_usd': round(adj_pnl_usd, 2),
            'dd': round(max_dd, 2), 'rr': rr,
            'overlap_ok': no_overlap,
            'trades': trade_details
        })

    output.sort(key=lambda x: x['adj_pips'], reverse=True)
    return output


btc_strats = analyze_strategies(btc_trades, 'BTCUSD')
xau_strats = analyze_strategies(xau_trades, 'XAUUSD')

# Filter: net profitable (adj_pnl_pips > 0) and R:R >= 1.5
btc_profitable = [s for s in btc_strats if s['adj_pips'] > 0 and s['rr'] >= 1.5 and s['overlap_ok']]
xau_profitable = [s for s in xau_strats if s['adj_pips'] > 0 and s['rr'] >= 1.5 and s['overlap_ok']]

result = {
    'btc_total_strats': len(btc_strats),
    'btc_total_trades': len(btc_trades),
    'btc_profitable_count': len(btc_profitable),
    'btc_top30': btc_profitable[:30],
    'xau_total_strats': len(xau_strats),
    'xau_total_trades': len(xau_trades),
    'xau_profitable_count': len(xau_profitable),
    'xau_top30': xau_profitable[:30],
    'btc_all': btc_strats,
    'xau_all': xau_strats,
}

print(json.dumps(result, ensure_ascii=False))
