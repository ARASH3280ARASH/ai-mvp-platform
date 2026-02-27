"""
Whilber-AI — Risk Management Engine
========================================
Complete risk/money/trade management calculations.
Supports Forex, Gold, Crypto, Indices with market-specific rules.
Generates post-trade reports with lessons.
"""

import json
import os
import math
from datetime import datetime, timezone
from threading import Lock

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
PROFILES_DIR = os.path.join(PROJECT_DIR, "risk_profiles")
os.makedirs(PROFILES_DIR, exist_ok=True)
_lock = Lock()

# ══════ MARKET SPECIFICATIONS ══════

MARKET_SPECS = {
    "XAUUSD": {
        "type": "metals", "name_fa": "طلا", "pip": 0.1, "pip_digits": 1,
        "contract": 100, "tick_value_per_lot": 1.0,
        "avg_spread": 3.0, "avg_atr_h1": 12.0,
        "sessions": ["london", "newyork"],
        "swap_long": -5.2, "swap_short": 1.8,
        "min_sl_pips": 30, "recommended_sl_pips": 80,
        "notes_fa": "طلا نوسان بالایی دارد. SL باید حداقل ۳۰ پیپ و ترجیحاً ۸۰+ پیپ باشد. حجم را کمتر بگیرید.",
    },
    "EURUSD": {
        "type": "forex", "name_fa": "یورو/دلار", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 1.2, "avg_atr_h1": 0.0008,
        "sessions": ["london", "newyork"],
        "swap_long": -6.5, "swap_short": 2.1,
        "min_sl_pips": 10, "recommended_sl_pips": 25,
        "notes_fa": "جفت ارز اصلی با نقدینگی بالا. اسپرد پایین. مناسب برای اسکالپ و سوینگ.",
    },
    "GBPUSD": {
        "type": "forex", "name_fa": "پوند/دلار", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 1.5, "avg_atr_h1": 0.0012,
        "sessions": ["london", "newyork"],
        "swap_long": -4.8, "swap_short": 1.5,
        "min_sl_pips": 15, "recommended_sl_pips": 30,
        "notes_fa": "نوسان بیشتر از EURUSD. مراقب اخبار انگلستان باشید.",
    },
    "USDJPY": {
        "type": "forex", "name_fa": "دلار/ین", "pip": 0.01, "pip_digits": 2,
        "contract": 100000, "tick_value_per_lot": 6.5,
        "avg_spread": 1.3, "avg_atr_h1": 0.12,
        "sessions": ["tokyo", "newyork"],
        "swap_long": 3.2, "swap_short": -8.1,
        "min_sl_pips": 12, "recommended_sl_pips": 25,
        "notes_fa": "حساس به نرخ بهره ژاپن و آمریکا. سشن توکیو فعال‌تر است.",
    },
    "BTCUSD": {
        "type": "crypto", "name_fa": "بیت‌کوین", "pip": 1.0, "pip_digits": 0,
        "contract": 1, "tick_value_per_lot": 1.0,
        "avg_spread": 30.0, "avg_atr_h1": 500.0,
        "sessions": ["24/7"],
        "swap_long": -15.0, "swap_short": -15.0,
        "min_sl_pips": 200, "recommended_sl_pips": 800,
        "notes_fa": "بازار ۲۴ ساعته. نوسان بسیار بالا. حجم را خیلی کم بگیرید. SL بزرگ الزامی است.",
    },
    "US30": {
        "type": "indices", "name_fa": "داوجونز", "pip": 1.0, "pip_digits": 0,
        "contract": 1, "tick_value_per_lot": 1.0,
        "avg_spread": 3.0, "avg_atr_h1": 80.0,
        "sessions": ["newyork"],
        "swap_long": -8.0, "swap_short": -3.0,
        "min_sl_pips": 30, "recommended_sl_pips": 100,
        "notes_fa": "گپ آخر هفته دارد. سشن نیویورک فعال‌تر است. مراقب اخبار اقتصادی آمریکا باشید.",
    },
    "NAS100": {
        "type": "indices", "name_fa": "نزدک", "pip": 1.0, "pip_digits": 0,
        "contract": 1, "tick_value_per_lot": 1.0,
        "avg_spread": 2.5, "avg_atr_h1": 60.0,
        "sessions": ["newyork"],
        "swap_long": -10.0, "swap_short": -4.0,
        "min_sl_pips": 25, "recommended_sl_pips": 80,
        "notes_fa": "حساس به سهام تکنولوژی. نوسان بالا در زمان گزارش درآمد شرکت‌ها.",
    },
    "XAGUSD": {
        "type": "metals", "name_fa": "نقره", "pip": 0.01, "pip_digits": 2,
        "contract": 5000, "tick_value_per_lot": 50.0,
        "avg_spread": 3.5, "avg_atr_h1": 0.15,
        "sessions": ["london", "newyork"],
        "swap_long": -4.0, "swap_short": 0.5,
        "min_sl_pips": 20, "recommended_sl_pips": 50,
        "notes_fa": "نوسان بیشتر از طلا نسبت به قیمت. حجم کمتر بگیرید.",
    },
    # ── Forex Majors (4 new) ──
    "USDCHF": {
        "type": "forex", "name_fa": "دلار/فرانک", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 1.4, "avg_atr_h1": 0.0007,
        "sessions": ["london", "newyork"],
        "swap_long": 3.5, "swap_short": -7.2,
        "min_sl_pips": 10, "recommended_sl_pips": 25,
        "notes_fa": "حساس به نرخ بهره سوئیس. همبستگی معکوس با EURUSD.",
    },
    "AUDUSD": {
        "type": "forex", "name_fa": "دلار استرالیا/دلار", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 1.4, "avg_atr_h1": 0.0007,
        "sessions": ["sydney", "tokyo", "london"],
        "swap_long": -3.5, "swap_short": 1.0,
        "min_sl_pips": 10, "recommended_sl_pips": 25,
        "notes_fa": "حساس به قیمت کالاها و اقتصاد چین. سشن سیدنی فعال‌تر.",
    },
    "NZDUSD": {
        "type": "forex", "name_fa": "دلار نیوزیلند/دلار", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 1.8, "avg_atr_h1": 0.0006,
        "sessions": ["sydney", "tokyo", "london"],
        "swap_long": -2.8, "swap_short": 0.5,
        "min_sl_pips": 10, "recommended_sl_pips": 25,
        "notes_fa": "نقدینگی کمتر از AUD. حساس به لبنیات و کالاهای نیوزیلند.",
    },
    "USDCAD": {
        "type": "forex", "name_fa": "دلار/دلار کانادا", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 1.6, "avg_atr_h1": 0.0007,
        "sessions": ["london", "newyork"],
        "swap_long": -2.0, "swap_short": -1.5,
        "min_sl_pips": 10, "recommended_sl_pips": 25,
        "notes_fa": "حساس به قیمت نفت. سشن نیویورک فعال‌تر.",
    },
    # ── Forex Minors (10 new) ──
    "EURGBP": {
        "type": "forex", "name_fa": "یورو/پوند", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 1.5, "avg_atr_h1": 0.0006,
        "sessions": ["london"],
        "swap_long": -4.0, "swap_short": 1.2,
        "min_sl_pips": 10, "recommended_sl_pips": 20,
        "notes_fa": "رنج‌محور. مناسب اسکالپ در سشن لندن. حساس به اخبار انگلستان و اروپا.",
    },
    "EURJPY": {
        "type": "forex", "name_fa": "یورو/ین", "pip": 0.01, "pip_digits": 2,
        "contract": 100000, "tick_value_per_lot": 6.5,
        "avg_spread": 1.8, "avg_atr_h1": 0.15,
        "sessions": ["tokyo", "london"],
        "swap_long": 1.5, "swap_short": -6.0,
        "min_sl_pips": 15, "recommended_sl_pips": 30,
        "notes_fa": "نوسان بالا. ترکیب حساسیت یورو و ین. سشن لندن-توکیو فعال‌تر.",
    },
    "GBPJPY": {
        "type": "forex", "name_fa": "پوند/ین", "pip": 0.01, "pip_digits": 2,
        "contract": 100000, "tick_value_per_lot": 6.5,
        "avg_spread": 2.5, "avg_atr_h1": 0.20,
        "sessions": ["tokyo", "london"],
        "swap_long": 2.0, "swap_short": -8.5,
        "min_sl_pips": 20, "recommended_sl_pips": 40,
        "notes_fa": "نوسان بسیار بالا — لقب: اژدها. SL بزرگتر و حجم کمتر بگیرید.",
    },
    "EURAUD": {
        "type": "forex", "name_fa": "یورو/دلار استرالیا", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 2.2, "avg_atr_h1": 0.0010,
        "sessions": ["sydney", "london"],
        "swap_long": -5.0, "swap_short": 1.5,
        "min_sl_pips": 15, "recommended_sl_pips": 30,
        "notes_fa": "نوسان متوسط. حساس به تفاوت نرخ بهره اروپا و استرالیا.",
    },
    "EURCAD": {
        "type": "forex", "name_fa": "یورو/دلار کانادا", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 2.4, "avg_atr_h1": 0.0009,
        "sessions": ["london", "newyork"],
        "swap_long": -6.0, "swap_short": 1.8,
        "min_sl_pips": 12, "recommended_sl_pips": 28,
        "notes_fa": "حساس به نفت و اخبار اروپا. اسپرد بیشتر از جفت‌های اصلی.",
    },
    "EURCHF": {
        "type": "forex", "name_fa": "یورو/فرانک", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 1.8, "avg_atr_h1": 0.0005,
        "sessions": ["london"],
        "swap_long": -1.0, "swap_short": -2.5,
        "min_sl_pips": 10, "recommended_sl_pips": 20,
        "notes_fa": "کم‌نوسان‌ترین جفت ارز. مناسب معاملات محافظه‌کارانه.",
    },
    "GBPAUD": {
        "type": "forex", "name_fa": "پوند/دلار استرالیا", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 3.0, "avg_atr_h1": 0.0014,
        "sessions": ["sydney", "london"],
        "swap_long": -3.5, "swap_short": 0.8,
        "min_sl_pips": 20, "recommended_sl_pips": 40,
        "notes_fa": "نوسان بالا. اسپرد زیاد. فقط در سشن لندن ترید کنید.",
    },
    "GBPCAD": {
        "type": "forex", "name_fa": "پوند/دلار کانادا", "pip": 0.0001, "pip_digits": 4,
        "contract": 100000, "tick_value_per_lot": 10.0,
        "avg_spread": 2.8, "avg_atr_h1": 0.0012,
        "sessions": ["london", "newyork"],
        "swap_long": -3.0, "swap_short": 0.5,
        "min_sl_pips": 18, "recommended_sl_pips": 35,
        "notes_fa": "حساس به نفت و اخبار انگلستان. اسپرد نسبتاً بالا.",
    },
    "AUDJPY": {
        "type": "forex", "name_fa": "دلار استرالیا/ین", "pip": 0.01, "pip_digits": 2,
        "contract": 100000, "tick_value_per_lot": 6.5,
        "avg_spread": 2.0, "avg_atr_h1": 0.12,
        "sessions": ["sydney", "tokyo"],
        "swap_long": 1.0, "swap_short": -5.0,
        "min_sl_pips": 12, "recommended_sl_pips": 25,
        "notes_fa": "شاخص ریسک‌پذیری بازار. در زمان بحران سقوط می‌کند.",
    },
    "CADJPY": {
        "type": "forex", "name_fa": "دلار کانادا/ین", "pip": 0.01, "pip_digits": 2,
        "contract": 100000, "tick_value_per_lot": 6.5,
        "avg_spread": 2.2, "avg_atr_h1": 0.11,
        "sessions": ["tokyo", "newyork"],
        "swap_long": 1.5, "swap_short": -5.5,
        "min_sl_pips": 12, "recommended_sl_pips": 25,
        "notes_fa": "حساس به نفت و نرخ بهره ژاپن. سشن نیویورک فعال‌تر.",
    },
    # ── Crypto (2 new) ──
    "ETHUSD": {
        "type": "crypto", "name_fa": "اتریوم", "pip": 0.1, "pip_digits": 1,
        "contract": 1, "tick_value_per_lot": 1.0,
        "avg_spread": 5.0, "avg_atr_h1": 30.0,
        "sessions": ["24/7"],
        "swap_long": -12.0, "swap_short": -12.0,
        "min_sl_pips": 100, "recommended_sl_pips": 400,
        "notes_fa": "بازار ۲۴ ساعته. نوسان بالا. حساس به آپدیت‌های شبکه و DeFi.",
    },
    "SOLUSD": {
        "type": "crypto", "name_fa": "سولانا", "pip": 0.01, "pip_digits": 2,
        "contract": 1, "tick_value_per_lot": 1.0,
        "avg_spread": 1.0, "avg_atr_h1": 3.0,
        "sessions": ["24/7"],
        "swap_long": -10.0, "swap_short": -10.0,
        "min_sl_pips": 50, "recommended_sl_pips": 200,
        "notes_fa": "آلت‌کوین با نوسان شدید. حجم خیلی کم بگیرید. مناسب تریدرهای باتجربه.",
    },
    # ── Indices (1 new) ──
    "US500": {
        "type": "indices", "name_fa": "S&P 500", "pip": 0.1, "pip_digits": 1,
        "contract": 1, "tick_value_per_lot": 1.0,
        "avg_spread": 0.5, "avg_atr_h1": 15.0,
        "sessions": ["newyork"],
        "swap_long": -7.0, "swap_short": -2.5,
        "min_sl_pips": 30, "recommended_sl_pips": 80,
        "notes_fa": "مهم‌ترین شاخص آمریکا. اسپرد پایین. گپ آخر هفته دارد.",
    },
}

