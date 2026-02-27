"""
Whilber-AI — Backtesting Engine
===================================
Bar-by-bar simulation with indicator conditions, exits, risk management.
Supports filters (time, day, volatility, trend) and enhanced reporting.
"""

import numpy as np
from datetime import datetime, timezone
from collections import defaultdict

from backend.api.indicator_calc import compute_indicator


def _check_condition(cond_type, val_a, val_b, prev_a=None, prev_b=None):
    """Check if condition is met."""
    if val_a is None or np.isnan(val_a):
        return False
    if cond_type == "is_above":
        return val_a > val_b
    elif cond_type == "is_below":
        return val_a < val_b
    elif cond_type == "crosses_above":
        if prev_a is None or np.isnan(prev_a):
            return False
        return prev_a <= prev_b and val_a > val_b
    elif cond_type == "crosses_below":
        if prev_a is None or np.isnan(prev_a):
            return False
        return prev_a >= prev_b and val_a < val_b
    elif cond_type == "is_rising":
        if prev_a is None or np.isnan(prev_a):
            return False
        return val_a > prev_a
    elif cond_type == "is_falling":
        if prev_a is None or np.isnan(prev_a):
            return False
        return val_a < prev_a
    elif cond_type == "is_overbought":
        return val_a > (val_b if val_b else 70)
    elif cond_type == "is_oversold":
        return val_a < (val_b if val_b else 30)
    elif cond_type == "equals":
        return abs(val_a - val_b) < 0.001
    return False


def _pip_value(symbol, price):
    """Get approximate pip value."""
    sym = symbol.upper()
    if "JPY" in sym:
        return 0.01
    elif "XAU" in sym or "GOLD" in sym:
        return 0.1
    elif "BTC" in sym:
        return 1.0
    elif "US30" in sym or "NAS" in sym or "SPX" in sym:
        return 1.0
    return 0.0001


def _parse_bar_time(bar_time):
    """Parse bar time to datetime object. Handles numpy datetime64 and strings."""
    if hasattr(bar_time, 'astype'):
        # numpy datetime64
        try:
            ts = (bar_time - np.datetime64('1970-01-01T00:00:00')) / np.timedelta64(1, 's')
            return datetime.utcfromtimestamp(float(ts))
        except Exception:
            pass
    try:
        s = str(bar_time)
        if 'T' in s:
            return datetime.fromisoformat(s.replace('Z', '+00:00').replace('+00:00', ''))
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _check_filters(filters, bar_dt, atr_val, price, trend_ma_val):
    """Check all strategy filters. Returns True if bar passes all filters."""
    if not filters or bar_dt is None:
        return True

    for f in filters:
        ftype = f.get("type", "")
        params = f.get("params", {})

        if ftype == "time_filter":
            start_h = params.get("start_hour", 0)
            end_h = params.get("end_hour", 23)
            if bar_dt.hour < start_h or bar_dt.hour > end_h:
                return False

        elif ftype == "day_filter":
            allowed_days = params.get("days", [1, 2, 3, 4, 5])
            # isoweekday: Mon=1..Sun=7
            if bar_dt.isoweekday() not in allowed_days:
                return False

        elif ftype == "spread_filter":
            # Spread filter is handled externally (spread_pips parameter)
            pass

        elif ftype == "volatility_filter":
            if atr_val is not None and not np.isnan(atr_val):
                min_atr = params.get("min_atr", 0)
                max_atr = params.get("max_atr", float('inf'))
                if atr_val < min_atr or atr_val > max_atr:
                    return False

        elif ftype == "trend_filter":
            if trend_ma_val is not None and not np.isnan(trend_ma_val):
                # Only allow trades in direction of trend
                # This is a soft filter — we store the trend direction
                # and use it in direction determination
                pass

    return True


