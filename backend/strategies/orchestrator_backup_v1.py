"""
Whilber-AI — Strategy Orchestrator v2
=======================================
Loads strategy packs dynamically.
Phase 1: RSI(12) + MACD(10) + Stoch(8) + BB(10) = 40 new
+ Original 32 strategies = 72 total
"""

import time
import sys
import traceback
from typing import Optional, List, Dict
from loguru import logger

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")

# ── Import original strategies ────────────────────────
try:
    from backend.strategies.original_strategies import ORIGINAL_STRATEGIES
    logger.info(f"✅ Loaded {len(ORIGINAL_STRATEGIES)} original strategies")
except Exception as e:
    logger.warning(f"⚠️ Original strategies not found: {e}")
    ORIGINAL_STRATEGIES = []

# ── Import Phase 1 strategy packs ────────────────────
try:
    from backend.strategies.rsi_strategies import RSI_STRATEGIES
    logger.info(f"✅ Loaded {len(RSI_STRATEGIES)} RSI strategies")
except Exception as e:
    logger.warning(f"⚠️ RSI strategies failed: {e}")
    RSI_STRATEGIES = []

try:
    from backend.strategies.macd_strategies import MACD_STRATEGIES
    logger.info(f"✅ Loaded {len(MACD_STRATEGIES)} MACD strategies")
except Exception as e:
    logger.warning(f"⚠️ MACD strategies failed: {e}")
    MACD_STRATEGIES = []

try:
    from backend.strategies.stoch_strategies import STOCH_STRATEGIES
    logger.info(f"✅ Loaded {len(STOCH_STRATEGIES)} Stochastic strategies")
except Exception as e:
    logger.warning(f"⚠️ Stoch strategies failed: {e}")
    STOCH_STRATEGIES = []

try:
    from backend.strategies.bb_strategies import BB_STRATEGIES
    logger.info(f"✅ Loaded {len(BB_STRATEGIES)} Bollinger strategies")
except Exception as e:
    logger.warning(f"⚠️ BB strategies failed: {e}")
    BB_STRATEGIES = []

# ── Future phase imports (will auto-load when available) ──
PHASE2_STRATEGIES = []
PHASE3_STRATEGIES = []
PHASE4_STRATEGIES = []
PHASE5_STRATEGIES = []

for mod_name, var_name, label in [
    ("backend.strategies.ma_strategies", "MA_STRATEGIES", "MA"),
    ("backend.strategies.ichimoku_strategies", "ICHIMOKU_STRATEGIES", "Ichimoku"),
    ("backend.strategies.supertrend_strategies", "SUPERTREND_STRATEGIES", "SuperTrend"),
    ("backend.strategies.adx_strategies", "ADX_STRATEGIES", "ADX"),
    ("backend.strategies.candle_strategies", "CANDLE_STRATEGIES", "Candle"),
    ("backend.strategies.divergence_strategies", "DIV_STRATEGIES", "Divergence"),
    ("backend.strategies.volume_strategies", "VOLUME_STRATEGIES", "Volume"),
    ("backend.strategies.fib_strategies", "FIB_STRATEGIES", "Fibonacci"),
    ("backend.strategies.smart_money_strategies", "SM_STRATEGIES", "SmartMoney"),
    ("backend.strategies.cci_strategies", "CCI_STRATEGIES", "CCI"),
    ("backend.strategies.williams_strategies", "WILLR_STRATEGIES", "WilliamsR"),
    ("backend.strategies.atr_strategies", "ATR_STRATEGIES", "ATR"),
    ("backend.strategies.momentum_strategies", "MOM_STRATEGIES", "Momentum"),
    ("backend.strategies.pivot_strategies", "PIVOT_STRATEGIES", "Pivots"),
    ("backend.strategies.mtf_strategies", "MTF_STRATEGIES", "MTF"),
    ("backend.strategies.price_action_strategies", "PA_STRATEGIES", "PriceAction"),
    ("backend.strategies.stats_strategies", "STATS_STRATEGIES", "Stats"),
]:
    try:
        mod = __import__(mod_name, fromlist=[var_name])
        strats = getattr(mod, var_name, [])
        if strats:
            PHASE2_STRATEGIES.extend(strats)
            logger.info(f"✅ Loaded {len(strats)} {label} strategies")
    except:
        pass  # Will be available in future phases


# ═══════════════════════════════════════════════════════
# ALL STRATEGIES REGISTRY
# ═══════════════════════════════════════════════════════

ALL_STRATEGIES = (
    ORIGINAL_STRATEGIES +
    RSI_STRATEGIES +
    MACD_STRATEGIES +
    STOCH_STRATEGIES +
    BB_STRATEGIES +
    PHASE2_STRATEGIES +
    PHASE3_STRATEGIES +
    PHASE4_STRATEGIES +
    PHASE5_STRATEGIES
)

logger.info(f"📊 Total strategies loaded: {len(ALL_STRATEGIES)}")


