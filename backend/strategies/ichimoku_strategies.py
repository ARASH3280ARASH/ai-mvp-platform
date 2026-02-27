"""
Whilber-AI — Ichimoku Strategy Pack (10 Sub-Strategies)
========================================================
ICH_01: Tenkan/Kijun Cross (TK Cross)
ICH_02: Price vs Kumo (Cloud)
ICH_03: Kumo Breakout
ICH_04: Kumo Twist (Cloud Color Change)
ICH_05: Chikou Span Confirmation
ICH_06: Full Ichimoku (All 5 Lines Aligned)
ICH_07: Tenkan Bounce (Pullback to Tenkan)
ICH_08: Kijun Bounce (Pullback to Kijun)
ICH_09: Kumo Thickness (Cloud Thickness as Strength)
ICH_10: Flat Kijun (Ranging Market Detection)
"""

import numpy as np
import pandas as pd


def _ichimoku(df, tenkan_p=9, kijun_p=26, senkou_b_p=52, displacement=26):
    """Calculate all Ichimoku components."""
    high = df['high']
    low = df['low']
    close = df['close']

    # Tenkan-sen (Conversion Line)
    tenkan = (high.rolling(tenkan_p).max() + low.rolling(tenkan_p).min()) / 2

    # Kijun-sen (Base Line)
    kijun = (high.rolling(kijun_p).max() + low.rolling(kijun_p).min()) / 2

    # Senkou Span A (Leading Span A) — shifted forward
    senkou_a = ((tenkan + kijun) / 2).shift(displacement)

    # Senkou Span B (Leading Span B) — shifted forward
    senkou_b = ((high.rolling(senkou_b_p).max() + low.rolling(senkou_b_p).min()) / 2).shift(displacement)

    # Chikou Span (Lagging Span) — shifted backward
    chikou = close.shift(-displacement)

    # Current cloud values (non-shifted for current bar comparison)
    senkou_a_now = (tenkan + kijun) / 2
    senkou_b_now = (high.rolling(senkou_b_p).max() + low.rolling(senkou_b_p).min()) / 2

    return {
        "tenkan": tenkan, "kijun": kijun,
        "senkou_a": senkou_a, "senkou_b": senkou_b,
        "senkou_a_now": senkou_a_now, "senkou_b_now": senkou_b_now,
        "chikou": chikou,
        "cloud_top": pd.concat([senkou_a, senkou_b], axis=1).max(axis=1),
        "cloud_bot": pd.concat([senkou_a, senkou_b], axis=1).min(axis=1),
    }


def _safe(series, idx=-1):
    try:
        v = series.iloc[idx]
        return v if not pd.isna(v) else None
    except:
        return None


# ─────────────────────────────────────────────────────
# ICH_01: Tenkan/Kijun Cross (TK Cross)
# BUY:  Tenkan crosses above Kijun
# SELL: Tenkan crosses below Kijun
# ─────────────────────────────────────────────────────
def ich_01_tk_cross(df, context=None):
    ich = _ichimoku(df)
    t = _safe(ich["tenkan"]); t_p = _safe(ich["tenkan"], -2)
    k = _safe(ich["kijun"]); k_p = _safe(ich["kijun"], -2)
    if None in (t, t_p, k, k_p):
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی برای ایچیموکو نیست"}

    p = df['close'].iloc[-1]
    cloud_top = _safe(ich["cloud_top"])
    cloud_bot = _safe(ich["cloud_bot"])
    above_cloud = p > cloud_top if cloud_top else False
    below_cloud = p < cloud_bot if cloud_bot else False

    if t_p <= k_p and t > k:
        conf = 82 if above_cloud else (70 if not below_cloud else 58)
        loc = "بالای ابر" if above_cloud else ("داخل ابر" if not below_cloud else "زیر ابر")
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"تقاطع صعودی تنکان/کیجون ({loc}) — TK Cross بالا"}
    elif t_p >= k_p and t < k:
        conf = 82 if below_cloud else (70 if not above_cloud else 58)
        loc = "زیر ابر" if below_cloud else ("داخل ابر" if not above_cloud else "بالای ابر")
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"تقاطع نزولی تنکان/کیجون ({loc}) — TK Cross پایین"}
    elif t > k:
        return {"signal": "BUY", "confidence": 42,
                "reason_fa": "تنکان بالای کیجون — مومنتوم صعودی"}
    elif t < k:
        return {"signal": "SELL", "confidence": 42,
                "reason_fa": "تنکان زیر کیجون — مومنتوم نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "تنکان و کیجون هم‌سطح"}


# ─────────────────────────────────────────────────────
# ICH_02: Price vs Kumo (Cloud)
# BUY:  Price above cloud
# SELL: Price below cloud
# ─────────────────────────────────────────────────────
def ich_02_price_cloud(df, context=None):
    ich = _ichimoku(df)
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]
    ct = _safe(ich["cloud_top"]); cb = _safe(ich["cloud_bot"])
    ct_p = _safe(ich["cloud_top"], -2); cb_p = _safe(ich["cloud_bot"], -2)
    if None in (ct, cb):
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده ابر کومو کافی نیست"}

    cloud_width = (ct - cb) / p * 100

    if p_prev <= ct_p and p > ct:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"قیمت از ابر کومو خارج شد (بالا) — شکست صعودی (عرض ابر {cloud_width:.2f}%)"}
    elif p_prev >= cb_p and p < cb:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"قیمت از ابر کومو خارج شد (پایین) — شکست نزولی (عرض ابر {cloud_width:.2f}%)"}
    elif p > ct:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"قیمت بالای ابر کومو — روند صعودی (عرض {cloud_width:.2f}%)"}
    elif p < cb:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"قیمت زیر ابر کومو — روند نزولی (عرض {cloud_width:.2f}%)"}
    else:
        pos = (p - cb) / (ct - cb) * 100 if ct != cb else 50
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"قیمت داخل ابر کومو ({pos:.0f}% از پایین) — بلاتکلیف"}


