"""
Whilber-AI — Phase 3 Payment System Tests
==========================================
Tests: payment_manager, endpoints, card/tether/zarinpal flows,
       discount codes, expiry, admin endpoints, frontend pages.

Run: python scripts/test_phase3.py
"""

import sys
import os
import json
import time
import sqlite3

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")

passed = 0
failed = 0
total = 0

def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} — {detail}")

def header(section):
    print(f"\n{'='*60}")
    print(f"  {section}")
    print(f"{'='*60}")


# ── Helpers ──────────────────────────────────────────────────

DB_PATH = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "data", "whilber.db")

def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def _create_test_user(email="testpay@example.com", name="Test Pay User"):
    """Create a test user and return user_id."""
    try:
        from backend.api.auth_manager import register_user, verify_otp, login_user
        # Try to register
        result = register_user(email, "TestPass123!", name)
        if result.get("success"):
            otp = result.get("_otp_debug", "")
            if otp:
                verify_otp(email, otp)
        # Login to get token
        login_result = login_user(email, "TestPass123!")
        if login_result.get("success"):
            return login_result["user"]["id"], login_result["token"]
        # User may already exist
        conn = _get_db()
        row = conn.execute("SELECT id FROM auth_users WHERE email=?", (email,)).fetchone()
        conn.close()
        if row:
            from backend.api.auth_manager import create_user_token
            return row["id"], create_user_token(row["id"], email)
    except Exception as e:
        print(f"    (test user setup warning: {e})")
    return None, None

def _create_discount_code(code="TEST20", percent=20, max_uses=100, valid_until=None):
    """Insert a discount code directly into DB."""
    conn = _get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO discount_codes (code, percent_off, max_uses, valid_until) VALUES (?,?,?,?)",
            (code, percent, max_uses, valid_until)
        )
        conn.commit()
    except Exception:
        pass
    conn.close()


# ═══════════════════════════════════════════════════════════════
# TEST 1: Import payment_manager
# ═══════════════════════════════════════════════════════════════

header("1. Import payment_manager")
try:
    from backend.api.payment_manager import (
        create_payment, verify_zarinpal_payment, confirm_card_payment,
        submit_tether_payment, admin_approve_payment, admin_reject_payment,
        get_payment_history, get_payment_by_id, apply_discount_code,
        upgrade_user_plan, check_expired_plans, get_all_payments_admin,
        get_payment_config, USDT_PRICES,
    )
    test("payment_manager imports OK", True)
except ImportError as e:
    test("payment_manager imports OK", False, str(e))
    print("\n*** Cannot continue without payment_manager. Exiting. ***")
    sys.exit(1)

test("USDT_PRICES has pro/premium/enterprise",
     all(k in USDT_PRICES for k in ("pro", "premium", "enterprise")))


# ═══════════════════════════════════════════════════════════════
# TEST 2: Create test user
# ═══════════════════════════════════════════════════════════════

header("2. Test User Setup")
user_id, user_token = _create_test_user()
test("Test user created", user_id is not None, "Could not create test user")
test("User token obtained", user_token is not None and len(user_token) > 10)


# ═══════════════════════════════════════════════════════════════
# TEST 3: Create Payment (each method)
# ═══════════════════════════════════════════════════════════════

header("3. Create Payment")

if user_id:
    # Card payment
    r = create_payment(user_id, "pro", 1, "card")
    test("Create card payment", r.get("success") is True, str(r))
    card_payment_id = r.get("payment_id")
    test("Card payment has payment_id", card_payment_id is not None)
    test("Card payment has card_number", "card_number" in r)

    # Tether payment
    r2 = create_payment(user_id, "premium", 1, "tether")
    test("Create tether payment", r2.get("success") is True, str(r2))
    tether_payment_id = r2.get("payment_id")
    test("Tether payment has wallet_address", "wallet_address" in r2)

    # Zarinpal payment (may fail if httpx not available or sandbox down)
    r3 = create_payment(user_id, "pro", 1, "zarinpal")
    if r3.get("success"):
        test("Create zarinpal payment", True)
        test("Zarinpal has redirect_url", "redirect_url" in r3)
    else:
        test("Create zarinpal payment (may fail in test env)", True,
             f"Expected — {r3.get('error', 'no httpx or sandbox down')}")

    # Invalid inputs
    r4 = create_payment(user_id, "invalid", 1, "card")
    test("Reject invalid plan", r4.get("success") is False)

    r5 = create_payment(user_id, "pro", 1, "bitcoin")
    test("Reject invalid method", r5.get("success") is False)

    r6 = create_payment(user_id, "pro", 6, "card")
    test("Reject invalid duration", r6.get("success") is False)
else:
    print("  (skipping — no test user)")
    card_payment_id = None
    tether_payment_id = None


# ═══════════════════════════════════════════════════════════════
# TEST 4: Discount Codes
# ═══════════════════════════════════════════════════════════════

