"""
Whilber-AI — Gap & Market Structure Strategies
================================================
GAP_01-05: Gap strategies (5)
MS_01-07:  Market Structure (7)
Total: 12
"""

import numpy as np


def _ema(data, period):
    if len(data) < period:
        return None
    e = np.zeros(len(data))
    e[0] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(1, len(data)):
        e[i] = data[i] * m + e[i-1] * (1 - m)
    return e


def _swing_points(df, order=5):
    highs, lows = [], []
    h, l = df["high"].values, df["low"].values
    for i in range(order, len(df) - order):
        if all(h[i] >= h[i-j] for j in range(1, order+1)) and all(h[i] >= h[i+j] for j in range(1, order+1)):
            highs.append((i, h[i]))
        if all(l[i] <= l[i-j] for j in range(1, order+1)) and all(l[i] <= l[i+j] for j in range(1, order+1)):
            lows.append((i, l[i]))
    return highs, lows


# ============================================================
# GAP STRATEGIES
# ============================================================

def _detect_gap(df, lookback=10):
    """Detect gaps in last N bars. Returns list of (index, direction, size_pct)."""
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    gaps = []
    start = max(1, len(o) - lookback)
    for i in range(start, len(o)):
        if l[i] > h[i-1]:  # Gap up
            size = (l[i] - h[i-1]) / h[i-1] * 100
            if size > 0.05:
                gaps.append((i, "UP", size))
        elif h[i] < l[i-1]:  # Gap down
            size = (l[i-1] - h[i]) / l[i-1] * 100
            if size > 0.05:
                gaps.append((i, "DOWN", size))
    return gaps