# ─────────────────────────────────────────────────────
# ICH_03: Kumo Breakout (Strong breakout with volume)
# BUY:  Price breaks above thick cloud from below
# SELL: Price breaks below thick cloud from above
# ─────────────────────────────────────────────────────
def ich_03_kumo_breakout(df, context=None):
    ich = _ichimoku(df)
    close = df['close']
    p = close.iloc[-1]
    ct = _safe(ich["cloud_top"]); cb = _safe(ich["cloud_bot"])
    if None in (ct, cb):
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    cloud_width = (ct - cb) / p * 100

    # Check last 3 candles for breakout pattern
    was_inside = False
    for i in range(-4, -1):
        ci = close.iloc[i]
        cti = _safe(ich["cloud_top"], i)
        cbi = _safe(ich["cloud_bot"], i)
        if cti and cbi and cbi <= ci <= cti:
            was_inside = True
            break

    if not was_inside:
        # Check if was below cloud
        was_below = any(close.iloc[i] < (_safe(ich["cloud_bot"], i) or 1e18) for i in range(-4, -1))
        was_above = any(close.iloc[i] > (_safe(ich["cloud_top"], i) or -1e18) for i in range(-4, -1))
    else:
        was_below = False
        was_above = False

    if p > ct and (was_inside or was_below) and cloud_width > 0.5:
        conf = min(90, 70 + int(cloud_width * 4))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"شکست کومو به بالا — ابر ضخیم شکسته شد ({cloud_width:.2f}%)"}
    elif p < cb and (was_inside or was_above) and cloud_width > 0.5:
        conf = min(90, 70 + int(cloud_width * 4))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"شکست کومو به پایین — ابر ضخیم شکسته شد ({cloud_width:.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون شکست کومو (عرض ابر {cloud_width:.2f}%)"}


# ─────────────────────────────────────────────────────
# ICH_04: Kumo Twist (Cloud Color Change)
# BUY:  Senkou A crosses above Senkou B (future cloud turns green)
# SELL: Senkou A crosses below Senkou B (future cloud turns red)
# ─────────────────────────────────────────────────────
def ich_04_kumo_twist(df, context=None):
    ich = _ichimoku(df)
    sa = _safe(ich["senkou_a_now"]); sb = _safe(ich["senkou_b_now"])
    sa_p = _safe(ich["senkou_a_now"], -2); sb_p = _safe(ich["senkou_b_now"], -2)
    if None in (sa, sb, sa_p, sb_p):
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    diff = (sa - sb) / df['close'].iloc[-1] * 100

    if sa_p <= sb_p and sa > sb:
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"پیچ کومو صعودی — ابر آینده سبز شد (فاصله {diff:.2f}%)"}
    elif sa_p >= sb_p and sa < sb:
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"پیچ کومو نزولی — ابر آینده قرمز شد (فاصله {diff:.2f}%)"}
    elif sa > sb:
        return {"signal": "BUY", "confidence": 40,
                "reason_fa": f"ابر آینده سبز (سنکو A > سنکو B: {diff:.2f}%)"}
    elif sa < sb:
        return {"signal": "SELL", "confidence": 40,
                "reason_fa": f"ابر آینده قرمز (سنکو A < سنکو B: {diff:.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سنکو A و B یکسان"}


