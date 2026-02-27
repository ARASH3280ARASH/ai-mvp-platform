# Track-Record Page — Critical Fixes

> Read ALL track-record related files (HTML, JS, CSS, Python/FastAPI backend) completely before starting.
> Phase this work: complete and test each phase before moving to the next.

---

## PHASE 1: Missing Header/Navigation

The top navigation menu and header have disappeared from the track-record page. This header/nav exists on ALL other pages of the site. Restore it:
- Look at other pages (e.g., landing page, builder page, admin panel) to find the shared header/nav structure
- It uses `div class="wnav"` with inline styles (NOT `class="header"`)
- Copy the same nav/header to track-record page so it matches the rest of the site
- Do NOT add `body{display:flex}`, do NOT remove any `</div>` closings
- Key layout: `.main(flex) > .sidebar + .content`, footer MUST be OUTSIDE `.main`

---

## PHASE 2: Strategy Ranking — Fix Flickering/Jumping

The strategy ranking table keeps flickering and jumping every ~3 seconds. Root cause: there was a previous system that checks MetaTrader 5 connection and Alert connection every 3 seconds, and if disconnected it re-renders the UI, causing the whole ranking to jump.

**Fix:**
- Remove or refactor the 3-second polling that causes full re-renders
- MetaTrader icon and Alert icon next to each strategy must be **static/stable** — no flickering
- Only update the icon status when the actual connection state changes (diff-check before DOM update)
- Do NOT re-render the entire ranking table on each poll cycle

---

## PHASE 3: Active Trades — Per-Strategy MetaTrader Controls

Currently there is only ONE MetaTrader button for all active trades. This is wrong.

**Fix:**
- Each strategy/setup row in Active Trades must have its OWN MetaTrader button and Alert button
- Each strategy should have **pre-configured default settings** (lot size, SL, TP based on the strategy parameters) so the user only needs to click "Connect" or "Enable Alert" without manual configuration
- These buttons must be **stable** — no flickering or jumping (same fix as Phase 2)
- Validate: only ONE active trade per symbol per strategy at any given time

---

## PHASE 4: Category Comparison — Missing First Name

In the category comparison section, the first category/strategy has no visible name. It shows something like:
```
1242trWR:66.8%$1449.03
```
Instead of showing the strategy name properly.

**Fix:**
- Debug why the first item's name is empty/missing
- Ensure all categories and strategies display their full name correctly
- Check the data source — the name field might be null or empty for the first record

---

## PHASE 5: Filter Results — Per-Strategy MT5 + Validation

The filter results section has the same problem as Active Trades:

**Fix:**
- Each strategy/setup row in filter results must have its OWN MetaTrader button with pre-configured trade settings
- Add validation rules:
  - Only show **valid** strategies and trades in filter results
  - Enforce: only **1 trade per symbol per strategy** at any given time (no duplicate simultaneous trades)
  - Filter out invalid setups before displaying
- Improve the filter results table: clean fonts, proper table borders, professional look
- Buttons must be stable (no flickering)

---

## Rules (apply to ALL phases)
- Do NOT add `body{display:flex}`
- Do NOT remove `</div>` closings
- Structure: `.main(flex) > .sidebar + .content`, footer OUTSIDE `.main`
- Old nav is `div class="wnav"` with inline styles
- Test each phase before proceeding to next
- Read all files fully before making any changes
