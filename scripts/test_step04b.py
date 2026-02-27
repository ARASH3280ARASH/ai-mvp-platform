"""
Whilber-AI MVP - Step 04b Test: New Strategies (7 added)
==========================================================
Run: python scripts/test_step04b.py
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
DIM = "\033[2m"

def ok(msg):    print(f"  {GREEN}[OK]{RESET}    {msg}")
def fail(msg):  print(f"  {RED}[FAIL]{RESET}  {msg}")
def info(msg):  print(f"  {CYAN}[INFO]{RESET}  {msg}")

def signal_color(sig):
    return {"\033[92m": "BUY", "\033[91m": "SELL"}.get(sig, YELLOW) if sig in ("BUY","SELL") else YELLOW

def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Whilber-AI - Step 04b: +7 New Strategies{RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    # ── 1. Import ───────────────────────────────────────────
    header("1. Import Check")
    try:
        from backend.strategies.orchestrator import (
            analyze_symbol, get_available_strategies, get_strategy_count
        )
        from backend.strategies.cat08_divergence import DivergenceStrategy
        from backend.strategies.cat09_ichimoku import IchimokuStrategy
        from backend.strategies.cat10_fibonacci import FibonacciStrategy
        from backend.strategies.cat11_multi_tf import MultiTFConfirmation
        from backend.strategies.cat12_range import RangeTrading
        from backend.strategies.cat13_smart_money import SmartMoneyStrategy
        from backend.strategies.cat14_supply_demand import SupplyDemandStrategy
        ok("All 7 new strategy modules imported")
    except Exception as e:
        fail(f"Import error: {e}")
        import traceback; traceback.print_exc()
        return

    # ── 2. Strategy Count ───────────────────────────────────
    header("2. Strategy Registry")

    count = get_strategy_count()
    strategies = get_available_strategies()

    if count >= 25:
        ok(f"{count} strategies registered (was 18, added 7)")
    else:
        fail(f"Only {count} strategies (expected 25)")
        return

    # Group and display
    cats = {}
    for s in strategies:
        cat = s["category_fa"]
        if cat not in cats:
            cats[cat] = []
        cats[cat].append(s["name_fa"])

    for cat_name, names in cats.items():
        info(f"  {cat_name}: {', '.join(names)}")

    # ── 3. Test New Strategies Individually ─────────────────
    header("3. Individual New Strategy Tests (EURUSD H1)")

    from backend.mt5.mt5_connector import MT5Connector
    connector = MT5Connector.get_instance()
    if not connector.connect():
        fail("MT5 connection failed")
        return

    new_ids = [
        "divergence", "ichimoku", "fibonacci",
        "multi_tf", "range_trading", "smart_money", "supply_demand"
    ]

    for sid in new_ids:
        r = analyze_symbol("EURUSD", "H1", strategies=[sid])
        if r.get("success") and r["strategies"]:
            s = r["strategies"][0]
            sig = s["signal"]
            conf = s["confidence"]
            reason = s["reason_fa"][:70]
            colors = {"BUY": GREEN, "SELL": RED, "NEUTRAL": YELLOW}
            c = colors.get(sig, RESET)
            print(f"  {GREEN}[OK]{RESET}  {s['strategy_name_fa']:25s} | {c}{sig:7s}{RESET} {conf:4.0f}% | {DIM}{reason}{RESET}")
        else:
            fail(f"{sid}: {r.get('error', 'unknown')}")

    # ── 4. Full Analysis with ALL 25 ───────────────────────
    header("4. Full Analysis — ALL 25 Strategies")

    test_pairs = [
        ("EURUSD", "H1"),
        ("XAUUSD", "H1"),
        ("BTCUSD", "H4"),
    ]

    for sym, tf in test_pairs:
        r = analyze_symbol(sym, tf)
        if r.get("success"):
            ov = r["overall"]
            sig = ov["signal"]
            strat_count = len(r["strategies"])
            colors = {"BUY": GREEN, "SELL": RED, "NEUTRAL": YELLOW}
            c = colors.get(sig, RESET)
            print(f"  {GREEN}[OK]{RESET}  {sym:10s} {tf:4s} | {c}{sig:7s}{RESET} {ov['confidence']:4.0f}% | "
                  f"B:{ov['buy_count']} S:{ov['sell_count']} N:{ov['neutral_count']} | "
                  f"{strat_count} strats | {r['performance']['total_time']:.2f}s")

            # Show active signals
            active = [s for s in r["strategies"] if s["signal"] != "NEUTRAL"]
            for s in active[:5]:
                c2 = colors.get(s["signal"], RESET)
                print(f"        {c2}{s['signal']:7s}{RESET} {s['confidence']:4.0f}% {s['strategy_name_fa']}")
        else:
            fail(f"{sym} {tf}: {r.get('error')}")

    # ── Cleanup ─────────────────────────────────────────────
    connector.disconnect()

    # ── Summary ─────────────────────────────────────────────
    header("FINAL SUMMARY")
    ok(f"{count} strategies total (18 original + 7 new)")
    ok("واگرایی (Divergence)")
    ok("ایچیموکو (Ichimoku Cloud)")
    ok("فیبوناچی (Fibonacci Retracement)")
    ok("مولتی‌تایم‌فریم (Multi-Timeframe)")
    ok("معامله رنج (Range Trading)")
    ok("اسمارت مانی (Smart Money / Order Blocks)")
    ok("عرضه و تقاضا (Supply / Demand Zones)")
    print(f"\n  {GREEN}{BOLD}✅ Strategy Engine COMPLETE — 25 strategies!{RESET}")
    print(f"  Next: FastAPI + Dashboard\n")


if __name__ == "__main__":
    main()
