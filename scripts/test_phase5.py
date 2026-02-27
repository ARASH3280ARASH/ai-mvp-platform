"""
Whilber-AI MVP - Phase 5 Test: Plan UI Integration
====================================================
Tests plan-ui.js serving, plan API endpoints, and script tag presence in all pages.
Requires server running at localhost:8000

Run: python scripts/test_phase5.py
"""

import os
import sys
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

BASE = "http://localhost:8000"
passed = 0
failed = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  {GREEN}[PASS]{RESET}  {msg}")

def fail(msg):
    global failed
    failed += 1
    print(f"  {RED}[FAIL]{RESET}  {msg}")

def info(msg):
    print(f"  {CYAN}[INFO]{RESET}  {msg}")

def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def http_get(path, headers=None):
    url = BASE + path
    try:
        req = urllib.request.Request(url)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            content_type = resp.headers.get("Content-Type", "")
            if "json" in content_type:
                return json.loads(body), resp.status
            return body, resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(body), e.code
        except Exception:
            return {"error": body}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def http_post(path, data, headers=None):
    url = BASE + path
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(body), e.code
        except Exception:
            return {"error": body}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def get_test_token():
    """Try to login and get a token for authenticated tests."""
    data, code = http_post("/api/auth/login", {
        "email": "admin@whilber-ai.com",
        "password": "admin123"
    })
    if code == 200 and data.get("token"):
        return data["token"]
    # Try register + login
    http_post("/api/auth/register", {
        "email": "test_phase5@whilber.ai",
        "password": "test12345",
        "name": "Phase5 Tester"
    })
    data, code = http_post("/api/auth/login", {
        "email": "test_phase5@whilber.ai",
        "password": "test12345"
    })
    if code == 200 and data.get("token"):
        return data["token"]
    return None


