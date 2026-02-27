"""
Whilber-AI — Fibonacci Strategy Pack (8 Sub-Strategies)
========================================================
FIB_01: Fib Retracement 38.2% Support/Resistance
FIB_02: Fib Retracement 50% (Half-way)
FIB_03: Fib Retracement 61.8% (Golden Ratio)
FIB_04: Fib Extension 127.2% / 161.8% Target
FIB_05: Fib Cluster (Multiple Fibs Converge)
FIB_06: Fib + RSI Combo
FIB_07: Fib + Volume Confirmation
FIB_08: Auto Fib (Dynamic Swing Detection)
"""

import numpy as np
import pandas as pd


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def _find_major_swing(df, lookback=100):
    """
    Find the most recent major swing high and swing low.
    Returns: (swing_low, swing_low_idx, swing_high, swing_high_idx, trend)
    trend: 'up' if swing_low came before swing_high, 'down' otherwise
    """
    high = df['high']
    low = df['low']
    close = df['close']
    n = min(lookback, len(df) - 1)

    if n < 20:
        return None, None, None, None, None

    recent = df.tail(n)
    sw_high = recent['high'].max()
    sw_high_idx = recent['high'].idxmax()
    sw_low = recent['low'].min()
    sw_low_idx = recent['low'].idxmin()

    # Determine trend: which came first?
    high_pos = recent.index.get_loc(sw_high_idx) if sw_high_idx in recent.index else 0
    low_pos = recent.index.get_loc(sw_low_idx) if sw_low_idx in recent.index else 0

    if low_pos < high_pos:
        trend = "up"  # Low came first, then high = uptrend
    else:
        trend = "down"  # High came first, then low = downtrend

    return sw_low, sw_low_idx, sw_high, sw_high_idx, trend


def _fib_levels(sw_low, sw_high, trend):
    """
    Calculate Fibonacci retracement levels.
    In uptrend: retracement from high back toward low
    In downtrend: retracement from low back toward high
    """
    diff = sw_high - sw_low
    levels = {}

    if trend == "up":
        # Retracing down from high
        levels["0.0"] = sw_high
        levels["23.6"] = sw_high - 0.236 * diff
        levels["38.2"] = sw_high - 0.382 * diff
        levels["50.0"] = sw_high - 0.500 * diff
        levels["61.8"] = sw_high - 0.618 * diff
        levels["78.6"] = sw_high - 0.786 * diff
        levels["100.0"] = sw_low
        # Extensions
        levels["127.2"] = sw_high + 0.272 * diff
        levels["161.8"] = sw_high + 0.618 * diff
    else:
        # Retracing up from low
        levels["0.0"] = sw_low
        levels["23.6"] = sw_low + 0.236 * diff
        levels["38.2"] = sw_low + 0.382 * diff
        levels["50.0"] = sw_low + 0.500 * diff
        levels["61.8"] = sw_low + 0.618 * diff
        levels["78.6"] = sw_low + 0.786 * diff
        levels["100.0"] = sw_high
        levels["127.2"] = sw_low - 0.272 * diff
        levels["161.8"] = sw_low - 0.618 * diff

    return levels


def _near_level(price, level, tolerance_pct=0.5):
    """Check if price is near a Fibonacci level."""
    return abs(price - level) / price * 100 < tolerance_pct


# ─────────────────────────────────────────────────────
# FIB_01: Fibonacci 38.2% Retracement
# BUY:  Price bouncing off 38.2% in uptrend
# SELL: Price rejecting 38.2% in downtrend
# ─────────────────────────────────────────────────────
def fib_01_382(df, context=None):
    sw_low, _, sw_high, _, trend = _find_major_swing(df, 100)
    if trend is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی یافت نشد"}

    levels = _fib_levels(sw_low, sw_high, trend)
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]
    fib_382 = levels["38.2"]
    dist_pct = (p - fib_382) / p * 100

    if trend == "up" and _near_level(p, fib_382, 0.5):
        if p > p_prev:  # Bouncing up
            return {"signal": "BUY", "confidence": 76,
                    "reason_fa": f"برگشت از فیبوناچی ۳۸.۲٪ در روند صعودی — سطح حمایت ({fib_382:.4f})"}
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"نزدیک فیبوناچی ۳۸.۲٪ صعودی — منتظر برگشت ({dist_pct:+.2f}%)"}

    elif trend == "down" and _near_level(p, fib_382, 0.5):
        if p < p_prev:  # Rejecting down
            return {"signal": "SELL", "confidence": 76,
                    "reason_fa": f"ریجکت از فیبوناچی ۳۸.۲٪ در روند نزولی — سطح مقاومت ({fib_382:.4f})"}
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"نزدیک فیبوناچی ۳۸.۲٪ نزولی — منتظر ریجکت ({dist_pct:+.2f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"فاصله از فیب ۳۸.۲٪ ({dist_pct:+.2f}%)"}


