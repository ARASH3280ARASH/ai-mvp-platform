"""
Whilber-AI — Adaptive Strategies
====================================
ADP_01: Volatility-Adjusted
ADP_02: Timeframe-Adjusted
ADP_03: Trend/Range Switcher
ADP_04: Dynamic Threshold
ADP_05: Performance-Weighted
ADP_06: State Machine
"""

import numpy as np


def _get_other_results(context):
    if not context:
        return []
    return context.get("strategy_results", [])


def _ema(data, period):
    if len(data) < period:
        return None
    e = np.zeros(len(data))
    e[0] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(1, len(data)):
        e[i] = data[i] * m + e[i-1] * (1 - m)
    return e


# -- ADP_01: Volatility-Adjusted
def adaptive_volatility(df, context=None):
    """نوسان‌تطبیقی — پارامترها با ATR تنظیم"""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "نوسان‌تطبیقی — داده کافی نیست"}

    atr_pct = context.get("atr_percent", 1) if context else 1
    rsi = context.get("rsi_14", 50) if context else 50

    # Adjust RSI thresholds based on volatility
    if atr_pct > 2:
        # High volatility: wider thresholds
        ob_level = 85
        os_level = 15
        label = "نوسان بالا"
    elif atr_pct < 0.5:
        # Low volatility: tighter thresholds
        ob_level = 70
        os_level = 30
        label = "نوسان پایین"
    else:
        ob_level = 75
        os_level = 25
        label = "نوسان نرمال"

    if rsi < os_level:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"تطبیقی — RSI={rsi:.0f} < {os_level} ({label} ATR={atr_pct:.2f}%) | خرید"}
    elif rsi > ob_level:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"تطبیقی — RSI={rsi:.0f} > {ob_level} ({label} ATR={atr_pct:.2f}%) | فروش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"تطبیقی — RSI={rsi:.0f} در محدوده {os_level}-{ob_level} ({label})"}


# -- ADP_02: Timeframe-Adjusted
def adaptive_timeframe(df, context=None):
    """تایم‌فریم‌تطبیقی — وزن بر اساس مومنتوم چند دوره"""
    c = df["close"].values
    if len(c) < 50:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "TF تطبیقی — داده کافی نیست"}

    # Short, medium, long momentum
    roc_3 = (c[-1] - c[-3]) / c[-3] * 100
    roc_10 = (c[-1] - c[-10]) / c[-10] * 100
    roc_30 = (c[-1] - c[-30]) / c[-30] * 100

    # Weight: short=50%, medium=30%, long=20%
    score = roc_3 * 0.5 + roc_10 * 0.3 + roc_30 * 0.2

    if score > 1.0:
        conf = min(int(55 + abs(score) * 5), 80)
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"TF تطبیقی خرید — Score={score:.2f} (3d={roc_3:.1f}% 10d={roc_10:.1f}% 30d={roc_30:.1f}%)"}
    elif score < -1.0:
        conf = min(int(55 + abs(score) * 5), 80)
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"TF تطبیقی فروش — Score={score:.2f} (3d={roc_3:.1f}% 10d={roc_10:.1f}% 30d={roc_30:.1f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"TF تطبیقی — Score={score:.2f} | بدون جهت واضح"}


