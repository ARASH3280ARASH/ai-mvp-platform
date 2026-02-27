"""
Whilber-AI — Plan Limits & Feature Gating
==========================================
Central config for free / pro / premium / enterprise plans.
Helper functions for checking access limits.
"""

from typing import Dict, Tuple, Optional, List

# ── Symbol Groups ───────────────────────────────────────

FREE_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD", "US30", "USOIL",
]

PRO_SYMBOLS = [
    # Free symbols
    "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD", "US30", "USOIL",
    # Extra forex
    "USDCHF", "AUDUSD", "NZDUSD", "USDCAD", "EURGBP", "EURJPY", "GBPJPY",
    # Extra metals
    "XAGUSD",
    # Extra indices
    "US100", "US500",
    # Extra crypto
    "ETHUSD", "SOLUSD", "XRPUSD",
]

ALL_TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]

# ── Plan Limits ─────────────────────────────────────────

PLAN_LIMITS: Dict[str, dict] = {
    "free": {
        "max_strategies": 32,
        "symbols": FREE_SYMBOLS,
        "timeframes": ["H1"],
        "analyses_per_day": 5,
        "max_alerts": 2,
        "max_journal": 10,
        "max_robots": 0,
        "builder": False,
        "backtest": False,
        "telegram_alerts": False,
        "price_toman_monthly": 0,
        "price_toman_yearly": 0,
    },
    "pro": {
        "max_strategies": 150,
        "symbols": PRO_SYMBOLS,
        "timeframes": ["H1", "H4", "D1"],
        "analyses_per_day": 50,
        "max_alerts": 15,
        "max_journal": 100,
        "max_robots": 1,
        "builder": True,
        "backtest": "basic",
        "telegram_alerts": False,
        "price_toman_monthly": 149_000,
        "price_toman_yearly": 1_490_000,
    },
    "premium": {
        "max_strategies": 9999,
        "symbols": None,  # all symbols
        "timeframes": ALL_TIMEFRAMES,
        "analyses_per_day": 9999,
        "max_alerts": 50,
        "max_journal": 9999,
        "max_robots": 5,
        "builder": True,
        "backtest": "full",
        "telegram_alerts": True,
        "price_toman_monthly": 399_000,
        "price_toman_yearly": 3_990_000,
    },
    "enterprise": {
        "max_strategies": 9999,
        "symbols": None,  # all symbols
        "timeframes": ALL_TIMEFRAMES,
        "analyses_per_day": 9999,
        "max_alerts": 9999,
        "max_journal": 9999,
        "max_robots": 9999,
        "builder": True,
        "backtest": "full",
        "telegram_alerts": True,
        "price_toman_monthly": 999_000,
        "price_toman_yearly": 9_990_000,
    },
}

# Farsi plan names
PLAN_NAMES_FA = {
    "free": "رایگان",
    "pro": "حرفه‌ای",
    "premium": "ویژه",
    "enterprise": "سازمانی",
}


# ── Helper Functions ────────────────────────────────────

def get_plan_limits(plan: str) -> dict:
    """Return limits dict for a plan. Defaults to free."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def check_symbol_access(plan: str, symbol: str) -> bool:
    """True if symbol is allowed for this plan."""
    limits = get_plan_limits(plan)
    allowed = limits.get("symbols")
    if allowed is None:
        return True  # premium/enterprise = all symbols
    return symbol.upper() in allowed


def check_timeframe_access(plan: str, timeframe: str) -> bool:
    """True if timeframe is allowed for this plan."""
    limits = get_plan_limits(plan)
    return timeframe.upper() in limits.get("timeframes", ["H1"])


def check_daily_analysis_limit(plan: str, count: int) -> Tuple[bool, int, int]:
    """Check daily analysis limit. Returns (allowed, remaining, limit)."""
    limits = get_plan_limits(plan)
    limit = limits["analyses_per_day"]
    remaining = max(0, limit - count)
    return (count < limit, remaining, limit)


def check_alert_limit(plan: str, count: int) -> Tuple[bool, int, int]:
    """Check active alert limit. Returns (allowed, remaining, limit)."""
    limits = get_plan_limits(plan)
    limit = limits["max_alerts"]
    remaining = max(0, limit - count)
    return (count < limit, remaining, limit)


def check_journal_limit(plan: str, count: int) -> Tuple[bool, int, int]:
    """Check journal entry limit. Returns (allowed, remaining, limit)."""
    limits = get_plan_limits(plan)
    limit = limits["max_journal"]
    remaining = max(0, limit - count)
    return (count < limit, remaining, limit)


def check_feature_access(plan: str, feature: str) -> bool:
    """Check boolean feature access: builder, backtest, telegram_alerts."""
    limits = get_plan_limits(plan)
    val = limits.get(feature, False)
    return bool(val)


def get_strategy_limit(plan: str) -> int:
    """Max number of strategies to return in analysis results."""
    limits = get_plan_limits(plan)
    return limits["max_strategies"]


def get_plan_info_for_response(plan: str, daily_count: int = 0) -> dict:
    """Build plan info block for API responses."""
    limits = get_plan_limits(plan)
    allowed, remaining, limit = check_daily_analysis_limit(plan, daily_count)
    return {
        "plan": plan,
        "plan_fa": PLAN_NAMES_FA.get(plan, "رایگان"),
        "analyses_today": daily_count,
        "analyses_remaining": remaining,
        "analyses_limit": limit,
        "max_strategies": limits["max_strategies"],
        "upgrade_url": "/pricing",
    }
