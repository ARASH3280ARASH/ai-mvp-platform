"""
Whilber-AI MVP - FastAPI Server (v5 - Alerts + Setup + Registration)
=====================================================================
Run: uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload
"""

import os, sys, time, json, numpy as np, html as _html_mod
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")

from backend.mt5.mt5_connector import MT5Connector
from backend.mt5.data_fetcher import fetch_current_price, clear_cache
from backend.mt5.symbol_map import (
    SYMBOLS, CATEGORY_FA, SymbolCategory,
    get_symbols_by_category, get_all_categories,
    get_farsi_name, get_symbol_info, validate_symbol,
)
from backend.mt5.timeframes import get_all_timeframes, validate_timeframe
from backend.strategies.orchestrator import (
    analyze_symbol, get_available_strategies, get_strategy_count
)

# Setup calculator
try:
    from backend.strategies.setup_calculator import (
        calculate_master_setup, enrich_strategies_with_setups
    )
    SETUP_AVAILABLE = True
except ImportError:
    SETUP_AVAILABLE = True

# User manager
try:
    from backend.api.user_manager import register_user, check_user, get_user_count
    USER_MGMT = True
except ImportError:
    USER_MGMT = False

# Alert manager
try:
    from backend.api.alert_manager import (
        create_alert, get_alerts, get_alert_by_id, delete_alert, toggle_alert,
        update_alert, reactivate_alert, get_alert_stats,
        get_notifications, delete_notification, mark_read, get_unread_count,
        check_alerts, check_price_alerts_live, check_trade_updates,
        get_alert_types,
        get_templates as get_alert_templates,
        save_template as save_alert_template,
        reset_template as reset_alert_template,
        save_user_config, get_user_config,
    )
    ALERT_AVAILABLE = True
    logger.info("✅ Alert manager loaded")
except ImportError:
    ALERT_AVAILABLE = False
    logger.warning("⚠️ alert_manager not found")

# Performance monitor
try:
    from backend.api.performance_monitor import (
        get_account_details as perf_account,
        get_open_positions as perf_positions,
        get_trade_history as perf_history,
        calculate_metrics as perf_metrics,
        get_equity_curve as perf_equity,
        get_drawdown_analysis as perf_drawdown,
        get_daily_summary as perf_daily,
        get_symbol_distribution as perf_symbols,
        get_performance_snapshot as perf_snapshot,
    )
    _PERF_AVAILABLE = True
    logger.info("✅ Performance monitor loaded")
except ImportError:
    _PERF_AVAILABLE = False
    logger.warning("⚠️ performance_monitor not found")


def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'item'):
        return obj.item()
    elif obj is np.nan or (isinstance(obj, float) and np.isnan(obj)):
        return None
    return obj


def _sanitize_input(s):
    """HTML-escape user-facing string inputs to prevent XSS."""
    if not isinstance(s, str):
        return s
    return _html_mod.escape(s.strip())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Whilber-AI server v5...")
    connector = MT5Connector.get_instance()
    if connector.connect():
        logger.info("✅ MT5 connected")
    else:
        logger.warning("⚠️ MT5 failed — will retry")

    # Auto daily snapshot on startup
    try:
        from backend.api.daily_snapshot import take_snapshot
        snap_result = take_snapshot()
        logger.info(f"[SNAPSHOT] {snap_result}")
    except Exception as _se:
        logger.warning(f"[SNAPSHOT] Failed: {_se}")


    # Start Telegram bot polling


    try:


        from backend.api.telegram_bot import init as tg_init, start_polling as tg_start


        if tg_init():


            tg_start()


            print("[TELEGRAM] Bot polling started")


    except Exception as _tge:


        print(f"[TELEGRAM] Startup error: {_tge}")

    # Check expired plans on startup
    try:
        if _PAY_OK:
            expired = _pay_check_expiry()
            logger.info(f"[EXPIRY] Downgraded {expired} expired plans")
    except Exception as _exp_e:
        logger.warning(f"[EXPIRY] Check failed: {_exp_e}")

    yield
    logger.info("🛑 Shutting down...")
    connector.disconnect()


app = FastAPI(

    title="Whilber-AI Trading Analysis",
    description="184 strategies + trade setups + alerts",
    version="5.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000", "http://54.37.187.87:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: str = ""

@app.post("/api/register")
async def api_register(req: RegisterRequest, request: Request):
    if not USER_MGMT:
        return {"success": True, "message": "Registration disabled"}
    ip = request.client.host if request.client else ""
    return register_user(req.name, req.email, req.phone, ip)

@app.get("/api/check-user")
async def api_check_user(email: str = "", request: Request = None):
    if not USER_MGMT:
        return {"registered": True}
    ip = request.client.host if request and request.client else ""
    return check_user(email=email, ip=ip)


# ═══════════════════════════════════════════════════
# ALERT ENDPOINTS
# ═══════════════════════════════════════════════════

class CreateAlertRequest(BaseModel):
    user_email: str
    symbol: str
    timeframe: str = ""
    alert_type: str
    strategy_id: Optional[str] = None
    target_price: Optional[float] = None
    notes: str = ""
    channels: Optional[dict] = None
    custom_message: Optional[str] = None
    repeat: bool = False

@app.post("/api/alerts")
async def api_create_alert(req: CreateAlertRequest, authorization: str = Header(None)):
    if not ALERT_AVAILABLE:
        raise HTTPException(503, "Alert system not available")
    # Plan limit enforcement
    if _PLANS_OK and req.user_email:
        user_id, _email, plan = _resolve_plan_from_auth(authorization)
        existing = get_alerts(user_email=req.user_email, active_only=True)
        current_count = len(existing) if isinstance(existing, list) else 0
        allowed, remaining, limit = check_alert_limit(plan, current_count)
        if not allowed:
            raise HTTPException(403, detail={
                "error": f"سقف هشدارها ({limit} هشدار) در پلن {PLAN_NAMES_FA.get(plan, 'رایگان')} پر شده است",
                "error_code": "alert_limit_reached",
                "upgrade_url": "/pricing",
                "limit": limit,
                "used": current_count,
            })
    result = create_alert(
        user_email=req.user_email,
        symbol=req.symbol,
        timeframe=req.timeframe,
        alert_type=req.alert_type,
        strategy_id=req.strategy_id,
        target_price=req.target_price,
        notes=req.notes,
        channels=req.channels,
        custom_message=req.custom_message,
        repeat=req.repeat,
    )
    return result

@app.get("/api/alerts")
async def api_get_alerts(email: str, symbol: str = None, active_only: bool = True, category: str = None, all: bool = False):
    if not ALERT_AVAILABLE:
        return {"alerts": []}
    alerts = get_alerts(user_email=email, symbol=symbol, active_only=active_only, category=category, include_all=all)
    return {"alerts": alerts}

@app.get("/api/alerts/{alert_id}")
async def api_get_alert(alert_id: str, email: str = ""):
    if not ALERT_AVAILABLE:
        return {"alert": None}
    alert = get_alert_by_id(alert_id, user_email=email or None)
    return {"alert": alert}

@app.put("/api/alerts/{alert_id}")
async def api_update_alert(alert_id: str, request: Request):
    if not ALERT_AVAILABLE:
        return {"success": False}
    body = await request.json()
    email = body.pop("user_email", "")
    return update_alert(alert_id, email, body)

@app.delete("/api/alerts/{alert_id}")
async def api_delete_alert(alert_id: str, email: str = ""):
    if not ALERT_AVAILABLE:
        return {"success": False}
    return delete_alert(alert_id, user_email=email or None)

@app.post("/api/alerts/{alert_id}/toggle")
async def api_toggle_alert(alert_id: str, email: str = ""):
    if not ALERT_AVAILABLE:
        return {"success": False}
    return toggle_alert(alert_id, user_email=email or None)

@app.post("/api/alerts/{alert_id}/reactivate")
async def api_reactivate_alert(alert_id: str, request: Request):
    if not ALERT_AVAILABLE:
        return {"success": False}
    body = await request.json()
    return reactivate_alert(alert_id, body.get("user_email", ""))

@app.get("/api/alert-types")
async def api_alert_types():
    if not ALERT_AVAILABLE:
        return {"types": {}}
    return {"types": get_alert_types()}

@app.get("/api/alert/stats")
async def api_alert_stats(email: str = ""):
    if not ALERT_AVAILABLE:
        return {}
    return get_alert_stats(email)

# ── Templates ──
@app.get("/api/alert/templates")
async def api_get_templates(email: str = ""):
    if not ALERT_AVAILABLE:
        return {"templates": {}}
    return {"templates": get_alert_templates(email or None)}

@app.post("/api/alert/templates")
async def api_save_template(request: Request):
    if not ALERT_AVAILABLE:
        return {"success": False}
    body = await request.json()
    return save_alert_template(body.get("email", ""), body.get("alert_type", ""), body.get("template", ""))

@app.post("/api/alert/templates/reset")
async def api_reset_template(request: Request):
    if not ALERT_AVAILABLE:
        return {"success": False}
    body = await request.json()
    return reset_alert_template(body.get("email", ""), body.get("alert_type", ""))

# ── Simplified user config (email + telegram) ──
@app.post("/api/alert/simple-setup")
async def api_simple_setup(request: Request):
    if not ALERT_AVAILABLE:
        return {"success": False}
    body = await request.json()
    return save_user_config(body.get("email", ""), body)

@app.get("/api/alert/user-config")
async def api_user_config(email: str = ""):
    if not ALERT_AVAILABLE:
        return {}
    return get_user_config(email)

# ── Live price alert check ──
@app.post("/api/alert/check-prices")
async def api_check_prices(request: Request):
    if not ALERT_AVAILABLE:
        return {"triggered": []}
    body = await request.json()
    prices = body.get("prices", {})
    if not prices:
        # Try to get live prices from MT5
        try:
            import MetaTrader5 as mt5
            connector = MT5Connector.get_instance()
            if connector.ensure_connected():
                for sym in ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]:
                    tick = mt5.symbol_info_tick(sym)
                    if tick:
                        prices[sym] = tick.bid
        except Exception:
            pass
    triggered = check_price_alerts_live(prices)
    return {"triggered": len(triggered), "alerts": triggered}

# ── Notification delete ──
@app.delete("/api/notifications/{notif_id}")
async def api_delete_notification(notif_id: str, email: str = ""):
    if not ALERT_AVAILABLE:
        return {"success": False}
    return delete_notification(email, notif_id)


# ═══════════════════════════════════════════════════
# NOTIFICATION ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/api/notifications")
async def api_get_notifications(email: str, limit: int = 50, unread: bool = False):
    if not ALERT_AVAILABLE:
        return {"notifications": [], "unread_count": 0}
    notifs = get_notifications(email, limit=limit, unread_only=unread)
    count = get_unread_count(email)
    return {"notifications": notifs, "unread_count": count}

@app.post("/api/notifications/read")
async def api_mark_read(email: str, notif_id: str = None):
    if not ALERT_AVAILABLE:
        return {"marked": 0}
    return mark_read(email, notif_id)

@app.get("/api/notifications/count")
async def api_unread_count(email: str):
    if not ALERT_AVAILABLE:
        return {"count": 0}
    return {"count": get_unread_count(email)}


