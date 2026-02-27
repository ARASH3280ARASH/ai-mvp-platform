"""
Whilber-AI — MQL5 Code Generator
====================================
Converts user strategy JSON to complete MQL5 Expert Advisor.
Supports: filters, time-based exit, multi-TP partial close,
configurable direction, multi-symbol EA generation.
"""

from datetime import datetime

# ══════ INDICATOR CODE TEMPLATES ══════

IND_MQL5 = {
    "SMA": {
        "handle": "iMA({symbol},{tf},{period},0,MODE_SMA,{price})",
        "price_map": {"close": "PRICE_CLOSE", "open": "PRICE_OPEN", "high": "PRICE_HIGH", "low": "PRICE_LOW", "hl2": "PRICE_MEDIAN", "hlc3": "PRICE_TYPICAL"},
    },
    "EMA": {
        "handle": "iMA({symbol},{tf},{period},0,MODE_EMA,{price})",
        "price_map": {"close": "PRICE_CLOSE", "open": "PRICE_OPEN", "high": "PRICE_HIGH", "low": "PRICE_LOW", "hl2": "PRICE_MEDIAN", "hlc3": "PRICE_TYPICAL"},
    },
    "WMA": {"handle": "iMA({symbol},{tf},{period},0,MODE_LWMA,PRICE_CLOSE)"},
    "DEMA": {"handle": "iDEMA({symbol},{tf},{period},0,PRICE_CLOSE)"},
    "TEMA": {"handle": "iTEMA({symbol},{tf},{period},0,PRICE_CLOSE)"},
    "RSI": {"handle": "iRSI({symbol},{tf},{period},PRICE_CLOSE)"},
    "STOCH": {"handle": "iStochastic({symbol},{tf},{k_period},{d_period},{slowing},MODE_SMA,STO_LOWHIGH)"},
    "STOCHRSI": {"handle": 'iCustom({symbol},{tf},"StochRSI",{rsi_period},{stoch_period},{k_smooth},{d_smooth})'},
    "CCI": {"handle": "iCCI({symbol},{tf},{period},PRICE_TYPICAL)"},
    "WILLIAMS": {"handle": "iWPR({symbol},{tf},{period})"},
    "MFI": {"handle": "iMFI({symbol},{tf},{period},VOLUME_TICK)"},
    "MACD": {"handle": "iMACD({symbol},{tf},{fast},{slow},{signal},PRICE_CLOSE)"},
    "BB": {"handle": "iBands({symbol},{tf},{period},0,{std_dev},PRICE_CLOSE)"},
    "ATR": {"handle": "iATR({symbol},{tf},{period})"},
    "ADX": {"handle": "iADX({symbol},{tf},{period})"},
    "AROON": {"handle": 'iCustom({symbol},{tf},"Aroon",{period})'},
    "SUPERTREND": {"handle": 'iCustom({symbol},{tf},"SuperTrend",{period},{multiplier})'},
    "PSAR": {"handle": "iSAR({symbol},{tf},{af_start},0.02,{af_max})"},
    "ICHIMOKU": {"handle": "iIchimoku({symbol},{tf},{tenkan},{kijun},{senkou_b})"},
    "VOLUME": {"handle": "iVolumes({symbol},{tf},VOLUME_TICK)"},
    "OBV": {"handle": "iOBV({symbol},{tf},VOLUME_TICK)"},
    "KELTNER": {"handle": 'iCustom({symbol},{tf},"Keltner",{ema_period},{atr_period},{multiplier})'},
    "DONCHIAN": {"handle": 'iCustom({symbol},{tf},"Donchian",{period})'},
}

BUFFER_MAP = {
    "MACD": {"macd": 0, "signal": 1, "histogram": 2},
    "STOCH": {"k": 0, "d": 1},
    "BB": {"upper": 1, "middle": 0, "lower": 2},
    "ADX": {"adx": 0, "plus_di": 1, "minus_di": 2},
    "ICHIMOKU": {"tenkan": 0, "kijun": 1, "senkou_a": 2, "senkou_b": 3, "chikou": 4},
    "AROON": {"up": 0, "down": 1, "oscillator": 2},
    "SUPERTREND": {"trend": 0, "direction": 1},
    "KELTNER": {"upper": 0, "middle": 1, "lower": 2},
    "DONCHIAN": {"upper": 0, "lower": 1, "middle": 2},
}

CONDITION_MQL = {
    "is_above": "{a} > {b}",
    "is_below": "{a} < {b}",
    "crosses_above": "{a_prev} <= {b_prev} && {a} > {b}",
    "crosses_below": "{a_prev} >= {b_prev} && {a} < {b}",
    "is_rising": "{a} > {a_prev}",
    "is_falling": "{a} < {a_prev}",
    "is_overbought": "{a} > {b}",
    "is_oversold": "{a} < {b}",
    "equals": "MathAbs({a} - {b}) < 0.001",
}

CONDITION_INVERSE = {
    "is_above": "is_below",
    "is_below": "is_above",
    "crosses_above": "crosses_below",
    "crosses_below": "crosses_above",
    "is_rising": "is_falling",
    "is_falling": "is_rising",
    "is_overbought": "is_oversold",
    "is_oversold": "is_overbought",
    "equals": "equals",
}

TF_MQL5 = {
    "M1": "PERIOD_M1", "M5": "PERIOD_M5", "M15": "PERIOD_M15",
    "M30": "PERIOD_M30", "H1": "PERIOD_H1", "H4": "PERIOD_H4",
    "D1": "PERIOD_D1", "W1": "PERIOD_W1", "MN1": "PERIOD_MN1",
}


def _get_handle_code(ind_id, params, symbol="_Symbol", tf="PERIOD_CURRENT"):
    """Generate iHandle creation code."""
    tmpl = IND_MQL5.get(ind_id, {}).get("handle", "")
    if not tmpl:
        return f"// Unsupported: {ind_id}"

    price_map = IND_MQL5.get(ind_id, {}).get("price_map", {})
    src = params.get("source", "close")
    price = price_map.get(src, "PRICE_CLOSE")

    code = tmpl.format(
        symbol=symbol, tf=tf, price=price,
        period=params.get("period", 14),
        k_period=params.get("k_period", 14),
        d_period=params.get("d_period", 3),
        slowing=params.get("slowing", 3),
        fast=params.get("fast", 12),
        slow=params.get("slow", 26),
        signal=params.get("signal", 9),
        std_dev=params.get("std_dev", 2.0),
        af_start=params.get("af_start", 0.02),
        af_max=params.get("af_max", 0.2),
        tenkan=params.get("tenkan", 9),
        kijun=params.get("kijun", 26),
        senkou_b=params.get("senkou_b", 52),
        multiplier=params.get("multiplier", 3.0),
        ema_period=params.get("ema_period", 20),
        atr_period=params.get("atr_period", 14),
        rsi_period=params.get("rsi_period", 14),
        stoch_period=params.get("stoch_period", 14),
        k_smooth=params.get("k_smooth", 3),
        d_smooth=params.get("d_smooth", 3),
    )
    return code


