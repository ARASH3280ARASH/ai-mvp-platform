"""
Whilber-AI — Admin Manager (Phase 4)
======================================
Admin-specific backend logic: user management (auth_users),
discount codes, revenue analytics, admin notifications.
"""

import sqlite3
import os
import csv
import io
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


# ═══════════════════════════════════════════════════
# USER MANAGEMENT (auth_users)
# ═══════════════════════════════════════════════════

def get_auth_users(
    limit: int = 50,
    offset: int = 0,
    search: str = "",
    plan_filter: str = "",
    status_filter: str = "",
) -> Dict:
    """Paginated user list from auth_users with filters."""
    conn = _get_db()
    conditions = []
    params = []

    if search:
        conditions.append("(email LIKE ? OR name LIKE ? OR mobile LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])

    if plan_filter:
        conditions.append("plan = ?")
        params.append(plan_filter)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    if status_filter == "active":
        conditions.append(
            "(plan = 'free' OR plan_expires_at IS NULL OR plan_expires_at >= ?)"
        )
        params.append(now_iso)
    elif status_filter == "expired":
        conditions.append(
            "plan != 'free' AND plan_expires_at IS NOT NULL AND plan_expires_at < ?"
        )
        params.append(now_iso)
    elif status_filter == "inactive":
        conditions.append("is_active = 0")

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    # Total count
    total = conn.execute(
        f"SELECT COUNT(*) as cnt FROM auth_users {where}", params
    ).fetchone()["cnt"]

    # Fetch users
    rows = conn.execute(
        f"""SELECT id, email, mobile, name, plan, plan_expires_at,
                   is_active, is_verified, created_at, last_login,
                   daily_analysis_count, daily_analysis_reset_date
            FROM auth_users {where}
            ORDER BY id DESC LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()

    users = []
    for r in rows:
        u = dict(r)
        # Determine effective status
        plan = u["plan"]
        exp = u["plan_expires_at"]
        if not u["is_active"]:
            u["status"] = "inactive"
        elif plan != "free" and exp and exp < now_iso:
            u["status"] = "expired"
        else:
            u["status"] = "active"
        users.append(u)

    conn.close()
    return {"users": users, "total": total}


def get_auth_user_detail(user_id: int) -> Optional[Dict]:
    """Full user detail + payment summary."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM auth_users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return None

    u = dict(row)
    u.pop("password_hash", None)
    u.pop("otp_code", None)
    u.pop("otp_expires_at", None)

    # Payment stats
    pay_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM payments WHERE user_id = ?", (user_id,)
    ).fetchone()["cnt"]

    last_pay = conn.execute(
        "SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()

    u["payment_count"] = pay_count
    u["last_payment"] = dict(last_pay) if last_pay else None

    conn.close()
    return u


def admin_change_plan(user_id: int, plan: str, duration_days: int = 30) -> Dict:
    """Manually set user plan + expiry."""
    valid_plans = ("free", "pro", "premium", "enterprise")
    if plan not in valid_plans:
        return {"success": False, "error": f"Invalid plan. Must be one of {valid_plans}"}

    conn = _get_db()
    row = conn.execute("SELECT id, email FROM auth_users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "User not found"}

    if plan == "free":
        conn.execute(
            "UPDATE auth_users SET plan = 'free', plan_expires_at = NULL WHERE id = ?",
            (user_id,),
        )
    else:
        expires = (datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat()
        conn.execute(
            "UPDATE auth_users SET plan = ?, plan_expires_at = ? WHERE id = ?",
            (plan, expires, user_id),
        )

    conn.commit()
    conn.close()
    logger.info(f"🔧 Admin changed plan for user {user_id} to {plan} ({duration_days} days)")
    return {"success": True, "plan": plan, "duration_days": duration_days}


def admin_toggle_user(user_id: int, active: bool) -> Dict:
    """Enable/disable user account."""
    conn = _get_db()
    row = conn.execute("SELECT id FROM auth_users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "User not found"}

    conn.execute(
        "UPDATE auth_users SET is_active = ? WHERE id = ?",
        (1 if active else 0, user_id),
    )
    conn.commit()
    conn.close()
    logger.info(f"🔧 Admin {'activated' if active else 'deactivated'} user {user_id}")
    return {"success": True, "is_active": active}


def get_user_stats() -> Dict:
    """User statistics: total, per-plan counts, new today/week/month."""
    conn = _get_db()
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    total = conn.execute("SELECT COUNT(*) as cnt FROM auth_users").fetchone()["cnt"]

    plans = {}
    for row in conn.execute(
        "SELECT plan, COUNT(*) as cnt FROM auth_users GROUP BY plan"
    ).fetchall():
        plans[row["plan"]] = row["cnt"]

    new_today = conn.execute(
        "SELECT COUNT(*) as cnt FROM auth_users WHERE created_at >= ?",
        (today,),
    ).fetchone()["cnt"]

    new_week = conn.execute(
        "SELECT COUNT(*) as cnt FROM auth_users WHERE created_at >= ?",
        (week_ago,),
    ).fetchone()["cnt"]

    new_month = conn.execute(
        "SELECT COUNT(*) as cnt FROM auth_users WHERE created_at >= ?",
        (month_ago,),
    ).fetchone()["cnt"]

    conn.close()
    return {
        "total": total,
        "per_plan": plans,
        "new_today": new_today,
        "new_week": new_week,
        "new_month": new_month,
    }


def export_users_csv(plan_filter: str = "") -> str:
    """Export users as CSV string."""
    conn = _get_db()
    if plan_filter:
        rows = conn.execute(
            "SELECT id, email, name, mobile, plan, plan_expires_at, is_active, created_at, last_login FROM auth_users WHERE plan = ? ORDER BY id",
            (plan_filter,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, email, name, mobile, plan, plan_expires_at, is_active, created_at, last_login FROM auth_users ORDER BY id"
        ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "email", "name", "mobile", "plan", "plan_expires_at", "is_active", "created_at", "last_login"])
    for r in rows:
        writer.writerow([r["id"], r["email"], r["name"], r["mobile"], r["plan"], r["plan_expires_at"], r["is_active"], r["created_at"], r["last_login"]])

    return output.getvalue()


# ═══════════════════════════════════════════════════
# DISCOUNT CODES (discount_codes table)
# ═══════════════════════════════════════════════════

def create_discount(
    code: str,
    percent_off: int = 10,
    max_uses: int = 100,
    valid_until: str = "",
) -> Dict:
    """Create a new discount code."""
    code = code.strip().upper()
    if not code:
        return {"success": False, "error": "Code is required"}
    if percent_off < 1 or percent_off > 100:
        return {"success": False, "error": "Percent must be 1-100"}

    conn = _get_db()
    existing = conn.execute(
        "SELECT id FROM discount_codes WHERE code = ?", (code,)
    ).fetchone()
    if existing:
        conn.close()
        return {"success": False, "error": "Code already exists"}

    conn.execute(
        "INSERT INTO discount_codes (code, percent_off, max_uses, valid_until) VALUES (?,?,?,?)",
        (code, percent_off, max_uses, valid_until or None),
    )
    conn.commit()
    new_id = conn.execute(
        "SELECT id FROM discount_codes WHERE code = ?", (code,)
    ).fetchone()["id"]
    conn.close()

    logger.info(f"🏷 Admin created discount code: {code} ({percent_off}%)")
    return {"success": True, "id": new_id, "code": code}


def get_all_discounts() -> List[Dict]:
    """List all discount codes with usage stats."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM discount_codes ORDER BY id DESC"
    ).fetchall()
    conn.close()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    result = []
    for r in rows:
        d = dict(r)
        # Determine if active
        vu = d.get("valid_until")
        if vu and vu < now_iso:
            d["is_active"] = False
        elif d.get("used_count", 0) >= d.get("max_uses", 100):
            d["is_active"] = False
        else:
            d["is_active"] = True
        result.append(d)

    return result


def toggle_discount(code_id: int, active: bool) -> Dict:
    """Enable/disable a discount code by adjusting valid_until."""
    conn = _get_db()
    row = conn.execute("SELECT id FROM discount_codes WHERE id = ?", (code_id,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Discount code not found"}

    if active:
        # Set valid_until to 1 year from now
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        conn.execute(
            "UPDATE discount_codes SET valid_until = ? WHERE id = ?",
            (future, code_id),
        )
    else:
        # Set valid_until to past
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        conn.execute(
            "UPDATE discount_codes SET valid_until = ? WHERE id = ?",
            (past, code_id),
        )

    conn.commit()
    conn.close()
    return {"success": True, "active": active}


def delete_discount(code_id: int) -> Dict:
    """Delete a discount code."""
    conn = _get_db()
    row = conn.execute("SELECT id FROM discount_codes WHERE id = ?", (code_id,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Discount code not found"}

    conn.execute("DELETE FROM discount_codes WHERE id = ?", (code_id,))
    conn.commit()
    conn.close()
    logger.info(f"🏷 Admin deleted discount code id={code_id}")
    return {"success": True}


# ═══════════════════════════════════════════════════
# REVENUE ANALYTICS (payments table)
# ═══════════════════════════════════════════════════

def get_revenue_stats() -> Dict:
    """Revenue stats: today, week, month, all_time + breakdowns."""
    conn = _get_db()
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    def _sum(where_clause, params):
        row = conn.execute(
            f"SELECT COALESCE(SUM(amount_toman), 0) as total FROM payments WHERE status = 'verified' AND {where_clause}",
            params,
        ).fetchone()
        return row["total"]

    today_rev = _sum("verified_at >= ?", (today,))
    week_rev = _sum("verified_at >= ?", (week_ago,))
    month_rev = _sum("verified_at >= ?", (month_ago,))
    all_time = _sum("1=1", ())

    # By plan
    by_plan = {}
    for row in conn.execute(
        "SELECT plan_purchased, COALESCE(SUM(amount_toman), 0) as total FROM payments WHERE status = 'verified' GROUP BY plan_purchased"
    ).fetchall():
        by_plan[row["plan_purchased"]] = row["total"]

    # By method
    by_method = {}
    for row in conn.execute(
        "SELECT method, COALESCE(SUM(amount_toman), 0) as total FROM payments WHERE status = 'verified' GROUP BY method"
    ).fetchall():
        by_method[row["method"]] = row["total"]

    # Total verified payments count
    total_payments = conn.execute(
        "SELECT COUNT(*) as cnt FROM payments WHERE status = 'verified'"
    ).fetchone()["cnt"]

    # Total paying users
    paying_users = conn.execute(
        "SELECT COUNT(DISTINCT user_id) as cnt FROM payments WHERE status = 'verified'"
    ).fetchone()["cnt"]

    # Total active paid users
    now_iso = now.isoformat()
    active_paid = conn.execute(
        "SELECT COUNT(*) as cnt FROM auth_users WHERE plan != 'free' AND (plan_expires_at IS NULL OR plan_expires_at >= ?)",
        (now_iso,),
    ).fetchone()["cnt"]

    # Churned (had paid plan but expired)
    churned = conn.execute(
        "SELECT COUNT(*) as cnt FROM auth_users WHERE plan != 'free' AND plan_expires_at IS NOT NULL AND plan_expires_at < ?",
        (now_iso,),
    ).fetchone()["cnt"]

    # MRR = month revenue
    mrr = month_rev

    # ARPU
    arpu = (all_time / paying_users) if paying_users > 0 else 0

    # Churn rate
    total_ever_paid = paying_users
    churn_rate = (churned / total_ever_paid * 100) if total_ever_paid > 0 else 0

    conn.close()

    return {
        "today": today_rev,
        "week": week_rev,
        "month": month_rev,
        "all_time": all_time,
        "by_plan": by_plan,
        "by_method": by_method,
        "total_payments": total_payments,
        "paying_users": paying_users,
        "active_paid": active_paid,
        "mrr": mrr,
        "arpu": round(arpu),
        "churn_rate": round(churn_rate, 1),
    }


def get_revenue_chart(days: int = 30) -> List[Dict]:
    """Daily revenue for last N days."""
    conn = _get_db()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    rows = conn.execute(
        """SELECT DATE(verified_at) as day, COALESCE(SUM(amount_toman), 0) as total
           FROM payments
           WHERE status = 'verified' AND verified_at >= ?
           GROUP BY DATE(verified_at)
           ORDER BY day""",
        (start,),
    ).fetchall()
    conn.close()

    # Fill in missing days
    chart = {}
    for r in rows:
        if r["day"]:
            chart[r["day"]] = r["total"]

    result = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        result.append({"date": d, "amount": chart.get(d, 0)})

    return result


# ═══════════════════════════════════════════════════
# ADMIN NOTIFICATIONS
# ═══════════════════════════════════════════════════

def admin_send_notification(target: str, message: str, title: str = "اطلاع‌رسانی") -> Dict:
    """Send notification to user(s). Target: email or plan name (pro/premium/enterprise/all)."""
    try:
        from backend.api.alert_manager import add_notification
    except ImportError:
        return {"success": False, "error": "Alert manager not available"}

    if not message.strip():
        return {"success": False, "error": "Message is required"}

    conn = _get_db()

    plan_targets = ("pro", "premium", "enterprise", "all", "free")
    if target.lower() in plan_targets:
        # Send to all users with matching plan
        if target.lower() == "all":
            rows = conn.execute("SELECT email FROM auth_users WHERE is_active = 1").fetchall()
        else:
            rows = conn.execute(
                "SELECT email FROM auth_users WHERE plan = ? AND is_active = 1",
                (target.lower(),),
            ).fetchall()
        conn.close()

        sent = 0
        for r in rows:
            add_notification(
                user_email=r["email"],
                alert_id=f"admin_notify_{sent}",
                title=title,
                body=message,
                icon="📨",
            )
            sent += 1

        logger.info(f"📨 Admin sent notification to {sent} users (target={target})")
        return {"success": True, "sent_count": sent}
    else:
        # Single user by email
        email = target.strip().lower()
        row = conn.execute(
            "SELECT id FROM auth_users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": "User not found"}

        add_notification(
            user_email=email,
            alert_id="admin_notify_single",
            title=title,
            body=message,
            icon="📨",
        )
        logger.info(f"📨 Admin sent notification to {email}")
        return {"success": True, "sent_count": 1}
