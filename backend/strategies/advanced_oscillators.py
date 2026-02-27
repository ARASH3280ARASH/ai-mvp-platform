"""
Whilber-AI — Advanced Oscillator Strategies
=============================================
ARN_01-04: Aroon (4)
VTX_01-04: Vortex (4)
ULT_01-04: Ultimate Oscillator (4)
KST_01-03: KST (3)
Total: 15
"""

import numpy as np


def _ema(data, period):
    if len(data) < period:
        return None
    ema = np.zeros(len(data))
    ema[0] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(1, len(data)):
        ema[i] = data[i] * m + ema[i-1] * (1 - m)
    return ema


def _sma(data, period):
    if len(data) < period:
        return None
    return np.convolve(data, np.ones(period)/period, mode='valid')


def _roc(data, period):
    if len(data) <= period:
        return None
    return (data[period:] - data[:-period]) / np.where(data[:-period] != 0, data[:-period], 1) * 100


# ═══════════════════════════════════════════════════
# AROON
# ═══════════════════════════════════════════════════

def _calc_aroon(high, low, period=25):
    if len(high) < period + 1:
        return None, None, None
    n = len(high)
    aroon_up = np.zeros(n)
    aroon_dn = np.zeros(n)
    for i in range(period, n):
        window_h = high[i - period:i + 1]
        window_l = low[i - period:i + 1]
        days_since_high = period - np.argmax(window_h)
        days_since_low = period - np.argmin(window_l)
        aroon_up[i] = (days_since_high / period) * 100
        aroon_dn[i] = (days_since_low / period) * 100
    osc = aroon_up - aroon_dn
    return aroon_up[period:], aroon_dn[period:], osc[period:]


def aroon_cross(df, context=None):
    """آرون تقاطع — Aroon Up از Down عبور"""
    up, dn, _ = _calc_aroon(df["high"].values, df["low"].values)
    if up is None or len(up) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "آرون — داده کافی نیست"}

    cross_up = up[-2] <= dn[-2] and up[-1] > dn[-1]
    cross_dn = up[-2] >= dn[-2] and up[-1] < dn[-1]

    if cross_up:
        return {"signal": "BUY", "confidence": 58,
                "reason_fa": f"آرون تقاطع صعودی — Up={up[-1]:.0f} از Down={dn[-1]:.0f} عبور بالا"}
    elif cross_dn:
        return {"signal": "SELL", "confidence": 58,
                "reason_fa": f"آرون تقاطع نزولی — Down={dn[-1]:.0f} از Up={up[-1]:.0f} عبور بالا"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"آرون — بدون تقاطع Up={up[-1]:.0f} Down={dn[-1]:.0f}"}


def aroon_trend(df, context=None):
    """آرون روند قوی — Up>70 + Down<30"""
    up, dn, _ = _calc_aroon(df["high"].values, df["low"].values)
    if up is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "آرون — داده کافی نیست"}

    if up[-1] > 70 and dn[-1] < 30:
        conf = 70 if up[-1] > 90 else 60
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"آرون روند صعودی قوی — Up={up[-1]:.0f} Down={dn[-1]:.0f}"}
    elif dn[-1] > 70 and up[-1] < 30:
        conf = 70 if dn[-1] > 90 else 60
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"آرون روند نزولی قوی — Down={dn[-1]:.0f} Up={up[-1]:.0f}"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"آرون — روند قوی نیست Up={up[-1]:.0f} Down={dn[-1]:.0f}"}


def aroon_oscillator(df, context=None):
    """آرون اسیلاتور — عبور از صفر"""
    _, _, osc = _calc_aroon(df["high"].values, df["low"].values)
    if osc is None or len(osc) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "آرون OSC — داده کافی نیست"}

    if osc[-2] <= 0 and osc[-1] > 0:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"آرون اسیلاتور عبور صعودی — OSC={osc[-1]:.0f}"}
    elif osc[-2] >= 0 and osc[-1] < 0:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"آرون اسیلاتور عبور نزولی — OSC={osc[-1]:.0f}"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"آرون OSC={osc[-1]:.0f} بدون عبور"}