# ═══════════════════════════════════════════════════
# CORE ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    connector = MT5Connector.get_instance()
    connected = connector.ensure_connected()
    return {
        "status": "ok" if connected else "degraded",
        "mt5_connected": connected,
        "strategies": get_strategy_count(),
        "symbols": len(SYMBOLS),
        "setup_engine": SETUP_AVAILABLE,
        "alert_engine": ALERT_AVAILABLE,
        "users": get_user_count() if USER_MGMT else 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/api/symbols")
async def list_symbols():
    """List all 33 supported symbols grouped by category."""
    groups = {
    "فارکس — ماژور": [
        {
            "symbol": "EURUSD",
            "name_fa": "یورو/دلار"
        },
        {
            "symbol": "GBPUSD",
            "name_fa": "پوند/دلار"
        },
        {
            "symbol": "USDJPY",
            "name_fa": "دلار/ین"
        },
        {
            "symbol": "USDCHF",
            "name_fa": "دلار/فرانک"
        },
        {
            "symbol": "AUDUSD",
            "name_fa": "استرالیا/دلار"
        },
        {
            "symbol": "NZDUSD",
            "name_fa": "نیوزیلند/دلار"
        },
        {
            "symbol": "USDCAD",
            "name_fa": "دلار/کانادا"
        }
    ],
    "فارکس — یورو کراس": [
        {
            "symbol": "EURGBP",
            "name_fa": "یورو/پوند"
        },
        {
            "symbol": "EURJPY",
            "name_fa": "یورو/ین"
        },
        {
            "symbol": "EURAUD",
            "name_fa": "یورو/استرالیا"
        },
        {
            "symbol": "EURCAD",
            "name_fa": "یورو/کانادا"
        },
        {
            "symbol": "EURCHF",
            "name_fa": "یورو/فرانک"
        },
        {
            "symbol": "EURNZD",
            "name_fa": "یورو/نیوزیلند"
        }
    ],
    "فارکس — پوند کراس": [
        {
            "symbol": "GBPJPY",
            "name_fa": "پوند/ین"
        },
        {
            "symbol": "GBPAUD",
            "name_fa": "پوند/استرالیا"
        },
        {
            "symbol": "GBPCAD",
            "name_fa": "پوند/کانادا"
        },
        {
            "symbol": "GBPCHF",
            "name_fa": "پوند/فرانک"
        },
        {
            "symbol": "GBPNZD",
            "name_fa": "پوند/نیوزیلند"
        }
    ],
    "فارکس — AUD/NZD/CAD/CHF": [
        {
            "symbol": "AUDJPY",
            "name_fa": "استرالیا/ین"
        },
        {
            "symbol": "AUDNZD",
            "name_fa": "استرالیا/نیوزیلند"
        },
        {
            "symbol": "AUDCAD",
            "name_fa": "استرالیا/کانادا"
        },
        {
            "symbol": "AUDCHF",
            "name_fa": "استرالیا/فرانک"
        },
        {
            "symbol": "NZDJPY",
            "name_fa": "نیوزیلند/ین"
        },
        {
            "symbol": "NZDCAD",
            "name_fa": "نیوزیلند/کانادا"
        },
        {
            "symbol": "NZDCHF",
            "name_fa": "نیوزیلند/فرانک"
        },
        {
            "symbol": "CADJPY",
            "name_fa": "کانادا/ین"
        },
        {
            "symbol": "CADCHF",
            "name_fa": "کانادا/فرانک"
        },
        {
            "symbol": "CHFJPY",
            "name_fa": "فرانک/ین"
        }
    ],
    "فلزات": [
        {
            "symbol": "XAUUSD",
            "name_fa": "طلا"
        },
        {
            "symbol": "XAGUSD",
            "name_fa": "نقره"
        }
    ],
    "کریپتو": [
        {
            "symbol": "BTCUSD",
            "name_fa": "بیت‌کوین"
        }
    ],
    "شاخص‌ها": [
        {
            "symbol": "NAS100",
            "name_fa": "نزدک"
        },
        {
            "symbol": "US30",
            "name_fa": "داوجونز"
        }
    ]
}
    all_syms = []
    for syms in groups.values():
        all_syms.extend(syms)
    return {
        "total": len(all_syms),
        "groups": groups,
        "symbols": all_syms,
    }


@app.get("/api/strategies")
async def list_strategies():
    return {"total": get_strategy_count(), "strategies": get_available_strategies()}

@app.get("/api/analyze/{symbol}")
@app.get("/api/analyze/{symbol}/{timeframe}")
async def analyze(
    symbol: str,
    # TEST

    # TEST

    # TEST

    # TEST

    timeframe: str = "H1",
    strategies: Optional[str] = Query(None),
):
    print("[ANALYZE-HIT]")
    print("[ANALYZE-HIT]")
    print("[ANALYZE-HIT]")
    print("[ANALYZE-HIT]")
    symbol = symbol.upper()
    timeframe = timeframe.upper()
    strat_list = [s.strip() for s in strategies.split(",")] if strategies else None
    result = analyze_symbol(symbol, timeframe, strategies=strat_list)
    print(f"[SERVER] strategies from orchestrator: {len(result.get(chr(115)+chr(116)+chr(114)+chr(97)+chr(116)+chr(101)+chr(103)+chr(105)+chr(101)+chr(115),[]))}")
    print(f"[SERVER] result keys: {list(result.keys())}")
    print(f"[SERVER] strategies from orchestrator: {len(result.get(chr(115)+chr(116)+chr(114)+chr(97)+chr(116)+chr(101)+chr(103)+chr(105)+chr(101)+chr(115),[]))}")
    print(f"[SERVER] result keys: {list(result.keys())}")
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Analysis failed"))
    # Preserve strategies count
    strat_count = len(result.get("strategies", []))
    # Try setup enrichment but never lose strategies
    if False and SETUP_AVAILABLE:
        try:
            price = result.get("last_close")
            ctx = result.get("context", {})
            atr = ctx.get("atr_value")
            if atr is None and ctx.get("atr_percent"):
                atr = price * ctx["atr_percent"] / 100 if price else None
            if price and atr:
                result["strategies"] = enrich_strategies_with_setups(
                    result.get("strategies", []), price, atr, ctx
                )
            result["master_setup"] = calculate_master_setup(result)
        except Exception as e:
            logger.error(f"Setup error: {e}")
            result["master_setup"] = {"has_setup": False, "reason_fa": "خطا"}
    else:
        result["master_setup"] = {"has_setup": False, "reason_fa": "غیرفعال"}
    # Safety check - if strategies got lost, something is very wrong
    if len(result.get("strategies", [])) == 0 and strat_count > 0:
        logger.error(f"STRATEGIES LOST! Had {strat_count}, now 0")
    # Alerts
    triggered_alerts = []
    if ALERT_AVAILABLE:
        try:
            triggered_alerts = check_alerts(result)
        except:
            pass
    result["triggered_alerts"] = triggered_alerts
    strats=result.get("strategies",[]); return {"count":len(strats),"strategies":strats[:5]}

@app.get("/api/multi/{symbols}")
async def analyze_multi(symbols: str, timeframe: str = "H1"):
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    if len(symbol_list) > 10:
        raise HTTPException(400, "حداکثر ۱۰ نماد")
    results = {}
    for sym in symbol_list:
        r = analyze_symbol(sym, timeframe)
        if r.get("success"):
            results[sym] = {
                "signal": r["overall"]["signal"],
                "signal_fa": r["overall"]["signal_fa"],
                "confidence": r["overall"]["confidence"],
                "buy_count": r["overall"]["buy_count"],
                "sell_count": r["overall"]["sell_count"],
                "neutral_count": r["overall"]["neutral_count"],
                "summary_fa": r["overall"]["summary_fa"],
                "last_close": r["last_close"],
                "price": r.get("price", {}),
                "context": r.get("context", {}),
                "time": r["performance"]["total_time"],
            }
        else:
            results[sym] = {"error": r.get("error")}
    return JSONResponse(content=sanitize({
        "timeframe": timeframe, "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }))

@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
    symbol = symbol.upper()
    if not validate_symbol(symbol):
        raise HTTPException(400, f"نماد {symbol} پشتیبانی نمی‌شود")
    connector = MT5Connector.get_instance()
    if not connector.ensure_connected():
        raise HTTPException(503, "MT5 متصل نیست")
    price = fetch_current_price(symbol)
    if not price:
        raise HTTPException(404, "قیمت در دسترس نیست")
    return JSONResponse(content=sanitize({
        "symbol": symbol, "symbol_fa": get_farsi_name(symbol),
        **price, "timestamp": datetime.now(timezone.utc).isoformat(),
    }))

@app.get("/api/timeframes")
async def list_timeframes():
    return {"timeframes": get_all_timeframes()}

@app.post("/api/cache/clear")
async def clear_data_cache():
    clear_cache()
    return {"status": "cache cleared"}

# Dashboard
DASHBOARD_PATH = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "dashboard.html")
LANDING_PATH = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "landing.html")

@app.get("/", response_class=HTMLResponse)
async def landing_home():
    if os.path.exists(LANDING_PATH):
        with open(LANDING_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    elif os.path.exists(DASHBOARD_PATH):
        with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard not found</h1>")

# ======= ROBOT STORE =======
try:
    from backend.api.robot_manager import (
        add_robot, update_robot, delete_robot, get_robots, get_robot,
        increment_download, toggle_featured, toggle_active,
        get_categories, get_stats as robot_stats, verify_admin,
        add_review, get_reviews, delete_review, increment_views,
        search_robots, get_robots_sorted,
    )
    ROBOT_STORE = True
except ImportError:
    ROBOT_STORE = False

from typing import Optional as _OptR

class RobotCreateRequest(BaseModel):
    password: str
    name_fa: str
    description_fa: str
    category: str = "other"
    version: str = "1.0"
    platform: str = "MT5"
    price_type: str = "free"
    price_amount: float = 0
    symbols_fa: str = ""
    timeframes_fa: str = ""
    min_balance: str = ""
    features_fa: str = ""
    tags: str = ""
    image_data: _OptR[str] = None
    image_ext: str = "png"
    file_data: _OptR[str] = None
    file_name: str = "robot.ex5"

class ReviewRequest(BaseModel):
    author: str
    rating: int
    text: str

class RobotUpdateRequest(BaseModel):
    password: str
    name_fa: _OptR[str] = None
    description_fa: _OptR[str] = None
    category: _OptR[str] = None
    version: _OptR[str] = None
    platform: _OptR[str] = None
    price_type: _OptR[str] = None
    price_amount: _OptR[float] = None
    symbols_fa: _OptR[str] = None
    timeframes_fa: _OptR[str] = None
    min_balance: _OptR[str] = None
    features_fa: _OptR[str] = None
    tags: _OptR[str] = None
    image_data: _OptR[str] = None
    image_ext: str = "png"
    file_data: _OptR[str] = None
    file_name: _OptR[str] = None

if ROBOT_STORE:

    @app.get("/api/robots")
    async def api_list_robots(category: str = None, sort: str = None):
        if sort:
            return {"robots": get_robots_sorted(sort_by=sort, category=category)}
        return {"robots": get_robots(category=category)}

    @app.get("/api/robots/categories")
    async def api_robot_categories():
        return {"categories": get_categories()}

    @app.get("/api/robots/stats")
    async def api_robot_stats():
        return robot_stats()

    @app.get("/api/robots/search")
    async def api_search_robots(q: str = ""):
        return {"robots": search_robots(q)}

    @app.get("/api/robots/{rid}")
    async def api_get_robot(rid: str):
        r = get_robot(rid)
        return r if r else {"error": "not found"}

    @app.post("/api/robots")
    async def api_create_robot(req: RobotCreateRequest):
        if not verify_admin(req.password):
            return {"success": False, "error": "forbidden"}
        return add_robot(
            name_fa=req.name_fa, description_fa=req.description_fa,
            category=req.category, version=req.version, platform=req.platform,
            price_type=req.price_type, price_amount=req.price_amount,
            symbols_fa=req.symbols_fa, timeframes_fa=req.timeframes_fa,
            min_balance=req.min_balance, features_fa=req.features_fa,
            tags=req.tags, image_data=req.image_data, image_ext=req.image_ext,
            file_data=req.file_data, file_name=req.file_name,
        )

    @app.put("/api/robots/{rid}")
    async def api_update_robot(rid: str, req: RobotUpdateRequest):
        if not verify_admin(req.password):
            return {"success": False, "error": "forbidden"}
        updates = {}
        for k in ["name_fa","description_fa","category","version","platform","price_type","price_amount","symbols_fa","timeframes_fa","min_balance","features_fa","tags"]:
            v = getattr(req, k, None)
            if v is not None:
                updates[k] = v
        return update_robot(rid, updates, image_data=req.image_data, image_ext=req.image_ext, file_data=req.file_data, file_name=req.file_name)

    @app.delete("/api/robots/{rid}")
    async def api_delete_robot(rid: str, password: str = ""):
        if not verify_admin(password):
            return {"success": False, "error": "forbidden"}
        return delete_robot(rid)

    @app.post("/api/robots/{rid}/download")
    async def api_download_robot(rid: str, authorization: str = Header(None)):
        # Plan gate: robots not available on free plan
        if _PLANS_OK:
            _uid, _em, plan = _resolve_plan_from_auth(authorization)
            limits = get_plan_limits(plan)
            if limits.get("max_robots", 0) <= 0:
                raise HTTPException(403, detail={
                    "error": "دانلود ربات مخصوص پلن حرفه‌ای و بالاتر است",
                    "error_code": "feature_restricted",
                    "upgrade_url": "/pricing",
                })
        r = get_robot(rid)
        if not r or not r.get("file_path"):
            return {"error": "not found"}
        increment_download(rid)
        import os as _os
        fp = _os.path.join(r"C:\Users\Administrator\Desktop\mvp", "robots", r["file_path"])
        if not _os.path.exists(fp):
            return {"error": "file missing"}
        from fastapi.responses import FileResponse
        return FileResponse(fp, filename=r.get("file_name","robot.ex5"), media_type="application/octet-stream")

    @app.post("/api/robots/{rid}/toggle-featured")
    async def api_toggle_featured(rid: str, password: str = ""):
        if not verify_admin(password):
            return {"success": False}
        return toggle_featured(rid)

    @app.post("/api/robots/{rid}/toggle-active")
    async def api_toggle_active(rid: str, password: str = ""):
        if not verify_admin(password):
            return {"success": False}
        return toggle_active(rid)

    @app.post("/api/robots/{rid}/reviews")
    async def api_add_review(rid: str, req: ReviewRequest):
        return add_review(rid, req.author, req.rating, req.text)

    @app.get("/api/robots/{rid}/reviews")
    async def api_get_reviews(rid: str):
        return {"reviews": get_reviews(rid)}

    @app.delete("/api/robots/{rid}/reviews/{rev_id}")
    async def api_delete_review(rid: str, rev_id: str, password: str = ""):
        return delete_review(rev_id, password)

    @app.post("/api/robots/{rid}/view")
    async def api_increment_views(rid: str):
        return {"views": increment_views(rid)}

    import os as _os2
    _ri = _os2.path.join(r"C:\Users\Administrator\Desktop\mvp", "robots", "images")
    if _os2.path.isdir(_ri):
        from fastapi.staticfiles import StaticFiles
        app.mount("/robots/images", StaticFiles(directory=_ri), name="robot-images")

import os as _os3
_robots_page = _os3.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "robots.html")
_admin_page = _os3.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "admin.html")

@app.get("/robots")
async def page_robots():
    from fastapi.responses import HTMLResponse
    if _os3.path.exists(_robots_page):
        with open(_robots_page, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Not found</h1>")

@app.get("/admin")
async def page_admin():
    from fastapi.responses import HTMLResponse
    if _os3.path.exists(_admin_page):
        with open(_admin_page, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Not found</h1>")
# ======= END ROBOT STORE =======


# ======= USER AUTH =======
try:
    from backend.api.auth_manager import (
        register_user as _auth_register,
        login_user as _auth_login,
        verify_otp as _auth_verify_otp,
        get_user_profile as _auth_profile,
        verify_user_token as _auth_verify_token,
        increment_daily_analysis as _auth_increment_analysis,
        get_daily_analysis_count as _auth_get_analysis_count,
        check_login_rate as _auth_check_login_rate,
        check_register_rate as _auth_check_register_rate,
    )
    _AUTH_OK = True
except ImportError as _ae:
    _AUTH_OK = False
    logger.warning(f"[AUTH] Not available: {_ae}")

# ── Plans ──
try:
    import backend.api.plans as _plans_module
    from backend.api.plans import (
        PLAN_LIMITS, PLAN_NAMES_FA,
        get_plan_limits, check_symbol_access, check_timeframe_access,
        check_daily_analysis_limit, check_alert_limit, check_journal_limit,
        check_feature_access, get_strategy_limit, get_plan_info_for_response,
    )
    _PLANS_OK = True
    logger.info("✅ Plans module loaded")
except ImportError as _pe:
    _PLANS_OK = False
    _plans_module = None
    logger.warning(f"[PLANS] Not available: {_pe}")

# ── Payment Manager ──
try:
    from backend.api.payment_manager import (
        create_payment as _pay_create,
        verify_zarinpal_payment as _pay_verify_zp,
        confirm_card_payment as _pay_confirm_card,
        submit_tether_payment as _pay_submit_tether,
        admin_approve_payment as _pay_admin_approve,
        admin_reject_payment as _pay_admin_reject,
        get_payment_history as _pay_history,
        get_payment_by_id as _pay_get,
        apply_discount_code as _pay_discount,
        check_expired_plans as _pay_check_expiry,
        get_all_payments_admin as _pay_admin_list,
        get_payment_config as _pay_config,
    )
    _PAY_OK = True
    logger.info("✅ Payment manager loaded")
except ImportError as _paye:
    _PAY_OK = False
    logger.warning(f"[PAYMENT] Not available: {_paye}")

# ── Admin Manager (Phase 4) ──
try:
    from backend.api.admin_manager import (
        get_auth_users as _adm_users,
        get_auth_user_detail as _adm_user_detail,
        admin_change_plan as _adm_change_plan,
        admin_toggle_user as _adm_toggle_user,
        get_user_stats as _adm_user_stats,
        export_users_csv as _adm_export_csv,
        create_discount as _adm_create_disc,
        get_all_discounts as _adm_get_discs,
        toggle_discount as _adm_toggle_disc,
        delete_discount as _adm_del_disc,
        get_revenue_stats as _adm_rev_stats,
        get_revenue_chart as _adm_rev_chart,
        admin_send_notification as _adm_notify,
    )
    _ADM_EXT_OK = True
    logger.info("✅ Admin manager (Phase 4) loaded")
except ImportError as _adme:
    _ADM_EXT_OK = False
    logger.warning(f"[ADMIN-EXT] Not available: {_adme}")


def _resolve_plan_from_auth(authorization: str = None) -> tuple:
    """Resolve (user_id, email, plan) from Authorization header. Returns (None, None, 'free') if no auth."""
    if not authorization or not _AUTH_OK:
        return None, None, "free"
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None, None, "free"
    payload = _auth_verify_token(token)
    if not payload:
        return None, None, "free"
    user_id = payload.get("sub")
    email = payload.get("email", "")
    profile = _auth_profile(user_id) if user_id else None
    plan = profile.get("plan", "free") if profile else "free"
    return user_id, email, plan

class _RegisterReq(BaseModel):
    email: str
    password: str
    name: str
    mobile: str = ""

class _LoginReq(BaseModel):
    email: str
    password: str

class _OtpReq(BaseModel):
    email: str
    otp: str

if _AUTH_OK:

    @app.post("/api/auth/register")
    async def api_auth_register(req: _RegisterReq, request: Request):
        ip = request.client.host if request.client else "unknown"
        if not _auth_check_register_rate(ip):
            raise HTTPException(429, "تعداد تلاش‌ها بیش از حد مجاز. لطفا بعدا تلاش کنید")
        name = _sanitize_input(req.name)
        mobile = _sanitize_input(req.mobile)
        result = _auth_register(req.email, req.password, name, mobile)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.post("/api/auth/login")
    async def api_auth_login(req: _LoginReq, request: Request):
        ip = request.client.host if request.client else "unknown"
        if not _auth_check_login_rate(ip):
            raise HTTPException(429, "تعداد تلاش‌ها بیش از حد مجاز. لطفا بعدا تلاش کنید")
        result = _auth_login(req.email, req.password)
        if not result["success"]:
            code = result.get("code", "")
            status = 401 if code == "invalid_credentials" else 400
            raise HTTPException(status, result["error"])
        return result

    @app.post("/api/auth/verify-otp")
    async def api_auth_verify_otp(req: _OtpReq):
        result = _auth_verify_otp(req.email, req.otp)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.get("/api/auth/profile")
    async def api_auth_profile(authorization: str = Header(None)):
        if not authorization:
            raise HTTPException(401, "توکن احراز هویت الزامی است")
        token = authorization.replace("Bearer ", "").strip()
        payload = _auth_verify_token(token)
        if not payload:
            raise HTTPException(401, "توکن نامعتبر یا منقضی شده")
        profile = _auth_profile(payload["sub"])
        if not profile:
            raise HTTPException(404, "کاربر یافت نشد")
        return {"success": True, "user": profile}

import os as _os_auth
_login_page_path = _os_auth.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "login.html")
_register_page_path = _os_auth.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "register.html")

@app.get("/login")
async def page_login():
    from fastapi.responses import HTMLResponse
    if _os_auth.path.exists(_login_page_path):
        with open(_login_page_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Not found</h1>")

@app.get("/register")
async def page_register():
    from fastapi.responses import HTMLResponse
    if _os_auth.path.exists(_register_page_path):
        with open(_register_page_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Not found</h1>")
# ======= END USER AUTH =======


# ======= STRATEGY BUILDER =======
try:
    from backend.api.strategy_engine import get_builder_config, validate_strategy
    from backend.api.strategy_store import (
        save_strategy, get_strategies, get_strategy,
        delete_strategy, duplicate_strategy, export_strategy, import_strategy,
    )
    BUILDER_AVAILABLE = True
except ImportError:
    BUILDER_AVAILABLE = False

if BUILDER_AVAILABLE:

    @app.get("/api/builder/config")
    async def api_builder_config():
        return get_builder_config()

    @app.get("/api/builder/strategies")
    async def api_builder_list(email: str = ""):
        if not email:
            return {"strategies": []}
        return {"strategies": get_strategies(email)}

    @app.get("/api/builder/strategies/{sid}")
    async def api_builder_get(sid: str, email: str = ""):
        s = get_strategy(email, sid)
        return s if s else {"error": "not found"}

    @app.post("/api/builder/strategies")
    async def api_builder_save(request: Request, authorization: str = Header(None)):
        body = await request.json()
        email = body.get("email", "")
        strategy = body.get("strategy", {})
        if not email:
            return {"success": False, "errors": ["email required"]}
        # Plan gate: builder is pro+ only
        if _PLANS_OK:
            _uid, _em, plan = _resolve_plan_from_auth(authorization)
            if not check_feature_access(plan, "builder"):
                raise HTTPException(403, detail={
                    "error": "استراتژی‌ساز مخصوص پلن حرفه‌ای و بالاتر است",
                    "error_code": "feature_restricted",
                    "upgrade_url": "/pricing",
                })
        return save_strategy(email, strategy)

    @app.delete("/api/builder/strategies/{sid}")
    async def api_builder_delete(sid: str, email: str = ""):
        return delete_strategy(email, sid)

    @app.post("/api/builder/strategies/{sid}/duplicate")
    async def api_builder_duplicate(sid: str, email: str = ""):
        return duplicate_strategy(email, sid)

    @app.post("/api/builder/strategies/{sid}/export")
    async def api_builder_export(sid: str, email: str = ""):
        return export_strategy(email, sid)

    @app.post("/api/builder/import")
    async def api_builder_import(request: Request):
        body = await request.json()
        email = body.get("email", "")
        json_str = body.get("json", "")
        return import_strategy(email, json_str)

    @app.post("/api/builder/validate")
    async def api_builder_validate(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        valid, errors = validate_strategy(strategy)
        return {"valid": valid, "errors": errors}

import os as _osb
_bp = _osb.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "strategy_builder.html")

@app.get("/builder")
async def builder_page():
    from fastapi.responses import HTMLResponse
    if _osb.path.exists(_bp):
        with open(_bp, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Builder not found</h1>")
# ======= END STRATEGY BUILDER =======


# ======= BACKTEST ENGINE =======
try:
    from backend.api.backtest_engine import run_backtest
    BACKTEST_AVAILABLE = True
except ImportError:
    BACKTEST_AVAILABLE = False

if BACKTEST_AVAILABLE:

    @app.post("/api/backtest")
    async def api_run_backtest(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbol = strategy.get("symbol", "XAUUSD")
        timeframe = strategy.get("timeframe", "H1")
        bars = int(body.get("bars", 500))
        balance = float(body.get("balance", 10000))
        spread = float(body.get("spread", 2))

        if bars > 2000:
            bars = 2000
        if bars < 50:
            bars = 50

        # Fetch data from MT5
        try:
            from backend.mt5.mt5_connector import MT5Connector
            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}

            import MetaTrader5 as mt5
            tf_map = {
                "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
            }
            tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)

            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            if rates is None or len(rates) < 50:
                return {"success": False, "error": f"No data for {symbol} {timeframe}"}

            import pandas as pd
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

        except Exception as e:
            return {"success": False, "error": f"Data fetch error: {str(e)}"}

        # Run backtest
        try:
            result = run_backtest(df, strategy, initial_balance=balance, spread_pips=spread)
            return JSONResponse(content=sanitize(result))
        except Exception as e:
            return {"success": False, "error": f"Backtest error: {str(e)}"}
# ======= END BACKTEST =======


# ======= MQL CODE GENERATOR =======
try:
    from backend.api.mql5_generator import generate_mql5, generate_mql5_multi
    from backend.api.mql4_generator import generate_mql4, generate_mql4_multi
    MQL_GEN_AVAILABLE = True
except ImportError:
    MQL_GEN_AVAILABLE = False

if MQL_GEN_AVAILABLE:

    @app.post("/api/builder/generate-mql5")
    async def api_generate_mql5(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbols = body.get("symbols", [])
        if not strategy.get("name"):
            return {"success": False, "error": "Strategy name required"}
        try:
            if symbols and len(symbols) > 1:
                code = generate_mql5_multi(strategy, symbols)
                fname = strategy["name"] + "_Multi.mq5"
            else:
                code = generate_mql5(strategy)
                fname = strategy["name"] + ".mq5"
            return {"success": True, "code": code, "filename": fname}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/builder/generate-mql4")
    async def api_generate_mql4(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbols = body.get("symbols", [])
        if not strategy.get("name"):
            return {"success": False, "error": "Strategy name required"}
        try:
            if symbols and len(symbols) > 1:
                code = generate_mql4_multi(strategy, symbols)
                fname = strategy["name"] + "_Multi.mq4"
            else:
                code = generate_mql4(strategy)
                fname = strategy["name"] + ".mq4"
            return {"success": True, "code": code, "filename": fname}
        except Exception as e:
            return {"success": False, "error": str(e)}
# ======= END MQL GENERATOR =======


# ======= STRATEGY PREVIEW =======
try:
    from backend.api.strategy_preview import preview_strategy, compare_strategies
    PREVIEW_AVAILABLE = True
except ImportError:
    PREVIEW_AVAILABLE = False

if PREVIEW_AVAILABLE:

    @app.post("/api/builder/preview")
    async def api_preview(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbol = strategy.get("symbol", "XAUUSD")
        timeframe = strategy.get("timeframe", "H1")
        bars = int(body.get("bars", 200))
        if bars > 1000:
            bars = 1000

        try:
            from backend.mt5.mt5_connector import MT5Connector
            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}

            import MetaTrader5 as mt5
            import pandas as pd
            tf_map = {
                "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
            }
            tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            if rates is None or len(rates) < 30:
                return {"success": False, "error": f"No data for {symbol}"}
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
        except Exception as e:
            return {"success": False, "error": f"Data error: {str(e)}"}

        try:
            result = preview_strategy(df, strategy)
            return JSONResponse(content=sanitize(result))
        except Exception as e:
            return {"success": False, "error": f"Preview error: {str(e)}"}

    @app.post("/api/builder/compare")
    async def api_compare(request: Request):
        body = await request.json()
        s1 = body.get("strategy1", {})
        s2 = body.get("strategy2", {})
        symbol = s1.get("symbol", "XAUUSD")
        timeframe = s1.get("timeframe", "H1")

        try:
            from backend.mt5.mt5_connector import MT5Connector
            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}

            import MetaTrader5 as mt5
            import pandas as pd
            tf_map = {
                "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
            }
            tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, 500)
            if rates is None or len(rates) < 30:
                return {"success": False, "error": "No data"}
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
        except Exception as e:
            return {"success": False, "error": str(e)}

        try:
            result = compare_strategies(df, s1, s2)
            return JSONResponse(content=sanitize(result))
        except Exception as e:
            return {"success": False, "error": str(e)}
# ======= END PREVIEW =======


# ======= OPTIMIZER =======
try:
    from backend.api.optimizer import grid_search, walk_forward, monte_carlo, get_optimizable_params
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False

if OPTIMIZER_AVAILABLE:

    @app.post("/api/builder/optimize/params")
    async def api_opt_params(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        params = get_optimizable_params(strategy)
        return {"success": True, "params": params}

    @app.post("/api/builder/optimize/grid")
    async def api_opt_grid(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        selected = body.get("selected_params", None)
        symbol = strategy.get("symbol", "XAUUSD")
        timeframe = strategy.get("timeframe", "H1")
        bars = int(body.get("bars", 500))

        try:
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            import pandas as pd
            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}
            tf_map = {"M1":mt5.TIMEFRAME_M1,"M5":mt5.TIMEFRAME_M5,"M15":mt5.TIMEFRAME_M15,"M30":mt5.TIMEFRAME_M30,"H1":mt5.TIMEFRAME_H1,"H4":mt5.TIMEFRAME_H4,"D1":mt5.TIMEFRAME_D1,"W1":mt5.TIMEFRAME_W1}
            rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1), 0, min(bars, 1000))
            if rates is None or len(rates) < 50:
                return {"success": False, "error": "No data"}
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
        except Exception as e:
            return {"success": False, "error": str(e)}

        result = grid_search(df, strategy, selected, max_combos=200)
        return JSONResponse(content=sanitize(result))

    @app.post("/api/builder/optimize/walk-forward")
    async def api_opt_wf(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbol = strategy.get("symbol", "XAUUSD")
        timeframe = strategy.get("timeframe", "H1")
        windows = int(body.get("windows", 5))

        try:
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            import pandas as pd
            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}
            tf_map = {"M1":mt5.TIMEFRAME_M1,"M5":mt5.TIMEFRAME_M5,"M15":mt5.TIMEFRAME_M15,"M30":mt5.TIMEFRAME_M30,"H1":mt5.TIMEFRAME_H1,"H4":mt5.TIMEFRAME_H4,"D1":mt5.TIMEFRAME_D1,"W1":mt5.TIMEFRAME_W1}
            rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1), 0, 1000)
            if rates is None or len(rates) < 200:
                return {"success": False, "error": "Need 200+ bars"}
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
        except Exception as e:
            return {"success": False, "error": str(e)}

        result = walk_forward(df, strategy, windows)
        return JSONResponse(content=sanitize(result))

    @app.post("/api/builder/optimize/monte-carlo")
    async def api_opt_mc(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbol = strategy.get("symbol", "XAUUSD")
        timeframe = strategy.get("timeframe", "H1")
        sims = int(body.get("simulations", 500))

        try:
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            import pandas as pd
            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}
            tf_map = {"M1":mt5.TIMEFRAME_M1,"M5":mt5.TIMEFRAME_M5,"M15":mt5.TIMEFRAME_M15,"M30":mt5.TIMEFRAME_M30,"H1":mt5.TIMEFRAME_H1,"H4":mt5.TIMEFRAME_H4,"D1":mt5.TIMEFRAME_D1,"W1":mt5.TIMEFRAME_W1}
            rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1), 0, 500)
            if rates is None or len(rates) < 50:
                return {"success": False, "error": "No data"}
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
        except Exception as e:
            return {"success": False, "error": str(e)}

        result = monte_carlo(df, strategy, min(sims, 1000))
        return JSONResponse(content=sanitize(result))
