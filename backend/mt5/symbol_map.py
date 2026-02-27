"""
Whilber-AI MVP - Symbol Map (Fixed for Moneta Markets)
=========================================================
Complete mapping of all available symbols on broker.
Broker: Moneta Markets Demo
  - Minor forex pairs use '+' suffix
  - XAUUSD → XAUUSD+
  - Index: NAS100 (not US100)
  - US30, US500 NOT available
  - 5 crypto removed (DOGEUSD, LINKUSD, AVAXUSD, ALGOUSD, IOTAUSD)
"""

from typing import List, Dict, Optional
from enum import Enum
from loguru import logger


# ── Categories ──────────────────────────────────────────────────

class SymbolCategory(str, Enum):
    FOREX = "forex"
    CRYPTO = "crypto"
    METALS = "metals"
    INDICES = "indices"


CATEGORY_FA = {
    SymbolCategory.FOREX: "فارکس",
    SymbolCategory.CRYPTO: "کریپتو",
    SymbolCategory.METALS: "فلزات",
    SymbolCategory.INDICES: "شاخص‌ها"
}


# ── Symbol Definitions ──────────────────────────────────────────
# mt5_name = exact name on Moneta Markets broker

SYMBOLS = {
    # ════════════════════════════════════════════════════════
    # FOREX MAJOR (no suffix on majors)
    # ════════════════════════════════════════════════════════
    "EURUSD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "EURUSD",
        "name_fa": "یورو / دلار",
        "sub": "major"
    },
    "GBPUSD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "GBPUSD",
        "name_fa": "پوند / دلار",
        "sub": "major"
    },
    "USDJPY": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "USDJPY",
        "name_fa": "دلار / ین",
        "sub": "major"
    },
    "USDCHF": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "USDCHF+",
        "name_fa": "دلار / فرانک",
        "sub": "major"
    },
    "AUDUSD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "AUDUSD",
        "name_fa": "دلار استرالیا / دلار",
        "sub": "major"
    },
    "NZDUSD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "NZDUSD",
        "name_fa": "دلار نیوزلند / دلار",
        "sub": "major"
    },
    "USDCAD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "USDCAD",
        "name_fa": "دلار / دلار کانادا",
        "sub": "major"
    },

    # ════════════════════════════════════════════════════════
    # FOREX MINOR (all use '+' suffix on Moneta Markets)
    # ════════════════════════════════════════════════════════
    "EURGBP": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "EURGBP+",
        "name_fa": "یورو / پوند",
        "sub": "minor"
    },
    "EURJPY": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "EURJPY+",
        "name_fa": "یورو / ین",
        "sub": "minor"
    },
    "GBPJPY": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "GBPJPY+",
        "name_fa": "پوند / ین",
        "sub": "minor"
    },
    "EURAUD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "EURAUD+",
        "name_fa": "یورو / دلار استرالیا",
        "sub": "minor"
    },
    "EURCAD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "EURCAD+",
        "name_fa": "یورو / دلار کانادا",
        "sub": "minor"
    },
    "EURCHF": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "EURCHF+",
        "name_fa": "یورو / فرانک",
        "sub": "minor"
    },
    "EURNZD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "EURNZD+",
        "name_fa": "یورو / دلار نیوزلند",
        "sub": "minor"
    },
    "GBPAUD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "GBPAUD+",
        "name_fa": "پوند / دلار استرالیا",
        "sub": "minor"
    },
    "GBPCAD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "GBPCAD+",
        "name_fa": "پوند / دلار کانادا",
        "sub": "minor"
    },
    "GBPCHF": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "GBPCHF+",
        "name_fa": "پوند / فرانک",
        "sub": "minor"
    },
    "GBPNZD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "GBPNZD+",
        "name_fa": "پوند / دلار نیوزلند",
        "sub": "minor"
    },
    "AUDJPY": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "AUDJPY+",
        "name_fa": "دلار استرالیا / ین",
        "sub": "minor"
    },
    "AUDNZD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "AUDNZD+",
        "name_fa": "دلار استرالیا / نیوزلند",
        "sub": "minor"
    },
    "AUDCAD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "AUDCAD+",
        "name_fa": "دلار استرالیا / کانادا",
        "sub": "minor"
    },
    "AUDCHF": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "AUDCHF+",
        "name_fa": "دلار استرالیا / فرانک",
        "sub": "minor"
    },
    "NZDJPY": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "NZDJPY+",
        "name_fa": "دلار نیوزلند / ین",
        "sub": "minor"
    },
    "NZDCAD": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "NZDCAD+",
        "name_fa": "دلار نیوزلند / کانادا",
        "sub": "minor"
    },
    "NZDCHF": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "NZDCHF+",
        "name_fa": "دلار نیوزلند / فرانک",
        "sub": "minor"
    },
    "CADJPY": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "CADJPY+",
        "name_fa": "دلار کانادا / ین",
        "sub": "minor"
    },
    "CADCHF": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "CADCHF+",
        "name_fa": "دلار کانادا / فرانک",
        "sub": "minor"
    },
    "CHFJPY": {
        "category": SymbolCategory.FOREX,
        "mt5_name": "CHFJPY+",
        "name_fa": "فرانک / ین",
        "sub": "minor"
    },

    # ════════════════════════════════════════════════════════
    # METALS (XAUUSD uses '+', XAGUSD no suffix)
    # ════════════════════════════════════════════════════════
    "XAUUSD": {
        "category": SymbolCategory.METALS,
        "mt5_name": "XAUUSD+",
        "name_fa": "طلا",
        "sub": "precious"
    },
    "XAGUSD": {
        "category": SymbolCategory.METALS,
        "mt5_name": "XAGUSD",
        "name_fa": "نقره",
        "sub": "precious"
    },

    # ════════════════════════════════════════════════════════
    # INDICES (only NAS100 available on this broker)
    # US30 and US500 are NOT available
    # ════════════════════════════════════════════════════════
    "NAS100": {
        "category": SymbolCategory.INDICES,
        "mt5_name": "NAS100",
        "name_fa": "نزدک ۱۰۰",
        "sub": "us"
    },
    "US30": {
        "mt5_name": "DJ30",
        "name_fa": "داو جونز",
        "sub": "index"
    },


    # ════════════════════════════════════════════════════════
    # CRYPTO (21 symbols — removed 5 unavailable)
    # Removed: DOGEUSD, LINKUSD, AVAXUSD, ALGOUSD, IOTAUSD
    # ════════════════════════════════════════════════════════
    "BTCUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "BTCUSD",
        "name_fa": "بیت‌کوین",
        "sub": "crypto"
    },
    "ETHUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "ETHUSD",
        "name_fa": "اتریوم",
        "sub": "crypto"
    },
    "SOLUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "SOLUSD",
        "name_fa": "سولانا",
        "sub": "crypto"
    },
    "XRPUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "XRPUSD",
        "name_fa": "ریپل",
        "sub": "crypto"
    },
    "ADAUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "ADAUSD",
        "name_fa": "کاردانو",
        "sub": "crypto"
    },
    "DOTUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "DOTUSD",
        "name_fa": "پولکادات",
        "sub": "crypto"
    },
    "LTCUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "LTCUSD",
        "name_fa": "لایت‌کوین",
        "sub": "crypto"
    },
    "BCHUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "BCHUSD",
        "name_fa": "بیت‌کوین‌کش",
        "sub": "crypto"
    },
    "UNIUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "UNIUSD",
        "name_fa": "یونی‌سواپ",
        "sub": "crypto"
    },
    "XLMUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "XLMUSD",
        "name_fa": "استلار",
        "sub": "crypto"
    },
    "TRXUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "TRXUSD",
        "name_fa": "ترون",
        "sub": "crypto"
    },
    "FILUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "FILUSD",
        "name_fa": "فایل‌کوین",
        "sub": "crypto"
    },
    "NEOUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "NEOUSD",
        "name_fa": "نئو",
        "sub": "crypto"
    },
    "BATUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "BATUSD",
        "name_fa": "بت",
        "sub": "crypto"
    },
    "ZECUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "ZECUSD",
        "name_fa": "زی‌کش",
        "sub": "crypto"
    },
    "SHBUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "SHBUSD",
        "name_fa": "شیبا",
        "sub": "crypto"
    },
    "HBARUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "HBARUSD",
        "name_fa": "هدرا",
        "sub": "crypto"
    },
    "ONDOUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "ONDOUSD",
        "name_fa": "اوندو",
        "sub": "crypto"
    },
    "WIFUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "WIFUSD",
        "name_fa": "ویف",
        "sub": "crypto"
    },
    "BERAUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "BERAUSD",
        "name_fa": "بِرا",
        "sub": "crypto"
    },
    "TRUMPUSD": {
        "category": SymbolCategory.CRYPTO,
        "mt5_name": "TRUMPUSD",
        "name_fa": "ترامپ",
        "sub": "crypto"
    }
}


