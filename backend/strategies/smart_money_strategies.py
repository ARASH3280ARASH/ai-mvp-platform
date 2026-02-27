"""
Whilber-AI — Smart Money Strategy Pack (10 Sub-Strategies)
============================================================
SM_01: Order Block Detection (Bullish/Bearish OB)
SM_02: Fair Value Gap (FVG / Imbalance)
SM_03: Break of Structure (BOS)
SM_04: Change of Character (CHoCH)
SM_05: Liquidity Sweep (Stop Hunt)
SM_06: Institutional Candle (Big Body + Volume)
SM_07: Supply & Demand Zones
SM_08: Equal Highs/Lows (Liquidity Pool)
SM_09: Displacement (Strong Momentum Move)
SM_10: Smart Money + Trend Confluence
"""

import numpy as np
import pandas as pd


def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _avg_body(df, n=20):
    return (df['close'] - df['open']).abs().tail(n).mean()


def _avg_range(df, n=20):
    return (df['high'] - df['low']).tail(n).mean()


def _get_volume(df):
    vol = df.get('tick_volume', df.get('volume', None))
    if vol is None or (isinstance(vol, pd.Series) and vol.sum() == 0):
        return None
    return vol


def _swing_highs_lows(df, order=5, count=10):
    """Find recent swing highs and lows."""
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    n = len(high)
    highs = []  # (index, value)
    lows = []
    for i in range(order, n - order):
        if all(high[i] >= high[i-j] for j in range(1, order+1)) and all(high[i] >= high[i+j] for j in range(1, order+1)):
            highs.append((i, high[i]))
        if all(low[i] <= low[i-j] for j in range(1, order+1)) and all(low[i] <= low[i+j] for j in range(1, order+1)):
            lows.append((i, low[i]))
    return highs[-count:], lows[-count:]


# ─────────────────────────────────────────────────────
# SM_01: Order Block Detection
# Bullish OB: last bearish candle before strong bullish move
# Bearish OB: last bullish candle before strong bearish move
# BUY:  Price returns to bullish order block zone
# SELL: Price returns to bearish order block zone
# ─────────────────────────────────────────────────────
def sm_01_order_block(df, context=None):
    if len(df) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    close = df['close']; op = df['open']; high = df['high']; low = df['low']
    avg_body = _avg_body(df, 20)
    p = close.iloc[-1]

    # Search last 20 bars for order blocks
    bull_ob = None  # (ob_high, ob_low)
    bear_ob = None

    for i in range(-15, -3):
        body_i = abs(close.iloc[i] - op.iloc[i])
        is_bearish_i = close.iloc[i] < op.iloc[i]
        is_bullish_i = close.iloc[i] > op.iloc[i]

        # Check if next 2 candles made a strong move
        body_next1 = abs(close.iloc[i+1] - op.iloc[i+1])
        body_next2 = abs(close.iloc[i+2] - op.iloc[i+2])
        move = close.iloc[i+2] - close.iloc[i]
        move_pct = abs(move) / p * 100

        # Bullish OB: bearish candle + strong bullish follow
        if is_bearish_i and move > 0 and move_pct > 0.5 and (body_next1 + body_next2) > avg_body * 2:
            bull_ob = (max(op.iloc[i], close.iloc[i]), min(op.iloc[i], close.iloc[i]))

        # Bearish OB: bullish candle + strong bearish follow
        if is_bullish_i and move < 0 and move_pct > 0.5 and (body_next1 + body_next2) > avg_body * 2:
            bear_ob = (max(op.iloc[i], close.iloc[i]), min(op.iloc[i], close.iloc[i]))

    # Check if price is at an order block
    if bull_ob and bull_ob[1] <= p <= bull_ob[0]:
        return {"signal": "BUY", "confidence": 78,
                "reason_fa": f"قیمت در اردر بلاک صعودی ({bull_ob[1]:.4f}-{bull_ob[0]:.4f}) — ناحیه تقاضای نهادی"}
    elif bull_ob and abs(p - bull_ob[0]) / p < 0.003:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"قیمت نزدیک اردر بلاک صعودی ({bull_ob[0]:.4f})"}

    if bear_ob and bear_ob[1] <= p <= bear_ob[0]:
        return {"signal": "SELL", "confidence": 78,
                "reason_fa": f"قیمت در اردر بلاک نزولی ({bear_ob[1]:.4f}-{bear_ob[0]:.4f}) — ناحیه عرضه نهادی"}
    elif bear_ob and abs(p - bear_ob[1]) / p < 0.003:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"قیمت نزدیک اردر بلاک نزولی ({bear_ob[1]:.4f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "اردر بلاک فعال در نزدیکی قیمت یافت نشد"}