# Default for unknown symbols
DEFAULT_SPEC = {
    "type": "forex", "name_fa": "نامشخص", "pip": 0.0001, "pip_digits": 4,
    "contract": 100000, "tick_value_per_lot": 10.0,
    "avg_spread": 2.0, "avg_atr_h1": 0.001,
    "sessions": [], "swap_long": 0, "swap_short": 0,
    "min_sl_pips": 10, "recommended_sl_pips": 30,
    "notes_fa": "",
}

RISK_PRESETS = {
    "conservative": {
        "name_fa": "محافظه‌کار 🛡️",
        "risk_pct": 1.0, "max_daily_dd": 3.0, "max_total_dd": 10.0,
        "max_open": 2, "max_daily_trades": 3,
        "desc_fa": "مناسب مبتدیان. ریسک پایین، رشد آهسته اما مطمئن.",
    },
    "moderate": {
        "name_fa": "متعادل ⚖️",
        "risk_pct": 2.0, "max_daily_dd": 5.0, "max_total_dd": 15.0,
        "max_open": 3, "max_daily_trades": 5,
        "desc_fa": "تعادل بین رشد و حفظ سرمایه. مناسب اکثر تریدرها.",
    },
    "aggressive": {
        "name_fa": "تهاجمی 🔥",
        "risk_pct": 3.0, "max_daily_dd": 8.0, "max_total_dd": 25.0,
        "max_open": 5, "max_daily_trades": 8,
        "desc_fa": "ریسک بالا، سود بالقوه بیشتر. فقط برای تریدرهای باتجربه.",
    },
}