# ── Alternate MT5 Names ─────────────────────────────────────────
# For symbols where broker name differs from standard name.
# First entry is the PRIMARY broker name.

MT5_ALTERNATES = {
    "USDCHF":  ["USDCHF+", "USDCHF"],
    "EURGBP":  ["EURGBP+", "EURGBP"],
    "EURJPY":  ["EURJPY+", "EURJPY"],
    "GBPJPY":  ["GBPJPY+", "GBPJPY"],
    "EURAUD":  ["EURAUD+", "EURAUD"],
    "EURCAD":  ["EURCAD+", "EURCAD"],
    "EURCHF":  ["EURCHF+", "EURCHF"],
    "EURNZD":  ["EURNZD+", "EURNZD"],
    "GBPAUD":  ["GBPAUD+", "GBPAUD"],
    "GBPCAD":  ["GBPCAD+", "GBPCAD"],
    "GBPCHF":  ["GBPCHF+", "GBPCHF"],
    "GBPNZD":  ["GBPNZD+", "GBPNZD"],
    "AUDJPY":  ["AUDJPY+", "AUDJPY"],
    "AUDNZD":  ["AUDNZD+", "AUDNZD"],
    "AUDCAD":  ["AUDCAD+", "AUDCAD"],
    "AUDCHF":  ["AUDCHF+", "AUDCHF"],
    "NZDJPY":  ["NZDJPY+", "NZDJPY"],
    "NZDCAD":  ["NZDCAD+", "NZDCAD"],
    "NZDCHF":  ["NZDCHF+", "NZDCHF"],
    "CADJPY":  ["CADJPY+", "CADJPY"],
    "CADCHF":  ["CADCHF+", "CADCHF"],
    "CHFJPY":  ["CHFJPY+", "CHFJPY"],
    "XAUUSD":  ["XAUUSD+", "XAUUSD"]
}


