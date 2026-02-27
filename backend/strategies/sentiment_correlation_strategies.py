"""
Whilber-AI — Sentiment & Correlation Strategies
=================================================
SNT_01-05: Sentiment (5)
COR_01-05: Correlation (5)
Total: 10
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


def _rsi(close, period=14):
    if len(close) < period + 1:
        return None
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_g = np.mean(gain[:period])
    avg_l = np.mean(loss[:period])
    rsi_vals = [100 - 100/(1 + avg_g/avg_l) if avg_l > 0 else 100]
    for i in range(period, len(delta)):
        avg_g = (avg_g * (period-1) + gain[i]) / period
        avg_l = (avg_l * (period-1) + loss[i]) / period
        rsi_vals.append(100 - 100/(1 + avg_g/avg_l) if avg_l > 0 else 100)
    return np.array(rsi_vals)


# ============================================================
# SENTIMENT
# ============================================================

def sentiment_fear_greed(df, context=None):
    """شاخص ترس/طمع پراکسی — ATR+RSI+BB ترکیبی"""
    c = df["close"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "ترس/طمع — داده کافی نیست"}

    rsi_val = context.get("rsi_14", 50) if context else 50
    atr_pct = context.get("atr_percent", 1) if context else 1

    # BB width as volatility proxy
    sma20 = np.mean(c[-20:])
    std20 = np.std(c[-20:])
    bb_width = (std20 / sma20) * 100 if sma20 > 0 else 1

    # Composite fear/greed: RSI weight + ATR weight + BB width
    # Fear: low RSI + high ATR + wide BB
    # Greed: high RSI + low ATR + narrow BB
    fear_score = (100 - rsi_val) * 0.4 + min(atr_pct * 20, 40) * 0.3 + min(bb_width * 10, 30) * 0.3
    greed_score = rsi_val * 0.4 + max(0, 40 - atr_pct * 20) * 0.3 + max(0, 30 - bb_width * 10) * 0.3

    if fear_score > 70:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"ترس شدید — RSI={rsi_val:.0f} ATR={atr_pct:.2f}% | Contrarian خرید"}
    elif greed_score > 70:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"طمع شدید — RSI={rsi_val:.0f} ATR={atr_pct:.2f}% | Contrarian فروش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ترس={fear_score:.0f} طمع={greed_score:.0f} — خنثی"}


def sentiment_vol_regime(df, context=None):
    """رژیم نوسان — VIX-like از ATR"""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "رژیم نوسان — داده کافی نیست"}

    # Calculate historical volatility
    returns = np.diff(np.log(c[-30:]))
    hv = np.std(returns) * np.sqrt(252) * 100  # Annualized

    atr_pct = context.get("atr_percent", 1) if context else 1

    if hv > 30 or atr_pct > 2.0:
        return {"signal": "NEUTRAL", "confidence": 55,
                "reason_fa": f"رژیم نوسان بالا — HV={hv:.1f}% ATR={atr_pct:.2f}% | احتیاط + SL بزرگتر"}
    elif hv < 10 and atr_pct < 0.5:
        return {"signal": "NEUTRAL", "confidence": 45,
                "reason_fa": f"رژیم نوسان پایین — HV={hv:.1f}% | فشردگی = آماده شکست"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"نوسان نرمال — HV={hv:.1f}%"}


def sentiment_extreme_mom(df, context=None):
    """مومنتوم اکسترم — ROC+RSI اکسترم = بازگشت"""
    c = df["close"].values
    if len(c) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "مومنتوم اکسترم — داده کافی نیست"}

    roc_10 = (c[-1] - c[-10]) / c[-10] * 100
    rsi_val = context.get("rsi_14", 50) if context else 50

    if roc_10 < -5 and rsi_val < 25:
        return {"signal": "BUY", "confidence": 63,
                "reason_fa": f"مومنتوم اکسترم نزولی — ROC={roc_10:.1f}% RSI={rsi_val:.0f} | بازگشت صعودی"}
    elif roc_10 > 5 and rsi_val > 75:
        return {"signal": "SELL", "confidence": 63,
                "reason_fa": f"مومنتوم اکسترم صعودی — ROC={roc_10:.1f}% RSI={rsi_val:.0f} | بازگشت نزولی"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"مومنتوم — ROC={roc_10:.1f}% RSI={rsi_val:.0f} | اکسترم نیست"}


def sentiment_mean_revert(df, context=None):
    """بازگشت به میانگین — فاصله زیاد از MA200"""
    c = df["close"].values
    if len(c) < 200:
        # Use MA50 as fallback
        if len(c) < 50:
            return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Mean Revert — داده کافی نیست"}
        ma = np.mean(c[-50:])
        ma_label = "MA50"
    else:
        ma = np.mean(c[-200:])
        ma_label = "MA200"

    price = c[-1]
    dev = (price - ma) / ma * 100

    if dev < -8:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"فاصله {dev:.1f}% زیر {ma_label}={ma:.5g} | بازگشت به میانگین = خرید"}
    elif dev > 8:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"فاصله +{dev:.1f}% بالای {ma_label}={ma:.5g} | بازگشت به میانگین = فروش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"فاصله {dev:+.1f}% از {ma_label} | نرمال"}


def sentiment_contrarian(df, context=None):
    """Contrarian — اشباع شدید RSI+Stoch = خلاف جمع"""
    c = df["close"].values
    if len(c) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Contrarian — داده کافی نیست"}

    rsi = context.get("rsi_14", 50) if context else 50
    stoch_k = context.get("stoch_k", 50) if context else 50

    both_os = rsi < 20 and stoch_k < 15
    both_ob = rsi > 80 and stoch_k > 85

    if both_os:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"Contrarian خرید — RSI={rsi:.0f} Stoch={stoch_k:.0f} هر دو اشباع فروش شدید"}
    elif both_ob:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"Contrarian فروش — RSI={rsi:.0f} Stoch={stoch_k:.0f} هر دو اشباع خرید شدید"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Contrarian — RSI={rsi:.0f} Stoch={stoch_k:.0f} | اشباع شدید نیست"}


# ============================================================
# CORRELATION
# ============================================================

def corr_dxy_inverse(df, context=None):
    """DXY معکوس — ضعف دلار بر اساس پراکسی"""
    c = df["close"].values
    if len(c) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "DXY — داده کافی نیست"}

    # We use price momentum as proxy since we don't have DXY data
    # For Gold/EURUSD: strong uptrend suggests dollar weakness
    roc_5 = (c[-1] - c[-5]) / c[-5] * 100
    roc_20 = (c[-1] - c[-20]) / c[-20] * 100

    # If both short and long term momentum align
    if roc_5 > 0.5 and roc_20 > 1.5:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"مومنتوم مثبت — ROC5={roc_5:.1f}% ROC20={roc_20:.1f}% | ادامه صعود (ضعف DXY)"}
    elif roc_5 < -0.5 and roc_20 < -1.5:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"مومنتوم منفی — ROC5={roc_5:.1f}% ROC20={roc_20:.1f}% | ادامه نزول (قدرت DXY)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"DXY — مومنتوم خنثی ROC5={roc_5:.1f}%"}


def corr_risk_onoff(df, context=None):
    """Risk On/Off — رژیم ریسک‌پذیری"""
    c = df["close"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Risk — داده کافی نیست"}

    # Use volatility + trend as risk proxy
    returns = np.diff(np.log(c[-20:]))
    vol = np.std(returns) * 100
    trend = (c[-1] - c[-20]) / c[-20] * 100

    if vol < 1.5 and trend > 1:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"Risk On — نوسان کم {vol:.2f}% + صعود {trend:.1f}% | ریسک‌پذیری بالا"}
    elif vol > 3 and trend < -1:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"Risk Off — نوسان بالا {vol:.2f}% + نزول {trend:.1f}% | ریسک‌گریزی"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Risk — نوسان={vol:.2f}% روند={trend:.1f}% | خنثی"}


def corr_intermarket(df, context=None):
    """سیگنال بین‌بازاری — مومنتوم نسبی"""
    c = df["close"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "بین‌بازاری — داده کافی نیست"}

    # Multi-timeframe momentum agreement
    roc_3 = (c[-1] - c[-3]) / c[-3] * 100
    roc_10 = (c[-1] - c[-10]) / c[-10] * 100
    roc_20 = (c[-1] - c[-20]) / c[-20] * 100

    all_up = roc_3 > 0 and roc_10 > 0 and roc_20 > 0
    all_dn = roc_3 < 0 and roc_10 < 0 and roc_20 < 0

    if all_up:
        return {"signal": "BUY", "confidence": 58,
                "reason_fa": f"مومنتوم هم‌جهت صعودی — 3d={roc_3:.1f}% 10d={roc_10:.1f}% 20d={roc_20:.1f}%"}
    elif all_dn:
        return {"signal": "SELL", "confidence": 58,
                "reason_fa": f"مومنتوم هم‌جهت نزولی — 3d={roc_3:.1f}% 10d={roc_10:.1f}% 20d={roc_20:.1f}%"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"مومنتوم — هم‌جهت نیست 3d={roc_3:.1f}% 10d={roc_10:.1f}%"}


def corr_divergence(df, context=None):
    """واگرایی همبستگی — شکست رفتار عادی"""
    c = df["close"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "واگرایی همبستگی — داده کافی نیست"}

    # Detect unusual behavior: price making new high/low but momentum fading
    rsi_val = context.get("rsi_14", 50) if context else 50
    price_at_high = c[-1] >= np.max(c[-20:]) * 0.998
    price_at_low = c[-1] <= np.min(c[-20:]) * 1.002

    if price_at_high and rsi_val < 60:
        return {"signal": "SELL", "confidence": 58,
                "reason_fa": f"سقف قیمتی + RSI ضعیف={rsi_val:.0f} | واگرایی = احتمال بازگشت"}
    elif price_at_low and rsi_val > 40:
        return {"signal": "BUY", "confidence": 58,
                "reason_fa": f"کف قیمتی + RSI قوی={rsi_val:.0f} | واگرایی = احتمال بازگشت"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "واگرایی همبستگی — شناسایی نشد"}


def corr_pair_strength(df, context=None):
    """قدرت نسبی جفت — مقایسه مومنتوم کوتاه و بلند"""
    c = df["close"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "قدرت جفت — داده کافی نیست"}

    # Relative strength: short vs long momentum
    short_mom = (c[-1] - c[-5]) / c[-5] * 100
    long_mom = (c[-1] - c[-20]) / c[-20] * 100

    # Strong when short accelerating faster than long
    if short_mom > 1 and short_mom > long_mom * 1.5 and long_mom > 0:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"قدرت صعودی تسریع — کوتاه={short_mom:.1f}% > بلند={long_mom:.1f}% | مومنتوم قوی"}
    elif short_mom < -1 and short_mom < long_mom * 1.5 and long_mom < 0:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"ضعف نزولی تسریع — کوتاه={short_mom:.1f}% < بلند={long_mom:.1f}% | مومنتوم ضعیف"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"قدرت — کوتاه={short_mom:.1f}% بلند={long_mom:.1f}% | بدون تسریع"}


SNT_STRATEGIES = [
    {"id": "SNT_01", "name": "Fear Greed Proxy", "name_fa": "سنتیمنت: ترس/طمع", "func": sentiment_fear_greed},
    {"id": "SNT_02", "name": "Volatility Regime", "name_fa": "سنتیمنت: رژیم نوسان", "func": sentiment_vol_regime},
    {"id": "SNT_03", "name": "Extreme Momentum", "name_fa": "سنتیمنت: مومنتوم اکسترم", "func": sentiment_extreme_mom},
    {"id": "SNT_04", "name": "Mean Reversion", "name_fa": "سنتیمنت: بازگشت میانگین", "func": sentiment_mean_revert},
    {"id": "SNT_05", "name": "Contrarian", "name_fa": "سنتیمنت: Contrarian", "func": sentiment_contrarian},
]

COR_STRATEGIES = [
    {"id": "COR_01", "name": "DXY Inverse", "name_fa": "همبستگی: DXY معکوس", "func": corr_dxy_inverse},
    {"id": "COR_02", "name": "Risk OnOff", "name_fa": "همبستگی: Risk On/Off", "func": corr_risk_onoff},
    {"id": "COR_03", "name": "Intermarket Signal", "name_fa": "همبستگی: بین‌بازاری", "func": corr_intermarket},
    {"id": "COR_04", "name": "Correlation Divergence", "name_fa": "همبستگی: واگرایی", "func": corr_divergence},
    {"id": "COR_05", "name": "Pair Strength", "name_fa": "همبستگی: قدرت جفت", "func": corr_pair_strength},
]
