"""
Whilber-AI MVP - Performance Monitor
======================================
MT5 account performance data fetching and metrics calculation.
"""

import sys
from datetime import datetime, timezone, timedelta
from loguru import logger

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")

try:
    import MetaTrader5 as mt5
    from backend.mt5.mt5_connector import MT5Connector
    _MT5_OK = True
except ImportError:
    _MT5_OK = False
    logger.warning("⚠️ MetaTrader5 not available for performance_monitor")


def _ensure_mt5():
    """Ensure MT5 is connected, return True/False."""
    if not _MT5_OK:
        return False
    connector = MT5Connector.get_instance()
    return connector.ensure_connected()


def get_account_details() -> dict:
    """Full account info from MT5."""
    if not _ensure_mt5():
        return {"error": "MT5 not connected"}
    info = mt5.account_info()
    if info is None:
        return {"error": "Could not get account info"}
    return {
        "login": info.login,
        "server": info.server,
        "name": info.name,
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "free_margin": info.margin_free,
        "profit": info.profit,
        "leverage": info.leverage,
        "currency": info.currency,
        "margin_level": info.margin_level if info.margin > 0 else 0.0,
        "trade_mode": info.trade_mode,
        "connected": True,
    }


def get_open_positions() -> list:
    """All open positions (no magic filter)."""
    if not _ensure_mt5():
        return []
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return []
    result = []
    now = datetime.now(timezone.utc)
    for pos in positions:
        open_time = datetime.fromtimestamp(pos.time, tz=timezone.utc)
        duration = now - open_time
        hours = int(duration.total_seconds() // 3600)
        mins = int((duration.total_seconds() % 3600) // 60)
        result.append({
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": "BUY" if pos.type == 0 else "SELL",
            "volume": pos.volume,
            "open_price": pos.price_open,
            "current_price": pos.price_current,
            "sl": pos.sl,
            "tp": pos.tp,
            "profit": pos.profit,
            "swap": pos.swap,
            "commission": pos.commission if hasattr(pos, 'commission') else 0.0,
            "time_open": open_time.isoformat(),
            "magic": pos.magic,
            "comment": pos.comment,
            "duration": f"{hours}h {mins}m",
        })
    return result


def get_trade_history(days: int = 30) -> list:
    """Closed trades from MT5 history."""
    if not _ensure_mt5():
        return []
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=days)
    deals = mt5.history_deals_get(from_date, to_date)
    if deals is None or len(deals) == 0:
        return []
    result = []
    for deal in deals:
        # Filter: only actual trades (buy/sell), skip balance/credit/etc
        if deal.type not in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL):
            continue
        # Determine entry type
        if deal.entry == mt5.DEAL_ENTRY_IN:
            entry_type = "in"
        elif deal.entry == mt5.DEAL_ENTRY_OUT:
            entry_type = "out"
        elif deal.entry == mt5.DEAL_ENTRY_INOUT:
            entry_type = "inout"
        else:
            entry_type = "unknown"
        result.append({
            "ticket": deal.ticket,
            "order": deal.order,
            "symbol": deal.symbol,
            "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
            "volume": deal.volume,
            "price": deal.price,
            "profit": deal.profit,
            "swap": deal.swap,
            "commission": deal.commission,
            "time": datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat(),
            "magic": deal.magic,
            "comment": deal.comment,
            "entry_type": entry_type,
        })
    return result