# ─────────────────────────────────────────────────────
# ICH_05: Chikou Span Confirmation
# BUY:  Chikou above price 26 bars ago + above cloud
# SELL: Chikou below price 26 bars ago + below cloud
# ─────────────────────────────────────────────────────
def ich_05_chikou(df, context=None):
    ich = _ichimoku(df)
    close = df['close']
    p = close.iloc[-1]

    # Chikou = current close compared to price 26 bars ago
    if len(close) < 27:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    price_26_ago = close.iloc[-27]
    chikou_vs_price = (p - price_26_ago) / price_26_ago * 100

    ct = _safe(ich["cloud_top"])
    cb = _safe(ich["cloud_bot"])
    above_cloud = p > ct if ct else False
    below_cloud = p < cb if cb else False

    if p > price_26_ago and above_cloud:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"چیکو بالای قیمت ۲۶ بار قبل + بالای ابر — تایید صعودی ({chikou_vs_price:+.2f}%)"}
    elif p < price_26_ago and below_cloud:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"چیکو زیر قیمت ۲۶ بار قبل + زیر ابر — تایید نزولی ({chikou_vs_price:+.2f}%)"}
    elif p > price_26_ago:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"چیکو بالای قیمت ۲۶ بار قبل ({chikou_vs_price:+.2f}%)"}
    elif p < price_26_ago:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"چیکو زیر قیمت ۲۶ بار قبل ({chikou_vs_price:+.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "چیکو بدون تفاوت معنادار با ۲۶ بار قبل"}


# ─────────────────────────────────────────────────────
# ICH_06: Full Ichimoku (All 5 Conditions Aligned)
# BUY:  TK cross up + Price>Cloud + Chikou>Price26 + Cloud green + Price>Kijun
# SELL: TK cross down + Price<Cloud + Chikou<Price26 + Cloud red + Price<Kijun
# ─────────────────────────────────────────────────────
def ich_06_full(df, context=None):
    ich = _ichimoku(df)
    close = df['close']
    p = close.iloc[-1]

    t = _safe(ich["tenkan"]); k = _safe(ich["kijun"])
    ct = _safe(ich["cloud_top"]); cb = _safe(ich["cloud_bot"])
    sa = _safe(ich["senkou_a_now"]); sb = _safe(ich["senkou_b_now"])
    if None in (t, k, ct, cb, sa, sb) or len(close) < 27:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    price_26_ago = close.iloc[-27]

    bull_conditions = [
        t > k,            # Tenkan above Kijun
        p > ct,           # Price above cloud
        p > price_26_ago, # Chikou confirmation
        sa > sb,          # Future cloud green
        p > k,            # Price above Kijun
    ]
    bear_conditions = [
        t < k,
        p < cb,
        p < price_26_ago,
        sa < sb,
        p < k,
    ]

    bull_count = sum(bull_conditions)
    bear_count = sum(bear_conditions)

    if bull_count == 5:
        return {"signal": "BUY", "confidence": 92,
                "reason_fa": "ایچیموکو کامل صعودی — هر ۵ شرط تایید (TK + Cloud + Chikou + Green + Kijun)"}
    elif bear_count == 5:
        return {"signal": "SELL", "confidence": 92,
                "reason_fa": "ایچیموکو کامل نزولی — هر ۵ شرط تایید (TK + Cloud + Chikou + Red + Kijun)"}
    elif bull_count >= 4:
        return {"signal": "BUY", "confidence": 75,
                "reason_fa": f"ایچیموکو تقریبا صعودی — {bull_count}/5 شرط تایید"}
    elif bear_count >= 4:
        return {"signal": "SELL", "confidence": 75,
                "reason_fa": f"ایچیموکو تقریبا نزولی — {bear_count}/5 شرط تایید"}
    elif bull_count >= 3:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"ایچیموکو نسبتا صعودی — {bull_count}/5 شرط تایید"}
    elif bear_count >= 3:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"ایچیموکو نسبتا نزولی — {bear_count}/5 شرط تایید"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ایچیموکو مختلط — صعودی {bull_count}/5, نزولی {bear_count}/5"}