# -- ADP_03: Trend/Range Switcher
def adaptive_trend_range(df, context=None):
    """روند/رنج سوئیچ — ADX تعیین میکنه کدوم استراتژی"""
    results = _get_other_results(context)
    adx = context.get("adx", 25) if context else 25

    if len(results) < 5:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "سوئیچ — نتایج کافی نیست"}

    # Trending strategies
    trend_ids = {"MA_", "ADX_", "ST_", "ICH_", "MACD_", "ARN_", "VTX_"}
    # Range strategies
    range_ids = {"RSI_", "BB_", "STOCH_", "SRSI_", "CCI_", "ULT_", "WR_"}

    if adx > 25:
        # Use trend strategies
        filtered = [r for r in results if any(r.get("strategy_id", "").startswith(p) for p in trend_ids)]
        mode = "روند"
    else:
        # Use range strategies
        filtered = [r for r in results if any(r.get("strategy_id", "").startswith(p) for p in range_ids)]
        mode = "رنج"

    if not filtered:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"سوئیچ {mode} — استراتژی مرتبط یافت نشد"}

    buy_c = sum(1 for r in filtered if r["signal"] == "BUY" and r.get("confidence", 0) > 40)
    sell_c = sum(1 for r in filtered if r["signal"] == "SELL" and r.get("confidence", 0) > 40)
    total = buy_c + sell_c

    if total == 0:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"سوئیچ {mode} — بدون سیگنال فعال"}

    if buy_c > sell_c and buy_c / total > 0.6:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"سوئیچ {mode} خرید — {buy_c}/{total} ADX={adx:.0f}"}
    elif sell_c > buy_c and sell_c / total > 0.6:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"سوئیچ {mode} فروش — {sell_c}/{total} ADX={adx:.0f}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"سوئیچ {mode} — خرید={buy_c} فروش={sell_c} | بدون اکثریت"}


# -- ADP_04: Dynamic Threshold
def adaptive_dynamic_threshold(df, context=None):
    """آستانه پویا — سطوح OB/OS با نوسان و روند تنظیم"""
    c = df["close"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "آستانه پویا — داده کافی نیست"}

    rsi = context.get("rsi_14", 50) if context else 50
    stoch_k = context.get("stoch_k", 50) if context else 50
    adx = context.get("adx", 25) if context else 25
    atr_pct = context.get("atr_percent", 1) if context else 1

    # Dynamic thresholds
    # In strong trends: shift thresholds in trend direction
    # High volatility: widen thresholds
    vol_adj = min(atr_pct * 3, 10)

    if adx > 30:
        # Strong trend
        ema20 = _ema(c, 20)
        if ema20 is not None and c[-1] > ema20[-1]:
            # Uptrend: raise OS level (buy dips higher)
            os_rsi = 35 + vol_adj
            if rsi < os_rsi and stoch_k < 30:
                return {"signal": "BUY", "confidence": 65,
                        "reason_fa": f"آستانه پویا — RSI={rsi:.0f} < {os_rsi:.0f} (روند صعودی + ADX={adx:.0f}) | خرید اصلاح"}
        elif ema20 is not None:
            # Downtrend: lower OB level
            ob_rsi = 65 - vol_adj
            if rsi > ob_rsi and stoch_k > 70:
                return {"signal": "SELL", "confidence": 65,
                        "reason_fa": f"آستانه پویا — RSI={rsi:.0f} > {ob_rsi:.0f} (روند نزولی + ADX={adx:.0f}) | فروش بانس"}
    else:
        # Range: standard with vol adjustment
        os_level = 25 - vol_adj
        ob_level = 75 + vol_adj
        if rsi < os_level:
            return {"signal": "BUY", "confidence": 58,
                    "reason_fa": f"آستانه پویا — RSI={rsi:.0f} < {os_level:.0f} (رنج) | خرید"}
        elif rsi > ob_level:
            return {"signal": "SELL", "confidence": 58,
                    "reason_fa": f"آستانه پویا — RSI={rsi:.0f} > {ob_level:.0f} (رنج) | فروش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"آستانه پویا — RSI={rsi:.0f} ADX={adx:.0f} | خنثی"}


# -- ADP_05: Performance-Weighted
def adaptive_performance(df, context=None):
    """وزن عملکردی — وزن بیشتر به استراتژی‌های با اطمینان ثابت"""
    results = _get_other_results(context)
    if len(results) < 10:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "عملکردی — نتایج کافی نیست"}

    # Weight strategies by their confidence consistency
    # Higher confidence = more reliable historically
    buy_score = 0
    sell_score = 0
    total_w = 0

    for r in results:
        conf = r.get("confidence", 0)
        if conf < 30:
            continue

        # Cubic weighting: heavily favor high-confidence
        w = (conf / 100) ** 3
        total_w += w

        if r["signal"] == "BUY":
            buy_score += w
        elif r["signal"] == "SELL":
            sell_score += w

    if total_w == 0:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "عملکردی — وزن کل صفر"}

    buy_pct = buy_score / total_w * 100
    sell_pct = sell_score / total_w * 100

    if buy_pct > 60:
        return {"signal": "BUY", "confidence": min(int(buy_pct * 0.95), 88),
                "reason_fa": f"عملکردی خرید — {buy_pct:.0f}% وزن (cubic) | اطمینان بالا"}
    elif sell_pct > 60:
        return {"signal": "SELL", "confidence": min(int(sell_pct * 0.95), 88),
                "reason_fa": f"عملکردی فروش — {sell_pct:.0f}% وزن (cubic) | اطمینان بالا"}

    return {"signal": "NEUTRAL", "confidence": 20,
            "reason_fa": f"عملکردی — خرید={buy_pct:.0f}% فروش={sell_pct:.0f}% | بدون غلبه"}


