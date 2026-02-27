"""
Whilber-AI Strategy Builder Engine
=====================================
Defines available indicators, conditions, exit types, filters.
Validates and processes user-built strategies.
"""

import json
import hashlib
from datetime import datetime, timezone

# ══════════════════════════════════════════════
# AVAILABLE INDICATORS
# ══════════════════════════════════════════════

INDICATORS = {
    # --- Trend ---
    "SMA": {
        "name_fa": "میانگین ساده (SMA)",
        "category": "trend",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 500},
            {"id": "source", "name_fa": "منبع", "type": "select", "default": "close",
             "options": ["close", "open", "high", "low", "hl2", "hlc3"]},
        ],
        "outputs": ["value"],
    },
    "EMA": {
        "name_fa": "میانگین نمایی (EMA)",
        "category": "trend",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 500},
            {"id": "source", "name_fa": "منبع", "type": "select", "default": "close",
             "options": ["close", "open", "high", "low", "hl2", "hlc3"]},
        ],
        "outputs": ["value"],
    },
    "WMA": {
        "name_fa": "میانگین وزنی (WMA)",
        "category": "trend",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 500},
        ],
        "outputs": ["value"],
    },
    "DEMA": {
        "name_fa": "میانگین نمایی دوگانه (DEMA)",
        "category": "trend",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 500},
        ],
        "outputs": ["value"],
    },
    "TEMA": {
        "name_fa": "میانگین نمایی سه‌گانه (TEMA)",
        "category": "trend",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 500},
        ],
        "outputs": ["value"],
    },

    # --- Oscillators ---
    "RSI": {
        "name_fa": "شاخص قدرت نسبی (RSI)",
        "category": "oscillator",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 14, "min": 2, "max": 100},
        ],
        "outputs": ["value"],
    },
    "STOCH": {
        "name_fa": "استوکاستیک",
        "category": "oscillator",
        "params": [
            {"id": "k_period", "name_fa": "دوره %K", "type": "int", "default": 14, "min": 1, "max": 100},
            {"id": "d_period", "name_fa": "دوره %D", "type": "int", "default": 3, "min": 1, "max": 50},
            {"id": "slowing", "name_fa": "اسلوینگ", "type": "int", "default": 3, "min": 1, "max": 50},
        ],
        "outputs": ["k", "d"],
    },
    "STOCHRSI": {
        "name_fa": "استوکاستیک RSI",
        "category": "oscillator",
        "params": [
            {"id": "rsi_period", "name_fa": "دوره RSI", "type": "int", "default": 14, "min": 2, "max": 100},
            {"id": "stoch_period", "name_fa": "دوره Stoch", "type": "int", "default": 14, "min": 2, "max": 100},
            {"id": "k_smooth", "name_fa": "صاف‌سازی K", "type": "int", "default": 3, "min": 1, "max": 20},
            {"id": "d_smooth", "name_fa": "صاف‌سازی D", "type": "int", "default": 3, "min": 1, "max": 20},
        ],
        "outputs": ["k", "d"],
    },
    "CCI": {
        "name_fa": "شاخص کانال کالا (CCI)",
        "category": "oscillator",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 200},
        ],
        "outputs": ["value"],
    },
    "WILLIAMS": {
        "name_fa": "ویلیامز %R",
        "category": "oscillator",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 14, "min": 2, "max": 100},
        ],
        "outputs": ["value"],
    },
    "MFI": {
        "name_fa": "شاخص جریان پول (MFI)",
        "category": "oscillator",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 14, "min": 2, "max": 100},
        ],
        "outputs": ["value"],
    },

    # --- MACD ---
    "MACD": {
        "name_fa": "مکدی (MACD)",
        "category": "momentum",
        "params": [
            {"id": "fast", "name_fa": "سریع", "type": "int", "default": 12, "min": 2, "max": 100},
            {"id": "slow", "name_fa": "کند", "type": "int", "default": 26, "min": 2, "max": 200},
            {"id": "signal", "name_fa": "سیگنال", "type": "int", "default": 9, "min": 2, "max": 50},
        ],
        "outputs": ["macd", "signal", "histogram"],
    },

    # --- Volatility ---
    "BB": {
        "name_fa": "باند بولینگر",
        "category": "volatility",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 200},
            {"id": "std_dev", "name_fa": "انحراف معیار", "type": "float", "default": 2.0, "min": 0.5, "max": 5.0},
        ],
        "outputs": ["upper", "middle", "lower", "width", "percent_b"],
    },
    "ATR": {
        "name_fa": "میانگین محدوده واقعی (ATR)",
        "category": "volatility",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 14, "min": 2, "max": 100},
        ],
        "outputs": ["value"],
    },
    "KELTNER": {
        "name_fa": "کانال کلتنر",
        "category": "volatility",
        "params": [
            {"id": "ema_period", "name_fa": "دوره EMA", "type": "int", "default": 20, "min": 2, "max": 200},
            {"id": "atr_period", "name_fa": "دوره ATR", "type": "int", "default": 14, "min": 2, "max": 100},
            {"id": "multiplier", "name_fa": "ضریب", "type": "float", "default": 1.5, "min": 0.5, "max": 5.0},
        ],
        "outputs": ["upper", "middle", "lower"],
    },
    "DONCHIAN": {
        "name_fa": "کانال دونچیان",
        "category": "volatility",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 200},
        ],
        "outputs": ["upper", "middle", "lower"],
    },

    # --- Trend Strength ---
    "ADX": {
        "name_fa": "شاخص جهت‌دار (ADX)",
        "category": "trend_strength",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 14, "min": 2, "max": 100},
        ],
        "outputs": ["adx", "plus_di", "minus_di"],
    },
    "AROON": {
        "name_fa": "آرون",
        "category": "trend_strength",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 25, "min": 2, "max": 200},
        ],
        "outputs": ["up", "down", "oscillator"],
    },
    "SUPERTREND": {
        "name_fa": "سوپرترند",
        "category": "trend_strength",
        "params": [
            {"id": "period", "name_fa": "دوره ATR", "type": "int", "default": 10, "min": 2, "max": 100},
            {"id": "multiplier", "name_fa": "ضریب", "type": "float", "default": 3.0, "min": 1.0, "max": 10.0},
        ],
        "outputs": ["value", "direction"],
    },
    "PSAR": {
        "name_fa": "پارابولیک SAR",
        "category": "trend_strength",
        "params": [
            {"id": "af_start", "name_fa": "AF شروع", "type": "float", "default": 0.02, "min": 0.01, "max": 0.1},
            {"id": "af_max", "name_fa": "AF حداکثر", "type": "float", "default": 0.2, "min": 0.05, "max": 0.5},
        ],
        "outputs": ["value"],
    },

    # --- Ichimoku ---
    "ICHIMOKU": {
        "name_fa": "ایچیموکو",
        "category": "ichimoku",
        "params": [
            {"id": "tenkan", "name_fa": "تنکان", "type": "int", "default": 9, "min": 2, "max": 100},
            {"id": "kijun", "name_fa": "کیجون", "type": "int", "default": 26, "min": 2, "max": 200},
            {"id": "senkou_b", "name_fa": "سنکو B", "type": "int", "default": 52, "min": 2, "max": 500},
        ],
        "outputs": ["tenkan", "kijun", "senkou_a", "senkou_b", "chikou"],
    },

    # --- Volume ---
    "VOLUME": {
        "name_fa": "حجم معاملات",
        "category": "volume",
        "params": [],
        "outputs": ["value"],
    },
    "OBV": {
        "name_fa": "حجم تعادلی (OBV)",
        "category": "volume",
        "params": [],
        "outputs": ["value"],
    },
    "VWAP": {
        "name_fa": "میانگین وزنی حجمی (VWAP)",
        "category": "volume",
        "params": [],
        "outputs": ["value"],
    },

    # --- Price ---
    "PRICE": {
        "name_fa": "قیمت",
        "category": "price",
        "params": [
            {"id": "source", "name_fa": "منبع", "type": "select", "default": "close",
             "options": ["close", "open", "high", "low", "hl2", "hlc3"]},
        ],
        "outputs": ["value"],
    },
    "CANDLE": {
        "name_fa": "الگوی کندل",
        "category": "price",
        "params": [
            {"id": "pattern", "name_fa": "الگو", "type": "select", "default": "engulfing",
             "options": [
                 "engulfing", "hammer", "shooting_star", "doji", "pin_bar",
                 "morning_star", "evening_star", "three_white_soldiers", "three_black_crows",
                 "harami", "piercing", "dark_cloud", "tweezer_top", "tweezer_bottom",
             ]},
        ],
        "outputs": ["bullish", "bearish"],
    },

    # --- Momentum ---
    "ROC": {
        "name_fa": "نرخ تغییر (ROC)",
        "category": "momentum",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 12, "min": 1, "max": 200},
        ],
        "outputs": ["value"],
    },
    "TRIX": {
        "name_fa": "تریکس (TRIX)",
        "category": "momentum",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 15, "min": 2, "max": 200},
        ],
        "outputs": ["value", "signal"],
    },
    "CMO": {
        "name_fa": "مومنتوم چاند (CMO)",
        "category": "momentum",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 14, "min": 2, "max": 100},
        ],
        "outputs": ["value"],
    },
    "MOM": {
        "name_fa": "مومنتوم (MOM)",
        "category": "momentum",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 10, "min": 1, "max": 200},
        ],
        "outputs": ["value"],
    },
    "PPO": {
        "name_fa": "درصد اسیلاتور قیمت (PPO)",
        "category": "momentum",
        "params": [
            {"id": "fast", "name_fa": "دوره سریع", "type": "int", "default": 12, "min": 2, "max": 100},
            {"id": "slow", "name_fa": "دوره کند", "type": "int", "default": 26, "min": 2, "max": 200},
            {"id": "signal", "name_fa": "سیگنال", "type": "int", "default": 9, "min": 2, "max": 50},
        ],
        "outputs": ["ppo", "signal", "histogram"],
    },

    # --- Additional Oscillators ---
    "UO": {
        "name_fa": "اسیلاتور نهایی (Ultimate)",
        "category": "oscillator",
        "params": [
            {"id": "period1", "name_fa": "دوره ۱", "type": "int", "default": 7, "min": 1, "max": 50},
            {"id": "period2", "name_fa": "دوره ۲", "type": "int", "default": 14, "min": 2, "max": 100},
            {"id": "period3", "name_fa": "دوره ۳", "type": "int", "default": 28, "min": 3, "max": 200},
        ],
        "outputs": ["value"],
    },
    "KST": {
        "name_fa": "KST (Know Sure Thing)",
        "category": "oscillator",
        "params": [
            {"id": "roc1", "name_fa": "ROC1", "type": "int", "default": 10, "min": 1, "max": 100},
            {"id": "roc2", "name_fa": "ROC2", "type": "int", "default": 15, "min": 1, "max": 100},
            {"id": "roc3", "name_fa": "ROC3", "type": "int", "default": 20, "min": 1, "max": 100},
            {"id": "roc4", "name_fa": "ROC4", "type": "int", "default": 30, "min": 1, "max": 200},
            {"id": "signal", "name_fa": "سیگنال", "type": "int", "default": 9, "min": 1, "max": 50},
        ],
        "outputs": ["kst", "signal"],
    },
    "RVI": {
        "name_fa": "شاخص قدرت نسبی (RVI)",
        "category": "oscillator",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 10, "min": 2, "max": 100},
        ],
        "outputs": ["rvi", "signal"],
    },

    # --- Additional Volume ---
    "AD": {
        "name_fa": "خط انباشت/توزیع (A/D)",
        "category": "volume",
        "params": [],
        "outputs": ["value"],
    },
    "FI": {
        "name_fa": "شاخص نیرو (Force Index)",
        "category": "volume",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 13, "min": 1, "max": 100},
        ],
        "outputs": ["value"],
    },

    # --- Additional Trend ---
    "HMA": {
        "name_fa": "میانگین هال (HMA)",
        "category": "trend",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 500},
        ],
        "outputs": ["value"],
    },
    "VWMA": {
        "name_fa": "میانگین وزنی حجمی (VWMA)",
        "category": "trend",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 500},
        ],
        "outputs": ["value"],
    },

    # --- Additional Volatility ---
    "ENVELOPE": {
        "name_fa": "پاکت نوسان (Envelope)",
        "category": "volatility",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 20, "min": 2, "max": 200},
            {"id": "percent", "name_fa": "درصد", "type": "float", "default": 2.5, "min": 0.1, "max": 20.0},
            {"id": "ma_type", "name_fa": "نوع MA", "type": "select", "default": "SMA",
             "options": ["SMA", "EMA"]},
        ],
        "outputs": ["upper", "middle", "lower"],
    },

    # --- Fibonacci ---
    "FIB_RETRACE": {
        "name_fa": "اصلاح فیبوناچی",
        "category": "fibonacci",
        "params": [
            {"id": "lookback", "name_fa": "بازه", "type": "int", "default": 50, "min": 10, "max": 500},
            {"id": "level", "name_fa": "سطح", "type": "select", "default": "0.618",
             "options": ["0.236", "0.382", "0.5", "0.618", "0.786"]},
        ],
        "outputs": ["level_price"],
    },

    # --- Pivot ---
    "PIVOT": {
        "name_fa": "پیوت پوینت",
        "category": "pivot",
        "params": [
            {"id": "type", "name_fa": "نوع", "type": "select", "default": "classic",
             "options": ["classic", "fibonacci", "camarilla", "woodie"]},
        ],
        "outputs": ["pp", "r1", "r2", "r3", "s1", "s2", "s3"],
    },
}

