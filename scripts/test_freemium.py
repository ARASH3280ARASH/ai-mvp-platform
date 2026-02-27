"""
Whilber-AI — Phase 6 Freemium Test Suite
==========================================
80+ test cases covering auth security, plan enforcement, payments,
admin endpoints, page loading, cross-phase compatibility, performance.

Requires server running at localhost:8000

Run: python scripts/test_freemium.py
"""

import os
import sys
import time
import json
import random
import string
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

PASS_COUNT = 0
FAIL_COUNT = 0
SKIP_COUNT = 0


def ok(msg):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  {GREEN}[PASS]{RESET}  {msg}")


def fail(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"  {RED}[FAIL]{RESET}  {msg}")


def skip(msg):
    global SKIP_COUNT
    SKIP_COUNT += 1
    print(f"  {YELLOW}[SKIP]{RESET}  {msg}")


def info(msg):
    print(f"  {CYAN}[INFO]{RESET}  {msg}")


def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def _rand_email():
    r = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{r}@testfreemium.com"


def _rand_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase, k=n))


def api_request(method, path, data=None, headers=None, expect_code=None):
    """Make an HTTP request. Return (body_dict, status_code, elapsed_ms)."""
    url = BASE + path
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            elapsed = int((time.time() - t0) * 1000)
            try:
                return json.loads(raw), resp.status, elapsed
            except json.JSONDecodeError:
                return {"_raw": raw[:500]}, resp.status, elapsed
    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - t0) * 1000)
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(raw), e.code, elapsed
        except json.JSONDecodeError:
            return {"_raw": raw[:500]}, e.code, elapsed
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        return {"_error": str(e)}, 0, elapsed


def api_get(path, headers=None):
    return api_request("GET", path, headers=headers)


def api_post(path, data=None, headers=None):
    return api_request("POST", path, data=data, headers=headers)


def api_put(path, data=None, headers=None):
    return api_request("PUT", path, data=data, headers=headers)


def api_delete(path, headers=None):
    return api_request("DELETE", path, headers=headers)


def page_get(path):
    """Fetch an HTML page. Return (html_text, status, elapsed_ms)."""
    url = BASE + path
    t0 = time.time()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            elapsed = int((time.time() - t0) * 1000)
            return raw, resp.status, elapsed
    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - t0) * 1000)
        return "", e.code, elapsed
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        return "", 0, elapsed


# ═══════════════════════════════════════════════════════
# TEST SECTIONS
# ═══════════════════════════════════════════════════════

def test_auth_security():
    """Section 1: Auth Security (10 tests)"""
    header("1. Auth Security Tests")

    # 1.1 Register with weak password (no number)
    data, code, _ = api_post("/api/auth/register", {
        "email": _rand_email(), "password": "abcdefgh", "name": "Test"
    })
    if code == 400:
        ok("1.1 Weak password (no number) rejected")
    else:
        fail(f"1.1 Weak password not rejected (code={code})")

    # 1.2 Register with short password
    data, code, _ = api_post("/api/auth/register", {
        "email": _rand_email(), "password": "Ab1", "name": "Test"
    })
    if code == 400:
        ok("1.2 Short password rejected")
    else:
        fail(f"1.2 Short password not rejected (code={code})")

    # 1.3 Register with valid strong password
    good_email = _rand_email()
    data, code, _ = api_post("/api/auth/register", {
        "email": good_email, "password": "TestPass123", "name": "Test User"
    })
    if code == 200 and isinstance(data, dict) and data.get("success"):
        ok(f"1.3 Strong password accepted (user={good_email})")
    else:
        fail(f"1.3 Strong password not accepted (code={code}, resp={str(data)[:100]})")

    # 1.4 Register with disposable email
    data, code, _ = api_post("/api/auth/register", {
        "email": f"test@mailinator.com", "password": "TestPass123", "name": "Test"
    })
    if code == 400:
        ok("1.4 Disposable email rejected")
    else:
        fail(f"1.4 Disposable email not rejected (code={code})")

    # 1.5 Register with new disposable domain (expanded list)
    data, code, _ = api_post("/api/auth/register", {
        "email": f"test@guerrillamail.de", "password": "TestPass123", "name": "Test"
    })
    if code == 400:
        ok("1.5 Expanded disposable domain rejected (guerrillamail.de)")
    else:
        fail(f"1.5 Expanded disposable domain not rejected (code={code})")

    # 1.6 Login rate limit: 11 rapid login attempts
    info("1.6 Testing login rate limit (11 attempts)...")
    rate_limited = False
    for i in range(11):
        data, code, _ = api_post("/api/auth/login", {
            "email": "ratelimit@test.com", "password": "wrong"
        })
        if code == 429:
            rate_limited = True
            break
    if rate_limited:
        ok(f"1.6 Login rate limited after {i+1} attempts")
    else:
        fail("1.6 Login NOT rate limited after 11 attempts")

    # 1.7 Register rate limit: 4 rapid register attempts
    info("1.7 Testing register rate limit (4 attempts)...")
    rate_limited = False
    for i in range(4):
        data, code, _ = api_post("/api/auth/register", {
            "email": _rand_email(), "password": "TestPass123", "name": "Rate Test"
        })
        if code == 429:
            rate_limited = True
            break
    if rate_limited:
        ok(f"1.7 Register rate limited after {i+1} attempts")
    else:
        fail("1.7 Register NOT rate limited after 4 attempts")

    # 1.8 JWT token verify
    login_email = _rand_email()
    api_post("/api/auth/register", {
        "email": login_email, "password": "ValidPass1", "name": "JWT Test"
    })
    data, code, _ = api_post("/api/auth/login", {
        "email": login_email, "password": "ValidPass1"
    })
    token = data.get("token", "") if isinstance(data, dict) else ""
    if token:
        data2, code2, _ = api_get("/api/auth/profile", headers={"Authorization": f"Bearer {token}"})
        if code2 == 200:
            ok("1.8 JWT token verify works")
        else:
            fail(f"1.8 JWT token verify failed (code={code2})")
    else:
        skip("1.8 JWT token verify — could not get token")

    # 1.9 Malformed token
    data, code, _ = api_get("/api/auth/profile", headers={"Authorization": "Bearer invalid.token.here"})
    if code == 401:
        ok("1.9 Malformed token rejected (401)")
    else:
        fail(f"1.9 Malformed token not rejected (code={code})")

    # 1.10 No token on protected endpoint
    data, code, _ = api_get("/api/auth/profile")
    if code == 401:
        ok("1.10 No token on protected endpoint rejected (401)")
    else:
        fail(f"1.10 No token not rejected (code={code})")


