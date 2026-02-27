"""
Whilber-AI — Chart Pattern Strategies
========================================
CP_01: Head & Shoulders
CP_02: Inverse Head & Shoulders
CP_03: Symmetric Triangle
CP_04: Ascending Triangle
CP_05: Descending Triangle
CP_06: Rising Wedge
CP_07: Falling Wedge
CP_08: Flag & Pennant
CP_09: Rectangle (Range)
CP_10: Cup & Handle
CP_11: Rounding Bottom
"""

import numpy as np


def _swing_points(df, order=5):
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


def _near_pct(a, b, pct=0.005):
    """Check if a ≈ b within pct."""
    if b == 0:
        return False
    return abs(a - b) / abs(b) <= pct


def _linear_slope(points):
    """Fit linear regression to (index, price) points, return slope."""
    if len(points) < 2:
        return 0
    x = np.array([p[0] for p in points], dtype=float)
    y = np.array([p[1] for p in points], dtype=float)
    if len(x) < 2:
        return 0
    m = np.polyfit(x, y, 1)[0]
    return m


# ── CP_01: Head & Shoulders ────────────────────────

def cp_head_shoulders(df, context=None):
    """سر و شانه — الگوی بازگشتی نزولی"""
    highs, lows = _swing_points(df, order=5)
    price = df["close"].iloc[-1]

    if len(highs) < 3 or len(lows) < 2:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "سر و شانه — سوئینگ کافی نیست"}

    # Last 3 highs
    h = [p for _, p in highs[-3:]]
    l = [p for _, p in lows[-2:]]

    # Head should be highest, shoulders roughly equal
    if h[1] > h[0] and h[1] > h[2]:
        shoulder_diff = abs(h[0] - h[2]) / h[1]
        if shoulder_diff < 0.03:  # Shoulders within 3%
            neckline = (l[0] + l[1]) / 2
            # Price breaking below neckline
            if price < neckline:
                height = h[1] - neckline
                target = neckline - height
                return {"signal": "SELL", "confidence": 72,
                        "reason_fa": f"سر و شانه — شکست گردن {neckline:.5g} | سر={h[1]:.5g} هدف≈{target:.5g}"}
            elif price < neckline * 1.01:
                return {"signal": "SELL", "confidence": 55,
                        "reason_fa": f"سر و شانه در حال شکل‌گیری — گردن={neckline:.5g} | نزدیک شکست"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "سر و شانه — الگو شناسایی نشد"}


# ── CP_02: Inverse Head & Shoulders ────────────────

def cp_inv_head_shoulders(df, context=None):
    """سر و شانه معکوس — الگوی بازگشتی صعودی"""
    highs, lows = _swing_points(df, order=5)
    price = df["close"].iloc[-1]

    if len(lows) < 3 or len(highs) < 2:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "سر و شانه معکوس — سوئینگ کافی نیست"}

    l = [p for _, p in lows[-3:]]
    h = [p for _, p in highs[-2:]]

    # Head (middle low) should be lowest
    if l[1] < l[0] and l[1] < l[2]:
        shoulder_diff = abs(l[0] - l[2]) / abs(l[1]) if l[1] != 0 else 1
        if shoulder_diff < 0.03:
            neckline = (h[0] + h[1]) / 2
            if price > neckline:
                height = neckline - l[1]
                target = neckline + height
                return {"signal": "BUY", "confidence": 72,
                        "reason_fa": f"سر و شانه معکوس — شکست گردن {neckline:.5g} | هدف≈{target:.5g}"}
            elif price > neckline * 0.99:
                return {"signal": "BUY", "confidence": 55,
                        "reason_fa": f"سر و شانه معکوس — نزدیک گردن {neckline:.5g}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "سر و شانه معکوس — الگو شناسایی نشد"}


# ── CP_03: Symmetric Triangle ──────────────────────

def cp_sym_triangle(df, context=None):
    """مثلث متقارن — شکست هر دو جهت"""
    highs, lows = _swing_points(df, order=4)
    price = df["close"].iloc[-1]

    if len(highs) < 3 or len(lows) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "مثلث متقارن — سوئینگ کافی نیست"}

    h_slope = _linear_slope(highs[-3:])
    l_slope = _linear_slope(lows[-3:])

    # Symmetric: highs descending, lows ascending (converging)
    if h_slope < 0 and l_slope > 0:
        last_high = highs[-1][1]
        last_low = lows[-1][1]
        width = last_high - last_low
        mid = (last_high + last_low) / 2

        if price > last_high:
            return {"signal": "BUY", "confidence": 65,
                    "reason_fa": f"مثلث متقارن — شکست بالا از {last_high:.5g} | TP≈{last_high + width:.5g}"}
        elif price < last_low:
            return {"signal": "SELL", "confidence": 65,
                    "reason_fa": f"مثلث متقارن — شکست پایین از {last_low:.5g} | TP≈{last_low - width:.5g}"}
        else:
            return {"signal": "NEUTRAL", "confidence": 35,
                    "reason_fa": f"مثلث متقارن — فشردگی | سقف={last_high:.5g} کف={last_low:.5g} منتظر شکست"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "مثلث متقارن — الگو شناسایی نشد"}