# ══════════════════════════════════════════════
# CONDITIONS (comparisons)
# ══════════════════════════════════════════════

CONDITIONS = {
    "crosses_above": {"name_fa": "کراس به بالا", "type": "cross"},
    "crosses_below": {"name_fa": "کراس به پایین", "type": "cross"},
    "is_above": {"name_fa": "بالاتر از", "type": "compare"},
    "is_below": {"name_fa": "پایین‌تر از", "type": "compare"},
    "is_between": {"name_fa": "بین", "type": "range"},
    "is_rising": {"name_fa": "صعودی", "type": "direction"},
    "is_falling": {"name_fa": "نزولی", "type": "direction"},
    "equals": {"name_fa": "برابر با", "type": "compare"},
    "is_overbought": {"name_fa": "اشباع خرید", "type": "zone"},
    "is_oversold": {"name_fa": "اشباع فروش", "type": "zone"},
    "turns_up": {"name_fa": "تغییر جهت به بالا", "type": "direction"},
    "turns_down": {"name_fa": "تغییر جهت به پایین", "type": "direction"},
    "divergence_bullish": {"name_fa": "واگرایی صعودی", "type": "divergence"},
    "divergence_bearish": {"name_fa": "واگرایی نزولی", "type": "divergence"},
    "is_inside_cloud": {"name_fa": "داخل ابر ایچیموکو", "type": "ichimoku"},
    "is_above_cloud": {"name_fa": "بالای ابر ایچیموکو", "type": "ichimoku"},
    "is_below_cloud": {"name_fa": "زیر ابر ایچیموکو", "type": "ichimoku"},
}

