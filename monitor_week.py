"""Daily health monitor — run anytime to check system."""
import urllib.request, json, os, glob, time
from datetime import datetime, timezone
from collections import defaultdict

def api(path):
    try:
        req = urllib.request.Request(f"http://127.0.0.1:8000{path}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except:
        return None

print("=" * 55)
print(f"  WHILBER MONITOR — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 55)

# Server
r = api("/api/tracker/status")
if r:
    last = r.get("last_cycle", "")
    age = 999
    if last:
        try:
            lc = datetime.fromisoformat(last.replace("Z", "+00:00"))
            age = int((datetime.now(timezone.utc) - lc).total_seconds())
        except: pass
    
    running = "YES" if age < 120 else "NO"
    print(f"  Server:  ON")
    print(f"  Tracker: {running} (last cycle {age}s ago)")
    print(f"  Active:  {r.get('active_trades', 0)} trades")
else:
    print(f"  Server:  *** OFF ***")
    print(f"  -> Run start_week.bat!")

# State
TR = r"C:\Users\Administrator\Desktop\mvp\track_records"
sf = os.path.join(TR, "tracker_state.json")
if os.path.exists(sf):
    with open(sf, "r", encoding="utf-8") as f:
        st = json.load(f)
    print(f"  Cycles:  {st.get('total_cycles', 0)}")
    print(f"  Signals: {st.get('total_signals', 0)}")
    print(f"  Closes:  {st.get('total_closes', 0)}")

# Symbols
print(f"\n  Symbols:")
syms = defaultdict(lambda: {"t":0, "a":0})
for fp in glob.glob(os.path.join(TR, "rec_*.json")):
    try:
        with open(fp, "r", encoding="utf-8") as f:
            d = json.load(f)
        for t in d.get("trades", []):
            s = t.get("symbol", "?")
            syms[s]["t"] += 1
            if t.get("status") == "active":
                syms[s]["a"] += 1
    except: pass

for s in ["XAUUSD","EURUSD","GBPUSD","USDJPY","BTCUSD","NAS100","US30","XAGUSD","AUDUSD","USDCAD","NZDUSD","USDCHF"]:
    d = syms.get(s, {"t":0, "a":0})
    i = "OK" if d["t"] > 0 else "--"
    print(f"    {i:2s} {s:8s}: {d['t']:5d} trades, {d['a']:2d} active")

print("=" * 55)
input("Press Enter...")