# ─────────────────────────────────────────────────────
# FIB_02: Fibonacci 50% Retracement
# BUY:  Price at 50% in uptrend
# SELL: Price at 50% in downtrend
# ─────────────────────────────────────────────────────
def fib_02_50(df, context=None):
    sw_low, _, sw_high, _, trend = _find_major_swing(df, 100)
    if trend is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی یافت نشد"}

    levels = _fib_levels(sw_low, sw_high, trend)
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]
    fib_50 = levels["50.0"]
    dist_pct = (p - fib_50) / p * 100

    if trend == "up" and _near_level(p, fib_50, 0.5):
        if p > p_prev:
            return {"signal": "BUY", "confidence": 78,
                    "reason_fa": f"برگشت از فیبوناچی ۵۰٪ در روند صعودی — سطح نیمه ({fib_50:.4f})"}
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"نزدیک فیبوناچی ۵۰٪ صعودی ({dist_pct:+.2f}%)"}

    elif trend == "down" and _near_level(p, fib_50, 0.5):
        if p < p_prev:
            return {"signal": "SELL", "confidence": 78,
                    "reason_fa": f"ریجکت از فیبوناچی ۵۰٪ در روند نزولی — سطح نیمه ({fib_50:.4f})"}
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"نزدیک فیبوناچی ۵۰٪ نزولی ({dist_pct:+.2f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"فاصله از فیب ۵۰٪ ({dist_pct:+.2f}%)"}


# ─────────────────────────────────────────────────────
# FIB_03: Fibonacci 61.8% (Golden Ratio)
# BUY:  Price bouncing off 61.8% in uptrend (deep retracement)
# SELL: Price rejecting 61.8% in downtrend
# ─────────────────────────────────────────────────────
def fib_03_618(df, context=None):
    sw_low, _, sw_high, _, trend = _find_major_swing(df, 100)
    if trend is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی یافت نشد"}

    levels = _fib_levels(sw_low, sw_high, trend)
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]
    fib_618 = levels["61.8"]
    dist_pct = (p - fib_618) / p * 100

    if trend == "up" and _near_level(p, fib_618, 0.6):
        if p > p_prev:
            return {"signal": "BUY", "confidence": 82,
                    "reason_fa": f"برگشت از فیبوناچی ۶۱.۸٪ (نسبت طلایی) — اصلاح عمیق تمام ({fib_618:.4f})"}
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"نزدیک فیب ۶۱.۸٪ صعودی — آخرین حمایت ({dist_pct:+.2f}%)"}

    elif trend == "down" and _near_level(p, fib_618, 0.6):
        if p < p_prev:
            return {"signal": "SELL", "confidence": 82,
                    "reason_fa": f"ریجکت از فیبوناچی ۶۱.۸٪ (نسبت طلایی) — مقاومت عمیق ({fib_618:.4f})"}
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"نزدیک فیب ۶۱.۸٪ نزولی — آخرین مقاومت ({dist_pct:+.2f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"فاصله از فیب ۶۱.۸٪ ({dist_pct:+.2f}%)"}


