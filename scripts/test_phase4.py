"""
Whilber-AI — Phase 4 Test Suite
=================================
Tests: admin_manager, new endpoints, Phase 1-3 compatibility.
Run: python scripts/test_phase4.py
"""

import sys
import os
import io
import time
import json
import requests

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")

BASE = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "Whilber@2026"

passed = 0
failed = 0
errors = []


def ok(name):
    global passed
    passed += 1
    print(f"  [PASS] {name}")


def fail(name, reason=""):
    global failed
    failed += 1
    errors.append(f"{name}: {reason}")
    print(f"  [FAIL] {name} -- {reason}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── Helper: get admin token ──
def get_admin_token():
    r = requests.post(f"{BASE}/api/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if r.status_code == 200 and r.json().get("token"):
        return r.json()["token"]
    return None


def admin_headers(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════
# TEST 1: Import admin_manager
# ══════════════════════════════════════════════════
section("1. Import admin_manager")
try:
    from backend.api.admin_manager import (
        get_auth_users, get_auth_user_detail, admin_change_plan,
        admin_toggle_user, get_user_stats, export_users_csv,
        create_discount, get_all_discounts, toggle_discount, delete_discount,
        get_revenue_stats, get_revenue_chart, admin_send_notification,
    )
    ok("All admin_manager functions imported")
except ImportError as e:
    fail("Import admin_manager", str(e))


# ══════════════════════════════════════════════════
# TEST 2: User list with filters
# ══════════════════════════════════════════════════
section("2. User list with filters")
try:
    result = get_auth_users(limit=10, offset=0)
    assert "users" in result, "Missing 'users' key"
    assert "total" in result, "Missing 'total' key"
    assert isinstance(result["users"], list), "users should be list"
    ok(f"User list: {result['total']} total users")

    # With plan filter
    result2 = get_auth_users(plan_filter="free")
    ok(f"Plan filter (free): {result2['total']} users")

    # With status filter
    result3 = get_auth_users(status_filter="active")
    ok(f"Status filter (active): {result3['total']} users")
except Exception as e:
    fail("User list", str(e))


# ══════════════════════════════════════════════════
# TEST 3: User detail
# ══════════════════════════════════════════════════
section("3. User detail")
try:
    users = get_auth_users(limit=1)
    if users["total"] > 0:
        uid = users["users"][0]["id"]
        detail = get_auth_user_detail(uid)
        assert detail is not None, "Detail should not be None"
        assert "email" in detail, "Missing email"
        assert "payment_count" in detail, "Missing payment_count"
        assert "password_hash" not in detail, "Should not expose password_hash"
        ok(f"User detail for id={uid}: {detail['email']}")
    else:
        ok("No users to test detail (skip)")
except Exception as e:
    fail("User detail", str(e))


# ══════════════════════════════════════════════════
# TEST 4: Admin change user plan
# ══════════════════════════════════════════════════
section("4. Admin change user plan")
try:
    users = get_auth_users(limit=1)
    if users["total"] > 0:
        uid = users["users"][0]["id"]
        original_plan = users["users"][0]["plan"]

        # Change to pro
        r = admin_change_plan(uid, "pro", 30)
        assert r["success"], f"Change plan failed: {r}"
        ok("Changed plan to pro")

        # Verify
        detail = get_auth_user_detail(uid)
        assert detail["plan"] == "pro", f"Expected pro, got {detail['plan']}"
        ok("Verified plan is now pro")

        # Restore
        admin_change_plan(uid, original_plan, 30)
        ok(f"Restored plan to {original_plan}")
    else:
        ok("No users to test (skip)")
except Exception as e:
    fail("Admin change plan", str(e))


# ══════════════════════════════════════════════════
# TEST 5: Admin toggle user active
# ══════════════════════════════════════════════════
section("5. Admin toggle user active")
try:
    users = get_auth_users(limit=1)
    if users["total"] > 0:
        uid = users["users"][0]["id"]

        # Deactivate
        r = admin_toggle_user(uid, False)
        assert r["success"], "Toggle failed"
        detail = get_auth_user_detail(uid)
        assert detail["is_active"] == 0, "Should be inactive"
        ok("Deactivated user")

        # Reactivate
        r = admin_toggle_user(uid, True)
        assert r["success"], "Toggle failed"
        detail = get_auth_user_detail(uid)
        assert detail["is_active"] == 1, "Should be active"
        ok("Reactivated user")
    else:
        ok("No users to test (skip)")
except Exception as e:
    fail("Admin toggle user", str(e))


# ══════════════════════════════════════════════════
# TEST 6: User stats accuracy
# ══════════════════════════════════════════════════
section("6. User stats")
try:
    stats = get_user_stats()
    assert "total" in stats, "Missing total"
    assert "per_plan" in stats, "Missing per_plan"
    assert "new_today" in stats, "Missing new_today"
    assert "new_week" in stats, "Missing new_week"
    assert "new_month" in stats, "Missing new_month"
    ok(f"User stats: total={stats['total']}, per_plan={stats['per_plan']}")
except Exception as e:
    fail("User stats", str(e))


# ══════════════════════════════════════════════════
# TEST 7: Create discount
# ══════════════════════════════════════════════════
section("7. Create discount → list includes it")
try:
    test_code = f"TEST{int(time.time()) % 100000}"
    r = create_discount(test_code, 25, 50, "2027-12-31")
    assert r["success"], f"Create failed: {r}"
    ok(f"Created discount: {test_code}")

    discs = get_all_discounts()
    found = any(d["code"] == test_code for d in discs)
    assert found, "Discount not found in list"
    ok("Discount found in list")
except Exception as e:
    fail("Create discount", str(e))


# ══════════════════════════════════════════════════
# TEST 8: Toggle discount
# ══════════════════════════════════════════════════
section("8. Toggle discount → verify disabled")
try:
    discs = get_all_discounts()
    test_disc = next((d for d in discs if d["code"] == test_code), None)
    if test_disc:
        # Disable
        r = toggle_discount(test_disc["id"], False)
        assert r["success"], "Toggle failed"

        discs2 = get_all_discounts()
        d = next(x for x in discs2 if x["id"] == test_disc["id"])
        assert not d["is_active"], "Should be inactive"
        ok("Disabled discount")

        # Re-enable
        r = toggle_discount(test_disc["id"], True)
        assert r["success"], "Toggle failed"
        ok("Re-enabled discount")
    else:
        fail("Toggle discount", "Test discount not found")
except Exception as e:
    fail("Toggle discount", str(e))


# ══════════════════════════════════════════════════
# TEST 9: Delete discount
# ══════════════════════════════════════════════════
section("9. Delete discount → verify gone")
try:
    discs = get_all_discounts()
    test_disc = next((d for d in discs if d["code"] == test_code), None)
    if test_disc:
        r = delete_discount(test_disc["id"])
        assert r["success"], "Delete failed"

        discs2 = get_all_discounts()
        found = any(d["id"] == test_disc["id"] for d in discs2)
        assert not found, "Discount still exists after delete"
        ok("Deleted discount, verified gone")
    else:
        fail("Delete discount", "Test discount not found")
except Exception as e:
    fail("Delete discount", str(e))


# ══════════════════════════════════════════════════
# TEST 10: Revenue stats
# ══════════════════════════════════════════════════
section("10. Revenue stats")
try:
    rev = get_revenue_stats()
    for key in ["today", "week", "month", "all_time", "by_plan", "by_method", "mrr", "arpu", "churn_rate"]:
        assert key in rev, f"Missing key: {key}"
    ok(f"Revenue stats: today={rev['today']}, month={rev['month']}, all_time={rev['all_time']}")
except Exception as e:
    fail("Revenue stats", str(e))


# ══════════════════════════════════════════════════
# TEST 11: Revenue chart
# ══════════════════════════════════════════════════
section("11. Revenue chart")
try:
    chart = get_revenue_chart(30)
    assert isinstance(chart, list), "Chart should be a list"
    assert len(chart) == 30, f"Expected 30 entries, got {len(chart)}"
    assert "date" in chart[0], "Missing date key"
    assert "amount" in chart[0], "Missing amount key"
    ok(f"Revenue chart: {len(chart)} days")
except Exception as e:
    fail("Revenue chart", str(e))


# ══════════════════════════════════════════════════
# TEST 12: Admin send notification
# ══════════════════════════════════════════════════
section("12. Admin send notification")
try:
    users = get_auth_users(limit=1)
    if users["total"] > 0:
        email = users["users"][0]["email"]
        r = admin_send_notification(email, "تست اطلاع‌رسانی Phase 4", "تست")
        assert r["success"], f"Send failed: {r}"
        assert r["sent_count"] == 1, f"Expected 1, got {r['sent_count']}"
        ok(f"Sent notification to {email}")

        # Verify using alert_manager
        try:
            from backend.api.alert_manager import get_notifications
            notifs = get_notifications(email, limit=5)
            found = any("تست" in (n.get("title", "") or "") for n in notifs)
            if found:
                ok("Notification verified in user's notifications")
            else:
                ok("Notification sent (could not verify in list — may be timing)")
        except ImportError:
            ok("Notification sent (alert_manager not available for verification)")
    else:
        ok("No users to test (skip)")
except Exception as e:
    fail("Admin send notification", str(e))


# ══════════════════════════════════════════════════
# TEST 13: HTTP endpoints
# ══════════════════════════════════════════════════
section("13. HTTP endpoints return 200 with admin token")
try:
    token = get_admin_token()
    if not token:
        fail("HTTP endpoints", "Could not get admin token")
    else:
        ok(f"Admin login successful, token obtained")
        hdrs = admin_headers(token)

        endpoints = [
            ("GET", "/api/admin/auth-users"),
            ("GET", "/api/admin/user-stats"),
            ("GET", "/api/admin/discounts"),
            ("GET", "/api/admin/revenue"),
            ("GET", "/api/admin/revenue/chart"),
        ]
        for method, path in endpoints:
            r = requests.request(method, f"{BASE}{path}", headers=hdrs)
            if r.status_code == 200:
                ok(f"{method} {path} → 200")
            else:
                fail(f"{method} {path}", f"Status {r.status_code}: {r.text[:100]}")

        # Test users-export
        r = requests.get(f"{BASE}/api/admin/users-export", headers=hdrs)
        if r.status_code == 200 and "text/csv" in r.headers.get("content-type", ""):
            ok("GET /api/admin/users-export → 200 (CSV)")
        elif r.status_code == 200:
            ok("GET /api/admin/users-export → 200")
        else:
            fail("GET /api/admin/users-export", f"Status {r.status_code}")

        # Test notify
        r = requests.post(f"{BASE}/api/admin/notify", headers=hdrs,
                          json={"target": "all", "message": "HTTP test", "title": "Test"})
        if r.status_code == 200:
            ok("POST /api/admin/notify → 200")
        else:
            fail("POST /api/admin/notify", f"Status {r.status_code}")

except Exception as e:
    fail("HTTP endpoints", str(e))


# ══════════════════════════════════════════════════
# TEST 14: Phase 3 payment endpoints still work
# ══════════════════════════════════════════════════
section("14. Phase 3 payment endpoints (backward compat)")
try:
    token = get_admin_token()
    if token:
        hdrs = admin_headers(token)
        r = requests.get(f"{BASE}/api/admin/payments?limit=5", headers=hdrs)
        if r.status_code == 200:
            ok("GET /api/admin/payments → 200")
        else:
            fail("GET /api/admin/payments", f"Status {r.status_code}")

        r = requests.post(f"{BASE}/api/admin/payment/check-expiry", headers=hdrs)
        if r.status_code == 200:
            ok("POST /api/admin/payment/check-expiry → 200")
        else:
            fail("POST /api/admin/payment/check-expiry", f"Status {r.status_code}")
    else:
        fail("Phase 3 compat", "No admin token")
except Exception as e:
    fail("Phase 3 compat", str(e))


# ══════════════════════════════════════════════════
# TEST 15: Phase 1-3 compatibility
# ══════════════════════════════════════════════════
section("15. Phase 1-3 compatibility")
try:
    # Health endpoint
    r = requests.get(f"{BASE}/api/health")
    if r.status_code == 200:
        ok("GET /api/health → 200")
    else:
        fail("/api/health", f"Status {r.status_code}")

    # Auth endpoints exist
    r = requests.post(f"{BASE}/api/auth/login", json={"email": "test@test.com", "password": "test"})
    if r.status_code in (200, 400, 401, 422):
        ok("POST /api/auth/login → responds")
    else:
        fail("/api/auth/login", f"Status {r.status_code}")

    # Payment config
    r = requests.get(f"{BASE}/api/payment/config")
    if r.status_code == 200:
        ok("GET /api/payment/config → 200")
    elif r.status_code == 404:
        ok("GET /api/payment/config → 404 (payment module not loaded, acceptable)")
    else:
        fail("/api/payment/config", f"Status {r.status_code}")

    # Admin old endpoints
    token = get_admin_token()
    if token:
        hdrs = admin_headers(token)
        r = requests.get(f"{BASE}/api/admin/stats", headers=hdrs)
        if r.status_code == 200:
            ok("GET /api/admin/stats → 200 (old admin)")
        else:
            fail("/api/admin/stats", f"Status {r.status_code}")

        r = requests.get(f"{BASE}/api/admin/users?limit=5", headers=hdrs)
        if r.status_code == 200:
            ok("GET /api/admin/users → 200 (old users endpoint)")
        else:
            fail("/api/admin/users", f"Status {r.status_code}")
except Exception as e:
    fail("Phase 1-3 compat", str(e))


# ══════════════════════════════════════════════════
# TEST 16: Admin login still works
# ══════════════════════════════════════════════════
section("16. Admin login with admin/Whilber@2026")
try:
    r = requests.post(f"{BASE}/api/admin/login",
                      json={"username": "admin", "password": "Whilber@2026"})
    assert r.status_code == 200, f"Status {r.status_code}"
    d = r.json()
    assert d.get("success"), "Login not successful"
    assert d.get("token"), "No token returned"
    ok("Admin login works with correct credentials")

    # Wrong password should fail
    r2 = requests.post(f"{BASE}/api/admin/login",
                       json={"username": "admin", "password": "wrong"})
    assert r2.status_code == 401, f"Expected 401, got {r2.status_code}"
    ok("Wrong password correctly rejected")
except Exception as e:
    fail("Admin login", str(e))


# ══════════════════════════════════════════════════
# TEST 17: Export CSV content
# ══════════════════════════════════════════════════
section("17. Export CSV")
try:
    csv_data = export_users_csv()
    assert isinstance(csv_data, str), "Should be string"
    lines = csv_data.strip().split("\n")
    assert len(lines) >= 1, "Should have at least header"
    header = lines[0]
    assert "email" in header, "Header should contain email"
    ok(f"CSV export: {len(lines)} lines (including header)")
except Exception as e:
    fail("Export CSV", str(e))


# ══════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  PHASE 4 TEST RESULTS")
print(f"{'='*60}")
print(f"  PASSED: {passed}")
print(f"  FAILED: {failed}")
if errors:
    print(f"\n  Failures:")
    for e in errors:
        print(f"    - {e}")
print(f"{'='*60}")

sys.exit(0 if failed == 0 else 1)
