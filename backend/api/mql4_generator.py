"""
Whilber-AI — MQL4 Code Generator
====================================
Converts user strategy JSON to complete MQL4 Expert Advisor.
Supports: 23 indicators (full parity with MQL5), filters, time-based exit,
multi-TP partial close, configurable direction, multi-symbol EA generation.
"""

from datetime import datetime

# ══════ INDICATOR TEMPLATES (23 indicators, full parity with MQL5) ══════

IND_MQL4 = {
    "SMA": "iMA({sym},0,{period},0,MODE_SMA,{price},{shift})",
    "EMA": "iMA({sym},0,{period},0,MODE_EMA,{price},{shift})",
    "WMA": "iMA({sym},0,{period},0,MODE_LWMA,PRICE_CLOSE,{shift})",
    "DEMA": 'iCustom({sym},0,"DEMA",{period},{shift})',
    "TEMA": 'iCustom({sym},0,"TEMA",{period},{shift})',
    "RSI": "iRSI({sym},0,{period},PRICE_CLOSE,{shift})",
    "STOCH": "iStochastic({sym},0,{k_period},{d_period},{slowing},MODE_SMA,0,{mode},{shift})",
    "STOCHRSI": 'iCustom({sym},0,"StochRSI",{rsi_period},{stoch_period},{k_smooth},{d_smooth},{mode},{shift})',
    "CCI": "iCCI({sym},0,{period},PRICE_TYPICAL,{shift})",
    "WILLIAMS": "iWPR({sym},0,{period},{shift})",
    "MFI": "iMFI({sym},0,{period},{shift})",
    "MACD": "iMACD({sym},0,{fast},{slow},{signal},PRICE_CLOSE,{mode},{shift})",
    "BB": "iBands({sym},0,{period},{std_dev},0,PRICE_CLOSE,{mode},{shift})",
    "ATR": "iATR({sym},0,{period},{shift})",
    "ADX": "iADX({sym},0,{period},PRICE_CLOSE,{mode},{shift})",
    "AROON": 'iCustom({sym},0,"Aroon",{period},{mode},{shift})',
    "SUPERTREND": 'iCustom({sym},0,"SuperTrend",{period},{multiplier},{mode},{shift})',
    "PSAR": "iSAR({sym},0,{af_start},{af_max},{shift})",
    "ICHIMOKU": "iIchimoku({sym},0,{tenkan},{kijun},{senkou_b},{mode},{shift})",
    "VOLUME": "iVolume({sym},0,{shift})",
    "OBV": "iOBV({sym},0,PRICE_CLOSE,{shift})",
    "KELTNER": 'iCustom({sym},0,"Keltner",{ema_period},{atr_period},{multiplier},{mode},{shift})',
    "DONCHIAN": 'iCustom({sym},0,"Donchian",{period},{mode},{shift})',
}

MQL4_PRICE = {
    "close": "PRICE_CLOSE", "open": "PRICE_OPEN", "high": "PRICE_HIGH",
    "low": "PRICE_LOW", "hl2": "PRICE_MEDIAN", "hlc3": "PRICE_TYPICAL",
}

MQL4_MODE = {
    "MACD": {"macd": "MODE_MAIN", "signal": "MODE_SIGNAL", "histogram": "MODE_MAIN"},
    "STOCH": {"k": "MODE_MAIN", "d": "MODE_SIGNAL"},
    "STOCHRSI": {"k": "0", "d": "1"},
    "BB": {"upper": "MODE_UPPER", "middle": "MODE_MAIN", "lower": "MODE_LOWER"},
    "ADX": {"adx": "MODE_MAIN", "plus_di": "MODE_PLUSDI", "minus_di": "MODE_MINUSDI"},
    "ICHIMOKU": {"tenkan": "MODE_TENKANSEN", "kijun": "MODE_KIJUNSEN", "senkou_a": "MODE_SENKOUSPANA", "senkou_b": "MODE_SENKOUSPANB", "chikou": "MODE_CHIKOUSPAN"},
    "AROON": {"up": "0", "down": "1", "oscillator": "2"},
    "SUPERTREND": {"trend": "0", "direction": "1"},
    "KELTNER": {"upper": "0", "middle": "1", "lower": "2"},
    "DONCHIAN": {"upper": "0", "lower": "1", "middle": "2"},
}