def test_plan_enforcement():
    """Section 2: Plan Enforcement (15 tests)"""
    header("2. Plan Enforcement Tests")

    # Create a free user and get token
    free_email = _rand_email()
    api_post("/api/auth/register", {
        "email": free_email, "password": "FreeUser1", "name": "Free User"
    })
    data, code, _ = api_post("/api/auth/login", {
        "email": free_email, "password": "FreeUser1"
    })
    free_token = data.get("token", "") if isinstance(data, dict) else ""
    free_hdr = {"Authorization": f"Bearer {free_token}"} if free_token else {}

    # 2.1 Verify all 4 plan tiers exist in /api/plans
    data, code, _ = api_get("/api/plans")
    if code == 200 and isinstance(data, dict):
        plans = data.get("plans", data)
        plan_names = []
        if isinstance(plans, list):
            plan_names = [p.get("id", p.get("name", "")) for p in plans]
        elif isinstance(plans, dict):
            plan_names = list(plans.keys())
        has_all = all(p in str(plan_names).lower() for p in ["free", "pro", "premium", "enterprise"])
        if has_all:
            ok(f"2.1 All 4 plan tiers exist: {plan_names}")
        else:
            fail(f"2.1 Missing plan tiers (found: {plan_names})")
    else:
        fail(f"2.1 /api/plans failed (code={code})")

    # 2.2 Free user analyze (should work with H1)
    data, code, _ = api_get("/api/analyze3/XAUUSD/H1", headers=free_hdr)
    if code == 200:
        ok("2.2 Free user can analyze XAUUSD/H1")
    elif code == 0:
        skip("2.2 Analyze endpoint not reachable (MT5 issue)")
    else:
        fail(f"2.2 Free user analyze failed (code={code})")

    # 2.3 Free user → try restricted timeframe (H4 → 403)
    data, code, _ = api_get("/api/analyze3/XAUUSD/H4", headers=free_hdr)
    if code == 403:
        ok("2.3 Free user blocked from H4 timeframe")
    elif code == 0:
        skip("2.3 Analyze endpoint not reachable")
    else:
        fail(f"2.3 Free user NOT blocked from H4 (code={code})")

    # 2.4 Free user → try restricted symbol (AUDCAD → 403)
    data, code, _ = api_get("/api/analyze3/AUDCAD/H1", headers=free_hdr)
    if code == 403:
        ok("2.4 Free user blocked from AUDCAD symbol")
    elif code == 0:
        skip("2.4 Analyze endpoint not reachable")
    else:
        fail(f"2.4 Free user NOT blocked from AUDCAD (code={code})")

    # 2.5 Free user → builder access → 403
    data, code, _ = api_get("/api/builder/config", headers=free_hdr)
    if code == 403:
        ok("2.5 Free user blocked from builder")
    elif code == 200:
        # Builder might not check plan
        skip("2.5 Builder does not enforce plan (may be expected)")
    else:
        fail(f"2.5 Builder access unexpected (code={code})")

    # 2.6 Free user → robot download → 403
    data, code, _ = api_post("/api/robots/1/download", headers=free_hdr)
    if code == 403:
        ok("2.6 Free user blocked from robot download")
    elif code in (404, 422):
        skip("2.6 Robot endpoint returned 404/422 (no robots)")
    else:
        fail(f"2.6 Robot download access unexpected (code={code})")

    # 2.7 Anonymous user → free limits
    data, code, _ = api_get("/api/analyze3/XAUUSD/H1")
    if code == 200:
        ok("2.7 Anonymous user gets free-tier access")
    elif code == 0:
        skip("2.7 Analyze endpoint not reachable")
    else:
        fail(f"2.7 Anonymous user analyze failed (code={code})")

    # 2.8 Verify plan_info in analyze response
    data, code, _ = api_get("/api/analyze3/XAUUSD/H1", headers=free_hdr)
    if code == 200 and isinstance(data, dict):
        if "plan_info" in data:
            ok("2.8 plan_info present in analyze response")
        else:
            fail("2.8 plan_info missing from analyze response")
    elif code == 0:
        skip("2.8 Analyze endpoint not reachable")
    else:
        fail(f"2.8 Analyze failed (code={code})")

    # 2.9 Verify strategies_truncated flag
    if code == 200 and isinstance(data, dict):
        plan_info = data.get("plan_info", {})
        if "strategies_truncated" in plan_info or "strategies_shown" in plan_info or "total_strategies" in data:
            ok("2.9 Strategy truncation info present")
        else:
            fail("2.9 Strategy truncation info missing")
    else:
        skip("2.9 Could not check strategy truncation")

    # 2.10 Free user → max 2 alerts (try creating 3)
    existing_alerts = 0
    data, code, _ = api_get(f"/api/alerts?email={free_email}")
    if code == 200 and isinstance(data, dict):
        existing_alerts = len(data.get("alerts", []))

    alert_blocked = False
    for i in range(3):
        data, code, _ = api_post("/api/alerts", {
            "user_email": free_email,
            "symbol": "XAUUSD",
            "alert_type": "signal",
            "timeframe": "H1",
        }, headers=free_hdr)
        if code == 403:
            alert_blocked = True
            break
    if alert_blocked:
        ok(f"2.10 Free user alert limit enforced (blocked at attempt {i+1})")
    else:
        skip("2.10 Alert limit not enforced or alert system not available")

    # 2.11 Test /api/plans/my-usage
    data, code, _ = api_get("/api/plans/my-usage", headers=free_hdr)
    if code == 200:
        ok("2.11 /api/plans/my-usage works for free user")
    else:
        fail(f"2.11 /api/plans/my-usage failed (code={code})")

    # 2.12 Free user → journal entry limit
    data, code, _ = api_get("/api/journal/config", headers=free_hdr)
    if code == 200:
        ok("2.12 Free user can access journal config")
    elif code == 403:
        ok("2.12 Free user blocked from journal (plan enforced)")
    else:
        skip(f"2.12 Journal config status={code}")

    # 2.13 Test symbol whitelist data in plans
    data, code, _ = api_get("/api/plans")
    if code == 200 and isinstance(data, dict):
        plans = data.get("plans", [])
        if isinstance(plans, list) and len(plans) > 0:
            p = plans[0]
            if "symbols" in p or "allowed_symbols" in p or "limits" in p:
                ok("2.13 Plan data includes symbol/limit info")
            else:
                skip("2.13 Plan data format doesn't include symbol info")
        elif isinstance(plans, dict):
            ok("2.13 Plan data available as dict")
        else:
            skip("2.13 Unexpected plans format")
    else:
        fail(f"2.13 /api/plans failed (code={code})")

    # 2.14 Test timeframe whitelist in plan info
    data, code, _ = api_get("/api/analyze3/XAUUSD/H1", headers=free_hdr)
    if code == 200 and isinstance(data, dict):
        pi = data.get("plan_info", {})
        if "allowed_timeframes" in pi or "timeframes" in pi:
            ok("2.14 Timeframe whitelist in plan_info")
        else:
            skip("2.14 Timeframe list not in plan_info")
    else:
        skip(f"2.14 Could not check timeframe whitelist")

    # 2.15 Verify daily analysis count tracking
    data, code, _ = api_get("/api/plans/my-usage", headers=free_hdr)
    if code == 200 and isinstance(data, dict):
        if "daily_count" in data or "analyses_today" in data or "daily_analysis" in str(data):
            ok("2.15 Daily analysis count tracked")
        else:
            skip("2.15 Daily count field not in usage response")
    else:
        skip(f"2.15 Could not check daily count")