def calculate_metrics(trades: list) -> dict:
    """Calculate trading performance metrics from closed trades."""
    # Only count exit trades for PnL
    closed = [t for t in trades if t.get("entry_type") == "out"]
    total = len(closed)
    if total == 0:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate": 0, "total_profit": 0, "total_loss": 0,
            "net_profit": 0, "profit_factor": 0, "avg_win": 0, "avg_loss": 0,
            "largest_win": 0, "largest_loss": 0, "avg_trade": 0,
            "expectancy": 0, "sharpe_ratio": 0,
            "max_consecutive_wins": 0, "max_consecutive_losses": 0,
        }

    wins = [t for t in closed if t["profit"] > 0]
    losses = [t for t in closed if t["profit"] < 0]
    total_profit = sum(t["profit"] for t in wins)
    total_loss = abs(sum(t["profit"] for t in losses))
    net = total_profit - total_loss

    win_rate = (len(wins) / total * 100) if total > 0 else 0
    pf = (total_profit / total_loss) if total_loss > 0 else (999.99 if total_profit > 0 else 0)
    avg_win = (total_profit / len(wins)) if wins else 0
    avg_loss = (total_loss / len(losses)) if losses else 0
    avg_trade = net / total if total > 0 else 0
    largest_win = max((t["profit"] for t in wins), default=0)
    largest_loss = min((t["profit"] for t in losses), default=0)

    # Expectancy
    if total > 0:
        win_prob = len(wins) / total
        loss_prob = len(losses) / total
        expectancy = (win_prob * avg_win) - (loss_prob * avg_loss)
    else:
        expectancy = 0

    # Sharpe ratio (daily returns)
    daily_pnl = {}
    for t in closed:
        day = t["time"][:10]
        daily_pnl.setdefault(day, 0)
        daily_pnl[day] += t["profit"]
    returns = list(daily_pnl.values())
    if len(returns) > 1:
        import statistics
        mean_r = statistics.mean(returns)
        std_r = statistics.stdev(returns)
        sharpe = (mean_r / std_r * (252 ** 0.5)) if std_r > 0 else 0
    else:
        sharpe = 0

    # Consecutive wins/losses
    max_cw = max_cl = cw = cl = 0
    for t in closed:
        if t["profit"] > 0:
            cw += 1
            cl = 0
        elif t["profit"] < 0:
            cl += 1
            cw = 0
        else:
            cw = cl = 0
        max_cw = max(max_cw, cw)
        max_cl = max(max_cl, cl)

    return {
        "total_trades": total,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(win_rate, 1),
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "net_profit": round(net, 2),
        "profit_factor": round(pf, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2),
        "avg_trade": round(avg_trade, 2),
        "expectancy": round(expectancy, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_consecutive_wins": max_cw,
        "max_consecutive_losses": max_cl,
    }


def get_equity_curve(days: int = 30) -> dict:
    """Daily equity snapshots from trade history."""
    trades = get_trade_history(days)
    closed = [t for t in trades if t.get("entry_type") == "out"]
    if not closed:
        return {"dates": [], "equity": [], "balance": [], "daily_pnl": []}

    # Get starting balance
    acct = get_account_details()
    current_balance = acct.get("balance", 0)
    total_pnl = sum(t["profit"] + t.get("swap", 0) + t.get("commission", 0) for t in closed)
    start_balance = current_balance - total_pnl

    # Group by day
    daily = {}
    for t in closed:
        day = t["time"][:10]
        daily.setdefault(day, 0)
        daily[day] += t["profit"] + t.get("swap", 0) + t.get("commission", 0)

    sorted_days = sorted(daily.keys())
    dates = []
    equity_vals = []
    balance_vals = []
    daily_pnl = []
    running = start_balance

    for d in sorted_days:
        running += daily[d]
        dates.append(d)
        balance_vals.append(round(running, 2))
        equity_vals.append(round(running, 2))
        daily_pnl.append(round(daily[d], 2))

    return {
        "dates": dates,
        "equity": equity_vals,
        "balance": balance_vals,
        "daily_pnl": daily_pnl,
    }


def get_drawdown_analysis(equity_curve: dict) -> dict:
    """Max drawdown calculation from equity curve."""
    equity = equity_curve.get("equity", [])
    if not equity:
        return {
            "max_drawdown_pct": 0, "max_drawdown_value": 0,
            "current_drawdown_pct": 0, "drawdown_periods": [],
        }

    peak = equity[0]
    max_dd_val = 0
    max_dd_pct = 0
    dd_periods = []
    current_dd_start = None

    for i, val in enumerate(equity):
        if val > peak:
            if current_dd_start is not None:
                dd_periods.append({
                    "start": equity_curve["dates"][current_dd_start],
                    "end": equity_curve["dates"][i],
                })
                current_dd_start = None
            peak = val
        else:
            dd_val = peak - val
            dd_pct = (dd_val / peak * 100) if peak > 0 else 0
            if dd_val > max_dd_val:
                max_dd_val = dd_val
                max_dd_pct = dd_pct
            if current_dd_start is None and dd_val > 0:
                current_dd_start = i

    # Current drawdown
    current_dd = 0
    if equity:
        current_dd = ((peak - equity[-1]) / peak * 100) if peak > 0 else 0

    return {
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_drawdown_value": round(max_dd_val, 2),
        "current_drawdown_pct": round(max(current_dd, 0), 2),
        "drawdown_periods": dd_periods[-5:],  # Last 5
    }


def get_daily_summary(days: int = 30) -> list:
    """Per-day breakdown of trading activity."""
    trades = get_trade_history(days)
    closed = [t for t in trades if t.get("entry_type") == "out"]
    if not closed:
        return []

    daily = {}
    for t in closed:
        day = t["time"][:10]
        daily.setdefault(day, [])
        daily[day].append(t)

    result = []
    for day in sorted(daily.keys(), reverse=True):
        day_trades = daily[day]
        wins = [t for t in day_trades if t["profit"] > 0]
        pnl = sum(t["profit"] for t in day_trades)
        best = max(day_trades, key=lambda x: x["profit"])
        worst = min(day_trades, key=lambda x: x["profit"])
        wr = (len(wins) / len(day_trades) * 100) if day_trades else 0
        result.append({
            "date": day,
            "trades_count": len(day_trades),
            "pnl": round(pnl, 2),
            "win_rate": round(wr, 1),
            "best_trade": round(best["profit"], 2),
            "worst_trade": round(worst["profit"], 2),
        })
    return result


def get_symbol_distribution(trades: list) -> list:
    """Trades grouped by symbol."""
    closed = [t for t in trades if t.get("entry_type") == "out"]
    if not closed:
        return []

    by_symbol = {}
    for t in closed:
        sym = t["symbol"]
        by_symbol.setdefault(sym, [])
        by_symbol[sym].append(t)

    result = []
    for sym, sym_trades in sorted(by_symbol.items()):
        wins = [t for t in sym_trades if t["profit"] > 0]
        pnl = sum(t["profit"] for t in sym_trades)
        wr = (len(wins) / len(sym_trades) * 100) if sym_trades else 0
        result.append({
            "symbol": sym,
            "count": len(sym_trades),
            "pnl": round(pnl, 2),
            "win_rate": round(wr, 1),
        })
    return sorted(result, key=lambda x: x["count"], reverse=True)


def get_performance_snapshot() -> dict:
    """Single call aggregating everything."""
    try:
        account = get_account_details()
        positions = get_open_positions()
        trades = get_trade_history(30)
        metrics = calculate_metrics(trades)
        eq_curve = get_equity_curve(30)
        drawdown = get_drawdown_analysis(eq_curve)
        daily = get_daily_summary(30)
        symbols = get_symbol_distribution(trades)

        return {
            "account": account,
            "positions": positions,
            "metrics": metrics,
            "equity_curve": eq_curve,
            "drawdown": drawdown,
            "daily_summary": daily,
            "symbol_distribution": symbols,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Performance snapshot error: {e}")
        return {"error": str(e)}
