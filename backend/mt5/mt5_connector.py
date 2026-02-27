"""
Whilber-AI MVP - MT5 Connector
================================
Singleton connection manager for MetaTrader 5.
Handles connect, disconnect, retry, and health checks.
"""

import time
import threading
import MetaTrader5 as mt5
from pathlib import Path
from loguru import logger

# Load MT5 credentials from settings
try:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from config.settings import settings as _settings
    _MT5_LOGIN = _settings.MT5_LOGIN
    _MT5_PASSWORD = _settings.MT5_PASSWORD
    _MT5_SERVER = _settings.MT5_SERVER
except Exception:
    _MT5_LOGIN = None
    _MT5_PASSWORD = None
    _MT5_SERVER = None


class MT5Connector:
    """
    Thread-safe singleton connector to MetaTrader 5.

    Usage:
        connector = MT5Connector.get_instance()
        connector.connect()
        # ... use mt5 functions ...
        connector.disconnect()
    """

    _instance = None
    _lock = threading.Lock()

    # ── Default Config ──────────────────────────────────────

    MT5_PATH = r"C:\Program Files\Moneta Markets MT5 Terminal\terminal64.exe"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def __init__(self):
        self._connected = False
        self._terminal_info = None
        self._account_info = None

    @classmethod
    def get_instance(cls) -> "MT5Connector":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Connection ──────────────────────────────────────────

    def connect(self, path: str = None, login: int = None,
                password: str = None, server: str = None) -> bool:
        """
        Initialize MT5 connection with retry logic.

        Args:
            path: Path to terminal64.exe (optional, uses default)
            login: MT5 account login (optional, uses already logged in)
            password: MT5 account password (optional)
            server: MT5 server name (optional)

        Returns:
            True if connected successfully
        """
        if self._connected and self.is_healthy():
            logger.debug("MT5 already connected and healthy")
            return True

        mt5_path = path or self.MT5_PATH
        # Use provided credentials or fall back to settings
        _login = login or _MT5_LOGIN
        _password = password or _MT5_PASSWORD
        _server = server or _MT5_SERVER

        if not Path(mt5_path).exists():
            logger.error(f"MT5 executable not found: {mt5_path}")
            return False

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"MT5 connect attempt {attempt}/{self.MAX_RETRIES}")

                # Build init kwargs
                init_kwargs = {"path": mt5_path}
                if _login and _password and _server:
                    init_kwargs["login"] = _login
                    init_kwargs["password"] = _password
                    init_kwargs["server"] = _server

                result = mt5.initialize(**init_kwargs)

                if result:
                    self._connected = True
                    self._terminal_info = mt5.terminal_info()
                    self._account_info = mt5.account_info()

                    if self._account_info:
                        logger.info(
                            f"MT5 connected | Account: {self._account_info.login} | "
                            f"Server: {self._account_info.server} | "
                            f"Balance: {self._account_info.balance}"
                        )
                    else:
                        logger.warning("MT5 initialized but no account logged in")

                    return True
                else:
                    error = mt5.last_error()
                    logger.warning(f"MT5 init failed: {error}")

            except Exception as e:
                logger.error(f"MT5 connect exception: {e}")

            if attempt < self.MAX_RETRIES:
                logger.info(f"Retrying in {self.RETRY_DELAY}s...")
                time.sleep(self.RETRY_DELAY)

        logger.error("MT5 connection failed after all retries")
        self._connected = False
        return False

    def disconnect(self):
        """Shutdown MT5 connection."""
        try:
            mt5.shutdown()
            self._connected = False
            self._terminal_info = None
            self._account_info = None
            logger.info("MT5 disconnected")
        except Exception as e:
            logger.error(f"MT5 disconnect error: {e}")

    def ensure_connected(self) -> bool:
        """Ensure MT5 is connected. Reconnect if needed."""
        if self._connected and self.is_healthy():
            return True
        logger.warning("MT5 not connected or unhealthy, reconnecting...")
        return self.connect()

    # ── Health ──────────────────────────────────────────────

    def is_connected(self) -> bool:
        """Check if MT5 is connected."""
        return self._connected

    def is_healthy(self) -> bool:
        """Check if MT5 connection is alive and working."""
        if not self._connected:
            return False
        try:
            info = mt5.terminal_info()
            if info is None:
                return False
            return info.connected
        except Exception:
            return False

    # ── Info ────────────────────────────────────────────────

    def get_terminal_info(self) -> dict:
        """Get MT5 terminal information."""
        if not self.ensure_connected():
            return {}
        info = mt5.terminal_info()
        if info is None:
            return {}
        return {
            "build": info.build,
            "connected": info.connected,
            "trade_allowed": info.trade_allowed,
            "path": info.path,
        }

    def get_account_info(self) -> dict:
        """Get MT5 account information."""
        if not self.ensure_connected():
            return {}
        info = mt5.account_info()
        if info is None:
            return {}
        return {
            "login": info.login,
            "server": info.server,
            "balance": info.balance,
            "equity": info.equity,
            "currency": info.currency,
            "leverage": info.leverage,
        }

    def get_symbol_info(self, symbol: str) -> dict:
        """Get info for a specific symbol."""
        if not self.ensure_connected():
            return {}
        info = mt5.symbol_info(symbol)
        if info is None:
            return {}
        return {
            "name": info.name,
            "bid": info.bid,
            "ask": info.ask,
            "spread": info.spread,
            "digits": info.digits,
            "trade_mode": info.trade_mode,
            "visible": info.visible,
        }

    def check_symbol_available(self, symbol: str) -> bool:
        """Check if a symbol is available in Market Watch."""
        if not self.ensure_connected():
            return False

        info = mt5.symbol_info(symbol)
        if info is None:
            # Try to enable it
            if mt5.symbol_select(symbol, True):
                logger.info(f"Symbol {symbol} enabled in Market Watch")
                return True
            logger.warning(f"Symbol {symbol} not available")
            return False

        if not info.visible:
            mt5.symbol_select(symbol, True)

        return True
