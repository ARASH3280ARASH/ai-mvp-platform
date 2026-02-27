"""
Whilber-AI MVP - Step 03 Test: Indicator Engine
==================================================
Tests all 8 indicator modules on real MT5 data.
Run: python scripts/test_step03.py
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")
os.system("")

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
    print(f"\n{BOLD}{CYAN}{'='*55}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*55}{RESET}")


def main():
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  Whilber-AI - Indicator Engine Test{RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")

    # ── 1. Connect & Fetch Data ─────────────────────────────
    header("1. Connect MT5 & Fetch Test Data")

    from backend.mt5.mt5_connector import MT5Connector
    from backend.mt5.data_fetcher import fetch_bars, clear_cache

    connector = MT5Connector.get_instance()
    if not connector.connect():
        fail("MT5 connection failed")
        return

    # Fetch EURUSD H1 for testing
    df = fetch_bars("EURUSD", "H1", use_cache=False)
    if df is None or len(df) == 0:
        fail("Could not fetch test data")
        return
    ok(f"Test data: EURUSD H1, {len(df)} bars")

    # Also fetch XAUUSD and BTCUSD for variety
    df_gold = fetch_bars("XAUUSD", "H1", use_cache=False)
    df_btc = fetch_bars("BTCUSD", "H4", use_cache=False)

    results_summary = {}

    # ── 2. Moving Averages ──────────────────────────────────
    header("2. Moving Averages (Step 2.1)")
    try:
        start = time.time()
        from backend.indicators.moving_averages import compute_moving_averages
        ma_results = compute_moving_averages(df)
        elapsed = time.time() - start

        count = len(ma_results)
        ok(f"{count} indicators computed in {elapsed:.3f}s")

        # Check specific values
        assert "ema_9" in ma_results, "Missing ema_9"
        assert "ema_200" in ma_results, "Missing ema_200"
        assert "cross_9_21" in ma_results, "Missing cross"
        assert "ma_stack" in ma_results, "Missing stack"

        last = ma_results["ema_9"].iloc[-1]
        ok(f"EMA 9 last value: {last:.5f}")
        ok(f"EMA 200 last: {ma_results['ema_200'].iloc[-1]:.5f}")

        stack_val = ma_results["ma_stack"].iloc[-1]
        stack_label = {1: "Bullish", -1: "Bearish", 0: "Mixed"}
        ok(f"MA Stack: {stack_label.get(stack_val, '?')}")

        results_summary["Moving Averages"] = True
    except Exception as e:
        fail(f"Error: {e}")
        results_summary["Moving Averages"] = False

    # ── 3. Oscillators ──────────────────────────────────────
    header("3. Oscillators (Step 2.2)")
    try:
        start = time.time()
        from backend.indicators.oscillators import compute_oscillators
        osc_results = compute_oscillators(df)
        elapsed = time.time() - start

        ok(f"{len(osc_results)} indicators in {elapsed:.3f}s")

        rsi_val = osc_results["rsi_14"].iloc[-1]
        stoch_k = osc_results["stoch_k"].iloc[-1]
        cci_val = osc_results["cci_20"].iloc[-1]

        ok(f"RSI(14): {rsi_val:.1f}")
        ok(f"Stoch K: {stoch_k:.1f}")
        ok(f"CCI(20): {cci_val:.1f}")

        zone = {1: "Overbought", -1: "Oversold", 0: "Neutral"}
        ok(f"RSI Zone: {zone[osc_results['rsi_zone'].iloc[-1]]}")

        results_summary["Oscillators"] = True
    except Exception as e:
        fail(f"Error: {e}")
        results_summary["Oscillators"] = False

    # ── 4. MACD ─────────────────────────────────────────────
    header("4. MACD & Derivatives (Step 2.3)")
    try:
        start = time.time()
        from backend.indicators.macd_indicators import compute_macd_indicators
        macd_results = compute_macd_indicators(df)
        elapsed = time.time() - start

        ok(f"{len(macd_results)} indicators in {elapsed:.3f}s")

        ok(f"MACD Line: {macd_results['macd_line'].iloc[-1]:.6f}")
        ok(f"Signal: {macd_results['macd_signal'].iloc[-1]:.6f}")
        ok(f"Histogram: {macd_results['macd_hist'].iloc[-1]:.6f}")

        hist_trend = {1: "Growing+", -1: "Growing-", 2: "Shrinking+", -2: "Shrinking-", 0: "Flat"}
        ok(f"Hist Trend: {hist_trend.get(macd_results['macd_hist_trend'].iloc[-1], '?')}")

        results_summary["MACD"] = True
    except Exception as e:
        fail(f"Error: {e}")
        results_summary["MACD"] = False

    # ── 5. Volatility & Bands ───────────────────────────────
    header("5. Volatility & Bands (Step 2.4)")
    try:
        start = time.time()
        from backend.indicators.volatility import compute_volatility
        vol_results = compute_volatility(df)
        elapsed = time.time() - start

        ok(f"{len(vol_results)} indicators in {elapsed:.3f}s")

        ok(f"ATR(14): {vol_results['atr_14'].iloc[-1]:.5f}")
        ok(f"BB Upper: {vol_results['bb_upper'].iloc[-1]:.5f}")
        ok(f"BB Lower: {vol_results['bb_lower'].iloc[-1]:.5f}")
        ok(f"BB %B: {vol_results['bb_percent_b'].iloc[-1]:.1f}%")

        st_dir = {1: "Bullish", -1: "Bearish"}
        ok(f"SuperTrend: {st_dir.get(vol_results['supertrend_dir'].iloc[-1], '?')}")
        ok(f"PSAR Dir: {st_dir.get(vol_results['psar_dir'].iloc[-1], '?')}")

        sq = "ON (low vol)" if vol_results['squeeze_on'].iloc[-1] == 1 else "OFF"
        ok(f"Squeeze: {sq}")

        results_summary["Volatility"] = True
    except Exception as e:
        fail(f"Error: {e}")
        results_summary["Volatility"] = False

    # ── 6. Volume ───────────────────────────────────────────
    header("6. Volume Indicators (Step 2.5)")
    try:
        start = time.time()
        from backend.indicators.volume_indicators import compute_volume
        volume_results = compute_volume(df)
        elapsed = time.time() - start

        ok(f"{len(volume_results)} indicators in {elapsed:.3f}s")

        ok(f"OBV trend: {volume_results['obv_trend'].iloc[-1]}")
        ok(f"MFI(14): {volume_results['mfi_14'].iloc[-1]:.1f}")
        ok(f"CMF(20): {volume_results['cmf_20'].iloc[-1]:.4f}")
        ok(f"VWAP: {volume_results['vwap'].iloc[-1]:.5f}")

        results_summary["Volume"] = True
    except Exception as e:
        fail(f"Error: {e}")
        results_summary["Volume"] = False

    # ── 7. Trend Strength ───────────────────────────────────
    header("7. Trend Strength (Step 2.6)")
    try:
        start = time.time()
        from backend.indicators.trend_strength import compute_trend_strength
        trend_results = compute_trend_strength(df)
        elapsed = time.time() - start

        ok(f"{len(trend_results)} indicators in {elapsed:.3f}s")

        adx_val = trend_results['adx'].iloc[-1]
        strength = {0: "No Trend", 1: "Weak", 2: "Strong", 3: "Very Strong"}
        ok(f"ADX: {adx_val:.1f} ({strength.get(trend_results['adx_strength'].iloc[-1], '?')})")
        ok(f"+DI: {trend_results['plus_di'].iloc[-1]:.1f}")
        ok(f"-DI: {trend_results['minus_di'].iloc[-1]:.1f}")

        regime = trend_results['regime_label'].iloc[-1]
        ok(f"Market Regime: {regime}")

        results_summary["Trend Strength"] = True
    except Exception as e:
        fail(f"Error: {e}")
        results_summary["Trend Strength"] = False

    # ── 8. Structure ────────────────────────────────────────
    header("8. Market Structure (Step 2.7)")
    try:
        start = time.time()
        from backend.indicators.structure import compute_structure
        struct_results = compute_structure(df)
        elapsed = time.time() - start

        ok(f"Computed in {elapsed:.3f}s")

        sh_count = struct_results['swing_high'].notna().sum()
        sl_count = struct_results['swing_low'].notna().sum()
        ok(f"Swing Highs: {sh_count}, Swing Lows: {sl_count}")

        bos_count = (struct_results['bos'] != 0).sum()
        choch_count = (struct_results['choch'] != 0).sum()
        ok(f"BOS signals: {bos_count}, CHoCH signals: {choch_count}")

        sr = struct_results.get('sr_levels', {})
        sup_count = len(sr.get('support_levels', []))
        res_count = len(sr.get('resistance_levels', []))
        ok(f"S/R levels: {sup_count} support, {res_count} resistance")

        trend_val = struct_results['structure_trend'].iloc[-1]
        trend_label = {1: "Uptrend (HH/HL)", -1: "Downtrend (LH/LL)", 0: "Mixed"}
        ok(f"Structure: {trend_label.get(trend_val, '?')}")

        results_summary["Structure"] = True
    except Exception as e:
        fail(f"Error: {e}")
        results_summary["Structure"] = False

    # ── 9. Candlesticks ─────────────────────────────────────
    header("9. Candlestick Patterns (Step 2.8)")
    try:
        start = time.time()
        from backend.indicators.candlesticks import compute_candlesticks
        candle_results = compute_candlesticks(df)
        elapsed = time.time() - start

        ok(f"{len(candle_results)} indicators in {elapsed:.3f}s")

        patterns = {
            "doji": candle_results["doji"].sum(),
            "hammer": (candle_results["hammer"] == 1).sum(),
            "shooting_star": (candle_results["shooting_star"] == -1).sum(),
            "engulfing_bull": (candle_results["engulfing"] == 1).sum(),
            "engulfing_bear": (candle_results["engulfing"] == -1).sum(),
            "inside_bar": candle_results["inside_bar"].sum(),
            "pin_bar": (candle_results["pin_bar"] != 0).sum(),
            "morning_star": (candle_results["morning_star"] == 1).sum(),
            "evening_star": (candle_results["evening_star"] == -1).sum(),
        }

        for name, count in patterns.items():
            ok(f"{name}: {int(count)} detected")

        results_summary["Candlesticks"] = True
    except Exception as e:
        fail(f"Error: {e}")
        results_summary["Candlesticks"] = False

    # ── 10. Full Pipeline Test ──────────────────────────────
    header("10. Full Pipeline (compute_all_indicators)")
    try:
        from backend.indicators import compute_all_indicators

        start = time.time()
        all_results = compute_all_indicators(df)
        elapsed = time.time() - start

        total_indicators = sum(
            len(v) if isinstance(v, dict) else 1
            for v in all_results.values()
        )

        ok(f"ALL indicators computed in {elapsed:.3f}s")
        ok(f"Total indicator groups: {len(all_results)}")
        ok(f"Total indicators: ~{total_indicators}")

        # Test on gold
        if df_gold is not None:
            start = time.time()
            gold_results = compute_all_indicators(df_gold)
            gold_time = time.time() - start
            ok(f"XAUUSD H1: {gold_time:.3f}s")

        # Test on BTC
        if df_btc is not None:
            start = time.time()
            btc_results = compute_all_indicators(df_btc)
            btc_time = time.time() - start
            ok(f"BTCUSD H4: {btc_time:.3f}s")

        results_summary["Full Pipeline"] = True
    except Exception as e:
        fail(f"Error: {e}")
        import traceback
        traceback.print_exc()
        results_summary["Full Pipeline"] = False

    # ── Cleanup ─────────────────────────────────────────────
    clear_cache()
    connector.disconnect()

    # ── Summary ─────────────────────────────────────────────
    header("FINAL SUMMARY")

    passed = 0
    total = len(results_summary)

    for name, status in results_summary.items():
        if status:
            ok(name)
            passed += 1
        else:
            fail(name)

    print(f"\n  Result: {passed}/{total} modules passed")

    if passed == total:
        print(f"\n  {GREEN}{BOLD}PERFECT! Indicator engine complete!{RESET}")
        print(f"  Next: Build Strategy Modules (Phase 3-14)\n")
    else:
        print(f"\n  {YELLOW}{BOLD}{total - passed} modules need fixing{RESET}\n")


if __name__ == "__main__":
    main()