# ── CP_04: Ascending Triangle ──────────────────────

def cp_asc_triangle(df, context=None):
    """مثلث صعودی — سقف مسطح + کف‌های بالاتر"""
    highs, lows = _swing_points(df, order=4)
    price = df["close"].iloc[-1]

    if len(highs) < 2 or len(lows) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "مثلث صعودی — سوئینگ کافی نیست"}

    # Flat top
    h_vals = [p for _, p in highs[-3:]]
    h_flat = max(h_vals) - min(h_vals)
    avg_h = np.mean(h_vals)
    flat_pct = h_flat / avg_h if avg_h > 0 else 1

    # Rising bottoms
    l_slope = _linear_slope(lows[-3:])

    if flat_pct < 0.015 and l_slope > 0:  # Top flat within 1.5%, lows rising
        resistance = avg_h
        if price > resistance:
            return {"signal": "BUY", "confidence": 70,
                    "reason_fa": f"مثلث صعودی — شکست مقاومت {resistance:.5g} | صعودی قوی"}
        elif price > resistance * 0.99:
            return {"signal": "BUY", "confidence": 55,
                    "reason_fa": f"مثلث صعودی — نزدیک مقاومت {resistance:.5g} | احتمال شکست بالا"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "مثلث صعودی — الگو شناسایی نشد"}


# ── CP_05: Descending Triangle ─────────────────────

def cp_desc_triangle(df, context=None):
    """مثلث نزولی — کف مسطح + سقف‌های پایین‌تر"""
    highs, lows = _swing_points(df, order=4)
    price = df["close"].iloc[-1]

    if len(lows) < 2 or len(highs) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "مثلث نزولی — سوئینگ کافی نیست"}

    l_vals = [p for _, p in lows[-3:]]
    l_flat = max(l_vals) - min(l_vals)
    avg_l = np.mean(l_vals)
    flat_pct = l_flat / avg_l if avg_l > 0 else 1

    h_slope = _linear_slope(highs[-3:])

    if flat_pct < 0.015 and h_slope < 0:
        support = avg_l
        if price < support:
            return {"signal": "SELL", "confidence": 70,
                    "reason_fa": f"مثلث نزولی — شکست حمایت {support:.5g} | نزولی قوی"}
        elif price < support * 1.01:
            return {"signal": "SELL", "confidence": 55,
                    "reason_fa": f"مثلث نزولی — نزدیک حمایت {support:.5g} | احتمال شکست"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "مثلث نزولی — الگو شناسایی نشد"}


# ── CP_06: Rising Wedge ────────────────────────────

def cp_rising_wedge(df, context=None):
    """کنج صعودی — نزولی (هر دو خط بالا ولی همگرا)"""
    highs, lows = _swing_points(df, order=4)
    price = df["close"].iloc[-1]

    if len(highs) < 3 or len(lows) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "کنج صعودی — سوئینگ کافی نیست"}

    h_slope = _linear_slope(highs[-3:])
    l_slope = _linear_slope(lows[-3:])

    # Both rising but converging (lows rising faster than highs)
    if h_slope > 0 and l_slope > 0 and l_slope > h_slope * 0.5:
        last_low = lows[-1][1]
        if price < last_low:
            return {"signal": "SELL", "confidence": 65,
                    "reason_fa": f"کنج صعودی — شکست پایین | نزولی | حمایت شکسته={last_low:.5g}"}
        else:
            return {"signal": "SELL", "confidence": 45,
                    "reason_fa": f"کنج صعودی در حال شکل‌گیری — الگوی نزولی | منتظر شکست پایین"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "کنج صعودی — الگو شناسایی نشد"}


# ── CP_07: Falling Wedge ───────────────────────────