# ══════ PROFILE MANAGEMENT ══════

def _profile_file(email):
    safe = email.replace("@", "_at_").replace(".", "_")
    return os.path.join(PROFILES_DIR, f"{safe}.json")


def save_profile(email, profile):
    """Save user risk profile."""
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    profile.setdefault("balance", 10000)
    profile.setdefault("account_type", "standard")
    profile.setdefault("account_currency", "USD")
    profile.setdefault("risk_preset", "moderate")
    profile.setdefault("risk_pct", 2.0)
    profile.setdefault("max_daily_dd_pct", 5.0)
    profile.setdefault("max_total_dd_pct", 15.0)
    profile.setdefault("max_open_trades", 3)
    profile.setdefault("max_daily_trades", 5)
    profile.setdefault("leverage", 100)
    profile.setdefault("daily_trades_today", 0)
    profile.setdefault("daily_pnl_today", 0)
    profile.setdefault("trade_history", [])

    with _lock:
        with open(_profile_file(email), "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
    return {"success": True}


def load_profile(email):
    """Load user risk profile."""
    fp = _profile_file(email)
    try:
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def apply_preset(email, preset_id):
    """Apply a risk preset to profile."""
    preset = RISK_PRESETS.get(preset_id)
    if not preset:
        return {"success": False, "error": "Invalid preset"}
    profile = load_profile(email) or {}
    profile["risk_preset"] = preset_id
    profile["risk_pct"] = preset["risk_pct"]
    profile["max_daily_dd_pct"] = preset["max_daily_dd"]
    profile["max_total_dd_pct"] = preset["max_total_dd"]
    profile["max_open_trades"] = preset["max_open"]
    profile["max_daily_trades"] = preset["max_daily_trades"]
    return save_profile(email, profile)


# ══════ CALCULATION ENGINE ══════

def calculate_trade(profile, trade_input):
    """
    Main calculation: given profile + trade params, return full management plan.

    trade_input:
        symbol, direction (BUY/SELL), entry_price, sl_price, tp_price,
        optional: tp2_price, tp3_price, slippage_pips, commission_per_lot
    """
    symbol = trade_input.get("symbol", "XAUUSD")
    direction = trade_input.get("direction", "BUY")
    entry = float(trade_input.get("entry_price", 0))
    sl = float(trade_input.get("sl_price", 0))
    tp1 = float(trade_input.get("tp_price", 0))
    tp2 = float(trade_input.get("tp2_price", 0))
    tp3 = float(trade_input.get("tp3_price", 0))
    slippage_pips = float(trade_input.get("slippage_pips", 0))
    commission_per_lot = float(trade_input.get("commission_per_lot", 0))

    if entry <= 0 or sl <= 0:
        return {"success": False, "error": "قیمت ورود و SL الزامی است"}

    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC)
    pip = spec["pip"]
    tick_val = spec["tick_value_per_lot"]
    balance = float(profile.get("balance", 10000))
    risk_pct = float(profile.get("risk_pct", 2.0))
    leverage = int(profile.get("leverage", 100))
    max_daily_dd = float(profile.get("max_daily_dd_pct", 5.0))
    daily_pnl = float(profile.get("daily_pnl_today", 0))

    # SL distance
    if direction == "BUY":
        sl_dist = entry - sl
        tp1_dist = tp1 - entry if tp1 > 0 else 0
        tp2_dist = tp2 - entry if tp2 > 0 else 0
        tp3_dist = tp3 - entry if tp3 > 0 else 0
    else:
        sl_dist = sl - entry
        tp1_dist = entry - tp1 if tp1 > 0 else 0
        tp2_dist = entry - tp2 if tp2 > 0 else 0
        tp3_dist = entry - tp3 if tp3 > 0 else 0

    if sl_dist <= 0:
        return {"success": False, "error": "SL باید در جهت درست باشد (برای BUY پایین‌تر، برای SELL بالاتر)"}

    sl_pips = sl_dist / pip
    tp1_pips = tp1_dist / pip if tp1_dist > 0 else 0
    tp2_pips = tp2_dist / pip if tp2_dist > 0 else 0
    tp3_pips = tp3_dist / pip if tp3_dist > 0 else 0

    # Risk amount
    risk_amount = balance * risk_pct / 100.0
    daily_risk_remaining = balance * max_daily_dd / 100.0 + daily_pnl  # daily_pnl is negative if lost
    effective_risk = min(risk_amount, max(0, daily_risk_remaining))

    # Effective SL includes slippage for lot sizing
    effective_sl_pips = sl_pips + slippage_pips

    # Lot size (accounts for slippage in risk calculation)
    if tick_val > 0 and effective_sl_pips > 0:
        lot_size = effective_risk / (effective_sl_pips * tick_val)
    else:
        lot_size = 0.01

    # Round to step
    lot_size = math.floor(lot_size * 100) / 100
    lot_size = max(0.01, min(lot_size, 100.0))

    # Margin required
    if spec["type"] == "forex":
        margin = (lot_size * spec["contract"] * entry) / leverage
    elif spec["type"] == "metals":
        margin = (lot_size * spec["contract"] * entry) / leverage
    elif spec["type"] == "crypto":
        margin = (lot_size * entry) / leverage
    else:
        margin = (lot_size * entry) / leverage

    # Risk/Reward
    rr1 = round(tp1_pips / sl_pips, 2) if sl_pips > 0 and tp1_pips > 0 else 0
    rr2 = round(tp2_pips / sl_pips, 2) if sl_pips > 0 and tp2_pips > 0 else 0
    rr3 = round(tp3_pips / sl_pips, 2) if sl_pips > 0 and tp3_pips > 0 else 0

    # Potential PnL
    pnl_sl = -round(sl_pips * tick_val * lot_size, 2)
    pnl_tp1 = round(tp1_pips * tick_val * lot_size, 2) if tp1_pips > 0 else 0
    pnl_tp2 = round(tp2_pips * tick_val * lot_size, 2) if tp2_pips > 0 else 0
    pnl_tp3 = round(tp3_pips * tick_val * lot_size, 2) if tp3_pips > 0 else 0

    # Break even (after spread)
    spread_pips = spec["avg_spread"]
    if direction == "BUY":
        be_price = round(entry + spread_pips * pip, spec["pip_digits"] + 1)
    else:
        be_price = round(entry - spread_pips * pip, spec["pip_digits"] + 1)

    # SL validation
    warnings = []
    tips = []

    if sl_pips < spec["min_sl_pips"]:
        warnings.append(f"⚠️ SL خیلی نزدیک است! حداقل {spec['min_sl_pips']} پیپ توصیه می‌شود برای {spec['name_fa']}")

    if sl_pips > spec["recommended_sl_pips"] * 3:
        warnings.append(f"⚠️ SL خیلی دور است ({sl_pips:.0f} پیپ). حجم کم‌تری محاسبه شد.")

    if rr1 > 0 and rr1 < 1.0:
        warnings.append(f"⚠️ نسبت ریسک به ریوارد ({rr1}) کمتر از ۱ است. توصیه: حداقل R:R=1.5")

    if effective_risk < risk_amount * 0.5:
        warnings.append("⚠️ ریسک روزانه تقریباً پر شده! حجم کمتری محاسبه شد.")

    if margin > balance * 0.5:
        warnings.append("⚠️ مارجین بیش از ۵۰% بالانس است. خطر مارجین کال!")

    # Tips based on market type
    if spec["type"] == "metals":
        tips.append("💡 طلا: نوسان بالا → SL بزرگتر → حجم کمتر. از Trailing ATR استفاده کنید.")
        tips.append("💡 بهترین زمان: سشن لندن و نیویورک (همپوشانی)")
    elif spec["type"] == "forex":
        tips.append("💡 فارکس: به اسپرد و سواپ شبانه توجه کنید.")
        tips.append("💡 قبل از اخبار مهم معامله نکنید یا SL را بزرگتر بگذارید.")
    elif spec["type"] == "crypto":
        tips.append("💡 کریپتو: بازار ۲۴/۷ — حتماً SL بگذارید چون گپ ندارد اما نوسان شدید دارد.")
        tips.append("💡 حجم را ۵۰% کمتر از فارکس بگیرید به خاطر نوسان بالا.")
    elif spec["type"] == "indices":
        tips.append("💡 شاخص: گپ آخر هفته دارد. جمعه بعدازظهر معامله جدید باز نکنید.")
        tips.append("💡 حساس به اخبار اقتصادی آمریکا (NFP, CPI, FOMC)")

    # Partial close recommendations
    partial_plan = []
    if tp1_pips > 0:
        if tp2 > 0 and tp3 > 0:
            partial_plan = [
                {"level": "TP1", "price": tp1, "close_pct": 33, "action_fa": "⅓ حجم ببند، SL به ورود ببر", "rr": rr1},
                {"level": "TP2", "price": tp2, "close_pct": 33, "action_fa": "⅓ دیگر ببند، SL به TP1 ببر", "rr": rr2},
                {"level": "TP3", "price": tp3, "close_pct": 34, "action_fa": "باقی ببند یا Trailing بذار", "rr": rr3},
            ]
        elif tp2 > 0:
            partial_plan = [
                {"level": "TP1", "price": tp1, "close_pct": 50, "action_fa": "نصف ببند، SL به ورود ببر", "rr": rr1},
                {"level": "TP2", "price": tp2, "close_pct": 50, "action_fa": "باقی ببند", "rr": rr2},
            ]
        else:
            partial_plan = [
                {"level": "TP1", "price": tp1, "close_pct": 100, "action_fa": "کل ببند", "rr": rr1},
            ]
            if rr1 >= 2:
                partial_plan = [
                    {"level": "50% TP", "price": round((entry + tp1) / 2, spec["pip_digits"] + 1) if direction == "BUY" else round((entry + tp1) / 2, spec["pip_digits"] + 1), "close_pct": 50, "action_fa": "نصف ببند، SL به ورود ببر", "rr": round(rr1 / 2, 2)},
                    {"level": "TP1", "price": tp1, "close_pct": 50, "action_fa": "باقی ببند یا Trailing", "rr": rr1},
                ]

    # Trailing recommendation
    trail_reco = _recommend_trailing(spec, sl_pips, tp1_pips, direction)

    # Management milestones
    milestones = _build_milestones(entry, sl, tp1, tp2, tp3, direction, spec, be_price, lot_size, tick_val, sl_pips)

    return {
        "success": True,
        "symbol": symbol,
        "symbol_info": {
            "name_fa": spec["name_fa"],
            "type": spec["type"],
            "pip": pip,
            "avg_spread": spec["avg_spread"],
            "sessions": spec["sessions"],
            "notes_fa": spec["notes_fa"],
        },
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2 if tp2 > 0 else None,
        "tp3": tp3 if tp3 > 0 else None,
        "lot_size": lot_size,
        "risk": {
            "amount": round(effective_risk, 2),
            "pct": risk_pct,
            "pct_actual": round(effective_risk / balance * 100, 2),
            "daily_remaining": round(max(0, daily_risk_remaining), 2),
            "daily_remaining_pct": round(max(0, daily_risk_remaining) / balance * 100, 2),
        },
        "pips": {
            "sl": round(sl_pips, 1),
            "tp1": round(tp1_pips, 1),
            "tp2": round(tp2_pips, 1) if tp2_pips else None,
            "tp3": round(tp3_pips, 1) if tp3_pips else None,
        },
        "rr": {"tp1": rr1, "tp2": rr2 if rr2 else None, "tp3": rr3 if rr3 else None},
        "pnl": {
            "sl": pnl_sl,
            "tp1": pnl_tp1,
            "tp2": pnl_tp2 if pnl_tp2 else None,
            "tp3": pnl_tp3 if pnl_tp3 else None,
        },
        "margin": round(margin, 2),
        "margin_pct": round(margin / balance * 100, 2),
        "be_price": be_price,
        "spread_cost": round(spread_pips * tick_val * lot_size, 2),
        "slippage": {
            "pips": slippage_pips,
            "cost": round(slippage_pips * tick_val * lot_size, 2),
            "effective_sl_pips": round(effective_sl_pips, 1),
        } if slippage_pips > 0 else None,
        "commission": {
            "per_lot": commission_per_lot,
            "total": round(commission_per_lot * lot_size, 2),
        } if commission_per_lot > 0 else None,
        "swap": {
            "long": spec["swap_long"],
            "short": spec["swap_short"],
            "daily_cost": round(spec["swap_long" if direction == "BUY" else "swap_short"] * lot_size, 2),
        },
        "partial_plan": partial_plan,
        "trailing": trail_reco,
        "milestones": milestones,
        "warnings": warnings,
        "tips": tips,
    }