# ======= END OPTIMIZER =======


# ======= TEMPLATES + MULTI-SYMBOL =======
try:
    from backend.api.strategy_templates import get_templates, get_template
    from backend.api.multi_symbol import multi_symbol_test, get_common_symbols
    TEMPLATES_AVAILABLE = True
except ImportError:
    TEMPLATES_AVAILABLE = False

if TEMPLATES_AVAILABLE:

    @app.get("/api/builder/templates")
    async def api_templates():
        return get_templates()

    @app.get("/api/builder/templates/{tid}")
    async def api_template_get(tid: str):
        t = get_template(tid)
        if t:
            return {"success": True, "template": t}
        return {"success": False, "error": "Template not found"}

    @app.get("/api/builder/symbols")
    async def api_common_symbols():
        return {"symbols": get_common_symbols()}

    @app.post("/api/builder/multi-test")
    async def api_multi_test(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbols = body.get("symbols", [])
        bars = int(body.get("bars", 500))
        balance = float(body.get("balance", 10000))
        spread = float(body.get("spread", 2))

        if not symbols:
            return {"success": False, "error": "No symbols selected"}
        if len(symbols) > 12:
            symbols = symbols[:12]

        result = multi_symbol_test(symbols, strategy, bars, balance, spread)
        return JSONResponse(content=sanitize(result))
# ======= END TEMPLATES =======


# ======= MONITOR + REPORTS =======
try:
    from backend.api.strategy_monitor import (
        add_monitor, remove_monitor, toggle_monitor,
        get_monitors, get_alerts as monitor_get_alerts, clear_alerts,
        run_monitor_check, get_alert_count, mark_alerts_read,
        check_strategy_signal,
    )
    from backend.api.report_generator import generate_report
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False

if MONITOR_AVAILABLE:

    @app.post("/api/builder/monitor/add")
    async def api_monitor_add(request: Request):
        body = await request.json()
        return add_monitor(body.get("email",""), body.get("strategy_id",""), body.get("strategy",{}))

    @app.delete("/api/builder/monitor/{sid}")
    async def api_monitor_del(sid: str, email: str = ""):
        return remove_monitor(email, sid)

    @app.post("/api/builder/monitor/{sid}/toggle")
    async def api_monitor_toggle(sid: str, email: str = ""):
        return toggle_monitor(email, sid)

    @app.get("/api/builder/monitors")
    async def api_monitors_list(email: str = ""):
        return {"monitors": get_monitors(email)}

    @app.get("/api/builder/alerts")
    async def api_alerts_list(email: str = ""):
        return {"alerts": monitor_get_alerts(email)}

    @app.get("/api/builder/alerts/count")
    async def api_alert_count(email: str = ""):
        return {"count": get_alert_count(email)}

    @app.post("/api/builder/alerts/read")
    async def api_alerts_read(request: Request):
        body = await request.json()
        return mark_alerts_read(body.get("email",""))

    @app.post("/api/builder/alerts/clear")
    async def api_alerts_clear(request: Request):
        body = await request.json()
        return clear_alerts(body.get("email",""))

    @app.post("/api/builder/check-signal")
    async def api_check_signal(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbol = strategy.get("symbol", "XAUUSD")
        timeframe = strategy.get("timeframe", "H1")
        try:
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            import pandas as pd
            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}
            tf_map = {"M1":mt5.TIMEFRAME_M1,"M5":mt5.TIMEFRAME_M5,"M15":mt5.TIMEFRAME_M15,"M30":mt5.TIMEFRAME_M30,"H1":mt5.TIMEFRAME_H1,"H4":mt5.TIMEFRAME_H4,"D1":mt5.TIMEFRAME_D1,"W1":mt5.TIMEFRAME_W1}
            rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1), 0, 100)
            if rates is None or len(rates) < 10:
                return {"success": False, "error": "No data"}
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            result = check_strategy_signal(df, strategy)
            return JSONResponse(content=sanitize({"success": True, **result}))
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/builder/monitor/check-all")
    async def api_monitor_checkall():
        alerts = run_monitor_check()
        return {"success": True, "new_alerts": len(alerts)}

    @app.post("/api/builder/report")
    async def api_generate_report(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        bt_result = body.get("backtest_result", {})
        if not strategy.get("name"):
            return {"success": False, "error": "No strategy"}
        html = generate_report(strategy, bt_result)
        return {"success": True, "html": html, "filename": strategy["name"] + "_report.html"}

    @app.get("/api/builder/dashboard-widget")
    async def api_dashboard_widget(email: str = ""):
        from backend.api.strategy_store import get_strategies
        strategies = get_strategies(email)
        monitors = get_monitors(email)
        alert_count = get_alert_count(email)
        active_monitors = sum(1 for m in monitors if m.get("active"))
        return {
            "total_strategies": len(strategies),
            "active_monitors": active_monitors,
            "unread_alerts": alert_count,
            "recent_strategies": [{"name": s.get("name",""), "symbol": s.get("symbol",""), "id": s.get("id","")} for s in strategies[:5]],
        }
# ======= END MONITOR =======


# ======= TRADE JOURNAL =======
try:
    from backend.api.trade_journal import (
        add_entry, update_entry, delete_entry,
        get_entries, get_entry, add_daily_note,
        get_daily_notes, get_journal_analytics,
        get_journal_config, generate_recommendations,
        export_entries,
    )
    JOURNAL_AVAILABLE = True
except ImportError:
    JOURNAL_AVAILABLE = False

if JOURNAL_AVAILABLE:

    @app.get("/api/journal/config")
    async def api_journal_config():
        return get_journal_config()

    @app.get("/api/journal/entries")
    async def api_journal_list(email: str = "", limit: int = 100, symbol: str = None, strategy: str = None):
        return {"entries": get_entries(email, limit, symbol, strategy)}

    @app.get("/api/journal/entries/{eid}")
    async def api_journal_get(eid: str, email: str = ""):
        e = get_entry(email, eid)
        return e if e else {"error": "not found"}

    @app.post("/api/journal/entries")
    async def api_journal_add(request: Request, authorization: str = Header(None)):
        body = await request.json()
        email = body.get("email", "")
        # Plan limit enforcement
        if _PLANS_OK and email:
            _uid, _em, plan = _resolve_plan_from_auth(authorization)
            existing = get_entries(email, limit=99999)
            current_count = len(existing) if isinstance(existing, list) else 0
            allowed, remaining, limit = check_journal_limit(plan, current_count)
            if not allowed:
                raise HTTPException(403, detail={
                    "error": f"سقف ژورنال ({limit} ورودی) در پلن {PLAN_NAMES_FA.get(plan, 'رایگان')} پر شده است",
                    "error_code": "journal_limit_reached",
                    "upgrade_url": "/pricing",
                    "limit": limit,
                    "used": current_count,
                })
        return add_entry(email, body.get("entry", {}))

    @app.put("/api/journal/entries/{eid}")
    async def api_journal_update(eid: str, request: Request):
        body = await request.json()
        return update_entry(body.get("email",""), eid, body.get("updates",{}))

    @app.delete("/api/journal/entries/{eid}")
    async def api_journal_delete(eid: str, email: str = ""):
        return delete_entry(email, eid)

    @app.get("/api/journal/analytics")
    async def api_journal_analytics(email: str = ""):
        return get_journal_analytics(email)

    @app.post("/api/journal/daily-note")
    async def api_daily_note(request: Request):
        body = await request.json()
        return add_daily_note(body.get("email",""), body.get("date",""), body.get("note",""))

    @app.get("/api/journal/daily-notes")
    async def api_daily_notes(email: str = ""):
        return {"notes": get_daily_notes(email)}

    @app.post("/api/journal/recommend")
    async def api_journal_recommend(request: Request):
        body = await request.json()
        entry = body.get("entry", {})
        email = body.get("email", "")
        analytics = get_journal_analytics(email) if email else None
        recs = generate_recommendations(entry, analytics)
        return {"recommendations": recs}

    @app.get("/api/journal/export")
    async def api_journal_export(email: str = "", format: str = "json"):
        from fastapi.responses import PlainTextResponse
        data = export_entries(email, format)
        if format == "csv":
            return PlainTextResponse(content=data, media_type="text/csv",
                                     headers={"Content-Disposition": "attachment; filename=journal_export.csv"})
        return PlainTextResponse(content=data, media_type="application/json",
                                 headers={"Content-Disposition": "attachment; filename=journal_export.json"})

    @app.post("/api/journal/import-live")
    async def api_journal_import_live(request: Request):
        """Import a trade from live tracking into journal."""
        body = await request.json()
        email = body.get("email", "")
        trade = body.get("trade", {})
        entry = {
            "symbol": trade.get("symbol", "XAUUSD"),
            "type": trade.get("direction", "BUY"),
            "entry_price": trade.get("entry_price", 0),
            "exit_price": trade.get("exit_price", 0),
            "tp_price": trade.get("tp1", trade.get("tp_price", 0)),
            "sl_price": trade.get("sl", trade.get("sl_price", 0)),
            "lot_size": trade.get("lot_size", trade.get("lots", 0.01)),
            "pnl": trade.get("pnl_usd", trade.get("pnl", 0)),
            "pnl_pips": trade.get("pnl_pips", 0),
            "strategy_name": trade.get("strategy", trade.get("strategy_name", "")),
            "timeframe": trade.get("timeframe", "H1"),
            "notes": f"وارد شده از معامله لایو — {trade.get('symbol','')} {trade.get('direction','')}",
            "tags": ["imported"],
        }
        return add_entry(email, entry)

import os as _osj
_jp = _osj.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "journal.html")

@app.get("/journal")
async def journal_page():
    from fastapi.responses import HTMLResponse
    if _osj.path.exists(_jp):
        with open(_jp, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Journal not found</h1>")
# ======= END JOURNAL =======


# ======= ADVANCED ANALYTICS =======
try:
    from backend.api.advanced_analytics import compute_advanced_analytics
    ADVANCED_ANALYTICS_AVAILABLE = True
except ImportError:
    ADVANCED_ANALYTICS_AVAILABLE = False

if ADVANCED_ANALYTICS_AVAILABLE:

    @app.post("/api/builder/advanced-analytics")
    async def api_advanced_analytics(request: Request):
        body = await request.json()
        strategy = body.get("strategy", {})
        symbol = strategy.get("symbol", "XAUUSD")
        timeframe = strategy.get("timeframe", "H1")
        bars = int(body.get("bars", 500))

        try:
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            import pandas as pd
            from backend.api.backtest_engine import run_backtest

            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}
            tf_map = {"M1":mt5.TIMEFRAME_M1,"M5":mt5.TIMEFRAME_M5,"M15":mt5.TIMEFRAME_M15,"M30":mt5.TIMEFRAME_M30,"H1":mt5.TIMEFRAME_H1,"H4":mt5.TIMEFRAME_H4,"D1":mt5.TIMEFRAME_D1,"W1":mt5.TIMEFRAME_W1}
            rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1), 0, min(bars, 2000))
            if rates is None or len(rates) < 50:
                return {"success": False, "error": "No data"}
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            bt = run_backtest(df, strategy, initial_balance=10000, spread_pips=2)
            if not bt.get("success"):
                return {"success": False, "error": bt.get("error", "Backtest failed")}

            result = compute_advanced_analytics(bt, strategy)
            return JSONResponse(content=sanitize(result))
        except Exception as e:
            return {"success": False, "error": str(e)}
# ======= END ADVANCED ANALYTICS =======


# ======= RISK MANAGER =======
try:
    from backend.api.risk_engine import (
        save_profile, load_profile, apply_preset,
        calculate_trade, generate_trade_report,
        get_risk_config, suggest_entry_levels,
        calculate_pip_pnl,
    )
    RISK_MANAGER_AVAILABLE = True
except ImportError:
    RISK_MANAGER_AVAILABLE = False