def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Whilber-AI - Phase 5: Plan UI Integration Test{RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    # ── 1. plan-ui.js file exists and served ──────────────────
    header("1. plan-ui.js File & Static Serving")

    js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "plan-ui.js")
    if os.path.exists(js_path):
        size = os.path.getsize(js_path)
        ok(f"plan-ui.js exists ({size} bytes)")
    else:
        fail("plan-ui.js file not found")

    body, code = http_get("/static/plan-ui.js")
    if code == 200:
        ok(f"/static/plan-ui.js served (HTTP {code})")
        if isinstance(body, str) and "WHILBER_PLAN" in body:
            ok("plan-ui.js contains WHILBER_PLAN global")
        else:
            fail("plan-ui.js missing WHILBER_PLAN reference")
        if isinstance(body, str) and "whilber-plan-ready" in body:
            ok("plan-ui.js dispatches whilber-plan-ready event")
        else:
            fail("plan-ui.js missing whilber-plan-ready event")
    else:
        fail(f"/static/plan-ui.js returned HTTP {code}")

    # ── 2. /api/plans/my-usage with auth ──────────────────────
    header("2. Plan API Endpoints")

    token = get_test_token()
    if token:
        info(f"Got auth token: {token[:20]}...")
        data, code = http_get("/api/plans/my-usage", {"Authorization": f"Bearer {token}"})
        if code == 200:
            ok(f"/api/plans/my-usage returned 200")
            # Check structure
            for key in ["plan", "plan_fa", "limits", "usage", "upgrade_url"]:
                if key in data:
                    ok(f"  Response has '{key}' field")
                else:
                    fail(f"  Response missing '{key}' field")
            # Check limits sub-fields
            limits = data.get("limits", {})
            for lk in ["max_strategies", "analyses_per_day", "max_alerts"]:
                if lk in limits:
                    ok(f"  limits.{lk} = {limits[lk]}")
                else:
                    fail(f"  limits missing '{lk}'")
            # Check usage sub-fields
            usage = data.get("usage", {})
            if "analyses_today" in usage:
                ok(f"  usage.analyses_today = {usage['analyses_today']}")
            else:
                fail("  usage missing 'analyses_today'")
        else:
            fail(f"/api/plans/my-usage returned HTTP {code}")
    else:
        info("Could not get auth token — skipping authenticated tests")

    # ── 3. /api/plans/my-usage without token returns 401 ──────
    data, code = http_get("/api/plans/my-usage")
    if code in (401, 403):
        ok(f"/api/plans/my-usage without token returned {code}")
    else:
        fail(f"/api/plans/my-usage without token returned {code} (expected 401)")

    # ── 4. Script tag present in all modified HTML pages ──────
    header("3. Script Tag Presence in HTML Pages")

    pages_with_plan_ui = [
        ("/dashboard", "dashboard.html"),
        ("/alerts", "alerts_page.html"),
        ("/builder", "strategy_builder.html"),
        ("/risk-manager", "risk_manager.html"),
        ("/journal", "journal.html"),
        ("/robots", "robots.html"),
        ("/track-record", "track_record.html"),
        ("/", "landing.html"),
        ("/services", "services.html"),
        ("/about", "about.html"),
        ("/contact", "contact.html"),
        ("/guide", "guide.html"),
        ("/performance", "performance.html"),
        ("/pricing", "pricing.html"),
        ("/login", "login.html"),
        ("/register", "register.html"),
    ]

    for route, filename in pages_with_plan_ui:
        body, code = http_get(route)
        if code == 200:
            if isinstance(body, str) and '/static/plan-ui.js' in body:
                ok(f"{filename} ({route}) includes plan-ui.js")
            else:
                fail(f"{filename} ({route}) missing plan-ui.js script tag")
        else:
            fail(f"{filename} ({route}) returned HTTP {code}")

    # ── 5. All pages load without errors (200) ────────────────
    header("4. All Modified Pages Load (HTTP 200)")

    all_routes = [p[0] for p in pages_with_plan_ui]
    for route in all_routes:
        _, code = http_get(route)
        if code == 200:
            ok(f"{route} -> 200")
        else:
            fail(f"{route} -> {code}")

    # ── 6. Phase 1-4 compatibility ────────────────────────────
    header("5. Phase 1-4 Compatibility")

    # Auth endpoints
    _, code = http_get("/api/auth/profile")
    if code in (200, 401, 403):
        ok(f"/api/auth/profile -> {code}")
    else:
        fail(f"/api/auth/profile -> {code}")

    # Plans endpoint
    data, code = http_get("/api/plans")
    if code == 200 and "plans" in (data if isinstance(data, dict) else {}):
        ok("/api/plans returns plan list")
        plans = data.get("plans", {})
        for p in ["free", "pro", "premium", "enterprise"]:
            if p in plans:
                ok(f"  Plan '{p}' present")
            else:
                fail(f"  Plan '{p}' missing")
    else:
        fail(f"/api/plans -> {code}")

    # Payment endpoint
    _, code = http_get("/api/payments/plans")
    if code in (200, 404):
        ok(f"/api/payments/plans -> {code}")
    else:
        info(f"/api/payments/plans -> {code}")

    # Admin login check
    _, code = http_get("/admin")
    if code == 200:
        ok("/admin page loads")
    else:
        fail(f"/admin -> {code}")

    # ── 7. Feature pages have plan-specific code ──────────────
    header("6. Feature-Specific Plan Code")

    # Dashboard: plan widget + symbol/TF greying
    body, _ = http_get("/dashboard")
    if isinstance(body, str):
        if "whilber-plan-ready" in body and "planProgress" in body:
            ok("dashboard.html has plan-ready listener with planProgress")
        else:
            fail("dashboard.html missing plan-ready code")
        if "selSymbol" in body and "disabled" in body:
            ok("dashboard.html has symbol restriction logic")
        else:
            info("dashboard.html symbol restriction check inconclusive")

    # Alerts: alert limit + telegram lock
    body, _ = http_get("/alerts")
    if isinstance(body, str):
        if "whilber-plan-ready" in body and "max_alerts" in body:
            ok("alerts_page.html has alert limit logic")
        else:
            fail("alerts_page.html missing alert limit code")

    # Builder: lock overlay
    body, _ = http_get("/builder")
    if isinstance(body, str):
        if "whilber-plan-ready" in body and "builderLockOverlay" in body:
            ok("strategy_builder.html has plan-based lock logic")
        else:
            fail("strategy_builder.html missing plan lock code")

    # Risk manager: results panel lock
    body, _ = http_get("/risk-manager")
    if isinstance(body, str):
        if "whilber-plan-ready" in body and "resultsPanel" in body:
            ok("risk_manager.html has results panel lock logic")
        else:
            fail("risk_manager.html missing results lock code")

    # Journal: entry limit
    body, _ = http_get("/journal")
    if isinstance(body, str):
        if "whilber-plan-ready" in body and "max_journal" in body:
            ok("journal.html has journal limit logic")
        else:
            fail("journal.html missing journal limit code")

    # Robots: download lock
    body, _ = http_get("/robots")
    if isinstance(body, str):
        if "whilber-plan-ready" in body and "max_robots" in body:
            ok("robots.html has robot download lock logic")
        else:
            fail("robots.html missing robot lock code")

    # Track record: date restriction
    body, _ = http_get("/track-record")
    if isinstance(body, str):
        if "whilber-plan-ready" in body and "PLAN_MAX_DAYS" in body:
            ok("track_record.html has date restriction logic")
        else:
            fail("track_record.html missing date restriction code")

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    total = passed + failed
    print(f"{BOLD}  Results: {GREEN}{passed}{RESET}/{total} passed, {RED if failed else GREEN}{failed}{RESET} failed{RESET}")
    if failed == 0:
        print(f"  {GREEN}{BOLD}ALL TESTS PASSED{RESET}")
    else:
        print(f"  {YELLOW}Some tests failed — check output above{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
