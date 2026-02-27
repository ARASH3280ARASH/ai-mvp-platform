"""
═══════════════════════════════════════════════════════════════
  TRADE GUARDIAN — Independent Trade Manager
═══════════════════════════════════════════════════════════════
  Runs separately from web server.
  Manages all open MT5 positions with magic number tracking.
  Server can restart freely — trades are NEVER interrupted.
  
  Usage:
    python trade_guardian.py          (foreground)
    start /b python trade_guardian.py (background)
    
  Architecture:
    [Trade Guardian]  ←→  MT5  (manages positions, SL/TP)
    [Web Server]      ←→  API  (serves frontend, can restart)
    Both read/write → state files in data/
═══════════════════════════════════════════════════════════════
"""
import os, sys, json, time, signal, logging
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ──────────────────────────────────────────────────
PROJECT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT)

MAGIC_NUMBER = 777888       # Whilber-AI magic number
CYCLE_SECONDS = 60          # Check every 60 seconds
STATE_FILE = os.path.join(PROJECT, "data", "guardian_state.json")
LOG_FILE = os.path.join(PROJECT, "data", "guardian.log")
PID_FILE = os.path.join(PROJECT, "data", "guardian.pid")
TRACK_DIR = os.path.join(PROJECT, "track_records")

# ── Logging ─────────────────────────────────────────────────
os.makedirs(os.path.join(PROJECT, "data"), exist_ok=True)
os.makedirs(TRACK_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger("guardian")

# ── MT5 Setup ───────────────────────────────────────────────
import MetaTrader5 as mt5
MT5_PATH = r"C:\Program Files\Moneta Markets MT5 Terminal\terminal64.exe"
MT5_LOGIN = 1035360
MT5_PASSWORD = "G0Z#IQ1w"
MT5_SERVER = "MonetaMarkets-Demo"

SUFFIX_MAP = {}
ALL_SYMBOLS = [
    "EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","NZDUSD","USDCAD",
    "EURGBP","EURJPY","GBPJPY","EURAUD","EURCAD","EURCHF","EURNZD",
    "GBPAUD","GBPCAD","GBPCHF","GBPNZD",
    "AUDJPY","AUDNZD","AUDCAD","AUDCHF",
    "NZDJPY","NZDCAD","NZDCHF","CADJPY","CADCHF","CHFJPY",
    "XAUUSD","XAGUSD","BTCUSD","NAS100","US30",
]

# ── State Management ────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "active_trades": {},    # ticket -> trade info
        "closed_trades": [],    # history
        "started_at": datetime.now().isoformat(),
        "total_opened": 0,
        "total_closed": 0,
        "cycles": 0,
    }

def save_state(state):
    state["last_update"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=str)

