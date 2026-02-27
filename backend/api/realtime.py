"""
Whilber-AI — Real-Time Engine
==============================
- WebSocket connection manager
- Background price streamer (every 2s)
- Background analysis scheduler (every 15s per subscribed symbol)
- Memory manager (cleanup every 5 min)
"""

import asyncio
import time
import json
import gc
import sys
import numpy as np
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Set, Any, Optional
from loguru import logger
from fastapi import WebSocket

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")


# ═══════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════

PRICE_INTERVAL = 2          # seconds — price tick update
ANALYSIS_INTERVAL = 15      # seconds — strategy re-analysis
FULL_SCAN_INTERVAL = 60     # seconds — full multi-symbol scan
MEMORY_CLEANUP_INTERVAL = 300  # seconds — cache cleanup
MAX_CACHE_AGE = 600         # seconds — discard cache older than 10 min
MAX_PRICE_HISTORY = 60      # keep last 60 price ticks per symbol


# ═══════════════════════════════════════════════════════
# NUMPY SANITIZER
# ═══════════════════════════════════════════════════════

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
    elif obj is np.nan or (isinstance(obj, float) and obj != obj):
        return None
    return obj


# ═══════════════════════════════════════════════════════
# CONNECTION MANAGER
# ═══════════════════════════════════════════════════════

class ConnectionManager:
    """Manages WebSocket connections & subscriptions."""

    def __init__(self):
        # ws -> {symbol, timeframe, user_id}
        self.connections: Dict[WebSocket, Dict] = {}
        self.lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, symbol: str = "XAUUSD",
                      timeframe: str = "H1", user_id: int = 0):
        await ws.accept()
        async with self.lock:
            self.connections[ws] = {
                "symbol": symbol.upper(),
                "timeframe": timeframe.upper(),
                "user_id": user_id,
                "connected_at": time.time(),
            }
        logger.info(f"🔌 WS connected: {symbol}/{timeframe} (total: {len(self.connections)})")

    async def disconnect(self, ws: WebSocket):
        async with self.lock:
            self.connections.pop(ws, None)
        logger.info(f"🔌 WS disconnected (total: {len(self.connections)})")

    async def update_subscription(self, ws: WebSocket, symbol: str, timeframe: str):
        async with self.lock:
            if ws in self.connections:
                self.connections[ws]["symbol"] = symbol.upper()
                self.connections[ws]["timeframe"] = timeframe.upper()

    def get_subscribed_pairs(self) -> Set[tuple]:
        """Get unique (symbol, timeframe) pairs from all connections."""
        pairs = set()
        for info in self.connections.values():
            pairs.add((info["symbol"], info["timeframe"]))
        return pairs

    def get_subscribed_symbols(self) -> Set[str]:
        """Get unique symbols from all connections."""
        return {info["symbol"] for info in self.connections.values()}

    async def broadcast_to_symbol(self, symbol: str, timeframe: str, message: dict):
        """Send message to all clients watching this symbol/timeframe."""
        dead = []
        for ws, info in list(self.connections.items()):
            if info["symbol"] == symbol and info["timeframe"] == timeframe:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    async def broadcast_price(self, symbol: str, price_data: dict):
        """Send price to ALL clients watching this symbol (any timeframe)."""
        dead = []
        for ws, info in list(self.connections.items()):
            if info["symbol"] == symbol:
                try:
                    await ws.send_json(price_data)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    async def broadcast_all(self, message: dict):
        """Send to ALL connected clients."""
        dead = []
        for ws in list(self.connections.keys()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    @property
    def count(self):
        return len(self.connections)


# ═══════════════════════════════════════════════════════
# ANALYSIS CACHE
# ═══════════════════════════════════════════════════════

class AnalysisCache:
    """In-memory cache for analysis results with auto-cleanup."""

    def __init__(self):
        # key: "SYMBOL:TIMEFRAME" → {data, timestamp}
        self._cache: Dict[str, Dict] = {}
        self._price_cache: Dict[str, list] = defaultdict(list)  # symbol → [prices]

    def set_analysis(self, symbol: str, timeframe: str, data: dict):
        key = f"{symbol}:{timeframe}"
        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
        }

    def get_analysis(self, symbol: str, timeframe: str) -> Optional[dict]:
        key = f"{symbol}:{timeframe}"
        entry = self._cache.get(key)
        if entry and (time.time() - entry["timestamp"]) < MAX_CACHE_AGE:
            return entry["data"]
        return None

    def set_price(self, symbol: str, price: dict):
        self._price_cache[symbol].append({**price, "_ts": time.time()})
        # Keep only last N
        if len(self._price_cache[symbol]) > MAX_PRICE_HISTORY:
            self._price_cache[symbol] = self._price_cache[symbol][-MAX_PRICE_HISTORY:]

    def get_price(self, symbol: str) -> Optional[dict]:
        if self._price_cache[symbol]:
            return self._price_cache[symbol][-1]
        return None

    def cleanup(self):
        """Remove stale entries."""
        now = time.time()
        stale_keys = [k for k, v in self._cache.items()
                      if now - v["timestamp"] > MAX_CACHE_AGE]
        for k in stale_keys:
            del self._cache[k]

        # Clean old price ticks
        for sym in list(self._price_cache.keys()):
            self._price_cache[sym] = [
                p for p in self._price_cache[sym]
                if now - p["_ts"] < MAX_CACHE_AGE
            ]
            if not self._price_cache[sym]:
                del self._price_cache[sym]

        gc.collect()
        logger.info(f"🧹 Cache cleanup: {len(self._cache)} analyses, "
                     f"{sum(len(v) for v in self._price_cache.values())} price ticks")

    @property
    def stats(self):
        return {
            "cached_analyses": len(self._cache),
            "cached_symbols": len(self._price_cache),
            "price_ticks": sum(len(v) for v in self._price_cache.values()),
        }


