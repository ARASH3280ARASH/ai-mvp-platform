"""
Whilber-AI — MT5 Executor v2.0
================================
Real order execution on MetaTrader 5.
- Open positions (market orders)
- Modify SL/TP
- Close positions (full/partial)
- Track by magic number
- Position sizing with equal risk
"""

import json
import os
import time
import math
from datetime import datetime, timezone
from threading import Lock

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

PROJECT = r"C:\Users\Administrator\Desktop\mvp"
CONFIG_PATH = os.path.join(PROJECT, "data", "analysis", "executor_config.json")
LOG_PATH = os.path.join(PROJECT, "data", "analysis", "executor_log.json")

_lock = Lock()
_config = None


def _load_config():
    global _config
    if _config is None:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _config = json.load(f)
        except Exception as e:
            print(f"[EXECUTOR] Config load error: {e}")
            _config = {"symbols": {}, "risk_per_trade_pct": 1.0}
    return _config


def _log_action(action, data):
    """Append to executor log."""
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **data,
    }
    log = []
    try:
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                log = json.load(f)
    except Exception:
        log = []

    log.append(entry)
    # Keep last 1000 entries
    if len(log) > 1000:
        log = log[-1000:]

    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def ensure_connected():
    """Ensure MT5 is connected."""
    if mt5 is None:
        return False
    if not mt5.terminal_info():
        _path = r"C:\Program Files\Moneta Markets MT5 Terminal\terminal64.exe"
        if not mt5.initialize(path=_path, login=1035360, password="G0Z#IQ1w", server="MonetaMarkets-Demo"):
            # Fallback to path-only
            mt5.shutdown()
            if not mt5.initialize(path=_path):
                print(f"[EXECUTOR] MT5 init failed: {mt5.last_error()}")
                return False
    return True


def get_account_info():
    """Get current account balance, equity, margin."""
    if not ensure_connected():
        return None
    info = mt5.account_info()
    if info is None:
        return None
    return {
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "free_margin": info.margin_free,
        "profit": info.profit,
        "leverage": info.leverage,
    }


def get_open_positions(magic_filter=True):
    """Get all open positions (optionally filtered by our magic numbers)."""
    if not ensure_connected():
        return []
    positions = mt5.positions_get()
    if positions is None:
        return []

    config = _load_config()
    our_magics = set()
    if magic_filter:
        for sym_cfg in config.get("symbols", {}).values():
            our_magics.add(sym_cfg.get("magic", 0))

    result = []
    for pos in positions:
        if magic_filter and pos.magic not in our_magics:
            continue
        result.append({
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": "BUY" if pos.type == 0 else "SELL",
            "volume": pos.volume,
            "open_price": pos.price_open,
            "sl": pos.sl,
            "tp": pos.tp,
            "profit": pos.profit,
            "magic": pos.magic,
            "comment": pos.comment,
            "time_open": datetime.fromtimestamp(pos.time, tz=timezone.utc).isoformat(),
        })
    return result


def calculate_lot(symbol, sl_pips, risk_pct=None):
    """
    Calculate lot size for equal dollar risk.
    Formula: lot = (balance * risk%) / (sl_pips * pip_value_per_lot)
    """
    config = _load_config()
    if risk_pct is None:
        risk_pct = config.get("risk_per_trade_pct", 1.0)

    sym_cfg = config.get("symbols", {}).get(symbol)
    if not sym_cfg:
        print(f"[EXECUTOR] Symbol {symbol} not in config")
        return 0.01  # fallback

    acct = get_account_info()
    if acct is None:
        return 0.01

    balance = acct["balance"]
    risk_usd = balance * risk_pct / 100.0
    pip_value = sym_cfg.get("pip_value_per_lot", 10.0)

    if sl_pips <= 0 or pip_value <= 0:
        return sym_cfg.get("volume_min", 0.01)

    raw_lot = risk_usd / (sl_pips * pip_value)

    # Round to volume_step
    vol_step = sym_cfg.get("volume_step", 0.01)
    vol_min = sym_cfg.get("volume_min", 0.01)
    vol_max = sym_cfg.get("max_lot", 5.0)

    lot = max(vol_min, min(vol_max, math.floor(raw_lot / vol_step) * vol_step))
    lot = round(lot, 2)

    return lot


