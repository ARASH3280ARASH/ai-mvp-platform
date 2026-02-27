"""
Whilber-AI MVP - Configuration Settings
========================================
Central configuration for all project components.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


# ── Project Paths ──────────────────────────────────────────────

PROJECT_ROOT = Path(r"C:\Users\Administrator\Desktop\mvp")
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
TEMP_DIR = PROJECT_ROOT / "temp"
DB_DIR = PROJECT_ROOT / "db"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


class Settings(BaseSettings):
    """Application settings loaded from environment or defaults."""

    # ── App ─────────────────────────────────────────────────
    APP_NAME: str = "Whilber-AI"
    APP_VERSION: str = "0.1.0-mvp"
    DEBUG: bool = True
    SECRET_KEY: str = "whilber-ai-mvp-secret-key-change-in-production"

    # ── Server ──────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1  # uvicorn workers (1 for MVP)
    CORS_ORIGINS: list = ["*"]  # Allow all for MVP, restrict in production

    # ── Database ────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{DB_DIR / 'whilber.db'}"

    # ── MetaTrader 5 ────────────────────────────────────────
    MT5_PATH: str = r"C:\Program Files\Moneta Markets MT5 Terminal\terminal64.exe"
    MT5_LOGIN: Optional[int] = 1035360
    MT5_PASSWORD: Optional[str] = "G0Z#IQ1w"
    MT5_SERVER: Optional[str] = "MonetaMarkets-Demo"
    MT5_TIMEOUT: int = 30000             # Connection timeout in ms
    MT5_PORTABLE: bool = False

    # ── Redis / Celery ──────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── Processing ──────────────────────────────────────────
    MAX_WORKERS: int = 4          # Process pool size
    REQUEST_TIMEOUT: int = 60     # Max seconds per analysis request
    MAX_STRATEGIES: int = 5       # Max strategies per request
    CACHE_TTL: int = 30           # Data cache TTL in seconds

    # ── SMS (OTP) ───────────────────────────────────────────
    SMS_API_KEY: str = ""         # Kavenegar or other SMS provider
    SMS_SENDER: str = ""
    OTP_EXPIRY: int = 120         # OTP valid for 2 minutes

    # ── Payment (Zarinpal / USDT / Card-to-Card) ───────────
    ZARINPAL_MERCHANT_ID: str = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    ZARINPAL_SANDBOX: bool = True
    ZARINPAL_CALLBACK_URL: str = "http://localhost:8000/api/payment/zarinpal-callback"
    USDT_WALLET_ADDRESS: str = "TYourTRC20WalletAddressHere"
    USDT_NETWORK: str = "TRC20"
    CARD_TO_CARD_NUMBER: str = "6037-xxxx-xxxx-xxxx"
    CARD_TO_CARD_HOLDER: str = "نام صاحب حساب"
    CARD_TO_CARD_BANK: str = "بانک ملی"

    # ── Logging ─────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = str(LOGS_DIR / "whilber.log")
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "7 days"

    # ── Data Extraction ─────────────────────────────────────
    # Number of bars to fetch per timeframe
    BARS_COUNT: dict = {
        "M1": 200,
        "M5": 200,
        "M15": 200,
        "M30": 150,
        "H1": 150,
        "H4": 120,
        "D1": 100,
    }

    # ── JWT Secrets ───────────────────────────────────────────
    JWT_SECRET_USER: str = "whilber-ai-user-auth-2026-xK9mQ"
    JWT_SECRET_ADMIN: str = "whilber-ai-admin-2026-secret"

    # ── Admin ───────────────────────────────────────────────
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "whilber2024"  # Change in production!

    class Config:
        env_file = str(CONFIG_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "allow"


# ── Symbol Definitions ──────────────────────────────────────────

FOREX_MAJOR = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "NZDUSD", "USDCAD",
]

FOREX_MINOR = [
    "EURGBP", "EURJPY", "GBPJPY", "EURAUD",
    "EURCAD", "EURCHF", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
    "AUDJPY", "AUDNZD", "AUDCAD", "AUDCHF",
    "NZDJPY", "NZDCAD", "NZDCHF",
    "CADJPY", "CADCHF", "CHFJPY",
]

METALS = [
    "XAUUSD",  # Gold
    "XAGUSD",  # Silver
]

INDICES = [
    "US100",  # Nasdaq
    "US30",   # Dow Jones
    "US500",  # S&P 500
]

CRYPTO = [
    "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD",
    "DOGEUSD", "DOTUSD", "LINKUSD", "LTCUSD", "BCHUSD",
    "AVAXUSD", "UNIUSD", "XLMUSD", "TRXUSD", "ALGOUSD",
    "FILUSD", "NEOUSD", "BATUSD", "IOTAUSD", "ZECUSD",
    "SHBUSD", "HBARUSD", "ONDOUSD", "WIFUSD", "BERAUSD",
    "TRUMPUSD",
]

# ── Display Names (Farsi) ──────────────────────────────────────

CATEGORY_NAMES_FA = {
    "forex": "فارکس",
    "crypto": "کریپتو",
    "metals": "فلزات",
    "indices": "شاخص‌ها",
}

TIMEFRAME_NAMES_FA = {
    "M1": "۱ دقیقه",
    "M5": "۵ دقیقه",
    "M15": "۱۵ دقیقه",
    "M30": "۳۰ دقیقه",
    "H1": "۱ ساعت",
    "H4": "۴ ساعت",
    "D1": "۱ روزه",
}

SYMBOL_NAMES_FA = {
    # Forex Major
    "EURUSD": "یورو/دلار",
    "GBPUSD": "پوند/دلار",
    "USDJPY": "دلار/ین",
    "USDCHF": "دلار/فرانک",
    "AUDUSD": "دلار استرالیا/دلار",
    "NZDUSD": "دلار نیوزلند/دلار",
    "USDCAD": "دلار/دلار کانادا",
    # Metals
    "XAUUSD": "طلا",
    "XAGUSD": "نقره",
    # Indices
    "US100": "نزدک ۱۰۰",
    "US30": "داوجونز ۳۰",
    "US500": "S&P 500",
    # Crypto
    "BTCUSD": "بیت‌کوین",
    "ETHUSD": "اتریوم",
    "SOLUSD": "سولانا",
    "XRPUSD": "ریپل",
    "ADAUSD": "کاردانو",
    "DOGEUSD": "دوج‌کوین",
    "TRUMPUSD": "ترامپ",
}


# ── Singleton Settings Instance ─────────────────────────────────

settings = Settings()
