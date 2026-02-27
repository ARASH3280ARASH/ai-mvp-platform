"""
Whilber-AI — Payment Manager
==============================
Zarinpal + Tether (USDT TRC20) + Card-to-Card payment processing.
Tables: payments, discount_codes (created by auth_manager).
"""

import sqlite3
import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

from loguru import logger

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
DB_PATH = os.path.join(PROJECT_DIR, "data", "whilber.db")


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ── Schema Enhancement (safe ALTER TABLE) ──────────────────────

def _ensure_columns():
    conn = _get_db()
    cursor = conn.cursor()
    # Add discount_code column if missing
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN discount_code TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # already exists
    # Add zarinpal_authority column if missing
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN zarinpal_authority TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # already exists
    conn.commit()
    conn.close()

_ensure_columns()


# ── Price Config ───────────────────────────────────────────────

# Toman prices come from plans.py PLAN_LIMITS
# USDT prices defined here
USDT_PRICES = {
    "pro":        {"monthly": 3.5,  "yearly": 35.0},
    "premium":    {"monthly": 9.5,  "yearly": 95.0},
    "enterprise": {"monthly": 24.0, "yearly": 240.0},
}


def _get_toman_price(plan: str, duration_months: int) -> int:
    """Get Toman price from plans module."""
    try:
        from backend.api.plans import PLAN_LIMITS
        limits = PLAN_LIMITS.get(plan)
        if not limits:
            return 0
        if duration_months >= 12:
            return limits.get("price_toman_yearly", 0)
        return limits.get("price_toman_monthly", 0)
    except ImportError:
        return 0


def _get_usdt_price(plan: str, duration_months: int) -> float:
    prices = USDT_PRICES.get(plan)
    if not prices:
        return 0.0
    if duration_months >= 12:
        return prices["yearly"]
    return prices["monthly"]


# ── Zarinpal API Helpers ───────────────────────────────────────

def _zarinpal_base():
    try:
        from config.settings import settings
        if settings.ZARINPAL_SANDBOX:
            return "https://sandbox.zarinpal.com"
        return "https://api.zarinpal.com"
    except Exception:
        return "https://sandbox.zarinpal.com"


def _zarinpal_merchant():
    try:
        from config.settings import settings
        return settings.ZARINPAL_MERCHANT_ID
    except Exception:
        return "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"


def _zarinpal_callback():
    try:
        from config.settings import settings
        return settings.ZARINPAL_CALLBACK_URL
    except Exception:
        return "http://localhost:8000/api/payment/zarinpal-callback"


# ── 1. Create Payment ─────────────────────────────────────────