def check_safety():
    """Check if we can open new positions (DD, daily loss, max positions)."""
    config = _load_config()
    acct = get_account_info()
    if acct is None:
        return False, "Cannot get account info"

    # Max drawdown check
    max_dd = config.get("max_drawdown_pct", 5.0)
    dd_pct = ((acct["balance"] - acct["equity"]) / acct["balance"] * 100) if acct["balance"] > 0 else 0
    if dd_pct > max_dd:
        return False, f"Drawdown {dd_pct:.1f}% > {max_dd}%"

    # Max open positions
    max_pos = config.get("max_open_positions", 10)
    positions = get_open_positions()
    if len(positions) >= max_pos:
        return False, f"Max positions reached: {len(positions)}/{max_pos}"

    return True, "OK"


def check_symbol_limit(symbol):
    """Check max positions per symbol."""
    config = _load_config()
    max_per = config.get("max_per_symbol", 2)
    positions = get_open_positions()
    sym_cfg = config.get("symbols", {}).get(symbol, {})
    broker_name = sym_cfg.get("broker_name", symbol)

    count = sum(1 for p in positions if p["symbol"] == broker_name)
    if count >= max_per:
        return False, f"{symbol}: {count}/{max_per} positions"
    return True, "OK"


def open_position(symbol, direction, sl_price, tp_price, lot=None,
                  strategy_id="", comment=""):
    """
    Open a real position on MT5.

    Args:
        symbol: Internal symbol name (e.g., "EURUSD")
        direction: "BUY" or "SELL"
        sl_price: Stop loss price
        tp_price: Take profit price
        lot: Lot size (None = auto-calculate)
        strategy_id: Strategy ID for tracking
        comment: MT5 order comment
    Returns:
        dict with success, ticket, details
    """
    with _lock:
        if not ensure_connected():
            return {"success": False, "error": "MT5 not connected"}

        config = _load_config()
        sym_cfg = config.get("symbols", {}).get(symbol)
        if not sym_cfg:
            return {"success": False, "error": f"Unknown symbol: {symbol}"}

        # Safety checks
        safe, reason = check_safety()
        if not safe:
            _log_action("BLOCKED", {"symbol": symbol, "reason": reason})
            return {"success": False, "error": f"Safety: {reason}"}

        sym_safe, sym_reason = check_symbol_limit(symbol)
        if not sym_safe:
            _log_action("BLOCKED", {"symbol": symbol, "reason": sym_reason})
            return {"success": False, "error": f"Limit: {sym_reason}"}

        broker_name = sym_cfg["broker_name"]
        magic = sym_cfg["magic"]
        pip_size = sym_cfg["pip_size"]

        # Get current price
        tick = mt5.symbol_info_tick(broker_name)
        if tick is None:
            return {"success": False, "error": f"No tick for {broker_name}"}

        entry_price = tick.ask if direction == "BUY" else tick.bid

        # Validate SL/TP distances (stop level)
        stop_level = sym_cfg.get("stop_level", 20)
        point = sym_cfg.get("point", 0.00001)
        min_dist = stop_level * point

        sl_dist = abs(entry_price - sl_price)
        tp_dist = abs(entry_price - tp_price)

        if sl_dist < min_dist:
            return {"success": False, "error": f"SL too close: {sl_dist:.5f} < {min_dist:.5f}"}
        if tp_dist < min_dist:
            return {"success": False, "error": f"TP too close: {tp_dist:.5f} < {min_dist:.5f}"}

        # R:R check
        rr = tp_dist / sl_dist if sl_dist > 0 else 0
        min_rr = config.get("min_rr", 1.5)
        if rr < min_rr:
            return {"success": False, "error": f"R:R {rr:.2f} < {min_rr}"}

        # Calculate lot if not provided
        if lot is None:
            sl_pips = sl_dist / pip_size
            lot = calculate_lot(symbol, sl_pips)

        # Build order comment
        if not comment:
            comment = f"{strategy_id}|{direction[:1]}"
        # MT5 comment max 31 chars
        comment = comment[:31]

        # Build request
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_name,
            "volume": lot,
            "type": order_type,
            "price": entry_price,
            "sl": round(sl_price, sym_cfg["digits"]),
            "tp": round(tp_price, sym_cfg["digits"]),
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(request)

        if result is None:
            err = mt5.last_error()
            _log_action("ORDER_FAIL", {"symbol": symbol, "error": str(err), "request": str(request)})
            return {"success": False, "error": f"MT5 error: {err}"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            _log_action("ORDER_FAIL", {
                "symbol": symbol,
                "retcode": result.retcode,
                "comment": result.comment,
            })
            return {
                "success": False,
                "error": f"Order rejected: {result.retcode} - {result.comment}",
                "retcode": result.retcode,
            }

        # Success!
        _log_action("OPEN", {
            "symbol": symbol,
            "ticket": result.order,
            "direction": direction,
            "lot": lot,
            "price": result.price,
            "sl": sl_price,
            "tp": tp_price,
            "magic": magic,
            "strategy": strategy_id,
            "rr": round(rr, 2),
        })

        return {
            "success": True,
            "ticket": result.order,
            "price": result.price,
            "lot": lot,
            "sl": sl_price,
            "tp": tp_price,
            "magic": magic,
            "rr": round(rr, 2),
        }


def modify_position(ticket, new_sl=None, new_tp=None):
    """Modify SL/TP of an open position."""
    with _lock:
        if not ensure_connected():
            return {"success": False, "error": "MT5 not connected"}

        pos = mt5.positions_get(ticket=ticket)
        if not pos or len(pos) == 0:
            return {"success": False, "error": f"Position {ticket} not found"}

        pos = pos[0]
        sl = new_sl if new_sl is not None else pos.sl
        tp = new_tp if new_tp is not None else pos.tp

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": sl,
            "tp": tp,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = result.comment if result else str(mt5.last_error())
            _log_action("MODIFY_FAIL", {"ticket": ticket, "error": err})
            return {"success": False, "error": err}

        _log_action("MODIFY", {"ticket": ticket, "sl": sl, "tp": tp})
        return {"success": True, "sl": sl, "tp": tp}


def close_position(ticket, lot=None):
    """Close a position (full or partial)."""
    with _lock:
        if not ensure_connected():
            return {"success": False, "error": "MT5 not connected"}

        pos = mt5.positions_get(ticket=ticket)
        if not pos or len(pos) == 0:
            return {"success": False, "error": f"Position {ticket} not found"}

        pos = pos[0]
        close_vol = lot if lot else pos.volume
        close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY

        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            return {"success": False, "error": "No tick data"}

        price = tick.bid if pos.type == 0 else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": close_vol,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": pos.magic,
            "comment": "close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = result.comment if result else str(mt5.last_error())
            _log_action("CLOSE_FAIL", {"ticket": ticket, "error": err})
            return {"success": False, "error": err}

        _log_action("CLOSE", {
            "ticket": ticket,
            "price": result.price,
            "volume": close_vol,
            "profit": pos.profit,
        })
        return {"success": True, "price": result.price, "profit": pos.profit}


def close_all(reason="emergency"):
    """Emergency: close all our positions."""
    positions = get_open_positions()
    results = []
    for pos in positions:
        r = close_position(pos["ticket"])
        r["symbol"] = pos["symbol"]
        results.append(r)
    _log_action("CLOSE_ALL", {"reason": reason, "count": len(positions)})
    return results


def move_to_breakeven(ticket, offset_pips=1):
    """Move SL to entry price (+ small offset)."""
    if not ensure_connected():
        return {"success": False}

    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        return {"success": False}

    pos = pos[0]
    # Find symbol config
    config = _load_config()
    sym_name = pos.symbol
    pip_size = 0.0001
    for s, c in config.get("symbols", {}).items():
        if c.get("broker_name") == sym_name:
            pip_size = c["pip_size"]
            break

    entry = pos.price_open
    if pos.type == 0:  # BUY
        new_sl = entry + offset_pips * pip_size
    else:  # SELL
        new_sl = entry - offset_pips * pip_size

    return modify_position(ticket, new_sl=round(new_sl, 5))
