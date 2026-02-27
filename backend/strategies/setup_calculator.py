"""
Whilber-AI — Setup Calculator
================================
Calculates actionable trade setups:
  - Per-strategy: entry, SL, TP based on each strategy signal
  - Master setup: aggregated from all strategies with precise levels

Uses: ATR for stop distance, S/R context, risk:reward ratios
"""

import numpy as np


def _round_price(price, digits=5):
    """Round price to appropriate decimal places."""
    if price > 1000:
        return round(price, 2)
    elif price > 10:
        return round(price, 3)
    elif price > 1:
        return round(price, 4)
    return round(price, digits)


def _detect_digits(price):
    """Detect number of decimal digits for a price."""
    if price > 1000:
        return 2
    elif price > 10:
        return 3
    elif price > 1:
        return 4
    return 5


def calculate_strategy_setup(strategy, price, atr, context=None):
    """
    Calculate entry/SL/TP for a single strategy.

    Args:
        strategy: dict with signal, confidence, strategy_id
        price: current close price
        atr: ATR value
        context: market context dict (optional)

    Returns:
        dict with setup info or None if no setup
    """
    sig = strategy.get("signal", "NEUTRAL")
    conf = strategy.get("confidence", 0)
    sid = strategy.get("strategy_id", "")

    if sig == "NEUTRAL" or conf < 25 or atr is None or atr <= 0:
        return {
            "has_setup": False,
            "reason_fa": "ستاپ معاملاتی فعالی توصیه نمی‌شود",
        }

    digits = _detect_digits(price)

    # ATR multipliers based on confidence
    if conf >= 80:
        sl_mult = 1.2
        tp1_mult = 1.5
        tp2_mult = 2.5
    elif conf >= 55:
        sl_mult = 1.5
        tp1_mult = 1.5
        tp2_mult = 2.2
    elif conf >= 35:
        sl_mult = 1.8
        tp1_mult = 1.2
        tp2_mult = 2.0
    else:
        sl_mult = 2.5
        tp1_mult = 1.0
        tp2_mult = 1.5

    sl_dist = atr * sl_mult
    tp1_dist = atr * tp1_mult
    tp2_dist = atr * tp2_mult

    if sig == "BUY":
        entry = _round_price(price, digits)
        sl = _round_price(price - sl_dist, digits)
        tp1 = _round_price(price + tp1_dist, digits)
        tp2 = _round_price(price + tp2_dist, digits)
        direction = "خرید"
    else:  # SELL
        entry = _round_price(price, digits)
        sl = _round_price(price + sl_dist, digits)
        tp1 = _round_price(price - tp1_dist, digits)
        tp2 = _round_price(price - tp2_dist, digits)
        direction = "فروش"

    rr1 = round(tp1_dist / sl_dist, 2) if sl_dist > 0 else 0
    rr2 = round(tp2_dist / sl_dist, 2) if sl_dist > 0 else 0
    risk_pips = _round_price(sl_dist, digits)

    return {
        "has_setup": True,
        "direction": sig,
        "direction_fa": direction,
        "entry": entry,
        "stop_loss": sl,
        "tp1": tp1,
        "tp2": tp2,
        "risk_pips": risk_pips,
        "rr1": rr1,
        "rr2": rr2,
        "confidence": conf,
        "reason_fa": f"ورود {direction}: {entry} | SL: {sl} | TP1: {tp1} (R:R {rr1}) | TP2: {tp2} (R:R {rr2})",
    }