def run_backtest(df, strategy, initial_balance=10000, spread_pips=2):
    """
    Run backtest on DataFrame.
    Returns: dict with trades, stats, equity curve, and enhanced reporting.
    """
    n = len(df)
    if n < 50:
        return {"success": False, "error": "Not enough data (min 50 bars)"}

    c = df["close"].values
    h = df["high"].values
    l = df["low"].values
    o = df["open"].values
    times = df["time"].values if "time" in df.columns else list(range(n))

    symbol = strategy.get("symbol", "XAUUSD")
    pip = _pip_value(symbol, c[-1])
    spread = spread_pips * pip
    direction = strategy.get("direction", "both")
    filters = strategy.get("filters", [])

    # Pre-compute all indicators
    ind_cache = {}
    all_conds = strategy.get("entry_conditions", [])

    for cond in all_conds:
        ind_id = cond.get("indicator", "")
        params = cond.get("indicator_params", {})
        key = f"{ind_id}_{hash(str(sorted(params.items())))}"
        if key not in ind_cache and ind_id:
            ind_cache[key] = compute_indicator(df, ind_id, params)
        cond["_cache_key"] = key
        cond["_output"] = cond.get("output", "value")

        # Compare indicator
        if cond.get("compare_to") == "indicator":
            cmp_id = cond.get("compare_indicator", "")
            cmp_params = cond.get("compare_indicator_params", {})
            cmp_key = f"{cmp_id}_{hash(str(sorted(cmp_params.items())))}"
            if cmp_key not in ind_cache and cmp_id:
                ind_cache[cmp_key] = compute_indicator(df, cmp_id, cmp_params)
            cond["_cmp_cache_key"] = cmp_key
            cond["_cmp_output"] = cond.get("compare_output", "value")

    # Pre-compute ATR for exits
    atr_14 = compute_indicator(df, "ATR", {"period": 14})["value"]

    # Pre-compute trend filter MA if needed
    trend_ma = None
    trend_filter_active = False
    for f in filters:
        if f.get("type") == "trend_filter":
            tf_period = f.get("params", {}).get("ma_period", 200)
            trend_ma = compute_indicator(df, "SMA", {"period": tf_period})["value"]
            trend_filter_active = True
            break

    # Risk settings
    risk = strategy.get("risk", {})
    risk_pct = risk.get("risk_per_trade", 2.0) / 100
    max_daily = risk.get("max_daily_trades", 5)
    max_open = risk.get("max_open_trades", 3)
    max_dd = risk.get("max_drawdown", 20) / 100
    min_rr = risk.get("min_rr", 1.5)
    lot_type = risk.get("lot_type", "risk_percent")
    fixed_lot = risk.get("fixed_lot", 0.01)

    # Direction params
    dir_params = strategy.get("direction_params", {"method": "ma_trend", "ma_period": 200})
    dir_method = dir_params.get("method", "ma_trend")
    dir_ma_period = dir_params.get("ma_period", 200)

    # Pre-compute direction MA
    dir_ma_key = f"SMA_{hash(str(sorted({'period': dir_ma_period}.items())))}"
    if dir_ma_key not in ind_cache:
        ind_cache[dir_ma_key] = compute_indicator(df, "SMA", {"period": dir_ma_period})
    dir_ma_vals = ind_cache[dir_ma_key].get("value", np.full(n, np.nan))

    # Simulation state
    balance = float(initial_balance)
    equity_curve = [balance]
    trades = []
    open_trades = []
    daily_count = {}
    peak_balance = balance
    entry_logic = strategy.get("entry_logic", "AND")

    # Exit configs
    tp_configs = strategy.get("exit_take_profit", [])
    sl_configs = strategy.get("exit_stop_loss", [])
    trail_config = strategy.get("exit_trailing")
    be_config = strategy.get("exit_break_even")
    time_exit = strategy.get("exit_time")

    # Enhanced reporting accumulators
    hourly_pnl = defaultdict(lambda: {"pnl": 0.0, "count": 0, "wins": 0})
    daily_pnl = defaultdict(lambda: {"pnl": 0.0, "count": 0, "wins": 0})
    monthly_data = defaultdict(lambda: {"pnl": 0.0, "count": 0, "wins": 0})

    # Bar-by-bar simulation
    for i in range(1, n):
        bar_time = str(times[i])
        day_key = bar_time[:10] if len(bar_time) >= 10 else str(i)

        # Check max drawdown
        if balance < initial_balance * (1 - max_dd):
            break

        # Parse datetime for filters
        bar_dt = _parse_bar_time(times[i])

        # Process open trades
        closed_indices = []
        for ti, trade in enumerate(open_trades):
            price = c[i]
            is_buy = trade["type"] == "BUY"

            # Trailing stop update
            if trail_config and trade.get("trailing_active"):
                if trail_config.get("type") == "trailing_fixed":
                    trail_dist = trail_config.get("value", 20) * pip
                elif trail_config.get("type") == "trailing_atr":
                    atr_v = atr_14[i] if not np.isnan(atr_14[i]) else atr_14[i - 1] if i > 0 else 0
                    trail_dist = trail_config.get("value", 2) * atr_v
                else:
                    trail_dist = 0

                if trail_dist > 0:
                    if is_buy:
                        new_sl = price - trail_dist
                        if new_sl > trade["sl"]:
                            trade["sl"] = new_sl
                    else:
                        new_sl = price + trail_dist
                        if new_sl < trade["sl"]:
                            trade["sl"] = new_sl

            # Break even
            if be_config and not trade.get("be_moved"):
                trigger = be_config.get("trigger", 20) * pip
                lock = be_config.get("lock", 5) * pip
                if is_buy and price >= trade["entry"] + trigger:
                    trade["sl"] = trade["entry"] + lock
                    trade["be_moved"] = True
                    trade["trailing_active"] = True
                elif not is_buy and price <= trade["entry"] - trigger:
                    trade["sl"] = trade["entry"] - lock
                    trade["be_moved"] = True
                    trade["trailing_active"] = True

            # Check SL
            if is_buy and l[i] <= trade["sl"]:
                pnl = (trade["sl"] - trade["entry"]) * trade["lot_size"] * (100000 if pip < 0.01 else 100 if pip < 1 else 1)
                trade["exit_price"] = trade["sl"]
                trade["exit_bar"] = i
                trade["exit_time"] = bar_time
                trade["pnl"] = round(pnl, 2)
                trade["exit_reason"] = "SL"
                trades.append(trade)
                closed_indices.append(ti)
                balance += pnl
                _record_trade_stats(trade, bar_dt, hourly_pnl, daily_pnl, monthly_data)
                continue
            elif not is_buy and h[i] >= trade["sl"]:
                pnl = (trade["entry"] - trade["sl"]) * trade["lot_size"] * (100000 if pip < 0.01 else 100 if pip < 1 else 1)
                trade["exit_price"] = trade["sl"]
                trade["exit_bar"] = i
                trade["exit_time"] = bar_time
                trade["pnl"] = round(pnl, 2)
                trade["exit_reason"] = "SL"
                trades.append(trade)
                closed_indices.append(ti)
                balance += pnl
                _record_trade_stats(trade, bar_dt, hourly_pnl, daily_pnl, monthly_data)
                continue

            # Check TP
            if is_buy and h[i] >= trade["tp"]:
                pnl = (trade["tp"] - trade["entry"]) * trade["lot_size"] * (100000 if pip < 0.01 else 100 if pip < 1 else 1)
                trade["exit_price"] = trade["tp"]
                trade["exit_bar"] = i
                trade["exit_time"] = bar_time
                trade["pnl"] = round(pnl, 2)
                trade["exit_reason"] = "TP"
                trades.append(trade)
                closed_indices.append(ti)
                balance += pnl
                _record_trade_stats(trade, bar_dt, hourly_pnl, daily_pnl, monthly_data)
                continue
            elif not is_buy and l[i] <= trade["tp"]:
                pnl = (trade["entry"] - trade["tp"]) * trade["lot_size"] * (100000 if pip < 0.01 else 100 if pip < 1 else 1)
                trade["exit_price"] = trade["tp"]
                trade["exit_bar"] = i
                trade["exit_time"] = bar_time
                trade["pnl"] = round(pnl, 2)
                trade["exit_reason"] = "TP"
                trades.append(trade)
                closed_indices.append(ti)
                balance += pnl
                _record_trade_stats(trade, bar_dt, hourly_pnl, daily_pnl, monthly_data)
                continue

            # Time exit
            if time_exit:
                bars_held = i - trade["entry_bar"]
                if bars_held >= time_exit.get("bars", 10):
                    pnl_raw = (price - trade["entry"]) if is_buy else (trade["entry"] - price)
                    pnl = pnl_raw * trade["lot_size"] * (100000 if pip < 0.01 else 100 if pip < 1 else 1)
                    trade["exit_price"] = price
                    trade["exit_bar"] = i
                    trade["exit_time"] = bar_time
                    trade["pnl"] = round(pnl, 2)
                    trade["exit_reason"] = "TIME"
                    trades.append(trade)
                    closed_indices.append(ti)
                    balance += pnl
                    _record_trade_stats(trade, bar_dt, hourly_pnl, daily_pnl, monthly_data)
                    continue

        # Remove closed trades
        for idx in sorted(closed_indices, reverse=True):
            open_trades.pop(idx)

        equity_curve.append(balance)
        peak_balance = max(peak_balance, balance)

        # Skip entry if max open
        if len(open_trades) >= max_open:
            continue
        # Skip if max daily
        if daily_count.get(day_key, 0) >= max_daily:
            continue

        # === Apply filters before entry ===
        atr_now = atr_14[i] if not np.isnan(atr_14[i]) else (atr_14[i - 1] if i > 0 and not np.isnan(atr_14[i - 1]) else 0)
        trend_ma_now = trend_ma[i] if trend_ma is not None and i < len(trend_ma) and not np.isnan(trend_ma[i]) else None
        if not _check_filters(filters, bar_dt, atr_now, c[i], trend_ma_now):
            continue

        # Check entry conditions
        buy_signal = False
        sell_signal = False

        cond_results = []
        for cond in all_conds:
            cache = ind_cache.get(cond.get("_cache_key", ""), {})
            output = cond.get("_output", "value")
            vals = cache.get(output, np.full(n, np.nan))
            val_now = vals[i] if i < len(vals) and not np.isnan(vals[i]) else None
            val_prev = vals[i - 1] if i > 0 and i - 1 < len(vals) and not np.isnan(vals[i - 1]) else None

            # Compare value
            cmp_to = cond.get("compare_to", "fixed_value")
            if cmp_to == "fixed_value":
                cmp_val = float(cond.get("compare_value", 0))
                cmp_prev = cmp_val
            elif cmp_to == "indicator":
                cmp_cache = ind_cache.get(cond.get("_cmp_cache_key", ""), {})
                cmp_output = cond.get("_cmp_output", "value")
                cmp_vals = cmp_cache.get(cmp_output, np.full(n, np.nan))
                cmp_val = cmp_vals[i] if i < len(cmp_vals) and not np.isnan(cmp_vals[i]) else None
                cmp_prev = cmp_vals[i - 1] if i > 0 and i - 1 < len(cmp_vals) and not np.isnan(cmp_vals[i - 1]) else cmp_val
            elif cmp_to == "price_close":
                cmp_val = c[i]
                cmp_prev = c[i - 1] if i > 0 else c[i]
            elif cmp_to == "price_high":
                cmp_val = h[i]
                cmp_prev = h[i - 1] if i > 0 else h[i]
            elif cmp_to == "price_low":
                cmp_val = l[i]
                cmp_prev = l[i - 1] if i > 0 else l[i]
            else:
                cmp_val = c[i]
                cmp_prev = c[i - 1] if i > 0 else c[i]

            if val_now is not None and cmp_val is not None:
                met = _check_condition(cond.get("condition", ""), val_now, cmp_val, val_prev, cmp_prev)
            else:
                met = False
            cond_results.append(met)

        if cond_results:
            if entry_logic == "AND":
                signal = all(cond_results)
            else:
                signal = any(cond_results)
        else:
            signal = False

        if not signal:
            continue

        # Determine direction
        if direction == "buy_only":
            buy_signal = True
        elif direction == "sell_only":
            sell_signal = True
        else:
            # Use configurable direction method
            if dir_method == "entry_signal":
                # Use the signal directly; buy if all conditions met as-is
                buy_signal = True
            elif dir_method == "always_both":
                # Open buy (could also open sell on inverse, but simplified for backtest)
                if not np.isnan(dir_ma_vals[i]) and c[i] > dir_ma_vals[i]:
                    buy_signal = True
                else:
                    sell_signal = True
            else:
                # ma_trend (default)
                if not np.isnan(dir_ma_vals[i]) and c[i] > dir_ma_vals[i]:
                    buy_signal = True
                else:
                    sell_signal = True

        # Trend filter direction override
        if trend_filter_active and trend_ma is not None:
            tm = trend_ma[i] if i < len(trend_ma) and not np.isnan(trend_ma[i]) else None
            if tm is not None:
                if buy_signal and c[i] < tm:
                    continue  # Against trend
                if sell_signal and c[i] > tm:
                    continue  # Against trend

        if not buy_signal and not sell_signal:
            continue

        # Calculate TP/SL
        if np.isnan(atr_now) or atr_now == 0:
            atr_now = c[i] * 0.01

        entry_price = c[i] + (spread / 2 if buy_signal else -spread / 2)

        # TP
        tp_dist = 0
        if tp_configs:
            tc = tp_configs[0]
            if tc["type"] == "atr_tp":
                tp_dist = tc["params"].get("multiplier", 2) * atr_now
            elif tc["type"] == "fixed_tp":
                tp_dist = tc["params"].get("pips", 50) * pip
            elif tc["type"] == "percent_tp":
                tp_dist = entry_price * tc["params"].get("percent", 1) / 100
            else:
                tp_dist = 2 * atr_now
        else:
            tp_dist = 2 * atr_now

        # SL
        sl_dist = 0
        if sl_configs:
            sc = sl_configs[0]
            if sc["type"] == "atr_sl":
                sl_dist = sc["params"].get("multiplier", 1.5) * atr_now
            elif sc["type"] == "fixed_sl":
                sl_dist = sc["params"].get("pips", 30) * pip
            elif sc["type"] == "percent_sl":
                sl_dist = entry_price * sc["params"].get("percent", 0.5) / 100
            elif sc["type"] == "swing_sl":
                lb = sc["params"].get("lookback", 10)
                buf = sc["params"].get("buffer_pips", 5) * pip
                if buy_signal:
                    sl_dist = entry_price - np.min(l[max(0, i - lb):i + 1]) + buf
                else:
                    sl_dist = np.max(h[max(0, i - lb):i + 1]) - entry_price + buf
            else:
                sl_dist = 1.5 * atr_now
        else:
            sl_dist = 1.5 * atr_now

        if sl_dist <= 0:
            sl_dist = atr_now
        if tp_dist <= 0:
            tp_dist = atr_now * 2

        # Check R:R
        rr = tp_dist / sl_dist if sl_dist > 0 else 0
        if rr < min_rr:
            continue

        # Position sizing
        if lot_type == "risk_percent":
            risk_amount = balance * risk_pct
            lot_size = risk_amount / (sl_dist / pip) / 10 if sl_dist > 0 else 0.01
            lot_size = round(max(0.01, min(lot_size, 10)), 2)
        elif lot_type == "balance_percent":
            lot_size = round(balance * risk_pct / 10000, 2)
            lot_size = max(0.01, min(lot_size, 10))
        else:
            lot_size = fixed_lot

        # Create trade
        if buy_signal:
            tp_price = entry_price + tp_dist
            sl_price = entry_price - sl_dist
        else:
            tp_price = entry_price - tp_dist
            sl_price = entry_price + sl_dist

        trade = {
            "type": "BUY" if buy_signal else "SELL",
            "entry": round(entry_price, 5),
            "tp": round(tp_price, 5),
            "sl": round(sl_price, 5),
            "lot_size": lot_size,
            "entry_bar": i,
            "entry_time": bar_time,
            "exit_price": None,
            "exit_bar": None,
            "exit_time": None,
            "pnl": 0,
            "exit_reason": "",
            "trailing_active": trail_config is not None and be_config is None,
            "be_moved": False,
            "rr": round(rr, 2),
        }

        open_trades.append(trade)
        daily_count[day_key] = daily_count.get(day_key, 0) + 1

    # Close remaining open trades at last price
    last_bar_dt = _parse_bar_time(times[-1])
    for trade in open_trades:
        is_buy = trade["type"] == "BUY"
        pnl_raw = (c[-1] - trade["entry"]) if is_buy else (trade["entry"] - c[-1])
        pnl = pnl_raw * trade["lot_size"] * (100000 if pip < 0.01 else 100 if pip < 1 else 1)
        trade["exit_price"] = round(c[-1], 5)
        trade["exit_bar"] = n - 1
        trade["exit_time"] = str(times[-1])
        trade["pnl"] = round(pnl, 2)
        trade["exit_reason"] = "CLOSE"
        trades.append(trade)
        balance += pnl
        equity_curve.append(balance)
        _record_trade_stats(trade, last_bar_dt, hourly_pnl, daily_pnl, monthly_data)

    # Calculate statistics
    stats = _calc_stats(trades, equity_curve, initial_balance)

    # Enhanced reporting
    enhanced = _build_enhanced_report(trades, equity_curve, initial_balance, hourly_pnl, daily_pnl, monthly_data)

    # Downsample equity curve for UI
    step = max(1, len(equity_curve) // 200)
    eq_sampled = equity_curve[::step]

    return {
        "success": True,
        "trades": trades[:500],  # Limit for UI
        "total_trades": len(trades),
        "stats": stats,
        "equity_curve": [round(e, 2) for e in eq_sampled],
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "bars_tested": n,
        # Enhanced report fields
        "monthly_returns": enhanced["monthly_returns"],
        "trade_distribution_hour": enhanced["trade_distribution_hour"],
        "trade_distribution_day": enhanced["trade_distribution_day"],
        "profit_factor_by_month": enhanced["profit_factor_by_month"],
        "drawdown_curve": enhanced["drawdown_curve"],
    }


def _record_trade_stats(trade, bar_dt, hourly_pnl, daily_pnl, monthly_data):
    """Record trade PnL into hourly/daily/monthly accumulators."""
    pnl = trade.get("pnl", 0)
    is_win = pnl > 0

    # Try to get entry time for hour/day
    entry_time_str = trade.get("entry_time", "")
    entry_dt = None
    try:
        if entry_time_str:
            entry_dt = _parse_bar_time(entry_time_str) if not isinstance(entry_time_str, datetime) else entry_time_str
    except Exception:
        pass

    if entry_dt is None:
        entry_dt = bar_dt

    if entry_dt:
        h = entry_dt.hour
        hourly_pnl[h]["pnl"] += pnl
        hourly_pnl[h]["count"] += 1
        if is_win:
            hourly_pnl[h]["wins"] += 1

        wd = entry_dt.isoweekday()  # 1=Mon..7=Sun
        daily_pnl[wd]["pnl"] += pnl
        daily_pnl[wd]["count"] += 1
        if is_win:
            daily_pnl[wd]["wins"] += 1

        month_key = entry_dt.strftime("%Y-%m")
        monthly_data[month_key]["pnl"] += pnl
        monthly_data[month_key]["count"] += 1
        if is_win:
            monthly_data[month_key]["wins"] += 1


def _build_enhanced_report(trades, equity_curve, initial_balance, hourly_pnl, daily_pnl, monthly_data):
    """Build enhanced backtest report with additional analytics."""
    # Monthly returns
    monthly_returns = []
    for month, data in sorted(monthly_data.items()):
        win_rate = round(data["wins"] / data["count"] * 100, 1) if data["count"] > 0 else 0
        monthly_returns.append({
            "month": month,
            "pnl": round(data["pnl"], 2),
            "trades": data["count"],
            "win_rate": win_rate,
        })

    # Profit factor by month
    pf_by_month = {}
    for month, data in sorted(monthly_data.items()):
        month_trades = [t for t in trades if t.get("entry_time", "").startswith(month)]
        wins_sum = sum(t["pnl"] for t in month_trades if t["pnl"] > 0)
        losses_sum = abs(sum(t["pnl"] for t in month_trades if t["pnl"] < 0))
        pf_by_month[month] = round(wins_sum / losses_sum, 2) if losses_sum > 0 else (999 if wins_sum > 0 else 0)

    # Trade distribution by hour
    trade_dist_hour = []
    for h in range(24):
        d = hourly_pnl.get(h, {"pnl": 0, "count": 0, "wins": 0})
        wr = round(d["wins"] / d["count"] * 100, 1) if d["count"] > 0 else 0
        trade_dist_hour.append({
            "hour": h,
            "count": d["count"],
            "pnl": round(d["pnl"], 2),
            "win_rate": wr,
        })

    # Trade distribution by day
    day_names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    trade_dist_day = []
    for wd in range(1, 8):
        d = daily_pnl.get(wd, {"pnl": 0, "count": 0, "wins": 0})
        wr = round(d["wins"] / d["count"] * 100, 1) if d["count"] > 0 else 0
        trade_dist_day.append({
            "day": day_names.get(wd, str(wd)),
            "day_num": wd,
            "count": d["count"],
            "pnl": round(d["pnl"], 2),
            "win_rate": wr,
        })

    # Drawdown curve
    drawdown_curve = []
    peak = initial_balance
    step = max(1, len(equity_curve) // 200)
    for idx in range(0, len(equity_curve), step):
        eq = equity_curve[idx]
        peak = max(peak, eq)
        dd_pct = round((peak - eq) / peak * 100, 2) if peak > 0 else 0
        drawdown_curve.append({"bar": idx, "drawdown": dd_pct})

    return {
        "monthly_returns": monthly_returns,
        "trade_distribution_hour": trade_dist_hour,
        "trade_distribution_day": trade_dist_day,
        "profit_factor_by_month": pf_by_month,
        "drawdown_curve": drawdown_curve,
    }


def _calc_stats(trades, equity, initial):
    if not trades:
        return {
            "total": 0, "wins": 0, "losses": 0, "win_rate": 0,
            "profit_factor": 0, "avg_win": 0, "avg_loss": 0,
            "max_drawdown_pct": 0, "max_drawdown_abs": 0,
            "expected_payoff": 0, "sharpe": 0,
            "max_consec_wins": 0, "max_consec_losses": 0,
            "avg_rr": 0, "best_trade": 0, "worst_trade": 0,
            "avg_bars_held": 0, "total_pnl": 0,
        }

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total_pnl = sum(pnls)

    # Win rate
    win_rate = len(wins) / len(trades) * 100 if trades else 0

    # Profit factor
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    # Drawdown
    peak = initial
    max_dd_abs = 0
    max_dd_pct = 0
    for eq in equity:
        peak = max(peak, eq)
        dd = peak - eq
        dd_pct = dd / peak * 100 if peak > 0 else 0
        max_dd_abs = max(max_dd_abs, dd)
        max_dd_pct = max(max_dd_pct, dd_pct)

    # Consecutive
    max_cw = 0
    max_cl = 0
    cw = 0
    cl = 0
    for p in pnls:
        if p > 0:
            cw += 1
            cl = 0
        else:
            cl += 1
            cw = 0
        max_cw = max(max_cw, cw)
        max_cl = max(max_cl, cl)

    # Sharpe (simplified)
    if len(pnls) > 1:
        avg_ret = np.mean(pnls)
        std_ret = np.std(pnls)
        sharpe = (avg_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0
    else:
        sharpe = 0

    # Avg bars held
    bars_held = [(t.get("exit_bar", 0) - t.get("entry_bar", 0)) for t in trades]
    avg_bars = np.mean(bars_held) if bars_held else 0

    return {
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(pf, 2),
        "avg_win": round(np.mean(wins), 2) if wins else 0,
        "avg_loss": round(np.mean(losses), 2) if losses else 0,
        "max_drawdown_pct": round(max_dd_pct, 1),
        "max_drawdown_abs": round(max_dd_abs, 2),
        "expected_payoff": round(total_pnl / len(trades), 2) if trades else 0,
        "sharpe": round(sharpe, 2),
        "max_consec_wins": max_cw,
        "max_consec_losses": max_cl,
        "avg_rr": round(np.mean([t.get("rr", 0) for t in trades]), 2),
        "best_trade": round(max(pnls), 2) if pnls else 0,
        "worst_trade": round(min(pnls), 2) if pnls else 0,
        "avg_bars_held": round(avg_bars, 1),
        "total_pnl": round(total_pnl, 2),
    }