def aroon_adx(df, context=None):
    """آرون + ADX — جهت آرون + قدرت ADX"""
    up, dn, osc = _calc_aroon(df["high"].values, df["low"].values)
    if osc is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "آرون+ADX — داده کافی نیست"}

    adx = context.get("adx", 20) if context else 20
    strong = adx > 25

    if osc[-1] > 50 and strong:
        return {"signal": "BUY", "confidence": 70,
                "reason_fa": f"آرون صعودی + ADX قوی={adx:.0f} — تایید روند | OSC={osc[-1]:.0f}"}
    elif osc[-1] < -50 and strong:
        return {"signal": "SELL", "confidence": 70,
                "reason_fa": f"آرون نزولی + ADX قوی={adx:.0f} — تایید روند | OSC={osc[-1]:.0f}"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"آرون OSC={osc[-1]:.0f} ADX={adx:.0f} — شرایط کافی نیست"}


# ═══════════════════════════════════════════════════
# VORTEX
# ═══════════════════════════════════════════════════

def _calc_vortex(high, low, close, period=14):
    if len(high) < period + 1:
        return None, None
    n = len(high)
    vm_plus = np.abs(high[1:] - low[:-1])
    vm_minus = np.abs(low[1:] - high[:-1])
    tr = np.maximum(high[1:] - low[1:],
         np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))

    vi_plus = np.zeros(len(vm_plus))
    vi_minus = np.zeros(len(vm_minus))
    for i in range(period - 1, len(vm_plus)):
        sum_tr = np.sum(tr[i - period + 1:i + 1])
        if sum_tr > 0:
            vi_plus[i] = np.sum(vm_plus[i - period + 1:i + 1]) / sum_tr
            vi_minus[i] = np.sum(vm_minus[i - period + 1:i + 1]) / sum_tr
    return vi_plus[period-1:], vi_minus[period-1:]


def vortex_cross(df, context=None):
    """ورتکس تقاطع — VI+ از VI- عبور"""
    vp, vm = _calc_vortex(df["high"].values, df["low"].values, df["close"].values)
    if vp is None or len(vp) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "ورتکس — داده کافی نیست"}

    cross_up = vp[-2] <= vm[-2] and vp[-1] > vm[-1]
    cross_dn = vp[-2] >= vm[-2] and vp[-1] < vm[-1]

    if cross_up:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"ورتکس تقاطع صعودی — VI+={vp[-1]:.3f} > VI-={vm[-1]:.3f}"}
    elif cross_dn:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"ورتکس تقاطع نزولی — VI-={vm[-1]:.3f} > VI+={vp[-1]:.3f}"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ورتکس — بدون تقاطع VI+={vp[-1]:.3f} VI-={vm[-1]:.3f}"}


def vortex_trend(df, context=None):
    """ورتکس روند — VI+ بالای 1.1 = صعود قوی"""
    vp, vm = _calc_vortex(df["high"].values, df["low"].values, df["close"].values)
    if vp is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "ورتکس — داده کافی نیست"}

    diff = vp[-1] - vm[-1]
    if vp[-1] > 1.10 and diff > 0.15:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"ورتکس صعودی قوی — VI+={vp[-1]:.3f} فاصله={diff:.3f}"}
    elif vm[-1] > 1.10 and diff < -0.15:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"ورتکس نزولی قوی — VI-={vm[-1]:.3f} فاصله={abs(diff):.3f}"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ورتکس — روند قوی نیست diff={diff:.3f}"}