def cp_falling_wedge(df, context=None):
    """کنج نزولی — صعودی (هر دو خط پایین ولی همگرا)"""
    highs, lows = _swing_points(df, order=4)
    price = df["close"].iloc[-1]

    if len(highs) < 3 or len(lows) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "کنج نزولی — سوئینگ کافی نیست"}

    h_slope = _linear_slope(highs[-3:])
    l_slope = _linear_slope(lows[-3:])

    if h_slope < 0 and l_slope < 0 and h_slope > l_slope * 0.5:
        last_high = highs[-1][1]
        if price > last_high:
            return {"signal": "BUY", "confidence": 65,
                    "reason_fa": f"کنج نزولی — شکست بالا | صعودی | مقاومت شکسته={last_high:.5g}"}
        else:
            return {"signal": "BUY", "confidence": 45,
                    "reason_fa": f"کنج نزولی در حال شکل‌گیری — الگوی صعودی | منتظر شکست بالا"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "کنج نزولی — الگو شناسایی نشد"}


# ── CP_08: Flag & Pennant ──────────────────────────

def cp_flag_pennant(df, context=None):
    """پرچم و پرچم سه‌گوش — الگوی ادامه‌دهنده"""
    price = df["close"].iloc[-1]
    c = df["close"].values

    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "پرچم — داده کافی نیست"}

    # Detect flagpole: strong move in last 20-30 bars
    pole_start = c[-30]
    pole_end_area = c[-15:-10]
    pole_end = np.mean(pole_end_area)
    pole_move = (pole_end - pole_start) / pole_start * 100

    # Flag body: last 10-15 bars should be consolidating
    flag_body = c[-12:]
    flag_range = (max(flag_body) - min(flag_body)) / np.mean(flag_body) * 100
    flag_slope = np.polyfit(range(len(flag_body)), flag_body, 1)[0]

    # Bullish flag: strong up-move + slight down/sideways consolidation
    if pole_move > 2 and flag_range < abs(pole_move) * 0.5:
        if flag_slope <= 0 or flag_range < 1.5:  # Flag goes down or sideways
            if price > max(flag_body) * 0.998:
                target = price + abs(pole_end - pole_start)
                return {"signal": "BUY", "confidence": 62,
                        "reason_fa": f"پرچم صعودی — میله={pole_move:.1f}% فشردگی={flag_range:.1f}% | TP≈{target:.5g}"}

    # Bearish flag
    if pole_move < -2 and flag_range < abs(pole_move) * 0.5:
        if flag_slope >= 0 or flag_range < 1.5:
            if price < min(flag_body) * 1.002:
                return {"signal": "SELL", "confidence": 62,
                        "reason_fa": f"پرچم نزولی — میله={pole_move:.1f}% | ادامه نزول"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "پرچم — الگوی فعالی شناسایی نشد"}


# ── CP_09: Rectangle (Range) ───────────────────────

def cp_rectangle(df, context=None):
    """مستطیل (رنج) — شکست بالا یا پایین"""
    highs, lows = _swing_points(df, order=4)
    price = df["close"].iloc[-1]

    if len(highs) < 2 or len(lows) < 2:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "مستطیل — سوئینگ کافی نیست"}

    h_vals = [p for _, p in highs[-3:]]
    l_vals = [p for _, p in lows[-3:]]

    h_range = (max(h_vals) - min(h_vals)) / np.mean(h_vals)
    l_range = (max(l_vals) - min(l_vals)) / np.mean(l_vals)

    # Both tops and bottoms roughly flat
    if h_range < 0.015 and l_range < 0.015:
        resistance = np.mean(h_vals)
        support = np.mean(l_vals)
        rect_height = resistance - support

        if price > resistance:
            target = resistance + rect_height
            return {"signal": "BUY", "confidence": 68,
                    "reason_fa": f"مستطیل — شکست بالا {resistance:.5g} | TP≈{target:.5g}"}
        elif price < support:
            target = support - rect_height
            return {"signal": "SELL", "confidence": 68,
                    "reason_fa": f"مستطیل — شکست پایین {support:.5g} | TP≈{target:.5g}"}
        else:
            pct = (price - support) / rect_height * 100 if rect_height > 0 else 50
            return {"signal": "NEUTRAL", "confidence": 30,
                    "reason_fa": f"مستطیل — رنج | حمایت={support:.5g} مقاومت={resistance:.5g} | موقعیت {pct:.0f}%"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "مستطیل — الگو شناسایی نشد"}


# ── CP_10: Cup & Handle ────────────────────────────