def create_payment(user_id: int, plan: str, duration_months: int,
                   method: str, discount_code: str = "") -> Dict:
    """
    Create a new payment record.
    method: 'zarinpal' | 'tether' | 'card'
    Returns payment_id + method-specific data.
    """
    if plan not in ("pro", "premium", "enterprise"):
        return {"success": False, "error": "پلن نامعتبر است"}
    if method not in ("zarinpal", "tether", "card"):
        return {"success": False, "error": "روش پرداخت نامعتبر است"}
    if duration_months not in (1, 12):
        return {"success": False, "error": "مدت اشتراک نامعتبر است"}

    # Calculate prices
    amount_toman = _get_toman_price(plan, duration_months)
    amount_usdt = _get_usdt_price(plan, duration_months)

    # Apply discount
    discount_pct = 0
    if discount_code:
        disc = apply_discount_code(discount_code)
        if disc["valid"]:
            discount_pct = disc["percent_off"]
            amount_toman = int(amount_toman * (100 - discount_pct) / 100)
            amount_usdt = round(amount_usdt * (100 - discount_pct) / 100, 2)

    conn = _get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO payments
               (user_id, amount_toman, amount_usdt, method, status,
                plan_purchased, duration_months, discount_code)
               VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (user_id, amount_toman, amount_usdt, method, plan,
             duration_months, discount_code)
        )
        conn.commit()
        payment_id = cursor.lastrowid

        # Increment discount usage
        if discount_code and discount_pct > 0:
            conn.execute(
                "UPDATE discount_codes SET used_count = used_count + 1 WHERE code = ?",
                (discount_code,)
            )
            conn.commit()

        result = {
            "success": True,
            "payment_id": payment_id,
            "method": method,
            "amount_toman": amount_toman,
            "amount_usdt": amount_usdt,
            "plan": plan,
            "duration_months": duration_months,
            "discount_applied": discount_pct,
        }

        # Method-specific handling
        if method == "zarinpal":
            zp_result = _zarinpal_request(payment_id, amount_toman, plan)
            if zp_result.get("success"):
                result["redirect_url"] = zp_result["redirect_url"]
                result["authority"] = zp_result["authority"]
            else:
                # Mark payment failed if ZP request fails
                conn.execute(
                    "UPDATE payments SET status='failed', admin_note=? WHERE id=?",
                    (zp_result.get("error", "ZP request failed"), payment_id)
                )
                conn.commit()
                conn.close()
                return {"success": False, "error": zp_result.get("error", "خطا در اتصال به زرین‌پال")}
        elif method == "tether":
            try:
                from config.settings import settings
                result["wallet_address"] = settings.USDT_WALLET_ADDRESS
                result["network"] = settings.USDT_NETWORK
            except Exception:
                result["wallet_address"] = "TYourTRC20WalletAddressHere"
                result["network"] = "TRC20"
            result["instructions"] = f"مبلغ {amount_usdt} USDT را به آدرس کیف پول ارسال کنید"
        elif method == "card":
            try:
                from config.settings import settings
                result["card_number"] = settings.CARD_TO_CARD_NUMBER
                result["card_holder"] = settings.CARD_TO_CARD_HOLDER
                result["bank_name"] = settings.CARD_TO_CARD_BANK
            except Exception:
                result["card_number"] = "6037-xxxx-xxxx-xxxx"
                result["card_holder"] = "نام صاحب حساب"
                result["bank_name"] = "بانک ملی"
            result["instructions"] = f"مبلغ {amount_toman:,} تومان را کارت به کارت کنید"

        conn.close()
        return result
    except Exception as e:
        conn.close()
        logger.error(f"[PAYMENT] create_payment error: {e}")
        return {"success": False, "error": str(e)}


def _zarinpal_request(payment_id: int, amount_toman: int, plan: str) -> Dict:
    """Send payment request to Zarinpal API."""
    try:
        import httpx
    except ImportError:
        return {"success": False, "error": "httpx not installed"}

    base = _zarinpal_base()
    merchant = _zarinpal_merchant()
    callback = _zarinpal_callback()

    from backend.api.plans import PLAN_NAMES_FA
    plan_fa = PLAN_NAMES_FA.get(plan, plan)

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{base}/pg/v4/payment/request.json",
                json={
                    "merchant_id": merchant,
                    "amount": amount_toman,
                    "callback_url": f"{callback}?payment_id={payment_id}",
                    "description": f"خرید اشتراک {plan_fa} ویلبر",
                },
            )
            data = resp.json()
            if data.get("data", {}).get("code") == 100:
                authority = data["data"]["authority"]
                # Store authority in payment record
                conn = _get_db()
                conn.execute(
                    "UPDATE payments SET zarinpal_authority=? WHERE id=?",
                    (authority, payment_id)
                )
                conn.commit()
                conn.close()
                gateway = f"{base}/pg/StartPay/{authority}"
                return {"success": True, "authority": authority, "redirect_url": gateway}
            else:
                err_msg = str(data.get("errors", data))
                return {"success": False, "error": f"Zarinpal error: {err_msg}"}
    except Exception as e:
        logger.error(f"[ZARINPAL] Request error: {e}")
        return {"success": False, "error": str(e)}