# ═══════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════

try:
    from backend.mt5.mt5_connector import MT5Connector
except ImportError:
    MT5Connector = None
    logger.warning("MT5Connector not found")

from backend.mt5 import data_fetcher as _df_module

try:
    from backend.mt5.symbol_map import get_farsi_name, get_symbol_info, validate_symbol
except ImportError:
    get_farsi_name = lambda s: s
    get_symbol_info = lambda s: {"name": s}
    validate_symbol = lambda s: s
    logger.warning("symbol_map imports failed - using defaults")

try:
    from backend.mt5.timeframes import validate_timeframe, get_mt5_timeframe
except ImportError:
    validate_timeframe = lambda t: t
    get_mt5_timeframe = lambda t: t
    logger.warning("timeframes imports failed - using defaults")

# Auto-detect function names from data_fetcher (different versions use different names)
_ohlcv_func = None
_price_func = None
for _name in ["fetch_ohlcv", "get_ohlcv", "get_candles", "fetch_candles", "get_historical_data", "fetch_historical"]:
    if hasattr(_df_module, _name):
        _ohlcv_func = getattr(_df_module, _name)
        break
for _name in ["fetch_current_price", "get_current_price", "get_price", "fetch_price", "get_tick"]:
    if hasattr(_df_module, _name):
        _price_func = getattr(_df_module, _name)
        break

if _ohlcv_func is None:
    _all_funcs = [x for x in dir(_df_module) if not x.startswith("_") and callable(getattr(_df_module, x, None))]
    logger.warning(f"Could not find OHLCV function in data_fetcher. Available: {_all_funcs}")
if _price_func is None:
    _all_funcs = [x for x in dir(_df_module) if not x.startswith("_") and callable(getattr(_df_module, x, None))]
    logger.warning(f"Could not find price function in data_fetcher. Available: {_all_funcs}")


def _fetch_data(symbol: str, timeframe: str, bars: int = 500):
    if MT5Connector is not None:
        connector = MT5Connector.get_instance()
        if not connector.ensure_connected():
            return None, "MT5 متصل نیست"
    if _ohlcv_func is None:
        return None, "OHLCV function not found in data_fetcher"
    df = _ohlcv_func(symbol, timeframe, bars)
    if df is None or df.empty:
        return None, f"داده‌ای برای {symbol}/{timeframe} یافت نشد"
    return df, None


# ═══════════════════════════════════════════════════════
# CONTEXT BUILDER (shared indicators)
# ═══════════════════════════════════════════════════════

def _build_context(df):
    """Pre-calculate shared indicators for all strategies."""
    close = df['close']
    high = df['high']
    low = df['low']
    ctx = {}

    try:
        # EMA
        ctx['ema_9'] = close.ewm(span=9).mean().iloc[-1]
        ctx['ema_21'] = close.ewm(span=21).mean().iloc[-1]
        ctx['ema_50'] = close.ewm(span=50).mean().iloc[-1]
        ctx['ema_200'] = close.ewm(span=200).mean().iloc[-1] if len(close) > 200 else None

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, min_periods=14).mean()
        rs = gain / loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))
        ctx['rsi_14'] = rsi.iloc[-1]

        # Stochastic
        low14 = low.rolling(14).min()
        high14 = high.rolling(14).max()
        ctx['stoch_k'] = ((close.iloc[-1] - low14.iloc[-1]) /
                          (high14.iloc[-1] - low14.iloc[-1] + 1e-10) * 100)

        # ATR
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        ctx['atr_14'] = atr.iloc[-1]
        ctx['atr_percent'] = (atr.iloc[-1] / close.iloc[-1]) * 100

        # Bollinger
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        ctx['bb_upper'] = (sma20 + 2 * std20).iloc[-1]
        ctx['bb_lower'] = (sma20 - 2 * std20).iloc[-1]
        ctx['bb_percent_b'] = ((close.iloc[-1] - ctx['bb_lower']) /
                                (ctx['bb_upper'] - ctx['bb_lower'] + 1e-10) * 100)

        # ADX
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        atr14 = tr.ewm(alpha=1/14).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / (atr14 + 1e-10))
        minus_di = 100 * (minus_dm.ewm(alpha=1/14).mean() / (atr14 + 1e-10))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        ctx['adx'] = dx.ewm(alpha=1/14).mean().iloc[-1]
        ctx['plus_di'] = plus_di.iloc[-1]
        ctx['minus_di'] = minus_di.iloc[-1]

        # Regime
        if ctx['adx'] > 25:
            ctx['regime'] = 'صعودی' if ctx['plus_di'] > ctx['minus_di'] else 'نزولی'
        else:
            ctx['regime'] = 'رنج'

        # MA Stack
        if ctx.get('ema_200'):
            if ctx['ema_9'] > ctx['ema_21'] > ctx['ema_50'] > ctx['ema_200']:
                ctx['ma_stack'] = 1
            elif ctx['ema_9'] < ctx['ema_21'] < ctx['ema_50'] < ctx['ema_200']:
                ctx['ma_stack'] = -1
            else:
                ctx['ma_stack'] = 0
        else:
            ctx['ma_stack'] = 0

        # SuperTrend
        hl2 = (high + low) / 2
        st_upper = hl2 - 3 * atr
        st_lower = hl2 + 3 * atr
        ctx['supertrend_dir'] = 1 if close.iloc[-1] > st_upper.iloc[-1] else -1

    except Exception as e:
        logger.debug(f"Context calc partial error: {e}")

    return ctx


