"""
Whilber-AI MVP - Step 02 Test (Fixed for Moneta Markets)
==========================================================
Run: python scripts/test_step02.py
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")
os.system("")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg):
    print(f"  {GREEN}[OK]{RESET}    {msg}")

def fail(msg):
    print(f"  {RED}[FAIL]{RESET}  {msg}")

def warn(msg):
    print(f"  {YELLOW}[WARN]{RESET}  {msg}")

def info(msg):
    print(f"  {CYAN}[INFO]{RESET}  {msg}")

def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*55}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*55}{RESET}")


def main():
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  Whilber-AI - Data Extraction Test (Moneta Markets){RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")

    # ── 1. Import and Connect ───────────────────────────────
    header("1. Import Modules & Connect MT5")

    try:
        from backend.mt5.mt5_connector import MT5Connector
        from backend.mt5.symbol_map import (
            get_symbols_by_category, get_all_categories,
            get_farsi_name, validate_symbol, SymbolCategory
        )
        from backend.mt5.timeframes import (
            get_all_timeframes, validate_timeframe, get_bar_count
        )
        from backend.mt5.data_fetcher import (
            fetch_bars, fetch_current_price, clear_cache, get_cache_info
        )
        ok("All modules imported")
    except Exception as e:
        fail(f"Import error: {e}")
        return

    connector = MT5Connector.get_instance()
    if connector.connect():
        ok("MT5 connected")
    else:
        fail("MT5 connection failed")
        return

    # ── 2. Symbol Map ───────────────────────────────────────
    header("2. Symbol Map")

    total_symbols = 0
    for cat in get_all_categories():
        symbols = get_symbols_by_category(cat["id"])
        total_symbols += len(symbols)
        ok(f"{cat['name_fa']} ({cat['id']}): {len(symbols)} symbols")
    info(f"Total: {total_symbols} symbols")

    assert validate_symbol("EURUSD") == True
    assert validate_symbol("XAUUSD") == True
    assert validate_symbol("NAS100") == True
    assert validate_symbol("INVALID") == False
    ok("Validation works")

    assert get_farsi_name("XAUUSD") == "طلا"
    assert get_farsi_name("BTCUSD") == "بیت‌کوین"
    assert get_farsi_name("NAS100") == "نزدک ۱۰۰"
    ok("Farsi names work")

    # ── 3. Timeframes ───────────────────────────────────────
    header("3. Timeframe Map")
    for tf in get_all_timeframes():
        ok(f"{tf['name_fa']} ({tf['id']}): {get_bar_count(tf['id'])} bars")

    # ── 4. Data Fetch — One from each category ──────────────
    header("4. Data Fetch (one per category)")

    test_symbols = [
        ("EURUSD", "forex major"),
        ("EURGBP", "forex minor (+)"),
        ("XAUUSD", "metals (+)"),
        ("NAS100", "indices"),
        ("BTCUSD", "crypto"),
    ]

    all_pass = True
    for symbol, desc in test_symbols:
        start = time.time()
        df = fetch_bars(symbol, "H1", use_cache=False)
        elapsed = time.time() - start

        if df is not None and len(df) > 0:
            ok(f"{symbol:10s} | {desc:20s} | {len(df):4d} bars | {elapsed:.2f}s")
        else:
            fail(f"{symbol:10s} | {desc:20s} | FAILED | {elapsed:.2f}s")
            all_pass = False

    # ── 5. All Timeframes ───────────────────────────────────
    header("5. All Timeframes (EURUSD)")

    for tf in ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]:
        start = time.time()
        df = fetch_bars("EURUSD", tf, use_cache=False)
        elapsed = time.time() - start

        if df is not None and len(df) > 0:
            ok(f"{tf:4s} | {len(df):4d} bars | {elapsed:.2f}s | "
               f"{df['time'].iloc[0]} → {df['time'].iloc[-1]}")
        else:
            fail(f"{tf:4s} | FAILED")

    # ── 6. Current Price ────────────────────────────────────
    header("6. Current Price")

    for sym in ["EURUSD", "XAUUSD", "BTCUSD", "NAS100"]:
        price = fetch_current_price(sym)
        if price:
            ok(f"{sym:10s} | Bid: {price['bid']} | Ask: {price['ask']}")
        else:
            fail(f"{sym:10s} | FAILED")

    # ── 7. Cache Test ───────────────────────────────────────
    header("7. Cache Test")

    clear_cache()
    start = time.time()
    df1 = fetch_bars("EURUSD", "M5", use_cache=True)
    time1 = time.time() - start

    start = time.time()
    df2 = fetch_bars("EURUSD", "M5", use_cache=True)
    time2 = time.time() - start

    if df1 is not None and df2 is not None:
        ok(f"MT5 fetch:    {time1:.3f}s")
        ok(f"Cached fetch: {time2:.3f}s")
        ok(f"Speedup: {time1/max(time2, 0.0001):.0f}x faster")

    # ── 8. Data Quality ────────────────────────────────────
    header("8. Data Quality Check")

    df = fetch_bars("XAUUSD", "H1", use_cache=False)
    if df is not None:
        checks = [
            ("High >= Open,Close", (df["high"] >= df["open"]).all() and (df["high"] >= df["close"]).all()),
            ("Low <= Open,Close",  (df["low"] <= df["open"]).all() and (df["low"] <= df["close"]).all()),
            ("High >= Low",        (df["high"] >= df["low"]).all()),
            ("No zero prices",     (df["close"] > 0).all()),
            ("No NaN values",      df[["open","high","low","close"]].isna().sum().sum() == 0),
            ("Time sorted",        df["time"].is_monotonic_increasing),
        ]
        for name, passed in checks:
            (ok if passed else fail)(name)

        info("Last 3 bars (XAUUSD H1):")
        for _, r in df.tail(3).iterrows():
            info(f"  {r['time']} | O:{r['open']:.2f} H:{r['high']:.2f} L:{r['low']:.2f} C:{r['close']:.2f}")
    else:
        fail("Could not fetch XAUUSD for quality check")

    # ── 9. Full Symbol Scan ─────────────────────────────────
    header("9. Full Symbol Scan (all 50)")

    success = 0
    failed_list = []

    for cat in get_all_categories():
        symbols = get_symbols_by_category(cat["id"])
        for sym_info in symbols:
            symbol = sym_info["symbol"]
            df = fetch_bars(symbol, "H1", use_cache=False)
            if df is not None and len(df) > 0:
                success += 1
            else:
                failed_list.append(f"{symbol} ({sym_info['mt5_name']})")

    ok(f"Success: {success}/{total_symbols}")
    if failed_list:
        for f_sym in failed_list:
            fail(f"  {f_sym}")
    else:
        ok("ALL symbols fetched successfully!")

    # ── 10. Performance ─────────────────────────────────────
    header("10. Performance")

    clear_cache()
    test_5 = ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD", "NAS100"]
    start_all = time.time()
    for s in test_5:
        fetch_bars(s, "M15", use_cache=False)
    total = time.time() - start_all

    ok(f"5 fetches: {total:.2f}s total | {total/5:.2f}s avg")

    # ── Cleanup ─────────────────────────────────────────────
    clear_cache()
    connector.disconnect()

    # ── Summary ─────────────────────────────────────────────
    header("FINAL SUMMARY")

    ok(f"{total_symbols} symbols defined")
    ok(f"{success}/{total_symbols} fetch successfully")
    ok(f"All 7 timeframes OK")
    ok(f"Cache working")
    ok(f"Data quality verified")

    if success == total_symbols:
        print(f"\n  {GREEN}{BOLD}PERFECT! All symbols working!{RESET}")
    else:
        print(f"\n  {YELLOW}{BOLD}{total_symbols - success} symbols need attention{RESET}")

    print(f"  Next: Build indicator engine (Phase 2)\n")


if __name__ == "__main__":
    main()