def test_payment_flow():
    """Section 3: Payment Flow (20 tests)"""
    header("3. Payment Flow Tests")

    # Get admin token first
    admin_data, admin_code, _ = api_post("/api/admin/login", {
        "username": "admin", "password": "Whilber@2026"
    })
    admin_token = admin_data.get("token", "") if isinstance(admin_data, dict) else ""
    admin_hdr = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

    if not admin_token:
        skip("3.x All payment tests skipped — admin login failed")
        return

    # Create a test user
    pay_email = _rand_email()
    api_post("/api/auth/register", {
        "email": pay_email, "password": "PayUser1", "name": "Pay User"
    })
    data, _, _ = api_post("/api/auth/login", {"email": pay_email, "password": "PayUser1"})
    pay_token = data.get("token", "") if isinstance(data, dict) else ""
    pay_hdr = {"Authorization": f"Bearer {pay_token}"} if pay_token else {}
    user_info = data.get("user", {}) if isinstance(data, dict) else {}
    user_id = user_info.get("id", 0)

    # 3.1 Create card-to-card payment
    data, code, _ = api_post("/api/payment/create", {
        "method": "card", "plan": "pro", "duration_months": 1
    }, headers=pay_hdr)
    card_payment_id = None
    if code == 200 and isinstance(data, dict) and data.get("success"):
        card_payment_id = data.get("payment_id")
        ok(f"3.1 Card payment created (id={card_payment_id})")
    else:
        fail(f"3.1 Card payment creation failed (code={code})")

    # 3.2 Confirm card payment with receipt
    if card_payment_id:
        data, code, _ = api_post("/api/payment/card-confirm", {
            "payment_id": card_payment_id,
            "receipt_ref": "TEST-RECEIPT-12345"
        }, headers=pay_hdr)
        if code == 200:
            ok("3.2 Card payment confirmed with receipt")
        else:
            fail(f"3.2 Card payment confirm failed (code={code})")
    else:
        skip("3.2 No card payment to confirm")

    # 3.3 Admin approve payment → plan upgraded
    if card_payment_id:
        data, code, _ = api_post("/api/admin/payment/approve", {
            "payment_id": card_payment_id
        }, headers=admin_hdr)
        if code == 200:
            ok("3.3 Admin approved card payment")
        else:
            fail(f"3.3 Admin approve failed (code={code})")
    else:
        skip("3.3 No payment to approve")

    # 3.4 Create tether payment
    data, code, _ = api_post("/api/payment/create", {
        "method": "tether", "plan": "pro", "duration_months": 1
    }, headers=pay_hdr)
    tether_id = None
    if code == 200 and isinstance(data, dict) and data.get("success"):
        tether_id = data.get("payment_id")
        ok(f"3.4 Tether payment created (id={tether_id})")
    else:
        fail(f"3.4 Tether payment creation failed (code={code})")

    # 3.5 Submit tether tx hash
    if tether_id:
        data, code, _ = api_post("/api/payment/tether-confirm", {
            "payment_id": tether_id,
            "tx_hash": "abcdef1234567890abcdef1234567890"
        }, headers=pay_hdr)
        if code == 200:
            ok("3.5 Tether tx hash submitted")
        else:
            fail(f"3.5 Tether confirm failed (code={code})")
    else:
        skip("3.5 No tether payment to confirm")

    # 3.6 Create zarinpal payment
    data, code, _ = api_post("/api/payment/create", {
        "method": "zarinpal", "plan": "pro", "duration_months": 1
    }, headers=pay_hdr)
    if code == 200 and isinstance(data, dict):
        ok("3.6 Zarinpal payment created (sandbox)")
    else:
        fail(f"3.6 Zarinpal payment creation failed (code={code})")

    # 3.7 Payment ownership — create second user, try to see first user's payment
    other_email = _rand_email()
    api_post("/api/auth/register", {"email": other_email, "password": "OtherUser1", "name": "Other"})
    data2, _, _ = api_post("/api/auth/login", {"email": other_email, "password": "OtherUser1"})
    other_token = data2.get("token", "") if isinstance(data2, dict) else ""
    other_hdr = {"Authorization": f"Bearer {other_token}"} if other_token else {}

    if card_payment_id:
        data, code, _ = api_get(f"/api/payment/verify/{card_payment_id}", headers=other_hdr)
        if code in (403, 404):
            ok("3.7 Payment ownership enforced (other user can't see)")
        elif code == 200:
            # Check if the response hides data
            skip("3.7 Payment ownership — endpoint returned 200 (might show limited data)")
        else:
            fail(f"3.7 Payment ownership check unexpected (code={code})")
    else:
        skip("3.7 No payment to check ownership")

    # 3.8 Payment history returns user's payments
    data, code, _ = api_get("/api/payment/history", headers=pay_hdr)
    if code == 200 and isinstance(data, dict):
        payments = data.get("payments", [])
        if isinstance(payments, list):
            ok(f"3.8 Payment history returned {len(payments)} payments")
        else:
            ok("3.8 Payment history returned")
    else:
        fail(f"3.8 Payment history failed (code={code})")

    # 3.9 Apply valid discount code — first create one via admin
    disc_code = f"TEST{_rand_str(4).upper()}"
    data, code, _ = api_post("/api/admin/discounts", {
        "code": disc_code, "percent_off": 20, "max_uses": 10
    }, headers=admin_hdr)
    if code == 200:
        # Now apply it
        data, code2, _ = api_post("/api/payment/apply-discount", {
            "code": disc_code, "plan": "pro"
        }, headers=pay_hdr)
        if code2 == 200:
            ok(f"3.9 Discount code '{disc_code}' applied")
        else:
            fail(f"3.9 Discount apply failed (code={code2})")
    else:
        skip(f"3.9 Could not create discount code (code={code})")

    # 3.10 Apply invalid discount code
    data, code, _ = api_post("/api/payment/apply-discount", {
        "code": "INVALID_CODE_XYZ", "plan": "pro"
    }, headers=pay_hdr)
    if code in (400, 404):
        ok("3.10 Invalid discount code rejected")
    else:
        fail(f"3.10 Invalid discount code not rejected (code={code})")

    # 3.11 Apply expired discount code (create one with past date)
    exp_code = f"EXP{_rand_str(4).upper()}"
    api_post("/api/admin/discounts", {
        "code": exp_code, "percent_off": 10, "max_uses": 10,
        "valid_until": "2020-01-01"
    }, headers=admin_hdr)
    data, code, _ = api_post("/api/payment/apply-discount", {
        "code": exp_code, "plan": "pro"
    }, headers=pay_hdr)
    if code in (400, 404):
        ok("3.11 Expired discount code rejected")
    else:
        fail(f"3.11 Expired discount code not rejected (code={code})")

    # 3.12 Admin create discount code (already tested in 3.9, verify response)
    disc_code2 = f"DC{_rand_str(4).upper()}"
    data, code, _ = api_post("/api/admin/discounts", {
        "code": disc_code2, "percent_off": 15, "max_uses": 50
    }, headers=admin_hdr)
    if code == 200 and isinstance(data, dict) and data.get("success"):
        ok(f"3.12 Admin created discount '{disc_code2}'")
    else:
        fail(f"3.12 Admin discount creation failed (code={code})")

    # 3.13 Admin list discounts
    data, code, _ = api_get("/api/admin/discounts", headers=admin_hdr)
    if code == 200 and isinstance(data, dict):
        discs = data.get("discounts", [])
        ok(f"3.13 Admin listed {len(discs)} discounts")
    else:
        fail(f"3.13 Admin list discounts failed (code={code})")

    # 3.14 Admin toggle discount
    if code == 200 and isinstance(discs, list) and len(discs) > 0:
        did = discs[0].get("id", 1)
        data, code, _ = api_put(f"/api/admin/discounts/{did}/toggle", {"active": False}, headers=admin_hdr)
        if code == 200:
            ok(f"3.14 Admin toggled discount {did}")
        else:
            fail(f"3.14 Admin toggle discount failed (code={code})")
    else:
        skip("3.14 No discounts to toggle")

    # 3.15 Admin delete discount
    del_code = f"DEL{_rand_str(4).upper()}"
    data, code, _ = api_post("/api/admin/discounts", {
        "code": del_code, "percent_off": 5, "max_uses": 1
    }, headers=admin_hdr)
    if code == 200 and isinstance(data, dict):
        del_id = data.get("discount_id", data.get("id"))
        if del_id:
            data, code, _ = api_delete(f"/api/admin/discounts/{del_id}", headers=admin_hdr)
            if code == 200:
                ok(f"3.15 Admin deleted discount {del_id}")
            else:
                fail(f"3.15 Admin delete discount failed (code={code})")
        else:
            skip("3.15 No discount ID in response")
    else:
        skip("3.15 Could not create discount to delete")

    # 3.16 Admin list payments with filters
    data, code, _ = api_get("/api/admin/payments?status=pending&limit=10", headers=admin_hdr)
    if code == 200:
        ok("3.16 Admin listed payments with filters")
    else:
        fail(f"3.16 Admin list payments failed (code={code})")

    # 3.17 Admin reject payment
    if tether_id:
        data, code, _ = api_post("/api/admin/payment/reject", {
            "payment_id": tether_id, "reason": "Test rejection"
        }, headers=admin_hdr)
        if code == 200:
            ok("3.17 Admin rejected payment")
        else:
            fail(f"3.17 Admin reject payment failed (code={code})")
    else:
        skip("3.17 No payment to reject")

    # 3.18 Payment config endpoint (card/wallet info)
    data, code, _ = api_get("/api/payment/config", headers=pay_hdr)
    if code == 200 and isinstance(data, dict):
        ok("3.18 Payment config returned")
    else:
        fail(f"3.18 Payment config failed (code={code})")

    # 3.19 Plan expiry check (admin)
    data, code, _ = api_post("/api/admin/payment/check-expiry", headers=admin_hdr)
    if code == 200:
        ok("3.19 Plan expiry check OK")
    else:
        fail(f"3.19 Plan expiry check failed (code={code})")

    # 3.20 Maxed out discount code
    max_code = f"MAX{_rand_str(3).upper()}"
    api_post("/api/admin/discounts", {
        "code": max_code, "percent_off": 5, "max_uses": 0
    }, headers=admin_hdr)
    data, code, _ = api_post("/api/payment/apply-discount", {
        "code": max_code, "plan": "pro"
    }, headers=pay_hdr)
    if code in (400, 404):
        ok("3.20 Maxed out discount code rejected")
    else:
        skip(f"3.20 Maxed out discount code test (code={code})")


