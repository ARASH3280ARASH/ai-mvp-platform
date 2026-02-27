"""
Whilber-AI — Database Module (SQLite) v2
==========================================
Stores: users, analysis logs, admin, settings, support messages.
"""

import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger
import bcrypt as _bcrypt

DB_PATH = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "data", "whilber.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now')),
            is_blocked INTEGER DEFAULT 0,
            notes TEXT DEFAULT ''
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_fp ON users(fingerprint)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_ip ON users(ip_address)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS analysis_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            signal TEXT,
            confidence REAL,
            ip_address TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON analysis_logs(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_logs_time ON analysis_logs(created_at)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Support Messages ───────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT DEFAULT '',
            body TEXT NOT NULL,
            ip_address TEXT,
            is_read INTEGER DEFAULT 0,
            admin_reply TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_support_time ON support_messages(created_at)")

    # ── Trade Executions (shared with bot_server) ─────
    c.execute("""
        CREATE TABLE IF NOT EXISTS trade_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'bot_server',
            ticket INTEGER,
            strategy_id TEXT,
            symbol TEXT,
            direction TEXT,
            entry_price REAL,
            close_price REAL,
            sl_price REAL,
            tp_price REAL,
            lot_size REAL,
            pnl_pips REAL,
            pnl_usd REAL,
            magic INTEGER,
            opened_at TEXT,
            closed_at TEXT,
            be_moved INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_te_ticket ON trade_executions(ticket)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_te_status ON trade_executions(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_te_strategy ON trade_executions(strategy_id)")

    # Default admin (bcrypt)
    existing = c.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    if existing == 0:
        pw_hash = _bcrypt.hashpw("Whilber@2026".encode(), _bcrypt.gensalt()).decode()
        c.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", ("admin", pw_hash))
        logger.info("Default admin created: admin / Whilber@2026")

    defaults = {"site_active": "1", "require_registration": "1",
                "max_daily_analyses": "100", "welcome_message": "به Whilber-AI خوش آمدید!"}
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


# ── Admin ──────────────────────────────────────────────

def verify_admin(username: str, password: str) -> bool:
    conn = get_db()
    row = conn.execute("SELECT id, password_hash FROM admins WHERE username=?", (username,)).fetchone()
    if not row:
        conn.close()
        return False
    stored = row["password_hash"]
    # Support both old SHA256 and new bcrypt
    if stored.startswith("$2"):
        valid = _bcrypt.checkpw(password.encode(), stored.encode())
    else:
        valid = stored == hashlib.sha256(password.encode()).hexdigest()
        if valid:
            # Auto-upgrade to bcrypt
            new_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
            conn.execute("UPDATE admins SET password_hash=? WHERE id=?", (new_hash, row["id"]))
            conn.commit()
    if valid:
        conn.execute("UPDATE admins SET last_login=datetime('now') WHERE id=?", (row["id"],))
        conn.commit()
    conn.close()
    return valid

def change_admin_password(username: str, new_password: str) -> bool:
    conn = get_db()
    pw_hash = _bcrypt.hashpw(new_password.encode(), _bcrypt.gensalt()).decode()
    c = conn.execute("UPDATE admins SET password_hash=? WHERE username=?", (pw_hash, username))
    conn.commit()
    conn.close()
    return c.rowcount > 0


# ── Users ──────────────────────────────────────────────

def check_user_registered(fingerprint: str, ip_address: str) -> Optional[Dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE fingerprint=? OR ip_address=? LIMIT 1", (fingerprint, ip_address)).fetchone()
    conn.close()
    return dict(row) if row else None

def register_user(first_name, last_name, email, phone, fingerprint, ip_address, user_agent="") -> Dict:
    conn = get_db()
    c = conn.execute("INSERT INTO users (first_name,last_name,email,phone,fingerprint,ip_address,user_agent) VALUES (?,?,?,?,?,?,?)",
                     (first_name, last_name, email, phone, fingerprint, ip_address, user_agent))
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id=?", (c.lastrowid,)).fetchone()
    conn.close()
    return dict(row)

def update_user_last_seen(user_id: int):
    conn = get_db()
    conn.execute("UPDATE users SET last_seen=datetime('now') WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users(limit=200, offset=0, search="") -> List[Dict]:
    conn = get_db()
    if search:
        q = f"%{search}%"
        rows = conn.execute("SELECT * FROM users WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (q,q,q,q,limit,offset)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_count() -> int:
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count

def block_user(user_id: int, block: bool = True):
    conn = get_db()
    conn.execute("UPDATE users SET is_blocked=? WHERE id=?", (1 if block else 0, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id: int):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


# ── Analysis Logs ──────────────────────────────────────

def log_analysis(user_id, symbol, timeframe, signal="", confidence=0, ip_address=""):
    conn = get_db()
    conn.execute("INSERT INTO analysis_logs (user_id,symbol,timeframe,signal,confidence,ip_address) VALUES (?,?,?,?,?,?)",
                 (user_id, symbol, timeframe, signal, confidence, ip_address))
    conn.commit()
    conn.close()

def get_analysis_count(days=0) -> int:
    conn = get_db()
    if days > 0:
        count = conn.execute("SELECT COUNT(*) FROM analysis_logs WHERE created_at >= datetime('now', ?)", (f"-{days} days",)).fetchone()[0]
    else:
        count = conn.execute("SELECT COUNT(*) FROM analysis_logs").fetchone()[0]
    conn.close()
    return count

def get_popular_symbols(limit=10) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT symbol, COUNT(*) as cnt, AVG(confidence) as avg_conf FROM analysis_logs GROUP BY symbol ORDER BY cnt DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_recent_analyses(limit=50) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT a.*, u.first_name, u.last_name, u.email FROM analysis_logs a LEFT JOIN users u ON a.user_id=u.id ORDER BY a.created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_hourly_stats(hours=24) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT strftime('%Y-%m-%d %H:00', created_at) as hour, COUNT(*) as cnt FROM analysis_logs WHERE created_at >= datetime('now', ?) GROUP BY hour ORDER BY hour", (f"-{hours} hours",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_daily_stats(days=30) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT DATE(created_at) as day, COUNT(*) as cnt, COUNT(DISTINCT user_id) as unique_users FROM analysis_logs WHERE created_at >= datetime('now', ?) GROUP BY day ORDER BY day", (f"-{days} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Support Messages ──────────────────────────────────

def add_support_message(name, phone, email, subject, body, ip_address="") -> int:
    conn = get_db()
    c = conn.execute("INSERT INTO support_messages (name,phone,email,subject,body,ip_address) VALUES (?,?,?,?,?,?)",
                     (name, phone, email, subject, body, ip_address))
    conn.commit()
    msg_id = c.lastrowid
    conn.close()
    return msg_id

def get_support_messages(limit=100, unread_only=False) -> List[Dict]:
    conn = get_db()
    if unread_only:
        rows = conn.execute("SELECT * FROM support_messages WHERE is_read=0 ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM support_messages ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_unread_count() -> int:
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM support_messages WHERE is_read=0").fetchone()[0]
    conn.close()
    return count

def mark_message_read(msg_id: int):
    conn = get_db()
    conn.execute("UPDATE support_messages SET is_read=1 WHERE id=?", (msg_id,))
    conn.commit()
    conn.close()

def delete_support_message(msg_id: int):
    conn = get_db()
    conn.execute("DELETE FROM support_messages WHERE id=?", (msg_id,))
    conn.commit()
    conn.close()


# ── Settings ──────────────────────────────────────────

def get_setting(key, default="") -> str:
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))", (key, value))
    conn.commit()
    conn.close()

def get_all_settings() -> Dict:
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


# ── Dashboard Stats ───────────────────────────────────

def get_dashboard_stats() -> Dict:
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    today_users = conn.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = DATE('now')").fetchone()[0]
    total_analyses = conn.execute("SELECT COUNT(*) FROM analysis_logs").fetchone()[0]
    today_analyses = conn.execute("SELECT COUNT(*) FROM analysis_logs WHERE DATE(created_at) = DATE('now')").fetchone()[0]
    active_today = conn.execute("SELECT COUNT(DISTINCT user_id) FROM analysis_logs WHERE DATE(created_at) = DATE('now')").fetchone()[0]
    blocked = conn.execute("SELECT COUNT(*) FROM users WHERE is_blocked=1").fetchone()[0]
    unread_msgs = conn.execute("SELECT COUNT(*) FROM support_messages WHERE is_read=0").fetchone()[0]
    total_msgs = conn.execute("SELECT COUNT(*) FROM support_messages").fetchone()[0]
    conn.close()
    return {"total_users": total_users, "today_users": today_users, "total_analyses": total_analyses,
            "today_analyses": today_analyses, "active_today": active_today, "blocked_users": blocked,
            "unread_messages": unread_msgs, "total_messages": total_msgs}


init_db()


# ═══ JWT Token Functions (admin patch) ═══
import hmac as _hmac, base64 as _b64, json as _jj, time as _tt

try:
    from config.settings import settings as _db_settings
    _JWT_SECRET = _db_settings.JWT_SECRET_ADMIN
except Exception:
    _JWT_SECRET = "whilber-ai-admin-2026-secret"
_JWT_EXPIRE = 86400

def create_admin_token(username: str) -> str:
    payload = _jj.dumps({"sub": username, "exp": int(_tt.time()) + _JWT_EXPIRE})
    p64 = _b64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = _hmac.new(_JWT_SECRET.encode(), p64.encode(), "sha256").hexdigest()[:32]
    return f"{p64}.{sig}"

def verify_token(token: str):
    try:
        p64, sig = token.split(".")
        exp = _hmac.new(_JWT_SECRET.encode(), p64.encode(), "sha256").hexdigest()[:32]
        if not _hmac.compare_digest(sig, exp): return None
        pad = 4 - len(p64) % 4
        if pad != 4: p64 += "=" * pad
        pl = _jj.loads(_b64.urlsafe_b64decode(p64))
        if pl.get("exp", 0) < _tt.time(): return None
        return pl.get("sub")
    except: return None