def vortex_atr(df, context=None):
    """ورتکس + ATR فیلتر — تقاطع با نوسان بالا"""
    vp, vm = _calc_vortex(df["high"].values, df["low"].values, df["close"].values)
    if vp is None or len(vp) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "ورتکس ATR — داده کافی نیست"}

    atr_pct = context.get("atr_percent", 0) if context else 0
    high_vol = atr_pct > 0.5

    cross_up = vp[-2] <= vm[-2] and vp[-1] > vm[-1]
    cross_dn = vp[-2] >= vm[-2] and vp[-1] < vm[-1]

    if cross_up and high_vol:
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"ورتکس صعودی + نوسان بالا ATR={atr_pct:.2f}% | تایید شده"}
    elif cross_dn and high_vol:
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"ورتکس نزولی + نوسان بالا ATR={atr_pct:.2f}% | تایید شده"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ورتکس — شرایط تایید نشده ATR={atr_pct:.2f}%"}


def vortex_divergence(df, context=None):
    """ورتکس واگرایی — VI vs قیمت"""
    vp, vm = _calc_vortex(df["high"].values, df["low"].values, df["close"].values)
    if vp is None or len(vp) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "ورتکس Div — داده کافی نیست"}

    c = df["close"].values
    diff = vp - vm
    p_r, p_p = c[-10:], c[-20:-10]
    d_r, d_p = diff[-10:], diff[-20:-10]

    if np.min(p_r) < np.min(p_p) and np.min(d_r) > np.min(d_p):
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": "ورتکس واگرایی صعودی — قیمت کف جدید ولی VI فاصله بالاتر"}
    if np.max(p_r) > np.max(p_p) and np.max(d_r) < np.max(d_p):
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": "ورتکس واگرایی نزولی — قیمت سقف جدید ولی VI فاصله پایین‌تر"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "ورتکس — واگرایی یافت نشد"}


# ═══════════════════════════════════════════════════
# ULTIMATE OSCILLATOR
# ═══════════════════════════════════════════════════

def _calc_ultimate(high, low, close, p1=7, p2=14, p3=28):
    if len(close) < p3 + 1:
        return None
    bp = close[1:] - np.minimum(low[1:], close[:-1])
    tr = np.maximum(high[1:], close[:-1]) - np.minimum(low[1:], close[:-1])
    tr = np.where(tr == 0, 1, tr)

    n = len(bp)
    uo = np.zeros(n)
    for i in range(p3 - 1, n):
        avg1 = np.sum(bp[i-p1+1:i+1]) / np.sum(tr[i-p1+1:i+1]) if np.sum(tr[i-p1+1:i+1]) > 0 else 0
        avg2 = np.sum(bp[i-p2+1:i+1]) / np.sum(tr[i-p2+1:i+1]) if np.sum(tr[i-p2+1:i+1]) > 0 else 0
        avg3 = np.sum(bp[i-p3+1:i+1]) / np.sum(tr[i-p3+1:i+1]) if np.sum(tr[i-p3+1:i+1]) > 0 else 0
        uo[i] = 100 * (4 * avg1 + 2 * avg2 + avg3) / 7
    return uo[p3-1:]


def ultimate_obos(df, context=None):
    """Ultimate Oscillator اشباع — <30 خرید، >70 فروش"""
    uo = _calc_ultimate(df["high"].values, df["low"].values, df["close"].values)
    if uo is None or len(uo) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "UO — داده کافی نیست"}

    v = uo[-1]
    if v < 30 and uo[-1] > uo[-2]:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"UO اشباع فروش — UO={v:.1f} و برگشت | ورود خرید"}
    elif v > 70 and uo[-1] < uo[-2]:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"UO اشباع خرید — UO={v:.1f} و برگشت | ورود فروش"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": f"UO خنثی — UO={v:.1f}"}


def ultimate_divergence(df, context=None):
    """Ultimate Oscillator واگرایی"""
    uo = _calc_ultimate(df["high"].values, df["low"].values, df["close"].values)
    if uo is None or len(uo) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "UO Div — داده کافی نیست"}

    c = df["close"].values
    p_r, p_p = c[-10:], c[-20:-10]
    u_r, u_p = uo[-10:], uo[-20:-10]

    if np.min(p_r) < np.min(p_p) and np.min(u_r) > np.min(u_p):
        return {"signal": "BUY", "confidence": 63,
                "reason_fa": "UO واگرایی صعودی — قیمت کف جدید + UO کف بالاتر"}
    if np.max(p_r) > np.max(p_p) and np.max(u_r) < np.max(u_p):
        return {"signal": "SELL", "confidence": 63,
                "reason_fa": "UO واگرایی نزولی — قیمت سقف جدید + UO سقف پایین‌تر"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "UO — واگرایی یافت نشد"}