def cp_cup_handle(df, context=None):
    """فنجان و دسته — الگوی صعودی"""
    c = df["close"].values
    price = c[-1]

    if len(c) < 40:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "فنجان — داده کافی نیست"}

    # Look for U-shape in last 40 bars
    cup_data = c[-40:-5]
    handle_data = c[-8:]

    cup_min_idx = np.argmin(cup_data)
    cup_min = cup_data[cup_min_idx]
    cup_left = cup_data[0]
    cup_right = cup_data[-1]

    # Cup: left and right rims roughly equal, minimum in middle third
    left_third = len(cup_data) // 3
    right_third = len(cup_data) * 2 // 3

    if left_third < cup_min_idx < right_third:
        rim_diff = abs(cup_left - cup_right) / cup_left
        if rim_diff < 0.03:  # Rims within 3%
            rim_level = max(cup_left, cup_right)
            depth = (rim_level - cup_min) / rim_level

            if 0.05 <= depth <= 0.30:  # Cup depth 5-30%
                # Handle: slight pullback
                handle_max = max(handle_data)
                handle_min = min(handle_data)
                handle_depth = (handle_max - handle_min) / rim_level

                if handle_depth < depth * 0.5:  # Handle < half of cup
                    if price > rim_level:
                        target = rim_level + (rim_level - cup_min)
                        return {"signal": "BUY", "confidence": 70,
                                "reason_fa": f"فنجان و دسته — شکست لبه {rim_level:.5g} | هدف≈{target:.5g}"}
                    elif price > rim_level * 0.99:
                        return {"signal": "BUY", "confidence": 55,
                                "reason_fa": f"فنجان و دسته — نزدیک لبه {rim_level:.5g} | عمق={depth:.1%}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "فنجان و دسته — الگو شناسایی نشد"}


# ── CP_11: Rounding Bottom ─────────────────────────

def cp_rounding_bottom(df, context=None):
    """کف گرد — الگوی صعودی بلندمدت"""
    c = df["close"].values
    price = c[-1]

    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "کف گرد — داده کافی نیست"}

    window = c[-30:]
    min_idx = np.argmin(window)
    min_val = window[min_idx]

    # Minimum should be in middle area
    if min_idx < 8 or min_idx > 22:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "کف گرد — کمینه در وسط نیست"}

    # Left side descending, right side ascending
    left = window[:min_idx]
    right = window[min_idx:]

    if len(left) >= 3 and len(right) >= 3:
        left_slope = np.polyfit(range(len(left)), left, 1)[0]
        right_slope = np.polyfit(range(len(right)), right, 1)[0]

        if left_slope < 0 and right_slope > 0:
            # U-shape confirmed
            neckline = max(window[0], window[-1])
            depth = (neckline - min_val) / neckline

            if depth >= 0.03:  # At least 3% depth
                if price > neckline:
                    return {"signal": "BUY", "confidence": 65,
                            "reason_fa": f"کف گرد — شکست گردن {neckline:.5g} | عمق={depth:.1%} | صعودی"}
                elif price > neckline * 0.99:
                    return {"signal": "BUY", "confidence": 50,
                            "reason_fa": f"کف گرد — نزدیک گردن {neckline:.5g} | عمق={depth:.1%}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "کف گرد — الگو شناسایی نشد"}


# ── Export ──────────────────────────────────────────

CP_STRATEGIES = [
    {"id": "CP_01", "name": "CP_01", "name_fa": "الگو: سر و شانه", "func": cp_head_shoulders},
    {"id": "CP_02", "name": "CP_02", "name_fa": "الگو: سر و شانه معکوس", "func": cp_inv_head_shoulders},
    {"id": "CP_03", "name": "CP_03", "name_fa": "الگو: مثلث متقارن", "func": cp_sym_triangle},
    {"id": "CP_04", "name": "CP_04", "name_fa": "الگو: مثلث صعودی", "func": cp_asc_triangle},
    {"id": "CP_05", "name": "CP_05", "name_fa": "الگو: مثلث نزولی", "func": cp_desc_triangle},
    {"id": "CP_06", "name": "CP_06", "name_fa": "الگو: کنج صعودی", "func": cp_rising_wedge},
    {"id": "CP_07", "name": "CP_07", "name_fa": "الگو: کنج نزولی", "func": cp_falling_wedge},
    {"id": "CP_08", "name": "CP_08", "name_fa": "الگو: پرچم", "func": cp_flag_pennant},
    {"id": "CP_09", "name": "CP_09", "name_fa": "الگو: مستطیل (رنج)", "func": cp_rectangle},
    {"id": "CP_10", "name": "CP_10", "name_fa": "الگو: فنجان و دسته", "func": cp_cup_handle},
    {"id": "CP_11", "name": "CP_11", "name_fa": "الگو: کف گرد", "func": cp_rounding_bottom},
]
