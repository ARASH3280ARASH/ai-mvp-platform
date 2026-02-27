"""
Whilber-AI — Volume Strategy Pack (8 Sub-Strategies)
=====================================================
VOL_01: Volume Spike (Unusual Volume)
VOL_02: OBV Trend (On-Balance Volume Direction)
VOL_03: Volume Price Trend (VPT)
VOL_04: Volume Climax (Exhaustion)
VOL_05: Accumulation/Distribution (A/D Line)
VOL_06: Money Flow Index (MFI) Overbought/Oversold
VOL_07: Chaikin Money Flow (CMF)
VOL_08: Volume Dry-Up (Low Volume = Breakout Coming)
"""

import numpy as np
import pandas as pd


def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _get_volume(df):
    """Get volume from either 'tick_volume' or 'volume' column."""
    vol = df.get('tick_volume', df.get('volume', None))
    if vol is None:
        return None
    if isinstance(vol, pd.Series) and vol.sum() == 0:
        return None
    return vol


# ─────────────────────────────────────────────────────
# VOL_01: Volume Spike (Unusual Volume)
# BUY:  Volume > 2x average + bullish candle
# SELL: Volume > 2x average + bearish candle
# ─────────────────────────────────────────────────────
def vol_01_spike(df, context=None):
    vol = _get_volume(df)
    if vol is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    avg_vol = _sma(vol, 20)
    if avg_vol.isna().iloc[-1] or avg_vol.iloc[-1] == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    v = vol.iloc[-1]
    avg = avg_vol.iloc[-1]
    ratio = v / avg
    is_bull = df['close'].iloc[-1] > df['open'].iloc[-1]
    is_bear = df['close'].iloc[-1] < df['open'].iloc[-1]
    body_pct = abs(df['close'].iloc[-1] - df['open'].iloc[-1]) / df['close'].iloc[-1] * 100

    if ratio >= 3 and is_bull:
        return {"signal": "BUY", "confidence": min(88, 65 + int(ratio * 5)),
                "reason_fa": f"جهش حجم {ratio:.1f}x + کندل صعودی ({body_pct:.2f}%) — فشار خرید شدید"}
    elif ratio >= 3 and is_bear:
        return {"signal": "SELL", "confidence": min(88, 65 + int(ratio * 5)),
                "reason_fa": f"جهش حجم {ratio:.1f}x + کندل نزولی ({body_pct:.2f}%) — فشار فروش شدید"}
    elif ratio >= 2 and is_bull:
        return {"signal": "BUY", "confidence": min(75, 55 + int(ratio * 8)),
                "reason_fa": f"حجم بالا {ratio:.1f}x + صعودی ({body_pct:.2f}%)"}
    elif ratio >= 2 and is_bear:
        return {"signal": "SELL", "confidence": min(75, 55 + int(ratio * 8)),
                "reason_fa": f"حجم بالا {ratio:.1f}x + نزولی ({body_pct:.2f}%)"}
    elif ratio >= 1.5:
        dir_str = "صعودی" if is_bull else "نزولی"
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"حجم نسبتا بالا {ratio:.1f}x — {dir_str} ولی نه جهش"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"حجم عادی ({ratio:.1f}x میانگین)"}