def _recommend_trailing(spec, sl_pips, tp1_pips, direction):
    """Recommend trailing stop method based on market and distances."""
    recos = []

    if spec["type"] == "metals":
        recos.append({
            "method": "ATR Trailing",
            "method_fa": "تریلینگ بر اساس ATR",
            "value": "2x ATR(14)",
            "desc_fa": "بهترین روش برای طلا و نقره. با نوسان بازار تنظیم می‌شود.",
            "when_fa": "وقتی معامله به R:R=1 رسید فعال کنید.",
        })
    elif spec["type"] == "crypto":
        recos.append({
            "method": "ATR Trailing",
            "method_fa": "تریلینگ ATR بزرگ",
            "value": "3x ATR(14)",
            "desc_fa": "کریپتو نوسان زیاد دارد. ATR بزرگتر می‌گیریم تا زود خارج نشویم.",
            "when_fa": "وقتی معامله به R:R=1 رسید.",
        })
    elif spec["type"] == "indices":
        recos.append({
            "method": "Step Trailing",
            "method_fa": "تریلینگ پلکانی",
            "value": f"هر {int(sl_pips * 0.5)} پیپ",
            "desc_fa": "شاخص‌ها روند قوی دارند. پلکانی بهتر عمل می‌کند.",
            "when_fa": "بعد از رسیدن به Break Even.",
        })
    else:  # forex
        if tp1_pips > sl_pips * 2:
            recos.append({
                "method": "Fixed Trailing",
                "method_fa": "تریلینگ فاصله ثابت",
                "value": f"{int(sl_pips * 0.7)} پیپ",
                "desc_fa": "فاصله ثابت مناسب سوینگ ترید. ۷۰% اندازه SL.",
                "when_fa": "وقتی در سود هستید و R:R >= 1.",
            })
        else:
            recos.append({
                "method": "BE + Fixed",
                "method_fa": "Break Even + تریلینگ",
                "value": f"BE بعد از {int(sl_pips * 0.5)} پیپ سود",
                "desc_fa": "اول SL به ورود ببرید، بعد تریلینگ فعال کنید.",
                "when_fa": "فوری بعد از ۵۰% SL سود.",
            })

    return recos


