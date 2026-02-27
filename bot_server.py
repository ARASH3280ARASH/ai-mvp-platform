"""
Whilber-AI Trading Bot Server — Standalone Live Execution System
Runs on port 8001, independent from the website server (port 8000).
Reads tracker signals, filters by qualified strategy whitelist, executes on MT5.
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sqlite3
import MetaTrader5 as mt5
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(r"C:\Users\Administrator\Desktop\mvp")
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "db" / "whilber.db"
WHITELIST_PATH = DATA_DIR / "bot_whitelist.json"
PENDING_SIGNALS_PATH = DATA_DIR / "pending_signals.json"
ACTIVE_TRACKS_PATH = BASE_DIR / "track_records" / "active_tracks.json"
EXECUTOR_CONFIG_PATH = DATA_DIR / "analysis" / "executor_config.json"
STATE_PATH = DATA_DIR / "bot_state.json"
TRADES_PATH = DATA_DIR / "bot_trades.json"
LOG_PATH = DATA_DIR / "bot_server.log"

# ---------------------------------------------------------------------------
# MT5 Credentials
# ---------------------------------------------------------------------------
MT5_PATH = r"C:\Program Files\Moneta Markets MT5 Terminal\terminal64.exe"
MT5_LOGIN = 1035360
MT5_PASSWORD = "G0Z#IQ1w"
MT5_SERVERS = ["MonetaMarketsTrading-Demo", "MonetaMarkets-Demo"]  # Try in order

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAGIC_NUMBER = 888999
BOT_COMMENT_PREFIX = "BOT"
SIGNAL_POLL_INTERVAL = 10       # seconds
POSITION_CHECK_INTERVAL = 30    # seconds
MAX_OPEN_POSITIONS = 25
MAX_DRAWDOWN_PCT = 5.0
COOLDOWN_HOURS = 4
BE_PROFIT_RATIO = 0.50          # move to BE at 50% of SL distance
MIN_RR = 1.5

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("bot")

# ---------------------------------------------------------------------------
# Global State
# ---------------------------------------------------------------------------
state = {
    "started": None,
    "cycles": 0,
    "orders_sent": 0,
    "orders_failed": 0,
    "last_cycle": None,
    "daily_loss_usd": 0.0,
    "daily_loss_reset": None,
    "cooldowns": {},        # "strategy_id": ISO timestamp
    "active_trades": {},    # ticket_str: {strategy_id, symbol, direction, entry, sl, tp, opened_at, lot}
    "mt5_connected": False,
    "running": False,
    "balance_start": 0.0,
}

whitelist = {}              # strategy_id -> {symbol, lot, ...}
whitelist_ids = set()
executor_config = {}        # from executor_config.json
closed_trades = []          # history of closed trades


# ===================================================================
# MT5 Connection (standalone — no singleton, avoids website conflicts)
# ===================================================================
def mt5_connect() -> bool:
    """Connect to MT5 terminal. Uses path-only init to preserve AutoTrading state."""
    if mt5.terminal_info() is not None:
        info = mt5.terminal_info()
        if info.connected:
            state["mt5_connected"] = True
            return True

    # IMPORTANT: Initialize with path only (not login/password/server).
    # Using credentials causes MT5 to re-initialize and disables AutoTrading.
    # The terminal must already be logged in to the correct account.
    init_ok = mt5.initialize(path=MT5_PATH)
    if init_ok:
        acct = mt5.account_info()
        if acct and acct.login == MT5_LOGIN:
            log.info(f"MT5 connected (path-only) — Account {acct.login}")
        elif acct:
            log.warning(f"MT5 connected but wrong account: {acct.login} (expected {MT5_LOGIN})")
            # Wrong account — need to re-init with credentials (will disable AutoTrading)
            mt5.shutdown()
            init_ok = False

    # Fallback: full credentials (this WILL disable AutoTrading — user must re-enable)
    if not init_ok:
        log.warning("Path-only init failed, trying with credentials (AutoTrading will be disabled)...")
        for server_name in MT5_SERVERS:
            init_ok = mt5.initialize(path=MT5_PATH, login=MT5_LOGIN, password=MT5_PASSWORD, server=server_name)
            if init_ok:
                log.info(f"MT5 connected with server: {server_name}")
                log.warning("NOTE: AutoTrading was likely disabled by re-init. Please enable it in MT5.")
                break
            mt5.shutdown()
            time.sleep(1)

    if not init_ok:
        log.error(f"MT5 init failed: {mt5.last_error()}")
        state["mt5_connected"] = False
        return False

    acct = mt5.account_info()
    if acct is None:
        log.error("MT5 account_info() returned None")
        state["mt5_connected"] = False
        return False

    state["mt5_connected"] = True
    state["balance_start"] = acct.balance
    log.info(f"MT5 connected — Account {acct.login} | Balance ${acct.balance:.2f} | Equity ${acct.equity:.2f}")

    ti = mt5.terminal_info()
    if ti and not ti.trade_allowed:
        log.warning("AutoTrading is DISABLED. Enable it in MT5 toolbar (Algo Trading button).")
    else:
        log.info("AutoTrading is ENABLED — ready to trade")

    return True


def mt5_ensure() -> bool:
    """Ensure MT5 is connected, reconnect if needed."""
    try:
        info = mt5.terminal_info()
        if info and info.connected:
            state["mt5_connected"] = True
            return True
    except Exception:
        pass
    log.warning("MT5 disconnected — reconnecting...")
    mt5.shutdown()
    time.sleep(1)
    return mt5_connect()


BROKER_OVERRIDES = {
    "US30": "DJ30",
}


def get_broker_name(symbol: str) -> str:
    """Resolve internal symbol name to broker name via executor_config, with overrides."""
    if symbol in BROKER_OVERRIDES:
        return BROKER_OVERRIDES[symbol]
    if symbol in executor_config.get("symbols", {}):
        bn = executor_config["symbols"][symbol]["broker_name"]
        # Verify symbol exists on MT5
        if mt5.symbol_info(bn) is not None:
            return bn
        # Try without + suffix
        if bn.endswith("+") and mt5.symbol_info(bn[:-1]) is not None:
            return bn[:-1]
    return symbol


def get_symbol_config(symbol: str) -> dict:
    """Get full symbol config from executor_config."""
    return executor_config.get("symbols", {}).get(symbol, {})


# ===================================================================
# Whitelist & Config Loading
# ===================================================================
def load_whitelist():
    """Load qualified strategy whitelist."""
    global whitelist, whitelist_ids
    try:
        data = json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
        whitelist = {}
        for s in data.get("strategies", []):
            whitelist[s["strategy_id"]] = s
        whitelist_ids = set(whitelist.keys())
        log.info(f"Whitelist loaded: {len(whitelist_ids)} strategies")
    except Exception as e:
        log.error(f"Failed to load whitelist: {e}")


def load_executor_config():
    """Load executor config for symbol details."""
    global executor_config
    try:
        executor_config = json.loads(EXECUTOR_CONFIG_PATH.read_text(encoding="utf-8"))
        log.info(f"Executor config loaded: {len(executor_config.get('symbols', {}))} symbols")
    except Exception as e:
        log.error(f"Failed to load executor config: {e}")


# ===================================================================
# Signal Reading
# ===================================================================
def read_pending_signals() -> list:
    """Read signals from pending_signals.json (non-destructive read)."""
    try:
        if not PENDING_SIGNALS_PATH.exists():
            return []
        text = PENDING_SIGNALS_PATH.read_text(encoding="utf-8").strip()
        if not text:
            return []
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception as e:
        log.warning(f"Error reading pending signals: {e}")
        return []


def read_active_tracks() -> list:
    """Read active tracks from tracker to find new open signals."""
    try:
        if not ACTIVE_TRACKS_PATH.exists():
            return []
        text = ACTIVE_TRACKS_PATH.read_text(encoding="utf-8").strip()
        if not text:
            return []
        data = json.loads(text)
        if isinstance(data, dict):
            # Could be keyed by strategy_id
            tracks = []
            for key, val in data.items():
                if isinstance(val, list):
                    tracks.extend(val)
                elif isinstance(val, dict):
                    tracks.append(val)
            return tracks
        return data if isinstance(data, list) else []
    except Exception as e:
        log.warning(f"Error reading active tracks: {e}")
        return []


def filter_signals(signals: list) -> list:
    """Filter signals to only whitelisted strategies, no duplicates, respect cooldowns."""
    now = datetime.now(timezone.utc)
    valid = []

    # Current open strategy_ids and symbol-direction map
    open_strats = {t["strategy_id"] for t in state["active_trades"].values()}
    open_sym_dirs = {}  # symbol -> set of directions already open
    for t in state["active_trades"].values():
        sym = t.get("symbol", "")
        d = t.get("direction", "")
        open_sym_dirs.setdefault(sym, set()).add(d)

    for sig in signals:
        sid = sig.get("strategy_id", "")

        # Must match whitelist (could be partial match — ADX_03 in ADX_03_BTCUSD_H1)
        matched_wl = None
        if sid in whitelist_ids:
            matched_wl = whitelist[sid]
        else:
            # Try matching by prefix: signal might have "ADX_03" and whitelist has "ADX_03_BTCUSD_H1"
            sym = sig.get("symbol", "")
            for wl_id, wl_data in whitelist.items():
                if wl_id.startswith(sid) and wl_data["symbol"] == sym:
                    matched_wl = wl_data
                    sid = wl_id
                    break

        if matched_wl is None:
            continue

        # Symbol must match
        sig_symbol = sig.get("symbol", "")
        if sig_symbol != matched_wl["symbol"]:
            continue

        # Direction must be present
        direction = sig.get("signal") or sig.get("direction") or sig.get("signal_type")
        if direction not in ("BUY", "SELL"):
            continue

        # No duplicate positions (same strategy)
        if sid in open_strats:
            continue

        # No conflicting direction on same symbol (prevent hedging BUY+SELL)
        opposite = "SELL" if direction == "BUY" else "BUY"
        if sig_symbol in open_sym_dirs and opposite in open_sym_dirs[sig_symbol]:
            continue

        # Cooldown check
        cd_key = sid
        if cd_key in state["cooldowns"]:
            cd_time = datetime.fromisoformat(state["cooldowns"][cd_key])
            if now < cd_time:
                continue

        # Must have SL and TP
        sl = sig.get("sl_price", 0)
        tp = sig.get("tp_price") or sig.get("tp1_price", 0)
        entry = sig.get("entry_price", 0)
        if not all([sl, tp, entry]):
            continue

        # R:R check
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp - entry)
        if sl_dist == 0 or (tp_dist / sl_dist) < MIN_RR:
            continue

        valid.append({
            "strategy_id": sid,
            "symbol": matched_wl["symbol"],
            "direction": direction,
            "entry_price": entry,
            "sl_price": sl,
            "tp_price": tp,
            "lot": matched_wl["lot"],
            "confidence": sig.get("confidence", 0),
        })

    return valid


# ===================================================================
# Trade Execution
# ===================================================================
def open_trade(signal: dict) -> bool:
    """Execute a trade on MT5 based on a filtered signal."""
    symbol = signal["symbol"]
    broker_name = get_broker_name(symbol)
    direction = signal["direction"]
    lot = signal["lot"]
    sl_price = signal["sl_price"]
    tp_price = signal["tp_price"]
    strategy_id = signal["strategy_id"]

    sym_config = get_symbol_config(symbol)
    digits = sym_config.get("digits", 2)
    point = sym_config.get("point", 0.01)
    stop_level = sym_config.get("stop_level", 20)

    # Ensure symbol is available
    sym_info = mt5.symbol_info(broker_name)
    if sym_info is None:
        log.error(f"Symbol {broker_name} not found on MT5")
        return False
    if not sym_info.visible:
        mt5.symbol_select(broker_name, True)

    # Get current price
    tick = mt5.symbol_info_tick(broker_name)
    if tick is None:
        log.error(f"No tick data for {broker_name}")
        return False

    if direction == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid

    # Validate SL/TP distance against stop level
    min_dist = stop_level * point
    if abs(price - sl_price) < min_dist:
        log.warning(f"SL too close for {strategy_id}: {abs(price - sl_price):.5f} < {min_dist:.5f}")
        return False
    if abs(price - tp_price) < min_dist:
        log.warning(f"TP too close for {strategy_id}: {abs(price - tp_price):.5f} < {min_dist:.5f}")
        return False

    # Safety checks
    positions = mt5.positions_get()
    if positions and len(positions) >= MAX_OPEN_POSITIONS:
        log.warning(f"Max positions ({MAX_OPEN_POSITIONS}) reached — skipping {strategy_id}")
        return False

    acct = mt5.account_info()
    if acct:
        dd = (acct.balance - acct.equity) / acct.balance * 100 if acct.balance > 0 else 0
        if dd > MAX_DRAWDOWN_PCT:
            log.warning(f"Drawdown {dd:.1f}% exceeds {MAX_DRAWDOWN_PCT}% — skipping")
            return False

    comment = f"{BOT_COMMENT_PREFIX}|{strategy_id}"[:31]

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": broker_name,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": round(sl_price, digits),
        "tp": round(tp_price, digits),
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    log.info(f"SENDING ORDER: {direction} {lot} {broker_name} @ {price:.{digits}f} | SL={sl_price:.{digits}f} TP={tp_price:.{digits}f} | {strategy_id}")
    result = mt5.order_send(request)

    if result is None:
        log.error(f"order_send returned None — {mt5.last_error()}")
        state["orders_failed"] += 1
        return False

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error(f"Order FAILED: retcode={result.retcode} comment={result.comment} | {strategy_id}")
        state["orders_failed"] += 1
        return False

    ticket = result.order
    log.info(f"ORDER FILLED: ticket={ticket} | {direction} {lot} {broker_name} | {strategy_id}")
    state["orders_sent"] += 1

    # Track the trade
    state["active_trades"][str(ticket)] = {
        "strategy_id": strategy_id,
        "symbol": symbol,
        "broker_name": broker_name,
        "direction": direction,
        "entry_price": price,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "lot": lot,
        "ticket": ticket,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "be_moved": False,
    }

    # Set cooldown
    state["cooldowns"][strategy_id] = (datetime.now(timezone.utc) + timedelta(hours=COOLDOWN_HOURS)).isoformat()

    # Persist immediately (prevent orphan if crash after this)
    save_state()
    db_record_trade_open(state["active_trades"][str(ticket)])
    return True


# ===================================================================
# Position Management
# ===================================================================
def manage_positions():
    """Sync positions with MT5, detect closed trades, manage breakeven."""
    mt5_positions = mt5.positions_get()
    mt5_tickets = set()
    if mt5_positions:
        mt5_tickets = {str(p.ticket) for p in mt5_positions}

    # Recover orphaned positions (in MT5 with our magic, but not in state)
    if mt5_positions:
        for pos in mt5_positions:
            ticket_str = str(pos.ticket)
            if pos.magic == MAGIC_NUMBER and ticket_str not in state["active_trades"]:
                strategy_id = "RECOVERED"
                if pos.comment and "|" in pos.comment:
                    strategy_id = pos.comment.split("|", 1)[1]
                direction = "BUY" if pos.type == 0 else "SELL"
                state["active_trades"][ticket_str] = {
                    "strategy_id": strategy_id,
                    "symbol": pos.symbol.rstrip("+"),
                    "broker_name": pos.symbol,
                    "direction": direction,
                    "entry_price": pos.price_open,
                    "sl_price": pos.sl,
                    "tp_price": pos.tp,
                    "lot": pos.volume,
                    "ticket": pos.ticket,
                    "opened_at": datetime.fromtimestamp(pos.time, tz=timezone.utc).isoformat(),
                    "be_moved": False,
                }
                log.info(f"RECOVERED orphaned position: ticket={pos.ticket} {direction} {pos.volume} {pos.symbol}")
                save_state()

    if not state["active_trades"]:
        return

    # Detect closed trades
    closed_tickets = []
    for ticket_str, trade in list(state["active_trades"].items()):
        if ticket_str not in mt5_tickets:
            closed_tickets.append(ticket_str)

    for ticket_str in closed_tickets:
        trade = state["active_trades"].pop(ticket_str)
        record_closed_trade(trade)

    if closed_tickets:
        save_state()

    # Breakeven management for remaining positions
    if not mt5_positions:
        return

    for pos in mt5_positions:
        ticket_str = str(pos.ticket)
        if ticket_str not in state["active_trades"]:
            continue

        trade = state["active_trades"][ticket_str]
        if trade.get("be_moved"):
            continue

        entry = trade["entry_price"]
        sl = trade["sl_price"]
        sl_dist = abs(entry - sl)
        sym_config = get_symbol_config(trade["symbol"])
        digits = sym_config.get("digits", 2)
        point = sym_config.get("point", 0.01)

        if trade["direction"] == "BUY":
            current_profit_dist = pos.price_current - entry
            be_target = sl_dist * BE_PROFIT_RATIO
            if current_profit_dist >= be_target:
                new_sl = entry + (2 * point)  # tiny offset above entry
                if new_sl > trade["sl_price"]:
                    move_to_breakeven(pos, trade, new_sl, digits)
        else:
            current_profit_dist = entry - pos.price_current
            be_target = sl_dist * BE_PROFIT_RATIO
            if current_profit_dist >= be_target:
                new_sl = entry - (2 * point)  # tiny offset below entry
                if new_sl < trade["sl_price"]:
                    move_to_breakeven(pos, trade, new_sl, digits)


def move_to_breakeven(pos, trade: dict, new_sl: float, digits: int):
    """Modify position SL to breakeven."""
    broker_name = trade["broker_name"]
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": broker_name,
        "position": pos.ticket,
        "sl": round(new_sl, digits),
        "tp": round(trade["tp_price"], digits),
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        trade["be_moved"] = True
        trade["sl_price"] = new_sl
        ticket_str = str(pos.ticket)
        state["active_trades"][ticket_str] = trade
        log.info(f"BE MOVED: {trade['strategy_id']} ticket={pos.ticket} new_sl={new_sl:.{digits}f}")
    else:
        err = result.comment if result else mt5.last_error()
        log.warning(f"BE move failed for {trade['strategy_id']}: {err}")


def record_closed_trade(trade: dict):
    """Record a closed trade to history."""
    symbol = trade["symbol"]
    sym_config = get_symbol_config(symbol)
    pip_size = sym_config.get("pip_size", 1.0)

    # Try to get close info from deal history
    ticket = trade.get("ticket", 0)
    close_price = 0.0
    close_time = datetime.now(timezone.utc).isoformat()

    try:
        now = datetime.now(timezone.utc)
        from_time = now - timedelta(days=7)
        deals = mt5.history_deals_get(from_time, now, group=f"*{trade['broker_name']}*")
        if deals:
            for deal in reversed(deals):
                if deal.position_id == ticket and deal.entry == 1:  # entry=1 means exit deal
                    close_price = deal.price
                    close_time = datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat()
                    break
    except Exception:
        pass

    if close_price == 0:
        close_price = trade.get("entry_price", 0)

    # Calculate PnL
    if trade["direction"] == "BUY":
        pnl_pips = (close_price - trade["entry_price"]) / pip_size
    else:
        pnl_pips = (trade["entry_price"] - close_price) / pip_size

    record = {
        "ticket": ticket,
        "strategy_id": trade["strategy_id"],
        "symbol": symbol,
        "direction": trade["direction"],
        "lot": trade["lot"],
        "entry_price": trade["entry_price"],
        "close_price": close_price,
        "sl_price": trade.get("sl_price", 0),
        "tp_price": trade.get("tp_price", 0),
        "pnl_pips": round(pnl_pips, 1),
        "opened_at": trade.get("opened_at", ""),
        "closed_at": close_time,
        "be_moved": trade.get("be_moved", False),
    }

    closed_trades.append(record)
    save_trades()
    db_record_trade_close(record)

    outcome = "WIN" if pnl_pips > 0 else "LOSS"
    log.info(f"TRADE CLOSED: {outcome} {trade['strategy_id']} | {pnl_pips:+.1f} pips | {trade['direction']} {symbol}")

    # Update daily loss
    if pnl_pips < 0:
        state["daily_loss_usd"] += abs(pnl_pips)


def emergency_close_all(reason: str = "manual") -> int:
    """Close all open positions managed by this bot."""
    closed = 0
    positions = mt5.positions_get()
    if not positions:
        return 0

    for pos in positions:
        if pos.magic != MAGIC_NUMBER:
            continue

        close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            continue
        price = tick.bid if pos.type == 0 else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": MAGIC_NUMBER,
            "comment": f"BOT_CLOSE|{reason}"[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            closed += 1
            log.info(f"EMERGENCY CLOSE: ticket={pos.ticket} {pos.symbol} | reason={reason}")
        else:
            err = result.comment if result else mt5.last_error()
            log.error(f"Failed to close ticket={pos.ticket}: {err}")

    # Clear active trades
    state["active_trades"].clear()
    save_state()
    return closed


# ===================================================================
# State Persistence
# ===================================================================
def save_state():
    """Save bot state to JSON file."""
    try:
        out = {k: v for k, v in state.items() if k != "mt5_connected" and k != "running"}
        STATE_PATH.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        log.warning(f"Failed to save state: {e}")


def load_state():
    """Load bot state from JSON file."""
    try:
        if STATE_PATH.exists():
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            for key in ("cycles", "orders_sent", "orders_failed", "daily_loss_usd",
                        "cooldowns", "active_trades", "balance_start"):
                if key in data:
                    state[key] = data[key]
            log.info(f"State restored: {data.get('cycles', 0)} cycles, {len(state['active_trades'])} active trades")
    except Exception as e:
        log.warning(f"Failed to load state: {e}")


def save_trades():
    """Save closed trade history."""
    try:
        TRADES_PATH.write_text(json.dumps(closed_trades, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        log.warning(f"Failed to save trades: {e}")


def load_trades():
    """Load closed trade history."""
    global closed_trades
    try:
        if TRADES_PATH.exists():
            closed_trades = json.loads(TRADES_PATH.read_text(encoding="utf-8"))
            log.info(f"Trade history loaded: {len(closed_trades)} closed trades")
    except Exception as e:
        log.warning(f"Failed to load trades: {e}")


# ===================================================================
# SQLite Trade Recording (shared with website server)
# ===================================================================
def init_trade_executions_table():
    """Create trade_executions table in shared SQLite database."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL DEFAULT 'bot_server',
                ticket INTEGER,
                strategy_id TEXT,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                close_price REAL,
                sl_price REAL,
                tp_price REAL,
                lot_size REAL,
                pnl_pips REAL,
                pnl_usd REAL,
                magic INTEGER,
                opened_at TEXT,
                closed_at TEXT,
                be_moved INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_te_ticket ON trade_executions(ticket)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_te_status ON trade_executions(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_te_strategy ON trade_executions(strategy_id)")
        conn.commit()
        conn.close()
        log.info("trade_executions table ready in shared SQLite DB")
    except Exception as e:
        log.warning(f"Failed to init trade_executions table: {e}")


def db_record_trade_open(trade: dict):
    """Write an opened trade to SQLite."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            INSERT OR REPLACE INTO trade_executions
            (source, ticket, strategy_id, symbol, direction, entry_price,
             sl_price, tp_price, lot_size, magic, opened_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (
            "bot_server",
            trade.get("ticket", 0),
            trade.get("strategy_id", ""),
            trade.get("symbol", ""),
            trade.get("direction", ""),
            trade.get("entry_price", 0),
            trade.get("sl_price", 0),
            trade.get("tp_price", 0),
            trade.get("lot", 0),
            MAGIC_NUMBER,
            trade.get("opened_at", ""),
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning(f"Failed to record trade open to DB: {e}")


def db_record_trade_close(record: dict):
    """Update a closed trade in SQLite."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            UPDATE trade_executions
            SET close_price=?, pnl_pips=?, closed_at=?, be_moved=?, status='closed'
            WHERE ticket=? AND source='bot_server'
        """, (
            record.get("close_price", 0),
            record.get("pnl_pips", 0),
            record.get("closed_at", ""),
            1 if record.get("be_moved") else 0,
            record.get("ticket", 0),
        ))
        # Also compute PnL USD from deal history if available
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning(f"Failed to record trade close to DB: {e}")


def db_backfill_active_trades():
    """Backfill existing active trades to SQLite (for trades opened before this feature)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        for ticket_str, trade in state.get("active_trades", {}).items():
            existing = conn.execute(
                "SELECT id FROM trade_executions WHERE ticket=? AND source='bot_server'",
                (trade.get("ticket", 0),)
            ).fetchone()
            if not existing:
                conn.execute("""
                    INSERT INTO trade_executions
                    (source, ticket, strategy_id, symbol, direction, entry_price,
                     sl_price, tp_price, lot_size, magic, opened_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """, (
                    "bot_server",
                    trade.get("ticket", 0),
                    trade.get("strategy_id", ""),
                    trade.get("symbol", ""),
                    trade.get("direction", ""),
                    trade.get("entry_price", 0),
                    trade.get("sl_price", 0),
                    trade.get("tp_price", 0),
                    trade.get("lot", 0),
                    MAGIC_NUMBER,
                    trade.get("opened_at", ""),
                ))
        # Also backfill closed trades
        for record in closed_trades:
            existing = conn.execute(
                "SELECT id FROM trade_executions WHERE ticket=? AND source='bot_server'",
                (record.get("ticket", 0),)
            ).fetchone()
            if not existing:
                conn.execute("""
                    INSERT INTO trade_executions
                    (source, ticket, strategy_id, symbol, direction, entry_price,
                     close_price, sl_price, tp_price, lot_size, pnl_pips, magic,
                     opened_at, closed_at, be_moved, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'closed')
                """, (
                    "bot_server",
                    record.get("ticket", 0),
                    record.get("strategy_id", ""),
                    record.get("symbol", ""),
                    record.get("direction", ""),
                    record.get("entry_price", 0),
                    record.get("close_price", 0),
                    record.get("sl_price", 0),
                    record.get("tp_price", 0),
                    record.get("lot", 0),
                    record.get("pnl_pips", 0),
                    MAGIC_NUMBER,
                    record.get("opened_at", ""),
                    record.get("closed_at", ""),
                    1 if record.get("be_moved") else 0,
                ))
        conn.commit()
        conn.close()
        log.info(f"DB backfill complete: {len(state.get('active_trades', {}))} active + {len(closed_trades)} closed")
    except Exception as e:
        log.warning(f"DB backfill failed: {e}")


# ===================================================================
# Orphaned Position Recovery
# ===================================================================
def recover_orphaned_positions():
    """Discover MT5 positions with our magic number that aren't in active_trades."""
    try:
        mt5_positions = mt5.positions_get()
        if not mt5_positions:
            return
        recovered = 0
        for pos in mt5_positions:
            ticket_str = str(pos.ticket)
            if pos.magic == MAGIC_NUMBER and ticket_str not in state["active_trades"]:
                # Extract strategy_id from comment (format: "BOT|strategy_id")
                strategy_id = "RECOVERED"
                if pos.comment and "|" in pos.comment:
                    strategy_id = pos.comment.split("|", 1)[1]

                direction = "BUY" if pos.type == 0 else "SELL"
                state["active_trades"][ticket_str] = {
                    "strategy_id": strategy_id,
                    "symbol": pos.symbol.rstrip("+"),
                    "broker_name": pos.symbol,
                    "direction": direction,
                    "entry_price": pos.price_open,
                    "sl_price": pos.sl,
                    "tp_price": pos.tp,
                    "lot": pos.volume,
                    "ticket": pos.ticket,
                    "opened_at": datetime.fromtimestamp(pos.time, tz=timezone.utc).isoformat(),
                    "be_moved": False,
                }
                recovered += 1
                log.info(f"RECOVERED orphaned position: ticket={pos.ticket} {direction} {pos.volume} {pos.symbol} | {strategy_id}")

        if recovered > 0:
            save_state()
            log.info(f"Recovered {recovered} orphaned positions from MT5")
    except Exception as e:
        log.warning(f"Orphan recovery failed: {e}")


# ===================================================================
# Background Tasks
# ===================================================================
async def signal_scanner_loop():
    """Main loop: scan signals every 10 seconds."""
    log.info("Signal scanner started")
    while state["running"]:
        try:
            if not mt5_ensure():
                await asyncio.sleep(SIGNAL_POLL_INTERVAL)
                continue

            # Daily loss reset
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if state.get("daily_loss_reset") != today:
                state["daily_loss_reset"] = today
                state["daily_loss_usd"] = 0.0

            # Drawdown check
            acct = mt5.account_info()
            if acct and acct.balance > 0:
                dd = (acct.balance - acct.equity) / acct.balance * 100
                if dd > MAX_DRAWDOWN_PCT:
                    log.warning(f"DRAWDOWN {dd:.1f}% > {MAX_DRAWDOWN_PCT}% — emergency close!")
                    emergency_close_all("max_drawdown")
                    await asyncio.sleep(SIGNAL_POLL_INTERVAL)
                    continue

            # Read signals from both sources
            pending = read_pending_signals()
            tracks = read_active_tracks()

            # Extract signals from active tracks (open status + BUY/SELL)
            track_signals = []
            for t in tracks:
                if t.get("status") in ("open", "active") and t.get("direction") in ("BUY", "SELL"):
                    track_signals.append({
                        "strategy_id": t.get("strategy_id", ""),
                        "symbol": t.get("symbol", ""),
                        "signal": t.get("direction"),
                        "entry_price": t.get("entry_price", 0),
                        "sl_price": t.get("sl_price", 0),
                        "tp_price": t.get("tp1_price") or t.get("tp_price", 0),
                        "confidence": t.get("confidence", 50),
                    })

            all_signals = pending + track_signals
            if all_signals:
                valid = filter_signals(all_signals)
                for sig in valid:
                    log.info(f"SIGNAL: {sig['direction']} {sig['symbol']} | {sig['strategy_id']} | conf={sig['confidence']}")
                    open_trade(sig)

            state["cycles"] += 1
            state["last_cycle"] = datetime.now(timezone.utc).isoformat()

            if state["cycles"] % 60 == 0:
                pos_count = len(state["active_trades"])
                balance = acct.balance if acct else 0
                log.info(f"STATUS: cycle={state['cycles']} | positions={pos_count} | balance=${balance:.2f} | orders={state['orders_sent']}")

            save_state()

        except Exception as e:
            log.error(f"Signal scanner error: {e}")

        await asyncio.sleep(SIGNAL_POLL_INTERVAL)


async def position_manager_loop():
    """Position management loop: check every 30 seconds."""
    log.info("Position manager started")
    while state["running"]:
        try:
            if state["mt5_connected"]:
                manage_positions()
        except Exception as e:
            log.error(f"Position manager error: {e}")

        await asyncio.sleep(POSITION_CHECK_INTERVAL)


# ===================================================================
# FastAPI Application
# ===================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    log.info("=" * 60)
    log.info("Whilber-AI Trading Bot Server starting...")
    log.info("=" * 60)

    # Load configs
    load_whitelist()
    load_executor_config()
    load_state()
    load_trades()
    init_trade_executions_table()
    db_backfill_active_trades()

    # Connect MT5
    if not mt5_connect():
        log.error("MT5 connection failed on startup — will retry in background")
    else:
        # Recover any orphaned positions (open in MT5 but missing from state)
        recover_orphaned_positions()

    state["started"] = datetime.now(timezone.utc).isoformat()
    state["running"] = True

    # Start background tasks
    scanner_task = asyncio.create_task(signal_scanner_loop())
    manager_task = asyncio.create_task(position_manager_loop())

    log.info(f"Bot server running on port 8001 | {len(whitelist_ids)} strategies | magic={MAGIC_NUMBER}")

    yield

    # Shutdown
    log.info("Bot server shutting down...")
    state["running"] = False
    scanner_task.cancel()
    manager_task.cancel()
    save_state()
    save_trades()
    mt5.shutdown()
    log.info("Bot server stopped")


app = FastAPI(title="Whilber-AI Trading Bot", version="1.0.0", lifespan=lifespan)


# ===================================================================
# API Endpoints
# ===================================================================
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Status dashboard page."""
    acct = mt5.account_info() if state["mt5_connected"] else None
    balance = acct.balance if acct else 0
    equity = acct.equity if acct else 0
    pos_count = len(state["active_trades"])
    uptime = ""
    if state["started"]:
        started = datetime.fromisoformat(state["started"])
        delta = datetime.now(timezone.utc) - started
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        uptime = f"{hours}h {minutes}m"

    trades_html = ""
    for tid, t in state["active_trades"].items():
        trades_html += f"<tr><td>{tid}</td><td>{t['strategy_id']}</td><td>{t['direction']}</td><td>{t['symbol']}</td><td>{t['lot']}</td><td>{t.get('entry_price', 0):.2f}</td></tr>"

    if not trades_html:
        trades_html = '<tr><td colspan="6" style="text-align:center;color:#888;">No open positions</td></tr>'

    html = f"""<!DOCTYPE html>
<html><head><title>Trading Bot</title>
<meta http-equiv="refresh" content="15">
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; }}
h1 {{ color: #58a6ff; }} h2 {{ color: #8b949e; border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin: 10px 0; display: inline-block; min-width: 180px; margin-right: 12px; }}
.card .value {{ font-size: 24px; font-weight: bold; color: #58a6ff; }}
.card .label {{ color: #8b949e; font-size: 13px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #21262d; }}
th {{ background: #161b22; color: #8b949e; }}
.ok {{ color: #3fb950; }} .err {{ color: #f85149; }}
</style></head><body>
<h1>Whilber-AI Trading Bot</h1>
<div>
<div class="card"><div class="label">MT5 Status</div><div class="value {'ok' if state['mt5_connected'] else 'err'}">{'Connected' if state['mt5_connected'] else 'Disconnected'}</div></div>
<div class="card"><div class="label">Balance</div><div class="value">${balance:,.2f}</div></div>
<div class="card"><div class="label">Equity</div><div class="value">${equity:,.2f}</div></div>
<div class="card"><div class="label">Open Positions</div><div class="value">{pos_count}</div></div>
<div class="card"><div class="label">Orders Sent</div><div class="value">{state['orders_sent']}</div></div>
<div class="card"><div class="label">Cycles</div><div class="value">{state['cycles']}</div></div>
<div class="card"><div class="label">Uptime</div><div class="value">{uptime}</div></div>
<div class="card"><div class="label">Strategies</div><div class="value">{len(whitelist_ids)}</div></div>
</div>
<h2>Open Positions</h2>
<table><tr><th>Ticket</th><th>Strategy</th><th>Direction</th><th>Symbol</th><th>Lot</th><th>Entry</th></tr>
{trades_html}
</table>
<h2>Recent Closed Trades</h2>
<table><tr><th>Strategy</th><th>Symbol</th><th>Direction</th><th>PnL (pips)</th><th>Closed At</th></tr>"""

    for ct in closed_trades[-10:]:
        pnl_class = "ok" if ct.get("pnl_pips", 0) > 0 else "err"
        html += f'<tr><td>{ct["strategy_id"]}</td><td>{ct["symbol"]}</td><td>{ct["direction"]}</td><td class="{pnl_class}">{ct["pnl_pips"]:+.1f}</td><td>{ct.get("closed_at", "")[:19]}</td></tr>'

    if not closed_trades:
        html += '<tr><td colspan="5" style="text-align:center;color:#888;">No closed trades yet</td></tr>'

    html += """</table>
<p style="color:#484f58;margin-top:30px;">Auto-refreshes every 15s | Magic: 888999 | Port: 8001</p>
</body></html>"""
    return HTMLResponse(html)


@app.get("/api/status")
async def api_status():
    """JSON status endpoint."""
    acct = mt5.account_info() if state["mt5_connected"] else None
    return {
        "running": state["running"],
        "mt5_connected": state["mt5_connected"],
        "account": {
            "login": acct.login if acct else None,
            "balance": acct.balance if acct else 0,
            "equity": acct.equity if acct else 0,
            "currency": acct.currency if acct else "",
        } if acct else None,
        "positions": len(state["active_trades"]),
        "strategies": len(whitelist_ids),
        "cycles": state["cycles"],
        "orders_sent": state["orders_sent"],
        "orders_failed": state["orders_failed"],
        "started": state["started"],
        "last_cycle": state["last_cycle"],
        "daily_loss_usd": state["daily_loss_usd"],
        "magic": MAGIC_NUMBER,
    }


@app.get("/api/positions")
async def api_positions():
    """All open positions."""
    return {"count": len(state["active_trades"]), "positions": state["active_trades"]}


@app.get("/api/trades")
async def api_trades():
    """Trade history."""
    total_pips = sum(t.get("pnl_pips", 0) for t in closed_trades)
    wins = sum(1 for t in closed_trades if t.get("pnl_pips", 0) > 0)
    losses = sum(1 for t in closed_trades if t.get("pnl_pips", 0) <= 0)
    return {
        "count": len(closed_trades),
        "total_pips": round(total_pips, 1),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(closed_trades) * 100, 1) if closed_trades else 0,
        "trades": closed_trades,
    }


@app.get("/api/whitelist")
async def api_whitelist():
    """Active whitelist."""
    return {"count": len(whitelist), "strategies": list(whitelist.values())}


@app.post("/api/emergency-close")
async def api_emergency_close():
    """Close all bot positions."""
    closed = emergency_close_all("api_emergency")
    return {"closed": closed, "message": f"Emergency close: {closed} positions closed"}


@app.get("/api/health")
async def api_health():
    """Health check."""
    return {
        "status": "ok",
        "service": "trading-bot",
        "mt5": state["mt5_connected"],
        "uptime_cycles": state["cycles"],
        "positions": len(state["active_trades"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ===================================================================
# Entry Point
# ===================================================================
if __name__ == "__main__":
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", 8001))
        sock.close()
    except OSError:
        print("ERROR: Port 8001 is already in use. Bot server is likely already running.")
        print("       Use 'curl http://localhost:8001/api/health' to check.")
        sys.exit(1)
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
