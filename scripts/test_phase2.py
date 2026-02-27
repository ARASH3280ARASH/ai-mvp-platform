"""
Phase 2 Tests — Plan Model + Feature Restrictions + Pricing Page
================================================================
Run: python scripts/test_phase2.py
"""
import sys, os, time, requests

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} — {detail}")


def test_plans_module():
    """Test 1: plans.py import + unit checks"""
    print("\n=== Test 1: plans.py module ===")
    from backend.api.plans import (
        PLAN_LIMITS, get_plan_limits, check_symbol_access,
        check_timeframe_access, check_daily_analysis_limit,
        check_alert_limit, check_journal_limit, check_feature_access,
        get_strategy_limit, get_plan_info_for_response, PLAN_NAMES_FA,
    )

    check("PLAN_LIMITS has 4 plans", len(PLAN_LIMITS) == 4, f"got {len(PLAN_LIMITS)}")
    check("free plan exists", "free" in PLAN_LIMITS)
    check("pro plan exists", "pro" in PLAN_LIMITS)
    check("premium plan exists", "premium" in PLAN_LIMITS)
    check("enterprise plan exists", "enterprise" in PLAN_LIMITS)

    # Symbol access
    check("free: XAUUSD allowed", check_symbol_access("free", "XAUUSD") == True)
    check("free: BTCUSD allowed", check_symbol_access("free", "BTCUSD") == True)
    check("free: EURUSD allowed", check_symbol_access("free", "EURUSD") == True)
    check("free: AUDCAD blocked", check_symbol_access("free", "AUDCAD") == False)
    check("free: ETHUSD blocked", check_symbol_access("free", "ETHUSD") == False)
    check("pro: ETHUSD allowed", check_symbol_access("pro", "ETHUSD") == True)
    check("pro: AUDCAD blocked", check_symbol_access("pro", "AUDCAD") == False)
    check("premium: AUDCAD allowed (all)", check_symbol_access("premium", "AUDCAD") == True)
    check("enterprise: anything allowed", check_symbol_access("enterprise", "ANYTHING") == True)

    # Timeframe access
    check("free: H1 allowed", check_timeframe_access("free", "H1") == True)
    check("free: H4 blocked", check_timeframe_access("free", "H4") == False)
    check("free: D1 blocked", check_timeframe_access("free", "D1") == False)
    check("pro: H4 allowed", check_timeframe_access("pro", "H4") == True)
    check("pro: D1 allowed", check_timeframe_access("pro", "D1") == True)
    check("pro: M5 blocked", check_timeframe_access("pro", "M5") == False)
    check("premium: M5 allowed", check_timeframe_access("premium", "M5") == True)

    # Daily analysis limit
    allowed, remaining, limit = check_daily_analysis_limit("free", 0)
    check("free: 0/5 allowed", allowed == True and remaining == 5 and limit == 5)
    allowed, remaining, limit = check_daily_analysis_limit("free", 4)
    check("free: 4/5 allowed, 1 remaining", allowed == True and remaining == 1)
    allowed, remaining, limit = check_daily_analysis_limit("free", 5)
    check("free: 5/5 blocked", allowed == False and remaining == 0)

    # Alert limit
    allowed, _, _ = check_alert_limit("free", 1)
    check("free: 1 alert ok", allowed == True)
    allowed, _, _ = check_alert_limit("free", 2)
    check("free: 2 alerts blocked", allowed == False)

    # Journal limit
    allowed, _, _ = check_journal_limit("free", 9)
    check("free: 9 journal ok", allowed == True)
    allowed, _, _ = check_journal_limit("free", 10)
    check("free: 10 journal blocked", allowed == False)

    # Feature access
    check("free: builder blocked", check_feature_access("free", "builder") == False)
    check("pro: builder allowed", check_feature_access("pro", "builder") == True)
    check("free: telegram blocked", check_feature_access("free", "telegram_alerts") == False)
    check("premium: telegram allowed", check_feature_access("premium", "telegram_alerts") == True)

    # Strategy limit
    check("free: 32 strategies", get_strategy_limit("free") == 32)
    check("pro: 150 strategies", get_strategy_limit("pro") == 150)
    check("premium: 9999 strategies", get_strategy_limit("premium") == 9999)

    # Farsi names
    check("free Farsi name", PLAN_NAMES_FA.get("free") == "رایگان")
    check("pro Farsi name", PLAN_NAMES_FA.get("pro") == "حرفه‌ای")

    # Plan info
    info = get_plan_info_for_response("free", 3)
    check("plan_info has plan", info["plan"] == "free")
    check("plan_info has remaining", info["analyses_remaining"] == 2)
    check("plan_info has upgrade_url", info["upgrade_url"] == "/pricing")