def gap_fill(df, context=None):
    """Gap Fill — پر شدن گپ"""
    gaps = _detect_gap(df, 15)
    if not gaps:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Gap Fill — گپی یافت نشد"}

    c = df["close"].values
    price = c[-1]
    last_gap = gaps[-1]
    idx, direction, size = last_gap

    h, l = df["high"].values, df["low"].values
    if direction == "UP":
        gap_bottom = h[idx-1]
        if price < gap_bottom * 1.001 and price > gap_bottom * 0.995:
            return {"signal": "BUY", "confidence": 60,
                    "reason_fa": f"Gap Fill صعودی — قیمت در حال پر کردن گپ بالا {gap_bottom:.5g} | بانس"}
        elif price < gap_bottom:
            return {"signal": "SELL", "confidence": 55,
                    "reason_fa": f"Gap Fill — گپ بالا پر شد و شکست | ادامه نزول"}
    elif direction == "DOWN":
        gap_top = l[idx-1]
        if price > gap_top * 0.999 and price < gap_top * 1.005:
            return {"signal": "SELL", "confidence": 60,
                    "reason_fa": f"Gap Fill نزولی — قیمت در حال پر کردن گپ پایین {gap_top:.5g} | ریجکت"}
        elif price > gap_top:
            return {"signal": "BUY", "confidence": 55,
                    "reason_fa": f"Gap Fill — گپ پایین پر شد و شکست بالا | صعود"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Gap — گپ {direction} اندازه {size:.2f}% هنوز فعال نیست"}


def gap_breakaway(df, context=None):
    """Breakaway Gap — گپ شکست با حجم"""
    gaps = _detect_gap(df, 5)
    if not gaps:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Breakaway — گپی یافت نشد"}

    v = df["tick_volume"].values if "tick_volume" in df.columns else df.get("volume", np.ones(len(df))).values
    avg_vol = np.mean(v[-20:]) if len(v) >= 20 else np.mean(v)

    last = gaps[-1]
    idx, direction, size = last

    # Breakaway: large gap + high volume + near current bar
    if idx >= len(v) - 3 and size > 0.15:
        vol_ratio = v[idx] / avg_vol if avg_vol > 0 else 1
        if vol_ratio > 1.5:
            if direction == "UP":
                return {"signal": "BUY", "confidence": 68,
                        "reason_fa": f"Breakaway Gap صعودی — {size:.2f}% + حجم {vol_ratio:.1f}x | ادامه صعود"}
            else:
                return {"signal": "SELL", "confidence": 68,
                        "reason_fa": f"Breakaway Gap نزولی — {size:.2f}% + حجم {vol_ratio:.1f}x | ادامه نزول"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Breakaway — شرایط تایید نشد"}


def gap_exhaustion(df, context=None):
    """Exhaustion Gap — گپ خستگی بعد حرکت طولانی"""
    gaps = _detect_gap(df, 5)
    c = df["close"].values
    if not gaps or len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Exhaustion — شرایط نیست"}

    last = gaps[-1]
    idx, direction, size = last

    # Check if there was a prolonged move before the gap
    move_20 = (c[-5] - c[-25]) / c[-25] * 100 if len(c) >= 25 else 0

    if direction == "UP" and move_20 > 5 and size > 0.1:
        if c[-1] < c[-2]:  # Reversal candle after gap
            return {"signal": "SELL", "confidence": 62,
                    "reason_fa": f"Exhaustion Gap — گپ بالا بعد {move_20:.1f}% صعود | خستگی = بازگشت"}
    elif direction == "DOWN" and move_20 < -5 and size > 0.1:
        if c[-1] > c[-2]:
            return {"signal": "BUY", "confidence": 62,
                    "reason_fa": f"Exhaustion Gap — گپ پایین بعد {abs(move_20):.1f}% نزول | خستگی = بازگشت"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Exhaustion — گپ خستگی شناسایی نشد"}


def gap_island(df, context=None):
    """Island Reversal — جزیره بازگشتی"""
    gaps = _detect_gap(df, 15)
    if len(gaps) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Island — ۲ گپ لازمه"}

    g1, g2 = gaps[-2], gaps[-1]
    if g1[1] == "UP" and g2[1] == "DOWN" and g2[0] - g1[0] <= 8:
        return {"signal": "SELL", "confidence": 70,
                "reason_fa": f"Island Reversal نزولی — گپ بالا + گپ پایین = جزیره | بازگشت قوی"}
    elif g1[1] == "DOWN" and g2[1] == "UP" and g2[0] - g1[0] <= 8:
        return {"signal": "BUY", "confidence": 70,
                "reason_fa": f"Island Reversal صعودی — گپ پایین + گپ بالا = جزیره | بازگشت قوی"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Island — الگو یافت نشد"}


def gap_volume(df, context=None):
    """Gap + Volume — تایید گپ با حجم"""
    gaps = _detect_gap(df, 3)
    if not gaps:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Gap+Vol — گپی نیست"}

    v = df["tick_volume"].values if "tick_volume" in df.columns else df.get("volume", np.ones(len(df))).values
    avg_vol = np.mean(v[-20:]) if len(v) >= 20 else np.mean(v)

    last = gaps[-1]
    idx, direction, size = last
    if idx >= len(v):
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Gap+Vol — ایندکس خارج"}

    vol_ratio = v[idx] / avg_vol if avg_vol > 0 else 1

    if vol_ratio > 2.0:
        if direction == "UP":
            return {"signal": "BUY", "confidence": 72,
                    "reason_fa": f"Gap صعودی + حجم {vol_ratio:.1f}x — شکست معتبر | ادامه"}
        else:
            return {"signal": "SELL", "confidence": 72,
                    "reason_fa": f"Gap نزولی + حجم {vol_ratio:.1f}x — شکست معتبر | ادامه"}
    elif vol_ratio < 0.8:
        return {"signal": "NEUTRAL", "confidence": 35,
                "reason_fa": f"Gap با حجم پایین {vol_ratio:.1f}x — احتمال فیک | احتیاط"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Gap+Vol — حجم {vol_ratio:.1f}x نرمال"}


# ============================================================
# MARKET STRUCTURE STRATEGIES
# ============================================================

def ms_range_detect(df, context=None):
    """Range Detection — تشخیص رنج"""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Range — داده کافی نیست"}

    high_20 = np.max(h[-20:])
    low_20 = np.min(l[-20:])
    rng = (high_20 - low_20) / low_20 * 100
    price = c[-1]

    adx = context.get("adx", 25) if context else 25
    is_range = adx < 22 and rng < 3

    if is_range:
        pos = (price - low_20) / (high_20 - low_20) if high_20 != low_20 else 0.5
        if pos < 0.20:
            return {"signal": "BUY", "confidence": 55,
                    "reason_fa": f"رنج — کف رنج={low_20:.5g} ADX={adx:.0f} | خرید در حمایت"}
        elif pos > 0.80:
            return {"signal": "SELL", "confidence": 55,
                    "reason_fa": f"رنج — سقف رنج={high_20:.5g} ADX={adx:.0f} | فروش در مقاومت"}
        return {"signal": "NEUTRAL", "confidence": 30,
                "reason_fa": f"رنج شناسایی شد — {rng:.1f}% ADX={adx:.0f} | منتظر لبه"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"رنج نیست — ADX={adx:.0f} رنج={rng:.1f}%"}


def ms_breakout_confirm(df, context=None):
    """Breakout Confirm — تایید شکست با حجم و رتست"""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(len(df))
    if len(c) < 25:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Breakout — داده کافی نیست"}

    # 20-bar range
    high_20 = np.max(h[-25:-5])
    low_20 = np.min(l[-25:-5])
    avg_vol = np.mean(v[-25:-5]) if len(v) >= 25 else np.mean(v)
    price = c[-1]
    vol_now = np.mean(v[-3:])
    vol_ratio = vol_now / avg_vol if avg_vol > 0 else 1

    if price > high_20 and vol_ratio > 1.3:
        return {"signal": "BUY", "confidence": 70,
                "reason_fa": f"شکست بالا تایید شده — {price:.5g} > {high_20:.5g} + حجم {vol_ratio:.1f}x"}
    elif price < low_20 and vol_ratio > 1.3:
        return {"signal": "SELL", "confidence": 70,
                "reason_fa": f"شکست پایین تایید شده — {price:.5g} < {low_20:.5g} + حجم {vol_ratio:.1f}x"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Breakout — بدون شکست تایید شده"}


def ms_retest(df, context=None):
    """Retest Entry — ورود در رتست پس از شکست"""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Retest — داده کافی نیست"}

    high_prev = np.max(h[-30:-10])
    low_prev = np.min(l[-30:-10])
    max_recent = np.max(h[-10:])
    min_recent = np.min(l[-10:])
    price = c[-1]

    # Broke above, came back to test, bouncing
    if max_recent > high_prev and abs(price - high_prev) / price < 0.005 and c[-1] > c[-2]:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"رتست حمایت جدید — شکست {high_prev:.5g} و برگشت تست | خرید"}

    if min_recent < low_prev and abs(price - low_prev) / price < 0.005 and c[-1] < c[-2]:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"رتست مقاومت جدید — شکست {low_prev:.5g} و برگشت تست | فروش"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Retest — الگو فعال نیست"}


def ms_structure_shift(df, context=None):
    """Structure Shift — تغییر ساختار بازار (CHoCH)"""
    highs, lows = _swing_points(df, order=4)
    if len(highs) < 3 or len(lows) < 3:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "CHoCH — سوئینگ کافی نیست"}

    c = df["close"].values
    price = c[-1]

    # Bearish structure (LH, LL) then bullish break
    h_vals = [p for _, p in highs[-3:]]
    l_vals = [p for _, p in lows[-3:]]

    if h_vals[-3] > h_vals[-2] and l_vals[-2] < l_vals[-3]:  # Was bearish
        if price > h_vals[-2]:  # Broke last lower high
            return {"signal": "BUY", "confidence": 68,
                    "reason_fa": f"CHoCH صعودی — شکست سقف پایین‌تر {h_vals[-2]:.5g} | تغییر ساختار"}

    if h_vals[-3] < h_vals[-2] and l_vals[-2] > l_vals[-3]:  # Was bullish
        if price < l_vals[-2]:  # Broke last higher low
            return {"signal": "SELL", "confidence": 68,
                    "reason_fa": f"CHoCH نزولی — شکست کف بالاتر {l_vals[-2]:.5g} | تغییر ساختار"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "CHoCH — بدون تغییر ساختار"}


def ms_trend_maturity(df, context=None):
    """Trend Maturity — بلوغ روند و هشدار پایان"""
    highs, lows = _swing_points(df, order=5)
    c = df["close"].values
    if len(highs) < 4 or len(lows) < 4:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "بلوغ روند — سوئینگ کافی نیست"}

    h_vals = [p for _, p in highs[-4:]]
    l_vals = [p for _, p in lows[-4:]]

    # Count consecutive HH or LL
    hh_count = sum(1 for i in range(1, len(h_vals)) if h_vals[i] > h_vals[i-1])
    ll_count = sum(1 for i in range(1, len(l_vals)) if l_vals[i] < l_vals[i-1])

    if hh_count >= 3:
        diff = h_vals[-1] - h_vals[-2]
        prev_diff = h_vals[-2] - h_vals[-3]
        if prev_diff > 0 and diff < prev_diff * 0.5:
            return {"signal": "SELL", "confidence": 55,
                    "reason_fa": f"بلوغ روند صعودی — {hh_count} سقف بالاتر ولی شتاب کاهشی | هشدار بازگشت"}
    if ll_count >= 3:
        diff = abs(l_vals[-1] - l_vals[-2])
        prev_diff = abs(l_vals[-2] - l_vals[-3])
        if prev_diff > 0 and diff < prev_diff * 0.5:
            return {"signal": "BUY", "confidence": 55,
                    "reason_fa": f"بلوغ روند نزولی — {ll_count} کف پایین‌تر ولی شتاب کاهشی | هشدار بازگشت"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "بلوغ — روند هنوز جوان"}


def ms_fractal(df, context=None):
    """Fractal — فراکتال ویلیامز"""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(h) < 7:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "فراکتال — داده کافی نیست"}

    # Check last completed fractal (bar -3 is center, -5 and -1 are wings)
    price = c[-1]

    # Bullish fractal: low[-3] is lowest of 5
    if l[-3] < l[-4] and l[-3] < l[-5] and l[-3] < l[-2] and l[-3] < l[-1]:
        frac_low = l[-3]
        if price > frac_low and c[-1] > c[-2]:
            return {"signal": "BUY", "confidence": 52,
                    "reason_fa": f"فراکتال صعودی — کف={frac_low:.5g} + قیمت بالا | حمایت"}

    # Bearish fractal
    if h[-3] > h[-4] and h[-3] > h[-5] and h[-3] > h[-2] and h[-3] > h[-1]:
        frac_high = h[-3]
        if price < frac_high and c[-1] < c[-2]:
            return {"signal": "SELL", "confidence": 52,
                    "reason_fa": f"فراکتال نزولی — سقف={frac_high:.5g} + قیمت پایین | مقاومت"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "فراکتال — الگو فعال نیست"}


def ms_swing_failure(df, context=None):
    """Swing Failure — شکست جعلی سوئینگ"""
    highs, lows = _swing_points(df, order=4)
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(highs) < 2 or len(lows) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "SFP — سوئینگ کافی نیست"}

    price = c[-1]
    prev_high = highs[-1][1]
    prev_low = lows[-1][1]

    # Bullish SFP: price went below prev low then closed back above
    if np.min(l[-3:]) < prev_low and price > prev_low:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"SFP صعودی — زیر کف {prev_low:.5g} رفت و برگشت بالا | شکست جعلی = خرید"}

    # Bearish SFP
    if np.max(h[-3:]) > prev_high and price < prev_high:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"SFP نزولی — بالای سقف {prev_high:.5g} رفت و برگشت پایین | شکست جعلی = فروش"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "SFP — شکست جعلی شناسایی نشد"}