def calculate_master_setup(analysis_result):
    """
    Calculate the MASTER trade setup from all strategy results.

    Aggregates all strategy signals, uses ATR + context to find
    precise entry, stop loss, and two take-profit levels.

    Args:
        analysis_result: full analysis dict from orchestrator

    Returns:
        dict with master setup
    """
    overall = analysis_result.get("overall", {})
    strategies = analysis_result.get("strategies", [])
    context = analysis_result.get("context", {})
    price = analysis_result.get("last_close")
    symbol = analysis_result.get("symbol", "")
    tf = analysis_result.get("timeframe", "H1")

    if not price or not overall:
        return _no_setup("داده کافی برای محاسبه ستاپ نیست")

    sig = overall.get("signal", "NEUTRAL")
    conf = overall.get("confidence", 0)
    buy_count = overall.get("buy_count", 0)
    sell_count = overall.get("sell_count", 0)
    total = buy_count + sell_count + overall.get("neutral_count", 0)

    # Must have clear signal + minimum confidence
    if sig == "NEUTRAL" or conf < 20:
        return _no_setup("سیگنال کلی خنثی یا اطمینان پایین — ستاپ فعالی توصیه نمی‌شود")

    # Calculate agreement ratio
    if sig == "BUY":
        agree_ratio = buy_count / total if total > 0 else 0
    else:
        agree_ratio = sell_count / total if total > 0 else 0

    if agree_ratio < 0.15:
        return _no_setup("توافق استراتژی‌ها کمتر از ۱۵% — ستاپ معتبر نیست")

    # ATR from context
    atr = context.get("atr_value")
    atr_pct = context.get("atr_percent")

    # Fallback ATR calculation
    if atr is None or atr <= 0:
        if atr_pct and atr_pct > 0:
            atr = price * atr_pct / 100
        else:
            # Rough estimate: 0.5% of price
            atr = price * 0.005

    digits = _detect_digits(price)

    # ── STOP LOSS CALCULATION ─────────────────────
    # Base SL on ATR, adjust for confidence and agreement
    if conf >= 80 and agree_ratio >= 0.6:
        sl_mult = 1.0   # Tight stop, high confidence
        quality = "عالی"
        quality_stars = "⭐⭐⭐⭐⭐"
    elif conf >= 55 and agree_ratio >= 0.35:
        sl_mult = 1.3
        quality = "خوب"
        quality_stars = "⭐⭐⭐⭐"
    elif conf >= 35 and agree_ratio >= 0.25:
        sl_mult = 1.6
        quality = "متوسط"
        quality_stars = "⭐⭐⭐"
    elif conf >= 20 and agree_ratio >= 0.15:
        sl_mult = 2.5
        quality = "ضعیف"
        quality_stars = "⭐⭐"
    else:
        sl_mult = 2.0
        quality = "ضعیف"
        quality_stars = "⭐⭐"

    sl_dist = atr * sl_mult

    # ── TAKE PROFIT CALCULATION ───────────────────
    # TP1: Conservative (1:1 to 1:1.5 R:R)
    # TP2: Extended (1:2 to 1:3 R:R)

    # Check for pivot/fib levels in context for smarter TPs
    ema9 = context.get("ema_9")
    ema50 = context.get("ema_50")
    bb_upper = context.get("bb_upper")
    bb_lower = context.get("bb_lower")
    supertrend = context.get("supertrend_value")

    # Base TP multipliers
    tp1_mult = 1.3
    tp2_mult = 2.5

    # Adjust based on regime
    regime = context.get("regime", "")
    if regime and "trend" in str(regime).lower():
        tp2_mult = 3.0  # Wider TP in trending market
    elif regime and "rang" in str(regime).lower():
        tp2_mult = 1.8  # Tighter TP in ranging market
        tp1_mult = 1.0

    tp1_dist = atr * tp1_mult
    tp2_dist = atr * tp2_mult

    # ── CALCULATE LEVELS ──────────────────────────
    if sig == "BUY":
        entry = _round_price(price, digits)
        sl = _round_price(price - sl_dist, digits)
        tp1 = _round_price(price + tp1_dist, digits)
        tp2 = _round_price(price + tp2_dist, digits)

        # Smart TP: use BB upper if available and reasonable
        if bb_upper and bb_upper > price and bb_upper < tp2:
            tp1 = _round_price(bb_upper, digits)

        # Smart SL: use EMA50 if below price and closer than ATR SL
        if ema50 and ema50 < price and (price - ema50) < sl_dist * 1.5:
            smart_sl = _round_price(ema50 - atr * 0.2, digits)
            if smart_sl < sl:
                sl = smart_sl

        direction_fa = "🟢 خرید (LONG)"
    else:
        entry = _round_price(price, digits)
        sl = _round_price(price + sl_dist, digits)
        tp1 = _round_price(price - tp1_dist, digits)
        tp2 = _round_price(price - tp2_dist, digits)

        # Smart TP: use BB lower if available
        if bb_lower and bb_lower < price and bb_lower > tp2:
            tp1 = _round_price(bb_lower, digits)

        # Smart SL: use EMA50 if above price
        if ema50 and ema50 > price and (ema50 - price) < sl_dist * 1.5:
            smart_sl = _round_price(ema50 + atr * 0.2, digits)
            if smart_sl > sl:
                sl = smart_sl

        direction_fa = "🔴 فروش (SHORT)"

    # ── RISK:REWARD ───────────────────────────────
    actual_sl_dist = abs(entry - sl)
    actual_tp1_dist = abs(tp1 - entry)
    actual_tp2_dist = abs(tp2 - entry)
    rr1 = round(actual_tp1_dist / actual_sl_dist, 2) if actual_sl_dist > 0 else 0
    rr2 = round(actual_tp2_dist / actual_sl_dist, 2) if actual_sl_dist > 0 else 0

    # ── POSITION SIZE HINT ────────────────────────
    risk_pct = 1.0  # 1% risk default
    lot_hint_fa = f"ریسک پیشنهادی: {risk_pct}% سرمایه"

    # ── TIMEFRAME GUIDANCE ────────────────────────
    tf_guide = {
        "M1": "اسکالپ — نگه‌داری چند دقیقه",
        "M5": "اسکالپ — نگه‌داری ۵-۳۰ دقیقه",
        "M15": "اینتری‌دی — نگه‌داری ۱۵ دقیقه تا چند ساعت",
        "M30": "اینتری‌دی — نگه‌داری ۳۰ دقیقه تا نیم روز",
        "H1": "اینتری‌دی/سوئینگ — نگه‌داری چند ساعت",
        "H4": "سوئینگ — نگه‌داری ۱-۳ روز",
        "D1": "پوزیشن — نگه‌داری چند روز تا چند هفته",
    }.get(tf, "")

    # ── BUILD SUMMARY ─────────────────────────────
    summary_parts = []
    summary_parts.append(f"جهت: {direction_fa}")
    summary_parts.append(f"توافق: {int(agree_ratio*100)}% از {total} استراتژی")
    summary_parts.append(f"اطمینان: {conf}%")
    summary_parts.append(f"کیفیت: {quality}")

    return {
        "has_setup": True,
        "symbol": symbol,
        "timeframe": tf,
        "direction": sig,
        "direction_fa": direction_fa,
        "entry": entry,
        "stop_loss": sl,
        "tp1": tp1,
        "tp2": tp2,
        "rr1": rr1,
        "rr2": rr2,
        "risk_distance": _round_price(actual_sl_dist, digits),
        "confidence": conf,
        "agreement_pct": int(agree_ratio * 100),
        "quality": quality,
        "quality_stars": quality_stars,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "total_strategies": total,
        "lot_hint_fa": lot_hint_fa,
        "tf_guide_fa": tf_guide,
        "regime": regime,
        "atr": _round_price(atr, digits),
        "summary_fa": " | ".join(summary_parts),
    }


def _no_setup(reason):
    return {
        "has_setup": False,
        "direction": "NEUTRAL",
        "direction_fa": "بدون سیگنال",
        "reason_fa": reason,
        "entry": None,
        "stop_loss": None,
        "tp1": None,
        "tp2": None,
        "confidence": 0,
        "quality": "—",
        "quality_stars": "",
    }


def enrich_strategies_with_setups(strategies, price, atr, context=None):
    """
    Add setup info to each strategy result.

    Args:
        strategies: list of strategy dicts
        price: current close
        atr: ATR value
        context: market context

    Returns:
        list of strategies with 'setup' key added
    """
    for s in strategies:
        s["setup"] = calculate_strategy_setup(s, price, atr, context)
    return strategies