def test_auth_daily_tracking():
    """Test 2: auth_manager daily analysis tracking"""
    print("\n=== Test 2: auth_manager daily tracking ===")
    from backend.api.auth_manager import (
        get_daily_analysis_count, increment_daily_analysis, _get_db,
    )

    # Create a test user
    import bcrypt
    conn = _get_db()
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode()
    conn.execute("DELETE FROM auth_users WHERE email='test_phase2@test.com'")
    conn.execute(
        "INSERT INTO auth_users (email, password_hash, name, is_verified) VALUES (?,?,?,1)",
        ("test_phase2@test.com", pw_hash, "Test Phase2")
    )
    conn.commit()
    row = conn.execute("SELECT id FROM auth_users WHERE email='test_phase2@test.com'").fetchone()
    uid = row["id"]
    conn.close()

    count = get_daily_analysis_count(uid)
    check("initial count is 0", count == 0, f"got {count}")

    new_count = increment_daily_analysis(uid)
    check("increment returns 1", new_count == 1, f"got {new_count}")

    new_count = increment_daily_analysis(uid)
    check("second increment returns 2", new_count == 2, f"got {new_count}")

    count = get_daily_analysis_count(uid)
    check("get count returns 2", count == 2, f"got {count}")

    # Cleanup
    conn = _get_db()
    conn.execute("DELETE FROM auth_users WHERE email='test_phase2@test.com'")
    conn.commit()
    conn.close()


def test_api_endpoints():
    """Test 3-7: API endpoint tests (requires running server)"""
    print("\n=== Test 3: API endpoint tests ===")

    # Check server is running
    try:
        r = requests.get(f"{BASE}/api/health", timeout=5)
        check("server is running", r.status_code == 200)
    except Exception as e:
        print(f"  [SKIP] Server not running at {BASE}: {e}")
        print("  Start server with: python -m uvicorn backend.api.server:app --host :: --port 8000")
        return

    # Pricing page
    r = requests.get(f"{BASE}/pricing", timeout=5)
    check("GET /pricing returns 200", r.status_code == 200)
    check("/pricing has plan cards", "plan-card" in r.text)
    check("/pricing has comparison table", "compare-section" in r.text or "ct-wrap" in r.text)

    # Plans API
    r = requests.get(f"{BASE}/api/plans", timeout=5)
    check("GET /api/plans returns 200", r.status_code == 200)
    data = r.json()
    check("/api/plans has plans dict", "plans" in data)
    check("/api/plans has 4 plans", len(data.get("plans", {})) == 4, f"got {len(data.get('plans', {}))}")

    # Plans my-usage (no auth = 401)
    r = requests.get(f"{BASE}/api/plans/my-usage", timeout=5)
    check("GET /api/plans/my-usage without auth = 401", r.status_code == 401)

    # Analyze XAUUSD H1 (free allowed)
    r = requests.get(f"{BASE}/api/analyze3/XAUUSD/H1", timeout=30)
    check("analyze3 XAUUSD H1 = 200 (free allowed)", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("response has plan_info", "plan_info" in data)

    # Analyze AUDCAD H1 (not free symbol)
    r = requests.get(f"{BASE}/api/analyze3/AUDCAD/H1", timeout=10)
    check("analyze3 AUDCAD H1 = 403 (symbol restricted)", r.status_code == 403, f"got {r.status_code}")

    # Analyze XAUUSD H4 (not free TF)
    r = requests.get(f"{BASE}/api/analyze3/XAUUSD/H4", timeout=10)
    check("analyze3 XAUUSD H4 = 403 (timeframe restricted)", r.status_code == 403, f"got {r.status_code}")

    # Check existing pages still return 200
    pages = ["/", "/dashboard", "/builder", "/journal", "/alerts",
             "/track-record", "/guide", "/services", "/about", "/contact",
             "/robots", "/performance", "/login", "/register"]
    for page in pages:
        try:
            r = requests.get(f"{BASE}{page}", timeout=5)
            check(f"GET {page} = 200", r.status_code == 200, f"got {r.status_code}")
        except Exception as e:
            check(f"GET {page}", False, str(e))


def test_nav_links():
    """Test 8: Nav has pricing link on all pages"""
    print("\n=== Test 8: Nav pricing links ===")

    try:
        r = requests.get(f"{BASE}/api/health", timeout=3)
    except:
        print("  [SKIP] Server not running")
        return

    pages = ["/dashboard", "/builder", "/journal", "/alerts",
             "/services", "/about", "/contact", "/guide",
             "/login", "/register", "/robots", "/performance", "/pricing"]
    for page in pages:
        try:
            r = requests.get(f"{BASE}{page}", timeout=5)
            has_link = '/pricing' in r.text and 'تعرفه' in r.text
            check(f"{page} has pricing nav link", has_link)
        except Exception as e:
            check(f"{page} nav link", False, str(e))


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 Tests — Plan Model + Feature Restrictions")
    print("=" * 60)

    # Unit tests (no server needed)
    test_plans_module()
    test_auth_daily_tracking()

    # API tests (server needed)
    test_api_endpoints()
    test_nav_links()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)
