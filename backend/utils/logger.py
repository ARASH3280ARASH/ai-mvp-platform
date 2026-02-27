"""
Whilber-AI MVP - Logger Configuration
======================================
Centralized logging with loguru.
"""

import sys
from pathlib import Path
from loguru import logger

# ── Paths ───────────────────────────────────────────────────────

LOGS_DIR = Path(r"C:\Users\Administrator\Desktop\mvp\logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(
    log_level: str = "INFO",
    log_file: str = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
):
    """
    Configure loguru logger for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file. If None, uses default.
        rotation: When to rotate log file.
        retention: How long to keep old logs.
    """

    # Remove default handler
    logger.remove()

    # Console handler (colored, readable)
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File handler (detailed, rotated)
    if log_file is None:
        log_file = str(LOGS_DIR / "whilber.log")

    logger.add(
        log_file,
        level=log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=True,  # Thread-safe
    )

    # Error-only file (for quick debugging)
    logger.add(
        str(LOGS_DIR / "errors.log"),
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}\n{exception}"
        ),
        rotation="5 MB",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
    )

    logger.info("Logger initialized | level={}", log_level)
    return logger


# ── Initialize with defaults ────────────────────────────────────

def get_logger(name: str = "whilber"):
    """Get a named logger instance."""
    return logger.bind(name=name)


# Auto-setup on import
setup_logger()
