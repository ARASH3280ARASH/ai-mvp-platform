"""
FINAL MT5 EXECUTOR — 4 Symbols, 43 Profitable Strategies
==========================================================
XAUUSD(20) + BTCUSD(7) + GBPUSD(5) + EURUSD(11)
1-month backtest verified | All costs included
Poll: 1s | 1 trade/strategy | Comment = strategy info
"""
import os, json, time, logging, MetaTrader5 as mt5
from datetime import datetime, timezone

PROJECT = r"C:\Users\Administrator\Desktop\mvp"
ACTIVE_FILE = os.path.join(PROJECT, "track_records", "active_tracks.json")
STATE_FILE = os.path.join(PROJECT, "data", "mt5_executor_state.json")

SYMBOLS = {
    "XAUUSD": {
        "broker": "XAUUSD+", "pip_size": 0.1, "stop_level": 20, "digits": 2,
        "whitelist": os.path.join(PROJECT, "data", "analysis", "xauusd_whitelist.json"),
        "magic": 202602,
    },
    "BTCUSD": {
        "broker": "BTCUSD", "pip_size": 1.0, "stop_level": 20, "digits": 2,
        "whitelist": os.path.join(PROJECT, "data", "analysis", "btcusd_whitelist.json"),
        "magic": 202603,
    },
    "GBPUSD": {
        "broker": "GBPUSD+", "pip_size": 0.0001, "stop_level": 20, "digits": 5,
        "whitelist": os.path.join(PROJECT, "data", "analysis", "gbpusd_whitelist.json"),
        "magic": 202604,
    },
    "EURUSD": {
        "broker": "EURUSD+", "pip_size": 0.0001, "stop_level": 20, "digits": 5,
        "whitelist": os.path.join(PROJECT, "data", "analysis", "eurusd_whitelist.json"),
        "magic": 202605,
    },
}

LOT = 0.01
POLL = 1
MAX_POS = 43  # total strategies

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [EXEC] %(message)s", datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(PROJECT, "data", "mt5_executor.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger("exec")


def load_whitelists():
    out = set()
    for sym, cfg in SYMBOLS.items():
        try:
            with open(cfg["whitelist"], "r", encoding="utf-8") as f:
                s = set(json.load(f).get("strategies", []))
            out.update(s)
            log.info(f"  {sym}: {len(s)} strategies")
        except Exception as e:
            log.warning(f"  {sym}: {e}")
    return out


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"opened": {}, "stats": {"total_opened": 0, "total_closed": 0}}


def save_state(st):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=1)
    except:
        pass


def get_positions():
    pos = []
    for cfg in SYMBOLS.values():
        p = mt5.positions_get(symbol=cfg["broker"])
        if p:
            pos.extend([x for x in p if x.magic == cfg["magic"]])
    return pos


def strat_has_pos(positions, sid):
    tag = sid[:20]
    return any(p.comment and tag in p.comment for p in positions)


def make_comment(sid, direction):
    """MT5 comment: 'ADX_06_XAU|BUY' (max 31 chars)"""
    parts = sid.split("_")
    if len(parts) >= 3:
        short = f"{parts[0]}_{parts[1]}_{parts[2][:3]}"
    else:
        short = sid[:15]
    return f"{short}|{direction}"[:31]


def open_trade(symbol, direction, sl, tp, sid, sname):
    cfg = SYMBOLS.get(symbol)
    if not cfg:
        return None

    broker = cfg["broker"]
    ps = cfg["pip_size"]
    sl_lvl = cfg["stop_level"]
    magic = cfg["magic"]
    dg = cfg["digits"]

    tick = mt5.symbol_info_tick(broker)
    if not tick:
        log.error(f"No tick {broker}")
        return None

    price = tick.ask if direction == "BUY" else tick.bid
    otype = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

    # Stop level
    md = sl_lvl * ps
    if direction == "BUY":
        if sl > price - md: sl = round(price - md, dg)
        if tp < price + md: tp = round(price + md, dg)
    else:
        if sl < price + md: sl = round(price + md, dg)
        if tp > price - md: tp = round(price - md, dg)

    comment = make_comment(sid, direction)

    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": broker,
        "volume": LOT, "type": otype, "price": price,
        "sl": round(sl, dg), "tp": round(tp, dg),
        "deviation": 20, "magic": magic, "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(req)
    if result is None:
        log.error(f"None | {sname}")
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        if result.retcode == mt5.TRADE_RETCODE_INVALID_FILL:
            req["type_filling"] = mt5.ORDER_FILLING_FOK
            result = mt5.order_send(req)
            if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
                log.error(f"Fail {result.retcode if result else '?'} | {sname}")
                return None
        else:
            log.error(f"Fail {result.retcode}: {result.comment} | {sname}")
            return None

    log.info(f"OPENED {direction} {broker} @ {result.price} SL={sl} TP={tp} [{comment}] #{result.order}")

    return {
        "ticket": result.order, "symbol": symbol, "broker": broker,
        "direction": direction, "entry": result.price, "sl": sl, "tp": tp,
        "strategy_id": sid, "strategy_name": sname, "comment": comment,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }


def run():
    log.info("=" * 60)
    log.info("  FINAL EXECUTOR — 4 Symbols, 43 Strategies")
    log.info("  XAUUSD(20) + BTCUSD(7) + GBPUSD(5) + EURUSD(11)")
    log.info("  1-Month Backtest Verified | Profitable Only")
    log.info("=" * 60)

    _path = r"C:\Program Files\Moneta Markets MT5 Terminal\terminal64.exe"
    if not mt5.initialize(path=_path, login=1035360, password="G0Z#IQ1w", server="MonetaMarkets-Demo"):
        mt5.shutdown()
        if not mt5.initialize(path=_path):
            log.error(f"MT5 failed: {mt5.last_error()}")
            return

    info = mt5.account_info()
    log.info(f"Account: {info.login} | ${info.balance:.2f} | {info.server}")

    for sym, cfg in SYMBOLS.items():
        si = mt5.symbol_info(cfg["broker"])
        if si:
            if not si.visible: mt5.symbol_select(cfg["broker"], True)
            log.info(f"  {cfg['broker']}: digits={si.digits} stop={si.trade_stops_level}")
        else:
            log.warning(f"  {cfg['broker']}: NOT FOUND")

    wl = load_whitelists()
    if not wl:
        log.error("No whitelist!")
        return

    state = load_state()
    seen = set(state.get("opened", {}).keys())
    last_save = time.time()
    cycle = 0

    log.info(f"Poll={POLL}s | Max={MAX_POS} | Whitelist={len(wl)}")
    log.info("-" * 60)

    while True:
        try:
            cycle += 1
            try:
                with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
                    trades = json.load(f).get("active", [])
            except:
                time.sleep(POLL); continue

            cands = []
            for t in trades:
                s = t.get("symbol", "")
                if s not in SYMBOLS: continue
                sid = t.get("strategy_id", "")
                if sid not in wl: continue
                tid = t.get("id", "")
                if tid in seen: continue
                cands.append(t)

            if not cands:
                if cycle % 60 == 0:
                    p = get_positions()
                    # Per-symbol count
                    sym_counts = {}
                    for pos in p:
                        for sn, sc in SYMBOLS.items():
                            if pos.magic == sc["magic"]:
                                sym_counts[sn] = sym_counts.get(sn, 0) + 1
                    counts_str = " ".join(f"{k}={v}" for k, v in sym_counts.items())
                    log.info(f"[STATUS] Total={len(p)} {counts_str} | Seen={len(seen)} | Cycle={cycle}")
                time.sleep(POLL); continue

            positions = get_positions()
            if len(positions) >= MAX_POS:
                for c in cands: seen.add(c.get("id", ""))
                time.sleep(POLL); continue

            for t in cands:
                tid = t.get("id", ""); seen.add(tid)
                sym = t.get("symbol", ""); sid = t.get("strategy_id", "")
                sname = t.get("strategy_name", sid)
                d = t.get("direction", "BUY")
                sl = t.get("sl_price", 0)
                tp = t.get("tp_price") or t.get("tp1_price", 0)
                if not sl or not tp: continue
                if strat_has_pos(positions, sid): continue
                if len(positions) >= MAX_POS: break

                r = open_trade(sym, d, sl, tp, sid, sname)
                if r:
                    state["opened"][tid] = r
                    state["stats"]["total_opened"] = state["stats"].get("total_opened", 0) + 1
                    positions = get_positions()

            if time.time() - last_save > 60:
                save_state(state); last_save = time.time()
            time.sleep(POLL)

        except KeyboardInterrupt:
            log.info("Stopping..."); save_state(state); break
        except Exception as e:
            log.error(f"Error: {e}")
            import traceback; traceback.print_exc()
            time.sleep(5)

    save_state(state)
    log.info(f"Done. Positions: {len(get_positions())}")


if __name__ == "__main__":
    run()