if RISK_MANAGER_AVAILABLE:

    @app.get("/api/risk/config")
    async def api_risk_config():
        return get_risk_config()

    @app.get("/api/risk/profile")
    async def api_risk_profile(email: str = ""):
        p = load_profile(email)
        if p:
            return {"success": True, "profile": p}
        return {"success": True, "profile": None}

    @app.post("/api/risk/profile")
    async def api_risk_save_profile(request: Request):
        body = await request.json()
        return save_profile(body.get("email", ""), body.get("profile", {}))

    @app.post("/api/risk/preset")
    async def api_risk_preset(request: Request):
        body = await request.json()
        return apply_preset(body.get("email", ""), body.get("preset", "moderate"))

    @app.post("/api/risk/calculate")
    async def api_risk_calculate(request: Request):
        body = await request.json()
        email = body.get("email", "")
        profile = body.get("profile") or load_profile(email) or {}
        trade = body.get("trade", {})

        # If symbol has live price, use it
        if not trade.get("entry_price") and trade.get("symbol"):
            try:
                from backend.mt5.mt5_connector import MT5Connector
                import MetaTrader5 as mt5
                connector = MT5Connector.get_instance()
                if connector.ensure_connected():
                    tick = mt5.symbol_info_tick(trade["symbol"])
                    if tick:
                        trade["entry_price"] = tick.ask if trade.get("direction") == "BUY" else tick.bid
            except Exception:
                pass

        result = calculate_trade(profile, trade)
        return JSONResponse(content=sanitize(result))

    @app.post("/api/risk/report")
    async def api_risk_report(request: Request):
        body = await request.json()
        email = body.get("email", "")
        profile = body.get("profile") or load_profile(email) or {}
        trade_input = body.get("trade_input", {})
        trade_result = body.get("trade_result", {})
        report = generate_trade_report(profile, trade_input, trade_result)
        return JSONResponse(content=sanitize(report))

    @app.post("/api/risk/suggest-entry")
    async def api_risk_suggest_entry(request: Request):
        body = await request.json()
        symbol = body.get("symbol", "XAUUSD")
        direction = body.get("direction", "BUY")
        result = suggest_entry_levels(symbol, direction)
        return JSONResponse(content=sanitize(result))

    @app.post("/api/risk/pip-calculator")
    async def api_risk_pip_calculator(request: Request):
        body = await request.json()
        result = calculate_pip_pnl(
            symbol=body.get("symbol", "XAUUSD"),
            direction=body.get("direction", "BUY"),
            entry_price=body.get("entry_price", 0),
            exit_price=body.get("exit_price", 0),
            lot_size=body.get("lot_size", 0.01),
            slippage_pips=body.get("slippage_pips", 0),
            commission_per_lot=body.get("commission_per_lot", 0),
        )
        return JSONResponse(content=sanitize(result))

    @app.post("/api/risk/live-price")
    async def api_risk_live_price(request: Request):
        body = await request.json()
        symbol = body.get("symbol", "XAUUSD")
        try:
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                return {"success": False, "error": "MT5 not connected"}
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return {"success": True, "bid": tick.bid, "ask": tick.ask, "spread": round((tick.ask - tick.bid), 6), "time": str(tick.time)}
            return {"success": False, "error": "No tick data"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    import os as _osr
    _rp = _osr.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "risk_manager.html")

    @app.get("/risk-manager")
    async def risk_manager_page():
        from fastapi.responses import HTMLResponse
        if _osr.path.exists(_rp):
            with open(_rp, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>Risk Manager not found</h1>")
# ======= END RISK MANAGER =======


# ======= LIVE TRADE MANAGER =======
try:
    from backend.api.live_manager import (
        open_trade, close_trade, get_active_trades, get_trade_history,
        update_trade_sl, record_partial_close, calculate_live,
    )
    LIVE_MANAGER_AVAILABLE = True
except ImportError:
    LIVE_MANAGER_AVAILABLE = False

if LIVE_MANAGER_AVAILABLE:

    @app.post("/api/risk/trade/open")
    async def api_trade_open(request: Request):
        body = await request.json()
        return open_trade(body.get("email",""), body.get("trade",{}))

    @app.post("/api/risk/trade/close")
    async def api_trade_close(request: Request):
        body = await request.json()
        return close_trade(body.get("email",""), body.get("trade_id",""), body.get("exit_price",0), body.get("exit_reason","manual"))

    @app.get("/api/risk/trade/active")
    async def api_trade_active(email: str = ""):
        return {"trades": get_active_trades(email)}

    @app.get("/api/risk/trade/history")
    async def api_trade_history(email: str = "", limit: int = 50):
        return {"trades": get_trade_history(email, limit)}

    @app.post("/api/risk/trade/update-sl")
    async def api_trade_update_sl(request: Request):
        body = await request.json()
        return update_trade_sl(body.get("email",""), body.get("trade_id",""), body.get("new_sl",0))

    @app.post("/api/risk/trade/partial-close")
    async def api_trade_partial(request: Request):
        body = await request.json()
        return record_partial_close(body.get("email",""), body.get("trade_id",""), body.get("pct",0), body.get("price",0))

    @app.post("/api/risk/trade/live")
    async def api_trade_live(request: Request):
        body = await request.json()
        trade = body.get("trade", {})
        symbol = trade.get("symbol", "XAUUSD")

        # Get current price from MT5
        current_price = body.get("current_price", 0)
        if not current_price:
            try:
                from backend.mt5.mt5_connector import MT5Connector
                import MetaTrader5 as mt5
                connector = MT5Connector.get_instance()
                if connector.ensure_connected():
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        current_price = tick.bid if trade.get("direction") == "SELL" else tick.ask
            except Exception:
                pass

        if not current_price:
            return {"success": False, "error": "No price data"}

        result = calculate_live(trade, current_price)

        # Dispatch Telegram alert if triggered
        if result.get("should_alert") and result.get("alert_type"):
            try:
                from backend.api.alert_dispatcher import dispatch_event
                dispatch_event("risk_alert", {
                    "symbol": symbol,
                    "alert_type": result["alert_type"],
                    "status_fa": result.get("status_fa", ""),
                    "pnl_pips": result.get("pnl_pips", 0),
                    "pnl_usd": result.get("pnl_usd", 0),
                    "current_price": current_price,
                })
            except Exception:
                pass

        return JSONResponse(content=sanitize({"success": True, **result}))

    @app.post("/api/risk/trade/live-multi")
    async def api_trade_live_multi(request: Request):
        body = await request.json()
        email = body.get("email", "")
        trades = get_active_trades(email)
        results = []

        for trade in trades:
            symbol = trade.get("symbol", "XAUUSD")
            try:
                from backend.mt5.mt5_connector import MT5Connector
                import MetaTrader5 as mt5
                connector = MT5Connector.get_instance()
                if connector.ensure_connected():
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        cp = tick.bid if trade.get("direction") == "SELL" else tick.ask
                        live = calculate_live(trade, cp)
                        results.append({"trade_id": trade["id"], "success": True, **live})
                    else:
                        results.append({"trade_id": trade["id"], "success": False, "error": "No tick"})
                else:
                    results.append({"trade_id": trade["id"], "success": False, "error": "MT5 disconnected"})
            except Exception as e:
                results.append({"trade_id": trade["id"], "success": False, "error": str(e)})

        return JSONResponse(content=sanitize({"success": True, "results": results}))

    # Dashboard integration: quick manage from strategy signal
    @app.post("/api/risk/from-strategy")
    async def api_risk_from_strategy(request: Request):
        body = await request.json()
        email = body.get("email", "")
        strategy_name = body.get("strategy_name", "")
        symbol = body.get("symbol", "XAUUSD")
        signal_type = body.get("signal_type", "BUY")
        tp_price = body.get("tp", 0)
        sl_price = body.get("sl", 0)
        entry_price = body.get("entry", 0)

        if not entry_price:
            try:
                from backend.mt5.mt5_connector import MT5Connector
                import MetaTrader5 as mt5
                connector = MT5Connector.get_instance()
                if connector.ensure_connected():
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        entry_price = tick.ask if signal_type == "BUY" else tick.bid
            except Exception:
                pass

        profile = None
        try:
            from backend.api.risk_engine import load_profile, calculate_trade
            profile = load_profile(email)
        except Exception:
            pass

        if not profile:
            profile = {"balance": 10000, "risk_pct": 2.0, "leverage": 100, "max_daily_dd_pct": 5.0}

        trade_input = {
            "symbol": symbol,
            "direction": signal_type,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
        }

        try:
            from backend.api.risk_engine import calculate_trade
            result = calculate_trade(profile, trade_input)
            result["strategy_name"] = strategy_name
            return JSONResponse(content=sanitize(result))
        except Exception as e:
            return {"success": False, "error": str(e)}
# ======= END LIVE MANAGER =======


# ======= PROFIT + TRAILING + REPORT =======
try:
    from backend.api.profit_trailing_engine import (
        get_profit_trailing_config, calculate_profit_plan,
        calculate_trailing, recommend_for_market,
        generate_full_report,
    )
    PROFIT_TRAIL_AVAILABLE = True
except ImportError:
    PROFIT_TRAIL_AVAILABLE = False

if PROFIT_TRAIL_AVAILABLE:

    @app.get("/api/risk/profit-trailing-config")
    async def api_pt_config():
        return get_profit_trailing_config()

    @app.post("/api/risk/profit-plan")
    async def api_profit_plan(request: Request):
        body = await request.json()
        return calculate_profit_plan(body.get("trade",{}), body.get("method","half_rr1"), body.get("params",{}))

    @app.post("/api/risk/trailing-calc")
    async def api_trailing_calc(request: Request):
        body = await request.json()
        return calculate_trailing(body.get("trade",{}), body.get("model","fixed"), body.get("params",{}), body.get("current_price"), body.get("highest_price"))

    @app.post("/api/risk/recommend")
    async def api_recommend(request: Request):
        body = await request.json()
        return recommend_for_market(body.get("symbol","XAUUSD"), float(body.get("sl_pips",50)), float(body.get("tp_pips",100)))

    @app.post("/api/risk/trade-report")
    async def api_trade_report(request: Request):
        body = await request.json()
        return generate_full_report(
            body.get("trade_input",{}),
            body.get("trade_result",{}),
            body.get("profit_method"),
            body.get("trailing_model"),
        )
# ======= END PROFIT + TRAILING =======


# ======= PORTFOLIO + ALERTS =======
try:
    from backend.api.portfolio_engine import (
        calculate_risk_score, add_price_alert, check_price_alerts,
        auto_create_trade_alerts, get_risk_alerts, get_active_price_alerts,
        clear_risk_alerts, mark_risk_alerts_read, get_unread_count,
        portfolio_summary,
    )
    PORTFOLIO_AVAILABLE = True
except ImportError:
    PORTFOLIO_AVAILABLE = False

if PORTFOLIO_AVAILABLE:

    @app.post("/api/risk/portfolio")
    async def api_portfolio(request: Request):
        body = await request.json()
        email = body.get("email", "")
        try:
            from backend.api.risk_engine import load_profile
            from backend.api.live_manager import get_active_trades
            profile = load_profile(email) or {"balance":10000,"risk_pct":2,"max_daily_dd_pct":5,"max_open_trades":3}
            trades = get_active_trades(email)
            prices = {}
            try:
                from backend.mt5.mt5_connector import MT5Connector
                import MetaTrader5 as mt5
                connector = MT5Connector.get_instance()
                if connector.ensure_connected():
                    for t in trades:
                        sym = t.get("symbol","XAUUSD")
                        if sym not in prices:
                            tick = mt5.symbol_info_tick(sym)
                            if tick:
                                prices[sym] = tick.bid
            except Exception:
                pass
            result = portfolio_summary(profile, trades, prices)
            return JSONResponse(content=sanitize(result))
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/risk/score")
    async def api_risk_score(request: Request):
        body = await request.json()
        email = body.get("email", "")
        try:
            from backend.api.risk_engine import load_profile
            from backend.api.live_manager import get_active_trades
            profile = load_profile(email) or {"balance":10000,"risk_pct":2,"max_daily_dd_pct":5,"max_open_trades":3}
            trades = get_active_trades(email)
            prices = {}
            try:
                from backend.mt5.mt5_connector import MT5Connector
                import MetaTrader5 as mt5
                connector = MT5Connector.get_instance()
                if connector.ensure_connected():
                    for t in trades:
                        sym = t.get("symbol","XAUUSD")
                        if sym not in prices:
                            tick = mt5.symbol_info_tick(sym)
                            if tick: prices[sym] = tick.bid
            except Exception:
                pass
            result = calculate_risk_score(profile, trades, prices)
            return JSONResponse(content=sanitize(result))
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/risk/alert/add")
    async def api_add_alert(request: Request):
        body = await request.json()
        return add_price_alert(body.get("email",""), body.get("alert",{}))

    @app.post("/api/risk/alert/auto-create")
    async def api_auto_alerts(request: Request):
        body = await request.json()
        return auto_create_trade_alerts(body.get("email",""), body.get("trade",{}))

    @app.post("/api/risk/alert/check")
    async def api_check_alerts(request: Request):
        body = await request.json()
        email = body.get("email","")
        prices = {}
        try:
            from backend.api.live_manager import get_active_trades
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            trades = get_active_trades(email)
            connector = MT5Connector.get_instance()
            if connector.ensure_connected():
                for t in trades:
                    sym = t.get("symbol","XAUUSD")
                    if sym not in prices:
                        tick = mt5.symbol_info_tick(sym)
                        if tick: prices[sym] = tick.bid
        except Exception:
            pass
        triggered = check_price_alerts(email, prices)
        return {"success": True, "triggered": len(triggered), "alerts": triggered}

    @app.get("/api/risk/alerts")
    async def api_risk_alerts(email: str = ""):
        return {"alerts": get_risk_alerts(email)}

    @app.get("/api/risk/alerts/active")
    async def api_active_alerts(email: str = ""):
        return {"alerts": get_active_price_alerts(email)}

    @app.get("/api/risk/alerts/unread")
    async def api_unread_alerts(email: str = ""):
        return {"count": get_unread_count(email)}

    @app.post("/api/risk/alerts/read")
    async def api_mark_read_ra(request: Request):
        body = await request.json()
        return mark_risk_alerts_read(body.get("email",""))

    @app.post("/api/risk/alerts/clear")
    async def api_clear_ra(request: Request):
        body = await request.json()
        return clear_risk_alerts(body.get("email",""))
# ======= END PORTFOLIO =======


# ======= AUTO SIGNAL TRACKER =======
try:
    from backend.api.tracker_engine import (
        get_tracker_status, get_active_tracked, get_strategy_records,
        get_all_strategy_ids, load_records, record_entry, record_exit,
    )
    from backend.api.tracker_daemon import start_tracker, stop_tracker, is_running
    TRACKER_AVAILABLE = True
except ImportError:
    TRACKER_AVAILABLE = False

if TRACKER_AVAILABLE:

# [DISABLED - slow status, replaced with fast version]
#     @app.get("/api/tracker/status")
#     async def api_tracker_status():
#         return get_tracker_status()
# 
    @app.post("/api/tracker/start")
    async def api_tracker_start():
        return start_tracker()

    @app.post("/api/tracker/stop")
    async def api_tracker_stop():
        return stop_tracker()

    @app.get("/api/tracker/active")
    async def api_tracker_active():
        return {"trades": get_active_tracked()}

    @app.get("/api/tracker/active-live")
    async def _tracker_active_live():
        """Real-time active trades for live panel — matches frontend exactly."""
        import json as _json
        from collections import Counter as _Ctr
        from datetime import datetime as _dt, timezone as _tz
        _af = os.path.join(r"C:\Users\Administrator\Desktop\mvp\track_records", "active_tracks.json")
        try:
            with open(_af, "r", encoding="utf-8") as _ff:
                _raw = _json.load(_ff)
            _active = _raw.get("active", []) if isinstance(_raw, dict) else []
        except:
            _active = []

        _ps = {"XAUUSD":0.1,"XAGUSD":0.01,"USDJPY":0.01,"NAS100":1.0,"US30":1.0,"BTCUSD":1.0}
        _enriched = []
        _near_tp = 0

        for _t in _active:
            _tr = dict(_t)
            _sym = _tr.get("symbol", "")
            _dir = _tr.get("direction", "BUY")
            _entry = _tr.get("entry_price", 0)
            _sl = _tr.get("sl_price", 0)
            _pip = _ps.get(_sym, 0.0001)

            # tp_price (frontend expects tp_price, data has tp1_price)
            _tr["tp_price"] = _tr.get("tp_price") or _tr.get("tp1_price") or _tr.get("tp2_price") or 0
            _tp = _tr["tp_price"]

            # confidence (from signal confidence or default 70)
            _tr["confidence"] = _tr.get("confidence") or _tr.get("signal_confidence") or 70

            # rr_ratio
            if _entry and _sl and _tp and _sl != _entry:
                if _dir == "BUY":
                    _risk = abs(_entry - _sl)
                    _reward = abs(_tp - _entry)
                else:
                    _risk = abs(_sl - _entry)
                    _reward = abs(_entry - _tp)
                _tr["rr_ratio"] = round(_reward / _risk, 1) if _risk > 0 else 0
            else:
                _tr["rr_ratio"] = 0

            # duration (time since opened)
            _opened = _tr.get("opened_at", "")
            if _opened:
                try:
                    _ot = _dt.fromisoformat(_opened.replace("Z", "+00:00"))
                    _now = _dt.now(_tz.utc)
                    _mins = int((_now - _ot).total_seconds() / 60)
                    if _mins < 60:
                        _tr["duration"] = f"{_mins}m"
                    elif _mins < 1440:
                        _tr["duration"] = f"{_mins // 60}h {_mins % 60}m"
                    else:
                        _tr["duration"] = f"{_mins // 1440}d {(_mins % 1440) // 60}h"
                except:
                    _tr["duration"] = ""
            else:
                _tr["duration"] = ""

            # Live PnL — use MT5 tick directly
            try:
                import MetaTrader5 as _mt5
                _sym_map = {"XAUUSD":"XAUUSD+","XAGUSD":"XAGUSD+","EURUSD":"EURUSD+","GBPUSD":"GBPUSD+","USDJPY":"USDJPY+","AUDUSD":"AUDUSD+","USDCAD":"USDCAD+","NZDUSD":"NZDUSD+","USDCHF":"USDCHF+","BTCUSD":"BTCUSD","NAS100":"NAS100","US30":"DJ30"}
                _tick = _mt5.symbol_info_tick(_sym_map.get(_sym, _sym))
                _price = _tick.bid if _tick else 0
                if _price and _entry:
                    if _dir == "BUY":
                        _pnl = round((_price - _entry) / _pip, 1)
                    else:
                        _pnl = round((_entry - _price) / _pip, 1)
                    _tr["current_pnl_pips"] = _pnl
                    _tr["current_price"] = _price

                    # Check near TP
                    if _tp and _price:
                        _dist_tp = abs(_tp - _price) / _pip
                        _dist_entry = abs(_entry - _price) / _pip
                        if _dist_entry > 0 and _dist_tp < _dist_entry * 0.3:
                            _near_tp += 1
                else:
                    _pnl = 0
                    _tr["current_pnl_pips"] = 0
            except:
                _pnl = 0
                _tr["current_pnl_pips"] = 0

            # Status labels
            if _pnl > 0:
                _tr["status_label"] = "در سود"
                _tr["status_color"] = "#00d4aa"
            elif _pnl < 0:
                _tr["status_label"] = "در ضرر"
                _tr["status_color"] = "#ff6b35"
            else:
                _tr["status_label"] = "سربه‌سر"
                _tr["status_color"] = "#888"

            _enriched.append(_tr)

        # Stats — frontend uses st.buy, st.sell (NOT buy_count/sell_count)
        _dirs = _Ctr(_t.get("direction", "") for _t in _enriched)
        _stats = {
            "buy": _dirs.get("BUY", 0),
            "sell": _dirs.get("SELL", 0),
            "trailing": 0,
            "break_even": sum(1 for _t in _enriched if _t.get("current_pnl_pips", 0) == 0),
            "near_tp": _near_tp,
        }

        return {"trades": _enriched, "stats": _stats, "count": len(_enriched)}

    @app.get("/api/tracker/strategies")
    async def api_tracker_strategies():
        return {"strategy_ids": get_all_strategy_ids()}

    @app.get("/api/tracker/records/{sid}")
    async def api_tracker_records(sid: str):
        return get_strategy_records(sid)

    @app.get("/api/tracker/records/{sid}/stats")
    async def api_tracker_stats(sid: str):
        rec = load_records(sid)
        trades = rec.get("trades", [])
        if not trades:
            return {"total": 0}
        wins = [t for t in trades if t.get("outcome") == "win"]
        losses = [t for t in trades if t.get("outcome") == "loss"]
        pnls = [t.get("pnl_usd", 0) for t in trades]
        total_pnl = sum(pnls)
        return {
            "total": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / len(trades), 2) if trades else 0,
            "best": round(max(pnls), 2) if pnls else 0,
            "worst": round(min(pnls), 2) if pnls else 0,
            "avg_duration": round(sum(t.get("duration_minutes", 0) for t in trades) / len(trades), 1) if trades else 0,
            "last_trade": trades[0].get("closed_at", "") if trades else "",
        }