def _build_milestones(entry, sl, tp1, tp2, tp3, direction, spec, be_price, lot_size, tick_val, sl_pips):
    """Build step-by-step management milestones."""
    pip = spec["pip"]
    ms = []

    # 1. Entry
    ms.append({
        "stage": "entry",
        "stage_fa": "🟢 ورود",
        "price": entry,
        "action_fa": f"معامله {direction} با حجم {lot_size} لات باز کنید. SL={sl}",
        "detail_fa": "بعد از باز شدن معامله، فوری SL و TP بگذارید. هرگز بدون SL نگذارید.",
    })

    # 2. Break Even zone
    if direction == "BUY":
        be_trigger = round(entry + sl_pips * 0.5 * pip, spec["pip_digits"] + 1)
    else:
        be_trigger = round(entry - sl_pips * 0.5 * pip, spec["pip_digits"] + 1)

    ms.append({
        "stage": "break_even",
        "stage_fa": "🟡 Break Even",
        "price": be_trigger,
        "action_fa": f"SL را به قیمت ورود ({entry}) منتقل کنید",
        "detail_fa": "وقتی قیمت ۵۰% فاصله SL را در سود طی کرد، SL به ورود ببرید تا ریسک صفر شود.",
    })

    # 3. TP levels
    if tp1 > 0:
        ms.append({
            "stage": "tp1",
            "stage_fa": "🎯 TP1",
            "price": tp1,
            "action_fa": "سیو سود — بخشی ببندید یا Trailing فعال کنید",
            "detail_fa": "اگر چند TP دارید ⅓ ببندید. اگر یک TP دارید ½ ببندید و بقیه را Trailing بگذارید.",
        })
    if tp2 > 0:
        ms.append({
            "stage": "tp2",
            "stage_fa": "🎯 TP2",
            "price": tp2,
            "action_fa": "سیو سود مرحله ۲ — SL به TP1 ببرید",
            "detail_fa": "بخش دیگر ببندید و SL باقیمانده را به TP1 منتقل کنید. سود تضمینی.",
        })
    if tp3 > 0:
        ms.append({
            "stage": "tp3",
            "stage_fa": "🎯 TP3",
            "price": tp3,
            "action_fa": "آخرین بخش — کامل ببندید",
            "detail_fa": "آخرین بخش معامله. همه چیز ببندید و سود نهایی ثبت کنید.",
        })

    # 4. SL hit
    ms.append({
        "stage": "sl",
        "stage_fa": "🔴 حد ضرر",
        "price": sl,
        "action_fa": "معامله بسته می‌شود — ضرر محدود",
        "detail_fa": "SL طبق پلن فعال شد. این یک ضرر مدیریت‌شده و عادی است. هرگز SL را جابجا نکنید!",
    })

    return ms


