"""
Whilber-AI — AI Combo Strategies
===================================
AIC_01: Top-5 Agreement
AIC_02: Weighted Vote
AIC_03: Category Consensus
AIC_04: Regime Adaptive
AIC_05: Confidence Cluster
AIC_06: Best-of-Breed
"""

import numpy as np


def _get_other_results(context):
    """Extract strategy results from context if available."""
    if not context:
        return []
    return context.get("strategy_results", [])


def _categorize(sid):
    """Get category from strategy ID prefix."""
    prefixes = {
        "RSI": "RSI", "BB": "BB", "MACD": "MACD", "STOCH": "Stoch",
        "MA": "MA", "ICH": "Ichimoku", "ST": "SuperTrend", "ADX": "ADX",
        "CDL": "Candle", "DIV": "Divergence", "VOL": "Volume", "FIB": "Fibonacci",
        "SM": "SmartMoney", "CCI": "CCI", "WR": "Williams", "ATR": "ATR",
        "MOM": "Momentum", "PVT": "Pivot", "MTF": "MTF", "PA": "PriceAction",
        "STAT": "Stats", "HARM": "Harmonic", "EW": "Elliott", "CP": "ChartPattern",
        "SRSI": "StochRSI", "ARN": "Aroon", "VTX": "Vortex", "ULT": "Ultimate",
        "KST": "KST", "CH": "Channel", "GAP": "Gap", "MS": "Structure",
        "WYC": "Wyckoff", "SNT": "Sentiment", "COR": "Correlation",
    }
    for prefix, cat in prefixes.items():
        if sid.startswith(prefix + "_"):
            return cat
    return "Other"


# -- AIC_01: Top-5 Agreement
def ai_top5_agreement(df, context=None):
    """Top-5 Agreement — ۵ استراتژی با بالاترین اطمینان هم‌جهت"""
    results = _get_other_results(context)
    if len(results) < 10:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "Top-5 — نتایج کافی نیست"}

    # Sort by confidence, take top 5 non-neutral
    active = [r for r in results if r.get("signal") != "NEUTRAL" and r.get("confidence", 0) > 40]
    active.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    top5 = active[:5]

    if len(top5) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "Top-5 — کمتر از ۳ سیگنال فعال"}

    buy_count = sum(1 for r in top5 if r["signal"] == "BUY")
    sell_count = sum(1 for r in top5 if r["signal"] == "SELL")
    avg_conf = np.mean([r["confidence"] for r in top5])

    if buy_count >= 4:
        names = ", ".join(r.get("strategy_id", "?")[:8] for r in top5 if r["signal"] == "BUY")
        return {"signal": "BUY", "confidence": min(int(avg_conf * 1.1), 92),
                "reason_fa": f"Top-5 خرید ({buy_count}/5) — {names} | اطمینان={avg_conf:.0f}%"}
    elif sell_count >= 4:
        names = ", ".join(r.get("strategy_id", "?")[:8] for r in top5 if r["signal"] == "SELL")
        return {"signal": "SELL", "confidence": min(int(avg_conf * 1.1), 92),
                "reason_fa": f"Top-5 فروش ({sell_count}/5) — {names} | اطمینان={avg_conf:.0f}%"}

    return {"signal": "NEUTRAL", "confidence": 30,
            "reason_fa": f"Top-5 — خرید={buy_count} فروش={sell_count} | بدون اجماع"}


# -- AIC_02: Weighted Vote
def ai_weighted_vote(df, context=None):
    """رای وزنی — وزن بیشتر به استراتژی‌های پراطمینان"""
    results = _get_other_results(context)
    if len(results) < 10:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "رای وزنی — نتایج کافی نیست"}

    buy_weight = 0
    sell_weight = 0
    total_weight = 0

    for r in results:
        conf = r.get("confidence", 0)
        if conf < 30:
            continue
        w = conf * conf / 100  # Quadratic weighting
        total_weight += w
        if r["signal"] == "BUY":
            buy_weight += w
        elif r["signal"] == "SELL":
            sell_weight += w

    if total_weight == 0:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "رای وزنی — وزن کل صفر"}

    buy_pct = buy_weight / total_weight * 100
    sell_pct = sell_weight / total_weight * 100

    if buy_pct > 65:
        return {"signal": "BUY", "confidence": min(int(buy_pct), 90),
                "reason_fa": f"رای وزنی خرید {buy_pct:.0f}% — وزن خرید={buy_weight:.0f} فروش={sell_weight:.0f}"}
    elif sell_pct > 65:
        return {"signal": "SELL", "confidence": min(int(sell_pct), 90),
                "reason_fa": f"رای وزنی فروش {sell_pct:.0f}% — وزن فروش={sell_weight:.0f} خرید={buy_weight:.0f}"}

    return {"signal": "NEUTRAL", "confidence": 30,
            "reason_fa": f"رای وزنی — خرید={buy_pct:.0f}% فروش={sell_pct:.0f}% | بدون اکثریت"}