# [DISABLED - slow, use /api/fast/summary or redirect]
#     @app.get("/api/tracker/summary")
#     async def api_tracker_summary():
#         sids = get_all_strategy_ids()
#         summary = []
#         for sid in sids:
#             rec = load_records(sid)
#             trades = rec.get("trades", [])
#             if not trades:
#                 continue
#             wins = sum(1 for t in trades if t.get("outcome") == "win")
#             total_pnl = sum(t.get("pnl_usd", 0) for t in trades)
#             name = trades[0].get("strategy_name", sid) if trades else sid
#             category = trades[0].get("category", "") if trades else ""
#             symbol = trades[0].get("symbol", "") if trades else ""
#             summary.append({
#                 "strategy_id": sid,
#                 "strategy_name": name,
#                 "category": category,
#                 "symbol": symbol,
#                 "total": len(trades),
#                 "wins": wins,
#                 "win_rate": round(wins / len(trades) * 100, 1),
#                 "total_pnl": round(total_pnl, 2),
#                 "last_trade": trades[0].get("closed_at", ""),
#             })
#         summary.sort(key=lambda x: x["win_rate"], reverse=True)
#         return {"strategies": summary, "total_strategies": len(summary)}
# 
#     # Auto-start tracker on server boot
#     import threading
#     def _auto_start():
#         import time
#         time.sleep(300)  # was 5, increased to reduce CPU
#         try:
#             pass  # start_tracker()
#             print("[TRACKER] Auto-started on server boot")
#         except Exception as e:
#             print(f"[TRACKER] Auto-start failed: {e}")
#     pass  # threading.Thread(target=_auto_start, daemon=True).start()  # was blocking GIL
# # ======= END TRACKER =======
# 
# 
# # ======= LIFECYCLE + STATS =======
try:
    from backend.api.lifecycle_manager import (
        compute_strategy_stats, compute_category_comparison,
        get_trade_timeline, STAGES,
    )
    LIFECYCLE_AVAILABLE = True
except ImportError:
    LIFECYCLE_AVAILABLE = False

if LIFECYCLE_AVAILABLE:

    @app.get("/api/tracker/stats/{sid}")
    async def api_lifecycle_stats(sid: str):
        return compute_strategy_stats(sid)

    @app.get("/api/tracker/timeline/{sid}/{trade_id}")
    async def api_trade_timeline(sid: str, trade_id: str):
        return get_trade_timeline(sid, trade_id)

    @app.get("/api/tracker/compare")
    async def api_category_compare():
        return compute_category_comparison()

    @app.get("/api/tracker/stages")
    async def api_stages():
        return {"stages": {k: {"icon": v["icon"], "fa": v["fa"]} for k, v in STAGES.items()}}

# [DISABLED - slow, use /api/fast/ranking or redirect]
#     @app.get("/api/tracker/ranking")
#     async def api_strategy_ranking(sort: str = "win_rate", limit: int = 20):
#         try:
#             from backend.api.tracker_engine import get_all_strategy_ids
#         except ImportError:
#             return {"ranking": []}
#         sids = get_all_strategy_ids()
#         results = []
#         for sid in sids:
#             try:
#                 stats = compute_strategy_stats(sid)
#                 if stats.get("total", 0) >= 3:
#                     results.append(stats)
#             except Exception:
#                 continue
#         valid_sorts = ["win_rate", "total_pnl", "profit_factor", "total"]
#         if sort not in valid_sorts:
#             sort = "win_rate"
#         results.sort(key=lambda x: x.get(sort, 0), reverse=True)
#         return {"ranking": results[:limit], "sort_by": sort, "total": len(results)}
# 
    @app.get("/api/tracker/signal-history/{sid}")
    async def api_signal_history(sid: str, limit: int = 20):
        try:
            from backend.api.tracker_engine import load_records
        except ImportError:
            return {"trades": []}
        rec = load_records(sid)
        trades = rec.get("trades", [])[:limit]
        history = []
        for t in trades:
            history.append({
                "id": t.get("id", ""),
                "symbol": t.get("symbol", ""),
                "direction": t.get("direction", ""),
                "entry_price": t.get("entry_price", 0),
                "exit_price": t.get("exit_price", 0),
                "sl_price": t.get("sl_price", 0),
                "tp1_price": t.get("tp1_price", 0),
                "pnl_pips": t.get("pnl_pips", 0),
                "pnl_usd": t.get("pnl_usd", 0),
                "outcome": t.get("outcome", ""),
                "exit_reason": t.get("exit_reason", ""),
                "duration_minutes": t.get("duration_minutes", 0),
                "opened_at": t.get("opened_at", ""),
                "closed_at": t.get("closed_at", ""),
                "events_count": len(t.get("events", [])),
                "sl_moved_to_be": t.get("sl_moved_to_be", False),
                "trailing_active": t.get("trailing_active", False),
                "partial_closes": len(t.get("partial_closes", [])),
            })
        return {"strategy_id": sid, "trades": history, "total": len(rec.get("trades", []))}
# ======= END LIFECYCLE =======


# ======= TRACK RECORD PAGE =======
import os as _ostr
_trp = _ostr.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "track_record.html")

@app.get("/track-record")
async def track_record_page():
    from fastapi.responses import HTMLResponse
    if _ostr.path.exists(_trp):
        with open(_trp, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Track Record not found</h1>")
# ======= END TRACK RECORD =======


# ======= FILTER + COMPARE + EXPORT =======
try:
    from backend.api.filter_export_engine import (
        filter_trades, compare_strategies, performance_heatmap,
        export_csv, export_html_report, get_filter_options,
    )
    FILTER_EXPORT_AVAILABLE = True
except ImportError:
    FILTER_EXPORT_AVAILABLE = False

if FILTER_EXPORT_AVAILABLE:

# [DISABLED - slow, redirected to fast version]
#     @app.get("/api/tracker/filter-options")
#     async def api_filter_options():
#         return get_filter_options()
# 
# # [REPLACED — now uses get_real_trades]
# #     @app.post("/api/tracker/filter")
# #     async def api_filter_trades(request: Request):
# #         body = await request.json()
# #         result = filter_trades(body.get("filters", {}))
# #         result["trades"] = result.get("trades", [])[:200]
# #         return JSONResponse(content=sanitize(result))
# # 
    @app.post("/api/tracker/compare-strategies")
    async def api_compare(request: Request):
        body = await request.json()
        return JSONResponse(content=sanitize(compare_strategies(body.get("strategy_ids", []))))

    @app.post("/api/tracker/heatmap")
    async def api_heatmap(request: Request):
        body = await request.json()
        return performance_heatmap(body.get("filters"))

    @app.post("/api/tracker/export/csv")
    async def api_export_csv(request: Request):
        body = await request.json()
        result = export_csv(body.get("filters"))
        if result.get("success"):
            from fastapi.responses import FileResponse
            return FileResponse(result["filepath"], filename=result["filename"], media_type="text/csv")
        return result

    @app.post("/api/tracker/export/html")
    async def api_export_html(request: Request):
        body = await request.json()
        result = export_html_report(body.get("filters"))
        if result.get("success"):
            from fastapi.responses import FileResponse
            return FileResponse(result["filepath"], filename=result["filename"], media_type="text/html")
        return result
# ======= END FILTER + EXPORT =======


# ======= SIGNAL BRIDGE CONFIG =======
try:
    from backend.api.signal_bridge import (
        get_tracked_symbols, set_tracked_symbols,
        get_tracked_timeframes, set_tracked_timeframes,
        TRACK_SYMBOLS,
    )
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False

if BRIDGE_AVAILABLE:

    @app.get("/api/tracker/config")
    async def api_tracker_config():
        return {
            "symbols": get_tracked_symbols(),
            "timeframes": get_tracked_timeframes(),
        }

    @app.post("/api/tracker/config")
    async def api_tracker_set_config(request: Request):
        body = await request.json()
        if "symbols" in body:
            set_tracked_symbols(body["symbols"])
        if "timeframes" in body:
            set_tracked_timeframes(body["timeframes"])
        return {
            "success": True,
            "symbols": get_tracked_symbols(),
            "timeframes": get_tracked_timeframes(),
        }

    @app.get("/api/tracker/scan-now")
    async def api_scan_now():
        """Manual scan trigger for testing."""
        try:
            import importlib
            import backend.api.signal_bridge as _sb
            importlib.reload(_sb)
            scan_all_signals = _sb.scan_all_signals
            from backend.api.tracker_engine import load_state, load_active
            state = load_state()
            active = load_active()
            active_ids = {t.get("strategy_id","") for t in active.get("active",[])}
            signals = scan_all_signals(state, active_ids)
            return {"success": True, "signals_found": len(signals), "signals": signals[:20]}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}


    @app.get("/api/tracker/debug")
    async def api_tracker_debug():
        """Show what the bridge sees."""
        import traceback as tb
        info = {"steps": []}
        try:
            info["steps"].append("1. Importing orchestrator...")
            from backend.strategies.orchestrator import analyze_symbol, get_available_strategies
            strats = get_available_strategies()
            info["available_strategies"] = len(strats)
            info["steps"].append(f"2. Found {len(strats)} strategies")

            info["steps"].append("3. Testing analyze_symbol XAUUSD H1...")
            result = analyze_symbol("XAUUSD", "H1")
            if result:
                all_strats = result.get("strategies", [])
                signals = [s for s in all_strats if s.get("signal") in ("BUY", "SELL")]
                info["total_results"] = len(all_strats)
                info["active_signals"] = len(signals)
                info["signal_names"] = [{"name": s.get("name",""), "signal": s.get("signal",""), "confidence": s.get("confidence",0)} for s in signals[:10]]
                info["neutral_sample"] = [s.get("name","") for s in all_strats if s.get("signal") == "NEUTRAL"][:5]
                info["steps"].append(f"4. {len(all_strats)} strategies analyzed, {len(signals)} active signals")

                # Check setup data
                if signals:
                    sample = signals[0]
                    info["sample_signal"] = {
                        "name": sample.get("name",""),
                        "signal": sample.get("signal",""),
                        "setup": sample.get("setup", {}),
                        "entry": sample.get("entry", 0),
                        "price": sample.get("price", 0),
                        "keys": list(sample.keys()),
                    }
            else:
                info["steps"].append("4. analyze_symbol returned None/empty")
                info["result_raw"] = str(result)[:500]

            # Check bridge
            info["steps"].append("5. Testing signal_bridge...")
            import importlib
            import backend.api.signal_bridge as _sb
            importlib.reload(_sb)
            scan_all_signals = _sb.scan_all_signals
            from backend.api.tracker_engine import load_state, load_active
            state = load_state()
            active = load_active()
            active_ids = {t.get("strategy_id","") for t in active.get("active",[])}
            bridge_signals = scan_all_signals(state, active_ids)
            info["bridge_signals"] = len(bridge_signals)
            info["bridge_sample"] = bridge_signals[:3] if bridge_signals else []
            info["steps"].append(f"6. Bridge found {len(bridge_signals)} signals")

            info["success"] = True
        except Exception as e:
            info["success"] = False
            info["error"] = str(e)
            info["traceback"] = tb.format_exc()

        return info

# ======= END BRIDGE =======


# ======= ALERT SUBSCRIPTIONS =======
try:
    from backend.api.alert_subscription import (
        subscribe, unsubscribe, get_subscriptions,
        get_notifications, get_unread_count, mark_read,
        clear_notifications, save_email_config, get_email_config,
    )
    ALERT_SUB_AVAILABLE = True
except ImportError:
    ALERT_SUB_AVAILABLE = False

if ALERT_SUB_AVAILABLE:

    @app.post("/api/alert/subscribe")
    async def api_subscribe(request: Request):
        body = await request.json()
        return subscribe(body.get("email", ""), body.get("config", {}))

    @app.post("/api/alert/unsubscribe")
    async def api_unsubscribe(request: Request):
        body = await request.json()
        return unsubscribe(body.get("email", ""), body.get("sub_id", ""))

    @app.get("/api/alert/subscriptions")
    async def api_get_subs(email: str = ""):
        return {"subscriptions": get_subscriptions(email)}

    @app.get("/api/alert/notifications")
    async def api_get_notifs(email: str = "", limit: int = 50, unread: bool = False):
        return {"notifications": get_notifications(email, limit, unread)}

    @app.get("/api/alert/unread-count")
    async def api_unread(email: str = ""):
        return {"count": get_unread_count(email)}

    @app.post("/api/alert/mark-read")
    async def api_mark_read(request: Request):
        body = await request.json()
        return mark_read(body.get("email", ""), body.get("notif_id"))

    @app.post("/api/alert/clear")
    async def api_clear_notifs(request: Request):
        body = await request.json()
        return clear_notifications(body.get("email", ""))

    @app.post("/api/alert/email-config")
    async def api_save_email_cfg(request: Request):
        body = await request.json()
        return save_email_config(body)

    @app.get("/api/alert/email-config")
    async def api_get_email_cfg():
        return get_email_config()
# ======= END ALERT SUBS =======




# ======= ALERTS PAGE =======
@app.get("/alerts")
async def serve_alerts_page():
    import os as _os
    from fastapi.responses import FileResponse
    html = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "frontend", "alerts_page.html")
    return FileResponse(html, media_type="text/html")
# ======= END ALERTS PAGE =======












# ======= PERFORMANCE: API CACHE =======
import time as _time

class _ApiCache:
    """Simple in-memory cache with TTL for expensive API endpoints."""
    def __init__(self):
        self._cache = {}
        self._hits = 0
        self._misses = 0
    
    def get(self, key, ttl=10):
        """Get cached value if not expired. TTL in seconds."""
        if key in self._cache:
            val, ts = self._cache[key]
            if _time.time() - ts < ttl:
                self._hits += 1
                return val
        self._misses += 1
        return None
    
    def set(self, key, val):
        self._cache[key] = (val, _time.time())
        # Cleanup old entries (keep max 200)
        if len(self._cache) > 200:
            oldest = sorted(self._cache.items(), key=lambda x: x[1][1])[:50]
            for k, _ in oldest:
                del self._cache[k]
    
    def stats(self):
        return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}

_api_cache = _ApiCache()

# Combined poll endpoint — single request replaces 5+ separate polls
@app.get("/api/poll")
async def api_poll(email: str = ""):
    """Single endpoint for all client polling — replaces multiple separate calls."""
    from fastapi.responses import JSONResponse
    import datetime
    
    result = {}
    
    # 1. Tracker status (cached 5s)
    cached = _api_cache.get("tracker_status", 5)
    if cached:
        result["tracker"] = cached
    else:
        try:
            from backend.api.tracker_engine import get_status
            status = get_status()
            _api_cache.set("tracker_status", status)
            result["tracker"] = status
        except Exception:
            result["tracker"] = {}
    
    # 2. Alert unread count (cached 5s)
    if email:
        cache_key = f"unread_{email}"
        cached = _api_cache.get(cache_key, 5)
        if cached is not None:
            result["unread"] = cached
        else:
            try:
                from backend.api.alert_subscription import get_unread_count
                cnt = get_unread_count(email)
                _api_cache.set(cache_key, cnt)
                result["unread"] = cnt
            except Exception:
                result["unread"] = 0
    
    # 3. Server time
    result["server_time"] = datetime.datetime.now().isoformat()
    
    # 4. Cache stats
    result["cache"] = _api_cache.stats()
    
    return JSONResponse(result, headers={"Cache-Control": "no-cache"})

# Cache wrapper for heavy endpoints
@app.get("/api/tracker/ranking-cached")
async def api_ranking_cached(sort: str = "win_rate", limit: int = 100):
    cache_key = f"ranking_{sort}_{limit}"
    cached = _api_cache.get(cache_key, 15)  # 15s cache
    if cached:
        return cached
    # Call original
    try:
        from backend.api.tracker_engine import get_ranking
        data = get_ranking(sort_by=sort, limit=limit)
        _api_cache.set(cache_key, data)
        return data
    except Exception as e:
        return {"ranking": [], "error": str(e)}

@app.get("/api/tracker/summary-cached")
async def api_summary_cached():
    cached = _api_cache.get("summary", 15)  # 15s cache
    if cached:
        return cached
    try:
        from backend.api.tracker_engine import get_summary
        data = get_summary()
        _api_cache.set("summary", data)
        return data
    except Exception as e:
        return {"strategies": [], "error": str(e)}

@app.get("/api/perf/stats")
async def api_perf_stats():
    import psutil, os
    proc = psutil.Process(os.getpid())
    return {
        "cache": _api_cache.stats(),
        "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 1),
        "cpu_percent": proc.cpu_percent(interval=0.1),
        "threads": proc.num_threads(),
    }
# ======= END CACHE =======


# ======= STATIC FILES (WILDCARD) =======

@app.get("/static/manifest.json")
async def serve_manifest():
    import json as _json
    p = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "static", "manifest.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            data = _json.load(f)
        return JSONResponse(content=data)
    return JSONResponse(content={}, status_code=404)


@app.get("/static/icon-{name}.png")
async def serve_icon(name: str):
    from fastapi.responses import FileResponse
    p = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "static", f"icon-{name}.png")
    if os.path.exists(p):
        return FileResponse(p, media_type="image/png")
    return Response("not found", status_code=404)

