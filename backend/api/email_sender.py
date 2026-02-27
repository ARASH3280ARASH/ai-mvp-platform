"""
Whilber-AI — Email Alert Sender
═══════════════════════════════════
Sends trade alerts via SMTP email.
Supports plain text and HTML format.
"""

import os
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

# ── Config: loaded from .env ──
_smtp_config = None


def _load_config():
    global _smtp_config
    if _smtp_config:
        return _smtp_config
    
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    config = {}
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
    
    _smtp_config = {
        "server": config.get("SMTP_SERVER", ""),
        "port": int(config.get("SMTP_PORT", "587")),
        "email": config.get("SMTP_EMAIL", ""),
        "password": config.get("SMTP_PASSWORD", ""),
        "from_name": config.get("SMTP_FROM_NAME", "Whilber-AI Alerts"),
        "use_tls": config.get("SMTP_USE_TLS", "true").lower() == "true",
    }
    return _smtp_config


def is_configured():
    """Check if SMTP is configured."""
    cfg = _load_config()
    return bool(cfg.get("server") and cfg.get("email") and cfg.get("password"))


EVENT_ICONS = {
    "entry": "🟢", "exit": "🔴",
    "closed_tp": "✅", "closed_sl": "❌",
    "closed_trailing": "🔄", "closed_be": "🟡",
    "be_activated": "🛡️", "trailing_active": "📈",
    "partial_close": "✂️", "near_tp": "🎯", "near_sl": "⚠️",
    "in_profit": "💚", "in_loss": "💔", "recovery": "🔄",
}

EVENT_TITLES = {
    "entry": "سیگنال جدید",
    "closed_tp": "بسته شد — TP",
    "closed_sl": "بسته شد — SL",
    "closed_trailing": "بسته شد — Trailing",
    "closed_be": "بسته شد — Break Even",
    "be_activated": "Break Even فعال",
    "trailing_active": "Trailing فعال",
    "near_tp": "نزدیک TP",
    "near_sl": "نزدیک SL",
}


def send_email(to_addr, event_type, trade_data):
    """Send an alert email."""
    cfg = _load_config()
    if not cfg.get("server"):
        return {"ok": False, "description": "SMTP not configured"}
    
    icon = EVENT_ICONS.get(event_type, "📌")
    title = EVENT_TITLES.get(event_type, event_type)
    symbol = trade_data.get("symbol", "?")
    direction = trade_data.get("direction", "?")
    strategy = trade_data.get("strategy_name", "?")
    
    subject = f"{icon} Whilber Alert — {symbol} {direction} | {title}"
    
    # Build HTML body
    pnl = trade_data.get("pnl_usd", 0)
    pnl_color = "#10b981" if pnl >= 0 else "#ef4444"
    
    html = f"""
    <div style="font-family:Tahoma,Arial,sans-serif;direction:rtl;max-width:500px;margin:0 auto;
                background:#111827;color:#e2e8f0;border-radius:12px;padding:20px;border:1px solid #2d3748;">
        <h2 style="color:#06b6d4;margin:0 0 16px;">{icon} {title}</h2>
        <div style="background:#1a2235;border-radius:8px;padding:12px;margin-bottom:12px;">
            <div style="font-size:18px;font-weight:bold;margin-bottom:8px;">
                {symbol} {'🟩' if direction=='BUY' else '🟥'} {direction}
            </div>
            <div style="font-size:13px;color:#94a3b8;">📊 {strategy}</div>
            <div style="font-size:13px;color:#94a3b8;">⏱ {trade_data.get('timeframe','H1')}</div>
        </div>
        <table style="width:100%;font-size:13px;border-collapse:collapse;">
    """
    
    if trade_data.get("entry_price"):
        html += f'<tr><td style="padding:4px 0;color:#94a3b8;">💰 ورود:</td><td style="text-align:left;">{trade_data["entry_price"]}</td></tr>'
    if trade_data.get("exit_price"):
        html += f'<tr><td style="padding:4px 0;color:#94a3b8;">📍 خروج:</td><td style="text-align:left;">{trade_data["exit_price"]}</td></tr>'
    if trade_data.get("tp1_price"):
        html += f'<tr><td style="padding:4px 0;color:#94a3b8;">🎯 TP:</td><td style="text-align:left;">{trade_data["tp1_price"]}</td></tr>'
    if trade_data.get("sl_price"):
        html += f'<tr><td style="padding:4px 0;color:#94a3b8;">🛑 SL:</td><td style="text-align:left;">{trade_data["sl_price"]}</td></tr>'
    if pnl:
        html += f'<tr><td style="padding:4px 0;color:#94a3b8;">📈 سود:</td><td style="text-align:left;color:{pnl_color};font-weight:bold;">{"+" if pnl>=0 else ""}{pnl}$</td></tr>'
    if trade_data.get("duration_minutes"):
        html += f'<tr><td style="padding:4px 0;color:#94a3b8;">⏱ مدت:</td><td style="text-align:left;">{int(trade_data["duration_minutes"])} دقیقه</td></tr>'
    
    html += f"""
        </table>
        <div style="margin-top:16px;font-size:11px;color:#64748b;border-top:1px solid #2d3748;padding-top:8px;">
            ⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | Whilber-AI
        </div>
    </div>
    """
    
    # Plain text version
    plain = f"{icon} {title} — {symbol} {direction}\n"
    plain += f"استراتژی: {strategy}\n"
    if trade_data.get("entry_price"):
        plain += f"ورود: {trade_data['entry_price']}\n"
    if trade_data.get("exit_price"):
        plain += f"خروج: {trade_data['exit_price']}\n"
    if pnl:
        plain += f"سود: {'+'if pnl>=0 else ''}{pnl}$\n"
    
    # Send
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{cfg['from_name']} <{cfg['email']}>"
        msg["To"] = to_addr
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        
        if cfg["use_tls"]:
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg["server"], cfg["port"]) as server:
                server.starttls(context=context)
                server.login(cfg["email"], cfg["password"])
                server.sendmail(cfg["email"], to_addr, msg.as_string())
        else:
            with smtplib.SMTP_SSL(cfg["server"], cfg["port"]) as server:
                server.login(cfg["email"], cfg["password"])
                server.sendmail(cfg["email"], to_addr, msg.as_string())
        
        return {"ok": True, "channel": "email"}
    
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "description": "SMTP auth failed — check email/password"}
    except smtplib.SMTPConnectError:
        return {"ok": False, "description": f"Cannot connect to {cfg['server']}:{cfg['port']}"}
    except Exception as e:
        return {"ok": False, "description": str(e)[:200]}


def test_connection():
    """Test SMTP connection without sending."""
    cfg = _load_config()
    if not cfg.get("server"):
        return {"ok": False, "description": "SMTP not configured in .env"}
    try:
        if cfg["use_tls"]:
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg["server"], cfg["port"], timeout=10) as server:
                server.starttls(context=context)
                server.login(cfg["email"], cfg["password"])
        else:
            with smtplib.SMTP_SSL(cfg["server"], cfg["port"], timeout=10) as server:
                server.login(cfg["email"], cfg["password"])
        return {"ok": True, "email": cfg["email"]}
    except Exception as e:
        return {"ok": False, "description": str(e)[:200]}