# ─────────────────────────────────────────────────────
# ICH_07: Tenkan Bounce (Pullback to Tenkan in Trend)
# BUY:  Price pulls back to Tenkan in uptrend and bounces
# SELL: Price pulls back up to Tenkan in downtrend and rejects
# ─────────────────────────────────────────────────────
def ich_07_tenkan_bounce(df, context=None):
    ich = _ichimoku(df)
    close = df['close']
    low = df['low']
    high = df['high']
    t = _safe(ich["tenkan"]); k = _safe(ich["kijun"])
    ct = _safe(ich["cloud_top"]); cb = _safe(ich["cloud_bot"])
    if None in (t, k, ct, cb):
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p = close.iloc[-1]
    p_low = low.iloc[-1]
    p_high = high.iloc[-1]
    t_dist = abs(p - t) / p * 100

    # Uptrend: price above cloud, tenkan above kijun
    if p > ct and t > k:
        if p_low <= t * 1.002 and p > t:  # touched tenkan and bounced
            return {"signal": "BUY", "confidence": 76,
                    "reason_fa": f"پولبک به تنکان در روند صعودی و برگشت — حمایت تنکان ({t_dist:.2f}%)"}
        elif t_dist < 0.3:
            return {"signal": "BUY", "confidence": 60,
                    "reason_fa": f"قیمت نزدیک تنکان در روند صعودی ({t_dist:.2f}%)"}

    # Downtrend: price below cloud, tenkan below kijun
    if p < cb and t < k:
        if p_high >= t * 0.998 and p < t:  # touched tenkan and rejected
            return {"signal": "SELL", "confidence": 76,
                    "reason_fa": f"پولبک به تنکان در روند نزولی و ریجکت — مقاومت تنکان ({t_dist:.2f}%)"}
        elif t_dist < 0.3:
            return {"signal": "SELL", "confidence": 60,
                    "reason_fa": f"قیمت نزدیک تنکان در روند نزولی ({t_dist:.2f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون پولبک تنکان مشخص (فاصله {t_dist:.2f}%)"}


# ─────────────────────────────────────────────────────
# ICH_08: Kijun Bounce (Pullback to Kijun in Trend)
# BUY:  Price pulls back to Kijun in strong uptrend
# SELL: Price pulls back to Kijun in strong downtrend
# ─────────────────────────────────────────────────────
def ich_08_kijun_bounce(df, context=None):
    ich = _ichimoku(df)
    close = df['close']
    low = df['low']
    high = df['high']
    t = _safe(ich["tenkan"]); k = _safe(ich["kijun"])
    ct = _safe(ich["cloud_top"]); cb = _safe(ich["cloud_bot"])
    if None in (t, k, ct, cb):
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p = close.iloc[-1]
    p_low = low.iloc[-1]
    p_high = high.iloc[-1]
    k_dist = abs(p - k) / p * 100

    # Strong uptrend: price above cloud
    if p > ct:
        if p_low <= k * 1.003 and p > k:
            return {"signal": "BUY", "confidence": 80,
                    "reason_fa": f"پولبک به کیجون در روند صعودی قوی — حمایت کلیدی ({k_dist:.2f}%)"}
        elif k_dist < 0.5 and p > k:
            return {"signal": "BUY", "confidence": 62,
                    "reason_fa": f"قیمت نزدیک کیجون در روند صعودی ({k_dist:.2f}%)"}

    # Strong downtrend: price below cloud
    if p < cb:
        if p_high >= k * 0.997 and p < k:
            return {"signal": "SELL", "confidence": 80,
                    "reason_fa": f"پولبک به کیجون در روند نزولی قوی — مقاومت کلیدی ({k_dist:.2f}%)"}
        elif k_dist < 0.5 and p < k:
            return {"signal": "SELL", "confidence": 62,
                    "reason_fa": f"قیمت نزدیک کیجون در روند نزولی ({k_dist:.2f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون پولبک کیجون مشخص (فاصله {k_dist:.2f}%)"}