@app.get("/static/{filename}")
async def serve_static_file(filename: str):
    import os as _os
    from fastapi.responses import FileResponse, Response
    static_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "frontend")
    filepath = _os.path.join(static_dir, filename)
    # Security: only serve known extensions
    if not filename.endswith(('.js', '.css', '.png', '.ico', '.json', '.svg', '.woff', '.woff2', '.ttf', '.map')):
        return Response("not allowed", status_code=403)
    if _os.path.exists(filepath):
        mt = "application/javascript" if filename.endswith('.js') else "text/css"
        return FileResponse(filepath, media_type=mt)
    return Response("// not found: " + filename, status_code=404, media_type="text/plain")
# ======= END STATIC =======


# ======= FAST CACHED ENDPOINTS =======
@app.get("/api/fast/ranking")
async def fast_ranking(sort: str = "score", limit: int = 100, since: str = None):
    from backend.api.fast_cache import get_ranking
    return get_ranking(sort_by=sort, limit=limit)


# ======= FAST FILTER + HEATMAP + EXPORT =======
# [REPLACED — was returning summaries, now returns real trades]
# @app.get("/api/fast/filter")
# async def api_fast_filter(request: Request):
#     try:
#         body = await request.json()
#     except:
#         body = {}
#     from backend.api.fast_cache import get_filtered_trades
#     return get_filtered_trades(
#         symbols=body.get("symbols"),
#         strategies=body.get("strategies"),
#         directions=body.get("directions"),
#         outcomes=body.get("outcomes"),
#         limit=body.get("limit", 200),
#     )
# 
@app.post("/api/fast/heatmap")
async def api_fast_heatmap(request: Request):
    from backend.api.fast_cache import get_heatmap
    return get_heatmap()

@app.get("/api/fast/heatmap")
async def api_fast_heatmap_get():
    from backend.api.fast_cache import get_heatmap
    return get_heatmap()

@app.post("/api/fast/export/csv")
async def api_fast_export_csv(request: Request):
    try:
        body = await request.json()
    except:
        body = {}
    from backend.api.fast_cache import get_export_data
    return get_export_data(fmt="csv", limit=body.get("limit", 500))

@app.post("/api/fast/export/html")
async def api_fast_export_html(request: Request):
    try:
        body = await request.json()
    except:
        body = {}
    from backend.api.fast_cache import get_export_data
    return get_export_data(fmt="json", limit=body.get("limit", 500))
# ======= END FAST ENDPOINTS =======

@app.get("/api/fast/summary")
async def fast_summary():
    from backend.api.fast_cache import get_summary
    return get_summary()

@app.get("/api/fast/filter-options")
async def fast_filter_options():
    from backend.api.fast_cache import get_filter_options
    return get_filter_options()

@app.get("/api/fast/build-cache")
async def fast_build_cache():
    from backend.api.fast_cache import build_cache
    import threading
    t = threading.Thread(target=build_cache, daemon=True)
    t.start()
    return {"status": "building"}


# ======= END FAST =======



# ═══════════════════════════════════════════════════════════════
# ADMIN API ENDPOINTS (auto-installed)
# ═══════════════════════════════════════════════════════════════
try:
    from backend.api.database import (
        verify_admin as _av, create_admin_token as _at,
        verify_token as _vt, change_admin_password as _cp,
        get_dashboard_stats as _ds, get_all_users as _au,
        get_user_count as _uc, get_recent_analyses as _ra,
        get_all_settings as _gs, set_setting as _ss,
        block_user as _bu, delete_user as _du,
        get_support_messages as _sm, get_unread_count as _ur,
        mark_message_read as _mr, delete_support_message as _dm,
        get_popular_symbols as _ps, get_hourly_stats as _hs,
        get_daily_stats as _dys,
    )
    _AOK = True
    logger.info("[ADMIN] Module loaded OK")
except ImportError as _e:
    _AOK = False
    logger.warning(f"[ADMIN] Not available: {_e}")


async def _adm(authorization: str = Header(None)) -> str:
    if not _AOK: raise HTTPException(503, "Admin not available")
    if not authorization: raise HTTPException(401, "No token")
    t = authorization.replace("Bearer ", "").strip()
    u = _vt(t)
    if not u: raise HTTPException(401, "Invalid token")
    return u


@app.post("/api/admin/login")
async def _admin_login(request: Request):
    if not _AOK: raise HTTPException(503, "Admin not loaded")
    d = await request.json()
    if _av(d.get("username",""), d.get("password","")):
        return {"success": True, "token": _at(d["username"])}
    raise HTTPException(401, "Wrong credentials")


@app.get("/api/admin/stats")
async def _admin_stats(a: str = Depends(_adm)):
    return {"stats": _ds(), "popular_symbols": _ps(10), "hourly_stats": _hs(24), "daily_stats": _dys(30)}


@app.get("/api/admin/users")
async def _admin_users(a: str = Depends(_adm), limit: int = 50, offset: int = 0, search: str = ""):
    return {"users": _au(limit, offset, search), "total": _uc()}


@app.post("/api/admin/user/{uid}/block")
async def _admin_block(uid: int, a: str = Depends(_adm)):
    _bu(uid, True); return {"success": True}


@app.post("/api/admin/user/{uid}/unblock")
async def _admin_unblock(uid: int, a: str = Depends(_adm)):
    _bu(uid, False); return {"success": True}


@app.delete("/api/admin/user/{uid}")
async def _admin_deluser(uid: int, a: str = Depends(_adm)):
    _du(uid); return {"success": True}


@app.get("/api/admin/analyses")
async def _admin_analyses(a: str = Depends(_adm), limit: int = 50):
    return {"analyses": _ra(limit)}


@app.get("/api/admin/settings")
async def _admin_gset(a: str = Depends(_adm)):
    return {"settings": _gs()}


@app.post("/api/admin/settings")
async def _admin_sset(request: Request, a: str = Depends(_adm)):
    d = await request.json()
    for k, v in d.items(): _ss(k, str(v))
    return {"success": True}


@app.post("/api/admin/password")
async def _admin_chpw(request: Request, a: str = Depends(_adm)):
    d = await request.json()
    pw = d.get("new_password", "")
    if len(pw) < 6: raise HTTPException(400, "Password too short")
    _cp(a, pw); return {"success": True}


@app.get("/api/admin/messages")
async def _admin_msgs(a: str = Depends(_adm), limit: int = 100):
    return {"messages": _sm(limit), "unread": _ur()}


@app.post("/api/admin/message/{mid}/read")
async def _admin_readmsg(mid: int, a: str = Depends(_adm)):
    _mr(mid); return {"success": True}


@app.delete("/api/admin/message/{mid}")
async def _admin_delmsg(mid: int, a: str = Depends(_adm)):
    _dm(mid); return {"success": True}



# ═══ REDIRECT SLOW TRACKER ENDPOINTS TO FAST CACHE ═══════════
# (added by tracker audit fix)

@app.get("/api/tracker/ranking")
async def _tracker_ranking_redirect(sort: str = "win_rate", limit: int = 100):
    """Redirect to fast cached ranking."""
    try:
        from backend.api.fast_cache import get_ranking
        return get_ranking(sort_by=sort, limit=limit)
    except ImportError:
        return {"ranking": [], "error": "fast_cache not available"}


@app.get("/api/tracker/summary")
async def _tracker_summary_redirect():
    """Redirect to fast cached summary."""
    try:
        from backend.api.fast_cache import get_summary
        return get_summary()
    except ImportError:
        return {"strategies": [], "error": "fast_cache not available"}



@app.get("/api/tracker/status")
async def _tracker_status_fast():
    """Fast tracker status — reads state file only, no scanning."""
    import os as _os2, json as _j2
    state_file = _os2.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\track_records", "tracker_state.json")
    active_file = _os2.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\track_records", "active_tracks.json")
    cache_file = r"C:\\Users\\Administrator\\Desktop\\mvp\\data\\tracker_cache.json"

    state = {}
    if _os2.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as _f:
                state = _j2.load(_f)
        except: pass

    active_count = 0
    if _os2.path.exists(active_file):
        try:
            with open(active_file, "r", encoding="utf-8") as _f:
                ad = _j2.load(_f)
            active_count = len(ad.get("active", []))
        except: pass

    cache_strategies = 0
    cache_trades = 0
    if _os2.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as _f:
                cc = _j2.load(_f)
            cache_strategies = len(cc.get("ranking", []))
            cache_trades = cc.get("total_trades", 0)
        except: pass

    return {
        "is_running": state.get("running", state.get("is_running", False)),
        "last_cycle": state.get("last_cycle", ""),
        "cycle_count": state.get("total_cycles", state.get("cycle_count", 0)),
        "total_cycles": state.get("total_cycles", state.get("cycle_count", 0)),
        "total_signals": state.get("total_signals", 0),
        "total_closes": state.get("total_closes", cache_trades),
        "active_trades": active_count,
        "total_strategies": cache_strategies,
        "total_closed_trades": cache_trades,
        "cycle_interval": state.get("cycle_interval", 120),
    }



@app.get("/api/tracker/filter-options")
async def _tracker_filter_options_redirect():
    """Redirect to fast cached version."""
    try:
        from backend.api.fast_cache import get_filter_options
        return get_filter_options()
    except ImportError:
        return {"symbols": [], "strategies": [], "timeframes": ["H1"], "directions": ["BUY","SELL"], "outcomes": ["win","loss"]}

# ═══ END REDIRECT ════════════════════════════════════════════

# ═══ END ADMIN API ════════════════════════════════════════════


# ═══ HISTORY & SNAPSHOT API ENDPOINTS ═════════════════════════

@app.get("/api/tracker/history")
async def _tracker_history(days: int = 30):
    """Get daily performance snapshots for trend analysis."""
    try:
        from backend.api.daily_snapshot import get_history, take_snapshot
        # Auto-create today's snapshot if missing
        take_snapshot()
        return {"history": get_history(days), "days": days}
    except ImportError:
        return {"history": [], "error": "daily_snapshot not available"}


@app.get("/api/tracker/history/{strategy_id}")
async def _tracker_strategy_history(strategy_id: str, days: int = 30):
    """Get performance history for a specific strategy over time."""
    try:
        from backend.api.daily_snapshot import get_strategy_history
        return {"strategy_id": strategy_id, "history": get_strategy_history(strategy_id, days)}
    except ImportError:
        return {"history": [], "error": "daily_snapshot not available"}


@app.get("/api/tracker/trade-events/{strategy_id}/{trade_id}")
async def _tracker_trade_events(strategy_id: str, trade_id: str):
    """Get full event timeline for a specific trade."""
    import os as _os3, json as _j3
    rec_file = _os3.path.join(r"C:\\\\Users\\\\Administrator\\\\Desktop\\\\mvp\\\\track_records", f"rec_{strategy_id[:60]}.json")
    if not _os3.path.exists(rec_file):
        return {"trade": None, "events": []}
    try:
        with open(rec_file, "r", encoding="utf-8") as _f:
            rec = _j3.load(_f)
        for t in rec.get("trades", []):
            if t.get("id") == trade_id:
                return {
                    "trade": t,
                    "events": t.get("events", []),
                    "total_events": len(t.get("events", [])),
                }
        return {"trade": None, "events": []}
    except Exception as _e:
        return {"trade": None, "events": [], "error": str(_e)}


@app.get("/api/tracker/active-details")
async def _tracker_active_details():
    """Get detailed info on all currently active trades with events."""
    import os as _os4, json as _j4
    af = _os4.path.join(r"C:\\\\Users\\\\Administrator\\\\Desktop\\\\mvp\\\\track_records", "active_tracks.json")
    if not _os4.path.exists(af):
        return {"active": [], "count": 0}
    try:
        with open(af, "r", encoding="utf-8") as _f:
            data = _j4.load(_f)
        trades = data.get("active", [])
        return {
            "active": trades,
            "count": len(trades),
            "symbols": list(set(t.get("symbol","") for t in trades)),
        }
    except Exception as _e:
        return {"active": [], "count": 0, "error": str(_e)}


@app.post("/api/tracker/snapshot")
async def _tracker_take_snapshot():
    """Manually trigger a daily snapshot."""
    try:
        from backend.api.daily_snapshot import take_snapshot
        return take_snapshot()
    except ImportError:
        return {"error": "daily_snapshot not available"}

# ═══ END HISTORY API ══════════════════════════════════════════


# ═══ FIXED FILTER — Returns real trade records ═══════════════

@app.post("/api/fast/filter")
async def _fast_filter_real(request: Request):
    """Filter trades — handles both {filters:{...}} and flat format."""
    try:
        from backend.api.fast_cache import get_real_trades_fast
        raw = await request.json()
        # Unwrap {filters: {...}} if present
        body = raw.get("filters", raw) if isinstance(raw.get("filters"), dict) else raw
        
        # Parse filter fields (handle both array and single values)
        def to_list(v):
            if not v: return None
            if isinstance(v, list): return [x for x in v if x] or None
            return [v] if v else None
        
        result = get_real_trades_fast(
            symbols=to_list(body.get("symbols")),
            strategies=to_list(body.get("strategies")),
            directions=to_list(body.get("directions")),
            outcomes=to_list(body.get("outcomes")),
            exit_reasons=to_list(body.get("exit_reasons") or body.get("exits")),
            timeframes=to_list(body.get("timeframes")),
            date_from=body.get("date_from") or body.get("from"),
            date_to=body.get("date_to") or body.get("to"),
            sort_by=body.get("sort_by") or body.get("sort", "opened_at"),
            sort_dir=body.get("sort_dir", "desc"),
            limit=min(int(body.get("limit", 200)), 500),
            offset=int(body.get("offset", 0)),
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"trades": [], "total_found": 0, "stats": {}, "error": str(e)}


@app.post("/api/tracker/filter")
async def _tracker_filter_real(request: Request):
    """Filter trades — handles both {filters:{...}} and flat format."""
    try:
        from backend.api.fast_cache import get_real_trades_fast
        raw = await request.json()
        body = raw.get("filters", raw) if isinstance(raw.get("filters"), dict) else raw
        def to_list(v):
            if not v: return None
            if isinstance(v, list): return [x for x in v if x] or None
            return [v] if v else None
        result = get_real_trades_fast(
            symbols=body.get("symbols"),
            strategies=body.get("strategies"),
            directions=body.get("directions"),
            outcomes=body.get("outcomes"),
            exit_reasons=body.get("exit_reasons"),
            timeframes=body.get("timeframes"),
            date_from=body.get("date_from"),
            date_to=body.get("date_to"),
            sort_by=body.get("sort_by", "opened_at"),
            sort_dir=body.get("sort_dir", "desc"),
            limit=min(body.get("limit", 200), 500),
            offset=body.get("offset", 0),
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"trades": [], "total_found": 0, "stats": {}, "error": str(e)}

# ═══ END FIXED FILTER ════════════════════════════════════════


# ═══ TELEGRAM BOT API ENDPOINTS ══════════════════════════════




@app.get("/api/telegram/status")
async def _telegram_status():
    """Get Telegram bot status."""
    try:
        from backend.api.telegram_bot import get_bot_info, _polling_active
        info = get_bot_info()
        return {
            "bot_connected": info.get("ok", False),
            "bot_username": info.get("result", {}).get("username", ""),
            "polling_active": _polling_active,
        }
    except Exception as e:
        return {"bot_connected": False, "error": str(e)}


@app.post("/api/telegram/test")
async def _telegram_test(request: Request):
    """Send a test alert to a chat_id."""
    try:
        from backend.api.telegram_bot import send_alert
        body = await request.json()
        chat_id = body.get("chat_id")
        if not chat_id:
            return {"ok": False, "error": "chat_id required"}
        
        test_trade = {
            "symbol": "EURUSD", "direction": "BUY",
            "strategy_name": "Test Strategy", "timeframe": "H1",
            "entry_price": 1.08540, "sl_price": 1.08340, "tp1_price": 1.08740,
        }
        result = send_alert(chat_id, "entry", test_trade)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/alerts/subscribers")
async def _alert_subscribers():
    """List all alert subscribers (admin)."""
    import sqlite3
    db = os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\data", "whilber.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM user_alerts ORDER BY created_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"subscribers": rows, "total": len(rows)}


@app.get("/api/alerts/log")
async def _alert_log(limit: int = 50):
    """Get alert sending log."""
    import sqlite3
    db = os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\data", "whilber.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM alert_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"logs": rows, "total": len(rows)}


@app.post("/api/alerts/settings")
async def _alert_save_settings(request: Request):
    """Save alert settings for a user."""
    import sqlite3
    body = await request.json()
    chat_id = str(body.get("chat_id", ""))
    if not chat_id:
        return {"ok": False, "error": "chat_id required"}
    
    db = os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\data", "whilber.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    
    now_str = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    
    strategies = body.get("strategies", "*")
    symbols = body.get("symbols", "*")
    events = body.get("events", "*")
    
    if isinstance(strategies, list):
        strategies = __import__("json").dumps(strategies)
    if isinstance(symbols, list):
        symbols = __import__("json").dumps(symbols)
    if isinstance(events, list):
        events = __import__("json").dumps(events)
    
    c.execute("""UPDATE user_alerts SET
        telegram_active=?, email_active=?, email_address=?,
        strategies=?, symbols=?, events=?,
        min_pnl=?, quiet_start=?, quiet_end=?, updated_at=?
        WHERE telegram_chat_id=?""",
        (
            1 if body.get("telegram_active", True) else 0,
            1 if body.get("email_active", False) else 0,
            body.get("email_address", ""),
            strategies, symbols, events,
            body.get("min_pnl", 0),
            body.get("quiet_start", ""),
            body.get("quiet_end", ""),
            now_str, chat_id,
        ))
    conn.commit()
    conn.close()
    return {"ok": True}



@app.get("/alerts-settings")
async def _alerts_settings_page():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\frontend", "alerts_settings.html"))

# ═══ END TELEGRAM API ═════════════════════════════════════════


# ═══ ALERT DISPATCHER API ════════════════════════════════════

@app.get("/api/alerts/stats")
async def _alerts_stats():
    """Get alert dispatcher statistics."""
    try:
        from backend.api.alert_dispatcher import get_stats
        return get_stats()
    except ImportError:
        return {"error": "dispatcher not available"}


