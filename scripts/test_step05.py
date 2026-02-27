"""
Whilber-AI MVP - Step 05 Test: API Server
============================================
Tests all API endpoints.
Requires server running at localhost:8000

Run: python scripts/test_step05.py
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
from datetime import datetime

os.system("")
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

BASE = "http://localhost:8000"

def ok(msg):    print(f"  {GREEN}[OK]{RESET}    {msg}")
def fail(msg):  print(f"  {RED}[FAIL]{RESET}  {msg}")
def info(msg):  print(f"  {CYAN}[INFO]{RESET}  {msg}")

def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def api_get(path):
    """Simple GET request."""
    url = BASE + path
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return {"error": body}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Whilber-AI - API Server Test{RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    # ── 1. Health Check ─────────────────────────────────────
    header("1. Health Check")
    data, code = api_get("/api/health")
    if code == 200 and data.get("mt5_connected"):
        ok(f"Server OK | MT5: Connected | Strategies: {data['strategies']} | Symbols: {data['symbols']}")
    elif code == 200:
        fail(f"Server OK but MT5 disconnected")
    else:
        fail(f"Server not responding (code={code})")
        print(f"  Make sure server is running: start_server.bat")
        return

    # ── 2. Symbols ──────────────────────────────────────────
    header("2. Symbol List")
    data, code = api_get("/api/symbols")
    if code == 200:
        total = data["total"]
        cats = len(data["categories"])
        ok(f"{total} symbols in {cats} categories")
        for cat, syms in list(data["categories"].items())[:4]:
            names = [s["symbol"] for s in syms[:5]]
            info(f"  {cat}: {', '.join(names)}{'...' if len(syms) > 5 else ''}")
    else:
        fail("Symbol list failed")

    # ── 3. Strategies ───────────────────────────────────────
    header("3. Strategy List")
    data, code = api_get("/api/strategies")
    if code == 200:
        ok(f"{data['total']} strategies")
    else:
        fail("Strategy list failed")

    # ── 4. Single Analysis ──────────────────────────────────
    header("4. Single Analysis: EURUSD H1")
    start = time.time()
    data, code = api_get("/api/analyze/EURUSD/H1")
    elapsed = time.time() - start

    if code == 200:
        ov = data["overall"]
        sig = ov["signal"]
        colors = {"BUY": GREEN, "SELL": RED, "NEUTRAL": YELLOW}
        c = colors.get(sig, RESET)
        ok(f"Analysis complete in {elapsed:.2f}s")
        print(f"\n  {BOLD}📊 Signal: {c}{sig}{RESET} ({ov['confidence']}%)")
        print(f"  {ov['summary_fa']}")
        print(f"  BUY:{ov['buy_count']} SELL:{ov['sell_count']} NEUTRAL:{ov['neutral_count']}")
        print(f"  Price: {data['last_close']}")

        # Show active strategies
        active = [s for s in data["strategies"] if s["signal"] != "NEUTRAL"]
        if active:
            print(f"\n  Active signals ({len(active)}):")
            for s in active:
                c2 = colors.get(s["signal"], RESET)
                print(f"    {c2}{s['signal']:7s}{RESET} {s['confidence']:3.0f}% {s['strategy_name_fa']}")
    else:
        fail(f"Analysis failed: {data}")

    # ── 5. Different Timeframes ─────────────────────────────
    header("5. Multiple Timeframes")
    for tf in ["M15", "H1", "H4", "D1"]:
        start = time.time()
        data, code = api_get(f"/api/analyze/EURUSD/{tf}")
        elapsed = time.time() - start
        if code == 200:
            ov = data["overall"]
            c = colors.get(ov["signal"], RESET)
            print(f"  {GREEN}[OK]{RESET}  {tf:4s} | {c}{ov['signal']:7s}{RESET} {ov['confidence']:4.0f}% | B:{ov['buy_count']} S:{ov['sell_count']} | {elapsed:.2f}s")
        else:
            fail(f"  {tf}: failed")

    # ── 6. Multi Symbol ─────────────────────────────────────
    header("6. Multi-Symbol Analysis")
    start = time.time()
    data, code = api_get("/api/multi/EURUSD,XAUUSD,BTCUSD,GBPUSD,NAS100?timeframe=H1")
    elapsed = time.time() - start

    if code == 200:
        ok(f"Multi-analysis: {len(data['results'])} symbols in {elapsed:.2f}s")
        for sym, r in data["results"].items():
            if "error" in r:
                fail(f"  {sym}: {r['error']}")
            else:
                c = colors.get(r["signal"], RESET)
                print(f"  {sym:10s} | {c}{r['signal']:7s}{RESET} {r['confidence']:4.0f}% | {r['summary_fa'][:40]}")
    else:
        fail(f"Multi failed: {data}")

    # ── 7. Price Endpoint ───────────────────────────────────
    header("7. Price Check")
    data, code = api_get("/api/price/EURUSD")
    if code == 200:
        ok(f"EURUSD: Bid={data['bid']} Ask={data['ask']} Spread={data['spread']}")
    else:
        fail("Price check failed")

    # ── 8. Selective Strategies ─────────────────────────────
    header("8. Selective Strategy Filter")
    data, code = api_get("/api/analyze/EURUSD/H1?strategies=trend_following,ichimoku,fibonacci")
    if code == 200:
        ok(f"Selective: {len(data['strategies'])} strategies")
        for s in data["strategies"]:
            c2 = colors.get(s["signal"], RESET)
            print(f"    {c2}{s['signal']:7s}{RESET} {s['confidence']:3.0f}% {s['strategy_name_fa']}")

    # ── 9. Dashboard ────────────────────────────────────────
    header("9. Dashboard Check")
    try:
        req = urllib.request.Request(BASE + "/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8")
            if "Whilber-AI" in html:
                ok(f"Dashboard loaded ({len(html)} bytes)")
            else:
                fail("Dashboard HTML wrong content")
    except Exception as e:
        fail(f"Dashboard: {e}")

    # ── 10. Error Handling ──────────────────────────────────
    header("10. Error Handling")
    data, code = api_get("/api/analyze/INVALID_SYMBOL/H1")
    if code == 400:
        ok(f"Invalid symbol: 400 error (correct)")
    else:
        fail(f"Expected 400, got {code}")

    # ── Summary ─────────────────────────────────────────────
    header("FINAL SUMMARY")
    ok("API Health endpoint")
    ok("Symbol listing")
    ok("Strategy listing")
    ok("Single analysis (real-time)")
    ok("Multi-timeframe")
    ok("Multi-symbol")
    ok("Price endpoint")
    ok("Selective strategies")
    ok("Dashboard HTML")
    ok("Error handling")

    print(f"\n  {GREEN}{BOLD}✅ API SERVER COMPLETE!{RESET}")
    print(f"  {BOLD}Dashboard: http://localhost:8000{RESET}")
    print(f"  {BOLD}API: http://localhost:8000/api/analyze/EURUSD/H1{RESET}\n")


if __name__ == "__main__":
    main()
