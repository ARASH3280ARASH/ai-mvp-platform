"""
Whilber-AI — Strategy Orchestrator v2
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

# Phase 8: Channel + Gap + Market Structure
try:
    from backend.strategies.channel_strategies import CH_STRATEGIES
    PHASE8_CH = CH_STRATEGIES
except ImportError:
    PHASE8_CH = []

try:
    from backend.strategies.gap_structure_strategies import GAP_STRATEGIES, MS_STRATEGIES
    PHASE8_GAP = GAP_STRATEGIES
    PHASE8_MS = MS_STRATEGIES
except ImportError:
    PHASE8_GAP = []
    PHASE8_MS = []

# Phase 9: Wyckoff + Sentiment + Correlation
try:
    from backend.strategies.wyckoff_strategies import WYC_STRATEGIES
    PHASE9_WYC = WYC_STRATEGIES
except ImportError:
    PHASE9_WYC = []

try:
    from backend.strategies.sentiment_correlation_strategies import SNT_STRATEGIES, COR_STRATEGIES
    PHASE9_SNT = SNT_STRATEGIES
    PHASE9_COR = COR_STRATEGIES
except ImportError:
    PHASE9_SNT = []
    PHASE9_COR = []

# Phase 10: AI Combo + Adaptive
try:
    from backend.strategies.ai_combo_strategies import AIC_STRATEGIES
    PHASE10_AIC = AIC_STRATEGIES
except ImportError:
    PHASE10_AIC = []

try:
    from backend.strategies.adaptive_strategies import ADP_STRATEGIES
    PHASE10_ADP = ADP_STRATEGIES
except ImportError:
    PHASE10_ADP = []




ALL_STRATEGIES = (
    ORIGINAL_STRATEGIES +
    RSI_STRATEGIES +
    MACD_STRATEGIES +
    STOCH_STRATEGIES +
    BB_STRATEGIES +
    PHASE2_STRATEGIES +
    PHASE3_STRATEGIES +
    PHASE4_STRATEGIES +
    PHASE5_STRATEGIES +
    PHASE10_ADP
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

# ── Phase 6: Harmonic + Elliott + Chart Patterns ────
try:
    from backend.strategies.harmonic_strategies import HARM_STRATEGIES
    PHASE6_HARM = HARM_STRATEGIES
except ImportError:
    PHASE6_HARM = []

try:
    from backend.strategies.elliott_strategies import EW_STRATEGIES
    PHASE6_EW = EW_STRATEGIES
except ImportError:
    PHASE6_EW = []

try:
    from backend.strategies.chart_pattern_strategies import CP_STRATEGIES
    PHASE6_CP = CP_STRATEGIES
except ImportError:
    PHASE6_CP = []
# ── End Phase 6
# ── Phase 7: Advanced Oscillators ───────────────────
try:
    from backend.strategies.stochrsi_strategies import SRSI_STRATEGIES
    PHASE7_SRSI = SRSI_STRATEGIES
except ImportError:
    PHASE7_SRSI = []

try:
    from backend.strategies.advanced_oscillators import ARN_STRATEGIES, VTX_STRATEGIES, ULT_STRATEGIES, KST_STRATEGIES
    PHASE7_ARN = ARN_STRATEGIES
    PHASE7_VTX = VTX_STRATEGIES
    PHASE7_ULT = ULT_STRATEGIES
    PHASE7_KST = KST_STRATEGIES
except ImportError:
    PHASE7_ARN = []
    PHASE7_VTX = []
    PHASE7_ULT = []
    PHASE7_KST = []
# ── End Phase 7 ─────────────────────────────────────


# Auto-detect function names from data_fetcher (different versions use different names)
_ohlcv_func = None
_price_func = None
for _name in ["fetch_ohlcv", "fetch_bars", "get_ohlcv", "get_candles", "fetch_candles", "get_historical_data", "fetch_historical"]:
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
# All supported symbols (Phase 1 expanded)
SUPPORTED_SYMBOLS = [
    "AUDCAD",     "AUDCHF",     "AUDJPY",     "AUDNZD",     "AUDUSD",     "BTCUSD",
    "CADCHF",     "CADJPY",     "CHFJPY",     "EURAUD",     "EURCAD",     "EURCHF",
    "EURGBP",     "EURJPY",     "EURNZD",     "EURUSD",     "GBPAUD",     "GBPCAD",
    "GBPCHF",     "GBPJPY",     "GBPNZD",     "GBPUSD",     "NAS100",     "NZDCAD",
    "NZDCHF",     "NZDJPY",     "NZDUSD",     "US30",     "USDCAD",     "USDCHF",
    "USDJPY",     "XAGUSD",     "XAUUSD", 
]




# ═══════════════════════════════════════════════════════
# MAIN ANALYZER
# ═══════════════════════════════════════════════════════
# ── Pack 1: Channel & Band Systems (Phase 3) ──
try:
    from backend.strategies.donchian_strategies import DON_STRATEGIES
    from backend.strategies.keltner_strategies import KC_STRATEGIES
    from backend.strategies.envelope_strategies import ENV_STRATEGIES
    from backend.strategies.psar_strategies import PSAR_STRATEGIES
    from backend.strategies.regression_strategies import REG_STRATEGIES
    PACK1_LOADED = True
except ImportError as e:
    print(f"[ORCH] Pack 1 import error: {e}")
    DON_STRATEGIES = KC_STRATEGIES = ENV_STRATEGIES = PSAR_STRATEGIES = REG_STRATEGIES = []
    PACK1_LOADED = False

# ── Pack 2: Momentum & Oscillator Advanced (Phase 4) ──
try:
    from backend.strategies.trix_strategies import TRIX_STRATEGIES
    from backend.strategies.roc_strategies import ROC_STRATEGIES
    from backend.strategies.cmo_strategies import CMO_STRATEGIES
    from backend.strategies.rvi_strategies import RVI_STRATEGIES
    from backend.strategies.ppo_strategies import PPO_STRATEGIES
    PACK2_LOADED = True
except ImportError as e:
    print(f"[ORCH] Pack 2 import error: {e}")
    TRIX_STRATEGIES = ROC_STRATEGIES = CMO_STRATEGIES = RVI_STRATEGIES = PPO_STRATEGIES = []
    PACK2_LOADED = False

# ── Pack 3: Volume & Flow Analysis (Phase 5) ──
try:
    from backend.strategies.obv_strategies import OBV_STRATEGIES
    from backend.strategies.mfi_strategies import MFI_STRATEGIES
    from backend.strategies.vwap_strategies import VWAP_STRATEGIES
    from backend.strategies.ad_strategies import AD_STRATEGIES
    from backend.strategies.fi_strategies import FI_STRATEGIES
    PACK3_LOADED = True
except ImportError as e:
    print(f"[ORCH] Pack 3 import error: {e}")
    OBV_STRATEGIES = MFI_STRATEGIES = VWAP_STRATEGIES = AD_STRATEGIES = FI_STRATEGIES = []
    PACK3_LOADED = False

# ── Pack 4: Trend Systems (Phase 6) ──
try:
    from backend.strategies.adx_adv_strategies import ADX_ADV_STRATEGIES
    from backend.strategies.supertrend_strategies import STREND_STRATEGIES
    from backend.strategies.aroon_strategies import AROON_STRATEGIES
    from backend.strategies.dpo_strategies import DPO_STRATEGIES
    from backend.strategies.vortex_strategies import VORTEX_STRATEGIES
    PACK4_LOADED = True
except ImportError as e:
    print(f"[ORCH] Pack 4 import error: {e}")
    ADX_ADV_STRATEGIES = STREND_STRATEGIES = AROON_STRATEGIES = DPO_STRATEGIES = VORTEX_STRATEGIES = []
    PACK4_LOADED = False

# ── Pack 5: Statistical & Transform (Phase 7) ──
try:
    from backend.strategies.elder_strategies import ELDER_STRATEGIES
    from backend.strategies.fisher_strategies import FISHER_STRATEGIES
    from backend.strategies.heikin_strategies import HEIKIN_STRATEGIES
    from backend.strategies.chop_strategies import CHOP_STRATEGIES
    from backend.strategies.mass_strategies import MASS_STRATEGIES
    PACK5_LOADED = True
except ImportError as e:
    print(f"[ORCH] Pack 5 import error: {e}")
    ELDER_STRATEGIES = FISHER_STRATEGIES = HEIKIN_STRATEGIES = CHOP_STRATEGIES = MASS_STRATEGIES = []
    PACK5_LOADED = False

# ── Pack 6: Pattern & Structure (Phase 8) ──
try:
    from backend.strategies.pivot_adv_strategies import PIVOT_ADV_STRATEGIES
    from backend.strategies.gaps_strategies import GAPS_STRATEGIES
    from backend.strategies.range_strategies import RANGE_STRATEGIES
    from backend.strategies.swing_strategies import SWING_STRATEGIES
    from backend.strategies.harmonic_strategies import HARMONIC_STRATEGIES
    PACK6_LOADED = True
except ImportError as e:
    print(f"[ORCH] Pack 6 import error: {e}")
    PIVOT_ADV_STRATEGIES = GAPS_STRATEGIES = RANGE_STRATEGIES = SWING_STRATEGIES = HARMONIC_STRATEGIES = []
    PACK6_LOADED = False

# ── Pack 7: Multi-Indicator Combos (Phase 9) ──
try:
    from backend.strategies.combo_strategies import COMBO_STRATEGIES
    PACK7_LOADED = True
except ImportError as e:
    print(f"[ORCH] Pack 7 import error: {e}")
    COMBO_STRATEGIES = []
    PACK7_LOADED = False

# ── Pack 8: Advanced Indicators (Phase 10) ──
try:
    from backend.strategies.tsi_strategies import TSI_STRATEGIES
    from backend.strategies.squeeze_strategies import SQZ_STRATEGIES
    from backend.strategies.alligator_strategies import ALLI_STRATEGIES
    from backend.strategies.kama_strategies import KAMA_STRATEGIES
    from backend.strategies.zlema_strategies import ZLEMA_STRATEGIES
    PACK8_LOADED = True
except ImportError as e:
    print(f"[ORCH] Pack 8 import error: {e}")
    TSI_STRATEGIES = SQZ_STRATEGIES = ALLI_STRATEGIES = KAMA_STRATEGIES = ZLEMA_STRATEGIES = []
    PACK8_LOADED = False


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


    # ── Pack 1: Channel & Band (25 strategies) ──
    if PACK1_LOADED:
        for pack_strats, cat_id, cat_fa in [
            (DON_STRATEGIES, "DON", "کانال دونچیان"),
            (KC_STRATEGIES, "KC", "کانال کلتنر"),
            (ENV_STRATEGIES, "ENV", "پوشش میانگین"),
            (PSAR_STRATEGIES, "PSAR", "پارابولیک SAR"),
            (REG_STRATEGIES, "REG", "کانال رگرسیون"),
        ]:
            for strat in pack_strats:
                try:
                    r = strat["func"](df, context, symbol, timeframe)
                    r["strategy_id"] = strat["id"]
                    r["strategy_name"] = strat["name"]
                    r["strategy_name_fa"] = strat["name_fa"]
                    r["category"] = cat_id
                    r["category_fa"] = cat_fa
                    r["symbol"] = symbol
                    r["timeframe"] = timeframe
                    results.append(r)
                except Exception as e:
                    results.append({
                        "strategy_id": strat["id"], "strategy_name": strat["name"],
                        "strategy_name_fa": strat["name_fa"], "category": cat_id,
                        "category_fa": cat_fa, "symbol": symbol, "timeframe": timeframe,
                        "signal": "NEUTRAL", "confidence": 0,
                        "reason_fa": f"خطا: {str(e)[:50]}",
                        "setup": {"has_setup": False},
                    })


    # ── Pack 2: Momentum & Oscillator (25 strategies) ──
    if PACK2_LOADED:
        for pack2_strats, cat_id, cat_fa in [
            (TRIX_STRATEGIES, "TRIX", "تریکس"),
            (ROC_STRATEGIES, "ROC", "نرخ تغییر"),
            (CMO_STRATEGIES, "CMO", "مومنتوم چاند"),
            (RVI_STRATEGIES, "RVI", "شاخص نیروی نسبی"),
            (PPO_STRATEGIES, "PPO", "اسیلاتور درصدی قیمت"),
        ]:
            for strat in pack2_strats:
                try:
                    r = strat["func"](df, context, symbol, timeframe)
                    r["strategy_id"] = strat["id"]
                    r["strategy_name"] = strat["name"]
                    r["strategy_name_fa"] = strat["name_fa"]
                    r["category"] = cat_id
                    r["category_fa"] = cat_fa
                    r["symbol"] = symbol
                    r["timeframe"] = timeframe
                    results.append(r)
                except Exception as e:
                    results.append({
                        "strategy_id": strat["id"], "strategy_name": strat["name"],
                        "strategy_name_fa": strat["name_fa"], "category": cat_id,
                        "category_fa": cat_fa, "symbol": symbol, "timeframe": timeframe,
                        "signal": "NEUTRAL", "confidence": 0,
                        "reason_fa": f"خطا: {str(e)[:50]}",
                        "setup": {"has_setup": False},
                    })


    # ── Pack 3: Volume & Flow (25 strategies) ──
    if PACK3_LOADED:
        for pack3_strats, cat_id, cat_fa in [
            (OBV_STRATEGIES, "OBV", "حجم تعادلی"),
            (MFI_STRATEGIES, "MFI", "شاخص جریان پول"),
            (VWAP_STRATEGIES, "VWAP", "میانگین وزنی حجم"),
            (AD_STRATEGIES, "AD", "تجمع/توزیع"),
            (FI_STRATEGIES, "FI", "شاخص قدرت"),
        ]:
            for strat in pack3_strats:
                try:
                    r = strat["func"](df, context, symbol, timeframe)
                    r["strategy_id"] = strat["id"]
                    r["strategy_name"] = strat["name"]
                    r["strategy_name_fa"] = strat["name_fa"]
                    r["category"] = cat_id
                    r["category_fa"] = cat_fa
                    r["symbol"] = symbol
                    r["timeframe"] = timeframe
                    results.append(r)
                except Exception as e:
                    results.append({
                        "strategy_id": strat["id"], "strategy_name": strat["name"],
                        "strategy_name_fa": strat["name_fa"], "category": cat_id,
                        "category_fa": cat_fa, "symbol": symbol, "timeframe": timeframe,
                        "signal": "NEUTRAL", "confidence": 0,
                        "reason_fa": f"خطا: {str(e)[:50]}",
                        "setup": {"has_setup": False},
                    })


    # ── Pack 4: Trend Systems (25 strategies) ──
    if PACK4_LOADED:
        for pack4_strats, cat_id, cat_fa in [
            (ADX_ADV_STRATEGIES, "ADX_ADV", "ADX پیشرفته"),
            (STREND_STRATEGIES, "STREND", "سوپرترند"),
            (AROON_STRATEGIES, "AROON", "آرون"),
            (DPO_STRATEGIES, "DPO", "DPO"),
            (VORTEX_STRATEGIES, "VORTEX", "ورتکس"),
        ]:
            for strat in pack4_strats:
                try:
                    r = strat["func"](df, context, symbol, timeframe)
                    r["strategy_id"] = strat["id"]
                    r["strategy_name"] = strat["name"]
                    r["strategy_name_fa"] = strat["name_fa"]
                    r["category"] = cat_id
                    r["category_fa"] = cat_fa
                    r["symbol"] = symbol
                    r["timeframe"] = timeframe
                    results.append(r)
                except Exception as e:
                    results.append({
                        "strategy_id": strat["id"], "strategy_name": strat["name"],
                        "strategy_name_fa": strat["name_fa"], "category": cat_id,
                        "category_fa": cat_fa, "symbol": symbol, "timeframe": timeframe,
                        "signal": "NEUTRAL", "confidence": 0,
                        "reason_fa": f"خطا: {str(e)[:50]}",
                        "setup": {"has_setup": False},
                    })


    # ── Pack 5: Statistical & Transform (25 strategies) ──
    if PACK5_LOADED:
        for pack5_strats, cat_id, cat_fa in [
            (ELDER_STRATEGIES, "ELDER", "Elder Ray"),
            (FISHER_STRATEGIES, "FISHER", "Fisher Transform"),
            (HEIKIN_STRATEGIES, "HEIKIN", "هیکن آشی"),
            (CHOP_STRATEGIES, "CHOP", "شاخص Choppiness"),
            (MASS_STRATEGIES, "MASS", "شاخص Mass"),
        ]:
            for strat in pack5_strats:
                try:
                    r = strat["func"](df, context, symbol, timeframe)
                    r["strategy_id"] = strat["id"]
                    r["strategy_name"] = strat["name"]
                    r["strategy_name_fa"] = strat["name_fa"]
                    r["category"] = cat_id
                    r["category_fa"] = cat_fa
                    r["symbol"] = symbol
                    r["timeframe"] = timeframe
                    results.append(r)
                except Exception as e:
                    results.append({
                        "strategy_id": strat["id"], "strategy_name": strat["name"],
                        "strategy_name_fa": strat["name_fa"], "category": cat_id,
                        "category_fa": cat_fa, "symbol": symbol, "timeframe": timeframe,
                        "signal": "NEUTRAL", "confidence": 0,
                        "reason_fa": f"خطا: {str(e)[:50]}",
                        "setup": {"has_setup": False},
                    })


    # ── Pack 6: Pattern & Structure (25 strategies) ──
    if PACK6_LOADED:
        for pack6_strats, cat_id, cat_fa in [
            (PIVOT_ADV_STRATEGIES, "PIVOT_ADV", "پیوت پیشرفته"),
            (GAPS_STRATEGIES, "GAPS", "تحلیل گپ"),
            (RANGE_STRATEGIES, "RANGE", "تشخیص رنج"),
            (SWING_STRATEGIES, "SWING", "سوئینگ"),
            (HARMONIC_STRATEGIES, "HARMONIC", "الگوی هارمونیک"),
        ]:
            for strat in pack6_strats:
                try:
                    r = strat["func"](df, context, symbol, timeframe)
                    r["strategy_id"] = strat["id"]
                    r["strategy_name"] = strat["name"]
                    r["strategy_name_fa"] = strat["name_fa"]
                    r["category"] = cat_id
                    r["category_fa"] = cat_fa
                    r["symbol"] = symbol
                    r["timeframe"] = timeframe
                    results.append(r)
                except Exception as e:
                    results.append({
                        "strategy_id": strat["id"], "strategy_name": strat["name"],
                        "strategy_name_fa": strat["name_fa"], "category": cat_id,
                        "category_fa": cat_fa, "symbol": symbol, "timeframe": timeframe,
                        "signal": "NEUTRAL", "confidence": 0,
                        "reason_fa": f"خطا: {str(e)[:50]}",
                        "setup": {"has_setup": False},
                    })


    # ── Pack 7: Multi-Indicator Combos (18 strategies) ──
    if PACK7_LOADED:
        for pack7_strats, cat_id, cat_fa in [
            (COMBO_STRATEGIES, "COMBO", "ترکیبی"),
        ]:
            for strat in pack7_strats:
                try:
                    r = strat["func"](df, context, symbol, timeframe)
                    r["strategy_id"] = strat["id"]
                    r["strategy_name"] = strat["name"]
                    r["strategy_name_fa"] = strat["name_fa"]
                    r["category"] = cat_id
                    r["category_fa"] = cat_fa
                    r["symbol"] = symbol
                    r["timeframe"] = timeframe
                    results.append(r)
                except Exception as e:
                    results.append({
                        "strategy_id": strat["id"], "strategy_name": strat["name"],
                        "strategy_name_fa": strat["name_fa"], "category": cat_id,
                        "category_fa": cat_fa, "symbol": symbol, "timeframe": timeframe,
                        "signal": "NEUTRAL", "confidence": 0,
                        "reason_fa": f"خطا: {str(e)[:50]}",
                        "setup": {"has_setup": False},
                    })


    # ── Pack 8: Advanced Indicators (25 strategies) ──
    if PACK8_LOADED:
        for pack8_strats, cat_id, cat_fa in [
            (TSI_STRATEGIES, "TSI", "شاخص قدرت واقعی"),
            (SQZ_STRATEGIES, "SQZ", "فشردگی مومنتوم"),
            (ALLI_STRATEGIES, "ALLI", "تمساح ویلیامز"),
            (KAMA_STRATEGIES, "KAMA", "میانگین تطبیقی کافمن"),
            (ZLEMA_STRATEGIES, "ZLEMA", "میانگین بدون تاخیر"),
        ]:
            for strat in pack8_strats:
                try:
                    r = strat["func"](df, context, symbol, timeframe)
                    r["strategy_id"] = strat["id"]
                    r["strategy_name"] = strat["name"]
                    r["strategy_name_fa"] = strat["name_fa"]
                    r["category"] = cat_id
                    r["category_fa"] = cat_fa
                    r["symbol"] = symbol
                    r["timeframe"] = timeframe
                    results.append(r)
                except Exception as e:
                    results.append({
                        "strategy_id": strat["id"], "strategy_name": strat["name"],
                        "strategy_name_fa": strat["name_fa"], "category": cat_id,
                        "category_fa": cat_fa, "symbol": symbol, "timeframe": timeframe,
                        "signal": "NEUTRAL", "confidence": 0,
                        "reason_fa": f"خطا: {str(e)[:50]}",
                        "setup": {"has_setup": False},
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

    print(f"[ORCH] RETURNING {len(results)} strategies")
    print(f"[ORCH] RETURNING {len(results)} strategies")
    print(f"[ORCH] RETURNING {len(results)} strategies")
    print(f"[ORCH] RETURNING {len(results)} strategies")
    print(f"[ORCH] RETURNING {len(results)} strategies")
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
    strats = [{"id": s["id"], "name": s["name"], "name_fa": s["name_fa"]} for s in ALL_STRATEGIES]
    # Include Pack 1-7 strategies
    pack_lists = []
    if PACK1_LOADED:
        pack_lists += [DON_STRATEGIES, KC_STRATEGIES, ENV_STRATEGIES, PSAR_STRATEGIES, REG_STRATEGIES]
    if PACK2_LOADED:
        pack_lists += [TRIX_STRATEGIES, ROC_STRATEGIES, CMO_STRATEGIES, RVI_STRATEGIES, PPO_STRATEGIES]
    if PACK3_LOADED:
        pack_lists += [OBV_STRATEGIES, MFI_STRATEGIES, VWAP_STRATEGIES, AD_STRATEGIES, FI_STRATEGIES]
    if PACK4_LOADED:
        pack_lists += [ADX_ADV_STRATEGIES, ADX_ADV_STRATEGIES, STREND_STRATEGIES, AROON_STRATEGIES, DPO_STRATEGIES, VORTEX_STRATEGIES]
    if PACK5_LOADED:
        pack_lists += [ELDER_STRATEGIES, FISHER_STRATEGIES, HEIKIN_STRATEGIES, CHOP_STRATEGIES, MASS_STRATEGIES]
    if PACK6_LOADED:
        pack_lists += [PIVOT_ADV_STRATEGIES, PIVOT_ADV_STRATEGIES, GAPS_STRATEGIES, RANGE_STRATEGIES, SWING_STRATEGIES, HARMONIC_STRATEGIES]
    if PACK7_LOADED:
        pack_lists += [COMBO_STRATEGIES]
    if PACK8_LOADED:
        pack_lists += [TSI_STRATEGIES, SQZ_STRATEGIES, ALLI_STRATEGIES, KAMA_STRATEGIES, ZLEMA_STRATEGIES]
    seen = {s["id"] for s in strats}
    for pl in pack_lists:
        for s in pl:
            if s["id"] not in seen:
                strats.append({"id": s["id"], "name": s["name"], "name_fa": s.get("name_fa", s["name"])})
                seen.add(s["id"])
    return strats


def get_strategy_count() -> int:
    return len(get_available_strategies())

# Phase 6
ALL_STRATEGIES += PHASE6_HARM + PHASE6_EW + PHASE6_CP

# Phase 7
ALL_STRATEGIES += PHASE7_SRSI + PHASE7_ARN + PHASE7_VTX + PHASE7_ULT + PHASE7_KST
ALL_STRATEGIES += PHASE8_CH + PHASE8_GAP + PHASE8_MS
ALL_STRATEGIES += PHASE9_WYC + PHASE9_SNT + PHASE9_COR
ALL_STRATEGIES += PHASE10_AIC + PHASE10_ADP

# Phase 8


try:
    from backend.strategies.gap_structure_strategies import GAP_STRATEGIES, MS_STRATEGIES
except ImportError:
    pass
# End Phase 8


# ── Register Pack 1-7 in ALL_STRATEGIES ──
if PACK1_LOADED:
    for _p in [DON_STRATEGIES,KC_STRATEGIES,ENV_STRATEGIES,PSAR_STRATEGIES,REG_STRATEGIES]:
        ALL_STRATEGIES.extend(_p)
if PACK2_LOADED:
    for _p in [TRIX_STRATEGIES,ROC_STRATEGIES,CMO_STRATEGIES,RVI_STRATEGIES,PPO_STRATEGIES]:
        ALL_STRATEGIES.extend(_p)
if PACK3_LOADED:
    for _p in [OBV_STRATEGIES,MFI_STRATEGIES,VWAP_STRATEGIES,AD_STRATEGIES,FI_STRATEGIES]:
        ALL_STRATEGIES.extend(_p)
if PACK4_LOADED:
    for _p in [ADX_ADV_STRATEGIES,STREND_STRATEGIES,AROON_STRATEGIES,DPO_STRATEGIES,VORTEX_STRATEGIES]:
        ALL_STRATEGIES.extend(_p)
if PACK5_LOADED:
    for _p in [ELDER_STRATEGIES,FISHER_STRATEGIES,HEIKIN_STRATEGIES,CHOP_STRATEGIES,MASS_STRATEGIES]:
        ALL_STRATEGIES.extend(_p)
if PACK6_LOADED:
    for _p in [PIVOT_ADV_STRATEGIES,GAPS_STRATEGIES,RANGE_STRATEGIES,SWING_STRATEGIES,HARMONIC_STRATEGIES]:
        ALL_STRATEGIES.extend(_p)
if PACK7_LOADED:
    ALL_STRATEGIES.extend(COMBO_STRATEGIES)
if PACK8_LOADED:
    for _p in [TSI_STRATEGIES,SQZ_STRATEGIES,ALLI_STRATEGIES,KAMA_STRATEGIES,ZLEMA_STRATEGIES]:
        ALL_STRATEGIES.extend(_p)
print(f"[ORCH] Packs registered. Total: {len(ALL_STRATEGIES)}")