# -- AIC_03: Category Consensus
def ai_category_consensus(df, context=None):
    """توافق بین گروه‌ها — اکثریت گروه‌ها هم‌جهت"""
    results = _get_other_results(context)
    if len(results) < 10:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "توافق گروهی — نتایج کافی نیست"}

    # Group by category
    cats = {}
    for r in results:
        sid = r.get("strategy_id", "")
        cat = _categorize(sid)
        if cat not in cats:
            cats[cat] = {"BUY": 0, "SELL": 0, "NEUTRAL": 0}
        sig = r.get("signal", "NEUTRAL")
        cats[cat][sig] = cats[cat].get(sig, 0) + 1

    # Each category votes
    cat_buy = 0
    cat_sell = 0
    cat_total = 0
    for cat, votes in cats.items():
        if votes["BUY"] + votes["SELL"] == 0:
            continue
        cat_total += 1
        if votes["BUY"] > votes["SELL"]:
            cat_buy += 1
        elif votes["SELL"] > votes["BUY"]:
            cat_sell += 1

    if cat_total < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "توافق — کمتر از ۳ گروه فعال"}

    buy_pct = cat_buy / cat_total * 100
    sell_pct = cat_sell / cat_total * 100

    if buy_pct >= 70:
        return {"signal": "BUY", "confidence": min(int(buy_pct), 88),
                "reason_fa": f"توافق گروهی خرید — {cat_buy}/{cat_total} گروه | {buy_pct:.0f}%"}
    elif sell_pct >= 70:
        return {"signal": "SELL", "confidence": min(int(sell_pct), 88),
                "reason_fa": f"توافق گروهی فروش — {cat_sell}/{cat_total} گروه | {sell_pct:.0f}%"}

    return {"signal": "NEUTRAL", "confidence": 25,
            "reason_fa": f"توافق — خرید={cat_buy} فروش={cat_sell} از {cat_total} گروه"}


# -- AIC_04: Regime Adaptive
def ai_regime_adaptive(df, context=None):
    """انتخاب استراتژی بر اساس رژیم بازار"""
    results = _get_other_results(context)
    if len(results) < 5:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "Regime — نتایج کافی نیست"}

    adx = context.get("adx", 25) if context else 25
    regime = context.get("regime", "unknown") if context else "unknown"

    # In trending: favor trend-following strategies
    trend_cats = {"MA", "ADX", "SuperTrend", "Ichimoku", "MACD", "Aroon", "Vortex"}
    # In ranging: favor mean-reversion strategies
    range_cats = {"RSI", "BB", "Stoch", "StochRSI", "CCI", "Ultimate", "Sentiment"}

    is_trending = adx > 25 or "trend" in str(regime).lower()

    target_cats = trend_cats if is_trending else range_cats
    filtered = [r for r in results if _categorize(r.get("strategy_id", "")) in target_cats and r.get("confidence", 0) > 40]

    if len(filtered) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"Regime — کمتر از ۳ استراتژی مرتبط با {'روند' if is_trending else 'رنج'}"}

    buy_c = sum(1 for r in filtered if r["signal"] == "BUY")
    sell_c = sum(1 for r in filtered if r["signal"] == "SELL")
    total = len(filtered)

    if buy_c > sell_c and buy_c / total > 0.6:
        avg_conf = np.mean([r["confidence"] for r in filtered if r["signal"] == "BUY"])
        return {"signal": "BUY", "confidence": min(int(avg_conf), 85),
                "reason_fa": f"Regime {'روند' if is_trending else 'رنج'} — {buy_c}/{total} خرید | ADX={adx:.0f}"}
    elif sell_c > buy_c and sell_c / total > 0.6:
        avg_conf = np.mean([r["confidence"] for r in filtered if r["signal"] == "SELL"])
        return {"signal": "SELL", "confidence": min(int(avg_conf), 85),
                "reason_fa": f"Regime {'روند' if is_trending else 'رنج'} — {sell_c}/{total} فروش | ADX={adx:.0f}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Regime — بدون اکثریت در {'روند' if is_trending else 'رنج'}"}