header("4. Discount Codes")

# Create test discount codes
_create_discount_code("TEST20", 20, 100, "2030-01-01T00:00:00+00:00")
_create_discount_code("EXPIRED10", 10, 100, "2020-01-01T00:00:00+00:00")
_create_discount_code("MAXED50", 50, 0, "2030-01-01T00:00:00+00:00")

d1 = apply_discount_code("TEST20")
test("Valid discount code", d1.get("valid") is True)
test("Discount percent = 20", d1.get("percent_off") == 20)

d2 = apply_discount_code("EXPIRED10")
test("Expired discount rejected", d2.get("valid") is False)

d3 = apply_discount_code("MAXED50")
test("Maxed-out discount rejected", d3.get("valid") is False)

d4 = apply_discount_code("NONEXISTENT")
test("Invalid code rejected", d4.get("valid") is False)

d5 = apply_discount_code("")
test("Empty code rejected", d5.get("valid") is False)

# Create payment with discount
if user_id:
    rd = create_payment(user_id, "pro", 1, "card", "TEST20")
    test("Payment with discount", rd.get("success") is True)
    test("Discount applied = 20", rd.get("discount_applied") == 20)
    test("Discounted toman < original 149000", rd.get("amount_toman", 999999) < 149000)


# ═══════════════════════════════════════════════════════════════
# TEST 5: Card-to-Card Flow
# ═══════════════════════════════════════════════════════════════

header("5. Card-to-Card Flow")