# ══════════════════════════════════════════════
# COMPARE TARGETS
# ══════════════════════════════════════════════

COMPARE_TARGETS = {
    "fixed_value": {"name_fa": "عدد ثابت"},
    "indicator": {"name_fa": "اندیکاتور دیگر"},
    "price_close": {"name_fa": "قیمت Close"},
    "price_open": {"name_fa": "قیمت Open"},
    "price_high": {"name_fa": "قیمت High"},
    "price_low": {"name_fa": "قیمت Low"},
}

# ══════════════════════════════════════════════
# EXIT TYPES
# ══════════════════════════════════════════════

EXIT_TYPES = {
    "fixed_tp": {
        "name_fa": "TP ثابت (پیپ)",
        "params": [{"id": "pips", "name_fa": "پیپ", "type": "float", "default": 50}],
    },
    "atr_tp": {
        "name_fa": "TP بر اساس ATR",
        "params": [
            {"id": "multiplier", "name_fa": "ضریب ATR", "type": "float", "default": 2.0},
            {"id": "atr_period", "name_fa": "دوره ATR", "type": "int", "default": 14},
        ],
    },
    "percent_tp": {
        "name_fa": "TP درصدی",
        "params": [{"id": "percent", "name_fa": "درصد", "type": "float", "default": 1.0}],
    },
    "stepped_tp": {
        "name_fa": "TP پله‌ای",
        "params": [
            {"id": "tp1_atr", "name_fa": "TP1 (ضریب ATR)", "type": "float", "default": 1.0},
            {"id": "tp1_close_pct", "name_fa": "سیو سود TP1 (%)", "type": "int", "default": 50},
            {"id": "tp2_atr", "name_fa": "TP2 (ضریب ATR)", "type": "float", "default": 2.0},
            {"id": "tp2_close_pct", "name_fa": "سیو سود TP2 (%)", "type": "int", "default": 30},
            {"id": "tp3_atr", "name_fa": "TP3 (ضریب ATR)", "type": "float", "default": 3.0},
        ],
    },
    "indicator_exit": {
        "name_fa": "خروج اندیکاتوری",
        "params": [
            {"id": "indicator", "name_fa": "اندیکاتور", "type": "select", "default": "RSI",
             "options": list(INDICATORS.keys())},
            {"id": "condition", "name_fa": "شرط", "type": "select", "default": "crosses_below",
             "options": ["crosses_above", "crosses_below", "is_above", "is_below"]},
            {"id": "value", "name_fa": "مقدار", "type": "float", "default": 70},
        ],
    },
    "fixed_sl": {
        "name_fa": "SL ثابت (پیپ)",
        "params": [{"id": "pips", "name_fa": "پیپ", "type": "float", "default": 30}],
    },
    "atr_sl": {
        "name_fa": "SL بر اساس ATR",
        "params": [
            {"id": "multiplier", "name_fa": "ضریب ATR", "type": "float", "default": 1.5},
            {"id": "atr_period", "name_fa": "دوره ATR", "type": "int", "default": 14},
        ],
    },
    "swing_sl": {
        "name_fa": "SL بر اساس Swing",
        "params": [
            {"id": "lookback", "name_fa": "بازه", "type": "int", "default": 10},
            {"id": "buffer_pips", "name_fa": "بافر (پیپ)", "type": "float", "default": 5},
        ],
    },
    "percent_sl": {
        "name_fa": "SL درصدی",
        "params": [{"id": "percent", "name_fa": "درصد", "type": "float", "default": 0.5}],
    },
    "trailing_fixed": {
        "name_fa": "تریلینگ ثابت (پیپ)",
        "params": [{"id": "pips", "name_fa": "پیپ", "type": "float", "default": 20}],
    },
    "trailing_atr": {
        "name_fa": "تریلینگ ATR",
        "params": [
            {"id": "multiplier", "name_fa": "ضریب ATR", "type": "float", "default": 2.0},
            {"id": "atr_period", "name_fa": "دوره ATR", "type": "int", "default": 14},
        ],
    },
    "break_even": {
        "name_fa": "Break Even",
        "params": [
            {"id": "trigger_pips", "name_fa": "فعال‌سازی (پیپ سود)", "type": "float", "default": 20},
            {"id": "lock_pips", "name_fa": "قفل (پیپ سود)", "type": "float", "default": 5},
        ],
    },
    "time_exit": {
        "name_fa": "خروج زمانی",
        "params": [
            {"id": "bars", "name_fa": "تعداد کندل", "type": "int", "default": 10},
        ],
    },
}