# ─────────────────────────────────────────────────────
# SM_02: Fair Value Gap (FVG / Imbalance)
# Gap between candle 1 high and candle 3 low (bullish)
# or candle 1 low and candle 3 high (bearish)
# BUY:  Price fills bullish FVG
# SELL: Price fills bearish FVG
# ─────────────────────────────────────────────────────
def sm_02_fvg(df, context=None):
    if len(df) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    high = df['high']; low = df['low']; close = df['close']
    p = close.iloc[-1]

    bull_fvg = None
    bear_fvg = None

    # Search last 15 bars for FVG
    for i in range(-12, -2):
        # Bullish FVG: candle[i] high < candle[i+2] low (gap up)
        if high.iloc[i] < low.iloc[i+2]:
            gap_top = low.iloc[i+2]
            gap_bot = high.iloc[i]
            gap_pct = (gap_top - gap_bot) / p * 100
            if gap_pct > 0.1:
                bull_fvg = (gap_top, gap_bot, gap_pct)

        # Bearish FVG: candle[i] low > candle[i+2] high (gap down)
        if low.iloc[i] > high.iloc[i+2]:
            gap_top = low.iloc[i]
            gap_bot = high.iloc[i+2]
            gap_pct = (gap_top - gap_bot) / p * 100
            if gap_pct > 0.1:
                bear_fvg = (gap_top, gap_bot, gap_pct)

    if bull_fvg and bull_fvg[1] <= p <= bull_fvg[0]:
        return {"signal": "BUY", "confidence": 76,
                "reason_fa": f"قیمت در FVG صعودی ({bull_fvg[2]:.2f}%) — پر کردن گپ ارزش منصفانه"}
    elif bull_fvg and p < bull_fvg[1] and abs(p - bull_fvg[1]) / p < 0.005:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"قیمت نزدیک FVG صعودی ({bull_fvg[1]:.4f})"}

    if bear_fvg and bear_fvg[1] <= p <= bear_fvg[0]:
        return {"signal": "SELL", "confidence": 76,
                "reason_fa": f"قیمت در FVG نزولی ({bear_fvg[2]:.2f}%) — پر کردن گپ ارزش منصفانه"}
    elif bear_fvg and p > bear_fvg[0] and abs(p - bear_fvg[0]) / p < 0.005:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"قیمت نزدیک FVG نزولی ({bear_fvg[0]:.4f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "FVG فعال در نزدیکی قیمت یافت نشد"}