def ultimate_multi(df, context=None):
    """Ultimate Oscillator چند دوره — 7+14+28 هم‌جهت"""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    uo1 = _calc_ultimate(h, l, c, 5, 10, 20)
    uo2 = _calc_ultimate(h, l, c, 7, 14, 28)
    uo3 = _calc_ultimate(h, l, c, 10, 20, 40)

    if uo1 is None or uo2 is None or uo3 is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "UO Multi — داده کافی نیست"}

    all_low = uo1[-1] < 35 and uo2[-1] < 35 and uo3[-1] < 40
    all_high = uo1[-1] > 65 and uo2[-1] > 65 and uo3[-1] > 60

    if all_low:
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"UO سه‌گانه اشباع فروش — {uo1[-1]:.0f}/{uo2[-1]:.0f}/{uo3[-1]:.0f}"}
    elif all_high:
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"UO سه‌گانه اشباع خرید — {uo1[-1]:.0f}/{uo2[-1]:.0f}/{uo3[-1]:.0f}"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"UO Multi — {uo1[-1]:.0f}/{uo2[-1]:.0f}/{uo3[-1]:.0f} هم‌جهت نیست"}


def ultimate_trend(df, context=None):
    """UO + فیلتر روند EMA"""
    uo = _calc_ultimate(df["high"].values, df["low"].values, df["close"].values)
    if uo is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "UO Trend — داده کافی نیست"}

    c = df["close"].values
    ema50 = _ema(c, 50)
    if ema50 is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "UO — EMA محاسبه نشد"}

    above = c[-1] > ema50[-1]
    v = uo[-1]

    if above and v < 35:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"UO={v:.0f} اشباع + بالای EMA50 | خرید تایید شده"}
    elif not above and v > 65:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"UO={v:.0f} اشباع + زیر EMA50 | فروش تایید شده"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"UO={v:.0f} {'بالای' if above else 'زیر'} EMA50"}


# ═══════════════════════════════════════════════════
# KST (Know Sure Thing)
# ═══════════════════════════════════════════════════

def _calc_kst(close):
    if len(close) < 35:
        return None, None
    r1 = _roc(close, 10)
    r2 = _roc(close, 15)
    r3 = _roc(close, 20)
    r4 = _roc(close, 30)
    if r1 is None or r2 is None or r3 is None or r4 is None:
        return None, None
    ml = min(len(r1), len(r2), len(r3), len(r4))
    r1, r2, r3, r4 = r1[-ml:], r2[-ml:], r3[-ml:], r4[-ml:]

    s1 = _sma(r1, 10)
    s2 = _sma(r2, 10)
    s3 = _sma(r3, 10)
    s4 = _sma(r4, 15)
    if s1 is None or s2 is None or s3 is None or s4 is None:
        return None, None

    ml2 = min(len(s1), len(s2), len(s3), len(s4))
    kst = s1[-ml2:] * 1 + s2[-ml2:] * 2 + s3[-ml2:] * 3 + s4[-ml2:] * 4
    sig = _sma(kst, 9)
    if sig is None:
        return kst, None
    ml3 = min(len(kst), len(sig))
    return kst[-ml3:], sig[-ml3:]


def kst_cross(df, context=None):
    """KST تقاطع سیگنال"""
    kst, sig = _calc_kst(df["close"].values)
    if kst is None or sig is None or len(kst) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "KST — داده کافی نیست"}

    cross_up = kst[-2] <= sig[-2] and kst[-1] > sig[-1]
    cross_dn = kst[-2] >= sig[-2] and kst[-1] < sig[-1]

    if cross_up:
        conf = 65 if kst[-1] < 0 else 55
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"KST تقاطع صعودی — KST از سیگنال عبور بالا"}
    elif cross_dn:
        conf = 65 if kst[-1] > 0 else 55
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"KST تقاطع نزولی — KST از سیگنال عبور پایین"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "KST — بدون تقاطع"}