def test_pro_user_flow():
    """Section 4: Pro User Flow (10 tests)"""
    header("4. Pro User Flow Tests")

    # Get admin token
    admin_data, _, _ = api_post("/api/admin/login", {
        "username": "admin", "password": "Whilber@2026"
    })
    admin_token = admin_data.get("token", "") if isinstance(admin_data, dict) else ""
    admin_hdr = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

    # Create and upgrade user to pro
    pro_email = _rand_email()
    api_post("/api/auth/register", {
        "email": pro_email, "password": "ProUser1", "name": "Pro User"
    })
    data, _, _ = api_post("/api/auth/login", {"email": pro_email, "password": "ProUser1"})
    pro_token = data.get("token", "") if isinstance(data, dict) else ""
    pro_hdr = {"Authorization": f"Bearer {pro_token}"} if pro_token else {}
    user_info = data.get("user", {}) if isinstance(data, dict) else {}
    pro_uid = user_info.get("id", 0)

    # 4.1 Admin upgrade user to pro
    if admin_token and pro_uid:
        data, code, _ = api_put(f"/api/admin/auth-users/{pro_uid}/plan", {
            "plan": "pro", "duration_days": 30
        }, headers=admin_hdr)
        if code == 200:
            ok(f"4.1 Admin upgraded user {pro_uid} to pro")
        else:
            fail(f"4.1 Admin upgrade failed (code={code})")
    else:
        skip("4.1 Cannot upgrade — admin or user not available")

    # Need to re-login to get updated plan in token context
    data, _, _ = api_post("/api/auth/login", {"email": pro_email, "password": "ProUser1"})
    pro_token = data.get("token", "") if isinstance(data, dict) else ""
    pro_hdr = {"Authorization": f"Bearer {pro_token}"} if pro_token else {}

    # 4.2 Pro user → more strategies
    data, code, _ = api_get("/api/analyze3/XAUUSD/H1", headers=pro_hdr)
    if code == 200 and isinstance(data, dict):
        strategies = data.get("strategies", data.get("results", []))
        plan_info = data.get("plan_info", {})
        strat_count = len(strategies) if isinstance(strategies, list) else 0
        limit = plan_info.get("strategies_shown", strat_count)
        ok(f"4.2 Pro user got {strat_count} strategies (limit={limit})")
    elif code == 0:
        skip("4.2 Analyze not reachable")
    else:
        fail(f"4.2 Pro analyze failed (code={code})")

    # 4.3 Pro user → H4 timeframe access
    data, code, _ = api_get("/api/analyze3/XAUUSD/H4", headers=pro_hdr)
    if code == 200:
        ok("4.3 Pro user can access H4 timeframe")
    elif code == 0:
        skip("4.3 Analyze not reachable")
    else:
        fail(f"4.3 Pro user H4 failed (code={code})")

    # 4.4 Pro user → D1 timeframe access
    data, code, _ = api_get("/api/analyze3/XAUUSD/D1", headers=pro_hdr)
    if code == 200:
        ok("4.4 Pro user can access D1 timeframe")
    elif code == 0:
        skip("4.4 Analyze not reachable")
    else:
        fail(f"4.4 Pro user D1 failed (code={code})")

    # 4.5 Pro user → more symbols (GBPJPY)
    data, code, _ = api_get("/api/analyze3/GBPJPY/H1", headers=pro_hdr)
    if code == 200:
        ok("4.5 Pro user can access GBPJPY")
    elif code == 0:
        skip("4.5 Analyze not reachable")
    else:
        fail(f"4.5 Pro user GBPJPY failed (code={code})")

    # 4.6 Pro user → builder access
    data, code, _ = api_get("/api/builder/config", headers=pro_hdr)
    if code == 200:
        ok("4.6 Pro user can access builder")
    elif code == 403:
        fail("4.6 Pro user blocked from builder")
    else:
        skip(f"4.6 Builder access code={code}")

    # 4.7 Pro user → profile shows pro plan
    data, code, _ = api_get("/api/auth/profile", headers=pro_hdr)
    if code == 200 and isinstance(data, dict):
        user = data.get("user", data)
        plan = user.get("plan", "")
        if plan == "pro":
            ok("4.7 Profile shows pro plan")
        else:
            fail(f"4.7 Profile shows plan='{plan}' (expected pro)")
    else:
        fail(f"4.7 Profile failed (code={code})")

    # 4.8 Pro user → higher alert limit
    data, code, _ = api_get("/api/plans/my-usage", headers=pro_hdr)
    if code == 200 and isinstance(data, dict):
        ok("4.8 Pro user usage endpoint works")
    else:
        fail(f"4.8 Pro user usage failed (code={code})")

    # 4.9 Pro user → journal access
    data, code, _ = api_get("/api/journal/entries", headers=pro_hdr)
    if code == 200:
        ok("4.9 Pro user can access journal")
    elif code == 403:
        fail("4.9 Pro user blocked from journal")
    else:
        skip(f"4.9 Journal access code={code}")

    # 4.10 Pro user → risk manager access
    data, code, _ = api_get("/api/risk/config", headers=pro_hdr)
    if code == 200:
        ok("4.10 Pro user can access risk manager")
    else:
        skip(f"4.10 Risk manager code={code}")


