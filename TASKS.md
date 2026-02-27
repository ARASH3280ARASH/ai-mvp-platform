# Track-Record Page - Bug Fixes & Improvements

> Read all track-record related files (HTML, JS, Python/FastAPI backend) fully before starting.

---

## PHASE 1: Data & Stats (Critical)

1. **Top stats are all zero** — Active trades, Signals, Closed, Cycles, Last Update time all show 0. Fix: connect them to real-time backend data, ensure API endpoints return correct counts.
2. **Login/Logout buttons not working** — Debug auth flow, check event listeners and API calls.
3. **Duplicate trades per strategy** — Some strategies open multiple trades simultaneously. Fix: enforce ONE active trade per strategy/setup at any given time. Validate before opening new trade.

---

## PHASE 2: Charts & Visualization

1. **Chart shows only lines, no entry/exit points** — Add markers for entry and exit points on the chart.
2. **Each strategy/setup should be visually distinguishable** on chart (color-coded or labeled).
3. **Chart must be real-time** — ensure it updates with live data.

---

## PHASE 3: Strategy Ranking & Filters

1. **Strategy ranking limited** — Should show top 20 strategies (currently less).
2. **First strategy in category comparison has no name** — Fix empty name bug.
3. **Filter results table** — Improve font, table styling, make it visually clean.
4. **Add MetaTrader connection button** in filter results view.
5. **Validate all strategies and setups** — each must be valid, filter out invalid ones.

---

## PHASE 4: Alerts & MetaTrader Connection

1. **Symbol alert and MetaTrader status flickering** — Elements jump/flash every ~3 seconds. Fix: only update DOM when data actually changes (diff check before re-render).
2. **Alert connection** — Verify alert system works end-to-end.
3. **MetaTrader connection** — Verify MT5 integration works, check active trades panel (left side) has MT5 connection.
4. **Active trades panel (left side)** — Add MetaTrader connection status/button.

---

## PHASE 5: Export & UI Polish

1. **HTML and CSV export** — Test and fix export functionality.
2. **Responsive design** — Check all breakpoints (mobile, tablet, desktop).
3. **RTL/Persian support** — Verify RTL layout is correct.
4. **Overall UI cleanup** — Fonts, spacing, alignment, visual consistency.
5. **Frontend + Backend integration test** — End-to-end test all features.

---

## Rules
- Read ALL related files before making changes
- Test after each phase
- Do NOT add `body{display:flex}`, do NOT remove `</div>` closings
- Key structure: `.main(flex) > .sidebar + .content`, footer OUTSIDE `.main`
- Old nav is inline-styled `div class="wnav"` not `class="header"`
