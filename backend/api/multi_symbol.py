"""
Whilber-AI — Multi-Symbol Tester
====================================
Test one strategy across multiple symbols/timeframes.
"""

from backend.api.backtest_engine import run_backtest


COMMON_SYMBOLS = [
    # --- Forex Major ---
    {"symbol": "EURUSD", "name_fa": "یورو/دلار", "group": "forex_major"},
    {"symbol": "GBPUSD", "name_fa": "پوند/دلار", "group": "forex_major"},
    {"symbol": "USDJPY", "name_fa": "دلار/ین", "group": "forex_major"},
    {"symbol": "USDCHF", "name_fa": "دلار/فرانک", "group": "forex_major"},
    {"symbol": "AUDUSD", "name_fa": "دلار استرالیا", "group": "forex_major"},
    {"symbol": "NZDUSD", "name_fa": "دلار نیوزلند", "group": "forex_major"},
    {"symbol": "USDCAD", "name_fa": "دلار/کانادا", "group": "forex_major"},
    # --- Forex Minor ---
    {"symbol": "EURGBP", "name_fa": "یورو/پوند", "group": "forex_minor"},
    {"symbol": "EURJPY", "name_fa": "یورو/ین", "group": "forex_minor"},
    {"symbol": "GBPJPY", "name_fa": "پوند/ین", "group": "forex_minor"},
    {"symbol": "EURAUD", "name_fa": "یورو/دلار استرالیا", "group": "forex_minor"},
    {"symbol": "EURCAD", "name_fa": "یورو/دلار کانادا", "group": "forex_minor"},
    {"symbol": "EURCHF", "name_fa": "یورو/فرانک", "group": "forex_minor"},
    {"symbol": "EURNZD", "name_fa": "یورو/دلار نیوزلند", "group": "forex_minor"},
    {"symbol": "GBPAUD", "name_fa": "پوند/دلار استرالیا", "group": "forex_minor"},
    {"symbol": "GBPCAD", "name_fa": "پوند/دلار کانادا", "group": "forex_minor"},
    {"symbol": "GBPCHF", "name_fa": "پوند/فرانک", "group": "forex_minor"},
    {"symbol": "GBPNZD", "name_fa": "پوند/دلار نیوزلند", "group": "forex_minor"},
    {"symbol": "AUDJPY", "name_fa": "دلار استرالیا/ین", "group": "forex_minor"},
    {"symbol": "AUDNZD", "name_fa": "دلار استرالیا/نیوزلند", "group": "forex_minor"},
    {"symbol": "AUDCAD", "name_fa": "دلار استرالیا/کانادا", "group": "forex_minor"},
    {"symbol": "AUDCHF", "name_fa": "دلار استرالیا/فرانک", "group": "forex_minor"},
    {"symbol": "NZDJPY", "name_fa": "دلار نیوزلند/ین", "group": "forex_minor"},
    {"symbol": "NZDCAD", "name_fa": "دلار نیوزلند/کانادا", "group": "forex_minor"},
    {"symbol": "NZDCHF", "name_fa": "دلار نیوزلند/فرانک", "group": "forex_minor"},
    {"symbol": "CADJPY", "name_fa": "دلار کانادا/ین", "group": "forex_minor"},
    {"symbol": "CADCHF", "name_fa": "دلار کانادا/فرانک", "group": "forex_minor"},
    {"symbol": "CHFJPY", "name_fa": "فرانک/ین", "group": "forex_minor"},
    # --- Metals ---
    {"symbol": "XAUUSD", "name_fa": "طلا", "group": "metals"},
    {"symbol": "XAGUSD", "name_fa": "نقره", "group": "metals"},
    # --- Indices ---
    {"symbol": "US100", "name_fa": "نزدک", "group": "indices"},
    {"symbol": "US30", "name_fa": "داوجونز", "group": "indices"},
    {"symbol": "US500", "name_fa": "S&P 500", "group": "indices"},
    # --- Crypto ---
    {"symbol": "BTCUSD", "name_fa": "بیت‌کوین", "group": "crypto"},
    {"symbol": "ETHUSD", "name_fa": "اتریوم", "group": "crypto"},
    {"symbol": "SOLUSD", "name_fa": "سولانا", "group": "crypto"},
    {"symbol": "XRPUSD", "name_fa": "ریپل", "group": "crypto"},
    {"symbol": "ADAUSD", "name_fa": "کاردانو", "group": "crypto"},
    {"symbol": "DOGEUSD", "name_fa": "دوج‌کوین", "group": "crypto"},
    {"symbol": "DOTUSD", "name_fa": "پولکادات", "group": "crypto"},
    {"symbol": "LINKUSD", "name_fa": "چین‌لینک", "group": "crypto"},
    {"symbol": "LTCUSD", "name_fa": "لایت‌کوین", "group": "crypto"},
    {"symbol": "BCHUSD", "name_fa": "بیت‌کوین کش", "group": "crypto"},
]


def multi_symbol_test(symbols, strategy, bars=500, balance=10000, spread=2):
    """Test strategy on multiple symbols."""

    results = []
    total_pnl = 0
    total_trades = 0
    total_wins = 0

    for sym_info in symbols:
        symbol = sym_info if isinstance(sym_info, str) else sym_info.get("symbol", "")
        if not symbol:
            continue

        s_copy = dict(strategy)
        s_copy["symbol"] = symbol

        try:
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            import pandas as pd

            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                results.append({"symbol": symbol, "success": False, "error": "MT5 not connected"})
                continue

            tf_map = {
                "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
            }
            tf = tf_map.get(strategy.get("timeframe", "H1").upper(), mt5.TIMEFRAME_H1)

            rates = mt5.copy_rates_from_pos(symbol, tf, 0, min(bars, 1000))
            if rates is None or len(rates) < 50:
                results.append({"symbol": symbol, "success": False, "error": "No data"})
                continue

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            bt = run_backtest(df, s_copy, initial_balance=balance, spread_pips=spread)

            if bt.get("success"):
                st = bt["stats"]
                total_pnl += st["total_pnl"]
                total_trades += st["total"]
                total_wins += st["wins"]

                results.append({
                    "symbol": symbol,
                    "success": True,
                    "total_trades": st["total"],
                    "win_rate": st["win_rate"],
                    "profit_factor": st["profit_factor"],
                    "total_pnl": st["total_pnl"],
                    "max_dd": st["max_drawdown_pct"],
                    "sharpe": st["sharpe"],
                    "final_balance": bt["final_balance"],
                    "avg_rr": st["avg_rr"],
                    "best_trade": st["best_trade"],
                    "worst_trade": st["worst_trade"],
                })
            else:
                results.append({"symbol": symbol, "success": False, "error": bt.get("error", "Backtest failed")})

        except Exception as e:
            results.append({"symbol": symbol, "success": False, "error": str(e)})

    # Sort by PnL
    results.sort(key=lambda x: x.get("total_pnl", -99999), reverse=True)

    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    profitable = sum(1 for r in results if r.get("success") and r.get("total_pnl", 0) > 0)

    return {
        "success": True,
        "results": results,
        "summary": {
            "symbols_tested": len(results),
            "symbols_profitable": profitable,
            "total_trades": total_trades,
            "total_wins": total_wins,
            "overall_win_rate": round(overall_wr, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_symbol": round(total_pnl / max(len(results), 1), 2),
        },
    }


def get_common_symbols():
    return COMMON_SYMBOLS
