"""Clean analyze endpoint - returns strategies correctly, with plan enforcement."""
import copy
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import JSONResponse

router = APIRouter()

# These will be set by server.py after import
_analyze_fn = None
_sanitize_fn = None
_setup_fn = None
_master_fn = None
_check_alerts_fn = None
_setup_available = False
_alert_available = False

# Plan enforcement (set from server.py)
_auth_verify_fn = None
_auth_profile_fn = None
_plan_module = None
_increment_analysis_fn = None
_get_analysis_count_fn = None

def init(analyze_fn, sanitize_fn, setup_fn=None, master_fn=None,
         check_alerts_fn=None, setup_available=False, alert_available=False,
         auth_verify_fn=None, auth_profile_fn=None, plan_module=None,
         increment_analysis_fn=None, get_analysis_count_fn=None):
    global _analyze_fn, _sanitize_fn, _setup_fn, _master_fn
    global _check_alerts_fn, _setup_available, _alert_available
    global _auth_verify_fn, _auth_profile_fn, _plan_module
    global _increment_analysis_fn, _get_analysis_count_fn
    _analyze_fn = analyze_fn
    _sanitize_fn = sanitize_fn
    _setup_fn = setup_fn
    _master_fn = master_fn
    _check_alerts_fn = check_alerts_fn
    _setup_available = setup_available
    _alert_available = alert_available
    _auth_verify_fn = auth_verify_fn
    _auth_profile_fn = auth_profile_fn
    _plan_module = plan_module
    _increment_analysis_fn = increment_analysis_fn
    _get_analysis_count_fn = get_analysis_count_fn


def _resolve_user(authorization: Optional[str]):
    """Extract user info from token. Returns (user_id, plan) or (None, 'free')."""
    if not authorization or not _auth_verify_fn:
        return None, "free"
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None, "free"
    payload = _auth_verify_fn(token)
    if not payload:
        return None, "free"
    user_id = payload.get("sub")
    if not user_id or not _auth_profile_fn:
        return user_id, "free"
    profile = _auth_profile_fn(user_id)
    if not profile:
        return user_id, "free"
    return user_id, profile.get("plan", "free")


@router.get("/api/analyze3/{symbol}")
@router.get("/api/analyze3/{symbol}/{timeframe}")
async def analyze3(symbol: str, timeframe: str = "H1",
                   strategies: Optional[str] = Query(None),
                   authorization: str = Header(None)):
    symbol = symbol.upper()
    timeframe = timeframe.upper()
    strat_list = [s.strip() for s in strategies.split(",")] if strategies else None

    # ── Plan checks ──
    user_id, plan = _resolve_user(authorization)
    daily_count = 0
    strategies_truncated = False

    if _plan_module:
        # Symbol access
        if not _plan_module.check_symbol_access(plan, symbol):
            raise HTTPException(403, detail={
                "error": f"نماد {symbol} در پلن {_plan_module.PLAN_NAMES_FA.get(plan, 'رایگان')} شما در دسترس نیست",
                "error_code": "symbol_restricted",
                "upgrade_url": "/pricing",
            })

        # Timeframe access
        if not _plan_module.check_timeframe_access(plan, timeframe):
            raise HTTPException(403, detail={
                "error": f"تایم‌فریم {timeframe} در پلن {_plan_module.PLAN_NAMES_FA.get(plan, 'رایگان')} شما در دسترس نیست",
                "error_code": "timeframe_restricted",
                "upgrade_url": "/pricing",
            })

        # Daily limit (only for authenticated users)
        if user_id and _get_analysis_count_fn:
            daily_count = _get_analysis_count_fn(user_id)
            allowed, remaining, limit = _plan_module.check_daily_analysis_limit(plan, daily_count)
            if not allowed:
                raise HTTPException(403, detail={
                    "error": f"سقف تحلیل روزانه ({limit} تحلیل) در پلن {_plan_module.PLAN_NAMES_FA.get(plan, 'رایگان')} شما تمام شده است",
                    "error_code": "daily_limit_reached",
                    "upgrade_url": "/pricing",
                    "limit": limit,
                    "used": daily_count,
                })

    # ── Run analysis ──
    result = _analyze_fn(symbol, timeframe, strategies=strat_list)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "fail"))

    # Save strategies with deepcopy
    saved = copy.deepcopy(result.get("strategies", []))

    # Setup
    result["master_setup"] = {"has_setup": False, "reason_fa": "غیرفعال"}
    if _setup_available and _setup_fn and _master_fn:
        try:
            price = result.get("last_close")
            ctx = result.get("context", {})
            atr = ctx.get("atr_value")
            if atr is None and ctx.get("atr_percent"):
                atr = price * ctx["atr_percent"] / 100 if price else None
            if price and atr:
                saved = _setup_fn(copy.deepcopy(saved), price, atr, ctx)
            result["master_setup"] = _master_fn(result)
        except:
            result["master_setup"] = {"has_setup": False, "reason_fa": "خطا"}

    # Force strategies
    result["strategies"] = saved

    # ── Truncate strategies by plan limit ──
    if _plan_module:
        strat_limit = _plan_module.get_strategy_limit(plan)
        if len(result["strategies"]) > strat_limit:
            result["strategies"] = result["strategies"][:strat_limit]
            strategies_truncated = True

    # Alerts
    result["triggered_alerts"] = []
    if _alert_available and _check_alerts_fn:
        try:
            result["triggered_alerts"] = _check_alerts_fn(copy.deepcopy(result))
        except:
            pass

    # ── Increment daily count for auth users ──
    if user_id and _increment_analysis_fn:
        daily_count = _increment_analysis_fn(user_id)

    # ── Add plan info to response ──
    if _plan_module:
        result["plan_info"] = _plan_module.get_plan_info_for_response(plan, daily_count)
        result["strategies_truncated"] = strategies_truncated

    return JSONResponse(content=_sanitize_fn(result))
