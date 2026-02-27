"""
Whilber-AI — Auth Manager
==========================
User registration, login, JWT tokens, OTP, plan management.
Tables: auth_users, payments, discount_codes
"""

import sqlite3
import os
import re
import random
import string
import time
import hmac
import base64
import json
from datetime import datetime, timezone
from typing import Optional, Dict

import bcrypt

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
DB_PATH = os.path.join(PROJECT_DIR, "data", "whilber.db")

try:
    from config.settings import settings
    _JWT_SECRET = settings.JWT_SECRET_USER
except Exception:
    _JWT_SECRET = "whilber-ai-user-auth-2026-xK9mQ"
_JWT_EXPIRE = 86400  # 24 hours


# ── Rate Limiting (in-memory, resets on restart) ─────────
_LOGIN_ATTEMPTS = {}    # {ip: [timestamp, ...]}
_REGISTER_ATTEMPTS = {}


def _check_rate_limit(store: dict, ip: str, max_attempts: int, window_secs: int) -> bool:
    """Return True if allowed, False if rate limited."""
    now = time.time()
    attempts = store.get(ip, [])
    attempts = [t for t in attempts if now - t < window_secs]
    store[ip] = attempts
    if len(attempts) >= max_attempts:
        return False
    attempts.append(now)
    store[ip] = attempts
    return True


def check_login_rate(ip: str) -> bool:
    """Allow max 10 login attempts per IP per hour."""
    return _check_rate_limit(_LOGIN_ATTEMPTS, ip, 10, 3600)


def check_register_rate(ip: str) -> bool:
    """Allow max 3 registration attempts per IP per hour."""
    return _check_rate_limit(_REGISTER_ATTEMPTS, ip, 3, 3600)


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_auth_tables():
    conn = _get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            plan TEXT NOT NULL DEFAULT 'free',
            plan_expires_at TEXT DEFAULT NULL,
            is_active INTEGER DEFAULT 1,
            is_verified INTEGER DEFAULT 0,
            otp_code TEXT DEFAULT NULL,
            otp_expires_at TEXT DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT DEFAULT NULL,
            daily_analysis_count INTEGER DEFAULT 0,
            daily_analysis_reset_date TEXT DEFAULT NULL
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_auth_email ON auth_users(email)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_auth_mobile ON auth_users(mobile)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount_toman REAL DEFAULT 0,
            amount_usdt REAL DEFAULT 0,
            method TEXT DEFAULT 'zarinpal',
            status TEXT DEFAULT 'pending',
            plan_purchased TEXT DEFAULT 'pro',
            duration_months INTEGER DEFAULT 1,
            ref_code TEXT DEFAULT '',
            admin_note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            verified_at TEXT DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES auth_users(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS discount_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            percent_off INTEGER DEFAULT 10,
            max_uses INTEGER DEFAULT 100,
            used_count INTEGER DEFAULT 0,
            valid_until TEXT DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Additional indexes for performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_auth_plan ON auth_users(plan)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_auth_plan_expires ON auth_users(plan_expires_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_discount_code ON discount_codes(code)")

    conn.commit()
    conn.close()


# ── Validation ────────────────────────────────────────

def _valid_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))


def _valid_password(pw: str) -> bool:
    if len(pw) < 8:
        return False
    if not re.search(r'[a-zA-Z]', pw):
        return False
    if not re.search(r'[0-9]', pw):
        return False
    return True


_DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "temp-mail.org", "fakeinbox.com", "mailnesia.com", "trashmail.com",
    "10minutemail.com", "guerrillamail.info", "mohmal.com", "dispostable.com",
    "getairmail.com", "maildrop.cc", "nada.email", "tmpmail.net",
    "getnada.com", "emailondeck.com", "crazymailing.com", "discard.email",
    "mailcatch.com", "tempail.com", "temp-mail.io", "mailinator.net",
    "mytemp.email", "tempinbox.com", "incognitomail.com", "burnermail.io",
    "harakirimail.com", "anonbox.net", "mailsac.com", "tmail.com",
    "spamgourmet.com", "guerrillamail.de", "guerrillamail.net",
    "guerrillamail.org", "spam4.me", "trashmail.me", "trashmail.net",
    "wegwerfmail.de", "trash-mail.com", "mailnull.com", "mintemail.com",
    "tempmailer.com", "tempr.email", "tempmailaddress.com",
}


def _is_disposable(email: str) -> bool:
    domain = email.split("@")[-1].lower()
    return domain in _DISPOSABLE_DOMAINS


# ── JWT Tokens ────────────────────────────────────────

def create_user_token(user_id: int, email: str) -> str:
    payload = json.dumps({
        "sub": user_id,
        "email": email,
        "type": "user",
        "exp": int(time.time()) + _JWT_EXPIRE,
    })
    p64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = hmac.new(_JWT_SECRET.encode(), p64.encode(), "sha256").hexdigest()[:32]
    return f"{p64}.{sig}"


def verify_user_token(token: str) -> Optional[Dict]:
    try:
        p64, sig = token.split(".")
        expected = hmac.new(_JWT_SECRET.encode(), p64.encode(), "sha256").hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            return None
        pad = 4 - len(p64) % 4
        if pad != 4:
            p64 += "=" * pad
        payload = json.loads(base64.urlsafe_b64decode(p64))
        if payload.get("exp", 0) < time.time():
            return None
        if payload.get("type") != "user":
            return None
        return payload
    except Exception:
        return None


# ── OTP ───────────────────────────────────────────────

def _generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))


# ── Registration ──────────────────────────────────────