# ══════════════════════════════════════════════
# TRADE FILTERS
# ══════════════════════════════════════════════

TRADE_FILTERS = {
    "trend_filter": {
        "name_fa": "فیلتر روند",
        "params": [
            {"id": "indicator", "name_fa": "اندیکاتور", "type": "select", "default": "EMA",
             "options": ["SMA", "EMA", "ADX", "SUPERTREND"]},
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 200},
            {"id": "rule", "name_fa": "قانون", "type": "select", "default": "price_above_buy",
             "options": [
                 "price_above_buy", "price_below_sell", "both",
                 "adx_above_25", "supertrend_direction",
             ]},
        ],
    },
    "session_filter": {
        "name_fa": "فیلتر سشن",
        "params": [
            {"id": "sessions", "name_fa": "سشن‌ها", "type": "multi_select", "default": ["london", "newyork"],
             "options": [
                 {"id": "asia", "name_fa": "آسیا (00:00-09:00)"},
                 {"id": "london", "name_fa": "لندن (07:00-16:00)"},
                 {"id": "newyork", "name_fa": "نیویورک (13:00-22:00)"},
                 {"id": "overlap", "name_fa": "همپوشانی (13:00-16:00)"},
             ]},
        ],
    },
    "volatility_filter": {
        "name_fa": "فیلتر نوسان",
        "params": [
            {"id": "min_atr", "name_fa": "حداقل ATR (پیپ)", "type": "float", "default": 5},
            {"id": "max_atr", "name_fa": "حداکثر ATR (پیپ)", "type": "float", "default": 100},
            {"id": "atr_period", "name_fa": "دوره ATR", "type": "int", "default": 14},
        ],
    },
    "spread_filter": {
        "name_fa": "فیلتر اسپرد",
        "params": [
            {"id": "max_spread", "name_fa": "حداکثر اسپرد (پیپ)", "type": "float", "default": 3},
        ],
    },
    "day_filter": {
        "name_fa": "فیلتر روز هفته",
        "params": [
            {"id": "days", "name_fa": "روزها", "type": "multi_select",
             "default": ["mon", "tue", "wed", "thu", "fri"],
             "options": [
                 {"id": "mon", "name_fa": "دوشنبه"},
                 {"id": "tue", "name_fa": "سه‌شنبه"},
                 {"id": "wed", "name_fa": "چهارشنبه"},
                 {"id": "thu", "name_fa": "پنج‌شنبه"},
                 {"id": "fri", "name_fa": "جمعه"},
             ]},
        ],
    },
    "rsi_filter": {
        "name_fa": "فیلتر RSI",
        "params": [
            {"id": "period", "name_fa": "دوره", "type": "int", "default": 14},
            {"id": "no_buy_above", "name_fa": "خرید نکن بالای", "type": "int", "default": 70},
            {"id": "no_sell_below", "name_fa": "فروش نکن زیر", "type": "int", "default": 30},
        ],
    },
    "news_filter": {
        "name_fa": "فیلتر اخبار",
        "params": [
            {"id": "minutes_before", "name_fa": "دقیقه قبل از خبر", "type": "int", "default": 30},
            {"id": "minutes_after", "name_fa": "دقیقه بعد از خبر", "type": "int", "default": 30},
            {"id": "impact", "name_fa": "اهمیت", "type": "select", "default": "high",
             "options": ["high", "medium", "all"]},
        ],
    },
    "consecutive_loss_filter": {
        "name_fa": "فیلتر ضرر متوالی",
        "params": [
            {"id": "max_consecutive", "name_fa": "حداکثر ضرر متوالی", "type": "int", "default": 3},
            {"id": "cooldown_bars", "name_fa": "توقف (تعداد کندل)", "type": "int", "default": 10},
        ],
    },
}

