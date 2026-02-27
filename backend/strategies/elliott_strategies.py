"""
Whilber-AI — Elliott Wave Strategies
======================================
EW_01: Wave Count (تشخیص موج فعلی)
EW_02: Wave 3 Entry (ورود موج ۳)
EW_03: Wave 5 Entry (ورود موج ۵)
EW_04: ABC Correction (اصلاح ABC)
EW_05: Fibonacci Wave (فیبو + الیوت)
EW_06: Wave 3 Extension (گسترش موج ۳)
"""

import numpy as np


def _swing_points(df, order=5):
    """Find swing highs and lows with index."""
    highs, lows = [], []
    h, l = df["high"].values, df["low"].values
    for i in range(order, len(df) - order):
        if all(h[i] >= h[i - j] for j in range(1, order + 1)) and \
           all(h[i] >= h[i + j] for j in range(1, order + 1)):
            highs.append((i, h[i]))
        if all(l[i] <= l[i - j] for j in range(1, order + 1)) and \
           all(l[i] <= l[i + j] for j in range(1, order + 1)):
            lows.append((i, l[i]))
    return highs, lows


def _alternating_swings(df, order=5, count=8):
    """Get alternating swing sequence."""
    highs, lows = _swing_points(df, order)
    all_sw = [(i, p, "H") for i, p in highs] + [(i, p, "L") for i, p in lows]
    all_sw.sort(key=lambda x: x[0])
    if len(all_sw) < 3:
        return []
    # Remove consecutive same types
    clean = [all_sw[0]]
    for s in all_sw[1:]:
        if s[2] != clean[-1][2]:
            clean.append(s)
    return clean[-count:] if len(clean) >= count else clean


def _detect_impulse(swings):
    """
    Detect 5-wave impulse pattern from swing points.
    Returns: (is_bullish, wave_num, waves_dict) or None
    """
    if len(swings) < 6:
        return None

    # Try bullish impulse: L-H-L-H-L-H (wave 0,1,2,3,4,5)
    last6 = swings[-6:]
    types = [s[2] for s in last6]
    prices = [s[1] for s in last6]

    # Bullish: starts Low
    if types[0] == "L" and types == ["L", "H", "L", "H", "L", "H"]:
        w0, w1, w2, w3, w4, w5 = prices
        # Elliott rules:
        # Wave 2 doesn't retrace 100% of wave 1
        if w2 > w0 and w1 > w0:
            # Wave 3 is not the shortest
            wave1 = w1 - w0
            wave3 = w3 - w2
            wave5 = w5 - w4
            if wave3 > wave1 * 0.5:  # Wave 3 reasonable
                if w3 > w1:  # Wave 3 exceeds wave 1
                    # Determine current position
                    if w5 > w3:
                        return ("bullish", 5, {"w0": w0, "w1": w1, "w2": w2,
                                               "w3": w3, "w4": w4, "w5": w5})
                    elif w4 < w3:
                        return ("bullish", 4, {"w0": w0, "w1": w1, "w2": w2,
                                               "w3": w3, "w4": w4})

    # Bearish: starts High
    if types[0] == "H" and types == ["H", "L", "H", "L", "H", "L"]:
        w0, w1, w2, w3, w4, w5 = prices
        if w2 < w0 and w1 < w0:
            wave1 = w0 - w1
            wave3 = w2 - w3
            if wave3 > wave1 * 0.5:
                if w3 < w1:
                    if w5 < w3:
                        return ("bearish", 5, {"w0": w0, "w1": w1, "w2": w2,
                                               "w3": w3, "w4": w4, "w5": w5})
                    elif w4 > w3:
                        return ("bearish", 4, {"w0": w0, "w1": w1, "w2": w2,
                                               "w3": w3, "w4": w4})
    return None


# ── EW_01: Wave Count ───────────────────────────────

def elliott_wave_count(df, context=None):
    """شمارش موج الیوت — تشخیص موج فعلی"""
    swings = _alternating_swings(df, order=5, count=8)
    if len(swings) < 4:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "شمارش الیوت — سوئینگ کافی نیست"}

    result = _detect_impulse(swings)
    price = df["close"].iloc[-1]

    if result:
        direction, wave_num, waves = result
        if direction == "bullish":
            if wave_num <= 3:
                return {"signal": "BUY", "confidence": 60,
                        "reason_fa": f"الیوت صعودی — موج {wave_num} فعال | w1={waves['w1']:.5g} w3={waves.get('w3','?')}"}
            elif wave_num == 4:
                return {"signal": "BUY", "confidence": 50,
                        "reason_fa": f"الیوت صعودی — اصلاح موج ۴ | منتظر موج ۵"}
            else:
                return {"signal": "NEUTRAL", "confidence": 40,
                        "reason_fa": f"الیوت صعودی — موج ۵ کامل | احتمال اصلاح ABC"}
        else:
            if wave_num <= 3:
                return {"signal": "SELL", "confidence": 60,
                        "reason_fa": f"الیوت نزولی — موج {wave_num} فعال"}
            elif wave_num == 4:
                return {"signal": "SELL", "confidence": 50,
                        "reason_fa": f"الیوت نزولی — اصلاح موج ۴ | منتظر موج ۵ نزولی"}
            else:
                return {"signal": "NEUTRAL", "confidence": 40,
                        "reason_fa": f"الیوت نزولی — موج ۵ کامل | احتمال بازگشت"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "الیوت — الگوی ۵ موجی شناسایی نشد"}