# ══════ POST-TRADE REPORT ══════

def generate_trade_report(profile, trade_input, trade_result):
    """
    Generate post-trade report with analysis and lessons.
    trade_result: {outcome: win/loss, exit_price, exit_reason, pnl, pnl_pips, bars_held, followed_plan}
    """
    symbol = trade_input.get("symbol", "XAUUSD")
    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC)
    direction = trade_input.get("direction", "BUY")
    entry = float(trade_input.get("entry_price", 0))
    sl = float(trade_input.get("sl_price", 0))
    tp = float(trade_input.get("tp_price", 0))

    outcome = trade_result.get("outcome", "unknown")
    pnl = float(trade_result.get("pnl", 0))
    exit_price = float(trade_result.get("exit_price", 0))
    exit_reason = trade_result.get("exit_reason", "")
    followed_plan = trade_result.get("followed_plan", True)
    bars_held = int(trade_result.get("bars_held", 0))

    pip = spec["pip"]
    sl_pips = abs(entry - sl) / pip
    tp_pips = abs(tp - entry) / pip if tp > 0 else 0
    rr = tp_pips / sl_pips if sl_pips > 0 and tp_pips > 0 else 0

    report = {
        "trade_summary": {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "exit": exit_price,
            "sl": sl,
            "tp": tp,
            "outcome": outcome,
            "pnl": round(pnl, 2),
            "exit_reason": exit_reason,
        },
        "analysis": [],
        "score": 0,
        "grade": "",
        "lessons": [],
    }

    score = 50  # base

    # Outcome analysis
    if outcome == "win":
        score += 20
        report["analysis"].append({
            "title_fa": "✅ معامله موفق",
            "text_fa": f"سود ${pnl:.2f} با {exit_reason}. نسبت R:R اولیه {rr:.1f} بود.",
        })
    else:
        report["analysis"].append({
            "title_fa": "❌ معامله ناموفق",
            "text_fa": f"ضرر ${abs(pnl):.2f}. {_exit_reason_text(exit_reason)}",
        })

    # Plan adherence
    if followed_plan:
        score += 15
        report["analysis"].append({
            "title_fa": "📋 پلن رعایت شد",
            "text_fa": "شما به پلن معاملاتی خود پایبند بودید. این مهم‌ترین عامل موفقیت بلندمدت است.",
        })
    else:
        score -= 10
        report["analysis"].append({
            "title_fa": "⚠️ پلن رعایت نشد",
            "text_fa": "عدم رعایت پلن یکی از بزرگترین اشتباهات تریدینگ است. حتی اگر سودده شد، تکرار نکنید.",
        })
        report["lessons"].append("درس: همیشه به پلن خود پایبند باشید. یک ضرر مدیریت‌شده بهتر از یک سود شانسی است.")

    # R:R analysis
    if rr >= 2:
        score += 10
        report["analysis"].append({
            "title_fa": "🎯 R:R مناسب",
            "text_fa": f"نسبت R:R شما {rr:.1f} بود که عالی است. حتی با نرخ برد ۴۰% سودآور خواهید بود.",
        })
    elif rr >= 1:
        score += 5
    elif rr > 0:
        report["analysis"].append({
            "title_fa": "⚠️ R:R ضعیف",
            "text_fa": f"R:R شما {rr:.1f} بود. برای سودآوری بلندمدت حداقل ۱.۵ توصیه می‌شود.",
        })
        report["lessons"].append("درس: قبل از ورود به معامله، مطمئن شوید R:R حداقل ۱.۵ است.")

    # Duration
    if bars_held > 0:
        if bars_held <= 3:
            report["analysis"].append({
                "title_fa": "⚡ خروج سریع",
                "text_fa": f"معامله فقط {bars_held} کندل طول کشید. بررسی کنید آیا نقطه ورود مناسب بود.",
            })
        elif bars_held > 50:
            report["analysis"].append({
                "title_fa": "⏰ معامله طولانی",
                "text_fa": f"معامله {bars_held} کندل طول کشید. به سواپ و هزینه نگهداری توجه کنید.",
            })

    # Market-specific lessons
    if spec["type"] == "metals" and outcome == "loss":
        report["lessons"].append("درس طلا: نوسان بالای طلا ممکن است SL نزدیک را فعال کند. SL بزرگتر با حجم کمتر امتحان کنید.")
    elif spec["type"] == "crypto" and outcome == "loss":
        report["lessons"].append("درس کریپتو: نوسان شدید عادی است. حجم معامله را کاهش دهید.")

    # General lessons
    if outcome == "win" and followed_plan:
        report["lessons"].append("ادامه بدهید! معامله خوبی بود. همین پلن را تکرار کنید.")
    elif outcome == "loss" and followed_plan:
        report["lessons"].append("ضرر با رعایت پلن کاملاً طبیعی است. این بخشی از تریدینگ است. به استراتژی خود اعتماد کنید.")
    elif outcome == "win" and not followed_plan:
        report["lessons"].append("هشدار: این سود شانسی بود. عدم رعایت پلن در بلندمدت ضرر می‌آورد.")

    # Grade
    if score >= 80:
        report["grade"] = "A"
    elif score >= 65:
        report["grade"] = "B"
    elif score >= 50:
        report["grade"] = "C"
    elif score >= 35:
        report["grade"] = "D"
    else:
        report["grade"] = "F"

    report["score"] = min(100, max(0, score))
    return report