# ══════════════════════════════════════════════
# INDICATOR CATEGORIES (for UI grouping)
# ══════════════════════════════════════════════

INDICATOR_CATEGORIES = [
    {"id": "trend", "name_fa": "روندی", "icon": "📈"},
    {"id": "oscillator", "name_fa": "اسیلاتور", "icon": "📊"},
    {"id": "momentum", "name_fa": "مومنتوم", "icon": "🚀"},
    {"id": "volatility", "name_fa": "نوسان", "icon": "📉"},
    {"id": "trend_strength", "name_fa": "قدرت روند", "icon": "💪"},
    {"id": "ichimoku", "name_fa": "ایچیموکو", "icon": "☁️"},
    {"id": "volume", "name_fa": "حجم", "icon": "📦"},
    {"id": "price", "name_fa": "قیمت و کندل", "icon": "🕯️"},
    {"id": "fibonacci", "name_fa": "فیبوناچی", "icon": "🌀"},
    {"id": "pivot", "name_fa": "پیوت", "icon": "🎯"},
]

# ══════════════════════════════════════════════
# RISK MANAGEMENT PRESETS
# ══════════════════════════════════════════════

RISK_PRESETS = {
    "conservative": {
        "name_fa": "محافظه‌کار",
        "risk_per_trade": 1.0,
        "max_daily_trades": 3,
        "max_open_trades": 2,
        "max_drawdown": 10,
        "min_rr": 2.0,
    },
    "moderate": {
        "name_fa": "متوسط",
        "risk_per_trade": 2.0,
        "max_daily_trades": 5,
        "max_open_trades": 3,
        "max_drawdown": 20,
        "min_rr": 1.5,
    },
    "aggressive": {
        "name_fa": "تهاجمی",
        "risk_per_trade": 3.0,
        "max_daily_trades": 10,
        "max_open_trades": 5,
        "max_drawdown": 30,
        "min_rr": 1.0,
    },
    "scalper": {
        "name_fa": "اسکالپر",
        "risk_per_trade": 1.5,
        "max_daily_trades": 20,
        "max_open_trades": 3,
        "max_drawdown": 15,
        "min_rr": 1.0,
    },
    "swing": {
        "name_fa": "سوئینگ",
        "risk_per_trade": 2.0,
        "max_daily_trades": 2,
        "max_open_trades": 4,
        "max_drawdown": 25,
        "min_rr": 2.5,
    },
}