def kst_zero(df, context=None):
    """KST عبور از خط صفر"""
    kst, _ = _calc_kst(df["close"].values)
    if kst is None or len(kst) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "KST Zero — داده کافی نیست"}

    if kst[-2] <= 0 and kst[-1] > 0:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"KST عبور صعودی از صفر — تغییر مومنتوم بلندمدت"}
    elif kst[-2] >= 0 and kst[-1] < 0:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"KST عبور نزولی از صفر — تغییر مومنتوم بلندمدت"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"KST={'مثبت' if kst[-1]>0 else 'منفی'} بدون عبور"}


def kst_divergence(df, context=None):
    """KST واگرایی بلندمدت"""
    kst, _ = _calc_kst(df["close"].values)
    if kst is None or len(kst) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "KST Div — داده کافی نیست"}

    c = df["close"].values
    p_r, p_p = c[-10:], c[-20:-10]
    k_r, k_p = kst[-10:], kst[-20:-10]

    if np.min(p_r) < np.min(p_p) and np.min(k_r) > np.min(k_p):
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": "KST واگرایی صعودی بلندمدت — تغییر روند محتمل"}
    if np.max(p_r) > np.max(p_p) and np.max(k_r) < np.max(k_p):
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": "KST واگرایی نزولی بلندمدت — ضعف روند"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "KST — واگرایی یافت نشد"}


# ═══════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════

ARN_STRATEGIES = [
    {"id": "ARN_01", "name": "Aroon Cross", "name_fa": "آرون: تقاطع", "func": aroon_cross},
    {"id": "ARN_02", "name": "Aroon Trend", "name_fa": "آرون: روند قوی", "func": aroon_trend},
    {"id": "ARN_03", "name": "Aroon Oscillator", "name_fa": "آرون: اسیلاتور", "func": aroon_oscillator},
    {"id": "ARN_04", "name": "Aroon ADX", "name_fa": "آرون: + ADX", "func": aroon_adx},
]

VTX_STRATEGIES = [
    {"id": "VTX_01", "name": "Vortex Cross", "name_fa": "ورتکس: تقاطع", "func": vortex_cross},
    {"id": "VTX_02", "name": "Vortex Trend", "name_fa": "ورتکس: روند", "func": vortex_trend},
    {"id": "VTX_03", "name": "Vortex ATR", "name_fa": "ورتکس: + ATR", "func": vortex_atr},
    {"id": "VTX_04", "name": "Vortex Divergence", "name_fa": "ورتکس: واگرایی", "func": vortex_divergence},
]

ULT_STRATEGIES = [
    {"id": "ULT_01", "name": "Ultimate OB/OS", "name_fa": "UO: اشباع", "func": ultimate_obos},
    {"id": "ULT_02", "name": "Ultimate Divergence", "name_fa": "UO: واگرایی", "func": ultimate_divergence},
    {"id": "ULT_03", "name": "Ultimate Multi", "name_fa": "UO: چند دوره", "func": ultimate_multi},
    {"id": "ULT_04", "name": "Ultimate Trend", "name_fa": "UO: + روند", "func": ultimate_trend},
]

KST_STRATEGIES = [
    {"id": "KST_01", "name": "KST Cross", "name_fa": "KST: تقاطع سیگنال", "func": kst_cross},
    {"id": "KST_02", "name": "KST Zero", "name_fa": "KST: خط صفر", "func": kst_zero},
    {"id": "KST_03", "name": "KST Divergence", "name_fa": "KST: واگرایی", "func": kst_divergence},
]

# Combined for easy import
PHASE7_ALL = SRSI_STRATEGIES if 'SRSI_STRATEGIES' in dir() else []
PHASE7_ALL = ARN_STRATEGIES + VTX_STRATEGIES + ULT_STRATEGIES + KST_STRATEGIES