def _exit_reason_text(reason):
    m = {
        "tp": "به حد سود رسید — عالی!",
        "sl": "حد ضرر فعال شد — ضرر مدیریت‌شده.",
        "trailing": "تریلینگ استاپ فعال شد — سود حفظ شد.",
        "break_even": "در نقطه سربه‌سر بسته شد — بدون ضرر.",
        "time": "خروج زمانی — معامله طولانی شده بود.",
        "manual": "خروج دستی.",
    }
    return m.get(reason, reason)


# ══════ ENTRY SUGGESTIONS ══════

def suggest_entry_levels(symbol, direction="BUY"):
    """
    Suggest entry, SL, TP levels based on current price and ATR.
    Uses MT5 for price data, falls back to ATR estimates if unavailable.
    """
    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC)
    pip = spec["pip"]
    atr_h1 = spec["avg_atr_h1"]
    spread = spec["avg_spread"]

    # Try to get live price and compute ATR from MT5
    current_price = 0
    atr_live = 0
    supports = []
    resistances = []

    try:
        from backend.mt5.mt5_connector import MT5Connector
        import MetaTrader5 as mt5
        connector = MT5Connector.get_instance()
        if connector.ensure_connected():
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                current_price = tick.ask if direction == "BUY" else tick.bid

            # Get H1 data for ATR and S/R
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
            if rates is not None and len(rates) >= 14:
                # ATR(14)
                highs = [r[2] for r in rates]  # high
                lows = [r[3] for r in rates]   # low
                closes = [r[4] for r in rates] # close
                trs = []
                for i in range(1, len(rates)):
                    tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                    trs.append(tr)
                atr_live = sum(trs[-14:]) / 14

                # Swing highs/lows for S/R (last 30 bars)
                for i in range(2, min(len(rates) - 2, 30)):
                    if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                        resistances.append(round(highs[i], spec["pip_digits"] + 1))
                    if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                        supports.append(round(lows[i], spec["pip_digits"] + 1))

                supports = sorted(set(supports))[-5:]
                resistances = sorted(set(resistances))[-5:]
    except Exception:
        pass

    atr = atr_live if atr_live > 0 else atr_h1
    if current_price <= 0:
        return {"success": False, "error": "قیمت فعلی در دسترس نیست. MT5 را بررسی کنید."}

    entry = current_price

    # SL: nearest S/R or 1.5 × ATR
    if direction == "BUY":
        # Find nearest support below entry
        nearby_supports = [s for s in supports if s < entry]
        if nearby_supports:
            sl = nearby_supports[-1] - spread * pip  # just below support
        else:
            sl = entry - 1.5 * atr
        tp1 = entry + abs(entry - sl) * 2  # R:R = 2
        tp2 = entry + abs(entry - sl) * 3  # R:R = 3
    else:
        # Find nearest resistance above entry
        nearby_resistances = [r for r in resistances if r > entry]
        if nearby_resistances:
            sl = nearby_resistances[0] + spread * pip  # just above resistance
        else:
            sl = entry + 1.5 * atr
        tp1 = entry - abs(sl - entry) * 2
        tp2 = entry - abs(sl - entry) * 3

    sl_pips = abs(entry - sl) / pip
    rr = 2.0

    return {
        "success": True,
        "symbol": symbol,
        "direction": direction,
        "entry": round(entry, spec["pip_digits"] + 1),
        "sl": round(sl, spec["pip_digits"] + 1),
        "tp1": round(tp1, spec["pip_digits"] + 1),
        "tp2": round(tp2, spec["pip_digits"] + 1),
        "sl_pips": round(sl_pips, 1),
        "rr": rr,
        "atr": round(atr, spec["pip_digits"] + 1),
        "atr_pips": round(atr / pip, 1),
        "spread": spec["avg_spread"],
        "supports": supports,
        "resistances": resistances,
        "notes_fa": spec["notes_fa"],
    }