# -- ADP_06: State Machine
def adaptive_state_machine(df, context=None):
    """ماشین حالت — ۵ حالت بازار و بهترین اقدام"""
    c = df["close"].values
    if len(c) < 30:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "State Machine — داده کافی نیست"}

    adx = context.get("adx", 25) if context else 25
    rsi = context.get("rsi_14", 50) if context else 50
    atr_pct = context.get("atr_percent", 1) if context else 1

    roc_10 = (c[-1] - c[-10]) / c[-10] * 100

    # 5 States:
    # 1. Strong Uptrend: ADX>30 + ROC>2 + RSI>50
    # 2. Strong Downtrend: ADX>30 + ROC<-2 + RSI<50
    # 3. Weak Trend: ADX 20-30
    # 4. Range: ADX<20 + low ATR
    # 5. Breakout: ADX rising + high ATR

    if adx > 30 and roc_10 > 2 and rsi > 50:
        state = "STRONG_UP"
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"State: روند صعودی قوی — ADX={adx:.0f} ROC={roc_10:.1f}% RSI={rsi:.0f} | خرید"}

    elif adx > 30 and roc_10 < -2 and rsi < 50:
        state = "STRONG_DOWN"
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"State: روند نزولی قوی — ADX={adx:.0f} ROC={roc_10:.1f}% RSI={rsi:.0f} | فروش"}

    elif 20 < adx < 30:
        state = "WEAK_TREND"
        if roc_10 > 1:
            return {"signal": "BUY", "confidence": 50,
                    "reason_fa": f"State: روند ضعیف صعودی — ADX={adx:.0f} | احتیاط"}
        elif roc_10 < -1:
            return {"signal": "SELL", "confidence": 50,
                    "reason_fa": f"State: روند ضعیف نزولی — ADX={adx:.0f} | احتیاط"}

    elif adx < 20:
        state = "RANGE"
        if rsi < 30:
            return {"signal": "BUY", "confidence": 55,
                    "reason_fa": f"State: رنج — RSI={rsi:.0f} اشباع فروش | خرید در حمایت"}
        elif rsi > 70:
            return {"signal": "SELL", "confidence": 55,
                    "reason_fa": f"State: رنج — RSI={rsi:.0f} اشباع خرید | فروش در مقاومت"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"State Machine — ADX={adx:.0f} RSI={rsi:.0f} ROC={roc_10:.1f}% | بدون سیگنال"}


ADP_STRATEGIES = [
    {"id": "ADP_01", "name": "Volatility Adjusted", "name_fa": "تطبیقی: نوسان‌تطبیقی", "func": adaptive_volatility},
    {"id": "ADP_02", "name": "Timeframe Adjusted", "name_fa": "تطبیقی: TF‌تطبیقی", "func": adaptive_timeframe},
    {"id": "ADP_03", "name": "Trend Range Switch", "name_fa": "تطبیقی: سوئیچ روند/رنج", "func": adaptive_trend_range},
    {"id": "ADP_04", "name": "Dynamic Threshold", "name_fa": "تطبیقی: آستانه پویا", "func": adaptive_dynamic_threshold},
    {"id": "ADP_05", "name": "Performance Weighted", "name_fa": "تطبیقی: وزن عملکردی", "func": adaptive_performance},
    {"id": "ADP_06", "name": "State Machine", "name_fa": "تطبیقی: ماشین حالت", "func": adaptive_state_machine},
]