# ─────────────────────────────────────────────────────
# SM_03: Break of Structure (BOS)
# BUY:  Price breaks above recent swing high (uptrend continuation)
# SELL: Price breaks below recent swing low (downtrend continuation)
# ─────────────────────────────────────────────────────
def sm_03_bos(df, context=None):
    if len(df) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    highs, lows = _swing_highs_lows(df, order=5, count=5)
    close = df['close']
    p = close.iloc[-1]
    p_prev = close.iloc[-2]

    if len(highs) < 2 or len(lows) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی نیست"}

    recent_high = highs[-1][1]
    recent_low = lows[-1][1]
    prev_high = highs[-2][1] if len(highs) >= 2 else recent_high
    prev_low = lows[-2][1] if len(lows) >= 2 else recent_low

    # BOS Up: price breaks above recent swing high
    if p > recent_high and p_prev <= recent_high:
        break_pct = (p - recent_high) / p * 100
        return {"signal": "BUY", "confidence": min(85, 70 + int(break_pct * 20)),
                "reason_fa": f"شکست ساختار صعودی (BOS) — عبور از سقف {recent_high:.4f} ({break_pct:+.2f}%)"}

    # BOS Down: price breaks below recent swing low
    if p < recent_low and p_prev >= recent_low:
        break_pct = (recent_low - p) / p * 100
        return {"signal": "SELL", "confidence": min(85, 70 + int(break_pct * 20)),
                "reason_fa": f"شکست ساختار نزولی (BOS) — عبور از کف {recent_low:.4f} ({break_pct:+.2f}%)"}

    # Higher highs/higher lows structure
    if recent_high > prev_high and recent_low > prev_low:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"ساختار صعودی — سقف و کف بالاتر"}
    elif recent_high < prev_high and recent_low < prev_low:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"ساختار نزولی — سقف و کف پایین‌تر"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "شکست ساختار شناسایی نشد"}


# ─────────────────────────────────────────────────────
# SM_04: Change of Character (CHoCH)
# Trend reversal signal: structure shifts from HH/HL to LH/LL or vice versa
# BUY:  First higher high after series of lower highs
# SELL: First lower low after series of higher lows
# ─────────────────────────────────────────────────────
def sm_04_choch(df, context=None):
    if len(df) < 40:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    highs, lows = _swing_highs_lows(df, order=4, count=6)
    p = df['close'].iloc[-1]

    if len(highs) < 3 or len(lows) < 3:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی نیست"}

    h_vals = [h[1] for h in highs[-4:]]
    l_vals = [l[1] for l in lows[-4:]]

    # CHoCH Bullish: was making lower highs, now made a higher high
    if len(h_vals) >= 3:
        was_lower = h_vals[-3] > h_vals[-2]  # Previous was lower high
        now_higher = h_vals[-1] > h_vals[-2]  # Current is higher high
        if was_lower and now_higher:
            return {"signal": "BUY", "confidence": 82,
                    "reason_fa": f"تغییر کاراکتر صعودی (CHoCH) — اولین سقف بالاتر بعد از سقف‌های پایین‌تر"}

    # CHoCH Bearish: was making higher lows, now made a lower low
    if len(l_vals) >= 3:
        was_higher = l_vals[-3] < l_vals[-2]  # Previous was higher low
        now_lower = l_vals[-1] < l_vals[-2]  # Current is lower low
        if was_higher and now_lower:
            return {"signal": "SELL", "confidence": 82,
                    "reason_fa": f"تغییر کاراکتر نزولی (CHoCH) — اولین کف پایین‌تر بعد از کف‌های بالاتر"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "تغییر کاراکتر (CHoCH) شناسایی نشد"}


# ─────────────────────────────────────────────────────
# SM_05: Liquidity Sweep (Stop Hunt)
# Price briefly breaks a level then reverses
# BUY:  Price sweeps below swing low then closes back above
# SELL: Price sweeps above swing high then closes back below
# ─────────────────────────────────────────────────────
def sm_05_liquidity_sweep(df, context=None):
    if len(df) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    highs, lows = _swing_highs_lows(df, order=5, count=5)
    close = df['close']; low_s = df['low']; high_s = df['high']
    p = close.iloc[-1]
    candle_low = low_s.iloc[-1]
    candle_high = high_s.iloc[-1]

    # Sweep below swing low (stop hunt) then close above
    for _, sw_low_val in lows[-3:]:
        if candle_low < sw_low_val and p > sw_low_val:
            sweep_depth = (sw_low_val - candle_low) / p * 100
            if sweep_depth > 0.05:
                return {"signal": "BUY", "confidence": min(85, 68 + int(sweep_depth * 30)),
                        "reason_fa": f"شکار نقدینگی زیر کف ({sw_low_val:.4f}) — سوئیپ {sweep_depth:.2f}% و برگشت"}

    # Sweep above swing high (stop hunt) then close below
    for _, sw_high_val in highs[-3:]:
        if candle_high > sw_high_val and p < sw_high_val:
            sweep_depth = (candle_high - sw_high_val) / p * 100
            if sweep_depth > 0.05:
                return {"signal": "SELL", "confidence": min(85, 68 + int(sweep_depth * 30)),
                        "reason_fa": f"شکار نقدینگی بالای سقف ({sw_high_val:.4f}) — سوئیپ {sweep_depth:.2f}% و برگشت"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "شکار نقدینگی شناسایی نشد"}