# ══════════════════════════════════════════════
# STRATEGY SCHEMA
# ══════════════════════════════════════════════

def create_empty_strategy():
    return {
        "id": "",
        "name": "",
        "description": "",
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "direction": "both",  # both / buy_only / sell_only
        "entry_conditions": [],
        "entry_logic": "AND",  # AND / OR
        "exit_take_profit": [],
        "exit_stop_loss": [],
        "exit_trailing": None,
        "exit_break_even": None,
        "exit_time": None,
        "exit_indicator": None,
        "filters": [],
        "risk": {
            "preset": "moderate",
            "risk_per_trade": 2.0,
            "lot_type": "risk_percent",  # fixed / risk_percent / balance_percent
            "fixed_lot": 0.01,
            "max_daily_trades": 5,
            "max_open_trades": 3,
            "max_drawdown": 20,
            "min_rr": 1.5,
        },
        "created_at": "",
        "updated_at": "",
    }


def validate_strategy(strategy):
    """Validate a strategy config. Returns (valid, errors)."""
    errors = []

    if not strategy.get("name"):
        errors.append("نام استراتژی الزامی است")

    if not strategy.get("entry_conditions"):
        errors.append("حداقل یک شرط ورود نیاز است")

    for i, cond in enumerate(strategy.get("entry_conditions", [])):
        if not cond.get("indicator"):
            errors.append(f"شرط ورود {i+1}: اندیکاتور انتخاب نشده")
        elif cond["indicator"] not in INDICATORS:
            errors.append(f"شرط ورود {i+1}: اندیکاتور نامعتبر")
        if not cond.get("condition"):
            errors.append(f"شرط ورود {i+1}: نوع شرط انتخاب نشده")

    has_tp = bool(strategy.get("exit_take_profit"))
    has_sl = bool(strategy.get("exit_stop_loss"))
    if not has_tp and not has_sl:
        errors.append("حداقل یک TP یا SL نیاز است")

    risk = strategy.get("risk", {})
    if risk.get("risk_per_trade", 0) <= 0:
        errors.append("ریسک هر معامله باید بزرگتر از صفر باشد")
    if risk.get("risk_per_trade", 0) > 10:
        errors.append("ریسک هر معامله نباید بیشتر از ۱۰% باشد")

    return len(errors) == 0, errors


def generate_strategy_id(name):
    ts = datetime.now(timezone.utc).isoformat()
    return hashlib.md5(f"{name}{ts}".encode()).hexdigest()[:10]


def get_builder_config():
    """Return full config for Strategy Builder UI."""
    return {
        "indicators": INDICATORS,
        "indicator_categories": INDICATOR_CATEGORIES,
        "conditions": CONDITIONS,
        "compare_targets": COMPARE_TARGETS,
        "exit_types": EXIT_TYPES,
        "trade_filters": TRADE_FILTERS,
        "risk_presets": RISK_PRESETS,
    }