GAP_STRATEGIES = [
    {"id": "GAP_01", "name": "Gap Fill", "name_fa": "گپ: پر شدن", "func": gap_fill},
    {"id": "GAP_02", "name": "Breakaway Gap", "name_fa": "گپ: شکست", "func": gap_breakaway},
    {"id": "GAP_03", "name": "Exhaustion Gap", "name_fa": "گپ: خستگی", "func": gap_exhaustion},
    {"id": "GAP_04", "name": "Island Reversal", "name_fa": "گپ: جزیره بازگشتی", "func": gap_island},
    {"id": "GAP_05", "name": "Gap Volume", "name_fa": "گپ: + حجم", "func": gap_volume},
]

MS_STRATEGIES = [
    {"id": "MS_01", "name": "Range Detection", "name_fa": "ساختار: تشخیص رنج", "func": ms_range_detect},
    {"id": "MS_02", "name": "Breakout Confirm", "name_fa": "ساختار: تایید شکست", "func": ms_breakout_confirm},
    {"id": "MS_03", "name": "Retest Entry", "name_fa": "ساختار: رتست", "func": ms_retest},
    {"id": "MS_04", "name": "Structure Shift", "name_fa": "ساختار: CHoCH", "func": ms_structure_shift},
    {"id": "MS_05", "name": "Trend Maturity", "name_fa": "ساختار: بلوغ روند", "func": ms_trend_maturity},
    {"id": "MS_06", "name": "Fractal", "name_fa": "ساختار: فراکتال", "func": ms_fractal},
    {"id": "MS_07", "name": "Swing Failure", "name_fa": "ساختار: شکست جعلی", "func": ms_swing_failure},
]