def save_track_record(trade_info):
    """Save closed trade to track_records for ranking."""
    sid = trade_info.get("strategy_id", "UNKNOWN")
    fname = f"{sid}_{int(time.time())}.json"
    fpath = os.path.join(TRACK_DIR, fname)
    try:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(trade_info, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        log.error(f"Failed to save track record: {e}")

# ── MT5 Helpers ─────────────────────────────────────────────
def init_mt5():
    if not mt5.initialize(path=MT5_PATH, login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        log.warning(f"MT5 init with credentials failed: {mt5.last_error()} — trying path-only...")
        mt5.shutdown()
        if not mt5.initialize(MT5_PATH):
            log.error(f"MT5 init failed: {mt5.last_error()}")
            return False
    
    # Build symbol suffix map
    SPECIAL = {"NAS100": ["NAS100+","NAS100","USTEC+","USTEC"],
               "US30": ["DJ30+","DJ30","US30+","US30"]}
    
    for sym in ALL_SYMBOLS:
        if sym in SPECIAL:
            for c in SPECIAL[sym]:
                if mt5.symbol_info(c):
                    SUFFIX_MAP[sym] = c
                    break
        else:
            for s in [sym + "+", sym]:
                if mt5.symbol_info(s):
                    SUFFIX_MAP[sym] = s
                    break
    
    acc = mt5.account_info()
    log.info(f"MT5 connected: {acc.login} | Balance: ${acc.balance:.2f} | Symbols: {len(SUFFIX_MAP)}/33")
    return True

def get_mt5_symbol(symbol):
    """Convert clean symbol to broker symbol."""
    return SUFFIX_MAP.get(symbol, symbol + "+")

def get_clean_symbol(mt5_sym):
    """Convert broker symbol to clean symbol."""
    for clean, broker in SUFFIX_MAP.items():
        if broker == mt5_sym:
            return clean
    return mt5_sym.replace("+", "")

def get_our_positions():
    """Get all positions opened by our system (magic number)."""
    positions = mt5.positions_get()
    if not positions:
        return []
    return [p for p in positions if p.magic == MAGIC_NUMBER]

def get_all_positions():
    """Get ALL positions (including manual ones we should track)."""
    positions = mt5.positions_get()
    return list(positions) if positions else []

# ── Signal Reader ───────────────────────────────────────────
def read_pending_signals():
    """Read signals from server's signal queue."""
    signal_file = os.path.join(PROJECT, "data", "pending_signals.json")
    if not os.path.exists(signal_file):
        return []
    try:
        with open(signal_file, "r", encoding="utf-8") as f:
            signals = json.load(f)
        # Clear after reading
        with open(signal_file, "w") as f:
            json.dump([], f)
        return signals if isinstance(signals, list) else []
    except:
        return []

# ── Trade Execution ─────────────────────────────────────────
def open_trade(signal):
    """Open a trade based on signal."""
    symbol = signal.get("symbol", "")
    direction = signal.get("signal", signal.get("direction", "")).upper()
    strategy_id = signal.get("strategy_id", "UNKNOWN")
    confidence = signal.get("confidence", 0)
    sl_price = signal.get("sl_price", 0)
    tp_price = signal.get("tp1_price", signal.get("tp_price", 0))
    
    if direction not in ("BUY", "SELL"):
        return None
    
    mt5_sym = get_mt5_symbol(symbol)
    info = mt5.symbol_info(mt5_sym)
    if not info:
        log.warning(f"Symbol not found: {mt5_sym}")
        return None
    
    # Enable symbol if needed
    if not info.visible:
        mt5.symbol_select(mt5_sym, True)
    
    tick = mt5.symbol_info_tick(mt5_sym)
    if not tick:
        return None
    
    price = tick.ask if direction == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    
    # Lot size (conservative for testing)
    lot = 0.01
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": mt5_sym,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl_price if sl_price > 0 else 0.0,
        "tp": tp_price if tp_price > 0 else 0.0,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": f"WB|{strategy_id}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        log.info(f"✅ OPENED {direction} {symbol} | {strategy_id} | ticket={result.order} | price={price}")
        return {
            "ticket": result.order,
            "symbol": symbol,
            "mt5_symbol": mt5_sym,
            "direction": direction,
            "strategy_id": strategy_id,
            "confidence": confidence,
            "entry_price": price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "lot": lot,
            "opened_at": datetime.now().isoformat(),
            "magic": MAGIC_NUMBER,
        }
    else:
        rc = result.retcode if result else "None"
        comment = result.comment if result else "Unknown"
        log.warning(f"❌ FAILED {direction} {symbol} | {strategy_id} | rc={rc} | {comment}")
        return None

def close_trade(ticket, reason="signal"):
    """Close a specific position by ticket."""
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        return False
    
    p = pos[0]
    close_type = mt5.ORDER_TYPE_SELL if p.type == 0 else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(p.symbol)
    if not tick:
        return False
    
    price = tick.bid if p.type == 0 else tick.ask
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": close_type,
        "position": ticket,
        "price": price,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": f"WB_CLOSE|{reason}",
    }
    
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        log.info(f"✅ CLOSED ticket={ticket} | {p.symbol} | profit=${p.profit:+.2f} | reason={reason}")
        return True
    return False

# ── Position Monitor ────────────────────────────────────────
def sync_positions(state):
    """Sync MT5 positions with our state. Detect closed trades."""
    our_positions = get_all_positions()
    mt5_tickets = {p.ticket for p in our_positions}
    
    # Check for positions that closed (in our state but not in MT5)
    closed = []
    for ticket_str, trade in list(state["active_trades"].items()):
        ticket = int(ticket_str)
        if ticket not in mt5_tickets:
            # Position was closed (by SL/TP or manually)
            trade["closed_at"] = datetime.now().isoformat()
            trade["close_reason"] = "sl_tp_or_manual"
            
            # Try to get close price from history
            from_date = datetime.now() - timedelta(days=1)
            deals = mt5.history_deals_get(from_date, datetime.now(), group=f"*{trade.get('mt5_symbol', '')}*")
            if deals:
                for d in reversed(deals):
                    if d.position_id == ticket:
                        trade["close_price"] = d.price
                        trade["profit"] = d.profit
                        trade["close_reason"] = "tp" if d.profit > 0 else "sl"
                        break
            
            # Calculate PnL in pips
            if "close_price" in trade and "entry_price" in trade:
                sym = trade.get("symbol", "")
                pip_size = 0.1 if "XAU" in sym or "XAG" in sym else 100 if "JPY" in sym else 0.0001
                diff = trade["close_price"] - trade["entry_price"]
                if trade.get("direction") == "SELL":
                    diff = -diff
                trade["pnl_pips"] = round(diff / pip_size, 1) if pip_size else 0
            
            closed.append(trade)
            state["closed_trades"].append(trade)
            state["total_closed"] += 1
            del state["active_trades"][ticket_str]
            
            # Save track record
            save_track_record(trade)
            log.info(f"📊 Trade closed: {trade.get('strategy_id')} | {trade.get('symbol')} | "
                     f"PnL: {trade.get('pnl_pips', '?')} pips | ${trade.get('profit', 0):+.2f}")
    
    # Check for new positions (opened manually or by server before restart)
    for p in our_positions:
        ticket_str = str(p.ticket)
        if ticket_str not in state["active_trades"]:
            # Parse strategy from comment
            comment = p.comment or ""
            strategy_id = ""
            if "WB|" in comment:
                strategy_id = comment.split("WB|")[1].split("|")[0]
            
            trade_info = {
                "ticket": p.ticket,
                "symbol": get_clean_symbol(p.symbol),
                "mt5_symbol": p.symbol,
                "direction": "BUY" if p.type == 0 else "SELL",
                "strategy_id": strategy_id,
                "entry_price": p.price_open,
                "sl_price": p.sl,
                "tp_price": p.tp,
                "lot": p.volume,
                "opened_at": datetime.fromtimestamp(p.time).isoformat(),
                "magic": p.magic,
                "current_profit": p.profit,
                "adopted": True,  # Means we found it, didn't open it
            }
            state["active_trades"][ticket_str] = trade_info
            log.info(f"📌 Adopted position: ticket={p.ticket} | {p.symbol} | "
                     f"{'BUY' if p.type == 0 else 'SELL'} | profit=${p.profit:+.2f}")
    
    return closed

def update_profit(state):
    """Update current P&L for all active trades."""
    for ticket_str, trade in state["active_trades"].items():
        pos = mt5.positions_get(ticket=int(ticket_str))
        if pos:
            trade["current_profit"] = pos[0].profit
            trade["current_price"] = pos[0].price_current

# ── Main Loop ───────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("  TRADE GUARDIAN starting...")
    log.info("=" * 60)
    
    # Write PID file
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    
    # Init MT5
    if not init_mt5():
        log.error("Cannot start without MT5")
        sys.exit(1)
    
    state = load_state()
    log.info(f"State loaded: {len(state['active_trades'])} active, {state['total_closed']} closed historically")
    
    # Signal handler for clean shutdown
    running = [True]
    def on_stop(sig, frame):
        log.info("Shutdown signal received...")
        running[0] = False
    signal.signal(signal.SIGINT, on_stop)
    signal.signal(signal.SIGTERM, on_stop)
    
    while running[0]:
        try:
            cycle_start = time.time()
            state["cycles"] += 1
            
            # Ensure MT5 is connected
            if not mt5.terminal_info():
                log.warning("MT5 disconnected, reconnecting...")
                if not init_mt5():
                    time.sleep(10)
                    continue
            
            # 1. Sync positions (detect closed trades)
            closed = sync_positions(state)
            if closed:
                for c in closed:
                    log.info(f"  Closed: {c.get('strategy_id')} | {c.get('pnl_pips', '?')} pips")
            
            # 2. Read pending signals from server
            signals = read_pending_signals()
            if signals:
                log.info(f"📥 {len(signals)} new signals")
                for sig in signals:
                    result = open_trade(sig)
                    if result:
                        state["active_trades"][str(result["ticket"])] = result
                        state["total_opened"] += 1
            
            # 3. Update current profit
            update_profit(state)
            
            # 4. Save state
            save_state(state)
            
            # 5. Status log every 10 cycles
            if state["cycles"] % 10 == 0:
                n_active = len(state["active_trades"])
                total_pnl = sum(t.get("current_profit", 0) for t in state["active_trades"].values())
                log.info(f"📊 Cycle {state['cycles']} | Active: {n_active} | "
                         f"P&L: ${total_pnl:+.2f} | Closed: {state['total_closed']}")
            
            # Wait for next cycle
            elapsed = time.time() - cycle_start
            wait = max(0, CYCLE_SECONDS - elapsed)
            time.sleep(wait)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Cycle error: {e}")
            time.sleep(10)
    
    # Cleanup
    save_state(state)
    mt5.shutdown()
    
    try:
        os.remove(PID_FILE)
    except:
        pass
    
    log.info("Trade Guardian stopped.")

if __name__ == "__main__":
    main()
