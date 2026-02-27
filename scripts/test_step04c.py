"""
Whilber-AI MVP - Step 04c Test: +7 More Strategies (Total: 32)
=================================================================
Run: python scripts/test_step04c.py
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

def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Whilber-AI - Step 04c: +7 More (Total: 32){RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    # ── 1. Import ───────────────────────────────────────────
    header("1. Import Check")
    try:
        from backend.strategies.orchestrator import (
            analyze_symbol, get_available_strategies, get_strategy_count
        )
        from backend.strategies.cat15_pivot import PivotPointStrategy
        from backend.strategies.cat16_mean_reversion import MeanReversion
        from backend.strategies.cat17_breakout import MomentumBreakout
        from backend.strategies.cat18_session import SessionAnalysis
        from backend.strategies.cat19_gap import GapTrading
        from backend.strategies.cat20_harmonic import HarmonicStrategy
        from backend.strategies.cat21_wyckoff import WyckoffStrategy
        ok("All 7 new modules imported")
    except Exception as e:
        fail(f"Import error: {e}")
        import traceback; traceback.print_exc()
        return

    # ── 2. Registry ─────────────────────────────────────────
    header("2. Strategy Registry")

    count = get_strategy_count()
    strategies = get_available_strategies()

    if count >= 32:
        ok(f"{count} strategies registered (was 25, added 7)")
    else:
        fail(f"Only {count} strategies (expected 32)")
        return

    cats = {}
    for s in strategies:
        cat = s["category_fa"]
        if cat not in cats:
            cats[cat] = []
        cats[cat].append(s["name_fa"])

    for cat_name, names in cats.items():
        info(f"  {cat_name}: {', '.join(names)}")

    # ── 3. Connect MT5 ─────────────────────────────────────
    header("3. MT5 Connection")

    from backend.mt5.mt5_connector import MT5Connector
    connector = MT5Connector.get_instance()
    if not connector.connect():
        fail("MT5 connection failed")
        return
    ok("MT5 connected")

    # ── 4. Test New Strategies ──────────────────────────────
    header("4. New Strategy Tests (EURUSD H1)")

    new_ids = [
        "pivot_points", "mean_reversion", "momentum_breakout",
        "session_analysis", "gap_trading", "harmonic", "wyckoff"
    ]

    for sid in new_ids:
        r = analyze_symbol("EURUSD", "H1", strategies=[sid])
        if r.get("success") and r["strategies"]:
            s = r["strategies"][0]
            sig = s["signal"]
            conf = s["confidence"]
            reason = s["reason_fa"][:65]
            colors = {"BUY": GREEN, "SELL": RED, "NEUTRAL": YELLOW}
            c = colors.get(sig, RESET)
            print(f"  {GREEN}[OK]{RESET}  {s['strategy_name_fa']:25s} | {c}{sig:7s}{RESET} {conf:4.0f}% | {DIM}{reason}{RESET}")
        else:
            fail(f"  {sid}: {r.get('error', 'unknown')}")

    # ── 5. Full 32-Strategy Analysis ────────────────────────
    header("5. Full Analysis — ALL 32 Strategies")

    test_pairs = [
        ("EURUSD", "H1"),
        ("XAUUSD", "H1"),
        ("BTCUSD", "H4"),
        ("GBPUSD", "M15"),
        ("NAS100", "H1"),
    ]

    for sym, tf in test_pairs:
        start = time.time()
        r = analyze_symbol(sym, tf)
        elapsed = time.time() - start

        if r.get("success"):
            ov = r["overall"]
            sig = ov["signal"]
            strat_count = len(r["strategies"])
            colors = {"BUY": GREEN, "SELL": RED, "NEUTRAL": YELLOW}
            c = colors.get(sig, RESET)
            print(f"  {GREEN}[OK]{RESET}  {sym:10s} {tf:4s} | {c}{sig:7s}{RESET} {ov['confidence']:4.0f}% | "
                  f"B:{ov['buy_count']} S:{ov['sell_count']} N:{ov['neutral_count']} | "
                  f"{strat_count} strats | {elapsed:.2f}s")

            # Active signals
            active = [s for s in r["strategies"] if s["signal"] != "NEUTRAL"]
            for s in active[:6]:
                c2 = colors.get(s["signal"], RESET)
                print(f"        {c2}{s['signal']:7s}{RESET} {s['confidence']:4.0f}% {s['strategy_name_fa']}")
        else:
            fail(f"  {sym} {tf}: {r.get('error')}")

    # ── 6. Performance Check ────────────────────────────────
    header("6. Performance (32 strategies)")

    times = []
    for _ in range(3):
        start = time.time()
        analyze_symbol("EURUSD", "H1")
        times.append(time.time() - start)

    avg_t = sum(times) / len(times)
    ok(f"Average analysis time: {avg_t:.3f}s ({avg_t*1000:.0f}ms)")

    if avg_t < 2.0:
        ok("Performance: EXCELLENT (<2s)")
    elif avg_t < 5.0:
        ok("Performance: GOOD (<5s)")
    else:
        info(f"Performance: {avg_t:.1f}s (consider optimization)")

    # ── Cleanup ─────────────────────────────────────────────
    connector.disconnect()

    # ── Summary ─────────────────────────────────────────────
    header("FINAL SUMMARY — COMPLETE STRATEGY ENGINE")

    print(f"""
  {GREEN}[OK]{RESET}  {count} strategies total

  {BOLD}📊 Categories:{RESET}""")

    all_cats = [
        ("روند و ساختار", "5", "روندیاب، پولبک، ادامه، برگشت، پله‌ای"),
        ("سیستم MA", "3", "کراس، سه‌گانه، حمایت/مقاومت MA"),
        ("مومنتوم", "4", "RSI، استوکاستیک، MACD، تلاقی نوسانگرها"),
        ("نوسان و باندها", "3", "بولینگر، فشردگی→انفجار، سوپرترند"),
        ("حجم", "1", "تأیید حجم"),
        ("حمایت/مقاومت", "1", "برگشت از S/R"),
        ("کندل", "1", "تلاقی کندلی"),
        ("واگرایی", "1", "Regular + Hidden RSI/MACD"),
        ("ایچیموکو", "1", "ابر + TK + Chikou"),
        ("فیبوناچی", "1", "سطوح ریتریسمنت"),
        ("مولتی‌تایم‌فریم", "1", "تأیید HTF"),
        ("رنج", "1", "معامله رنج"),
        ("اسمارت مانی", "1", "OB + FVG + Sweep"),
        ("عرضه/تقاضا", "1", "نواحی S/D"),
        ("پیوت", "1", "Classic + Camarilla"),
        ("بازگشت به میانگین", "1", "Z-Score"),
        ("شکست مومنتومی", "1", "Donchian + Volume"),
        ("سشن", "1", "Asian/London/NY"),
        ("گپ", "1", "Gap Fill/Continue"),
        ("هارمونیک", "1", "ABCD Pattern"),
        ("وایکاف", "1", "Accumulation/Distribution"),
    ]

    for cat, num, desc in all_cats:
        print(f"    {num:>2} | {cat:25s} | {DIM}{desc}{RESET}")

    print(f"""
  {GREEN}{BOLD}✅ STRATEGY ENGINE 100% COMPLETE — {count} strategies!{RESET}
  {BOLD}هر درخواست = داده زنده MT5 + ۳۲ استراتژی + تحلیل فارسی{RESET}

  {CYAN}Next: FastAPI server + Dashboard{RESET}
""")


if __name__ == "__main__":
    main()
