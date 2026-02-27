"""
Whilber-AI — User Manager
============================
Simple JSON-based user registration.
Stores users to users.json in project root.
"""

import json
import os
import hashlib
from datetime import datetime, timezone


USERS_FILE = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "users.json")


def _load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"users": []}
    return {"users": []}


def _save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_user(name, email, phone="", ip=""):
    """Register a new user. Returns dict with success status."""
    if not name or not email:
        return {"success": False, "error": "نام و ایمیل الزامی است"}

    data = _load_users()

    # Check duplicate email
    for u in data["users"]:
        if u.get("email", "").lower() == email.lower():
            return {"success": True, "message": "قبلا ثبت‌نام شده‌اید", "user_id": u["id"]}

    # Create user
    user_id = hashlib.md5(f"{email}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    user = {
        "id": user_id,
        "name": name,
        "email": email.lower(),
        "phone": phone,
        "ip": ip,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_active": datetime.now(timezone.utc).isoformat(),
    }
    data["users"].append(user)
    _save_users(data)

    return {"success": True, "message": "ثبت‌نام موفق", "user_id": user_id}


def check_user(email="", ip=""):
    """Check if user exists by email or IP."""
    data = _load_users()
    for u in data["users"]:
        if email and u.get("email", "").lower() == email.lower():
            return {"registered": True, "user": u}
        if ip and u.get("ip") == ip:
            return {"registered": True, "user": u}
    return {"registered": False}


def update_activity(email):
    """Update last_active timestamp."""
    data = _load_users()
    for u in data["users"]:
        if u.get("email", "").lower() == email.lower():
            u["last_active"] = datetime.now(timezone.utc).isoformat()
            _save_users(data)
            return True
    return False


def get_user_count():
    data = _load_users()
    return len(data.get("users", []))
