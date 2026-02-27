"""
Whilber-AI — Regression Channel Strategy Pack (5 Sub-Strategies)
==================================================================
REG_01: Linear Regression Bounce (price at band edge)
REG_02: Regression Slope Change (trend direction shift)
REG_03: Regression Deviation Extreme (>2 std from regression)
REG_04: R-Squared Trend (high R² = tradeable trend)
REG_05: Regression Mean Revert (return to center line)
"""

import numpy as np

CATEGORY_ID = "REG"
CATEGORY_NAME = "Regression Channel"
CATEGORY_FA = "کانال رگرسیون"
ICON = "📐"
COLOR = "#607d8b"


def _linreg(close, period=50):
    """Linear regression line + channels."""
    if len(close) < period:
        return None, None, None, None, None
    y = close[-period:]
    x = np.arange(period)
    # Fit
    mx, my = np.mean(x), np.mean(y)
    ss_xy = np.sum((x - mx) * (y - my))
    ss_xx = np.sum((x - mx) ** 2)
    slope = ss_xy / ss_xx if ss_xx != 0 else 0
    intercept = my - slope * mx
    reg_line = slope * x + intercept
    # Residuals
    residuals = y - reg_line
    std = np.std(residuals)
    # R²
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - my) ** 2)
    r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return reg_line, slope, std, r_sq, residuals


def _atr(high, low, close, period=14):
    if len(high) < period + 1: return None
    tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-close[:-1]), abs(low[1:]-close[:-1])))
    atr = np.zeros(len(tr))
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1]*(period-1)+tr[i])/period
    return np.concatenate([[0], atr])


def _pip_size(symbol):
    s = symbol.upper()
    if "JPY" in s: return 0.01
    if "XAU" in s: return 0.1
    if "XAG" in s: return 0.01
    if "BTC" in s: return 1.0
    if s in ("NAS100","US30","SPX500","GER40","UK100"): return 1.0
    return 0.0001


def _make_setup(direction, entry, atr_val, pip, rr_min=1.5):
    if atr_val is None or atr_val <= 0: return None
    sl_dist = atr_val * 1.5
    tp1_dist = sl_dist * rr_min
    tp2_dist = sl_dist * 3.0
    if direction == "BUY":
        sl, tp1, tp2 = entry-sl_dist, entry+tp1_dist, entry+tp2_dist
    else:
        sl, tp1, tp2 = entry+sl_dist, entry-tp1_dist, entry-tp2_dist
    if tp1_dist/sl_dist < rr_min: return None
    return {"has_setup": True, "direction": direction,
            "direction_fa": "خرید" if direction=="BUY" else "فروش",
            "entry": round(entry,6), "stop_loss": round(sl,6),
            "tp1": round(tp1,6), "tp2": round(tp2,6),
            "rr1": round(tp1_dist/sl_dist,2), "rr2": round(tp2_dist/sl_dist,2),
            "sl_pips": round(sl_dist/pip,1) if pip>0 else 0,
            "tp1_pips": round(tp1_dist/pip,1) if pip>0 else 0}


def _neutral(r):
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": r, "setup": {"has_setup": False}}


def reg_01(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 55: return _neutral("داده کافی نیست")
    reg, slope, std, r_sq, res = _linreg(c, 50)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if reg is None: return _neutral("محاسبه رگرسیون ناموفق")

    reg_val = reg[-1]
    upper = reg_val + 2 * std
    lower = reg_val - 2 * std

    if price <= lower * 1.001 and c[-2] < c[-1]:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 70, "reason_fa": f"بانس از کف کانال رگرسیون — R²={r_sq:.2f}", "setup": setup}
    if price >= upper * 0.999 and c[-2] > c[-1]:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 70, "reason_fa": f"بانس از سقف کانال رگرسیون — R²={r_sq:.2f}", "setup": setup}
    return _neutral("بانس رگرسیون شناسایی نشد")


def reg_02(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 55: return _neutral("داده کافی نیست")
    reg1, slope1, _, _, _ = _linreg(c, 50)
    reg2, slope2, _, _, _ = _linreg(c[:-10], 50) if len(c) > 65 else (None, None, None, None, None)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if slope1 is None: return _neutral("محاسبه ناموفق")

    if slope2 is not None:
        if slope1 > 0 and slope2 <= 0:
            setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 72, "reason_fa": "تغییر شیب رگرسیون به صعودی — شروع روند جدید", "setup": setup}
        if slope1 < 0 and slope2 >= 0:
            setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 72, "reason_fa": "تغییر شیب رگرسیون به نزولی — شروع روند جدید", "setup": setup}
    return _neutral("تغییر شیب رگرسیون شناسایی نشد")


def reg_03(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 55: return _neutral("داده کافی نیست")
    reg, slope, std, r_sq, res = _linreg(c, 50)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    if reg is None: return _neutral("محاسبه ناموفق")
    z = res[-1] / std if std > 0 else 0

    if z < -2:
        setup = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 75, "reason_fa": f"انحراف شدید پایین رگرسیون — Z={z:.1f}", "setup": setup}
    if z > 2:
        setup = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 75, "reason_fa": f"انحراف شدید بالای رگرسیون — Z={z:.1f}", "setup": setup}
    return _neutral(f"انحراف رگرسیون کافی نیست — Z={z:.1f}")


def reg_04(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 55: return _neutral("داده کافی نیست")
    reg, slope, std, r_sq, _ = _linreg(c, 50)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if reg is None: return _neutral("محاسبه ناموفق")

    if r_sq > 0.8:
        if slope > 0:
            setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 78, "reason_fa": f"روند صعودی قوی — R²={r_sq:.2f} شیب مثبت", "setup": setup}
        elif slope < 0:
            setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 78, "reason_fa": f"روند نزولی قوی — R²={r_sq:.2f} شیب منفی", "setup": setup}
    return _neutral(f"R²={r_sq:.2f} — روند کافی نیست")


def reg_05(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 55: return _neutral("داده کافی نیست")
    reg, slope, std, r_sq, res = _linreg(c, 50)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if reg is None: return _neutral("محاسبه ناموفق")

    z = res[-1] / std if std > 0 else 0
    z_prev = res[-2] / std if std > 0 else 0

    # Returning to mean from extremes
    if z_prev < -1.5 and z > z_prev and z < 0:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 68, "reason_fa": f"بازگشت به میانگین رگرسیون — Z: {z_prev:.1f}→{z:.1f}", "setup": setup}

    if z_prev > 1.5 and z < z_prev and z > 0:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 68, "reason_fa": f"بازگشت به میانگین رگرسیون — Z: {z_prev:.1f}→{z:.1f}", "setup": setup}

    return _neutral("بازگشت به میانگین رگرسیون شناسایی نشد")


REG_STRATEGIES = [
    {"id": "REG_01", "name": "Regression Bounce", "name_fa": "بانس رگرسیون", "func": reg_01},
    {"id": "REG_02", "name": "Slope Change", "name_fa": "تغییر شیب", "func": reg_02},
    {"id": "REG_03", "name": "Deviation Extreme", "name_fa": "انحراف شدید", "func": reg_03},
    {"id": "REG_04", "name": "R² Trend", "name_fa": "روند R²", "func": reg_04},
    {"id": "REG_05", "name": "Mean Revert", "name_fa": "بازگشت میانگین", "func": reg_05},
]