# ── Lookup Functions ────────────────────────────────────────────

def get_symbols_by_category(category: str) -> List[Dict]:
    """Get all symbols for a category with display info."""
    cat = SymbolCategory(category)
    result = []
    for key, info in SYMBOLS.items():
        if info["category"] == cat:
            result.append({
                "symbol": key,
                "mt5_name": info["mt5_name"],
                "name_fa": info["name_fa"],
                "sub": info["sub"]
            })
    return result


def get_symbol_info(symbol: str) -> Optional[Dict]:
    """Get info for a specific symbol."""
    return SYMBOLS.get(symbol.upper())


def get_mt5_name(symbol: str) -> str:
    """Get the MT5 broker name for a symbol."""
    info = SYMBOLS.get(symbol.upper())
    if info:
        return info["mt5_name"]
    return symbol.upper()


def get_farsi_name(symbol: str) -> str:
    """Get Farsi display name for a symbol."""
    info = SYMBOLS.get(symbol.upper())
    if info:
        return info["name_fa"]
    return symbol.upper()


def get_alternates(symbol: str) -> List[str]:
    """Get list of alternative MT5 names for a symbol."""
    alts = MT5_ALTERNATES.get(symbol.upper(), [])
    if not alts:
        return [get_mt5_name(symbol)]
    return alts


def get_all_categories() -> List[Dict]:
    """Get list of all categories with Farsi names."""
    return [
        {"id": cat.value, "name_fa": CATEGORY_FA[cat]}
        for cat in SymbolCategory
    ]


def validate_symbol(symbol: str) -> bool:
    """Check if a symbol is in our supported list."""
    return symbol.upper() in SYMBOLS


def search_symbols(query: str) -> List[Dict]:
    """Search symbols by name (English or Farsi)."""
    query = query.lower()
    results = []
    for key, info in SYMBOLS.items():
        if (query in key.lower() or
            query in info["name_fa"] or
            query in info.get("sub", "")):
            results.append({
                "symbol": key,
                "name_fa": info["name_fa"],
                "category": info["category"].value
            })
    return results