# ── 2. Verify Zarinpal Payment ────────────────────────────────

def verify_zarinpal_payment(authority: str, status: str, payment_id: int = 0) -> Dict:
    """Called by Zarinpal callback. Verify payment with ZP API."""
    if status != "OK":
        if payment_id:
            conn = _get_db()
            conn.execute("UPDATE payments SET status='failed' WHERE id=?", (payment_id,))
            conn.commit()
            conn.close()
        return {"success": False, "error": "پرداخت توسط کاربر لغو شد"}

    # Find payment by authority or payment_id
    conn = _get_db()
    if payment_id:
        row = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM payments WHERE zarinpal_authority=? AND status='pending'",
            (authority,)
        ).fetchone()

    if not row:
        conn.close()
        return {"success": False, "error": "پرداخت یافت نشد"}

    payment = dict(row)
    amount = payment["amount_toman"]

    try:
        import httpx
    except ImportError:
        conn.close()
        return {"success": False, "error": "httpx not installed"}

    base = _zarinpal_base()
    merchant = _zarinpal_merchant()

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{base}/pg/v4/payment/verify.json",
                json={
                    "merchant_id": merchant,
                    "amount": amount,
                    "authority": authority,
                },
            )
            data = resp.json()
            code = data.get("data", {}).get("code")
            if code in (100, 101):
                ref_id = data["data"].get("ref_id", "")
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "UPDATE payments SET status='verified', ref_code=?, verified_at=? WHERE id=?",
                    (str(ref_id), now, payment["id"])
                )
                conn.commit()
                # Upgrade user plan
                upgrade_user_plan(
                    payment["user_id"],
                    payment["plan_purchased"],
                    payment["duration_months"]
                )
                conn.close()
                return {
                    "success": True,
                    "payment_id": payment["id"],
                    "ref_id": ref_id,
                    "plan": payment["plan_purchased"],
                }
            else:
                conn.execute("UPDATE payments SET status='failed' WHERE id=?", (payment["id"],))
                conn.commit()
                conn.close()
                return {"success": False, "error": f"تایید پرداخت ناموفق (کد: {code})"}
    except Exception as e:
        conn.close()
        logger.error(f"[ZARINPAL] Verify error: {e}")
        return {"success": False, "error": str(e)}


# ── 3. Confirm Card Payment ───────────────────────────────────

def confirm_card_payment(payment_id: int, user_id: int,
                         ref_number: str, last4_card: str, amount: int) -> Dict:
    """User submits card-to-card receipt info. Sets status='submitted'."""
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM payments WHERE id=? AND user_id=? AND method='card' AND status='pending'",
        (payment_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "پرداخت یافت نشد یا قبلا تایید شده"}

    receipt = json.dumps({
        "ref_number": ref_number,
        "last4_card": last4_card,
        "amount_claimed": amount,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False)

    conn.execute(
        "UPDATE payments SET status='submitted', ref_code=? WHERE id=?",
        (receipt, payment_id)
    )
    conn.commit()
    conn.close()
    logger.info(f"[PAYMENT] Card receipt submitted for payment #{payment_id}")
    return {"success": True, "message": "رسید ارسال شد. منتظر تایید ادمین باشید."}


# ── 4. Submit Tether Payment ──────────────────────────────────

def submit_tether_payment(payment_id: int, user_id: int, tx_hash: str) -> Dict:
    """User submits USDT transaction hash. Sets status='submitted'."""
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM payments WHERE id=? AND user_id=? AND method='tether' AND status='pending'",
        (payment_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "پرداخت یافت نشد یا قبلا تایید شده"}

    receipt = json.dumps({
        "tx_hash": tx_hash,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False)

    conn.execute(
        "UPDATE payments SET status='submitted', ref_code=? WHERE id=?",
        (receipt, payment_id)
    )
    conn.commit()
    conn.close()
    logger.info(f"[PAYMENT] Tether TX submitted for payment #{payment_id}")
    return {"success": True, "message": "هش تراکنش ارسال شد. منتظر تایید ادمین باشید."}


# ── 5. Admin Approve Payment ──────────────────────────────────

def admin_approve_payment(payment_id: int, admin_note: str = "") -> Dict:
    """Admin approves a submitted card/tether payment."""
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM payments WHERE id=? AND status='submitted'",
        (payment_id,)
    ).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "پرداخت یافت نشد یا وضعیت نامعتبر"}

    payment = dict(row)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE payments SET status='verified', verified_at=?, admin_note=? WHERE id=?",
        (now, admin_note, payment_id)
    )
    conn.commit()
    conn.close()

    # Upgrade user plan
    upgrade_user_plan(
        payment["user_id"],
        payment["plan_purchased"],
        payment["duration_months"]
    )

    # Add notification for user
    _add_notification(
        payment["user_id"],
        f"پرداخت شما تایید شد و پلن {payment['plan_purchased']} فعال گردید."
    )

    logger.info(f"[PAYMENT] Admin approved payment #{payment_id}")
    return {"success": True, "message": "پرداخت تایید و پلن کاربر ارتقا یافت"}