@app.post("/api/alerts/dispatch-test")
async def _alerts_dispatch_test(request: Request):
    """Test dispatch: simulate an event and send to subscribers."""
    try:
        from backend.api.alert_dispatcher import dispatch_event_sync
        body = await request.json()
        event_type = body.get("event_type", "entry")
        trade_data = body.get("trade_data", {
            "symbol": "EURUSD", "direction": "BUY",
            "strategy_name": "Test Strategy", "strategy_id": "TEST_01",
            "timeframe": "H1", "entry_price": 1.08540,
            "sl_price": 1.08340, "tp1_price": 1.08740,
        })
        result = dispatch_event_sync(event_type, trade_data)
        return {"ok": True, "result": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

# ═══ END ALERT DISPATCHER API ════════════════════════════════


# ═══ EMAIL API ENDPOINTS ═════════════════════════════════════

@app.get("/api/email/status")
async def _email_status():
    """Check email SMTP configuration."""
    try:
        from backend.api.email_sender import is_configured, _load_config
        cfg = _load_config()
        return {
            "configured": is_configured(),
            "server": cfg.get("server", ""),
            "email": cfg.get("email", ""),
        }
    except Exception as e:
        return {"configured": False, "error": str(e)}


@app.post("/api/email/test")
async def _email_test(request: Request):
    """Test email connection or send test email."""
    try:
        body = await request.json()
        action = body.get("action", "test_connection")
        
        if action == "test_connection":
            from backend.api.email_sender import test_connection
            return test_connection()
        
        elif action == "send_test":
            from backend.api.email_sender import send_email
            to_addr = body.get("email", "")
            if not to_addr:
                return {"ok": False, "error": "email address required"}
            result = send_email(to_addr, "entry", {
                "symbol": "EURUSD", "direction": "BUY",
                "strategy_name": "Test Strategy", "timeframe": "H1",
                "entry_price": 1.08540, "sl_price": 1.08340, "tp1_price": 1.08740,
            })
            return result
        
        return {"ok": False, "error": "unknown action"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/email/configure")
async def _email_configure(request: Request):
    """Save SMTP settings to .env file."""
    try:
        body = await request.json()
        env_path = os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp", ".env")
        
        with open(env_path, "r", encoding="utf-8") as f:
            env = f.read()
        
        # Update or add each SMTP setting
        settings = {
            "SMTP_SERVER": body.get("server", ""),
            "SMTP_PORT": str(body.get("port", 587)),
            "SMTP_EMAIL": body.get("email", ""),
            "SMTP_PASSWORD": body.get("password", ""),
            "SMTP_FROM_NAME": body.get("from_name", "Whilber-AI Alerts"),
            "SMTP_USE_TLS": "true" if body.get("use_tls", True) else "false",
        }
        
        for key, val in settings.items():
            if val:
                pattern = f"#?\s*{key}=.*"
                import re as _re
                if _re.search(pattern, env):
                    env = _re.sub(pattern, f"{key}={val}", env)
                else:
                    env += f"\n{key}={val}"
        
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env)
        
        # Reset cached config
        try:
            from backend.api import email_sender
            email_sender._smtp_config = None
        except:
            pass
        
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ═══ END EMAIL API ═══════════════════════════════════════════


# ═══ ADMIN CHANNEL + NOTIFICATION API ════════════════════════

@app.post("/api/admin/send-channel")
async def _admin_send_channel(request: Request):
    """Admin: Send alert to public Telegram channel."""
    body = await request.json()
    # Verify admin token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        from backend.api.database import verify_token
        if not verify_token(token):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
    except:
        pass
    
    message = body.get("message", "")
    send_to_users = body.get("send_to_users", False)
    
    results = {"channel": None, "users": 0}
    
    # Send to channel
    try:
        from backend.api.telegram_bot import send_to_channel, send_message as tg_send
        if message:
            r = send_to_channel(message)
            results["channel"] = r
        
        # Also send to subscribed users if requested
        if send_to_users:
            import sqlite3
            db = os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\data", "whilber.db")
            conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row; c = conn.cursor()
            c.execute("SELECT telegram_chat_id FROM user_alerts WHERE telegram_active=1")
            users = [dict(r)["telegram_chat_id"] for r in c.fetchall()]
            conn.close()
            sent = 0
            for uid in users:
                r = tg_send(uid, message)
                if r.get("ok"): sent += 1
            results["users"] = sent
    except Exception as e:
        results["error"] = str(e)
    
    return results


@app.post("/api/admin/send-alert")
async def _admin_send_custom_alert(request: Request):
    """Admin: Send a custom formatted trade alert."""
    body = await request.json()
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        from backend.api.database import verify_token
        if not verify_token(token):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
    except:
        pass
    
    event_type = body.get("event_type", "entry")
    trade_data = body.get("trade_data", {})
    to_channel = body.get("to_channel", False)
    to_users = body.get("to_users", False)
    
    from backend.api.telegram_bot import format_alert, send_to_channel, send_message as tg_send
    msg = format_alert(event_type, trade_data)
    
    results = {"channel": None, "users": 0}
    
    if to_channel:
        results["channel"] = send_to_channel(msg)
    
    if to_users:
        from backend.api.alert_dispatcher import dispatch_event_sync
        r = dispatch_event_sync(event_type, trade_data)
        results["users"] = r.get("sent", 0)
    
    return results


@app.get("/api/admin/channel-status")
async def _admin_channel_status():
    """Check channel configuration."""
    import os
    env_path = os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp", ".env")
    channel_id = ""
    with open(env_path, "r") as f:
        for line in f:
            if line.strip().startswith("TELEGRAM_CHANNEL_ID="):
                channel_id = line.strip().split("=",1)[1].strip()
    return {"channel_id": channel_id, "configured": bool(channel_id)}

# ═══ END ADMIN CHANNEL ═══════════════════════════════════════

@app.get("/admin/alerts")
async def _admin_alerts_page():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\frontend", "admin_alerts.html"))


@app.get("/api/telegram/start-polling")
async def _tg_start_polling():
    """Manually start telegram polling (fallback)."""
    try:
        from backend.api.telegram_bot import init, start_polling, _polling_active
        if _polling_active:
            return {"status": "already_running"}
        if init():
            start_polling()
            return {"status": "started"}
        return {"status": "init_failed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/static/notif.js")
async def _notif_js():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\frontend", "notif.js"), media_type="application/javascript")


# ═══ STRATEGY ALERT CONFIG ═══════════════════════════════════

@app.post("/api/alerts/strategy-config")
async def _strategy_alert_config(request: Request):
    """Save alert config for a specific strategy."""
    import sqlite3, json as _json
    body = await request.json()
    sid = body.get("strategy_id", "")
    
    db = os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\data", "whilber.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS strategy_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id TEXT, symbol TEXT DEFAULT '', strategy_name TEXT DEFAULT '',
        symbols TEXT DEFAULT '*', events TEXT DEFAULT '*',
        telegram INTEGER DEFAULT 1, channel INTEGER DEFAULT 0,
        email INTEGER DEFAULT 0, popup INTEGER DEFAULT 1, sound INTEGER DEFAULT 1,
        min_confidence INTEGER DEFAULT 0, disabled INTEGER DEFAULT 0,
        chat_id TEXT DEFAULT '', created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '',
        UNIQUE(strategy_id, chat_id)
    )""")
    
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    
    # Handle disable
    if body.get("disabled"):
        c.execute("DELETE FROM strategy_alerts WHERE strategy_id=?", (sid,))
        conn.commit(); conn.close()
        return {"ok": True, "action": "disabled"}
    
    if not sid:
        conn.close()
        return {"ok": False, "error": "strategy_id required"}
    
    events = body.get("events", "*")
    symbols = body.get("symbols", "*")
    if isinstance(events, list): events = _json.dumps(events)
    if isinstance(symbols, list): symbols = _json.dumps(symbols)
    
    chat_id = body.get("chat_id", "93688216")
    
    c.execute("""INSERT INTO strategy_alerts 
                 (strategy_id, symbol, strategy_name, symbols, events, telegram, channel, email, popup, sound, min_confidence, chat_id, created_at, updated_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(strategy_id, chat_id) DO UPDATE SET
                 symbol=?, strategy_name=?, symbols=?, events=?, telegram=?, channel=?, email=?, popup=?, sound=?, min_confidence=?, disabled=0, updated_at=?""",
              (sid, body.get("symbol",""), body.get("strategy_name",""), symbols, events,
               1 if body.get("telegram",True) else 0, 1 if body.get("channel",False) else 0,
               1 if body.get("email",False) else 0, 1 if body.get("popup",True) else 0,
               1 if body.get("sound",True) else 0, body.get("min_confidence",0),
               chat_id, now, now,
               body.get("symbol",""), body.get("strategy_name",""), symbols, events,
               1 if body.get("telegram",True) else 0, 1 if body.get("channel",False) else 0,
               1 if body.get("email",False) else 0, 1 if body.get("popup",True) else 0,
               1 if body.get("sound",True) else 0, body.get("min_confidence",0), now))
    conn.commit(); conn.close()
    return {"ok": True, "strategy_id": sid}


# ═══ END STRATEGY ALERT CONFIG ═══════════════════════════════


@app.get("/static/alert-modal.js")
async def _alert_modal_js():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(r"C:\\Users\\Administrator\\Desktop\\mvp\\frontend", "alert-modal.js"), media_type="application/javascript")


# ═══════════════════════════════════════════════════════
# LANDING PAGE
# ═══════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════
# FIXED PAGE ROUTES (direct file read)
# ═══════════════════════════════════════════════════════

PAGES_DIR = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend")

@app.get("/dashboard", response_class=HTMLResponse)
async def page_dashboard():
    p = os.path.join(PAGES_DIR, "dashboard.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)

@app.get("/guide", response_class=HTMLResponse)
async def page_guide():
    p = os.path.join(PAGES_DIR, "guide.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Guide not found</h1>", status_code=404)

@app.get("/about", response_class=HTMLResponse)
async def page_about():
    p = os.path.join(PAGES_DIR, "about.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>About not found</h1>", status_code=404)

@app.get("/contact", response_class=HTMLResponse)
async def page_contact():
    p = os.path.join(PAGES_DIR, "contact.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Contact not found</h1>", status_code=404)


# ======= CHART API (Sprint 1.1) =======
@app.get("/api/candles/{symbol}/{tf}")
async def get_candles(symbol: str, tf: str, limit: int = 300):
    """Get OHLCV candle data for charting."""
    import MetaTrader5 as mt5
    from datetime import datetime, timezone
    
    symbol = symbol.upper()
    tf = tf.upper()
    
    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    
    mt5_tf = tf_map.get(tf, mt5.TIMEFRAME_H1)
    limit = min(limit, 1000)
    
    try:
        # MT5 broker symbol mapping
        _cmap = {"XAUUSD":"XAUUSD+","XAGUSD":"XAGUSD+","EURUSD":"EURUSD+","GBPUSD":"GBPUSD+","USDJPY":"USDJPY+","AUDUSD":"AUDUSD+","USDCAD":"USDCAD+","NZDUSD":"NZDUSD+","USDCHF":"USDCHF+","BTCUSD":"BTCUSD","NAS100":"NAS100","US30":"DJ30"}
        mt5_symbol = _cmap.get(symbol, symbol)
        rates = mt5.copy_rates_from_pos(mt5_symbol, mt5_tf, 0, limit)
        if rates is None or len(rates) == 0:
            return {"candles": [], "symbol": symbol, "tf": tf}
        
        candles = []
        for r in rates:
            candles.append({
                "time": int(r["time"]),
                "open": round(float(r["open"]), 5),
                "high": round(float(r["high"]), 5),
                "low": round(float(r["low"]), 5),
                "close": round(float(r["close"]), 5),
                "volume": int(r["tick_volume"]),
            })
        
        return {
            "candles": candles,
            "symbol": symbol,
            "tf": tf,
            "count": len(candles),
        }
    except Exception as e:
        return {"candles": [], "symbol": symbol, "tf": tf, "error": str(e)}


@app.get("/api/trades/{symbol}")
async def get_strategy_trades(symbol: str, tf: str = "", strategy: str = "", limit: int = 100):
    """Get strategy trade history for chart markers — matches rec_ file format."""
    import os as _os, json as _json, glob as _glob
    from datetime import datetime as _dt
    
    symbol = symbol.upper()
    track_dir = _os.path.join(r"C:\Users\Administrator\Desktop\mvp", "track_records")
    trades = []
    
    try:
        # Search for rec_ files containing this symbol
        pattern = _os.path.join(track_dir, f"rec_*{symbol}*.json")
        files = _glob.glob(pattern)
        
        if not files:
            # Broader search
            pattern = _os.path.join(track_dir, "rec_*.json")
            files = _glob.glob(pattern)
        
        for fpath in files[:200]:
            try:
                fname = _os.path.basename(fpath)
                if fname.endswith('.bak') or fname.startswith('active_') or fname == 'notifications.json':
                    continue
                
                with open(fpath, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                
                # rec_ files have: {"strategy_id": "...", "trades": [...], "stats": {...}}
                recs = []
                if isinstance(data, dict):
                    recs = data.get("trades", data.get("records", data.get("history", [])))
                elif isinstance(data, list):
                    recs = data
                
                for rec in recs:
                    if not isinstance(rec, dict):
                        continue
                    
                    # Filter by symbol
                    rec_sym = str(rec.get("symbol", "")).upper()
                    if rec_sym != symbol:
                        continue
                    
                    # Filter by timeframe
                    rec_tf = str(rec.get("timeframe", "")).upper()
                    if tf and rec_tf != tf.upper():
                        continue
                    
                    # Filter by strategy
                    rec_strat = str(rec.get("strategy_name", rec.get("strategy_id", "")))
                    if strategy and strategy.lower() not in rec_strat.lower():
                        continue
                    
                    # Parse timestamps
                    def _parse_time(val):
                        if not val:
                            return 0
                        if isinstance(val, (int, float)):
                            return int(val)
                        try:
                            return int(_dt.fromisoformat(str(val).replace("Z", "+00:00")).timestamp())
                        except:
                            return 0
                    
                    # Map fields correctly
                    entry_time = _parse_time(rec.get("opened_at", rec.get("entry_time", rec.get("open_time", 0))))
                    exit_time = _parse_time(rec.get("closed_at", rec.get("exit_time", rec.get("close_time", 0))))
                    
                    entry_price = rec.get("entry_price", 0)
                    exit_price = rec.get("exit_price", rec.get("current_price", 0))
                    sl = rec.get("sl_price", rec.get("sl", 0))
                    tp = rec.get("tp1_price", rec.get("tp_price", rec.get("tp", 0)))
                    direction = rec.get("direction", "BUY")
                    pnl = rec.get("pnl_pips", rec.get("pnl", rec.get("current_pnl_pips", 0)))
                    outcome = rec.get("outcome", rec.get("status", ""))
                    strategy_name = rec.get("strategy_name", rec.get("strategy_id", ""))
                    
                    trade = {
                        "entry_time": entry_time,
                        "exit_time": exit_time,
                        "entry_price": round(float(entry_price), 5) if entry_price else 0,
                        "exit_price": round(float(exit_price), 5) if exit_price else 0,
                        "sl": round(float(sl), 5) if sl else 0,
                        "tp": round(float(tp), 5) if tp else 0,
                        "direction": direction,
                        "pnl": round(float(pnl), 2) if pnl else 0,
                        "outcome": outcome,
                        "strategy": strategy_name,
                        "symbol": rec_sym,
                        "timeframe": rec_tf,
                    }
                    
                    trades.append(trade)
            except Exception:
                continue
        
        # Sort by entry time descending
        trades.sort(key=lambda x: x.get("entry_time", 0), reverse=True)
        
        # Limit
        trades = trades[:limit]
        
    except Exception as e:
        return {"error": str(e), "trades": []}
    
    return trades

# ======= END CHART API =======


# ======= MA OVERLAY API (Sprint 1.2) =======
@app.get("/api/indicators/{symbol}/{tf}")
async def get_indicators(symbol: str, tf: str, limit: int = 300):
    """Get EMA 20/50/200 for chart overlay."""
    import MetaTrader5 as mt5
    import numpy as np
    
    symbol = symbol.upper()
    tf = tf.upper()
    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    mt5_tf = tf_map.get(tf, mt5.TIMEFRAME_H1)
    extra = 200
    
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, min(limit + extra, 1200))
        if rates is None or len(rates) < 50:
            return {"ema20": [], "ema50": [], "ema200": []}
        
        closes = np.array([float(r["close"]) for r in rates])
        times = [int(r["time"]) for r in rates]
        
        def ema(data, period):
            result = np.zeros_like(data)
            result[0] = data[0]
            k = 2.0 / (period + 1)
            for i in range(1, len(data)):
                result[i] = data[i] * k + result[i-1] * (1 - k)
            return result
        
        e20 = ema(closes, 20)
        e50 = ema(closes, 50)
        e200 = ema(closes, 200)
        
        start = max(0, len(rates) - limit)
        
        def to_list(arr, period):
            s = max(start, period)
            return [{"time": times[i], "value": round(float(arr[i]), 5)} for i in range(s, len(arr))]
        
        return {
            "ema20": to_list(e20, 20),
            "ema50": to_list(e50, 50),
            "ema200": to_list(e200, 200),
        }
    except Exception as e:
        return {"ema20": [], "ema50": [], "ema200": [], "error": str(e)}
# ======= END MA OVERLAY =======


# ======= SERVICES PAGE =======
@app.get("/services")
async def services_page():
    from fastapi.responses import HTMLResponse
    import os as _os
    p = _os.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "services.html")
    if _os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Services not found</h1>", status_code=404)
# ======= END SERVICES =======



# ══════════════════════════════════════════════════════
# EXECUTOR API ENDPOINTS (Phase 2)
# ══════════════════════════════════════════════════════

@app.get("/api/executor/status")
async def executor_status():
    """Get executor daemon status + open positions."""
    try:
        from backend.executor.executor_daemon import get_executor_status
        return get_executor_status()
    except Exception as e:
        return {"error": str(e), "running": False}


@app.post("/api/executor/start")
async def executor_start():
    """Start executor daemon."""
    try:
        from backend.executor.executor_daemon import start_executor
        return start_executor()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/executor/stop")
async def executor_stop():
    """Stop executor daemon."""
    try:
        from backend.executor.executor_daemon import stop_executor
        return stop_executor()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/executor/close-all")
async def executor_close_all():
    """Emergency: close all positions."""
    try:
        from backend.executor.mt5_executor import close_all
        return {"results": close_all("api_emergency")}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/executor/positions")
async def executor_positions():
    """Get open MT5 positions."""
    try:
        from backend.executor.mt5_executor import get_open_positions, get_account_info
        return {
            "positions": get_open_positions(),
            "account": get_account_info(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/executor/whitelist/generate")
async def executor_generate_whitelist():
    """Generate whitelist from ranking data."""
    try:
        from backend.executor.whitelist_manager import generate_whitelist
        result = generate_whitelist()
        return {"success": True, "approved": len(result)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/executor/whitelist")
async def executor_get_whitelist():
    """Get current whitelist."""
    import json
    wl_path = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "data", "analysis", "whitelist.json")
    try:
        if os.path.exists(wl_path):
            with open(wl_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"strategies": [], "updated": None}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/executor/config")
async def executor_get_config():
    """Get executor config (symbols, magic numbers, risk settings)."""
    import json
    cfg_path = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "data", "analysis", "executor_config.json")
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"error": "Config not found"}
    except Exception as e:
        return {"error": str(e)}


# ═══ MT5 ACCOUNT MANAGEMENT ═══
@app.get("/api/mt5/accounts")
async def api_mt5_accounts():
    from backend.api.mt5_accounts import get_accounts
    return {"accounts": get_accounts()}

@app.post("/api/mt5/link")
async def api_mt5_link(request: Request):
    data = await request.json()
    from backend.api.mt5_accounts import add_account, link_strategy
    acc_id = data.get("account_id")
    if not acc_id:
        result = add_account(
            data.get("account_number", ""),
            data.get("password", ""),
            data.get("server", ""),
            data.get("platform", "mt5")
        )
        if not result.get("ok"):
            return result
        acc_id = result["id"]
    link_result = link_strategy(
        acc_id,
        data.get("strategy_id", ""),
        data.get("symbol", ""),
        float(data.get("lot_size", 0.01)),
        float(data.get("max_risk", 50))
    )
    return {"ok": True, "success": True, "account_id": acc_id, **link_result}

@app.post("/api/mt5/accounts/{account_id}/toggle")
async def api_mt5_toggle(account_id: str):
    from backend.api.mt5_accounts import toggle_account
    return toggle_account(account_id)

@app.delete("/api/mt5/accounts/{account_id}")
async def api_mt5_delete(account_id: str):
    from backend.api.mt5_accounts import delete_account
    return delete_account(account_id)
# ═══ END MT5 ROUTES ═══


# ═══ PERFORMANCE MONITORING ═══
@app.get("/api/performance/account")
async def api_perf_account():
    if not _PERF_AVAILABLE:
        return JSONResponse({"error": "Performance monitor not available"}, 503)
    try:
        return JSONResponse(content=sanitize(perf_account()))
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/api/performance/positions")
async def api_perf_positions():
    if not _PERF_AVAILABLE:
        return JSONResponse({"error": "Performance monitor not available"}, 503)
    try:
        return JSONResponse(content=sanitize({"positions": perf_positions()}))
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/api/performance/history")
async def api_perf_history(days: int = 30):
    if not _PERF_AVAILABLE:
        return JSONResponse({"error": "Performance monitor not available"}, 503)
    try:
        return JSONResponse(content=sanitize({"trades": perf_history(days)}))
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/api/performance/metrics")
async def api_perf_metrics(days: int = 30):
    if not _PERF_AVAILABLE:
        return JSONResponse({"error": "Performance monitor not available"}, 503)
    try:
        trades = perf_history(days)
        return JSONResponse(content=sanitize(perf_metrics(trades)))
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/api/performance/equity")
async def api_perf_equity(days: int = 30):
    if not _PERF_AVAILABLE:
        return JSONResponse({"error": "Performance monitor not available"}, 503)
    try:
        curve = perf_equity(days)
        dd = perf_drawdown(curve)
        return JSONResponse(content=sanitize({"curve": curve, "drawdown": dd}))
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/api/performance/daily")
async def api_perf_daily(days: int = 30):
    if not _PERF_AVAILABLE:
        return JSONResponse({"error": "Performance monitor not available"}, 503)
    try:
        return JSONResponse(content=sanitize({"daily": perf_daily(days)}))
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/api/performance/snapshot")
async def api_perf_snap():
    if not _PERF_AVAILABLE:
        return JSONResponse({"error": "Performance monitor not available"}, 503)
    try:
        return JSONResponse(content=sanitize(perf_snapshot()))
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/performance", response_class=HTMLResponse)
async def page_performance():
    p = os.path.join(PAGES_DIR, "performance.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Performance page not found</h1>", status_code=404)
# ═══ END PERFORMANCE MONITORING ═══


# ═══ BOT SERVER TRADE SYNC ═══
# These endpoints read from the shared SQLite trade_executions table
# and from bot_server JSON files, so the website can see bot trades.

_BOT_DATA_DIR = r"C:\Users\Administrator\Desktop\mvp\data"
_BOT_DB_PATH = r"C:\Users\Administrator\Desktop\mvp\db\whilber.db"

@app.get("/api/bot/status")
async def api_bot_status():
    """Read bot server status (from bot_state.json)."""
    state_path = os.path.join(_BOT_DATA_DIR, "bot_state.json")
    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return JSONResponse(content=data)
        return JSONResponse({"error": "Bot state file not found — bot may not be running"}, 404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/bot/positions")
async def api_bot_positions():
    """Get bot's active positions (from bot_state.json)."""
    state_path = os.path.join(_BOT_DATA_DIR, "bot_state.json")
    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            active = data.get("active_trades", {})
            return {"count": len(active), "positions": active}
        return JSONResponse({"error": "Bot not running"}, 404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/bot/trades")
async def api_bot_trades():
    """Get bot's closed trade history (from bot_trades.json)."""
    trades_path = os.path.join(_BOT_DATA_DIR, "bot_trades.json")
    try:
        if os.path.exists(trades_path):
            with open(trades_path, "r", encoding="utf-8") as f:
                trades = json.load(f)
            wins = sum(1 for t in trades if t.get("pnl_pips", 0) > 0)
            losses = len(trades) - wins
            total_pips = sum(t.get("pnl_pips", 0) for t in trades)
            return {
                "count": len(trades),
                "wins": wins,
                "losses": losses,
                "total_pips": round(total_pips, 1),
                "trades": trades,
            }
        return {"count": 0, "wins": 0, "losses": 0, "total_pips": 0, "trades": []}
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/bot/executions")
async def api_bot_executions(status: Optional[str] = Query(None), limit: int = Query(100)):
    """Get trade executions from shared SQLite DB (written by bot_server)."""
    try:
        import sqlite3 as _sq3
        conn = _sq3.connect(_BOT_DB_PATH)
        conn.row_factory = _sq3.Row
        if status:
            rows = conn.execute(
                "SELECT * FROM trade_executions WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trade_executions ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
        trades = [dict(r) for r in rows]
        return {"count": len(trades), "executions": trades}
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

# ═══ END BOT SERVER TRADE SYNC ═══


# ═══ DEBUG: Test analyze with strategies ═══
@app.get("/api/analyze2/{symbol}")
@app.get("/api/analyze2/{symbol}/{timeframe}")
async def analyze2(symbol: str, timeframe: str = "H1", strategies: Optional[str] = Query(None)):
    symbol = symbol.upper()
    timeframe = timeframe.upper()
    strat_list = [s.strip() for s in strategies.split(",")] if strategies else None
    result = analyze_symbol(symbol, timeframe, strategies=strat_list)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "fail"))
    # Setup enrichment (safe)
    if False and SETUP_AVAILABLE:
        try:
            price = result.get("last_close")
            ctx = result.get("context", {})
            atr = ctx.get("atr_value")
            if atr is None and ctx.get("atr_percent"):
                atr = price * ctx["atr_percent"] / 100 if price else None
            if price and atr:
                result["strategies"] = enrich_strategies_with_setups(result.get("strategies", []), price, atr, ctx)
            result["master_setup"] = calculate_master_setup(result)
        except Exception as e:
            result["master_setup"] = {"has_setup": False, "reason_fa": str(e)[:50]}
    else:
        result["master_setup"] = {"has_setup": False, "reason_fa": "غیرفعال"}
    # Alerts
    triggered_alerts = []
    if ALERT_AVAILABLE:
        try:
            triggered_alerts = check_alerts(result)
        except:
            pass
    result["triggered_alerts"] = triggered_alerts
    return JSONResponse(content=sanitize(result))

# ═══ ANALYZE ROUTER (clean endpoint) ═══
try:
    from backend.api.analyze_router import router as analyze_rt, init as analyze_rt_init
    analyze_rt_init(
        analyze_fn=analyze_symbol,
        sanitize_fn=sanitize,
        setup_fn=enrich_strategies_with_setups if SETUP_AVAILABLE else None,
        master_fn=calculate_master_setup if SETUP_AVAILABLE else None,
        check_alerts_fn=check_alerts if ALERT_AVAILABLE else None,
        setup_available=SETUP_AVAILABLE,
        alert_available=ALERT_AVAILABLE,
        auth_verify_fn=_auth_verify_token if _AUTH_OK else None,
        auth_profile_fn=_auth_profile if _AUTH_OK else None,
        plan_module=_plans_module if _PLANS_OK else None,
        increment_analysis_fn=_auth_increment_analysis if _AUTH_OK else None,
        get_analysis_count_fn=_auth_get_analysis_count if _AUTH_OK else None,
    )
    app.include_router(analyze_rt)
    logger.info("✅ analyze_router loaded (/api/analyze3/)")
except Exception as e:
    logger.error(f"❌ analyze_router failed: {e}")


# ═══ PLANS API ENDPOINTS ═══
_pricing_page_path = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "pricing.html")