# ─────────────────────────────────────────────────────
# VOL_02: OBV Trend (On-Balance Volume Direction)
# BUY:  OBV making higher highs while EMA(20) of OBV rising
# SELL: OBV making lower lows while EMA(20) of OBV falling
# ─────────────────────────────────────────────────────
def vol_02_obv_trend(df, context=None):
    vol = _get_volume(df)
    if vol is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    close = df['close']
    obv = pd.Series(0.0, index=df.index)
    for i in range(1, len(df)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + vol.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - vol.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]

    obv_ema = _ema(obv, 20)
    if obv_ema.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    obv_now = obv.iloc[-1]
    obv_ema_now = obv_ema.iloc[-1]
    obv_slope = obv_ema.iloc[-1] - obv_ema.iloc[-5] if len(obv_ema) > 5 else 0
    price_slope = close.iloc[-1] - close.iloc[-5] if len(close) > 5 else 0

    # OBV above its EMA and rising
    if obv_now > obv_ema_now and obv_slope > 0:
        if price_slope > 0:
            return {"signal": "BUY", "confidence": 72,
                    "reason_fa": "OBV صعودی بالای میانگین — حجم از قیمت حمایت می‌کند"}
        else:
            return {"signal": "BUY", "confidence": 65,
                    "reason_fa": "OBV صعودی ولی قیمت نزولی — انباشت پنهان (تجمیع)"}

    elif obv_now < obv_ema_now and obv_slope < 0:
        if price_slope < 0:
            return {"signal": "SELL", "confidence": 72,
                    "reason_fa": "OBV نزولی زیر میانگین — حجم تایید نزول"}
        else:
            return {"signal": "SELL", "confidence": 65,
                    "reason_fa": "OBV نزولی ولی قیمت صعودی — توزیع پنهان (فروش)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "OBV بدون جهت مشخص"}


# ─────────────────────────────────────────────────────
# VOL_03: Volume Price Trend (VPT)
# BUY:  VPT crossing above its signal line
# SELL: VPT crossing below its signal line
# ─────────────────────────────────────────────────────
def vol_03_vpt(df, context=None):
    vol = _get_volume(df)
    if vol is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    close = df['close']
    pct_change = close.pct_change()
    vpt = (pct_change * vol).cumsum()
    vpt_signal = _ema(vpt, 14)

    if vpt_signal.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    v = vpt.iloc[-1]
    s = vpt_signal.iloc[-1]
    v_prev = vpt.iloc[-2]
    s_prev = vpt_signal.iloc[-2]

    if v_prev <= s_prev and v > s:
        return {"signal": "BUY", "confidence": 74,
                "reason_fa": "VPT از سیگنال عبور کرد (بالا) — فشار خرید حجمی تایید شد"}
    elif v_prev >= s_prev and v < s:
        return {"signal": "SELL", "confidence": 74,
                "reason_fa": "VPT از سیگنال عبور کرد (پایین) — فشار فروش حجمی تایید شد"}
    elif v > s:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": "VPT بالای سیگنال — مومنتوم حجمی مثبت"}
    elif v < s:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": "VPT زیر سیگنال — مومنتوم حجمی منفی"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "VPT خنثی"}


# ─────────────────────────────────────────────────────
# VOL_04: Volume Climax (Exhaustion)
# Extremely high volume at end of trend = potential reversal
# ─────────────────────────────────────────────────────
def vol_04_climax(df, context=None):
    vol = _get_volume(df)
    if vol is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    close = df['close']
    avg_vol = _sma(vol, 20)
    if avg_vol.isna().iloc[-1] or avg_vol.iloc[-1] == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    v = vol.iloc[-1]
    avg = avg_vol.iloc[-1]
    ratio = v / avg

    # Check trend before climax
    if len(close) < 11:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    recent_change = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100
    is_bull_candle = close.iloc[-1] > df['open'].iloc[-1]

    # Climax: very high volume (3x+) after extended move
    if ratio < 2.5:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"حجم عادی ({ratio:.1f}x) — بدون کلایمکس"}

    # Selling climax at bottom (high vol + bearish after decline)
    if recent_change < -3 and not is_bull_candle and ratio >= 2.5:
        return {"signal": "BUY", "confidence": min(82, 60 + int(ratio * 5)),
                "reason_fa": f"کلایمکس فروش — حجم {ratio:.1f}x بعد از افت {recent_change:.1f}% — فرسودگی فروش"}

    # Buying climax at top (high vol + bullish after rally)
    if recent_change > 3 and is_bull_candle and ratio >= 2.5:
        return {"signal": "SELL", "confidence": min(82, 60 + int(ratio * 5)),
                "reason_fa": f"کلایمکس خرید — حجم {ratio:.1f}x بعد از رشد {recent_change:.1f}% — فرسودگی خرید"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"حجم بالا ({ratio:.1f}x) ولی بدون الگوی کلایمکس"}