# ── 6. Admin Reject Payment ───────────────────────────────────

def admin_reject_payment(payment_id: int, admin_note: str = "") -> Dict:
    """Admin rejects a submitted payment."""
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM payments WHERE id=? AND status='submitted'",
        (payment_id,)
    ).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "پرداخت یافت نشد یا وضعیت نامعتبر"}

    payment = dict(row)
    conn.execute(
        "UPDATE payments SET status='rejected', admin_note=? WHERE id=?",
        (admin_note, payment_id)
    )
    conn.commit()
    conn.close()

    _add_notification(
        payment["user_id"],
        f"پرداخت شما رد شد. {admin_note}" if admin_note else "پرداخت شما رد شد. لطفا با پشتیبانی تماس بگیرید."
    )

    logger.info(f"[PAYMENT] Admin rejected payment #{payment_id}")
    return {"success": True, "message": "پرداخت رد شد"}


# ── 7. Get Payment History ────────────────────────────────────

def get_payment_history(user_id: int, limit: int = 50) -> List[Dict]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── 8. Get Payment By ID ─────────────────────────────────────

def get_payment_by_id(payment_id: int) -> Optional[Dict]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── 9. Apply Discount Code ───────────────────────────────────

def apply_discount_code(code: str) -> Dict:
    """Validate a discount code. Returns {valid, percent_off} or {valid: False, error}."""
    if not code or not code.strip():
        return {"valid": False, "error": "کد تخفیف الزامی است"}

    code = code.strip().upper()
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM discount_codes WHERE code=?", (code,)
    ).fetchone()
    conn.close()

    if not row:
        return {"valid": False, "error": "کد تخفیف نامعتبر است"}

    disc = dict(row)

    # Check expiry
    if disc["valid_until"]:
        try:
            expiry = datetime.fromisoformat(disc["valid_until"])
            if expiry < datetime.now(timezone.utc):
                return {"valid": False, "error": "کد تخفیف منقضی شده است"}
        except ValueError:
            pass

    # Check max uses
    if disc["used_count"] >= disc["max_uses"]:
        return {"valid": False, "error": "کد تخفیف به حداکثر استفاده رسیده"}

    return {
        "valid": True,
        "percent_off": disc["percent_off"],
        "code": disc["code"],
    }


# ── 10. Upgrade User Plan ────────────────────────────────────

