"""Auto-start tracker after server boots."""
import time, urllib.request, json

time.sleep(15)

for attempt in range(5):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/tracker/start",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("success"):
                # Verify
                time.sleep(3)
                req2 = urllib.request.Request("http://127.0.0.1:8000/api/tracker/status")
                with urllib.request.urlopen(req2, timeout=10) as resp2:
                    status = json.loads(resp2.read().decode("utf-8"))
                    active = status.get("active_trades", 0)
                print(f"[OK] Tracker started — {active} active trades")
                break
    except Exception as e:
        print(f"[WAIT] Attempt {attempt+1}/5: {e}")
        time.sleep(10)