def register_user(email: str, password: str, name: str, mobile: str = "") -> Dict:
    email = email.strip().lower()
    name = name.strip()
    mobile = mobile.strip()

    if not email:
        return {"success": False, "error": "ایمیل الزامی است", "code": "email_required"}
    if not _valid_email(email):
        return {"success": False, "error": "فرمت ایمیل نامعتبر است", "code": "email_invalid"}
    if _is_disposable(email):
        return {"success": False, "error": "ایمیل‌های موقت پذیرفته نمی‌شوند", "code": "email_disposable"}
    if not name:
        return {"success": False, "error": "نام الزامی است", "code": "name_required"}
    if not password:
        return {"success": False, "error": "رمز عبور الزامی است", "code": "password_required"}
    if not _valid_password(password):
        return {"success": False, "error": "رمز عبور باید حداقل ۸ کاراکتر، شامل حداقل یک حرف و یک عدد باشد", "code": "password_weak"}

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    otp = _generate_otp()
    otp_exp = datetime.now(timezone.utc).isoformat()  # 5 min from now handled at verify

    conn = _get_db()
    try:
        existing = conn.execute("SELECT id FROM auth_users WHERE email=?", (email,)).fetchone()
        if existing:
            conn.close()
            return {"success": False, "error": "این ایمیل قبلا ثبت‌نام شده", "code": "email_exists"}

        conn.execute(
            "INSERT INTO auth_users (email, password_hash, name, mobile, otp_code, otp_expires_at) VALUES (?,?,?,?,?,?)",
            (email, pw_hash, name, mobile, otp, otp_exp)
        )
        conn.commit()
        user_id = conn.execute("SELECT id FROM auth_users WHERE email=?", (email,)).fetchone()["id"]
        conn.close()

        return {
            "success": True,
            "user_id": user_id,
            "otp_sent": True,
            "message": "ثبت‌نام موفق. کد تایید ارسال شد.",
            "_otp_debug": otp,  # Remove in production — for testing only
        }
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "این ایمیل قبلا ثبت‌نام شده", "code": "email_exists"}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e), "code": "server_error"}


# ── OTP Verification ─────────────────────────────────

def verify_otp(email: str, otp_code: str) -> Dict:
    email = email.strip().lower()
    conn = _get_db()
    row = conn.execute("SELECT id, otp_code, is_verified FROM auth_users WHERE email=?", (email,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "کاربر یافت نشد"}
    if row["is_verified"]:
        conn.close()
        return {"success": True, "message": "ایمیل قبلا تایید شده"}
    if row["otp_code"] != otp_code:
        conn.close()
        return {"success": False, "error": "کد تایید اشتباه است"}

    conn.execute("UPDATE auth_users SET is_verified=1, otp_code=NULL WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    return {"success": True, "message": "ایمیل با موفقیت تایید شد"}


# ── Login ─────────────────────────────────────────────

def login_user(email: str, password: str) -> Dict:
    email = email.strip().lower()

    if not email or not password:
        return {"success": False, "error": "ایمیل و رمز عبور الزامی است", "code": "missing_fields"}

    conn = _get_db()
    row = conn.execute("SELECT * FROM auth_users WHERE email=?", (email,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "ایمیل یا رمز عبور اشتباه است", "code": "invalid_credentials"}

    user = dict(row)
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        conn.close()
        return {"success": False, "error": "ایمیل یا رمز عبور اشتباه است", "code": "invalid_credentials"}

    if not user["is_active"]:
        conn.close()
        return {"success": False, "error": "حساب شما غیرفعال شده است", "code": "account_disabled"}

    conn.execute("UPDATE auth_users SET last_login=datetime('now') WHERE id=?", (user["id"],))
    conn.commit()
    conn.close()

    token = create_user_token(user["id"], user["email"])

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "mobile": user["mobile"],
            "plan": user["plan"],
            "plan_expires_at": user["plan_expires_at"],
            "is_verified": bool(user["is_verified"]),
            "created_at": user["created_at"],
        },
    }


# ── Profile ───────────────────────────────────────────

def get_user_profile(user_id: int) -> Optional[Dict]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM auth_users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    u = dict(row)
    return {
        "id": u["id"],
        "email": u["email"],
        "name": u["name"],
        "mobile": u["mobile"],
        "plan": u["plan"],
        "plan_expires_at": u["plan_expires_at"],
        "is_active": bool(u["is_active"]),
        "is_verified": bool(u["is_verified"]),
        "created_at": u["created_at"],
        "last_login": u["last_login"],
        "daily_analysis_count": u["daily_analysis_count"],
        "daily_analysis_reset_date": u["daily_analysis_reset_date"],
    }


# ── Daily Analysis Tracking ──────────────────────────

def get_daily_analysis_count(user_id: int) -> int:
    """Return today's analysis count for user. Resets if new day."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _get_db()
    row = conn.execute(
        "SELECT daily_analysis_count, daily_analysis_reset_date FROM auth_users WHERE id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return 0
    if row["daily_analysis_reset_date"] != today:
        return 0
    return row["daily_analysis_count"] or 0


def increment_daily_analysis(user_id: int) -> int:
    """Increment daily analysis count. Resets if new day. Returns new count."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _get_db()
    row = conn.execute(
        "SELECT daily_analysis_count, daily_analysis_reset_date FROM auth_users WHERE id=?",
        (user_id,)
    ).fetchone()
    if not row:
        conn.close()
        return 0
    if row["daily_analysis_reset_date"] != today:
        new_count = 1
        conn.execute(
            "UPDATE auth_users SET daily_analysis_count=1, daily_analysis_reset_date=? WHERE id=?",
            (today, user_id)
        )
    else:
        new_count = (row["daily_analysis_count"] or 0) + 1
        conn.execute(
            "UPDATE auth_users SET daily_analysis_count=? WHERE id=?",
            (new_count, user_id)
        )
    conn.commit()
    conn.close()
    return new_count


# ── Initialize ────────────────────────────────────────
init_auth_tables()