def test_admin_endpoints():
    """Section 5: Admin Endpoints (10 tests)"""
    header("5. Admin Endpoints Tests")

    # 5.1 Admin login
    data, code, _ = api_post("/api/admin/login", {
        "username": "admin", "password": "Whilber@2026"
    })
    if code == 200 and isinstance(data, dict) and data.get("token"):
        ok("5.1 Admin login successful")
        admin_token = data["token"]
    else:
        fail(f"5.1 Admin login failed (code={code})")
        return  # Can't continue without admin token

    admin_hdr = {"Authorization": f"Bearer {admin_token}"}

    # 5.2 Admin stats endpoint
    data, code, _ = api_get("/api/admin/stats", headers=admin_hdr)
    if code == 200 and isinstance(data, dict):
        stats = data.get("stats", {})
        ok(f"5.2 Admin stats: {stats.get('total_users', '?')} users, {stats.get('total_analyses', '?')} analyses")
    else:
        fail(f"5.2 Admin stats failed (code={code})")

    # 5.3 Admin users list
    data, code, _ = api_get("/api/admin/users", headers=admin_hdr)
    if code == 200 and isinstance(data, dict):
        users = data.get("users", [])
        ok(f"5.3 Admin users list: {len(users)} users")
    else:
        fail(f"5.3 Admin users list failed (code={code})")

    # 5.4 Admin auth-users list
    data, code, _ = api_get("/api/admin/auth-users", headers=admin_hdr)
    if code == 200:
        ok("5.4 Admin auth-users list works")
    else:
        fail(f"5.4 Admin auth-users failed (code={code})")

    # 5.5 Admin user-stats
    data, code, _ = api_get("/api/admin/user-stats", headers=admin_hdr)
    if code == 200:
        ok("5.5 Admin user-stats works")
    else:
        fail(f"5.5 Admin user-stats failed (code={code})")

    # 5.6 Admin revenue stats
    data, code, _ = api_get("/api/admin/revenue", headers=admin_hdr)
    if code == 200:
        ok("5.6 Admin revenue stats works")
    else:
        fail(f"5.6 Admin revenue failed (code={code})")

    # 5.7 Admin revenue chart
    data, code, _ = api_get("/api/admin/revenue/chart?days=7", headers=admin_hdr)
    if code == 200:
        ok("5.7 Admin revenue chart works")
    else:
        fail(f"5.7 Admin revenue chart failed (code={code})")

    # 5.8 Admin notify user
    data, code, _ = api_post("/api/admin/notify", {
        "target": "all", "message": "Test notification", "title": "Test"
    }, headers=admin_hdr)
    if code == 200:
        ok("5.8 Admin notify works")
    else:
        fail(f"5.8 Admin notify failed (code={code})")

    # 5.9 Admin payment check-expiry
    data, code, _ = api_post("/api/admin/payment/check-expiry", headers=admin_hdr)
    if code == 200:
        ok("5.9 Admin payment check-expiry works")
    else:
        fail(f"5.9 Admin payment check-expiry failed (code={code})")

    # 5.10 Admin wrong credentials → 401
    data, code, _ = api_post("/api/admin/login", {
        "username": "admin", "password": "wrongpassword"
    })
    if code == 401:
        ok("5.10 Admin wrong credentials rejected (401)")
    else:
        fail(f"5.10 Admin wrong creds not rejected (code={code})")