def _get_buffer(ind_id, output):
    buffers = BUFFER_MAP.get(ind_id, {})
    return buffers.get(output, 0)


def _tp_dist_expr(tp_config, idx):
    """Return MQL5 expression for TP distance for a given level."""
    tp_type = tp_config.get("type", "atr_tp")
    if tp_type == "atr_tp":
        return f"TP{idx + 1}_Mult * atr_val"
    elif tp_type == "fixed_tp":
        return f"TP{idx + 1}_Pips * point * 10"
    elif tp_type == "percent_tp":
        return f"bid * TP{idx + 1}_Pct / 100.0"
    return "2.0 * atr_val"


def generate_mql5(strategy):
    """Generate complete MQL5 Expert Advisor code."""
    name = strategy.get("name", "MyStrategy")
    desc = strategy.get("description", "")
    direction = strategy.get("direction", "both")
    direction_params = strategy.get("direction_params", {"method": "ma_trend", "ma_period": 200})
    entry_conds = strategy.get("entry_conditions", [])
    entry_logic = strategy.get("entry_logic", "AND")
    tp_configs = strategy.get("exit_take_profit", [])
    sl_configs = strategy.get("exit_stop_loss", [])
    trail = strategy.get("exit_trailing")
    be = strategy.get("exit_break_even")
    time_exit = strategy.get("exit_time")
    filters = strategy.get("filters", [])
    risk = strategy.get("risk", {})

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    logic_op = " && " if entry_logic == "AND" else " || "

    # Multi-TP settings
    tp_count = min(len(tp_configs), 3) if tp_configs else 1
    has_multi_tp = tp_count > 1
    # Compute close percentages
    tp_close_pcts = []
    for i, tc in enumerate(tp_configs[:tp_count]):
        tp_close_pcts.append(tc.get("close_pct", 0))
    if sum(tp_close_pcts) == 0:
        # Auto-split equally
        each = 100 // tp_count
        tp_close_pcts = [each] * tp_count
        tp_close_pcts[-1] = 100 - each * (tp_count - 1)

    # Filter flags
    has_time_filter = any(f.get("type") == "time_filter" for f in filters)
    has_day_filter = any(f.get("type") == "day_filter" for f in filters)
    has_vol_filter = any(f.get("type") == "volatility_filter" for f in filters)
    has_trend_filter = any(f.get("type") == "trend_filter" for f in filters)

    # Direction settings
    dir_method = direction_params.get("method", "ma_trend") if direction == "both" else None
    dir_ma_period = direction_params.get("ma_period", 200) if dir_method == "ma_trend" else 200

    # Needs ManageOpenTrades?
    needs_manage = bool(trail or be or time_exit or has_multi_tp)

    # Collect unique indicators
    indicators = {}
    for i, cond in enumerate(entry_conds):
        ind_id = cond.get("indicator", "")
        params = cond.get("indicator_params", {})
        key = f"h_{ind_id}_{i}"
        indicators[key] = {"id": ind_id, "params": params, "output": cond.get("output", "value")}
        if cond.get("compare_to") == "indicator":
            cmp_id = cond.get("compare_indicator", "")
            cmp_params = cond.get("compare_indicator_params", {})
            ckey = f"h_{cmp_id}_cmp_{i}"
            indicators[ckey] = {"id": cmp_id, "params": cmp_params, "output": cond.get("compare_output", "value")}

    # SL config
    sl_type = sl_configs[0]["type"] if sl_configs else "atr_sl"
    sl_params = sl_configs[0].get("params", {}) if sl_configs else {"multiplier": 1.5}

    # ═══════════ BUILD CODE ═══════════

    # ── HEADER ──
    code = f"""//+------------------------------------------------------------------+
//| {name}.mq5
//| Generated by Whilber-AI Strategy Builder
//| Date: {now}
//| Description: {desc}
//+------------------------------------------------------------------+
#property copyright "Whilber-AI"
#property link      "https://whilber.ai"
#property version   "1.00"
#property strict

#include <Trade\\Trade.mqh>

//--- Input Parameters
input double RiskPercent       = {risk.get('risk_per_trade', 2.0)};    // Risk per trade (%)
input double FixedLot          = {risk.get('fixed_lot', 0.01)};        // Fixed lot size
input int    MaxDailyTrades    = {risk.get('max_daily_trades', 5)};    // Max daily trades
input int    MaxOpenTrades     = {risk.get('max_open_trades', 3)};     // Max open trades
input double MaxDrawdownPct    = {risk.get('max_drawdown', 20)};       // Max drawdown (%)
input double MinRR             = {risk.get('min_rr', 1.5)};           // Min Risk:Reward
input int    MagicNumber       = 12345;                                 // Magic number
input double SpreadLimit       = 5.0;                                   // Max spread (pips)
"""

    # ── TP INPUTS ──
    for i in range(tp_count):
        tc = tp_configs[i] if i < len(tp_configs) else {"type": "atr_tp", "params": {"multiplier": 2}}
        tp_type = tc.get("type", "atr_tp")
        tp_p = tc.get("params", {})
        if tp_type == "atr_tp":
            code += f"input double TP{i + 1}_Mult          = {tp_p.get('multiplier', 2.0)};    // TP{i + 1} ATR multiplier\n"
        elif tp_type == "fixed_tp":
            code += f"input double TP{i + 1}_Pips          = {tp_p.get('pips', 50)};            // TP{i + 1} pips\n"
        elif tp_type == "percent_tp":
            code += f"input double TP{i + 1}_Pct           = {tp_p.get('percent', 1.0)};        // TP{i + 1} percent\n"
        if has_multi_tp:
            code += f"input double TP{i + 1}_ClosePct      = {tp_close_pcts[i]};                // TP{i + 1} close %\n"

    # ── SL INPUTS ──
    if sl_type == "atr_sl":
        code += f"input double SL_ATR_Mult       = {sl_params.get('multiplier', 1.5)};    // SL ATR multiplier\n"
    elif sl_type == "fixed_sl":
        code += f"input double SL_Pips           = {sl_params.get('pips', 30)};            // SL in pips\n"

    # ── TRAILING / BE / TIME EXIT INPUTS ──
    if trail:
        if trail.get("type") == "trailing_fixed":
            code += f"input double TrailingPips      = {trail.get('value', 20)};             // Trailing stop pips\n"
        else:
            code += f"input double TrailATRMult      = {trail.get('value', 2.0)};            // Trailing ATR mult\n"
    if be:
        code += f"input double BE_TriggerPips    = {be.get('trigger', 20)};               // Break even trigger\n"
        code += f"input double BE_LockPips       = {be.get('lock', 5)};                   // Break even lock\n"
    if time_exit:
        code += f"input int    TimeExitBars      = {time_exit.get('bars', 10)};            // Time exit (bars)\n"

    # ── FILTER INPUTS ──
    for f in filters:
        ft = f.get("type", "")
        fp = f.get("params", {})
        if ft == "time_filter":
            code += f"input int    FilterStartHour   = {fp.get('start_hour', 8)};            // Filter: start hour\n"
            code += f"input int    FilterEndHour     = {fp.get('end_hour', 20)};             // Filter: end hour\n"
        elif ft == "day_filter":
            days = fp.get("days", [1, 2, 3, 4, 5])
            code += f'input string FilterDays        = "{",".join(str(d) for d in days)}";   // Filter: allowed days (0=Sun..6=Sat)\n'
        elif ft == "volatility_filter":
            code += f"input double FilterMinATR      = {fp.get('min_atr', 0.0)};            // Filter: min ATR\n"
            code += f"input double FilterMaxATR      = {fp.get('max_atr', 9999.0)};         // Filter: max ATR\n"
            code += f"input int    FilterATRPeriod   = {fp.get('atr_period', 14)};           // Filter: ATR period\n"
        elif ft == "trend_filter":
            tf_str = TF_MQL5.get(fp.get("timeframe", "H4"), "PERIOD_H4")
            code += f"input int    FilterTrendMA     = {fp.get('ma_period', 200)};           // Filter: trend MA period\n"
            code += f"input ENUM_TIMEFRAMES FilterTrendTF = {tf_str};                         // Filter: trend timeframe\n"

    # ── DIRECTION INPUTS ──
    if dir_method == "ma_trend":
        code += f"input int    DirMA_Period      = {dir_ma_period};                       // Direction MA period\n"

    # ── INDICATOR-SPECIFIC INPUTS ──
    for i, cond in enumerate(entry_conds):
        ind_id = cond.get("indicator", "")
        params = cond.get("indicator_params", {})
        for pk, pv in params.items():
            if isinstance(pv, (int, float)):
                dtype = "int" if isinstance(pv, int) else "double"
                code += f"input {dtype}    Ind{i}_{pk} = {pv};  // {ind_id} {pk}\n"

    # ── GLOBAL VARIABLES ──
    code += """
//--- Global Variables
CTrade trade;
int dailyTradeCount = 0;
datetime lastDay = 0;
double initialBalance = 0;
"""

    # Indicator handles
    for key in indicators:
        code += f"int {key} = INVALID_HANDLE;\n"
    code += "int h_ATR_exit = INVALID_HANDLE;\n"
    if dir_method == "ma_trend":
        code += "int h_dir_ma = INVALID_HANDLE;\n"
    if has_vol_filter:
        code += "int h_filter_atr = INVALID_HANDLE;\n"
    if has_trend_filter:
        code += "int h_filter_trend_ma = INVALID_HANDLE;\n"

    # Multi-TP tracking arrays
    if has_multi_tp:
        code += """
//--- Multi-TP Tracking
ulong  _tpTickets[];
int    _tpLevels[];

int _GetTPLevel(ulong ticket)
{
   for(int i = 0; i < ArraySize(_tpTickets); i++)
      if(_tpTickets[i] == ticket) return _tpLevels[i];
   return -1;
}

void _SetTPLevel(ulong ticket, int level)
{
   for(int i = 0; i < ArraySize(_tpTickets); i++)
   {
      if(_tpTickets[i] == ticket) { _tpLevels[i] = level; return; }
   }
   int sz = ArraySize(_tpTickets);
   ArrayResize(_tpTickets, sz + 1);
   ArrayResize(_tpLevels, sz + 1);
   _tpTickets[sz] = ticket;
   _tpLevels[sz] = level;
}

void _RemoveTP(ulong ticket)
{
   for(int i = 0; i < ArraySize(_tpTickets); i++)
   {
      if(_tpTickets[i] == ticket)
      {
         int last = ArraySize(_tpTickets) - 1;
         _tpTickets[i] = _tpTickets[last];
         _tpLevels[i] = _tpLevels[last];
         ArrayResize(_tpTickets, last);
         ArrayResize(_tpLevels, last);
         return;
      }
   }
}
"""

    # ── OnInit ──
    code += """
//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(MagicNumber);
   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);

"""
    for key, info in indicators.items():
        handle_code = _get_handle_code(info["id"], info["params"])
        code += f"   {key} = {handle_code};\n"
        code += f'   if({key} == INVALID_HANDLE) {{ Print("Error creating {key}"); return(INIT_FAILED); }}\n'

    code += "   h_ATR_exit = iATR(_Symbol, PERIOD_CURRENT, 14);\n"
    code += "   if(h_ATR_exit == INVALID_HANDLE) return(INIT_FAILED);\n"

    if dir_method == "ma_trend":
        code += "   h_dir_ma = iMA(_Symbol, PERIOD_CURRENT, DirMA_Period, 0, MODE_SMA, PRICE_CLOSE);\n"
        code += '   if(h_dir_ma == INVALID_HANDLE) { Print("Error: direction MA"); return(INIT_FAILED); }\n'

    if has_vol_filter:
        code += "   h_filter_atr = iATR(_Symbol, PERIOD_CURRENT, FilterATRPeriod);\n"
        code += '   if(h_filter_atr == INVALID_HANDLE) { Print("Error: filter ATR"); return(INIT_FAILED); }\n'

    if has_trend_filter:
        code += "   h_filter_trend_ma = iMA(_Symbol, FilterTrendTF, FilterTrendMA, 0, MODE_SMA, PRICE_CLOSE);\n"
        code += '   if(h_filter_trend_ma == INVALID_HANDLE) { Print("Error: filter trend MA"); return(INIT_FAILED); }\n'

    code += f"""
   Print("EA initialized: {name}");
   return(INIT_SUCCEEDED);
}}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{{
"""
    for key in indicators:
        code += f"   if({key} != INVALID_HANDLE) IndicatorRelease({key});\n"
    code += "   if(h_ATR_exit != INVALID_HANDLE) IndicatorRelease(h_ATR_exit);\n"
    if dir_method == "ma_trend":
        code += "   if(h_dir_ma != INVALID_HANDLE) IndicatorRelease(h_dir_ma);\n"
    if has_vol_filter:
        code += "   if(h_filter_atr != INVALID_HANDLE) IndicatorRelease(h_filter_atr);\n"
    if has_trend_filter:
        code += "   if(h_filter_trend_ma != INVALID_HANDLE) IndicatorRelease(h_filter_trend_ma);\n"
    code += "}\n"

    # ── HELPER FUNCTIONS ──
    code += """
//+------------------------------------------------------------------+
//| Get indicator value                                                |
//+------------------------------------------------------------------+
double GetIndValue(int handle, int buffer, int shift)
{
   double val[];
   if(CopyBuffer(handle, buffer, shift, 1, val) <= 0) return(EMPTY_VALUE);
   return(val[0]);
}

//+------------------------------------------------------------------+
//| Count open positions                                               |
//+------------------------------------------------------------------+
int CountPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionSelectByTicket(PositionGetTicket(i)))
         if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Calculate lot size based on risk                                   |
//+------------------------------------------------------------------+
double CalcLotSize(double slPips)
{
   if(slPips <= 0) return FixedLot;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * RiskPercent / 100.0;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   if(tickValue <= 0 || tickSize <= 0) return FixedLot;
   double lots = riskAmount / (slPips / tickSize * tickValue);
   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMax(minLot, MathMin(maxLot, lots));
   return NormalizeDouble(lots, 2);
}

"""

    # ── ManageOpenTrades ──
    if needs_manage:
        code += """//+------------------------------------------------------------------+
//| Manage trailing stop, break even, time exit, partial TP            |
//+------------------------------------------------------------------+
void ManageOpenTrades()
{
   double atr = GetIndValue(h_ATR_exit, 0, 1);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionSelectByTicket(PositionGetTicket(i))) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      ulong ticket = PositionGetTicket(i);
      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
"""

        # Time-based exit
        if time_exit:
            code += """
      // Time-based exit
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int barsSinceOpen = Bars(_Symbol, PERIOD_CURRENT, openTime, TimeCurrent());
      if(barsSinceOpen >= TimeExitBars)
      {
         trade.PositionClose(ticket);
         continue;
      }
"""

        # Multi-TP partial close
        if has_multi_tp:
            code += "\n      // Multi-TP partial close\n"
            code += "      int tpLevel = _GetTPLevel(ticket);\n"
            code += "      if(tpLevel < 0) { _SetTPLevel(ticket, 0); tpLevel = 0; }\n"
            for ti in range(tp_count - 1):  # intermediate levels only
                tc = tp_configs[ti] if ti < len(tp_configs) else {"type": "atr_tp", "params": {"multiplier": 2}}
                dist_expr = _tp_dist_expr(tc, ti)
                pct = tp_close_pcts[ti]
                code += f"      if(tpLevel == {ti})\n"
                code += "      {\n"
                code += f"         double tpDist_{ti} = {dist_expr};\n"
                code += f"         bool tpHit = isBuy ? (bid >= openPrice + tpDist_{ti}) : (ask <= openPrice - tpDist_{ti});\n"
                code += "         if(tpHit)\n"
                code += "         {\n"
                code += "            double volume = PositionGetDouble(POSITION_VOLUME);\n"
                code += f"            double closeVol = NormalizeDouble(volume * {pct} / 100.0, 2);\n"
                code += "            double minVol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);\n"
                code += "            if(closeVol >= minVol)\n"
                code += "            {\n"
                code += "               trade.PositionClosePartial(ticket, closeVol);\n"
                code += f"               _SetTPLevel(ticket, {ti + 1});\n"
                code += "            }\n"
                code += "         }\n"
                code += "      }\n"

        # Break even
        if be:
            code += """
      // Break Even
      double beTrigger = BE_TriggerPips * point * 10;
      double beLock = BE_LockPips * point * 10;
      if(isBuy)
      {
         if(bid >= openPrice + beTrigger && currentSL < openPrice + beLock)
            trade.PositionModify(ticket, openPrice + beLock, currentTP);
      }
      else
      {
         if(ask <= openPrice - beTrigger && (currentSL > openPrice - beLock || currentSL == 0))
            trade.PositionModify(ticket, openPrice - beLock, currentTP);
      }
"""

        # Trailing stop
        if trail:
            if trail.get("type") == "trailing_fixed":
                code += """
      // Trailing Stop (Fixed)
      double trailDist = TrailingPips * point * 10;
"""
            else:
                code += """
      // Trailing Stop (ATR)
      double trailDist = TrailATRMult * atr;
"""
            code += """      if(isBuy)
      {
         double newSL = bid - trailDist;
         if(newSL > currentSL && newSL > openPrice)
            trade.PositionModify(ticket, newSL, currentTP);
      }
      else
      {
         double newSL = ask + trailDist;
         if((newSL < currentSL || currentSL == 0) && newSL < openPrice)
            trade.PositionModify(ticket, newSL, currentTP);
      }
"""

        code += """   }
}

"""

    # ── OnTick ──
    code += """//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   // Daily trade counter reset
   MqlDateTime dt;
   TimeCurrent(dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != lastDay) { dailyTradeCount = 0; lastDay = today; }

"""
    if needs_manage:
        code += "   ManageOpenTrades();\n\n"

    code += """   // Check limits
   if(dailyTradeCount >= MaxDailyTrades) return;
   if(CountPositions() >= MaxOpenTrades) return;

   // Drawdown check
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(balance < initialBalance * (1.0 - MaxDrawdownPct / 100.0)) return;

   // Spread check
   double spread = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(spread / point / 10.0 > SpreadLimit) return;

"""

    # ── FILTER CHECKS (before new bar check to save computation) ──
    if has_time_filter:
        code += "   // Time filter\n"
        code += "   if(dt.hour < FilterStartHour || dt.hour > FilterEndHour) return;\n\n"

    if has_day_filter:
        code += """   // Day filter
   {
      string daysStr = FilterDays;
      bool dayAllowed = false;
      string parts[];
      int cnt = StringSplit(daysStr, ',', parts);
      for(int d = 0; d < cnt; d++)
         if((int)StringToInteger(parts[d]) == dt.day_of_week) { dayAllowed = true; break; }
      if(!dayAllowed) return;
   }

"""

    if has_vol_filter:
        code += "   // Volatility filter\n"
        code += "   {\n"
        code += "      double fATR = GetIndValue(h_filter_atr, 0, 1);\n"
        code += "      if(fATR < FilterMinATR || fATR > FilterMaxATR) return;\n"
        code += "   }\n\n"

    code += """   // New bar check
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(currentBarTime == lastBarTime) return;
   lastBarTime = currentBarTime;

   // Get indicator values
"""

    # Get values for each indicator
    for i, cond in enumerate(entry_conds):
        ind_id = cond.get("indicator", "")
        output = cond.get("output", "value")
        key = f"h_{ind_id}_{i}"
        buf = _get_buffer(ind_id, output)
        code += f"   double val_{i} = GetIndValue({key}, {buf}, 1);\n"
        code += f"   double val_{i}_prev = GetIndValue({key}, {buf}, 2);\n"

        if cond.get("compare_to") == "indicator":
            cmp_id = cond.get("compare_indicator", "")
            cmp_output = cond.get("compare_output", "value")
            ckey = f"h_{cmp_id}_cmp_{i}"
            cbuf = _get_buffer(cmp_id, cmp_output)
            code += f"   double cmp_{i} = GetIndValue({ckey}, {cbuf}, 1);\n"
            code += f"   double cmp_{i}_prev = GetIndValue({ckey}, {cbuf}, 2);\n"

    code += "   double atr_val = GetIndValue(h_ATR_exit, 0, 1);\n"
    code += "   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);\n"
    code += "   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);\n\n"

    # Build entry conditions
    cond_parts = []
    for i, cond in enumerate(entry_conds):
        ct = cond.get("condition", "")
        cmp_to = cond.get("compare_to", "fixed_value")

        a = f"val_{i}"
        a_prev = f"val_{i}_prev"
        if cmp_to == "fixed_value":
            b = str(float(cond.get("compare_value", 0)))
            b_prev = b
        elif cmp_to == "indicator":
            b = f"cmp_{i}"
            b_prev = f"cmp_{i}_prev"
        elif cmp_to == "price_close":
            b = "iClose(_Symbol, PERIOD_CURRENT, 1)"
            b_prev = "iClose(_Symbol, PERIOD_CURRENT, 2)"
        else:
            b = "bid"
            b_prev = "bid"

        tmpl = CONDITION_MQL.get(ct, "{a} > {b}")
        expr = tmpl.format(a=a, b=b, a_prev=a_prev, b_prev=b_prev)
        cond_parts.append(f"({expr})")

    if cond_parts:
        signal_expr = logic_op.join(cond_parts)
    else:
        signal_expr = "false"

    code += f"   // Entry signal\n"
    code += f"   bool entrySignal = ({signal_expr});\n"

    # ── DIRECTION LOGIC ──
    code += "\n   // Determine direction\n"
    if direction == "buy_only":
        code += "   if(!entrySignal) return;\n"
        code += "   bool goBuy = true;\n   bool goSell = false;\n"
    elif direction == "sell_only":
        code += "   if(!entrySignal) return;\n"
        code += "   bool goBuy = false;\n   bool goSell = true;\n"
    elif dir_method == "ma_trend":
        code += "   if(!entrySignal) return;\n"
        code += "   double dirMA = GetIndValue(h_dir_ma, 0, 1);\n"
        code += "   bool goBuy = (bid > dirMA);\n"
        code += "   bool goSell = (bid <= dirMA);\n"
    elif dir_method == "entry_signal":
        # Build inverse conditions for sell
        inv_parts = []
        for i, cond in enumerate(entry_conds):
            ct = cond.get("condition", "")
            inv_ct = CONDITION_INVERSE.get(ct, ct)
            cmp_to = cond.get("compare_to", "fixed_value")
            a = f"val_{i}"
            a_prev = f"val_{i}_prev"
            if cmp_to == "fixed_value":
                b = str(float(cond.get("compare_value", 0)))
                b_prev = b
            elif cmp_to == "indicator":
                b = f"cmp_{i}"
                b_prev = f"cmp_{i}_prev"
            elif cmp_to == "price_close":
                b = "iClose(_Symbol, PERIOD_CURRENT, 1)"
                b_prev = "iClose(_Symbol, PERIOD_CURRENT, 2)"
            else:
                b = "bid"
                b_prev = "bid"
            tmpl = CONDITION_MQL.get(inv_ct, "{a} < {b}")
            expr = tmpl.format(a=a, b=b, a_prev=a_prev, b_prev=b_prev)
            inv_parts.append(f"({expr})")
        inv_expr = logic_op.join(inv_parts) if inv_parts else "false"
        code += f"   bool sellSignal = ({inv_expr});\n"
        code += "   if(!entrySignal && !sellSignal) return;\n"
        code += "   bool goBuy = entrySignal;\n"
        code += "   bool goSell = sellSignal && !entrySignal;\n"
    elif dir_method == "always_both":
        code += "   if(!entrySignal) return;\n"
        code += "   bool goBuy = true;\n   bool goSell = true;\n"
    else:
        # Default: MA trend with period 200
        code += "   if(!entrySignal) return;\n"
        code += "   double dirMA = GetIndValue(h_dir_ma, 0, 1);\n"
        code += "   bool goBuy = (bid > dirMA);\n"
        code += "   bool goSell = (bid <= dirMA);\n"

    # Trend filter (applied after direction is determined)
    if has_trend_filter:
        code += "\n   // Trend filter\n"
        code += "   double trendMA = GetIndValue(h_filter_trend_ma, 0, 1);\n"
        code += "   if(goBuy && bid < trendMA) goBuy = false;\n"
        code += "   if(goSell && bid > trendMA) goSell = false;\n"
        code += "   if(!goBuy && !goSell) return;\n"

    # ── TP/SL CALCULATION ──
    code += "\n   // Calculate TP and SL distances\n"

    # SL
    if sl_type == "atr_sl":
        code += "   double slDist = SL_ATR_Mult * atr_val;\n"
    elif sl_type == "fixed_sl":
        code += "   double slDist = SL_Pips * point * 10;\n"
    else:
        code += "   double slDist = 1.5 * atr_val;\n"

    # TP (use last level for order TP, intermediate levels managed in ManageOpenTrades)
    if has_multi_tp:
        # Last TP level for order TP
        last_tc = tp_configs[tp_count - 1] if tp_count - 1 < len(tp_configs) else {"type": "atr_tp", "params": {"multiplier": 3}}
        code += f"   double tpDist = {_tp_dist_expr(last_tc, tp_count - 1)};\n"
    else:
        tc0 = tp_configs[0] if tp_configs else {"type": "atr_tp", "params": {"multiplier": 2}}
        tp0_type = tc0.get("type", "atr_tp")
        if tp0_type == "atr_tp":
            code += "   double tpDist = TP1_Mult * atr_val;\n"
        elif tp0_type == "fixed_tp":
            code += "   double tpDist = TP1_Pips * point * 10;\n"
        elif tp0_type == "percent_tp":
            code += "   double tpDist = bid * TP1_Pct / 100.0;\n"
        else:
            code += "   double tpDist = 2.0 * atr_val;\n"

    code += """
   if(slDist <= 0 || tpDist <= 0) return;
   double rr = tpDist / slDist;
   if(rr < MinRR) return;

   double lotSize = CalcLotSize(slDist / point);
"""

    # ── EXECUTE TRADE ──
    open_comment = name.replace('"', "'")
    if dir_method == "always_both":
        code += f"""
   // Execute both directions
   if(goBuy)
   {{
      double tp = ask + tpDist;
      double sl = ask - slDist;
      if(trade.Buy(lotSize, _Symbol, ask, sl, tp, "{open_comment} BUY"))
         dailyTradeCount++;
   }}
   if(goSell)
   {{
      double tp = bid - tpDist;
      double sl = bid + slDist;
      if(trade.Sell(lotSize, _Symbol, bid, sl, tp, "{open_comment} SELL"))
         dailyTradeCount++;
   }}
"""
    else:
        code += f"""
   // Execute trade
   if(goBuy)
   {{
      double tp = ask + tpDist;
      double sl = ask - slDist;
      if(trade.Buy(lotSize, _Symbol, ask, sl, tp, "{open_comment} BUY"))
         dailyTradeCount++;
   }}
   else if(goSell)
   {{
      double tp = bid - tpDist;
      double sl = bid + slDist;
      if(trade.Sell(lotSize, _Symbol, bid, sl, tp, "{open_comment} SELL"))
         dailyTradeCount++;
   }}
"""

    code += """}
//+------------------------------------------------------------------+
"""
    return code