# ─────────────────────────────────────────────────────
# FIB_04: Fibonacci Extension 127.2% / 161.8% Target
# Price reaching extension = potential reversal / take profit zone
# ─────────────────────────────────────────────────────
def fib_04_extension(df, context=None):
    sw_low, _, sw_high, _, trend = _find_major_swing(df, 100)
    if trend is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی یافت نشد"}

    levels = _fib_levels(sw_low, sw_high, trend)
    p = df['close'].iloc[-1]
    ext_127 = levels["127.2"]
    ext_161 = levels["161.8"]

    if trend == "up":
        dist_127 = (p - ext_127) / p * 100
        dist_161 = (p - ext_161) / p * 100

        if _near_level(p, ext_161, 0.8):
            return {"signal": "SELL", "confidence": 78,
                    "reason_fa": f"قیمت به اکستنشن ۱۶۱.۸٪ رسید — هدف نهایی ({ext_161:.4f})"}
        elif _near_level(p, ext_127, 0.8):
            return {"signal": "SELL", "confidence": 68,
                    "reason_fa": f"قیمت به اکستنشن ۱۲۷.۲٪ رسید — هدف اول ({ext_127:.4f})"}
        elif p > sw_high:
            return {"signal": "BUY", "confidence": 50,
                    "reason_fa": f"بالای سقف سوئینگ — هدف بعدی ۱۲۷.۲٪ ({ext_127:.4f})"}

    elif trend == "down":
        dist_127 = (ext_127 - p) / p * 100
        dist_161 = (ext_161 - p) / p * 100

        if _near_level(p, ext_161, 0.8):
            return {"signal": "BUY", "confidence": 78,
                    "reason_fa": f"قیمت به اکستنشن ۱۶۱.۸٪ نزولی رسید — کف هدف ({ext_161:.4f})"}
        elif _near_level(p, ext_127, 0.8):
            return {"signal": "BUY", "confidence": 68,
                    "reason_fa": f"قیمت به اکستنشن ۱۲۷.۲٪ نزولی رسید — کف اول ({ext_127:.4f})"}
        elif p < sw_low:
            return {"signal": "SELL", "confidence": 50,
                    "reason_fa": f"زیر کف سوئینگ — هدف بعدی ۱۲۷.۲٪ ({ext_127:.4f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "قیمت بین سوئینگ‌ها — بدون اکستنشن فعال"}


# ─────────────────────────────────────────────────────
# FIB_05: Fibonacci Cluster (Multiple Fibs Converge)
# When multiple Fib levels from different swings align = strong S/R
# ─────────────────────────────────────────────────────
def fib_05_cluster(df, context=None):
    close = df['close']
    p = close.iloc[-1]
    high = df['high']; low = df['low']

    if len(df) < 60:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    # Find multiple swing sets (50-bar and 100-bar lookbacks)
    all_levels = []

    for lookback in [50, 80, 120]:
        sw_low, _, sw_high, _, trend = _find_major_swing(df, min(lookback, len(df)-1))
        if trend:
            levels = _fib_levels(sw_low, sw_high, trend)
            for name, val in levels.items():
                if name in ["38.2", "50.0", "61.8"]:
                    all_levels.append(val)

    if len(all_levels) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "سطوح فیب کافی برای تشخیص خوشه نیست"}

    # Find clusters: levels that are close to each other
    tolerance = p * 0.005  # 0.5%
    near_price = [lv for lv in all_levels if abs(lv - p) < p * 0.01]  # Within 1% of price
    cluster_count = len(near_price)

    if cluster_count >= 3:
        avg_level = sum(near_price) / len(near_price)
        if p > avg_level and close.iloc[-2] <= avg_level:
            return {"signal": "BUY", "confidence": 85,
                    "reason_fa": f"شکست خوشه فیبوناچی به بالا — {cluster_count} سطح هم‌پوشان ({avg_level:.4f})"}
        elif p < avg_level and close.iloc[-2] >= avg_level:
            return {"signal": "SELL", "confidence": 85,
                    "reason_fa": f"شکست خوشه فیبوناچی به پایین — {cluster_count} سطح هم‌پوشان ({avg_level:.4f})"}
        elif p > avg_level:
            return {"signal": "BUY", "confidence": 60,
                    "reason_fa": f"بالای خوشه فیبوناچی ({cluster_count} سطح) — حمایت قوی"}
        else:
            return {"signal": "SELL", "confidence": 60,
                    "reason_fa": f"زیر خوشه فیبوناچی ({cluster_count} سطح) — مقاومت قوی"}

    elif cluster_count == 2:
        avg_level = sum(near_price) / len(near_price)
        dist = (p - avg_level) / p * 100
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"۲ سطح فیب نزدیک قیمت ({dist:+.2f}%) — خوشه ضعیف"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "خوشه فیبوناچی شناسایی نشد"}