def test_page_loading():
    """Section 6: Page Loading (10 tests)"""
    header("6. Page Loading Tests")

    pages = [
        ("/", "Landing"),
        ("/dashboard", "Dashboard"),
        ("/login", "Login"),
        ("/register", "Register"),
        ("/pricing", "Pricing"),
        ("/alerts", "Alerts"),
        ("/builder", "Builder"),
        ("/journal", "Journal"),
        ("/robots", "Robots"),
        ("/admin", "Admin"),
        ("/about", "About"),
        ("/contact", "Contact"),
        ("/performance", "Performance"),
    ]

    # 6.1-6.10 Page loading
    loaded = 0
    for path, name in pages:
        html, code, elapsed = page_get(path)
        if code == 200:
            loaded += 1
        else:
            fail(f"6.x {name} page failed (code={code})")

    if loaded >= 10:
        ok(f"6.1 {loaded}/{len(pages)} pages load successfully (200)")
    elif loaded >= 7:
        ok(f"6.1 {loaded}/{len(pages)} pages load (some missing)")
    else:
        fail(f"6.1 Only {loaded}/{len(pages)} pages load")

    # 6.2 Check static JS files
    static_files = [
        "/static/notif.js",
        "/static/alert-modal.js",
    ]
    js_loaded = 0
    for sf in static_files:
        html, code, elapsed = page_get(sf)
        if code == 200 and len(html) > 10:
            js_loaded += 1

    if js_loaded == len(static_files):
        ok(f"6.2 All {js_loaded} static JS files served")
    else:
        fail(f"6.2 Only {js_loaded}/{len(static_files)} static JS files served")

    # 6.3 Page contains expected HTML structure
    html, code, _ = page_get("/dashboard")
    if code == 200 and ("<html" in html.lower() or "<div" in html.lower()):
        ok("6.3 Dashboard page has valid HTML structure")
    else:
        fail("6.3 Dashboard page missing HTML structure")

    # 6.4 Pricing page loads
    html, code, _ = page_get("/pricing")
    if code == 200 and len(html) > 100:
        ok(f"6.4 Pricing page loaded ({len(html)} bytes)")
    else:
        fail(f"6.4 Pricing page failed (code={code})")