COND_MQL4 = {
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


def _mql4_ind_call(ind_id, params, output="value", shift="1", sym="NULL"):
    tmpl = IND_MQL4.get(ind_id, "")
    if not tmpl:
        return "0"
    src = params.get("source", "close")
    price = MQL4_PRICE.get(src, "PRICE_CLOSE")
    modes = MQL4_MODE.get(ind_id, {})
    mode = modes.get(output, "MODE_MAIN") if modes else "0"

    return tmpl.format(
        sym=sym, shift=shift, price=price, mode=mode,
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


def generate_mql4(strategy):
    """Generate complete MQL4 Expert Advisor code."""
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
    tp_close_pcts = []
    for i, tc in enumerate(tp_configs[:tp_count]):
        tp_close_pcts.append(tc.get("close_pct", 0))
    if sum(tp_close_pcts) == 0:
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

    needs_manage = bool(trail or be or time_exit or has_multi_tp)

    # SL config
    sl_type = sl_configs[0]["type"] if sl_configs else "atr_sl"
    sl_params = sl_configs[0].get("params", {}) if sl_configs else {"multiplier": 1.5}

    # ═══════════ BUILD CODE ═══════════

    code = f"""//+------------------------------------------------------------------+
//| {name}.mq4
//| Generated by Whilber-AI Strategy Builder
//| Date: {now}
//| Description: {desc}
//+------------------------------------------------------------------+
#property copyright "Whilber-AI"
#property link      "https://whilber.ai"
#property version   "1.00"
#property strict

//--- Inputs
extern double RiskPercent    = {risk.get('risk_per_trade', 2.0)};
extern double FixedLot       = {risk.get('fixed_lot', 0.01)};
extern int    MaxDailyTrades = {risk.get('max_daily_trades', 5)};
extern int    MaxOpenTrades  = {risk.get('max_open_trades', 3)};
extern double MaxDrawdownPct = {risk.get('max_drawdown', 20)};
extern double MinRR          = {risk.get('min_rr', 1.5)};
extern int    MagicNumber    = 12345;
extern double SpreadLimit    = 5.0;
"""

    # TP inputs
    for i in range(tp_count):
        tc = tp_configs[i] if i < len(tp_configs) else {"type": "atr_tp", "params": {"multiplier": 2}}
        tp_type = tc.get("type", "atr_tp")
        tp_p = tc.get("params", {})
        if tp_type == "atr_tp":
            code += f"extern double TP{i + 1}_Mult       = {tp_p.get('multiplier', 2.0)};\n"
        elif tp_type == "fixed_tp":
            code += f"extern double TP{i + 1}_Pips       = {tp_p.get('pips', 50)};\n"
        elif tp_type == "percent_tp":
            code += f"extern double TP{i + 1}_Pct        = {tp_p.get('percent', 1.0)};\n"
        if has_multi_tp:
            code += f"extern double TP{i + 1}_ClosePct   = {tp_close_pcts[i]};\n"

    # SL inputs
    if sl_type == "atr_sl":
        code += f"extern double SL_ATR_Mult    = {sl_params.get('multiplier', 1.5)};\n"
    elif sl_type == "fixed_sl":
        code += f"extern double SL_Pips        = {sl_params.get('pips', 30)};\n"

    if trail:
        if trail.get("type") == "trailing_fixed":
            code += f"extern double TrailingPips   = {trail.get('value', 20)};\n"
        else:
            code += f"extern double TrailATRMult   = {trail.get('value', 2.0)};\n"
    if be:
        code += f"extern double BE_TriggerPips = {be.get('trigger', 20)};\n"
        code += f"extern double BE_LockPips    = {be.get('lock', 5)};\n"
    if time_exit:
        code += f"extern int    TimeExitBars   = {time_exit.get('bars', 10)};\n"

    # Filter inputs
    for f in filters:
        ft = f.get("type", "")
        fp = f.get("params", {})
        if ft == "time_filter":
            code += f"extern int    FilterStartHour = {fp.get('start_hour', 8)};\n"
            code += f"extern int    FilterEndHour   = {fp.get('end_hour', 20)};\n"
        elif ft == "day_filter":
            days = fp.get("days", [1, 2, 3, 4, 5])
            code += f'extern string FilterDays      = "{",".join(str(d) for d in days)}";\n'
        elif ft == "volatility_filter":
            code += f"extern double FilterMinATR    = {fp.get('min_atr', 0.0)};\n"
            code += f"extern double FilterMaxATR    = {fp.get('max_atr', 9999.0)};\n"
            code += f"extern int    FilterATRPeriod = {fp.get('atr_period', 14)};\n"
        elif ft == "trend_filter":
            code += f"extern int    FilterTrendMA   = {fp.get('ma_period', 200)};\n"
            tf_val = fp.get("timeframe", "H4")
            tf_map = {"M1": "PERIOD_M1", "M5": "PERIOD_M5", "M15": "PERIOD_M15", "M30": "PERIOD_M30", "H1": "PERIOD_H1", "H4": "PERIOD_H4", "D1": "PERIOD_D1", "W1": "PERIOD_W1"}
            code += f"extern int    FilterTrendTF   = {tf_map.get(tf_val, 'PERIOD_H4')};\n"

    if dir_method == "ma_trend":
        code += f"extern int    DirMA_Period    = {dir_ma_period};\n"

    # Globals
    code += """
//--- Globals
int dailyCount = 0;
datetime lastDay = 0;
double initBalance = 0;
"""

    if has_multi_tp:
        code += """
//--- Multi-TP tracking
int _tpTickets[];
int _tpLevels[];
double _tpOrigLots[];

int _GetTPLevel(int ticket)
{
   for(int i = 0; i < ArraySize(_tpTickets); i++)
      if(_tpTickets[i] == ticket) return _tpLevels[i];
   return -1;
}

double _GetOrigLots(int ticket)
{
   for(int i = 0; i < ArraySize(_tpTickets); i++)
      if(_tpTickets[i] == ticket) return _tpOrigLots[i];
   return 0;
}

void _SetTPLevel(int ticket, int level, double lots)
{
   for(int i = 0; i < ArraySize(_tpTickets); i++)
   {
      if(_tpTickets[i] == ticket) { _tpLevels[i] = level; return; }
   }
   int sz = ArraySize(_tpTickets);
   ArrayResize(_tpTickets, sz + 1);
   ArrayResize(_tpLevels, sz + 1);
   ArrayResize(_tpOrigLots, sz + 1);
   _tpTickets[sz] = ticket;
   _tpLevels[sz] = level;
   _tpOrigLots[sz] = lots;
}

void _RemoveTP(int ticket)
{
   for(int i = 0; i < ArraySize(_tpTickets); i++)
   {
      if(_tpTickets[i] == ticket)
      {
         int last = ArraySize(_tpTickets) - 1;
         _tpTickets[i] = _tpTickets[last];
         _tpLevels[i] = _tpLevels[last];
         _tpOrigLots[i] = _tpOrigLots[last];
         ArrayResize(_tpTickets, last);
         ArrayResize(_tpLevels, last);
         ArrayResize(_tpOrigLots, last);
         return;
      }
   }
}
"""

    code += """
//+------------------------------------------------------------------+
int init()
{
   initBalance = AccountBalance();
   return(0);
}

int deinit() { return(0); }

//+------------------------------------------------------------------+
int CountMyOrders()
{
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         if(OrderMagicNumber() == MagicNumber && OrderSymbol() == Symbol())
            count++;
   }
   return count;
}

//+------------------------------------------------------------------+
double CalcLots(double slPips)
{
   if(slPips <= 0) return(FixedLot);
   double riskMoney = AccountBalance() * RiskPercent / 100.0;
   double tickVal = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSize = MarketInfo(Symbol(), MODE_TICKSIZE);
   double minLot = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
   if(tickVal <= 0) return(FixedLot);
   double lots = riskMoney / (slPips / tickSize * tickVal);
   lots = MathFloor(lots / lotStep) * lotStep;
   return(MathMax(minLot, MathMin(maxLot, lots)));
}

"""

    # ManageTrades function
    if needs_manage:
        code += """//+------------------------------------------------------------------+
void ManageTrades()
{
   double atr = iATR(NULL, 0, 14, 1);
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderMagicNumber() != MagicNumber || OrderSymbol() != Symbol()) continue;

      double openP = OrderOpenPrice();
      double curSL = OrderStopLoss();
      double curTP = OrderTakeProfit();
      int ticket = OrderTicket();
      bool isBuy = (OrderType() == OP_BUY);
"""

        # Time exit
        if time_exit:
            code += """
      // Time-based exit
      if(TimeCurrent() - OrderOpenTime() > TimeExitBars * PeriodSeconds())
      {
         if(isBuy) OrderClose(ticket, OrderLots(), Bid, 3, clrNONE);
         else OrderClose(ticket, OrderLots(), Ask, 3, clrNONE);
         continue;
      }
"""

        # Multi-TP partial close
        if has_multi_tp:
            code += "\n      // Multi-TP partial close\n"
            code += "      int tpLevel = _GetTPLevel(ticket);\n"
            code += "      if(tpLevel < 0) { _SetTPLevel(ticket, 0, OrderLots()); tpLevel = 0; }\n"
            for ti in range(tp_count - 1):
                tc = tp_configs[ti] if ti < len(tp_configs) else {"type": "atr_tp", "params": {"multiplier": 2}}
                tp_type = tc.get("type", "atr_tp")
                tp_p = tc.get("params", {})
                pct = tp_close_pcts[ti]
                if tp_type == "atr_tp":
                    dist_expr = f"TP{ti + 1}_Mult * atr"
                elif tp_type == "fixed_tp":
                    dist_expr = f"TP{ti + 1}_Pips * Point * 10"
                elif tp_type == "percent_tp":
                    dist_expr = f"openP * TP{ti + 1}_Pct / 100.0"
                else:
                    dist_expr = "2.0 * atr"

                code += f"      if(tpLevel == {ti})\n"
                code += "      {\n"
                code += f"         double tpD{ti} = {dist_expr};\n"
                code += f"         bool tpHit = isBuy ? (Bid >= openP + tpD{ti}) : (Ask <= openP - tpD{ti});\n"
                code += "         if(tpHit)\n"
                code += "         {\n"
                code += "            double origLots = _GetOrigLots(ticket);\n"
                code += f"            double closeVol = NormalizeDouble(origLots * {pct} / 100.0, 2);\n"
                code += "            double minLot = MarketInfo(Symbol(), MODE_MINLOT);\n"
                code += "            if(closeVol >= minLot)\n"
                code += "            {\n"
                code += "               if(isBuy) OrderClose(ticket, closeVol, Bid, 3, clrNONE);\n"
                code += "               else OrderClose(ticket, closeVol, Ask, 3, clrNONE);\n"
                code += f"               _SetTPLevel(ticket, {ti + 1}, origLots);\n"
                code += "            }\n"
                code += "         }\n"
                code += "      }\n"

        # Break even
        if be:
            code += """
      // Break Even
      double beTrig = BE_TriggerPips * Point * 10;
      double beLock = BE_LockPips * Point * 10;
      if(isBuy)
      {
         if(Bid >= openP + beTrig && curSL < openP + beLock)
            OrderModify(ticket, openP, openP + beLock, curTP, 0, clrNONE);
      }
      else
      {
         if(Ask <= openP - beTrig && (curSL > openP - beLock || curSL == 0))
            OrderModify(ticket, openP, openP - beLock, curTP, 0, clrNONE);
      }
"""

        # Trailing
        if trail:
            if trail.get("type") == "trailing_fixed":
                code += """
      // Trailing Stop (Fixed)
      double trDist = TrailingPips * Point * 10;
"""
            else:
                code += """
      // Trailing Stop (ATR)
      double trDist = TrailATRMult * atr;
"""
            code += """      if(isBuy)
      {
         double nsl = Bid - trDist;
         if(nsl > curSL && nsl > openP)
            OrderModify(ticket, openP, nsl, curTP, 0, clrNONE);
      }
      else
      {
         double nsl = Ask + trDist;
         if((nsl < curSL || curSL == 0) && nsl < openP)
            OrderModify(ticket, openP, nsl, curTP, 0, clrNONE);
      }
"""

        code += """   }
}

"""

    # start()
    code += """//+------------------------------------------------------------------+
int start()
{
   // Daily reset
   if(TimeDay(TimeCurrent()) != TimeDay(lastDay))
   { dailyCount = 0; lastDay = TimeCurrent(); }

"""
    if needs_manage:
        code += "   ManageTrades();\n\n"

    code += """   if(dailyCount >= MaxDailyTrades) return(0);
   if(CountMyOrders() >= MaxOpenTrades) return(0);
   if(AccountBalance() < initBalance * (1.0 - MaxDrawdownPct / 100.0)) return(0);

   double spread = (Ask - Bid) / Point / 10.0;
   if(spread > SpreadLimit) return(0);

"""

    # Filter checks
    if has_time_filter:
        code += "   // Time filter\n"
        code += "   if(Hour() < FilterStartHour || Hour() > FilterEndHour) return(0);\n\n"

    if has_day_filter:
        code += """   // Day filter
   {
      string daysStr = FilterDays;
      bool dayOK = false;
      string parts[];
      int cnt = StringSplit(daysStr, ',', parts);
      for(int d = 0; d < cnt; d++)
         if((int)StringToInteger(parts[d]) == DayOfWeek()) { dayOK = true; break; }
      if(!dayOK) return(0);
   }

"""

    if has_vol_filter:
        code += "   // Volatility filter\n"
        code += "   double fATR = iATR(NULL, 0, FilterATRPeriod, 1);\n"
        code += "   if(fATR < FilterMinATR || fATR > FilterMaxATR) return(0);\n\n"

    code += """   // New bar
   static datetime lastBar = 0;
   if(Time[0] == lastBar) return(0);
   lastBar = Time[0];

   // Get values
"""

    # Indicator values
    for i, cond in enumerate(entry_conds):
        ind_id = cond.get("indicator", "")
        params = cond.get("indicator_params", {})
        output = cond.get("output", "value")
        call1 = _mql4_ind_call(ind_id, params, output, "1")
        call2 = _mql4_ind_call(ind_id, params, output, "2")
        code += f"   double v{i} = {call1};\n"
        code += f"   double v{i}p = {call2};\n"
        if cond.get("compare_to") == "indicator":
            cmp_id = cond.get("compare_indicator", "")
            cmp_params = cond.get("compare_indicator_params", {})
            cmp_out = cond.get("compare_output", "value")
            cc1 = _mql4_ind_call(cmp_id, cmp_params, cmp_out, "1")
            cc2 = _mql4_ind_call(cmp_id, cmp_params, cmp_out, "2")
            code += f"   double c{i} = {cc1};\n"
            code += f"   double c{i}p = {cc2};\n"

    code += "   double atr = iATR(NULL, 0, 14, 1);\n\n"

    # Conditions
    parts = []
    for i, cond in enumerate(entry_conds):
        ct = cond.get("condition", "")
        cmp_to = cond.get("compare_to", "fixed_value")
        a, ap = f"v{i}", f"v{i}p"
        if cmp_to == "fixed_value":
            b = str(float(cond.get("compare_value", 0)))
            bp = b
        elif cmp_to == "indicator":
            b, bp = f"c{i}", f"c{i}p"
        else:
            b, bp = "Close[1]", "Close[2]"
        tmpl = COND_MQL4.get(ct, "{a} > {b}")
        parts.append("(" + tmpl.format(a=a, b=b, a_prev=ap, b_prev=bp) + ")")

    sig = logic_op.join(parts) if parts else "false"
    code += f"   bool sig = ({sig});\n"

    # Direction logic
    if direction == "buy_only":
        code += "   if(!sig) return(0);\n"
        code += "   bool goBuy = true; bool goSell = false;\n"
    elif direction == "sell_only":
        code += "   if(!sig) return(0);\n"
        code += "   bool goBuy = false; bool goSell = true;\n"
    elif dir_method == "ma_trend":
        code += "   if(!sig) return(0);\n"
        code += "   double dirMA = iMA(NULL, 0, DirMA_Period, 0, MODE_SMA, PRICE_CLOSE, 1);\n"
        code += "   bool goBuy = (Bid > dirMA); bool goSell = (Bid <= dirMA);\n"
    elif dir_method == "entry_signal":
        # Build inverse conditions for sell
        inv_parts = []
        for i, cond in enumerate(entry_conds):
            ct = cond.get("condition", "")
            inv_ct = CONDITION_INVERSE.get(ct, ct)
            cmp_to = cond.get("compare_to", "fixed_value")
            a, ap = f"v{i}", f"v{i}p"
            if cmp_to == "fixed_value":
                b = str(float(cond.get("compare_value", 0)))
                bp = b
            elif cmp_to == "indicator":
                b, bp = f"c{i}", f"c{i}p"
            else:
                b, bp = "Close[1]", "Close[2]"
            tmpl = COND_MQL4.get(inv_ct, "{a} < {b}")
            inv_parts.append("(" + tmpl.format(a=a, b=b, a_prev=ap, b_prev=bp) + ")")
        inv_sig = logic_op.join(inv_parts) if inv_parts else "false"
        code += f"   bool sellSig = ({inv_sig});\n"
        code += "   if(!sig && !sellSig) return(0);\n"
        code += "   bool goBuy = sig; bool goSell = sellSig && !sig;\n"
    elif dir_method == "always_both":
        code += "   if(!sig) return(0);\n"
        code += "   bool goBuy = true; bool goSell = true;\n"
    else:
        code += "   if(!sig) return(0);\n"
        code += "   double dirMA = iMA(NULL, 0, DirMA_Period, 0, MODE_SMA, PRICE_CLOSE, 1);\n"
        code += "   bool goBuy = (Bid > dirMA); bool goSell = (Bid <= dirMA);\n"

    # Trend filter
    if has_trend_filter:
        code += "\n   // Trend filter\n"
        code += "   double trendMA = iMA(NULL, FilterTrendTF, FilterTrendMA, 0, MODE_SMA, PRICE_CLOSE, 1);\n"
        code += "   if(goBuy && Bid < trendMA) goBuy = false;\n"
        code += "   if(goSell && Bid > trendMA) goSell = false;\n"
        code += "   if(!goBuy && !goSell) return(0);\n"

    # TP/SL calculation
    # SL
    if sl_type == "atr_sl":
        code += "   double slD = SL_ATR_Mult * atr;\n"
    elif sl_type == "fixed_sl":
        code += "   double slD = SL_Pips * Point * 10;\n"
    else:
        code += "   double slD = 1.5 * atr;\n"

    # TP (use last level for order TP)
    if has_multi_tp:
        last_tc = tp_configs[tp_count - 1] if tp_count - 1 < len(tp_configs) else {"type": "atr_tp", "params": {"multiplier": 3}}
        ltp_type = last_tc.get("type", "atr_tp")
        if ltp_type == "atr_tp":
            code += f"   double tpD = TP{tp_count}_Mult * atr;\n"
        elif ltp_type == "fixed_tp":
            code += f"   double tpD = TP{tp_count}_Pips * Point * 10;\n"
        elif ltp_type == "percent_tp":
            code += f"   double tpD = Bid * TP{tp_count}_Pct / 100.0;\n"
        else:
            code += "   double tpD = 2.0 * atr;\n"
    else:
        tc0 = tp_configs[0] if tp_configs else {"type": "atr_tp", "params": {"multiplier": 2}}
        tp0_type = tc0.get("type", "atr_tp")
        if tp0_type == "atr_tp":
            code += "   double tpD = TP1_Mult * atr;\n"
        elif tp0_type == "fixed_tp":
            code += "   double tpD = TP1_Pips * Point * 10;\n"
        elif tp0_type == "percent_tp":
            code += "   double tpD = Bid * TP1_Pct / 100.0;\n"
        else:
            code += "   double tpD = 2.0 * atr;\n"

    open_comment = name.replace('"', "'")

    if dir_method == "always_both":
        code += f"""
   if(slD <= 0 || tpD <= 0) return(0);
   if(tpD / slD < MinRR) return(0);
   double lots = CalcLots(slD / Point);

   if(goBuy)
   {{
      double tp = Ask + tpD;
      double sl = Ask - slD;
      int ticket = OrderSend(Symbol(), OP_BUY, lots, Ask, 3, sl, tp, "{open_comment}", MagicNumber, 0, clrGreen);
      if(ticket > 0) dailyCount++;
   }}
   if(goSell)
   {{
      double tp = Bid - tpD;
      double sl = Bid + slD;
      int ticket = OrderSend(Symbol(), OP_SELL, lots, Bid, 3, sl, tp, "{open_comment}", MagicNumber, 0, clrRed);
      if(ticket > 0) dailyCount++;
   }}
   return(0);
}}
//+------------------------------------------------------------------+
"""
    else:
        code += f"""
   if(slD <= 0 || tpD <= 0) return(0);
   if(tpD / slD < MinRR) return(0);
   double lots = CalcLots(slD / Point);

   if(goBuy)
   {{
      double tp = Ask + tpD;
      double sl = Ask - slD;
      int ticket = OrderSend(Symbol(), OP_BUY, lots, Ask, 3, sl, tp, "{open_comment}", MagicNumber, 0, clrGreen);
      if(ticket > 0) dailyCount++;
   }}
   else if(goSell)
   {{
      double tp = Bid - tpD;
      double sl = Bid + slD;
      int ticket = OrderSend(Symbol(), OP_SELL, lots, Bid, 3, sl, tp, "{open_comment}", MagicNumber, 0, clrRed);
      if(ticket > 0) dailyCount++;
   }}
   return(0);
}}
//+------------------------------------------------------------------+
"""
    return code


def generate_mql4_multi(strategy, symbols_list):
    """Generate multi-symbol MQL4 EA that trades multiple symbols."""
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

    symbols_str = ",".join(symbols_list)

    code = f"""//+------------------------------------------------------------------+
//| {name}_Multi.mq4
//| Generated by Whilber-AI Strategy Builder (Multi-Symbol)
//| Date: {now}
//| Symbols: {symbols_str}
//| Description: {desc}
//+------------------------------------------------------------------+
#property copyright "Whilber-AI"
#property link      "https://whilber.ai"
#property version   "1.00"
#property strict

extern double RiskPercent    = {risk.get('risk_per_trade', 2.0)};
extern double FixedLot       = {risk.get('fixed_lot', 0.01)};
extern int    MaxDailyTrades = {risk.get('max_daily_trades', 5)};
extern int    MaxOpenTrades  = {risk.get('max_open_trades', 3)};
extern double MaxDrawdownPct = {risk.get('max_drawdown', 20)};
extern double MinRR          = {risk.get('min_rr', 1.5)};
extern int    BaseMagicNumber = 12345;
extern double SpreadLimit    = 5.0;
"""
    if tp_type == "atr_tp":
        code += f"extern double TP_ATR_Mult    = {tp_params.get('multiplier', 2.0)};\n"
    elif tp_type == "fixed_tp":
        code += f"extern double TP_Pips        = {tp_params.get('pips', 50)};\n"
    if sl_type == "atr_sl":
        code += f"extern double SL_ATR_Mult    = {sl_params.get('multiplier', 1.5)};\n"
    elif sl_type == "fixed_sl":
        code += f"extern double SL_Pips        = {sl_params.get('pips', 30)};\n"

    if trail:
        if trail.get("type") == "trailing_fixed":
            code += f"extern double TrailingPips   = {trail.get('value', 20)};\n"
        else:
            code += f"extern double TrailATRMult   = {trail.get('value', 2.0)};\n"
    if be:
        code += f"extern double BE_TriggerPips = {be.get('trigger', 20)};\n"
        code += f"extern double BE_LockPips    = {be.get('lock', 5)};\n"
    if time_exit:
        code += f"extern int    TimeExitBars   = {time_exit.get('bars', 10)};\n"

    for f in filters:
        ft = f.get("type", "")
        fp = f.get("params", {})
        if ft == "time_filter":
            code += f"extern int    FilterStartHour = {fp.get('start_hour', 8)};\n"
            code += f"extern int    FilterEndHour   = {fp.get('end_hour', 20)};\n"
        elif ft == "volatility_filter":
            code += f"extern double FilterMinATR    = {fp.get('min_atr', 0.0)};\n"
            code += f"extern double FilterMaxATR    = {fp.get('max_atr', 9999.0)};\n"
            code += f"extern int    FilterATRPeriod = {fp.get('atr_period', 14)};\n"
        elif ft == "trend_filter":
            code += f"extern int    FilterTrendMA   = {fp.get('ma_period', 200)};\n"
    if dir_method == "ma_trend":
        code += f"extern int    DirMA_Period    = {dir_ma_period};\n"

    code += f"""
#define NUM_SYMBOLS {num_sym}
string SymbolList[NUM_SYMBOLS] = {{{", ".join('"' + s + '"' for s in symbols_list)}}};
datetime lastBars[NUM_SYMBOLS];
int dailyCount = 0;
datetime lastDay = 0;
double initBalance = 0;

int init()
{{
   initBalance = AccountBalance();
   ArrayInitialize(lastBars, 0);
   return(0);
}}

int deinit() {{ return(0); }}

int CountOrdersForSymbol(string sym, int magic)
{{
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {{
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         if(OrderMagicNumber() == magic && OrderSymbol() == sym)
            count++;
   }}
   return count;
}}

double CalcLotsForSymbol(string sym, double slPips)
{{
   if(slPips <= 0) return(FixedLot);
   double riskMoney = AccountBalance() * RiskPercent / 100.0;
   double tickVal = MarketInfo(sym, MODE_TICKVALUE);
   double tickSize = MarketInfo(sym, MODE_TICKSIZE);
   double minLot = MarketInfo(sym, MODE_MINLOT);
   double maxLot = MarketInfo(sym, MODE_MAXLOT);
   double lotStep = MarketInfo(sym, MODE_LOTSTEP);
   if(tickVal <= 0) return(FixedLot);
   double lots = riskMoney / (slPips / tickSize * tickVal);
   lots = MathFloor(lots / lotStep) * lotStep;
   return(MathMax(minLot, MathMin(maxLot, lots)));
}}

int start()
{{
   if(TimeDay(TimeCurrent()) != TimeDay(lastDay))
   {{ dailyCount = 0; lastDay = TimeCurrent(); }}

   if(AccountBalance() < initBalance * (1.0 - MaxDrawdownPct / 100.0)) return(0);
   if(dailyCount >= MaxDailyTrades) return(0);
"""

    if has_time_filter:
        code += "   if(Hour() < FilterStartHour || Hour() > FilterEndHour) return(0);\n"

    code += """
   for(int s = 0; s < NUM_SYMBOLS; s++)
   {
      string sym = SymbolList[s];
      int magic = BaseMagicNumber + s;

      if(CountOrdersForSymbol(sym, magic) >= MaxOpenTrades) continue;

      double symAsk = MarketInfo(sym, MODE_ASK);
      double symBid = MarketInfo(sym, MODE_BID);
      double symPoint = MarketInfo(sym, MODE_POINT);
      if(symPoint <= 0) continue;
      double symSpread = (symAsk - symBid) / symPoint / 10.0;
      if(symSpread > SpreadLimit) continue;
"""

    if has_vol_filter:
        code += "      double fATR = iATR(sym, 0, FilterATRPeriod, 1);\n"
        code += "      if(fATR < FilterMinATR || fATR > FilterMaxATR) continue;\n"

    code += """
      // New bar check
      datetime curBar = iTime(sym, 0, 0);
      if(curBar == lastBars[s]) continue;
      lastBars[s] = curBar;

      // Get indicator values
"""

    for i, cond in enumerate(entry_conds):
        ind_id = cond.get("indicator", "")
        params = cond.get("indicator_params", {})
        output = cond.get("output", "value")
        call1 = _mql4_ind_call(ind_id, params, output, "1", "sym")
        call2 = _mql4_ind_call(ind_id, params, output, "2", "sym")
        code += f"      double v{i} = {call1};\n"
        code += f"      double v{i}p = {call2};\n"
        if cond.get("compare_to") == "indicator":
            cmp_id = cond.get("compare_indicator", "")
            cmp_params = cond.get("compare_indicator_params", {})
            cmp_out = cond.get("compare_output", "value")
            cc1 = _mql4_ind_call(cmp_id, cmp_params, cmp_out, "1", "sym")
            cc2 = _mql4_ind_call(cmp_id, cmp_params, cmp_out, "2", "sym")
            code += f"      double c{i} = {cc1};\n"
            code += f"      double c{i}p = {cc2};\n"

    code += "      double symATR = iATR(sym, 0, 14, 1);\n\n"

    # Build conditions
    parts = []
    for i, cond in enumerate(entry_conds):
        ct = cond.get("condition", "")
        cmp_to = cond.get("compare_to", "fixed_value")
        a, ap = f"v{i}", f"v{i}p"
        if cmp_to == "fixed_value":
            b = str(float(cond.get("compare_value", 0)))
            bp = b
        elif cmp_to == "indicator":
            b, bp = f"c{i}", f"c{i}p"
        else:
            b, bp = f"iClose(sym,0,1)", f"iClose(sym,0,2)"
        tmpl = COND_MQL4.get(ct, "{a} > {b}")
        parts.append("(" + tmpl.format(a=a, b=b, a_prev=ap, b_prev=bp) + ")")

    sig_expr = logic_op.join(parts) if parts else "false"
    code += f"      bool entrySig = ({sig_expr});\n"
    code += "      if(!entrySig) continue;\n\n"

    # Direction
    if direction == "buy_only":
        code += "      bool goBuy = true; bool goSell = false;\n"
    elif direction == "sell_only":
        code += "      bool goBuy = false; bool goSell = true;\n"
    elif dir_method == "ma_trend":
        code += f"      double dirMA = iMA(sym, 0, DirMA_Period, 0, MODE_SMA, PRICE_CLOSE, 1);\n"
        code += "      bool goBuy = (symBid > dirMA); bool goSell = (symBid <= dirMA);\n"
    else:
        code += "      bool goBuy = true; bool goSell = true;\n"

    if has_trend_filter:
        code += "      double trendMA = iMA(sym, FilterTrendMA, 200, 0, MODE_SMA, PRICE_CLOSE, 1);\n"
        code += "      if(goBuy && symBid < trendMA) goBuy = false;\n"
        code += "      if(goSell && symBid > trendMA) goSell = false;\n"
        code += "      if(!goBuy && !goSell) continue;\n"

    # TP/SL
    if tp_type == "atr_tp":
        code += "      double tpD = TP_ATR_Mult * symATR;\n"
    elif tp_type == "fixed_tp":
        code += "      double tpD = TP_Pips * symPoint * 10;\n"
    else:
        code += "      double tpD = 2.0 * symATR;\n"
    if sl_type == "atr_sl":
        code += "      double slD = SL_ATR_Mult * symATR;\n"
    elif sl_type == "fixed_sl":
        code += "      double slD = SL_Pips * symPoint * 10;\n"
    else:
        code += "      double slD = 1.5 * symATR;\n"

    open_comment = name.replace('"', "'")
    code += f"""
      if(slD <= 0 || tpD <= 0) continue;
      if(tpD / slD < MinRR) continue;
      double lots = CalcLotsForSymbol(sym, slD / symPoint);

      if(goBuy)
      {{
         double tp = symAsk + tpD;
         double sl = symAsk - slD;
         int ticket = OrderSend(sym, OP_BUY, lots, symAsk, 3, sl, tp, "{open_comment}", magic, 0, clrGreen);
         if(ticket > 0) dailyCount++;
      }}
      else if(goSell)
      {{
         double tp = symBid - tpD;
         double sl = symBid + slD;
         int ticket = OrderSend(sym, OP_SELL, lots, symBid, 3, sl, tp, "{open_comment}", magic, 0, clrRed);
         if(ticket > 0) dailyCount++;
      }}
   }} // end symbol loop
   return(0);
}}
//+------------------------------------------------------------------+
"""
    return code
