"""
Whilber-AI Strategy Store
============================
Save, load, list, delete user-built strategies.
Storage: strategies.json per user.
"""

import json
import os
from datetime import datetime, timezone
from threading import Lock

from backend.api.strategy_engine import (
    validate_strategy, generate_strategy_id, create_empty_strategy
)

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
STRATEGIES_DIR = os.path.join(PROJECT_DIR, "user_strategies")
os.makedirs(STRATEGIES_DIR, exist_ok=True)

_lock = Lock()


def _user_file(user_email):
    safe = user_email.replace("@", "_at_").replace(".", "_")
    return os.path.join(STRATEGIES_DIR, f"{safe}.json")


def _load_user(user_email):
    fp = _user_file(user_email)
    try:
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"strategies": []}


def _save_user(user_email, data):
    with _lock:
        fp = _user_file(user_email)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def save_strategy(user_email, strategy):
    """Save or update a strategy."""
    valid, errors = validate_strategy(strategy)
    if not valid:
        return {"success": False, "errors": errors}

    data = _load_user(user_email)
    now = datetime.now(timezone.utc).isoformat()

    if strategy.get("id"):
        # Update existing
        found = False
        for i, s in enumerate(data["strategies"]):
            if s["id"] == strategy["id"]:
                strategy["updated_at"] = now
                strategy["created_at"] = s.get("created_at", now)
                data["strategies"][i] = strategy
                found = True
                break
        if not found:
            strategy["updated_at"] = now
            strategy["created_at"] = now
            data["strategies"].insert(0, strategy)
    else:
        # New strategy
        strategy["id"] = generate_strategy_id(strategy.get("name", ""))
        strategy["created_at"] = now
        strategy["updated_at"] = now
        data["strategies"].insert(0, strategy)

    _save_user(user_email, data)
    return {"success": True, "strategy_id": strategy["id"], "strategy": strategy}


def get_strategies(user_email):
    """List all strategies for a user."""
    data = _load_user(user_email)
    return data.get("strategies", [])


def get_strategy(user_email, strategy_id):
    """Get a single strategy."""
    data = _load_user(user_email)
    for s in data["strategies"]:
        if s["id"] == strategy_id:
            return s
    return None


def delete_strategy(user_email, strategy_id):
    """Delete a strategy."""
    data = _load_user(user_email)
    before = len(data["strategies"])
    data["strategies"] = [s for s in data["strategies"] if s["id"] != strategy_id]
    if len(data["strategies"]) < before:
        _save_user(user_email, data)
        return {"success": True}
    return {"success": False, "error": "Strategy not found"}


def duplicate_strategy(user_email, strategy_id):
    """Duplicate a strategy."""
    data = _load_user(user_email)
    for s in data["strategies"]:
        if s["id"] == strategy_id:
            new_s = json.loads(json.dumps(s))
            new_s["id"] = generate_strategy_id(s.get("name", "") + "_copy")
            new_s["name"] = s.get("name", "") + " (کپی)"
            new_s["created_at"] = datetime.now(timezone.utc).isoformat()
            new_s["updated_at"] = new_s["created_at"]
            data["strategies"].insert(0, new_s)
            _save_user(user_email, data)
            return {"success": True, "strategy": new_s}
    return {"success": False, "error": "Strategy not found"}


def export_strategy(user_email, strategy_id):
    """Export strategy as JSON string."""
    s = get_strategy(user_email, strategy_id)
    if not s:
        return {"success": False, "error": "Not found"}
    return {"success": True, "json": json.dumps(s, ensure_ascii=False, indent=2)}


def import_strategy(user_email, json_str):
    """Import strategy from JSON string."""
    try:
        strategy = json.loads(json_str)
        strategy["id"] = ""  # Force new ID
        return save_strategy(user_email, strategy)
    except json.JSONDecodeError:
        return {"success": False, "errors": ["JSON format invalid"]}