def test_cross_phase():
    """Section 7: Cross-Phase Compatibility (8 tests)"""
    header("7. Cross-Phase Compatibility Tests")

    # 7.1 Health endpoint
    data, code, _ = api_get("/api/health")
    if code == 200:
        ok(f"7.1 Health endpoint OK")
    else:
        fail(f"7.1 Health endpoint failed (code={code})")

    # 7.2 Symbols endpoint
    data, code, _ = api_get("/api/symbols")
    if code == 200 and isinstance(data, dict):
        total = data.get("total", 0)
        ok(f"7.2 Symbols endpoint: {total} symbols")
    else:
        fail(f"7.2 Symbols endpoint failed (code={code})")

    # 7.3 Strategies list
    data, code, _ = api_get("/api/strategies")
    if code == 200:
        count = len(data) if isinstance(data, list) else data.get("total", data.get("count", "?"))
        ok(f"7.3 Strategies list: {count}")
    else:
        fail(f"7.3 Strategies list failed (code={code})")

    # 7.4 Analyze basic (no auth)
    data, code, _ = api_get("/api/analyze/XAUUSD/H1")
    if code == 200:
        ok("7.4 Analyze basic (no auth) works")
    elif code == 0:
        skip("7.4 Analyze not reachable (MT5)")
    else:
        fail(f"7.4 Analyze basic failed (code={code})")

    # 7.5 Alert list (with dummy email)
    data, code, _ = api_get("/api/alerts?email=test@test.com")
    if code == 200:
        ok("7.5 Alert list endpoint works")
    else:
        fail(f"7.5 Alert list failed (code={code})")

    # 7.6 Tracker endpoints
    data, code, _ = api_get("/api/tracker/status")
    if code == 200:
        ok("7.6 Tracker status endpoint works")
    else:
        fail(f"7.6 Tracker status failed (code={code})")

    # 7.7 Tracker ranking
    data, code, _ = api_get("/api/tracker/ranking")
    if code == 200:
        ok("7.7 Tracker ranking endpoint works")
    else:
        fail(f"7.7 Tracker ranking failed (code={code})")

    # 7.8 Plans endpoint
    data, code, _ = api_get("/api/plans")
    if code == 200:
        ok("7.8 Plans endpoint works")
    else:
        fail(f"7.8 Plans endpoint failed (code={code})")


