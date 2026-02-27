"""
Whilber-AI MVP - Orchestrator Patch (Step 04b)
=================================================
Adds 7 new strategies to the orchestrator.
Run this AFTER setup_step04b.bat to patch orchestrator.py
"""

# This script patches the existing orchestrator.py to add new strategies
import os
import sys

PROJECT = r"C:\Users\Administrator\Desktop\mvp"
ORCH_PATH = os.path.join(PROJECT, "backend", "strategies", "orchestrator.py")


def patch():
    with open(ORCH_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # ── Add new imports ─────────────────────────────────────
    new_imports = """
# Category 8: Divergence
from backend.strategies.cat08_divergence import DivergenceStrategy
# Category 9: Ichimoku
from backend.strategies.cat09_ichimoku import IchimokuStrategy
# Category 10: Fibonacci
from backend.strategies.cat10_fibonacci import FibonacciStrategy
# Category 11: Multi-Timeframe
from backend.strategies.cat11_multi_tf import MultiTFConfirmation
# Category 12: Range Trading
from backend.strategies.cat12_range import RangeTrading
# Category 13: Smart Money
from backend.strategies.cat13_smart_money import SmartMoneyStrategy
# Category 14: Supply/Demand
from backend.strategies.cat14_supply_demand import SupplyDemandStrategy
"""

    # Add after the last import block
    marker = "from backend.strategies.base_strategy import Signal, SIGNAL_FA, SIGNAL_COLOR"
    if "cat08_divergence" not in content:
        content = content.replace(marker, marker + "\n" + new_imports)

    # ── Add new strategy instances ──────────────────────────
    new_instances = """    # Cat 8: Divergence
    DivergenceStrategy(),
    # Cat 9: Ichimoku
    IchimokuStrategy(),
    # Cat 10: Fibonacci
    FibonacciStrategy(),
    # Cat 11: Multi-TF
    MultiTFConfirmation(),
    # Cat 12: Range
    RangeTrading(),
    # Cat 13: Smart Money
    SmartMoneyStrategy(),
    # Cat 14: Supply/Demand
    SupplyDemandStrategy(),
"""

    # Add before the closing bracket of ALL_STRATEGIES
    old_close = """    # Cat 5-7: Volume, S/R, Candles
    VolumeConfirmation(),
    SRBounce(),
    CandleConfluence(),
]"""
    new_close = """    # Cat 5-7: Volume, S/R, Candles
    VolumeConfirmation(),
    SRBounce(),
    CandleConfluence(),
""" + new_instances + "]"

    if "DivergenceStrategy()" not in content:
        content = content.replace(old_close, new_close)

    # ── Add new category names ──────────────────────────────
    old_cats = """    "candlestick": "الگوهای کندلی",
}"""
    new_cats = """    "candlestick": "الگوهای کندلی",
    "divergence": "واگرایی",
    "ichimoku": "ایچیموکو",
    "fibonacci": "فیبوناچی",
    "multi_tf": "مولتی‌تایم‌فریم",
    "range": "معامله رنج",
    "smart_money": "اسمارت مانی",
    "supply_demand": "عرضه و تقاضا",
}"""

    if '"divergence"' not in content:
        content = content.replace(old_cats, new_cats)

    # ── Set symbol/TF on MultiTF strategy before analyze ───
    # Add code in analyze_symbol to pass symbol/tf to strategies
    old_analyze_loop = """    strategy_results = []
    for strategy in active_strategies:
        try:
            result = strategy.analyze(df, indicators)"""

    new_analyze_loop = """    strategy_results = []
    for strategy in active_strategies:
        try:
            # Pass symbol/TF info for strategies that need it (e.g., MultiTF)
            strategy._current_symbol = symbol
            strategy._current_timeframe = timeframe
            result = strategy.analyze(df, indicators)"""

    if "_current_symbol" not in content:
        content = content.replace(old_analyze_loop, new_analyze_loop)

    with open(ORCH_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("[OK] Orchestrator patched with 7 new strategies (total: 25)")


if __name__ == "__main__":
    patch()