# ══════ PIP / PNL CALCULATOR ══════

def calculate_pip_pnl(symbol, direction, entry_price, exit_price, lot_size,
                       slippage_pips=0, commission_per_lot=0):
    """
    Calculate pip count and PnL for a trade.
    Returns gross and net values with cost breakdown.
    """
    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC)
    pip = spec["pip"]
    tick_val = spec["tick_value_per_lot"]
    spread_pips = spec["avg_spread"]

    entry = float(entry_price)
    exit_p = float(exit_price)
    lots = float(lot_size)
    slippage = float(slippage_pips)
    commission = float(commission_per_lot)

    if entry <= 0 or exit_p <= 0 or lots <= 0:
        return {"success": False, "error": "مقادیر ورودی نامعتبر"}

    # Gross pips
    if direction == "BUY":
        gross_pips = (exit_p - entry) / pip
    else:
        gross_pips = (entry - exit_p) / pip

    # Net pips (minus spread + slippage)
    net_pips = gross_pips - spread_pips - slippage

    # PnL
    pnl_gross = gross_pips * tick_val * lots
    spread_cost = spread_pips * tick_val * lots
    slippage_cost = slippage * tick_val * lots
    commission_total = commission * lots
    total_costs = spread_cost + slippage_cost + commission_total
    pnl_net = pnl_gross - total_costs

    return {
        "success": True,
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "exit": exit_p,
        "lot_size": lots,
        "pips_gross": round(gross_pips, 1),
        "pips_net": round(net_pips, 1),
        "pnl_gross": round(pnl_gross, 2),
        "pnl_net": round(pnl_net, 2),
        "costs": {
            "spread_pips": spread_pips,
            "spread_cost": round(spread_cost, 2),
            "slippage_pips": slippage,
            "slippage_cost": round(slippage_cost, 2),
            "commission_per_lot": commission,
            "commission_total": round(commission_total, 2),
            "total": round(total_costs, 2),
        },
    }


# ══════ CONFIG EXPORT ══════

def get_risk_config():
    """Return all config for frontend."""
    return {
        "market_specs": {k: {kk: vv for kk, vv in v.items()} for k, v in MARKET_SPECS.items()},
        "presets": RISK_PRESETS,
        "symbols": list(MARKET_SPECS.keys()),
    }