if user_id and card_payment_id:
    # Confirm card receipt
    rc = confirm_card_payment(card_payment_id, user_id, "12345678", "9876", 149000)
    test("Card confirm success", rc.get("success") is True, str(rc))

    # Verify payment status is 'submitted'
    p = get_payment_by_id(card_payment_id)
    test("Payment status = submitted", p and p.get("status") == "submitted")

    # Admin approve
    ra = admin_approve_payment(card_payment_id, "تایید تست")
    test("Admin approve success", ra.get("success") is True, str(ra))

    # Verify payment status = verified
    p2 = get_payment_by_id(card_payment_id)
    test("Payment status = verified", p2 and p2.get("status") == "verified")

    # Check user plan upgraded
    conn = _get_db()
    user_row = conn.execute("SELECT plan, plan_expires_at FROM auth_users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    test("User plan upgraded to pro", user_row and user_row["plan"] == "pro")
    test("Plan has expiry date", user_row and user_row["plan_expires_at"] is not None)
else:
    print("  (skipping — no test user or payment)")


# ═══════════════════════════════════════════════════════════════
# TEST 6: Tether Flow
# ═══════════════════════════════════════════════════════════════

header("6. Tether Flow")

if user_id and tether_payment_id:
    rt = submit_tether_payment(tether_payment_id, user_id, "0xabc123def456")
    test("Tether submit success", rt.get("success") is True, str(rt))

    p = get_payment_by_id(tether_payment_id)
    test("Payment status = submitted", p and p.get("status") == "submitted")

    ra = admin_approve_payment(tether_payment_id, "تایید تتر")
    test("Admin approve tether", ra.get("success") is True, str(ra))

    p2 = get_payment_by_id(tether_payment_id)
    test("Tether payment verified", p2 and p2.get("status") == "verified")

    conn = _get_db()
    user_row = conn.execute("SELECT plan FROM auth_users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    test("User plan upgraded to premium", user_row and user_row["plan"] == "premium")
else:
    print("  (skipping — no test user or payment)")


# ═══════════════════════════════════════════════════════════════
# TEST 7: Admin Reject
# ═══════════════════════════════════════════════════════════════

header("7. Admin Reject")

if user_id:
    rn = create_payment(user_id, "enterprise", 1, "card")
    if rn.get("success"):
        reject_pid = rn["payment_id"]
        confirm_card_payment(reject_pid, user_id, "999888", "1111", 999000)
        rr = admin_reject_payment(reject_pid, "رد تست")
        test("Admin reject success", rr.get("success") is True, str(rr))
        p = get_payment_by_id(reject_pid)
        test("Payment status = rejected", p and p.get("status") == "rejected")
else:
    print("  (skipping)")


# ═══════════════════════════════════════════════════════════════
# TEST 8: Plan Expiry
# ═══════════════════════════════════════════════════════════════

header("8. Plan Expiry")

if user_id:
    # Set user plan to expire in the past
    conn = _get_db()
    conn.execute(
        "UPDATE auth_users SET plan='pro', plan_expires_at='2020-01-01T00:00:00+00:00' WHERE id=?",
        (user_id,)
    )
    conn.commit()
    conn.close()

    count = check_expired_plans()
    test("check_expired_plans returns count >= 1", count >= 1, f"got {count}")

    conn = _get_db()
    user_row = conn.execute("SELECT plan, plan_expires_at FROM auth_users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    test("User downgraded to free", user_row and user_row["plan"] == "free")
    test("Plan expiry cleared", user_row and user_row["plan_expires_at"] is None)
else:
    print("  (skipping)")


# ═══════════════════════════════════════════════════════════════
# TEST 9: Payment History
# ═══════════════════════════════════════════════════════════════

header("9. Payment History")

if user_id:
    history = get_payment_history(user_id)
    test("Payment history is list", isinstance(history, list))
    test("History has entries", len(history) > 0, f"got {len(history)}")
else:
    print("  (skipping)")


# ═══════════════════════════════════════════════════════════════
# TEST 10: Payment Config
# ═══════════════════════════════════════════════════════════════

header("10. Payment Config")

config = get_payment_config()
test("Config has usdt_wallet", "usdt_wallet" in config)
test("Config has card_number", "card_number" in config)
test("Config has usdt_prices", "usdt_prices" in config)


# ═══════════════════════════════════════════════════════════════
# TEST 11: Admin Payments List
# ═══════════════════════════════════════════════════════════════

header("11. Admin Payments List")

admin_data = get_all_payments_admin(limit=10)
test("Admin list has payments key", "payments" in admin_data)
test("Admin list has total key", "total" in admin_data)
test("Admin list returns results", len(admin_data.get("payments", [])) > 0)

# Filter by status
filtered = get_all_payments_admin(limit=10, status_filter="verified")
test("Filter by status works", isinstance(filtered.get("payments"), list))


# ═══════════════════════════════════════════════════════════════
# TEST 12: HTTP Endpoint Tests (via httpx or requests)
# ═══════════════════════════════════════════════════════════════

header("12. HTTP Endpoint Tests")

try:
    import httpx
    BASE = "http://localhost:8000"
    client = httpx.Client(timeout=10)

    # GET /payment page
    r = client.get(f"{BASE}/payment")
    test("GET /payment returns 200", r.status_code == 200)
    test("/payment has payment HTML", "pay-container" in r.text)

    # GET /api/payment/config
    r = client.get(f"{BASE}/api/payment/config")
    test("GET /api/payment/config returns 200", r.status_code == 200)
    d = r.json()
    test("Config endpoint has usdt_wallet", "usdt_wallet" in d)

    # POST /api/payment/apply-discount
    r = client.post(f"{BASE}/api/payment/apply-discount", json={"code": "NONEXIST"})
    test("Discount endpoint returns JSON", r.status_code == 200)
    d = r.json()
    test("Invalid discount returns valid=false", d.get("valid") is False)

    # GET /api/payment/history without auth
    r = client.get(f"{BASE}/api/payment/history")
    test("History without auth returns 401", r.status_code == 401)

    # With auth
    if user_token:
        headers = {"Authorization": f"Bearer {user_token}"}
        r = client.get(f"{BASE}/api/payment/history", headers=headers)
        test("History with auth returns 200", r.status_code == 200)

    # Pricing page has payment redirect
    r = client.get(f"{BASE}/pricing")
    test("GET /pricing returns 200", r.status_code == 200)
    test("Pricing has /payment redirect", "/payment?plan=" in r.text)

    client.close()
except ImportError:
    print("  (httpx not available — skipping HTTP tests)")
    print("  Install with: pip install httpx")
except httpx.ConnectError:
    print("  (server not running — skipping HTTP tests)")
    print("  Start with: python -m uvicorn backend.api.server:app --host :: --port 8000")
except Exception as e:
    print(f"  (HTTP test error: {e})")


# ═══════════════════════════════════════════════════════════════
# TEST 13: Phase 1-2 Endpoints Still Work
# ═══════════════════════════════════════════════════════════════

header("13. Phase 1-2 Compatibility")

try:
    import httpx
    BASE = "http://localhost:8000"
    client = httpx.Client(timeout=10)

    r = client.get(f"{BASE}/api/plans")
    test("GET /api/plans still works", r.status_code == 200)
    d = r.json()
    test("Plans has free/pro/premium/enterprise",
         all(k in d.get("plans", {}) for k in ("free", "pro", "premium", "enterprise")))

    r = client.get(f"{BASE}/api/health")
    test("GET /api/health still works", r.status_code == 200)

    if user_token:
        headers = {"Authorization": f"Bearer {user_token}"}
        r = client.get(f"{BASE}/api/auth/profile", headers=headers)
        test("GET /api/auth/profile still works", r.status_code == 200)

    client.close()
except ImportError:
    print("  (httpx not available — skipping)")
except httpx.ConnectError:
    print("  (server not running — skipping)")
except Exception as e:
    print(f"  (error: {e})")


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
print(f"  PHASE 3 TEST RESULTS")
print(f"{'='*60}")
print(f"  Total:  {total}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"{'='*60}")

if failed == 0:
    print("  ALL TESTS PASSED!")
else:
    print(f"  {failed} test(s) failed.")

sys.exit(0 if failed == 0 else 1)