# ── EW_02: Wave 3 Entry ─────────────────────────────

def elliott_wave3_entry(df, context=None):
    """ورود موج ۳ الیوت — قوی‌ترین موج"""
    swings = _alternating_swings(df, order=5, count=6)
    if len(swings) < 4:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "موج ۳ — سوئینگ کافی نیست"}

    prices = [s[1] for s in swings]
    types = [s[2] for s in swings]
    price = df["close"].iloc[-1]

    # Bullish wave 3: after wave 2 pullback (L-H-L pattern, price breaking above H)
    if len(swings) >= 3:
        if types[-3] == "L" and types[-2] == "H" and types[-1] == "L":
            w0 = prices[-3]
            w1 = prices[-2]
            w2 = prices[-1]
            # Wave 2 retraced 38-78% of wave 1
            wave1 = w1 - w0
            retrace = (w1 - w2) / wave1 if wave1 > 0 else 0
            if 0.30 <= retrace <= 0.85 and w2 > w0:
                if price > w2 and price < w1 * 1.02:
                    conf = 65 if 0.50 <= retrace <= 0.618 else 55
                    return {"signal": "BUY", "confidence": conf,
                            "reason_fa": f"موج ۳ صعودی — W2 ریتریس {retrace:.1%} | ورود={price:.5g} هدف: بالای {w1:.5g}"}

    # Bearish wave 3
    if len(swings) >= 3:
        if types[-3] == "H" and types[-2] == "L" and types[-1] == "H":
            w0 = prices[-3]
            w1 = prices[-2]
            w2 = prices[-1]
            wave1 = w0 - w1
            retrace = (w2 - w1) / wave1 if wave1 > 0 else 0
            if 0.30 <= retrace <= 0.85 and w2 < w0:
                if price < w2 and price > w1 * 0.98:
                    conf = 65 if 0.50 <= retrace <= 0.618 else 55
                    return {"signal": "SELL", "confidence": conf,
                            "reason_fa": f"موج ۳ نزولی — W2 ریتریس {retrace:.1%} | ورود={price:.5g}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "موج ۳ — شرایط ورود فراهم نیست"}


# ── EW_03: Wave 5 Entry ─────────────────────────────

def elliott_wave5_entry(df, context=None):
    """ورود موج ۵ الیوت — آخرین موج حرکتی"""
    swings = _alternating_swings(df, order=5, count=8)
    result = _detect_impulse(swings)
    price = df["close"].iloc[-1]

    if result and result[1] == 4:
        direction, _, waves = result
        if direction == "bullish":
            w3 = waves["w3"]
            w4 = waves["w4"]
            # Wave 4 should not overlap wave 1
            if w4 > waves["w1"]:
                target = w3 + abs(waves["w1"] - waves["w0"]) * 0.618
                return {"signal": "BUY", "confidence": 55,
                        "reason_fa": f"موج ۵ صعودی — W4={w4:.5g} هدف≈{target:.5g} | TP محافظه‌کار"}
        else:
            w3 = waves["w3"]
            w4 = waves["w4"]
            if w4 < waves["w1"]:
                return {"signal": "SELL", "confidence": 55,
                        "reason_fa": f"موج ۵ نزولی — W4={w4:.5g} | TP محافظه‌کار"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "موج ۵ — موج ۴ شناسایی نشد"}


# ── EW_04: ABC Correction ───────────────────────────

def elliott_abc_correction(df, context=None):
    """اصلاح ABC الیوت — ورود پس از اتمام اصلاح"""
    swings = _alternating_swings(df, order=5, count=6)
    if len(swings) < 5:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "اصلاح ABC — سوئینگ کافی نیست"}

    price = df["close"].iloc[-1]
    # After bullish impulse (5 waves up), look for ABC down
    # ABC: H-L-H-L pattern at end
    types = [s[2] for s in swings[-4:]]
    prices = [s[1] for s in swings[-4:]]

    # Bearish correction after uptrend (ABC down: H-L-H-L)
    if types == ["H", "L", "H", "L"]:
        A_high, B_low, C_high, end_low = prices
        ab = A_high - B_low
        bc = C_high - B_low
        if ab > 0 and 0.30 <= bc / ab <= 0.78:
            # C didn't exceed A → valid ABC, expect reversal up
            if C_high < A_high and price > end_low:
                return {"signal": "BUY", "confidence": 58,
                        "reason_fa": f"ABC نزولی کامل — C={C_high:.5g}<A={A_high:.5g} | بازگشت صعودی"}

    # Bullish correction after downtrend (ABC up: L-H-L-H)
    if types == ["L", "H", "L", "H"]:
        A_low, B_high, C_low, end_high = prices
        ab = B_high - A_low
        bc = B_high - C_low
        if ab > 0 and 0.30 <= bc / ab <= 0.78:
            if C_low > A_low and price < end_high:
                return {"signal": "SELL", "confidence": 58,
                        "reason_fa": f"ABC صعودی کامل — C={C_low:.5g}>A={A_low:.5g} | بازگشت نزولی"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "اصلاح ABC — الگو شناسایی نشد"}