def upgrade_user_plan(user_id: int, plan: str, duration_months: int) -> bool:
    """Upgrade user's plan and set expiry date."""
    now = datetime.now(timezone.utc)
    if duration_months >= 12:
        expires = now + timedelta(days=365)
    else:
        expires = now + timedelta(days=30 * duration_months)

    conn = _get_db()
    conn.execute(
        "UPDATE auth_users SET plan=?, plan_expires_at=? WHERE id=?",
        (plan, expires.isoformat(), user_id)
    )
    conn.commit()
    conn.close()
    logger.info(f"[PAYMENT] User #{user_id} upgraded to {plan} until {expires.date()}")
    return True


# ── 11. Check Expired Plans ──────────────────────────────────

def check_expired_plans() -> int:
    """Find expired plans and downgrade to free. Returns count of downgraded users."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, email, plan FROM auth_users WHERE plan != 'free' AND plan_expires_at IS NOT NULL AND plan_expires_at < ?",
        (now,)
    ).fetchall()

    count = 0
    for row in rows:
        user = dict(row)
        conn.execute(
            "UPDATE auth_users SET plan='free', plan_expires_at=NULL WHERE id=?",
            (user["id"],)
        )
        _add_notification_conn(
            conn, user["id"],
            "اشتراک شما منقضی شده و به پلن رایگان تغییر یافت. برای تمدید اقدام کنید."
        )
        count += 1
        logger.info(f"[EXPIRY] User #{user['id']} ({user.get('email','')}) downgraded from {user['plan']} to free")

    if count:
        conn.commit()
    conn.close()
    return count


# ── 12. Get All Payments (Admin) ──────────────────────────────

def get_all_payments_admin(limit: int = 50, offset: int = 0,
                           status_filter: str = "") -> Dict:
    """All payments with user info for admin panel."""
    conn = _get_db()

    where = ""
    params: list = []
    if status_filter:
        where = "WHERE p.status = ?"
        params.append(status_filter)

    rows = conn.execute(
        f"""SELECT p.*, u.email, u.name
            FROM payments p
            LEFT JOIN auth_users u ON p.user_id = u.id
            {where}
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?""",
        params + [limit, offset]
    ).fetchall()

    total_row = conn.execute(
        f"SELECT COUNT(*) as cnt FROM payments p {where}", params
    ).fetchone()
    total = total_row["cnt"] if total_row else 0

    conn.close()
    return {
        "payments": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── 13. Get Payment Config ───────────────────────────────────

def get_payment_config() -> Dict:
    """Return wallet/card info for frontend (no secrets like merchant_id)."""
    try:
        from config.settings import settings
        return {
            "usdt_wallet": settings.USDT_WALLET_ADDRESS,
            "usdt_network": settings.USDT_NETWORK,
            "card_number": settings.CARD_TO_CARD_NUMBER,
            "card_holder": settings.CARD_TO_CARD_HOLDER,
            "card_bank": settings.CARD_TO_CARD_BANK,
            "usdt_prices": USDT_PRICES,
        }
    except Exception:
        return {
            "usdt_wallet": "",
            "usdt_network": "TRC20",
            "card_number": "",
            "card_holder": "",
            "card_bank": "",
            "usdt_prices": USDT_PRICES,
        }


# ── Notification Helper ──────────────────────────────────────

def _add_notification(user_id: int, message: str):
    """Add a notification to the notifications table (if it exists)."""
    try:
        conn = _get_db()
        _add_notification_conn(conn, user_id, message)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"[PAYMENT] Failed to add notification: {e}")


def _add_notification_conn(conn, user_id: int, message: str):
    """Add notification using existing connection (no commit)."""
    try:
        # Get user email for notification
        row = conn.execute("SELECT email FROM auth_users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return
        email = row["email"]
        conn.execute(
            """INSERT INTO notifications (user_email, title, message, type, created_at)
               VALUES (?, ?, ?, 'payment', datetime('now'))""",
            (email, "اطلاعیه پرداخت", message)
        )
    except Exception as e:
        # notifications table may not exist
        logger.debug(f"[PAYMENT] Notification insert skipped: {e}")
