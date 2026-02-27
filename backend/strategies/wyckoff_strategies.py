"""
Whilber-AI — Wyckoff Strategies
==================================
WYC_01: Accumulation Phase
WYC_02: Distribution Phase
WYC_03: Spring / Upthrust
WYC_04: Sign of Strength (SOS)
WYC_05: Sign of Weakness (SOW)
WYC_06: Effort vs Result
"""

import numpy as np


def _vol_avg(df, period=20):
    v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(len(df))
    return np.mean(v[-period:]) if len(v) >= period else np.mean(v)


def _range_info(df, lookback=30):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(h) < lookback:
        return None
    seg = slice(-lookback, None)
    hi = np.max(h[seg])
    lo = np.min(l[seg])
    rng_pct = (hi - lo) / lo * 100 if lo > 0 else 0
    price = c[-1]
    pos = (price - lo) / (hi - lo) if hi != lo else 0.5
    return {"high": hi, "low": lo, "range_pct": rng_pct, "price": price, "position": pos}


# -- WYC_01: Accumulation
def wyckoff_accumulation(df, context=None):
    """فاز تجمع وایکاف — رنج با حجم کاهشی + بانس صعودی"""
    r = _range_info(df, 30)
    if r is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "تجمع — داده کافی نیست"}

    v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(len(df))
    c = df["close"].values
    adx = context.get("adx", 25) if context else 25

    # Accumulation: range market + declining volume + price near bottom rising
    is_range = adx < 22 or r["range_pct"] < 4
    vol_early = np.mean(v[-30:-15]) if len(v) >= 30 else np.mean(v)
    vol_late = np.mean(v[-10:]) if len(v) >= 10 else np.mean(v)
    vol_declining = vol_late < vol_early * 0.85

    if is_range and r["position"] < 0.40 and c[-1] > c[-2] > c[-3]:
        conf = 65 if vol_declining else 55
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"تجمع وایکاف — رنج + قیمت نزدیک کف {r['low']:.5g} + صعود | خرید"}

    if is_range and vol_declining and r["position"] < 0.35:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"تجمع احتمالی — حجم کاهشی + کف رنج | منتظر تایید"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"تجمع — شرایط نیست | ADX={adx:.0f} موقعیت={r['position']:.0%}"}


# -- WYC_02: Distribution
def wyckoff_distribution(df, context=None):
    """فاز توزیع وایکاف — رنج در سقف + حجم کاهشی"""
    r = _range_info(df, 30)
    if r is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "توزیع — داده کافی نیست"}

    v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(len(df))
    c = df["close"].values
    adx = context.get("adx", 25) if context else 25

    is_range = adx < 22 or r["range_pct"] < 4
    vol_early = np.mean(v[-30:-15]) if len(v) >= 30 else np.mean(v)
    vol_late = np.mean(v[-10:]) if len(v) >= 10 else np.mean(v)
    vol_declining = vol_late < vol_early * 0.85

    if is_range and r["position"] > 0.60 and c[-1] < c[-2] < c[-3]:
        conf = 65 if vol_declining else 55
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"توزیع وایکاف — رنج + قیمت نزدیک سقف {r['high']:.5g} + نزول | فروش"}

    if is_range and vol_declining and r["position"] > 0.65:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"توزیع احتمالی — حجم کاهشی + سقف رنج | منتظر تایید"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"توزیع — شرایط نیست | موقعیت={r['position']:.0%}"}