# ── EW_05: Fibonacci Wave ───────────────────────────

def elliott_fib_wave(df, context=None):
    """فیبوناچی + الیوت — ترکیب سطوح فیبو با شمارش موج"""
    swings = _alternating_swings(df, order=5, count=6)
    if len(swings) < 4:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "فیبو-الیوت — سوئینگ کافی نیست"}

    price = df["close"].iloc[-1]
    # Get last significant move
    types = [s[2] for s in swings]
    prices = [s[1] for s in swings]

    # Bullish: price at 50-61.8% retracement of last up-swing
    for i in range(len(swings) - 2, 0, -1):
        if types[i] == "H" and types[i - 1] == "L":
            low = prices[i - 1]
            high = prices[i]
            move = high - low
            if move > 0:
                retrace = (high - price) / move
                if 0.45 <= retrace <= 0.68:
                    fib_level = "50%" if retrace < 0.55 else "61.8%"
                    return {"signal": "BUY", "confidence": 62,
                            "reason_fa": f"فیبو-الیوت — قیمت روی {fib_level} ریتریس | L={low:.5g} H={high:.5g}"}
                elif 0.33 <= retrace <= 0.44:
                    return {"signal": "BUY", "confidence": 52,
                            "reason_fa": f"فیبو-الیوت — قیمت روی 38.2% ریتریس | روند قوی"}
            break

    # Bearish: price at retracement of last down-swing
    for i in range(len(swings) - 2, 0, -1):
        if types[i] == "L" and types[i - 1] == "H":
            high = prices[i - 1]
            low = prices[i]
            move = high - low
            if move > 0:
                retrace = (price - low) / move
                if 0.45 <= retrace <= 0.68:
                    fib_level = "50%" if retrace < 0.55 else "61.8%"
                    return {"signal": "SELL", "confidence": 62,
                            "reason_fa": f"فیبو-الیوت — قیمت روی {fib_level} ریتریس نزولی | H={high:.5g} L={low:.5g}"}
            break

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "فیبو-الیوت — قیمت روی سطح فیبوی مهمی نیست"}


# ── EW_06: Wave 3 Extension ─────────────────────────

def elliott_wave3_extension(df, context=None):
    """گسترش موج ۳ الیوت — موج ۳ بیش از 161.8% موج ۱"""
    swings = _alternating_swings(df, order=5, count=8)
    result = _detect_impulse(swings)
    price = df["close"].iloc[-1]

    if result and result[1] >= 3:
        direction, wave_num, waves = result
        w0, w1, w2, w3 = waves["w0"], waves["w1"], waves["w2"], waves["w3"]

        if direction == "bullish":
            wave1_size = w1 - w0
            wave3_size = w3 - w2
            if wave1_size > 0:
                ext = wave3_size / wave1_size
                if ext >= 1.5:
                    ext_pct = f"{ext:.1%}"
                    return {"signal": "BUY", "confidence": 70,
                            "reason_fa": f"موج ۳ گسترش‌یافته {ext_pct} — حرکت قوی | W3={w3:.5g} ادامه‌دار"}
        else:
            wave1_size = w0 - w1
            wave3_size = w2 - w3
            if wave1_size > 0:
                ext = wave3_size / wave1_size
                if ext >= 1.5:
                    return {"signal": "SELL", "confidence": 70,
                            "reason_fa": f"موج ۳ گسترش‌یافته {ext:.1%} نزولی — W3={w3:.5g}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "گسترش موج ۳ — الگوی فعالی یافت نشد"}


# ── Export ──────────────────────────────────────────

EW_STRATEGIES = [
    {"id": "EW_01", "name": "EW_01", "name_fa": "الیوت: شمارش موج", "func": elliott_wave_count},
    {"id": "EW_02", "name": "EW_02", "name_fa": "الیوت: ورود موج ۳", "func": elliott_wave3_entry},
    {"id": "EW_03", "name": "EW_03", "name_fa": "الیوت: ورود موج ۵", "func": elliott_wave5_entry},
    {"id": "EW_04", "name": "EW_04", "name_fa": "الیوت: اصلاح ABC", "func": elliott_abc_correction},
    {"id": "EW_05", "name": "EW_05", "name_fa": "الیوت: فیبوناچی موجی", "func": elliott_fib_wave},
    {"id": "EW_06", "name": "EW_06", "name_fa": "الیوت: گسترش موج ۳", "func": elliott_wave3_extension},
]