# ─────────────────────────────────────────────────────
# VOL_05: Accumulation/Distribution Line
# BUY:  A/D Line rising while price falling (accumulation)
# SELL: A/D Line falling while price rising (distribution)
# ─────────────────────────────────────────────────────
def vol_05_ad_line(df, context=None):
    vol = _get_volume(df)
    if vol is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    high = df['high']; low = df['low']; close = df['close']
    hl_range = high - low
    clv = ((close - low) - (high - close)) / hl_range.replace(0, 1e-10)
    ad = (clv * vol).cumsum()
    ad_ema = _ema(ad, 10)

    if ad_ema.isna().iloc[-1] or len(close) < 11:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    ad_slope = ad_ema.iloc[-1] - ad_ema.iloc[-5]
    price_slope = close.iloc[-1] - close.iloc[-5]
    price_pct = price_slope / close.iloc[-5] * 100

    # Accumulation: A/D up, price down or flat
    if ad_slope > 0 and price_pct < -0.5:
        return {"signal": "BUY", "confidence": 76,
                "reason_fa": f"تجمیع (Accumulation) — A/D صعودی ولی قیمت نزولی ({price_pct:+.2f}%) — خرید هوشمند"}
    # Distribution: A/D down, price up or flat
    elif ad_slope < 0 and price_pct > 0.5:
        return {"signal": "SELL", "confidence": 76,
                "reason_fa": f"توزیع (Distribution) — A/D نزولی ولی قیمت صعودی ({price_pct:+.2f}%) — فروش هوشمند"}
    # Confirmation
    elif ad_slope > 0 and price_pct > 0:
        return {"signal": "BUY", "confidence": 52,
                "reason_fa": f"A/D تایید صعود — هم قیمت هم حجم صعودی ({price_pct:+.2f}%)"}
    elif ad_slope < 0 and price_pct < 0:
        return {"signal": "SELL", "confidence": 52,
                "reason_fa": f"A/D تایید نزول — هم قیمت هم حجم نزولی ({price_pct:+.2f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "خط A/D بدون سیگنال واضح"}


# ─────────────────────────────────────────────────────
# VOL_06: Money Flow Index (MFI) Overbought/Oversold
# BUY:  MFI < 20 (oversold) and turning up
# SELL: MFI > 80 (overbought) and turning down
# ─────────────────────────────────────────────────────
def vol_06_mfi(df, context=None):
    vol = _get_volume(df)
    if vol is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    period = 14
    tp = (df['high'] + df['low'] + df['close']) / 3
    mf = tp * vol

    pos_mf = pd.Series(0.0, index=df.index)
    neg_mf = pd.Series(0.0, index=df.index)
    for i in range(1, len(df)):
        if tp.iloc[i] > tp.iloc[i-1]:
            pos_mf.iloc[i] = mf.iloc[i]
        elif tp.iloc[i] < tp.iloc[i-1]:
            neg_mf.iloc[i] = mf.iloc[i]

    pos_sum = pos_mf.rolling(period).sum()
    neg_sum = neg_mf.rolling(period).sum()
    mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))

    if mfi.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    m = mfi.iloc[-1]
    m_prev = mfi.iloc[-2]

    if m_prev < 20 and m >= 20:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"MFI از اشباع فروش برگشت — MFI({m:.1f}) بالای ۲۰"}
    elif m_prev > 80 and m <= 80:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"MFI از اشباع خرید برگشت — MFI({m:.1f}) زیر ۸۰"}
    elif m < 20:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"MFI در اشباع فروش ({m:.1f}) — منتظر برگشت"}
    elif m > 80:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"MFI در اشباع خرید ({m:.1f}) — منتظر برگشت"}
    elif m < 40:
        return {"signal": "BUY", "confidence": 42,
                "reason_fa": f"MFI نسبتا پایین ({m:.1f})"}
    elif m > 60:
        return {"signal": "SELL", "confidence": 42,
                "reason_fa": f"MFI نسبتا بالا ({m:.1f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"MFI خنثی ({m:.1f})"}


# ─────────────────────────────────────────────────────
# VOL_07: Chaikin Money Flow (CMF)
# BUY:  CMF > 0 and rising (money flowing in)
# SELL: CMF < 0 and falling (money flowing out)
# ─────────────────────────────────────────────────────
def vol_07_cmf(df, context=None):
    vol = _get_volume(df)
    if vol is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    period = 20
    high = df['high']; low = df['low']; close = df['close']
    hl_range = high - low
    clv = ((close - low) - (high - close)) / hl_range.replace(0, 1e-10)
    mf_vol = clv * vol

    cmf = mf_vol.rolling(period).sum() / vol.rolling(period).sum().replace(0, 1e-10)
    if cmf.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    c = cmf.iloc[-1]
    c_prev = cmf.iloc[-2]

    if c_prev <= 0 and c > 0:
        return {"signal": "BUY", "confidence": 76,
                "reason_fa": f"CMF از منفی به مثبت — جریان پول ورودی ({c:+.3f})"}
    elif c_prev >= 0 and c < 0:
        return {"signal": "SELL", "confidence": 76,
                "reason_fa": f"CMF از مثبت به منفی — جریان پول خروجی ({c:+.3f})"}
    elif c > 0.1:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"CMF قوی مثبت — جریان پول ورودی قوی ({c:+.3f})"}
    elif c < -0.1:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"CMF قوی منفی — جریان پول خروجی قوی ({c:+.3f})"}
    elif c > 0:
        return {"signal": "BUY", "confidence": 42,
                "reason_fa": f"CMF اندکی مثبت ({c:+.3f})"}
    elif c < 0:
        return {"signal": "SELL", "confidence": 42,
                "reason_fa": f"CMF اندکی منفی ({c:+.3f})"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": f"CMF صفر ({c:+.3f})"}


# ─────────────────────────────────────────────────────
# VOL_08: Volume Dry-Up (Low Volume = Breakout Coming)
# Very low volume for several bars = compression before move
# ─────────────────────────────────────────────────────
def vol_08_dryup(df, context=None):
    vol = _get_volume(df)
    if vol is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    avg_vol = _sma(vol, 50)
    if avg_vol.isna().iloc[-1] or avg_vol.iloc[-1] == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    # Check last 5 bars for low volume
    recent_vol = vol.tail(5)
    avg = avg_vol.iloc[-1]
    low_vol_count = sum(1 for v in recent_vol if v < avg * 0.5)
    avg_recent_ratio = recent_vol.mean() / avg

    close = df['close']
    # Price range compression (Bollinger Band width proxy)
    high5 = df['high'].tail(5).max()
    low5 = df['low'].tail(5).min()
    range_pct = (high5 - low5) / close.iloc[-1] * 100

    # Determine bias from EMA
    ema20 = _ema(close, 20)
    above_ema = close.iloc[-1] > ema20.iloc[-1] if not ema20.isna().iloc[-1] else None

    if low_vol_count >= 4 and range_pct < 2:
        if above_ema:
            return {"signal": "BUY", "confidence": 68,
                    "reason_fa": f"خشکی حجم + فشردگی قیمت — آماده شکست صعودی ({low_vol_count}/5 کندل کم‌حجم, رنج {range_pct:.2f}%)"}
        elif above_ema is False:
            return {"signal": "SELL", "confidence": 68,
                    "reason_fa": f"خشکی حجم + فشردگی قیمت — آماده شکست نزولی ({low_vol_count}/5 کندل کم‌حجم, رنج {range_pct:.2f}%)"}
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"خشکی حجم — شکست نزدیک ولی جهت نامشخص ({avg_recent_ratio:.1f}x)"}

    elif low_vol_count >= 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"حجم نسبتا پایین ({low_vol_count}/5 کندل کم‌حجم) — نظارت"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"حجم عادی ({avg_recent_ratio:.1f}x میانگین)"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

VOLUME_STRATEGIES = [
    {"id": "VOL_01", "name": "Volume Spike", "name_fa": "جهش حجم", "func": vol_01_spike},
    {"id": "VOL_02", "name": "OBV Trend", "name_fa": "روند OBV", "func": vol_02_obv_trend},
    {"id": "VOL_03", "name": "Volume Price Trend", "name_fa": "روند قیمت-حجم VPT", "func": vol_03_vpt},
    {"id": "VOL_04", "name": "Volume Climax", "name_fa": "کلایمکس حجم", "func": vol_04_climax},
    {"id": "VOL_05", "name": "A/D Line", "name_fa": "خط انباشت/توزیع", "func": vol_05_ad_line},
    {"id": "VOL_06", "name": "Money Flow Index", "name_fa": "شاخص جریان پول MFI", "func": vol_06_mfi},
    {"id": "VOL_07", "name": "Chaikin Money Flow", "name_fa": "جریان پول چایکین CMF", "func": vol_07_cmf},
    {"id": "VOL_08", "name": "Volume Dry-Up", "name_fa": "خشکی حجم (شکست نزدیک)", "func": vol_08_dryup},
]