# ─────────────────────────────────────────────────────
# SM_06: Institutional Candle (Big Body + High Volume)
# Large candle with volume > 2x = institutional activity
# ─────────────────────────────────────────────────────
def sm_06_institutional_candle(df, context=None):
    vol = _get_volume(df)
    close = df['close']; op = df['open']
    body = abs(close.iloc[-1] - op.iloc[-1])
    avg_body = _avg_body(df, 20)
    is_bull = close.iloc[-1] > op.iloc[-1]

    if avg_body == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    body_ratio = body / avg_body

    if vol is not None:
        avg_vol = _sma(vol, 20)
        if not avg_vol.isna().iloc[-1] and avg_vol.iloc[-1] > 0:
            vol_ratio = vol.iloc[-1] / avg_vol.iloc[-1]
        else:
            vol_ratio = 1
    else:
        vol_ratio = 1  # No volume data, rely on body only

    # Institutional candle: body > 2x average + volume > 1.5x
    if body_ratio >= 2.5 and vol_ratio >= 2:
        if is_bull:
            return {"signal": "BUY", "confidence": min(88, 70 + int(body_ratio * 5)),
                    "reason_fa": f"کندل نهادی صعودی — بدنه {body_ratio:.1f}x + حجم {vol_ratio:.1f}x — ورود پول هوشمند"}
        else:
            return {"signal": "SELL", "confidence": min(88, 70 + int(body_ratio * 5)),
                    "reason_fa": f"کندل نهادی نزولی — بدنه {body_ratio:.1f}x + حجم {vol_ratio:.1f}x — خروج پول هوشمند"}
    elif body_ratio >= 2:
        if is_bull:
            return {"signal": "BUY", "confidence": 65,
                    "reason_fa": f"کندل بزرگ صعودی — بدنه {body_ratio:.1f}x (حجم {vol_ratio:.1f}x)"}
        else:
            return {"signal": "SELL", "confidence": 65,
                    "reason_fa": f"کندل بزرگ نزولی — بدنه {body_ratio:.1f}x (حجم {vol_ratio:.1f}x)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"کندل عادی (بدنه {body_ratio:.1f}x, حجم {vol_ratio:.1f}x)"}


# ─────────────────────────────────────────────────────
# SM_07: Supply & Demand Zones
# Supply: area where price dropped sharply (resistance)
# Demand: area where price rose sharply (support)
# ─────────────────────────────────────────────────────
def sm_07_supply_demand(df, context=None):
    if len(df) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    close = df['close']; op = df['open']; high = df['high']; low = df['low']
    p = close.iloc[-1]
    avg_range = _avg_range(df, 20)
    demand_zones = []  # (zone_high, zone_low)
    supply_zones = []

    for i in range(-20, -3):
        body = close.iloc[i] - op.iloc[i]
        move_after = close.iloc[i+2] - close.iloc[i]
        move_pct = abs(move_after) / p * 100

        if move_after > avg_range * 1.5 and body < 0:
            demand_zones.append((max(op.iloc[i], close.iloc[i]), min(op.iloc[i], close.iloc[i])))
        elif move_after < -avg_range * 1.5 and body > 0:
            supply_zones.append((max(op.iloc[i], close.iloc[i]), min(op.iloc[i], close.iloc[i])))

    # Check if price is in any zone
    for z_high, z_low in demand_zones[-3:]:
        if z_low <= p <= z_high:
            return {"signal": "BUY", "confidence": 75,
                    "reason_fa": f"قیمت در ناحیه تقاضا ({z_low:.4f}-{z_high:.4f}) — حمایت اسمارت مانی"}
        elif abs(p - z_high) / p < 0.003:
            return {"signal": "BUY", "confidence": 60,
                    "reason_fa": f"قیمت نزدیک ناحیه تقاضا ({z_high:.4f})"}

    for z_high, z_low in supply_zones[-3:]:
        if z_low <= p <= z_high:
            return {"signal": "SELL", "confidence": 75,
                    "reason_fa": f"قیمت در ناحیه عرضه ({z_low:.4f}-{z_high:.4f}) — مقاومت اسمارت مانی"}
        elif abs(p - z_low) / p < 0.003:
            return {"signal": "SELL", "confidence": 60,
                    "reason_fa": f"قیمت نزدیک ناحیه عرضه ({z_low:.4f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "ناحیه عرضه/تقاضای فعال یافت نشد"}


# ─────────────────────────────────────────────────────
# SM_08: Equal Highs / Equal Lows (Liquidity Pool)
# Equal highs = sell-side liquidity above
# Equal lows = buy-side liquidity below
# ─────────────────────────────────────────────────────
def sm_08_equal_hl(df, context=None):
    if len(df) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    highs, lows = _swing_highs_lows(df, order=4, count=8)
    p = df['close'].iloc[-1]
    tolerance = p * 0.002  # 0.2%

    # Find equal highs
    for i in range(len(highs)):
        for j in range(i+1, len(highs)):
            if abs(highs[i][1] - highs[j][1]) < tolerance:
                eq_level = (highs[i][1] + highs[j][1]) / 2
                dist = (eq_level - p) / p * 100
                if 0 < dist < 1:
                    return {"signal": "BUY", "confidence": 70,
                            "reason_fa": f"سقف‌های مساوی بالا ({eq_level:.4f}) — نقدینگی فروش = هدف صعودی ({dist:+.2f}%)"}
                elif -0.3 < dist < 0:
                    return {"signal": "SELL", "confidence": 72,
                            "reason_fa": f"رسیدن به سقف‌های مساوی ({eq_level:.4f}) — احتمال شکار نقدینگی و برگشت"}

    # Find equal lows
    for i in range(len(lows)):
        for j in range(i+1, len(lows)):
            if abs(lows[i][1] - lows[j][1]) < tolerance:
                eq_level = (lows[i][1] + lows[j][1]) / 2
                dist = (p - eq_level) / p * 100
                if 0 < dist < 1:
                    return {"signal": "SELL", "confidence": 70,
                            "reason_fa": f"کف‌های مساوی پایین ({eq_level:.4f}) — نقدینگی خرید = هدف نزولی ({dist:+.2f}%)"}
                elif -0.3 < dist < 0:
                    return {"signal": "BUY", "confidence": 72,
                            "reason_fa": f"رسیدن به کف‌های مساوی ({eq_level:.4f}) — احتمال شکار نقدینگی و برگشت"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "سقف/کف مساوی فعال یافت نشد"}


# ─────────────────────────────────────────────────────
# SM_09: Displacement (Strong Momentum Move)
# Series of strong candles in one direction = institutional push
# ─────────────────────────────────────────────────────
def sm_09_displacement(df, context=None):
    if len(df) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    avg_body = _avg_body(df, 20)
    avg_range = _avg_range(df, 20)
    if avg_body == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    # Check last 3 candles for displacement
    strong_bull = 0
    strong_bear = 0
    total_move = 0

    for i in range(-3, 0):
        body = df['close'].iloc[i] - df['open'].iloc[i]
        body_abs = abs(body)
        candle_range = df['high'].iloc[i] - df['low'].iloc[i]

        if body > avg_body * 1.5 and body_abs > candle_range * 0.6:
            strong_bull += 1
            total_move += body
        elif body < -avg_body * 1.5 and body_abs > candle_range * 0.6:
            strong_bear += 1
            total_move += body

    move_pct = total_move / df['close'].iloc[-1] * 100

    if strong_bull >= 2:
        return {"signal": "BUY", "confidence": min(85, 65 + strong_bull * 10),
                "reason_fa": f"جابجایی صعودی (Displacement) — {strong_bull} کندل قوی متوالی ({move_pct:+.2f}%)"}
    elif strong_bear >= 2:
        return {"signal": "SELL", "confidence": min(85, 65 + strong_bear * 10),
                "reason_fa": f"جابجایی نزولی (Displacement) — {strong_bear} کندل قوی متوالی ({move_pct:+.2f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "جابجایی نهادی شناسایی نشد"}


# ─────────────────────────────────────────────────────
# SM_10: Smart Money + Trend Confluence
# Combines: Order Block + BOS + FVG check for high-confidence signal
# ─────────────────────────────────────────────────────
def sm_10_confluence(df, context=None):
    if len(df) < 40:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    # Get sub-signals
    ob_sig = sm_01_order_block(df, context)
    bos_sig = sm_03_bos(df, context)
    fvg_sig = sm_02_fvg(df, context)

    bull_count = 0
    bear_count = 0
    details = []

    for name, sig in [("OB", ob_sig), ("BOS", bos_sig), ("FVG", fvg_sig)]:
        if sig["signal"] == "BUY" and sig["confidence"] > 50:
            bull_count += 1
            details.append(f"{name}+")
        elif sig["signal"] == "SELL" and sig["confidence"] > 50:
            bear_count += 1
            details.append(f"{name}-")

    detail_str = " + ".join(details) if details else "هیچ"

    if bull_count >= 3:
        return {"signal": "BUY", "confidence": 92,
                "reason_fa": f"همگرایی اسمارت مانی سه‌گانه صعودی — {detail_str}"}
    elif bear_count >= 3:
        return {"signal": "SELL", "confidence": 92,
                "reason_fa": f"همگرایی اسمارت مانی سه‌گانه نزولی — {detail_str}"}
    elif bull_count >= 2:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"همگرایی اسمارت مانی دوگانه صعودی — {detail_str}"}
    elif bear_count >= 2:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"همگرایی اسمارت مانی دوگانه نزولی — {detail_str}"}
    elif bull_count == 1:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"اسمارت مانی تکی صعودی — {detail_str}"}
    elif bear_count == 1:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"اسمارت مانی تکی نزولی — {detail_str}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "همگرایی اسمارت مانی شناسایی نشد"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