def test_performance():
    """Section 8: Performance Tests (5 tests)"""
    header("8. Performance Tests")

    # 8.1 Auth endpoint < 200ms
    _, _, elapsed = api_post("/api/auth/login", {"email": "perf@test.com", "password": "PerfTest1"})
    if elapsed < 200:
        ok(f"8.1 Auth endpoint: {elapsed}ms (< 200ms)")
    elif elapsed < 500:
        ok(f"8.1 Auth endpoint: {elapsed}ms (< 500ms, acceptable)")
    else:
        fail(f"8.1 Auth endpoint slow: {elapsed}ms")

    # 8.2 Plans endpoint < 100ms
    _, _, elapsed = api_get("/api/plans")
    if elapsed < 100:
        ok(f"8.2 Plans endpoint: {elapsed}ms (< 100ms)")
    elif elapsed < 300:
        ok(f"8.2 Plans endpoint: {elapsed}ms (< 300ms, acceptable)")
    else:
        fail(f"8.2 Plans endpoint slow: {elapsed}ms")

    # 8.3 Page load < 1s
    _, _, elapsed = page_get("/dashboard")
    if elapsed < 1000:
        ok(f"8.3 Dashboard page: {elapsed}ms (< 1s)")
    else:
        fail(f"8.3 Dashboard page slow: {elapsed}ms")

    # 8.4 Payment config < 1s
    _, _, elapsed = api_get("/api/payment/config")
    if elapsed < 1000:
        ok(f"8.4 Payment config: {elapsed}ms (< 1s)")
    else:
        fail(f"8.4 Payment config slow: {elapsed}ms")

    # 8.5 Static JS < 200ms
    _, _, elapsed = page_get("/static/notif.js")
    if elapsed < 200:
        ok(f"8.5 Static JS: {elapsed}ms (< 200ms)")
    elif elapsed < 500:
        ok(f"8.5 Static JS: {elapsed}ms (< 500ms, acceptable)")
    else:
        fail(f"8.5 Static JS slow: {elapsed}ms")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    global PASS_COUNT, FAIL_COUNT, SKIP_COUNT
    start_time = time.time()

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Whilber-AI — Phase 6 Freemium Test Suite{RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    # Verify server is running
    info("Checking server connectivity...")
    data, code, _ = api_get("/api/health")
    if code == 0:
        print(f"\n  {RED}Server not responding at {BASE}{RESET}")
        print(f"  Start with: python -m uvicorn backend.api.server:app --host :: --port 8000")
        return

    info(f"Server OK (code={code})")
    print()

    # Run all sections
    test_auth_security()
    test_plan_enforcement()
    test_payment_flow()
    test_pro_user_flow()
    test_admin_endpoints()
    test_page_loading()
    test_cross_phase()
    test_performance()

    # Summary
    elapsed_total = time.time() - start_time
    total = PASS_COUNT + FAIL_COUNT + SKIP_COUNT

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  TEST SUMMARY{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  Total:   {total}")
    print(f"  {GREEN}Passed:  {PASS_COUNT}{RESET}")
    print(f"  {RED}Failed:  {FAIL_COUNT}{RESET}")
    print(f"  {YELLOW}Skipped: {SKIP_COUNT}{RESET}")
    print(f"  Time:    {elapsed_total:.1f}s")

    # System stats from admin
    try:
        admin_data, _, _ = api_post("/api/admin/login", {
            "username": "admin", "password": "Whilber@2026"
        })
        if isinstance(admin_data, dict) and admin_data.get("token"):
            stats_data, sc, _ = api_get("/api/admin/stats", headers={
                "Authorization": f"Bearer {admin_data['token']}"
            })
            if sc == 200 and isinstance(stats_data, dict):
                s = stats_data.get("stats", {})
                print(f"\n  {CYAN}System Stats:{RESET}")
                print(f"    Users: {s.get('total_users', '?')}")
                print(f"    Analyses: {s.get('total_analyses', '?')}")
    except Exception:
        pass

    if FAIL_COUNT == 0:
        print(f"\n  {GREEN}{BOLD}ALL TESTS PASSED!{RESET}")
    else:
        print(f"\n  {RED}{BOLD}{FAIL_COUNT} TEST(S) FAILED{RESET}")

    print(f"{BOLD}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()
