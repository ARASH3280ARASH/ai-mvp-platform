"""
Whilber-AI — Original Strategies Wrapper
==========================================
Wraps existing 32 strategies into the new registry format.
This file reads the old orchestrator and re-exports them.
"""

import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")

ORIGINAL_STRATEGIES = []

# Try to import from old orchestrator
try:
    # The old orchestrator has a list of strategy functions
    # We import them and wrap into the new format
    from backend.strategies import orchestrator as old_orch

    # Check if old orchestrator has the strategy list
    if hasattr(old_orch, 'ALL_STRATEGIES'):
        # Already in new format
        ORIGINAL_STRATEGIES = old_orch.ALL_STRATEGIES
    elif hasattr(old_orch, 'STRATEGIES'):
        ORIGINAL_STRATEGIES = old_orch.STRATEGIES
    elif hasattr(old_orch, 'get_available_strategies'):
        # Old format had functions registered differently
        # We'll skip original and use only new strategies
        pass
except Exception:
    pass

# If import failed, that's OK — new strategies will work standalone
# The orchestrator v2 will just have the Phase 1+ strategies
