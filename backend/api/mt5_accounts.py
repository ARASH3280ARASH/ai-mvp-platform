"""
Whilber-AI — MT5 Account Manager
=================================
Manages MT5 account credentials, strategy linking, and signal forwarding.
Credentials are stored encrypted locally.
"""
import os, json, hashlib, base64, time, uuid
from threading import Lock

PROJECT = r"C:\Users\Administrator\Desktop\mvp"
DATA_DIR = os.path.join(PROJECT, "data")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "mt5_accounts.json")
LINKS_FILE = os.path.join(DATA_DIR, "mt5_strategy_links.json")

_lock = Lock()

# Simple encryption (XOR with key) — for local storage only
_KEY = "whilber_mt5_2026_secret"

def _encrypt(text):
    """Simple XOR encryption for local storage."""
    if not text:
        return ""
    key_bytes = _KEY.encode()
    encrypted = bytearray()
    for i, ch in enumerate(text.encode("utf-8")):
        encrypted.append(ch ^ key_bytes[i % len(key_bytes)])
    return base64.b64encode(encrypted).decode()

def _decrypt(encoded):
    """Decrypt XOR encoded text."""
    if not encoded:
        return ""
    try:
        data = base64.b64decode(encoded)
        key_bytes = _KEY.encode()
        decrypted = bytearray()
        for i, b in enumerate(data):
            decrypted.append(b ^ key_bytes[i % len(key_bytes)])
        return decrypted.decode("utf-8")
    except:
        return ""

def _load_accounts():
    with _lock:
        try:
            if os.path.exists(ACCOUNTS_FILE):
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
    return {"accounts": []}

def _save_accounts(data):
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def _load_links():
    with _lock:
        try:
            if os.path.exists(LINKS_FILE):
                with open(LINKS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
    return {"links": []}

def _save_links(data):
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# ═══ PUBLIC API ═══

def get_accounts():
    """Get all accounts (passwords masked)."""
    data = _load_accounts()
    safe = []
    for a in data.get("accounts", []):
        safe.append({
            "id": a["id"],
            "account_number": a["account_number"],
            "server": a["server"],
            "platform": a.get("platform", "mt5"),
            "active": a.get("active", True),
            "linked_strategies": get_linked_strategies(a["id"]),
            "created_at": a.get("created_at", "")
        })
    return safe

def add_account(account_number, password, server, platform="mt5"):
    """Add a new MT5 account."""
    data = _load_accounts()
    # Check duplicate
    for a in data["accounts"]:
        if a["account_number"] == account_number and a["server"] == server:
            return {"ok": False, "error": "This account already exists"}
    
    acc = {
        "id": str(uuid.uuid4())[:8],
        "account_number": account_number,
        "password_enc": _encrypt(password),
        "server": server,
        "platform": platform,
        "active": True,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    data["accounts"].append(acc)
    _save_accounts(data)
    return {"ok": True, "id": acc["id"]}

def toggle_account(account_id):
    """Toggle account active/inactive."""
    data = _load_accounts()
    for a in data["accounts"]:
        if a["id"] == account_id:
            a["active"] = not a.get("active", True)
            _save_accounts(data)
            return {"ok": True, "active": a["active"]}
    return {"ok": False, "error": "Account not found"}

def delete_account(account_id):
    """Delete an account and its links."""
    data = _load_accounts()
    data["accounts"] = [a for a in data["accounts"] if a["id"] != account_id]
    _save_accounts(data)
    # Also remove links
    links = _load_links()
    links["links"] = [l for l in links["links"] if l.get("account_id") != account_id]
    _save_links(links)
    return {"ok": True}

def link_strategy(account_id, strategy_id, symbol, lot_size=0.01, max_risk=50):
    """Link a strategy to an MT5 account."""
    links = _load_links()
    # Check duplicate
    for l in links["links"]:
        if l["account_id"] == account_id and l["strategy_id"] == strategy_id:
            l["lot_size"] = lot_size
            l["max_risk"] = max_risk
            l["active"] = True
            _save_links(links)
            return {"ok": True, "message": "Updated existing link"}
    
    # Generate unique magic number
    magic = int(hashlib.md5(f"{account_id}_{strategy_id}".encode()).hexdigest()[:8], 16) % 900000 + 100000
    
    link = {
        "id": str(uuid.uuid4())[:8],
        "account_id": account_id,
        "strategy_id": strategy_id,
        "symbol": symbol,
        "lot_size": lot_size,
        "max_risk": max_risk,
        "magic_number": magic,
        "active": True,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    links["links"].append(link)
    _save_links(links)
    return {"ok": True, "magic_number": magic}

def get_linked_strategies(account_id):
    """Get strategies linked to an account."""
    links = _load_links()
    return [l["strategy_id"] for l in links["links"] if l.get("account_id") == account_id and l.get("active")]

def get_account_credentials(account_id):
    """Get decrypted credentials (internal use only)."""
    data = _load_accounts()
    for a in data["accounts"]:
        if a["id"] == account_id:
            return {
                "account_number": a["account_number"],
                "password": _decrypt(a.get("password_enc", "")),
                "server": a["server"],
                "platform": a.get("platform", "mt5")
            }
    return None

def should_forward_signal(strategy_id):
    """Check if a signal should be forwarded to any MT5 account."""
    links = _load_links()
    accounts = _load_accounts()
    active_acc_ids = {a["id"] for a in accounts["accounts"] if a.get("active")}
    
    result = []
    for l in links["links"]:
        if l["strategy_id"] == strategy_id and l.get("active") and l["account_id"] in active_acc_ids:
            result.append({
                "account_id": l["account_id"],
                "lot_size": l.get("lot_size", 0.01),
                "max_risk": l.get("max_risk", 50),
                "magic_number": l.get("magic_number", 0)
            })
    return result