def generate_mql5_multi(strategy, symbols_list):
    """Generate multi-symbol MQL5 EA that trades multiple symbols."""
    name = strategy.get("name", "MyStrategy")
    desc = strategy.get("description", "")
    direction = strategy.get("direction", "both")
    direction_params = strategy.get("direction_params", {"method": "ma_trend", "ma_period": 200})
    entry_conds = strategy.get("entry_conditions", [])
    entry_logic = strategy.get("entry_logic", "AND")
    tp_configs = strategy.get("exit_take_profit", [])
    sl_configs = strategy.get("exit_stop_loss", [])
    trail = strategy.get("exit_trailing")
    be = strategy.get("exit_break_even")
    time_exit = strategy.get("exit_time")
    filters = strategy.get("filters", [])
    risk = strategy.get("risk", {})

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    logic_op = " && " if entry_logic == "AND" else " || "
    num_sym = len(symbols_list)

    # Filter flags
    has_time_filter = any(f.get("type") == "time_filter" for f in filters)
    has_day_filter = any(f.get("type") == "day_filter" for f in filters)
    has_vol_filter = any(f.get("type") == "volatility_filter" for f in filters)
    has_trend_filter = any(f.get("type") == "trend_filter" for f in filters)

    dir_method = direction_params.get("method", "ma_trend") if direction == "both" else None
    dir_ma_period = direction_params.get("ma_period", 200)

    sl_type = sl_configs[0]["type"] if sl_configs else "atr_sl"
    sl_params = sl_configs[0].get("params", {}) if sl_configs else {"multiplier": 1.5}
    tp_type = tp_configs[0]["type"] if tp_configs else "atr_tp"
    tp_params = tp_configs[0].get("params", {}) if tp_configs else {"multiplier": 2}

    # Collect entry indicators
    ind_list = []
    for i, cond in enumerate(entry_conds):
        ind_list.append({"id": cond.get("indicator", ""), "params": cond.get("indicator_params", {}), "output": cond.get("output", "value")})
        if cond.get("compare_to") == "indicator":
            ind_list.append({"id": cond.get("compare_indicator", ""), "params": cond.get("compare_indicator_params", {}), "output": cond.get("compare_output", "value")})

    symbols_str = ",".join(symbols_list)

    code = f"""//+------------------------------------------------------------------+
//| {name}_Multi.mq5
//| Generated by Whilber-AI Strategy Builder (Multi-Symbol)
//| Date: {now}
//| Symbols: {symbols_str}
//| Description: {desc}
//+------------------------------------------------------------------+
#property copyright "Whilber-AI"
#property link      "https://whilber.ai"
#property version   "1.00"
#property strict

#include <Trade\\Trade.mqh>

//--- Input Parameters
input double RiskPercent       = {risk.get('risk_per_trade', 2.0)};
input double FixedLot          = {risk.get('fixed_lot', 0.01)};
input int    MaxDailyTrades    = {risk.get('max_daily_trades', 5)};
input int    MaxOpenTrades     = {risk.get('max_open_trades', 3)};
input double MaxDrawdownPct    = {risk.get('max_drawdown', 20)};
input double MinRR             = {risk.get('min_rr', 1.5)};
input int    BaseMagicNumber   = 12345;
input double SpreadLimit       = 5.0;
"""

    # TP/SL inputs
    if tp_type == "atr_tp":
        code += f"input double TP_ATR_Mult       = {tp_params.get('multiplier', 2.0)};\n"
    elif tp_type == "fixed_tp":
        code += f"input double TP_Pips           = {tp_params.get('pips', 50)};\n"
    if sl_type == "atr_sl":
        code += f"input double SL_ATR_Mult       = {sl_params.get('multiplier', 1.5)};\n"
    elif sl_type == "fixed_sl":
        code += f"input double SL_Pips           = {sl_params.get('pips', 30)};\n"

    if trail:
        if trail.get("type") == "trailing_fixed":
            code += f"input double TrailingPips      = {trail.get('value', 20)};\n"
        else:
            code += f"input double TrailATRMult      = {trail.get('value', 2.0)};\n"
    if be:
        code += f"input double BE_TriggerPips    = {be.get('trigger', 20)};\n"
        code += f"input double BE_LockPips       = {be.get('lock', 5)};\n"
    if time_exit:
        code += f"input int    TimeExitBars      = {time_exit.get('bars', 10)};\n"

    # Filter inputs
    for f in filters:
        ft = f.get("type", "")
        fp = f.get("params", {})
        if ft == "time_filter":
            code += f"input int    FilterStartHour   = {fp.get('start_hour', 8)};\n"
            code += f"input int    FilterEndHour     = {fp.get('end_hour', 20)};\n"
        elif ft == "day_filter":
            days = fp.get("days", [1, 2, 3, 4, 5])
            code += f'input string FilterDays        = "{",".join(str(d) for d in days)}";\n'
        elif ft == "volatility_filter":
            code += f"input double FilterMinATR      = {fp.get('min_atr', 0.0)};\n"
            code += f"input double FilterMaxATR      = {fp.get('max_atr', 9999.0)};\n"
            code += f"input int    FilterATRPeriod   = {fp.get('atr_period', 14)};\n"
        elif ft == "trend_filter":
            tf_str = TF_MQL5.get(fp.get("timeframe", "H4"), "PERIOD_H4")
            code += f"input int    FilterTrendMA     = {fp.get('ma_period', 200)};\n"
            code += f"input ENUM_TIMEFRAMES FilterTrendTF = {tf_str};\n"

    if dir_method == "ma_trend":
        code += f"input int    DirMA_Period      = {dir_ma_period};\n"

    # Globals
    code += f"""
//--- Multi-Symbol Setup
#define NUM_SYMBOLS {num_sym}
string SymbolList[NUM_SYMBOLS] = {{{", ".join('"' + s + '"' for s in symbols_list)}}};

//--- Per-symbol handles
CTrade trade;
int dailyTradeCount = 0;
datetime lastDay = 0;
double initialBalance = 0;
"""

    # Handle arrays per indicator per symbol
    num_inds = len(ind_list)
    code += f"int h_ind[NUM_SYMBOLS][{max(num_inds, 1)}];  // indicator handles per symbol\n"
    code += "int h_atr[NUM_SYMBOLS];     // ATR handles per symbol\n"
    if dir_method == "ma_trend":
        code += "int h_dir[NUM_SYMBOLS];     // Direction MA handles\n"
    if has_vol_filter:
        code += "int h_filt_atr[NUM_SYMBOLS];\n"
    if has_trend_filter:
        code += "int h_filt_ma[NUM_SYMBOLS];\n"

    # OnInit
    code += """
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(BaseMagicNumber);
   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   for(int s = 0; s < NUM_SYMBOLS; s++)
   {
      string sym = SymbolList[s];
      if(!SymbolSelect(sym, true))
      {
         PrintFormat("Warning: Cannot select symbol %s", sym);
         continue;
      }
"""

    for idx, ind in enumerate(ind_list):
        handle_code = _get_handle_code(ind["id"], ind["params"], "sym", "PERIOD_CURRENT")
        code += f"      h_ind[s][{idx}] = {handle_code};\n"

    code += "      h_atr[s] = iATR(sym, PERIOD_CURRENT, 14);\n"
    if dir_method == "ma_trend":
        code += "      h_dir[s] = iMA(sym, PERIOD_CURRENT, DirMA_Period, 0, MODE_SMA, PRICE_CLOSE);\n"
    if has_vol_filter:
        code += "      h_filt_atr[s] = iATR(sym, PERIOD_CURRENT, FilterATRPeriod);\n"
    if has_trend_filter:
        code += "      h_filt_ma[s] = iMA(sym, FilterTrendTF, FilterTrendMA, 0, MODE_SMA, PRICE_CLOSE);\n"

    code += f"""   }}

   Print("Multi-Symbol EA initialized: {name} ({num_sym} symbols)");
   return(INIT_SUCCEEDED);
}}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{{
   for(int s = 0; s < NUM_SYMBOLS; s++)
   {{
"""
    for idx in range(num_inds):
        code += f"      if(h_ind[s][{idx}] != INVALID_HANDLE) IndicatorRelease(h_ind[s][{idx}]);\n"
    code += "      if(h_atr[s] != INVALID_HANDLE) IndicatorRelease(h_atr[s]);\n"
    if dir_method == "ma_trend":
        code += "      if(h_dir[s] != INVALID_HANDLE) IndicatorRelease(h_dir[s]);\n"
    if has_vol_filter:
        code += "      if(h_filt_atr[s] != INVALID_HANDLE) IndicatorRelease(h_filt_atr[s]);\n"
    if has_trend_filter:
        code += "      if(h_filt_ma[s] != INVALID_HANDLE) IndicatorRelease(h_filt_ma[s]);\n"
    code += "   }\n}\n"

    # Helper functions
    code += """
double GetIndValue(int handle, int buffer, int shift)
{
   double val[];
   if(CopyBuffer(handle, buffer, shift, 1, val) <= 0) return(EMPTY_VALUE);
   return(val[0]);
}

int CountPositions(int magic)
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionSelectByTicket(PositionGetTicket(i)))
         if(PositionGetInteger(POSITION_MAGIC) == magic)
            count++;
   }
   return count;
}

double CalcLotSize(string sym, double slPips)
{
   if(slPips <= 0) return FixedLot;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * RiskPercent / 100.0;
   double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double lotStep = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(tickValue <= 0 || tickSize <= 0) return FixedLot;
   double lots = riskAmount / (slPips / tickSize * tickValue);
   lots = MathFloor(lots / lotStep) * lotStep;
   return NormalizeDouble(MathMax(minLot, MathMin(maxLot, lots)), 2);
}

"""

    # OnTick - iterate over all symbols
    code += """//+------------------------------------------------------------------+
void OnTick()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != lastDay) { dailyTradeCount = 0; lastDay = today; }

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(balance < initialBalance * (1.0 - MaxDrawdownPct / 100.0)) return;
   if(dailyTradeCount >= MaxDailyTrades) return;
"""

    if has_time_filter:
        code += "   if(dt.hour < FilterStartHour || dt.hour > FilterEndHour) return;\n"
    if has_day_filter:
        code += """   {
      string daysStr = FilterDays;
      bool dayAllowed = false;
      string parts[];
      int cnt = StringSplit(daysStr, ',', parts);
      for(int d = 0; d < cnt; d++)
         if((int)StringToInteger(parts[d]) == dt.day_of_week) { dayAllowed = true; break; }
      if(!dayAllowed) return;
   }
"""

    code += """
   for(int s = 0; s < NUM_SYMBOLS; s++)
   {
      string sym = SymbolList[s];
      int magic = BaseMagicNumber + s;
      trade.SetExpertMagicNumber(magic);

      if(CountPositions(magic) >= MaxOpenTrades) continue;

      // Spread check
      double symAsk = SymbolInfoDouble(sym, SYMBOL_ASK);
      double symBid = SymbolInfoDouble(sym, SYMBOL_BID);
      double symPoint = SymbolInfoDouble(sym, SYMBOL_POINT);
      if(symPoint <= 0) continue;
      double symSpread = (symAsk - symBid) / symPoint / 10.0;
      if(symSpread > SpreadLimit) continue;
"""

    if has_vol_filter:
        code += "      double fATR = GetIndValue(h_filt_atr[s], 0, 1);\n"
        code += "      if(fATR < FilterMinATR || fATR > FilterMaxATR) continue;\n"

    code += """
      // New bar check per symbol
      static datetime lastBars[];
      if(ArraySize(lastBars) < NUM_SYMBOLS) ArrayResize(lastBars, NUM_SYMBOLS);
      datetime curBar = iTime(sym, PERIOD_CURRENT, 0);
      if(curBar == lastBars[s]) continue;
      lastBars[s] = curBar;

      // Get indicator values
"""

    # Get indicator values per symbol
    ind_idx = 0
    for i, cond in enumerate(entry_conds):
        buf = _get_buffer(cond.get("indicator", ""), cond.get("output", "value"))
        code += f"      double val_{i} = GetIndValue(h_ind[s][{ind_idx}], {buf}, 1);\n"
        code += f"      double val_{i}_prev = GetIndValue(h_ind[s][{ind_idx}], {buf}, 2);\n"
        ind_idx += 1
        if cond.get("compare_to") == "indicator":
            cbuf = _get_buffer(cond.get("compare_indicator", ""), cond.get("compare_output", "value"))
            code += f"      double cmp_{i} = GetIndValue(h_ind[s][{ind_idx}], {cbuf}, 1);\n"
            code += f"      double cmp_{i}_prev = GetIndValue(h_ind[s][{ind_idx}], {cbuf}, 2);\n"
            ind_idx += 1

    code += "      double atr_val = GetIndValue(h_atr[s], 0, 1);\n\n"

    # Build conditions
    cond_parts = []
    for i, cond in enumerate(entry_conds):
        ct = cond.get("condition", "")
        cmp_to = cond.get("compare_to", "fixed_value")
        a, a_prev = f"val_{i}", f"val_{i}_prev"
        if cmp_to == "fixed_value":
            b = str(float(cond.get("compare_value", 0)))
            b_prev = b
        elif cmp_to == "indicator":
            b, b_prev = f"cmp_{i}", f"cmp_{i}_prev"
        else:
            b, b_prev = "iClose(sym,PERIOD_CURRENT,1)", "iClose(sym,PERIOD_CURRENT,2)"
        tmpl = CONDITION_MQL.get(ct, "{a} > {b}")
        cond_parts.append("(" + tmpl.format(a=a, b=b, a_prev=a_prev, b_prev=b_prev) + ")")

    sig = logic_op.join(cond_parts) if cond_parts else "false"
    code += f"      bool entrySignal = ({sig});\n"
    code += "      if(!entrySignal) continue;\n\n"

    # Direction
    if direction == "buy_only":
        code += "      bool goBuy = true; bool goSell = false;\n"
    elif direction == "sell_only":
        code += "      bool goBuy = false; bool goSell = true;\n"
    elif dir_method == "ma_trend":
        code += "      double dirMA = GetIndValue(h_dir[s], 0, 1);\n"
        code += "      bool goBuy = (symBid > dirMA); bool goSell = (symBid <= dirMA);\n"
    else:
        code += "      bool goBuy = true; bool goSell = true;\n"

    if has_trend_filter:
        code += "      double trendMA = GetIndValue(h_filt_ma[s], 0, 1);\n"
        code += "      if(goBuy && symBid < trendMA) goBuy = false;\n"
        code += "      if(goSell && symBid > trendMA) goSell = false;\n"
        code += "      if(!goBuy && !goSell) continue;\n"

    # TP/SL
    if tp_type == "atr_tp":
        code += "      double tpDist = TP_ATR_Mult * atr_val;\n"
    elif tp_type == "fixed_tp":
        code += "      double tpDist = TP_Pips * symPoint * 10;\n"
    else:
        code += "      double tpDist = 2.0 * atr_val;\n"

    if sl_type == "atr_sl":
        code += "      double slDist = SL_ATR_Mult * atr_val;\n"
    elif sl_type == "fixed_sl":
        code += "      double slDist = SL_Pips * symPoint * 10;\n"
    else:
        code += "      double slDist = 1.5 * atr_val;\n"

    open_comment = name.replace('"', "'")
    code += f"""
      if(slDist <= 0 || tpDist <= 0) continue;
      if(tpDist / slDist < MinRR) continue;
      double lots = CalcLotSize(sym, slDist / symPoint);

      if(goBuy)
      {{
         double tp = symAsk + tpDist;
         double sl = symAsk - slDist;
         if(trade.Buy(lots, sym, symAsk, sl, tp, "{open_comment}"))
            dailyTradeCount++;
      }}
      else if(goSell)
      {{
         double tp = symBid - tpDist;
         double sl = symBid + slDist;
         if(trade.Sell(lots, sym, symBid, sl, tp, "{open_comment}"))
            dailyTradeCount++;
      }}
   }} // end symbol loop
}}
//+------------------------------------------------------------------+
"""
    return code