# ─────────────────────────────────────────────────────
# ICH_09: Kumo Thickness (Cloud as Support/Resistance Strength)
# Thick cloud = strong S/R, thin = weak
# ─────────────────────────────────────────────────────
def ich_09_kumo_thickness(df, context=None):
    ich = _ichimoku(df)
    close = df['close']
    p = close.iloc[-1]
    ct = _safe(ich["cloud_top"]); cb = _safe(ich["cloud_bot"])
    sa = _safe(ich["senkou_a_now"]); sb = _safe(ich["senkou_b_now"])
    if None in (ct, cb, sa, sb):
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    width_pct = (ct - cb) / p * 100
    future_width = abs(sa - sb) / p * 100

    # Approaching thick cloud from below = strong resistance
    if p < cb and width_pct > 2:
        dist_to_cloud = (cb - p) / p * 100
        if dist_to_cloud < 1:
            return {"signal": "SELL", "confidence": 70,
                    "reason_fa": f"نزدیک ابر ضخیم از پایین — مقاومت قوی (عرض {width_pct:.2f}%)"}

    # Approaching thick cloud from above = strong support
    if p > ct and width_pct > 2:
        dist_to_cloud = (p - ct) / p * 100
        if dist_to_cloud < 1:
            return {"signal": "BUY", "confidence": 70,
                    "reason_fa": f"حمایت ابر ضخیم از بالا — سطح قوی (عرض {width_pct:.2f}%)"}

    # Thin future cloud = potential breakout zone
    if future_width < 0.3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"ابر آینده بسیار نازک ({future_width:.2f}%) — آماده شکست"}

    if p > ct:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"بالای ابر با عرض {width_pct:.2f}% — حمایت {'قوی' if width_pct > 2 else 'ضعیف'}"}
    elif p < cb:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"زیر ابر با عرض {width_pct:.2f}% — مقاومت {'قوی' if width_pct > 2 else 'ضعیف'}"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"داخل ابر (عرض {width_pct:.2f}%)"}


# ─────────────────────────────────────────────────────
# ICH_10: Flat Kijun Detection (Range Market)
# Flat Kijun = ranging, slope Kijun = trending
# ─────────────────────────────────────────────────────
def ich_10_flat_kijun(df, context=None):
    ich = _ichimoku(df)
    k_vals = ich["kijun"].dropna().tail(10)
    if len(k_vals) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p = df['close'].iloc[-1]
    k = k_vals.iloc[-1]

    # Check flatness: how many bars kijun stayed same
    flat_count = sum(1 for i in range(1, len(k_vals)) if abs(k_vals.iloc[i] - k_vals.iloc[i-1]) / p < 0.001)
    is_flat = flat_count >= 7

    k_slope = (k_vals.iloc[-1] - k_vals.iloc[0]) / p * 100

    if is_flat:
        dist = (p - k) / k * 100
        if dist > 1:
            return {"signal": "SELL", "confidence": 60,
                    "reason_fa": f"کیجون صاف (رنج) — قیمت بالای کیجون ({dist:+.2f}%) احتمال بازگشت"}
        elif dist < -1:
            return {"signal": "BUY", "confidence": 60,
                    "reason_fa": f"کیجون صاف (رنج) — قیمت زیر کیجون ({dist:+.2f}%) احتمال بازگشت"}
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"کیجون صاف — بازار رنج (فاصله {dist:+.2f}%)"}
    else:
        if k_slope > 0.5:
            return {"signal": "BUY", "confidence": 50,
                    "reason_fa": f"کیجون صعودی ({k_slope:+.2f}%) — روند فعال"}
        elif k_slope < -0.5:
            return {"signal": "SELL", "confidence": 50,
                    "reason_fa": f"کیجون نزولی ({k_slope:+.2f}%) — روند فعال"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"کیجون بدون سیگنال واضح (شیب {k_slope:+.2f}%)"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

ICHIMOKU_STRATEGIES = [
    {"id": "ICH_01", "name": "TK Cross", "name_fa": "تقاطع تنکان/کیجون", "func": ich_01_tk_cross},
    {"id": "ICH_02", "name": "Price vs Kumo", "name_fa": "قیمت در برابر ابر کومو", "func": ich_02_price_cloud},
    {"id": "ICH_03", "name": "Kumo Breakout", "name_fa": "شکست ابر کومو", "func": ich_03_kumo_breakout},
    {"id": "ICH_04", "name": "Kumo Twist", "name_fa": "پیچ کومو", "func": ich_04_kumo_twist},
    {"id": "ICH_05", "name": "Chikou Confirm", "name_fa": "تایید چیکو اسپن", "func": ich_05_chikou},
    {"id": "ICH_06", "name": "Full Ichimoku (5/5)", "name_fa": "ایچیموکو کامل (۵/۵)", "func": ich_06_full},
    {"id": "ICH_07", "name": "Tenkan Bounce", "name_fa": "پولبک تنکان", "func": ich_07_tenkan_bounce},
    {"id": "ICH_08", "name": "Kijun Bounce", "name_fa": "پولبک کیجون", "func": ich_08_kijun_bounce},
    {"id": "ICH_09", "name": "Kumo Thickness", "name_fa": "ضخامت ابر کومو", "func": ich_09_kumo_thickness},
    {"id": "ICH_10", "name": "Flat Kijun Range", "name_fa": "کیجون صاف (بازار رنج)", "func": ich_10_flat_kijun},
]