@app.get("/pricing")
async def page_pricing():
    if os.path.exists(_pricing_page_path):
        with open(_pricing_page_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Pricing not found</h1>")

@app.get("/api/plans")
async def api_plans():
    if not _PLANS_OK:
        return {"plans": {}}
    # Return plan limits with Farsi names (strip symbol lists for cleaner response)
    plans_out = {}
    for pname, plimits in PLAN_LIMITS.items():
        plans_out[pname] = {
            "name_fa": PLAN_NAMES_FA.get(pname, pname),
            "max_strategies": plimits["max_strategies"],
            "timeframes": plimits["timeframes"],
            "analyses_per_day": plimits["analyses_per_day"],
            "max_alerts": plimits["max_alerts"],
            "max_journal": plimits["max_journal"],
            "max_robots": plimits["max_robots"],
            "builder": plimits["builder"],
            "backtest": plimits["backtest"],
            "telegram_alerts": plimits["telegram_alerts"],
            "symbols_count": len(plimits["symbols"]) if plimits["symbols"] else "all",
            "price_toman_monthly": plimits["price_toman_monthly"],
            "price_toman_yearly": plimits["price_toman_yearly"],
        }
    return {"plans": plans_out}

@app.get("/api/plans/my-usage")
async def api_plans_my_usage(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "توکن احراز هویت الزامی است")
    user_id, email, plan = _resolve_plan_from_auth(authorization)
    if not user_id:
        raise HTTPException(401, "توکن نامعتبر یا منقضی شده")
    limits = get_plan_limits(plan) if _PLANS_OK else {}
    daily_count = _auth_get_analysis_count(user_id) if _AUTH_OK else 0
    # Count alerts
    alert_count = 0
    if ALERT_AVAILABLE and email:
        alerts = get_alerts(user_email=email, active_only=True)
        alert_count = len(alerts) if isinstance(alerts, list) else 0
    return {
        "plan": plan,
        "plan_fa": PLAN_NAMES_FA.get(plan, "رایگان") if _PLANS_OK else "رایگان",
        "limits": limits,
        "usage": {
            "analyses_today": daily_count,
            "active_alerts": alert_count,
        },
        "upgrade_url": "/pricing",
    }


# ═══ PAYMENT ENDPOINTS ═══

class _PayCreateReq(BaseModel):
    plan: str
    duration_months: int = 1
    method: str  # zarinpal | tether | card
    discount_code: str = ""

class _PayCardConfirmReq(BaseModel):
    payment_id: int
    ref_number: str
    last4_card: str
    amount: int

class _PayTetherConfirmReq(BaseModel):
    payment_id: int
    tx_hash: str

class _PayDiscountReq(BaseModel):
    code: str

class _PayAdminActionReq(BaseModel):
    payment_id: int
    admin_note: str = ""


if _PAY_OK:

    @app.post("/api/payment/create")
    async def api_payment_create(req: _PayCreateReq, authorization: str = Header(None)):
        if not authorization:
            raise HTTPException(401, "توکن احراز هویت الزامی است")
        user_id, email, plan = _resolve_plan_from_auth(authorization)
        if not user_id:
            raise HTTPException(401, "توکن نامعتبر یا منقضی شده")
        result = _pay_create(user_id, req.plan, req.duration_months, req.method, req.discount_code)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.get("/api/payment/verify/{pid}")
    async def api_payment_verify(pid: int, authorization: str = Header(None)):
        if not authorization:
            raise HTTPException(401, "توکن احراز هویت الزامی است")
        user_id, email, plan = _resolve_plan_from_auth(authorization)
        if not user_id:
            raise HTTPException(401, "توکن نامعتبر یا منقضی شده")
        payment = _pay_get(pid)
        if not payment:
            raise HTTPException(404, "پرداخت یافت نشد")
        if payment["user_id"] != user_id:
            raise HTTPException(403, "دسترسی غیرمجاز")
        return {"success": True, "payment": payment}

    @app.get("/api/payment/history")
    async def api_payment_history(authorization: str = Header(None)):
        if not authorization:
            raise HTTPException(401, "توکن احراز هویت الزامی است")
        user_id, email, plan = _resolve_plan_from_auth(authorization)
        if not user_id:
            raise HTTPException(401, "توکن نامعتبر یا منقضی شده")
        payments = _pay_history(user_id)
        return {"success": True, "payments": payments}

    @app.post("/api/payment/card-confirm")
    async def api_payment_card_confirm(req: _PayCardConfirmReq, authorization: str = Header(None)):
        if not authorization:
            raise HTTPException(401, "توکن احراز هویت الزامی است")
        user_id, email, plan = _resolve_plan_from_auth(authorization)
        if not user_id:
            raise HTTPException(401, "توکن نامعتبر یا منقضی شده")
        result = _pay_confirm_card(req.payment_id, user_id, req.ref_number, req.last4_card, req.amount)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.post("/api/payment/tether-confirm")
    async def api_payment_tether_confirm(req: _PayTetherConfirmReq, authorization: str = Header(None)):
        if not authorization:
            raise HTTPException(401, "توکن احراز هویت الزامی است")
        user_id, email, plan = _resolve_plan_from_auth(authorization)
        if not user_id:
            raise HTTPException(401, "توکن نامعتبر یا منقضی شده")
        result = _pay_submit_tether(req.payment_id, user_id, req.tx_hash)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.post("/api/payment/apply-discount")
    async def api_payment_apply_discount(req: _PayDiscountReq):
        return _pay_discount(req.code)

    @app.get("/api/payment/zarinpal-callback")
    async def api_payment_zarinpal_callback(
        Authority: str = Query(""),
        Status: str = Query(""),
        payment_id: int = Query(0),
    ):
        result = _pay_verify_zp(Authority, Status, payment_id)
        from fastapi.responses import RedirectResponse
        if result["success"]:
            return RedirectResponse(url=f"/payment?result=success&payment_id={result.get('payment_id', payment_id)}")
        return RedirectResponse(url=f"/payment?result=failed&payment_id={payment_id}")

    @app.get("/api/payment/config")
    async def api_payment_config():
        return _pay_config()

    # ── Admin payment endpoints ──

    @app.get("/api/admin/payments")
    async def api_admin_payments(
        a: str = Depends(_adm),
        limit: int = 50, offset: int = 0, status: str = ""
    ):
        return _pay_admin_list(limit, offset, status)

    @app.post("/api/admin/payment/approve")
    async def api_admin_payment_approve(req: _PayAdminActionReq, a: str = Depends(_adm)):
        result = _pay_admin_approve(req.payment_id, req.admin_note)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.post("/api/admin/payment/reject")
    async def api_admin_payment_reject(req: _PayAdminActionReq, a: str = Depends(_adm)):
        result = _pay_admin_reject(req.payment_id, req.admin_note)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.post("/api/admin/payment/check-expiry")
    async def api_admin_check_expiry(a: str = Depends(_adm)):
        count = _pay_check_expiry()
        return {"success": True, "downgraded": count}


# ═══════════════════════════════════════════════════════════════
# ADMIN EXTENDED (Phase 4) — User mgmt, Discounts, Revenue, Notify
# ═══════════════════════════════════════════════════════════════

if _ADM_EXT_OK:

    @app.get("/api/admin/auth-users")
    async def api_admin_auth_users(
        a: str = Depends(_adm),
        limit: int = 50, offset: int = 0,
        search: str = "", plan: str = "", status: str = "",
    ):
        return _adm_users(limit, offset, search, plan, status)

    @app.get("/api/admin/auth-users/{uid}")
    async def api_admin_auth_user_detail(uid: int, a: str = Depends(_adm)):
        detail = _adm_user_detail(uid)
        if not detail:
            raise HTTPException(404, "User not found")
        return detail

    @app.put("/api/admin/auth-users/{uid}/plan")
    async def api_admin_change_plan(uid: int, request: Request, a: str = Depends(_adm)):
        d = await request.json()
        result = _adm_change_plan(uid, d.get("plan", "free"), d.get("duration_days", 30))
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.put("/api/admin/auth-users/{uid}/toggle")
    async def api_admin_toggle_user(uid: int, request: Request, a: str = Depends(_adm)):
        d = await request.json()
        result = _adm_toggle_user(uid, d.get("active", True))
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.get("/api/admin/user-stats")
    async def api_admin_user_stats(a: str = Depends(_adm)):
        return _adm_user_stats()

    @app.get("/api/admin/users-export")
    async def api_admin_users_export(a: str = Depends(_adm), plan: str = ""):
        from fastapi.responses import Response
        csv_data = _adm_export_csv(plan)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"},
        )

    @app.post("/api/admin/discounts")
    async def api_admin_create_discount(request: Request, a: str = Depends(_adm)):
        d = await request.json()
        result = _adm_create_disc(
            code=d.get("code", ""),
            percent_off=d.get("percent_off", 10),
            max_uses=d.get("max_uses", 100),
            valid_until=d.get("valid_until", ""),
        )
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.get("/api/admin/discounts")
    async def api_admin_list_discounts(a: str = Depends(_adm)):
        return {"discounts": _adm_get_discs()}

    @app.put("/api/admin/discounts/{did}/toggle")
    async def api_admin_toggle_discount(did: int, request: Request, a: str = Depends(_adm)):
        d = await request.json()
        result = _adm_toggle_disc(did, d.get("active", True))
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.delete("/api/admin/discounts/{did}")
    async def api_admin_delete_discount(did: int, a: str = Depends(_adm)):
        result = _adm_del_disc(did)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @app.get("/api/admin/revenue")
    async def api_admin_revenue(a: str = Depends(_adm)):
        return _adm_rev_stats()

    @app.get("/api/admin/revenue/chart")
    async def api_admin_revenue_chart(a: str = Depends(_adm), days: int = 30):
        return {"chart": _adm_rev_chart(days)}

    @app.post("/api/admin/notify")
    async def api_admin_notify(request: Request, a: str = Depends(_adm)):
        d = await request.json()
        result = _adm_notify(
            target=d.get("target", ""),
            message=d.get("message", ""),
            title=d.get("title", "اطلاع‌رسانی"),
        )
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result


# ── Payment page route ──
_payment_page_path = os.path.join(r"C:\Users\Administrator\Desktop\mvp", "frontend", "payment.html")

@app.get("/payment")
async def page_payment():
    if os.path.exists(_payment_page_path):
        with open(_payment_page_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Payment page not found</h1>")
