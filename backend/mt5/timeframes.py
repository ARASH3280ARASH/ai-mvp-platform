"""
Whilber-AI MVP - Timeframe Manager
=====================================
Maps timeframe strings to MT5 constants.
Determines optimal bar count per timeframe.
Handles last-closed-bar logic.
"""

from enum import Enum
from datetime import datetime, timedelta
import MetaTrader5 as mt5
from typing import Dict, Optional


# ── Timeframe Enum ──────────────────────────────────────────────

class Timeframe(str, Enum):
    M1  = "M1"
    M5  = "M5"
    M15 = "M15"
    M30 = "M30"
    H1  = "H1"
    H4  = "H4"
    D1  = "D1"


# ── MT5 Mapping ─────────────────────────────────────────────────

TF_TO_MT5 = {
    Timeframe.M1:  mt5.TIMEFRAME_M1,
    Timeframe.M5:  mt5.TIMEFRAME_M5,
    Timeframe.M15: mt5.TIMEFRAME_M15,
    Timeframe.M30: mt5.TIMEFRAME_M30,
    Timeframe.H1:  mt5.TIMEFRAME_H1,
    Timeframe.H4:  mt5.TIMEFRAME_H4,
    Timeframe.D1:  mt5.TIMEFRAME_D1,
}

# ── Bar Counts ──────────────────────────────────────────────────
# How many bars to fetch per timeframe for analysis.
# Enough for indicators (200-period MA, etc.) + strategy logic.

TF_BAR_COUNT = {
    Timeframe.M1:  250,   # ~4 hours of data
    Timeframe.M5:  250,   # ~20 hours of data
    Timeframe.M15: 200,   # ~2 days of data
    Timeframe.M30: 200,   # ~4 days of data
    Timeframe.H1:  200,   # ~8 days of data
    Timeframe.H4:  150,   # ~25 days of data
    Timeframe.D1:  120,   # ~4 months of data
}

# ── Farsi Names ─────────────────────────────────────────────────

TF_NAMES_FA = {
    Timeframe.M1:  "۱ دقیقه",
    Timeframe.M5:  "۵ دقیقه",
    Timeframe.M15: "۱۵ دقیقه",
    Timeframe.M30: "۳۰ دقیقه",
    Timeframe.H1:  "۱ ساعت",
    Timeframe.H4:  "۴ ساعت",
    Timeframe.D1:  "۱ روزه",
}

# ── Timeframe Duration in Minutes ───────────────────────────────

TF_MINUTES = {
    Timeframe.M1:  1,
    Timeframe.M5:  5,
    Timeframe.M15: 15,
    Timeframe.M30: 30,
    Timeframe.H1:  60,
    Timeframe.H4:  240,
    Timeframe.D1:  1440,
}


# ── Functions ───────────────────────────────────────────────────

def get_mt5_timeframe(tf: str) -> int:
    """Convert timeframe string to MT5 constant."""
    tf_enum = Timeframe(tf.upper())
    return TF_TO_MT5[tf_enum]


def get_bar_count(tf: str) -> int:
    """Get recommended bar count for a timeframe."""
    tf_enum = Timeframe(tf.upper())
    return TF_BAR_COUNT[tf_enum]


def get_farsi_name(tf: str) -> str:
    """Get Farsi display name for a timeframe."""
    tf_enum = Timeframe(tf.upper())
    return TF_NAMES_FA[tf_enum]


def get_tf_minutes(tf: str) -> int:
    """Get timeframe duration in minutes."""
    tf_enum = Timeframe(tf.upper())
    return TF_MINUTES[tf_enum]


def get_all_timeframes() -> list:
    """Get list of all timeframes with display info."""
    return [
        {
            "id": tf.value,
            "name_fa": TF_NAMES_FA[tf],
            "minutes": TF_MINUTES[tf],
        }
        for tf in Timeframe
    ]


def validate_timeframe(tf: str) -> bool:
    """Check if a timeframe string is valid."""
    try:
        Timeframe(tf.upper())
        return True
    except ValueError:
        return False