# -- AIC_05: Confidence Cluster
def ai_confidence_cluster(df, context=None):
    """خوشه‌بندی سیگنال‌های پراطمینان"""
    results = _get_other_results(context)
    if len(results) < 10:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "خوشه‌بندی — نتایج کافی نیست"}

    # Find high-confidence cluster (>65%)
    high_conf = [r for r in results if r.get("confidence", 0) >= 65]

    if len(high_conf) < 3:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"خوشه‌بندی — فقط {len(high_conf)} سیگنال بالای ۶۵%"}

    buy_hc = sum(1 for r in high_conf if r["signal"] == "BUY")
    sell_hc = sum(1 for r in high_conf if r["signal"] == "SELL")

    if buy_hc >= 3 and buy_hc > sell_hc * 2:
        avg = np.mean([r["confidence"] for r in high_conf if r["signal"] == "BUY"])
        return {"signal": "BUY", "confidence": min(int(avg * 1.05), 92),
                "reason_fa": f"خوشه خرید — {buy_hc} سیگنال با اطمینان بالا | میانگین={avg:.0f}%"}
    elif sell_hc >= 3 and sell_hc > buy_hc * 2:
        avg = np.mean([r["confidence"] for r in high_conf if r["signal"] == "SELL"])
        return {"signal": "SELL", "confidence": min(int(avg * 1.05), 92),
                "reason_fa": f"خوشه فروش — {sell_hc} سیگنال با اطمینان بالا | میانگین={avg:.0f}%"}

    return {"signal": "NEUTRAL", "confidence": 25,
            "reason_fa": f"خوشه‌بندی — خرید={buy_hc} فروش={sell_hc} از {len(high_conf)} بالای ۶۵%"}


# -- AIC_06: Best-of-Breed
def ai_best_of_breed(df, context=None):
    """بهترین از هر گروه — یک نماینده از هر دسته"""
    results = _get_other_results(context)
    if len(results) < 10:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "Best-of-Breed — نتایج کافی نیست"}

    # Get best (highest confidence) from each category
    best_per_cat = {}
    for r in results:
        cat = _categorize(r.get("strategy_id", ""))
        conf = r.get("confidence", 0)
        if cat not in best_per_cat or conf > best_per_cat[cat].get("confidence", 0):
            best_per_cat[cat] = r

    representatives = list(best_per_cat.values())
    if len(representatives) < 5:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"Best-of-Breed — فقط {len(representatives)} گروه"}

    buy_reps = [r for r in representatives if r["signal"] == "BUY" and r["confidence"] > 40]
    sell_reps = [r for r in representatives if r["signal"] == "SELL" and r["confidence"] > 40]
    total = len([r for r in representatives if r.get("confidence", 0) > 40])

    if total == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Best-of-Breed — بدون سیگنال فعال"}

    if len(buy_reps) > len(sell_reps) and len(buy_reps) / total > 0.6:
        avg = np.mean([r["confidence"] for r in buy_reps])
        return {"signal": "BUY", "confidence": min(int(avg), 88),
                "reason_fa": f"Best-of-Breed خرید — {len(buy_reps)}/{total} نماینده | اطمینان={avg:.0f}%"}
    elif len(sell_reps) > len(buy_reps) and len(sell_reps) / total > 0.6:
        avg = np.mean([r["confidence"] for r in sell_reps])
        return {"signal": "SELL", "confidence": min(int(avg), 88),
                "reason_fa": f"Best-of-Breed فروش — {len(sell_reps)}/{total} نماینده | اطمینان={avg:.0f}%"}

    return {"signal": "NEUTRAL", "confidence": 20,
            "reason_fa": f"Best-of-Breed — خرید={len(buy_reps)} فروش={len(sell_reps)} از {total}"}


AIC_STRATEGIES = [
    {"id": "AIC_01", "name": "Top5 Agreement", "name_fa": "هوش: توافق Top-5", "func": ai_top5_agreement},
    {"id": "AIC_02", "name": "Weighted Vote", "name_fa": "هوش: رای وزنی", "func": ai_weighted_vote},
    {"id": "AIC_03", "name": "Category Consensus", "name_fa": "هوش: توافق گروهی", "func": ai_category_consensus},
    {"id": "AIC_04", "name": "Regime Adaptive", "name_fa": "هوش: رژیم‌تطبیقی", "func": ai_regime_adaptive},
    {"id": "AIC_05", "name": "Confidence Cluster", "name_fa": "هوش: خوشه اطمینان", "func": ai_confidence_cluster},
    {"id": "AIC_06", "name": "Best of Breed", "name_fa": "هوش: بهترین هر گروه", "func": ai_best_of_breed},
]