# ═══════════════════════════════════════════════════════
# BACKGROUND TASKS
# ═══════════════════════════════════════════════════════

class RealtimeEngine:
    """Orchestrates all background tasks."""

    def __init__(self):
        self.manager = ConnectionManager()
        self.cache = AnalysisCache()
        self._running = False
        self._tasks = []

    async def start(self):
        """Start all background loops."""
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._price_loop()),
            asyncio.create_task(self._analysis_loop()),
            asyncio.create_task(self._cleanup_loop()),
        ]
        logger.info("⚡ Real-time engine started")

    async def stop(self):
        """Stop all background loops."""
        self._running = False
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()
        logger.info("⏹️ Real-time engine stopped")

    # ── Price Loop (every 2s) ──────────────────────────

    async def _price_loop(self):
        from backend.mt5.data_fetcher import fetch_current_price
        from backend.mt5.symbol_map import get_farsi_name

        while self._running:
            try:
                symbols = self.manager.get_subscribed_symbols()
                if not symbols:
                    await asyncio.sleep(PRICE_INTERVAL)
                    continue

                for symbol in symbols:
                    try:
                        price = await asyncio.to_thread(fetch_current_price, symbol)
                        if price:
                            self.cache.set_price(symbol, price)
                            msg = {
                                "type": "price",
                                "symbol": symbol,
                                "symbol_fa": get_farsi_name(symbol),
                                "bid": price.get("bid"),
                                "ask": price.get("ask"),
                                "spread": price.get("spread"),
                                "time": datetime.now(timezone.utc).isoformat(),
                            }
                            await self.manager.broadcast_price(symbol, sanitize(msg))
                    except Exception as e:
                        logger.debug(f"Price error {symbol}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Price loop error: {e}")

            await asyncio.sleep(PRICE_INTERVAL)

    # ── Analysis Loop (every 15s) ──────────────────────

    async def _analysis_loop(self):
        from backend.strategies.orchestrator import analyze_symbol

        while self._running:
            try:
                pairs = self.manager.get_subscribed_pairs()
                if not pairs:
                    await asyncio.sleep(ANALYSIS_INTERVAL)
                    continue

                for symbol, timeframe in pairs:
                    try:
                        result = await asyncio.to_thread(
                            analyze_symbol, symbol, timeframe
                        )
                        if result and result.get("success"):
                            # Cache it
                            self.cache.set_analysis(symbol, timeframe, result)

                            # Build compact message
                            o = result.get("overall", {})
                            msg = sanitize({
                                "type": "analysis",
                                "symbol": symbol,
                                "symbol_fa": result.get("symbol_fa", ""),
                                "timeframe": timeframe,
                                "last_close": result.get("last_close"),
                                "price": result.get("price", {}),
                                "overall": o,
                                "context": result.get("context", {}),
                                "strategies": result.get("strategies", []),
                                "performance": result.get("performance", {}),
                                "time": datetime.now(timezone.utc).isoformat(),
                            })
                            await self.manager.broadcast_to_symbol(
                                symbol, timeframe, msg
                            )
                            logger.debug(
                                f"📡 Analysis broadcast: {symbol}/{timeframe} "
                                f"→ {o.get('signal')} {o.get('confidence')}%"
                            )
                    except Exception as e:
                        logger.error(f"Analysis error {symbol}/{timeframe}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analysis loop error: {e}")

            await asyncio.sleep(ANALYSIS_INTERVAL)

    # ── Cleanup Loop (every 5 min) ─────────────────────

    async def _cleanup_loop(self):
        while self._running:
            try:
                await asyncio.sleep(MEMORY_CLEANUP_INTERVAL)
                self.cache.cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")


# ═══════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════

engine = RealtimeEngine()
