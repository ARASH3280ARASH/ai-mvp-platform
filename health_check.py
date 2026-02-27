"""
Whilber-AI MVP - Health Check Script
=====================================
Verifies all components are working:
  1. Python version
  2. Required packages
  3. MT5 connection
  4. Folder structure
  5. Database access
  6. System resources

Run: python scripts/health_check.py
"""

import sys
import os
import platform
import importlib
from pathlib import Path
from datetime import datetime

# ── Colors for Windows terminal ─────────────────────────────────

os.system("")  # Enable ANSI on Windows

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg):
    print(f"  {GREEN}[OK]{RESET}    {msg}")


def fail(msg):
    print(f"  {RED}[FAIL]{RESET}  {msg}")


def warn(msg):
    print(f"  {YELLOW}[WARN]{RESET}  {msg}")


def info(msg):
    print(f"  {CYAN}[INFO]{RESET}  {msg}")


def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*50}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*50}{RESET}")


# ── Checks ──────────────────────────────────────────────────────

def check_python():
    header("1. Python Version")
    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major == 3 and v.minor == 10:
        ok(f"Python {version_str}")
    elif v.major == 3 and v.minor >= 9:
        warn(f"Python {version_str} (recommended: 3.10.10)")
    else:
        fail(f"Python {version_str} (need 3.10+)")
    info(f"Path: {sys.executable}")


def check_packages():
    header("2. Required Packages")
    packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pandas": "pandas",
        "numpy": "numpy",
        "MetaTrader5": "MetaTrader5",
        "sqlalchemy": "sqlalchemy",
        "pydantic": "pydantic",
        "loguru": "loguru",
        "celery": "celery",
        "redis": "redis",
        "httpx": "httpx",
        "psutil": "psutil",
        "pandas_ta": "pandas_ta",
        "ta": "ta",
        "jose": "python-jose",
    }
    all_ok = True
    for import_name, display_name in packages.items():
        try:
            mod = importlib.import_module(import_name)
            version = getattr(mod, "__version__", "?")
            ok(f"{display_name} ({version})")
        except ImportError:
            fail(f"{display_name} - NOT INSTALLED")
            all_ok = False
    return all_ok


def check_mt5():
    header("3. MetaTrader 5 Connection")

    # Check if MT5 executable exists
    mt5_path = r"C:\Program Files\Moneta Markets MT5 Terminal\terminal64.exe"
    if os.path.exists(mt5_path):
        ok(f"MT5 executable found: {mt5_path}")
    else:
        fail(f"MT5 executable NOT found at: {mt5_path}")
        warn("Make sure MetaTrader 5 is installed at the correct path")
        return False

    # Try to connect
    try:
        import MetaTrader5 as mt5

        initialized = mt5.initialize(path=mt5_path, login=1035360, password="G0Z#IQ1w", server="MonetaMarkets-Demo")
        if not initialized:
            mt5.shutdown()
            initialized = mt5.initialize(mt5_path)
        if initialized:
            ok("MT5 initialized successfully")

            # Get terminal info
            terminal_info = mt5.terminal_info()
            if terminal_info:
                info(f"MT5 Build: {terminal_info.build}")
                info(f"Connected: {terminal_info.connected}")
                info(f"Trade allowed: {terminal_info.trade_allowed}")

            # Get account info
            account_info = mt5.account_info()
            if account_info:
                ok(f"Account: {account_info.login} ({account_info.server})")
                info(f"Balance: {account_info.balance} {account_info.currency}")
            else:
                warn("No account logged in (login to MT5 manually or set credentials)")

            # Quick data test
            import pandas as pd

            rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M1, 0, 5)
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                ok(f"Data extraction works! Got {len(df)} bars for EURUSD M1")
                info(f"Latest bar time: {pd.to_datetime(df['time'].iloc[-1], unit='s')}")
            else:
                warn("Could not fetch EURUSD data - symbol might not be available")
                info("Try with another symbol or check MT5 Market Watch")

            mt5.shutdown()
            ok("MT5 shutdown cleanly")
            return True
        else:
            error_code = mt5.last_error()
            fail(f"MT5 init failed: {error_code}")
            warn("Make sure MT5 is running and logged in")
            return False

    except Exception as e:
        fail(f"MT5 error: {e}")
        return False