import pandas as pd


# ═══════════════════════════════════════════════════════
# MAIN ANALYZER
# ═══════════════════════════════════════════════════════

def analyze_symbol(symbol: str, timeframe: str = "H1",
                   strategies: Optional[List[str]] = None) -> Dict:
    """Run all strategies on a symbol and return combined result."""
    t0 = time.time()

    symbol = symbol.upper()
    timeframe = timeframe.upper()

    if not validate_symbol(symbol):
        return {"success": False, "error": f"نماد {symbol} پشتیبانی نمی‌شود"}

    df, err = _fetch_data(symbol, timeframe, 500)
    if err:
        return {"success": False, "error": err}

    # Context (shared indicators)
    context = _build_context(df)

    # Price
    price = (_price_func(symbol) if _price_func else {}) or {}

    # Filter strategies if specified
    strats_to_run = ALL_STRATEGIES
    if strategies:
        strats_to_run = [s for s in ALL_STRATEGIES if s["id"] in strategies]

    # Run all strategies
    results = []
    for strat in strats_to_run:
        try:
            r = strat["func"](df, context)
            results.append({
                "strategy_id": strat["id"],
                "strategy_name": strat["name"],
                "strategy_name_fa": strat["name_fa"],
                "signal": r.get("signal", "NEUTRAL"),
                "signal_fa": "خرید" if r.get("signal") == "BUY" else "فروش" if r.get("signal") == "SELL" else "خنثی",
                "confidence": r.get("confidence", 0),
                "reason_fa": r.get("reason_fa", ""),
            })
        except Exception as e:
            logger.debug(f"Strategy {strat['id']} error: {e}")
            results.append({
                "strategy_id": strat["id"],
                "strategy_name": strat["name"],
                "strategy_name_fa": strat["name_fa"],
                "signal": "NEUTRAL",
                "signal_fa": "خنثی",
                "confidence": 0,
                "reason_fa": f"خطای محاسبه",
            })

    # Aggregate
    buy_count = sum(1 for r in results if r["signal"] == "BUY")
    sell_count = sum(1 for r in results if r["signal"] == "SELL")
    neutral_count = sum(1 for r in results if r["signal"] == "NEUTRAL")
    total = len(results)

    if buy_count > sell_count:
        signal = "BUY"
        signal_fa = "🟢 خرید"
        confidence = round((buy_count / total) * 100) if total > 0 else 0
        buy_confs = [r["confidence"] for r in results if r["signal"] == "BUY" and r["confidence"] > 0]
        avg_conf = sum(buy_confs) / len(buy_confs) if buy_confs else confidence
        confidence = round((confidence + avg_conf) / 2)
    elif sell_count > buy_count:
        signal = "SELL"
        signal_fa = "🔴 فروش"
        confidence = round((sell_count / total) * 100) if total > 0 else 0
        sell_confs = [r["confidence"] for r in results if r["signal"] == "SELL" and r["confidence"] > 0]
        avg_conf = sum(sell_confs) / len(sell_confs) if sell_confs else confidence
        confidence = round((confidence + avg_conf) / 2)
    else:
        signal = "NEUTRAL"
        signal_fa = "🟡 خنثی"
        confidence = round((neutral_count / total) * 100) if total > 0 else 50

    # Summary
    summary_fa = f"از {total} استراتژی: {buy_count} خرید، {sell_count} فروش، {neutral_count} خنثی"

    elapsed = time.time() - t0

    return {
        "success": True,
        "symbol": symbol,
        "symbol_fa": get_farsi_name(symbol),
        "timeframe": timeframe,
        "last_close": float(df['close'].iloc[-1]),
        "price": price,
        "overall": {
            "signal": signal,
            "signal_fa": signal_fa,
            "confidence": min(99, max(0, confidence)),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "neutral_count": neutral_count,
            "total_strategies": total,
            "summary_fa": summary_fa,
        },
        "context": context,
        "strategies": results,
        "performance": {
            "total_time": round(elapsed, 3),
            "bars_analyzed": len(df),
            "strategies_run": total,
        },
    }


def get_available_strategies() -> List[Dict]:
    return [{"id": s["id"], "name": s["name"], "name_fa": s["name_fa"]} for s in ALL_STRATEGIES]


def get_strategy_count() -> int:
    return len(ALL_STRATEGIES)