# -- WYC_03: Spring / Upthrust
def wyckoff_spring(df, context=None):
    """Spring و Upthrust — شکست جعلی کف/سقف رنج"""
    r = _range_info(df, 30)
    if r is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Spring — داده کافی نیست"}

    h, l, c = df["high"].values, df["low"].values, df["close"].values
    price = c[-1]

    # Spring: price dipped below range low then closed back inside
    recent_low = np.min(l[-5:])
    if recent_low < r["low"] and price > r["low"]:
        depth = (r["low"] - recent_low) / r["low"] * 100
        if depth < 1.5:
            return {"signal": "BUY", "confidence": 70,
                    "reason_fa": f"Spring وایکاف — زیر کف {r['low']:.5g} رفت و برگشت | شکست جعلی = خرید قوی"}

    # Upthrust: price spiked above range high then closed back inside
    recent_high = np.max(h[-5:])
    if recent_high > r["high"] and price < r["high"]:
        depth = (recent_high - r["high"]) / r["high"] * 100
        if depth < 1.5:
            return {"signal": "SELL", "confidence": 70,
                    "reason_fa": f"Upthrust وایکاف — بالای سقف {r['high']:.5g} رفت و برگشت | شکست جعلی = فروش قوی"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Spring/Upthrust — شناسایی نشد"}


# -- WYC_04: Sign of Strength
def wyckoff_sos(df, context=None):
    """نشانه قدرت — حرکت قوی + حجم بالا = ادامه"""
    c = df["close"].values
    v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(len(df))
    if len(c) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "SOS — داده کافی نیست"}

    avg_vol = np.mean(v[-20:]) if len(v) >= 20 else np.mean(v)
    move_5 = (c[-1] - c[-5]) / c[-5] * 100
    vol_5 = np.mean(v[-5:])
    vol_ratio = vol_5 / avg_vol if avg_vol > 0 else 1

    if move_5 > 1.5 and vol_ratio > 1.5:
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"SOS وایکاف — حرکت +{move_5:.1f}% + حجم {vol_ratio:.1f}x | قدرت خریدار"}
    elif move_5 < -1.5 and vol_ratio > 1.5:
        # Strong down move could be SOW instead, but context matters
        return {"signal": "NEUTRAL", "confidence": 40,
                "reason_fa": f"حرکت نزولی قوی {move_5:.1f}% + حجم بالا | ممکنه SOW باشه"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"SOS — حرکت {move_5:.1f}% حجم {vol_ratio:.1f}x | کافی نیست"}


# -- WYC_05: Sign of Weakness
def wyckoff_sow(df, context=None):
    """نشانه ضعف — حرکت نزولی قوی + حجم بالا"""
    c = df["close"].values
    v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(len(df))
    if len(c) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "SOW — داده کافی نیست"}

    avg_vol = np.mean(v[-20:]) if len(v) >= 20 else np.mean(v)
    move_5 = (c[-1] - c[-5]) / c[-5] * 100
    vol_5 = np.mean(v[-5:])
    vol_ratio = vol_5 / avg_vol if avg_vol > 0 else 1

    if move_5 < -1.5 and vol_ratio > 1.5:
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"SOW وایکاف — نزول {move_5:.1f}% + حجم {vol_ratio:.1f}x | ضعف = فروش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"SOW — حرکت {move_5:.1f}% حجم {vol_ratio:.1f}x | نشانه ضعف نیست"}


# -- WYC_06: Effort vs Result
def wyckoff_effort_result(df, context=None):
    """تلاش vs نتیجه — حجم بالا + حرکت کم = تغییر"""
    c = df["close"].values
    v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(len(df))
    if len(c) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Effort — داده کافی نیست"}

    avg_vol = np.mean(v[-20:]) if len(v) >= 20 else np.mean(v)

    # Last 3 bars: high volume but small range
    for i in range(-3, 0):
        bar_range = abs(c[i] - c[i-1]) / c[i-1] * 100
        bar_vol = v[i] / avg_vol if avg_vol > 0 else 1

        if bar_vol > 2.0 and bar_range < 0.3:
            # High effort, low result
            if c[i] > c[i-1]:
                return {"signal": "SELL", "confidence": 60,
                        "reason_fa": f"تلاش بالا نتیجه کم — حجم {bar_vol:.1f}x حرکت {bar_range:.2f}% صعودی | احتمال بازگشت نزولی"}
            else:
                return {"signal": "BUY", "confidence": 60,
                        "reason_fa": f"تلاش بالا نتیجه کم — حجم {bar_vol:.1f}x حرکت {bar_range:.2f}% نزولی | احتمال بازگشت صعودی"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "Effort vs Result — عدم تطابق شناسایی نشد"}


WYC_STRATEGIES = [
    {"id": "WYC_01", "name": "Wyckoff Accumulation", "name_fa": "وایکاف: تجمع", "func": wyckoff_accumulation},
    {"id": "WYC_02", "name": "Wyckoff Distribution", "name_fa": "وایکاف: توزیع", "func": wyckoff_distribution},
    {"id": "WYC_03", "name": "Wyckoff Spring", "name_fa": "وایکاف: Spring", "func": wyckoff_spring},
    {"id": "WYC_04", "name": "Wyckoff SOS", "name_fa": "وایکاف: نشانه قدرت", "func": wyckoff_sos},
    {"id": "WYC_05", "name": "Wyckoff SOW", "name_fa": "وایکاف: نشانه ضعف", "func": wyckoff_sow},
    {"id": "WYC_06", "name": "Wyckoff Effort", "name_fa": "وایکاف: تلاش vs نتیجه", "func": wyckoff_effort_result},
]
