"""
Whilber-AI — Start Executor (Standalone)
==========================================
Run this to start the executor daemon independently.
It reads whitelist + scans signals + opens real trades.
"""
import sys
import time
sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")

from backend.executor.executor_daemon import start_executor, stop_executor, get_executor_status
from backend.executor.whitelist_manager import generate_whitelist

print("=" * 60)
print("  Whilber-AI — MT5 Live Executor")
print("=" * 60)

# Step 1: Generate whitelist
print("\n[1] Generating whitelist from ranking...")
wl = generate_whitelist()
print(f"    Approved: {len(wl)} strategies")

if not wl:
    print("\n    ⚠️  No strategies approved!")
    print("    Executor needs ranking data with winning strategies.")
    print("    Run tracker for a few days first, then try again.")
    input("\nPress Enter to exit...")
    sys.exit(0)

# Step 2: Start executor
print("\n[2] Starting executor daemon...")
start_executor()

print("\n✅ Executor running! Scanning every 5 seconds.")
print("   Press Ctrl+C to stop.\n")

try:
    while True:
        time.sleep(30)
        status = get_executor_status()
        print(f"[STATUS] Cycles={status['cycles']} Orders={status['orders_sent']} "
              f"Open={status['open_positions']} Balance=${status.get('balance',0):.0f}")
except KeyboardInterrupt:
    print("\n\nStopping executor...")
    stop_executor()
    print("Done.")
