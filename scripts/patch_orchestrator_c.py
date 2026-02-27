"""
Whilber-AI MVP - Orchestrator Patch (Step 04c)
=================================================
Adds 7 MORE strategies to the orchestrator (25 → 32).
"""

import os

PROJECT = r"C:\Users\Administrator\Desktop\mvp"
ORCH_PATH = os.path.join(PROJECT, "backend", "strategies", "orchestrator.py")


def patch():
    with open(ORCH_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # ── Check if already patched ────────────────────────────
    if "cat15_pivot" in content:
        print("[OK] Already patched (step 04c)")
        return

    # ── Add new imports after last import block ─────────────
    new_imports = """
# Category 15-21: Additional strategies (Step 04c)
from backend.strategies.cat15_pivot import PivotPointStrategy
from backend.strategies.cat16_mean_reversion import MeanReversion
from backend.strategies.cat17_breakout import MomentumBreakout
from backend.strategies.cat18_session import SessionAnalysis
from backend.strategies.cat19_gap import GapTrading
from backend.strategies.cat20_harmonic import HarmonicStrategy
from backend.strategies.cat21_wyckoff import WyckoffStrategy
"""

    # Find the last import line from step 04b
    marker = "from backend.strategies.cat14_supply_demand import SupplyDemandStrategy"
    if marker in content:
        content = content.replace(marker, marker + "\n" + new_imports)
    else:
        # Fallback: add after base_strategy import
        fallback = "from backend.strategies.base_strategy import Signal, SIGNAL_FA, SIGNAL_COLOR"
        content = content.replace(fallback, fallback + "\n" + new_imports)

    # ── Add new strategy instances ──────────────────────────
    new_instances = """    # Cat 15-21: Additional (Step 04c)
    PivotPointStrategy(),
    MeanReversion(),
    MomentumBreakout(),
    SessionAnalysis(),
    GapTrading(),
    HarmonicStrategy(),
    WyckoffStrategy(),
"""

    # Find the closing bracket of ALL_STRATEGIES list
    # Insert before the last ]
    old_end = "    SupplyDemandStrategy(),\n]"
    new_end = "    SupplyDemandStrategy(),\n" + new_instances + "]"

    if old_end in content:
        content = content.replace(old_end, new_end)
    else:
        print("[WARN] Could not find SupplyDemandStrategy() in list, trying alternative...")
        # Try to find the ] that closes ALL_STRATEGIES
        # Look for the pattern after WyckoffStrategy
        pass

    # ── Add new category names ──────────────────────────────
    old_cats = '    "supply_demand": "عرضه و تقاضا",\n}'
    new_cats = """    "supply_demand": "عرضه و تقاضا",
    "pivot": "پیوت پوینت",
    "mean_reversion": "بازگشت به میانگین",
    "breakout": "شکست مومنتومی",
    "session": "تحلیل سشن",
    "gap": "معامله گپ",
    "harmonic": "هارمونیک",
    "wyckoff": "وایکاف",
}"""

    if '"pivot"' not in content:
        content = content.replace(old_cats, new_cats)

    with open(ORCH_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("[OK] Orchestrator patched with 7 MORE strategies (total: 32)")


if __name__ == "__main__":
    patch()