SM_STRATEGIES = [
    {"id": "SM_01", "name": "Order Block", "name_fa": "اردر بلاک", "func": sm_01_order_block},
    {"id": "SM_02", "name": "Fair Value Gap (FVG)", "name_fa": "گپ ارزش منصفانه", "func": sm_02_fvg},
    {"id": "SM_03", "name": "Break of Structure", "name_fa": "شکست ساختار (BOS)", "func": sm_03_bos},
    {"id": "SM_04", "name": "Change of Character", "name_fa": "تغییر کاراکتر (CHoCH)", "func": sm_04_choch},
    {"id": "SM_05", "name": "Liquidity Sweep", "name_fa": "شکار نقدینگی", "func": sm_05_liquidity_sweep},
    {"id": "SM_06", "name": "Institutional Candle", "name_fa": "کندل نهادی", "func": sm_06_institutional_candle},
    {"id": "SM_07", "name": "Supply & Demand", "name_fa": "عرضه و تقاضا", "func": sm_07_supply_demand},
    {"id": "SM_08", "name": "Equal Highs/Lows", "name_fa": "سقف/کف مساوی", "func": sm_08_equal_hl},
    {"id": "SM_09", "name": "Displacement", "name_fa": "جابجایی نهادی", "func": sm_09_displacement},
    {"id": "SM_10", "name": "Smart Money Confluence", "name_fa": "همگرایی اسمارت مانی", "func": sm_10_confluence},
]