# ─────────────────────────────────────────────────────
# FIB_06: Fibonacci + RSI Combo
# BUY:  At Fib support + RSI oversold
# SELL: At Fib resistance + RSI overbought
# ─────────────────────────────────────────────────────
def fib_06_rsi_combo(df, context=None):
    sw_low, _, sw_high, _, trend = _find_major_swing(df, 100)
    if trend is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی یافت نشد"}

    levels = _fib_levels(sw_low, sw_high, trend)
    p = df['close'].iloc[-1]
    rsi = _rsi(df['close'], 14)
    r = rsi.iloc[-1] if not rsi.isna().iloc[-1] else 50

    # Check proximity to any key Fib level
    for fib_name in ["38.2", "50.0", "61.8"]:
        fib_val = levels[fib_name]
        if _near_level(p, fib_val, 0.5):
            if trend == "up" and r < 35:
                return {"signal": "BUY", "confidence": 85,
                        "reason_fa": f"فیب {fib_name}% + RSI اشباع فروش ({r:.1f}) — سیگنال ترکیبی قوی خرید"}
            elif trend == "up" and r < 45:
                return {"signal": "BUY", "confidence": 70,
                        "reason_fa": f"فیب {fib_name}% + RSI نسبتا پایین ({r:.1f}) — حمایت فیب"}
            elif trend == "down" and r > 65:
                return {"signal": "SELL", "confidence": 85,
                        "reason_fa": f"فیب {fib_name}% + RSI اشباع خرید ({r:.1f}) — سیگنال ترکیبی قوی فروش"}
            elif trend == "down" and r > 55:
                return {"signal": "SELL", "confidence": 70,
                        "reason_fa": f"فیب {fib_name}% + RSI نسبتا بالا ({r:.1f}) — مقاومت فیب"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ترکیب فیب+RSI فعال نیست (RSI={r:.1f})"}


# ─────────────────────────────────────────────────────
# FIB_07: Fibonacci + Volume Confirmation
# BUY:  At Fib support + rising volume
# SELL: At Fib resistance + rising volume
# ─────────────────────────────────────────────────────
def fib_07_volume(df, context=None):
    sw_low, _, sw_high, _, trend = _find_major_swing(df, 100)
    if trend is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی یافت نشد"}

    vol = df.get('tick_volume', df.get('volume', None))
    if vol is None or vol.sum() == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    levels = _fib_levels(sw_low, sw_high, trend)
    p = df['close'].iloc[-1]
    avg_vol = _sma(vol, 20)
    if avg_vol.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    vol_ratio = vol.iloc[-1] / avg_vol.iloc[-1] if avg_vol.iloc[-1] > 0 else 1
    high_vol = vol_ratio > 1.5

    for fib_name in ["38.2", "50.0", "61.8"]:
        fib_val = levels[fib_name]
        if _near_level(p, fib_val, 0.5):
            if trend == "up" and high_vol and p > df['close'].iloc[-2]:
                return {"signal": "BUY", "confidence": 82,
                        "reason_fa": f"فیب {fib_name}% + حجم بالا ({vol_ratio:.1f}x) + کندل صعودی — تایید حمایت"}
            elif trend == "down" and high_vol and p < df['close'].iloc[-2]:
                return {"signal": "SELL", "confidence": 82,
                        "reason_fa": f"فیب {fib_name}% + حجم بالا ({vol_ratio:.1f}x) + کندل نزولی — تایید مقاومت"}
            elif trend == "up":
                return {"signal": "BUY", "confidence": 58,
                        "reason_fa": f"نزدیک فیب {fib_name}% صعودی (حجم {vol_ratio:.1f}x)"}
            elif trend == "down":
                return {"signal": "SELL", "confidence": 58,
                        "reason_fa": f"نزدیک فیب {fib_name}% نزولی (حجم {vol_ratio:.1f}x)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ترکیب فیب+حجم فعال نیست (حجم {vol_ratio:.1f}x)"}


# ─────────────────────────────────────────────────────
# FIB_08: Auto Fibonacci (Dynamic with Best Swing Detection)
# Automatically finds the best swing and reports nearest Fib level
# ─────────────────────────────────────────────────────
def fib_08_auto(df, context=None):
    sw_low, _, sw_high, _, trend = _find_major_swing(df, 100)
    if trend is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی یافت نشد"}

    levels = _fib_levels(sw_low, sw_high, trend)
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]

    # Find nearest Fib level
    closest_name = None
    closest_dist = float('inf')
    for name in ["23.6", "38.2", "50.0", "61.8", "78.6"]:
        dist = abs(p - levels[name])
        if dist < closest_dist:
            closest_dist = dist
            closest_name = name

    if closest_name is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "محاسبه فیب ممکن نشد"}

    nearest_val = levels[closest_name]
    dist_pct = (p - nearest_val) / p * 100

    # Determine position in Fib structure
    fib_position = (p - sw_low) / (sw_high - sw_low) * 100 if sw_high != sw_low else 50

    if abs(dist_pct) < 0.5:  # Near a Fib level
        if trend == "up" and p > p_prev:
            conf = 75 if closest_name in ["50.0", "61.8"] else 65
            return {"signal": "BUY", "confidence": conf,
                    "reason_fa": f"برگشت از فیب {closest_name}% (موقعیت {fib_position:.0f}%) — روند صعودی"}
        elif trend == "down" and p < p_prev:
            conf = 75 if closest_name in ["50.0", "61.8"] else 65
            return {"signal": "SELL", "confidence": conf,
                    "reason_fa": f"ریجکت از فیب {closest_name}% (موقعیت {fib_position:.0f}%) — روند نزولی"}
        else:
            return {"signal": "NEUTRAL", "confidence": 0,
                    "reason_fa": f"نزدیک فیب {closest_name}% — منتظر تایید (موقعیت {fib_position:.0f}%)"}

    # Not near any level — just report position
    if trend == "up":
        if fib_position > 80:
            return {"signal": "BUY", "confidence": 45,
                    "reason_fa": f"بالای فیب ۷۸.۶% — روند صعودی قوی (موقعیت {fib_position:.0f}%)"}
        elif fib_position < 30:
            return {"signal": "BUY", "confidence": 55,
                    "reason_fa": f"اصلاح عمیق — نزدیک کف سوئینگ (موقعیت {fib_position:.0f}%)"}
    elif trend == "down":
        if fib_position < 20:
            return {"signal": "SELL", "confidence": 45,
                    "reason_fa": f"زیر فیب ۷۸.۶% — روند نزولی قوی (موقعیت {fib_position:.0f}%)"}
        elif fib_position > 70:
            return {"signal": "SELL", "confidence": 55,
                    "reason_fa": f"اصلاح عمیق بالا — نزدیک سقف سوئینگ (موقعیت {fib_position:.0f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"فیب خودکار — موقعیت {fib_position:.0f}%, نزدیک‌ترین سطح: {closest_name}% ({dist_pct:+.2f}%)"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

FIB_STRATEGIES = [
    {"id": "FIB_01", "name": "Fib 38.2% Retracement", "name_fa": "اصلاح فیبوناچی ۳۸.۲٪", "func": fib_01_382},
    {"id": "FIB_02", "name": "Fib 50% Half-way", "name_fa": "اصلاح فیبوناچی ۵۰٪", "func": fib_02_50},
    {"id": "FIB_03", "name": "Fib 61.8% Golden Ratio", "name_fa": "فیبوناچی ۶۱.۸٪ نسبت طلایی", "func": fib_03_618},
    {"id": "FIB_04", "name": "Fib Extension Target", "name_fa": "اکستنشن فیبوناچی هدف", "func": fib_04_extension},
    {"id": "FIB_05", "name": "Fib Cluster Zone", "name_fa": "خوشه فیبوناچی", "func": fib_05_cluster},
    {"id": "FIB_06", "name": "Fib + RSI Combo", "name_fa": "فیبوناچی + RSI", "func": fib_06_rsi_combo},
    {"id": "FIB_07", "name": "Fib + Volume Confirm", "name_fa": "فیبوناچی + تایید حجم", "func": fib_07_volume},
    {"id": "FIB_08", "name": "Auto Fibonacci", "name_fa": "فیبوناچی خودکار", "func": fib_08_auto},
]