def check_folders():
    header("4. Folder Structure")
    project_root = Path(r"C:\Users\Administrator\Desktop\mvp")

    required_dirs = [
        "backend",
        "backend/api",
        "backend/api/routes",
        "backend/api/middleware",
        "backend/engine",
        "backend/indicators",
        "backend/strategies",
        "backend/mt5",
        "backend/models",
        "backend/services",
        "backend/utils",
        "frontend",
        "frontend/src",
        "config",
        "scripts",
        "logs",
        "temp",
        "db",
    ]

    all_ok = True
    for d in required_dirs:
        full_path = project_root / d
        if full_path.exists():
            ok(f"  {d}/")
        else:
            fail(f"  {d}/ - MISSING")
            all_ok = False

    return all_ok


def check_system():
    header("5. System Resources")
    import psutil

    # CPU
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    cpu_percent = psutil.cpu_percent(interval=1)
    ok(f"CPU: {cpu_count} threads @ {cpu_freq.current:.0f} MHz")
    info(f"CPU Usage: {cpu_percent}%")

    if cpu_count >= 8:
        ok(f"Enough threads for parallel processing (recommended workers: {min(cpu_count // 3, 4)})")
    else:
        warn(f"Limited threads ({cpu_count}), recommend max 2 workers")

    # RAM
    ram = psutil.virtual_memory()
    total_gb = ram.total / (1024**3)
    available_gb = ram.available / (1024**3)
    ok(f"RAM: {total_gb:.1f} GB total, {available_gb:.1f} GB available")

    if available_gb < 2:
        warn("Low available RAM! Close other applications before running.")

    # Disk
    disk = psutil.disk_usage("C:\\")
    free_gb = disk.free / (1024**3)
    ok(f"Disk C: {free_gb:.1f} GB free")

    if free_gb < 5:
        warn("Low disk space! Consider cleanup.")

    # Platform
    info(f"OS: {platform.platform()}")
    info(f"Machine: {platform.machine()}")


def check_config():
    header("6. Configuration")
    config_path = Path(r"C:\Users\Administrator\Desktop\mvp\config\settings.py")
    if config_path.exists():
        ok("settings.py exists")

        # Try to import it
        sys.path.insert(0, str(config_path.parent.parent))
        try:
            from config.settings import settings
            ok(f"Settings loaded: {settings.APP_NAME} v{settings.APP_VERSION}")
            info(f"Server: {settings.HOST}:{settings.PORT}")
            info(f"DB: {settings.DATABASE_URL}")
            info(f"MT5: {settings.MT5_PATH}")
        except Exception as e:
            warn(f"Could not import settings: {e}")
    else:
        fail("settings.py NOT found")


# ── Main ────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"{BOLD}  Whilber-AI MVP - Health Check{RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*50}{RESET}")

    check_python()
    packages_ok = check_packages()
    folders_ok = check_folders()
    check_config()
    check_system()

    if packages_ok:
        mt5_ok = check_mt5()
    else:
        warn("\nSkipping MT5 check due to missing packages")
        mt5_ok = False

    # Summary
    header("SUMMARY")
    total = 0
    passed = 0

    for name, status in [
        ("Packages", packages_ok),
        ("Folders", folders_ok),
        ("MT5", mt5_ok),
    ]:
        total += 1
        if status:
            passed += 1
            ok(name)
        else:
            fail(name)

    print(f"\n  Result: {passed}/{total} checks passed")

    if passed == total:
        print(f"\n  {GREEN}{BOLD}All systems go! Ready for Step 0.3{RESET}")
    else:
        print(f"\n  {YELLOW}{BOLD}Fix the issues above before proceeding{RESET}")

    print()


if __name__ == "__main__":
    main()
