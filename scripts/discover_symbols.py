"""
Whilber-AI - Broker Symbol Discovery
======================================
Scans MT5 to find actual symbol names on this broker.
Run this FIRST to see what names the broker uses.

Run: python scripts/discover_symbols.py
"""

import sys
import os

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")
os.system("")

import MetaTrader5 as mt5

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

MT5_PATH = r"C:\Program Files\Moneta Markets MT5 Terminal\terminal64.exe"

# What we're looking for
SEARCH_SYMBOLS = [
    # Forex Major
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
    # Forex Minor
    "EURGBP", "EURJPY", "GBPJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
    "AUDJPY", "AUDNZD", "AUDCAD", "AUDCHF",
    "NZDJPY", "NZDCAD", "NZDCHF",
    "CADJPY", "CADCHF", "CHFJPY",
    # Metals
    "XAUUSD", "XAGUSD",
    # Indices
    "US100", "US30", "US500", "NAS100", "USTEC",
    # Crypto
    "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD",
    "DOGEUSD", "DOTUSD", "LINKUSD", "LTCUSD", "BCHUSD",
    "AVAXUSD", "UNIUSD", "XLMUSD", "TRXUSD", "ALGOUSD",
    "FILUSD", "NEOUSD", "BATUSD", "IOTAUSD", "ZECUSD",
    "SHBUSD", "HBARUSD", "ONDOUSD", "WIFUSD", "BERAUSD",
    "TRUMPUSD",
]


def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Broker Symbol Discovery - Moneta Markets{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    if not mt5.initialize(path=MT5_PATH, login=1035360, password="G0Z#IQ1w", server="MonetaMarkets-Demo"):
        mt5.shutdown()
        if not mt5.initialize(MT5_PATH):
            print(f"{RED}Failed to connect to MT5{RESET}")
            return

    # Get ALL symbols from broker
    all_symbols = mt5.symbols_get()
    if all_symbols is None:
        print(f"{RED}Could not get symbols{RESET}")
        mt5.shutdown()
        return

    all_names = [s.name for s in all_symbols]
    print(f"{CYAN}Total symbols on broker: {len(all_names)}{RESET}\n")

    # ── Show ALL symbols grouped ────────────────────────────
    print(f"{BOLD}All broker symbols:{RESET}")
    for i, name in enumerate(sorted(all_names)):
        print(f"  {name}", end="")
        if (i + 1) % 8 == 0:
            print()
    print("\n")

    # ── Match our symbols ───────────────────────────────────
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Symbol Matching Results{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    found = {}
    not_found = []

    for base in SEARCH_SYMBOLS:
        # Try exact match
        if base in all_names:
            found[base] = base
            continue

        # Try with + suffix
        if f"{base}+" in all_names:
            found[base] = f"{base}+"
            continue

        # Try with .raw suffix
        if f"{base}.raw" in all_names:
            found[base] = f"{base}.raw"
            continue

        # Try with m suffix
        if f"{base}m" in all_names:
            found[base] = f"{base}m"
            continue

        # Try partial match (base name appears in broker name)
        partial = [n for n in all_names if base.lower() in n.lower()]
        if partial:
            found[base] = partial[0]  # Take first match
            continue

        not_found.append(base)

    # Print results
    print(f"{GREEN}Found ({len(found)}):{RESET}")
    for base, broker_name in sorted(found.items()):
        suffix = ""
        if base != broker_name:
            suffix = f"  →  {YELLOW}{broker_name}{RESET}"
        print(f"  {GREEN}[OK]{RESET}  {base:12s}{suffix}")

    if not_found:
        print(f"\n{RED}Not Found ({len(not_found)}):{RESET}")
        for base in not_found:
            print(f"  {RED}[--]{RESET}  {base}")

    # ── Generate MT5_ALTERNATES dict ────────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Copy this into symbol_map.py (MT5_ALTERNATES):{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    print("MT5_ALTERNATES = {")
    for base, broker_name in sorted(found.items()):
        if base != broker_name:
            print(f'    "{base}": ["{broker_name}", "{base}"],')
    print("}")

    # ── Generate mt5_name mapping ───────────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Actual MT5 names to use:{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    print("# Paste into SYMBOLS dict as mt5_name values:")
    for base, broker_name in sorted(found.items()):
        if base != broker_name:
            print(f'    "{base}": mt5_name = "{broker_name}"')

    # ── Quick data test on found symbols ────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Quick Data Test (H1, 5 bars):{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    import pandas as pd
    test_count = 0
    test_ok = 0

    for base, broker_name in sorted(found.items()):
        if test_count >= 15:  # Test first 15 only
            break
        test_count += 1

        mt5.symbol_select(broker_name, True)
        rates = mt5.copy_rates_from_pos(broker_name, mt5.TIMEFRAME_H1, 0, 5)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            last_close = df['close'].iloc[-1]
            print(f"  {GREEN}[OK]{RESET}  {base:12s} ({broker_name:14s}) | Close: {last_close}")
            test_ok += 1
        else:
            print(f"  {RED}[--]{RESET}  {base:12s} ({broker_name:14s}) | NO DATA")

    print(f"\n  Data test: {test_ok}/{test_count} OK")

    mt5.shutdown()
    print(f"\n{GREEN}{BOLD}Done! Use the output above to update symbol_map.py{RESET}\n")


if __name__ == "__main__":
    main()
