"""
Test suite for Whilber-AI Trading Bot Server.
Run: python scripts/test_bot.py
Requires bot server running on port 8001.
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(r"C:\Users\Administrator\Desktop\mvp")
BOT_URL = "http://localhost:8001"
WEB_URL = "http://localhost:8000"

passed = 0
failed = 0
errors = []


def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        msg = f"  FAIL  {name}" + (f" — {detail}" if detail else "")
        print(msg)
        errors.append(msg)


def section(title: str):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


# ==================================================================
# 1. Whitelist Tests
# ==================================================================
section("Whitelist Config")

wl_path = BASE_DIR / "data" / "bot_whitelist.json"
test("Whitelist file exists", wl_path.exists())

wl_data = {}
if wl_path.exists():
    wl_data = json.loads(wl_path.read_text(encoding="utf-8"))

test("Whitelist has strategies key", "strategies" in wl_data)
EXPECTED_COUNT = 45
test(f"Whitelist has {EXPECTED_COUNT} strategies", len(wl_data.get("strategies", [])) == EXPECTED_COUNT,
     f"got {len(wl_data.get('strategies', []))}")

strat_ids = [s["strategy_id"] for s in wl_data.get("strategies", [])]
test("MA_07_BTCUSD_H1 in whitelist (top performer)", "MA_07_BTCUSD_H1" in strat_ids)
test("VTX_02_XAUUSD_H1 in whitelist (XAUUSD)", "VTX_02_XAUUSD_H1" in strat_ids)
test("MTF_01_US30_H1 in whitelist (US30)", "MTF_01_US30_H1" in strat_ids)

# Check lot sizes
lots = wl_data.get("lot_sizes", {})
test("BTCUSD lot = 0.01", lots.get("BTCUSD") == 0.01)
test("XAUUSD lot = 0.01", lots.get("XAUUSD") == 0.01)
test("US30 lot = 0.10", lots.get("US30") == 0.10)

# Check each strategy has correct lot
for s in wl_data.get("strategies", []):
    sym = s["symbol"]
    expected_lot = lots.get(sym, 0)
    test(f"{s['strategy_id']} lot = {expected_lot}", s["lot"] == expected_lot,
         f"got {s['lot']}")


# Validate every strategy passed filters
for s in wl_data.get("strategies", []):
    test(f"{s['strategy_id']} has 5+ trades", s.get("trades", 0) >= 5, f"got {s.get('trades')}")
    test(f"{s['strategy_id']} WR >= 75%", s.get("win_rate", 0) >= 75, f"got {s.get('win_rate')}")
    test(f"{s['strategy_id']} net profitable", s.get("net_pips", 0) > 0, f"got {s.get('net_pips')}")

# Verify track record files exist for each strategy
for s in wl_data.get("strategies", []):
    rec_path = BASE_DIR / "track_records" / f"rec_{s['strategy_id']}.json"
    test(f"Track record exists: {s['strategy_id']}", rec_path.exists())


# ==================================================================
# 2. Executor Config Tests
# ==================================================================
section("Executor Config")

cfg_path = BASE_DIR / "data" / "analysis" / "executor_config.json"
test("Executor config exists", cfg_path.exists())

cfg = {}
if cfg_path.exists():
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

# Check symbols needed by whitelist
needed_symbols = {"BTCUSD", "XAUUSD", "US30"}
for sym in needed_symbols:
    test(f"{sym} in executor config", sym in cfg.get("symbols", {}))
    if sym in cfg.get("symbols", {}):
        broker = cfg["symbols"][sym]["broker_name"]
        test(f"{sym} broker_name = {broker}", broker != "")


# ==================================================================
# 3. Signal Queue Tests
# ==================================================================
section("Signal Queue")

sig_path = BASE_DIR / "data" / "pending_signals.json"
test("pending_signals.json exists", sig_path.exists())
if sig_path.exists():
    try:
        sig_data = json.loads(sig_path.read_text(encoding="utf-8"))
        test("pending_signals is valid JSON", True)
        test("pending_signals is a list", isinstance(sig_data, list))
    except json.JSONDecodeError:
        test("pending_signals is valid JSON", False, "JSON decode error")

tracks_path = BASE_DIR / "track_records" / "active_tracks.json"
test("active_tracks.json exists", tracks_path.exists())


# ==================================================================
# 4. Bot Server API Tests
# ==================================================================
section("Bot Server API (port 8001)")

bot_online = False
try:
    r = requests.get(f"{BOT_URL}/api/health", timeout=5)
    bot_online = r.status_code == 200
    test("Bot server health endpoint", bot_online)
    if bot_online:
        data = r.json()
        test("Health returns status=ok", data.get("status") == "ok")
        test("Health returns service=trading-bot", data.get("service") == "trading-bot")
        test("Health returns mt5 field", "mt5" in data)
except requests.ConnectionError:
    test("Bot server health endpoint", False, "Connection refused — is bot_server.py running?")
except Exception as e:
    test("Bot server health endpoint", False, str(e))

if bot_online:
    # Status endpoint
    try:
        r = requests.get(f"{BOT_URL}/api/status", timeout=5)
        test("Status endpoint returns 200", r.status_code == 200)
        data = r.json()
        test("Status has running field", "running" in data)
        test("Status has mt5_connected field", "mt5_connected" in data)
        test("Status has magic = 888999", data.get("magic") == 888999)
        test(f"Status has strategies count = {EXPECTED_COUNT}", data.get("strategies", 0) == EXPECTED_COUNT,
             f"got {data.get('strategies')}")
        test("Status has account info", "account" in data)

        if data.get("mt5_connected"):
            acct = data.get("account", {})
            test("MT5 account login present", acct.get("login") is not None)
            test("MT5 balance > 0", (acct.get("balance", 0) or 0) > 0,
                 f"balance={acct.get('balance')}")
    except Exception as e:
        test("Status endpoint", False, str(e))

    # Positions endpoint
    try:
        r = requests.get(f"{BOT_URL}/api/positions", timeout=5)
        test("Positions endpoint returns 200", r.status_code == 200)
        data = r.json()
        test("Positions has count field", "count" in data)
        test("Positions has positions field", "positions" in data)
    except Exception as e:
        test("Positions endpoint", False, str(e))

    # Trades endpoint
    try:
        r = requests.get(f"{BOT_URL}/api/trades", timeout=5)
        test("Trades endpoint returns 200", r.status_code == 200)
        data = r.json()
        test("Trades has count field", "count" in data)
        test("Trades has total_pips field", "total_pips" in data)
        test("Trades has win_rate field", "win_rate" in data)
    except Exception as e:
        test("Trades endpoint", False, str(e))

    # Whitelist endpoint
    try:
        r = requests.get(f"{BOT_URL}/api/whitelist", timeout=5)
        test("Whitelist endpoint returns 200", r.status_code == 200)
        data = r.json()
        test(f"Whitelist returns {EXPECTED_COUNT} strategies", data.get("count") == EXPECTED_COUNT,
             f"got {data.get('count')}")
    except Exception as e:
        test("Whitelist endpoint", False, str(e))

    # Dashboard (HTML)
    try:
        r = requests.get(f"{BOT_URL}/", timeout=5)
        test("Dashboard returns 200", r.status_code == 200)
        test("Dashboard returns HTML", "text/html" in r.headers.get("content-type", ""))
    except Exception as e:
        test("Dashboard endpoint", False, str(e))
else:
    print("  SKIP  Skipping API tests — bot server not running")


# ==================================================================
# 5. Website Server Tests
# ==================================================================
section("Website Server (port 8000)")

try:
    r = requests.get(f"{WEB_URL}/api/health", timeout=5)
    test("Website server health endpoint", r.status_code == 200)
except requests.ConnectionError:
    test("Website server health endpoint", False, "Connection refused — website not running (OK if testing bot only)")
except Exception as e:
    test("Website server health endpoint", False, str(e))


# ==================================================================
# 6. Bot State Files
# ==================================================================
section("State Files")

state_path = BASE_DIR / "data" / "bot_state.json"
if state_path.exists():
    try:
        st = json.loads(state_path.read_text(encoding="utf-8"))
        test("bot_state.json is valid JSON", True)
        test("State has cycles field", "cycles" in st)
        test("State has orders_sent field", "orders_sent" in st)
        test("State has cooldowns field", "cooldowns" in st)
    except Exception:
        test("bot_state.json is valid JSON", False)
else:
    print("  SKIP  bot_state.json not yet created (bot hasn't run)")

trades_path = BASE_DIR / "data" / "bot_trades.json"
if trades_path.exists():
    try:
        tr = json.loads(trades_path.read_text(encoding="utf-8"))
        test("bot_trades.json is valid JSON", True)
        test("bot_trades.json is a list", isinstance(tr, list))
    except Exception:
        test("bot_trades.json is valid JSON", False)
else:
    print("  SKIP  bot_trades.json not yet created (no closed trades)")

log_path = BASE_DIR / "data" / "bot_server.log"
test("Bot log file exists", log_path.exists() or not bot_online,
     "Log not found — bot may not have started yet")


# ==================================================================
# 7. Launch Script Tests
# ==================================================================
section("Launch Script")

bat_path = BASE_DIR / "start_bot.bat"
test("start_bot.bat exists", bat_path.exists())
if bat_path.exists():
    content = bat_path.read_text(encoding="utf-8")
    test("start_bot.bat runs bot_server.py", "bot_server.py" in content)
    test("start_bot.bat has cd /d", "cd /d" in content)


# ==================================================================
# Summary
# ==================================================================
print(f"\n{'=' * 50}")
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print(f"{'=' * 50}")

if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  {e}")

sys.exit(0 if failed == 0 else 1)
