"""
Whilber-AI — Backtest Report Generator
==========================================
Creates downloadable HTML report from backtest results.
"""

from datetime import datetime


def generate_report(strategy, backtest_result):
    """Generate HTML report string from backtest results."""
    name = strategy.get("name", "Strategy")
    symbol = strategy.get("symbol", "XAUUSD")
    tf = strategy.get("timeframe", "H1")
    st = backtest_result.get("stats", {})
    trades = backtest_result.get("trades", [])
    equity = backtest_result.get("equity_curve", [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Entry conditions text
    entry_text = ""
    for i, c in enumerate(strategy.get("entry_conditions", [])):
        ind = c.get("indicator", "?")
        cond = c.get("condition", "?")
        params = c.get("indicator_params", {})
        pstr = ", ".join(f"{k}={v}" for k, v in params.items())
        cmp = c.get("compare_to", "")
        if cmp == "fixed_value":
            cmp_str = str(c.get("compare_value", ""))
        elif cmp == "indicator":
            cmp_str = c.get("compare_indicator", "")
        else:
            cmp_str = cmp
        logic = strategy.get("entry_logic", "AND") if i > 0 else ""
        entry_text += f"{'<br><b>'+logic+'</b> ' if logic else ''}{ind}({pstr}) {cond} {cmp_str}"

    # Risk text
    risk = strategy.get("risk", {})

    # TP/SL text
    tp_text = ""
    for tp in strategy.get("exit_take_profit", []):
        tp_text += f"{tp.get('type','')} ({', '.join(f'{k}={v}' for k,v in tp.get('params',{}).items())})"
    sl_text = ""
    for sl in strategy.get("exit_stop_loss", []):
        sl_text += f"{sl.get('type','')} ({', '.join(f'{k}={v}' for k,v in sl.get('params',{}).items())})"

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>Whilber-AI Report - {name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Segoe UI',Tahoma,sans-serif;background:#0a0c10;color:#e2e5f0;padding:30px;direction:rtl;}}
.report{{max-width:900px;margin:0 auto;}}
.header{{text-align:center;margin-bottom:30px;padding:20px;background:#12151c;border:1px solid #2a2f42;border-radius:12px;}}
.header h1{{font-size:22px;color:#06b6d4;margin-bottom:6px;}}
.header .sub{{color:#7f849c;font-size:12px;}}
.section{{background:#12151c;border:1px solid #2a2f42;border-radius:12px;margin-bottom:14px;overflow:hidden;}}
.section-head{{padding:10px 16px;background:#1a1e2a;border-bottom:1px solid #2a2f42;font-size:14px;font-weight:700;color:#06b6d4;}}
.section-body{{padding:14px 16px;}}
.stat-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;}}
.stat{{background:#1a1e2a;border:1px solid #2a2f42;border-radius:8px;padding:10px;text-align:center;}}
.stat .val{{font-size:20px;font-weight:800;}}
.stat .val.green{{color:#22c55e;}}.stat .val.red{{color:#ef4444;}}.stat .val.cyan{{color:#06b6d4;}}
.stat .lbl{{font-size:10px;color:#7f849c;margin-top:3px;}}
.info-row{{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px;}}
.info-row .il{{color:#7f849c;}}.info-row .iv{{font-weight:600;}}
table{{width:100%;border-collapse:collapse;font-size:11px;}}
th{{background:#1a1e2a;padding:6px 8px;text-align:right;color:#7f849c;border-bottom:1px solid #2a2f42;}}
td{{padding:5px 8px;border-bottom:1px solid #2a2f42;}}
.win{{color:#22c55e;}}.loss{{color:#ef4444;}}
.footer{{text-align:center;margin-top:20px;color:#565a6e;font-size:11px;}}
@media print{{body{{background:#fff;color:#000;}} .section{{border-color:#ddd;background:#fff;}} .section-head{{background:#f5f5f5;color:#333;}} .stat{{background:#f9f9f9;border-color:#ddd;}} .stat .val.green{{color:#16a34a;}} .stat .val.red{{color:#dc2626;}} .stat .val.cyan{{color:#0891b2;}} th{{background:#f5f5f5;}} .header{{background:#f5f5f5;border-color:#ddd;}} .header h1{{color:#0891b2;}}}}
</style>
</head>
<body>
<div class="report">
<div class="header">
  <h1>Whilber-AI Backtest Report</h1>
  <div class="sub">{name} | {symbol} | {tf} | {now}</div>
</div>

<div class="section">
  <div class="section-head">📊 خلاصه عملکرد</div>
  <div class="section-body">
    <div class="stat-grid">
      <div class="stat"><div class="val cyan">{st.get('total',0)}</div><div class="lbl">کل معاملات</div></div>
      <div class="stat"><div class="val {'green' if st.get('win_rate',0)>=50 else 'red'}">{st.get('win_rate',0)}%</div><div class="lbl">نرخ برد</div></div>
      <div class="stat"><div class="val {'green' if st.get('total_pnl',0)>=0 else 'red'}">${st.get('total_pnl',0)}</div><div class="lbl">سود/زیان کل</div></div>
      <div class="stat"><div class="val {'green' if st.get('profit_factor',0)>=1.5 else 'cyan'}">{st.get('profit_factor',0)}</div><div class="lbl">Profit Factor</div></div>
      <div class="stat"><div class="val {'green' if st.get('max_drawdown_pct',0)<=15 else 'red'}">{st.get('max_drawdown_pct',0)}%</div><div class="lbl">Max Drawdown</div></div>
      <div class="stat"><div class="val cyan">{st.get('sharpe',0)}</div><div class="lbl">Sharpe Ratio</div></div>
      <div class="stat"><div class="val green">${st.get('avg_win',0)}</div><div class="lbl">میانگین برد</div></div>
      <div class="stat"><div class="val red">${abs(st.get('avg_loss',0))}</div><div class="lbl">میانگین باخت</div></div>
      <div class="stat"><div class="val cyan">{st.get('avg_rr',0)}</div><div class="lbl">R:R میانگین</div></div>
      <div class="stat"><div class="val green">{st.get('max_consec_wins',0)}</div><div class="lbl">بردهای متوالی</div></div>
      <div class="stat"><div class="val red">{st.get('max_consec_losses',0)}</div><div class="lbl">باخت‌های متوالی</div></div>
      <div class="stat"><div class="val cyan">{st.get('avg_bars_held',0)}</div><div class="lbl">میانگین کندل</div></div>
    </div>
    <div class="info-row"><span class="il">سرمایه اولیه</span><span class="iv">${backtest_result.get('initial_balance',10000)}</span></div>
    <div class="info-row"><span class="il">بالانس نهایی</span><span class="iv">${backtest_result.get('final_balance',0)}</span></div>
    <div class="info-row"><span class="il">بازده</span><span class="iv">{round((backtest_result.get('final_balance',10000)/backtest_result.get('initial_balance',10000)-1)*100,1)}%</span></div>
    <div class="info-row"><span class="il">کندل‌های تست شده</span><span class="iv">{backtest_result.get('bars_tested',0)}</span></div>
  </div>
</div>

<div class="section">
  <div class="section-head">⚙️ تنظیمات استراتژی</div>
  <div class="section-body">
    <div class="info-row"><span class="il">نماد</span><span class="iv">{symbol}</span></div>
    <div class="info-row"><span class="il">تایم‌فریم</span><span class="iv">{tf}</span></div>
    <div class="info-row"><span class="il">جهت</span><span class="iv">{strategy.get('direction','both')}</span></div>
    <div class="info-row"><span class="il">شرایط ورود</span><span class="iv">{entry_text or '-'}</span></div>
    <div class="info-row"><span class="il">Take Profit</span><span class="iv">{tp_text or '-'}</span></div>
    <div class="info-row"><span class="il">Stop Loss</span><span class="iv">{sl_text or '-'}</span></div>
    <div class="info-row"><span class="il">ریسک/معامله</span><span class="iv">{risk.get('risk_per_trade',2)}%</span></div>
    <div class="info-row"><span class="il">حداکثر معاملات روزانه</span><span class="iv">{risk.get('max_daily_trades',5)}</span></div>
    <div class="info-row"><span class="il">حداکثر افت مجاز</span><span class="iv">{risk.get('max_drawdown',20)}%</span></div>
    <div class="info-row"><span class="il">حداقل R:R</span><span class="iv">{risk.get('min_rr',1.5)}</span></div>
  </div>
</div>

<div class="section">
  <div class="section-head">📋 لیست معاملات ({len(trades)})</div>
  <div class="section-body" style="max-height:400px;overflow-y:auto;">
    <table>
      <thead><tr><th>#</th><th>نوع</th><th>ورود</th><th>خروج</th><th>TP</th><th>SL</th><th>لات</th><th>R:R</th><th>سود/زیان</th><th>خروج</th></tr></thead>
      <tbody>
"""

    for i, t in enumerate(trades[:100]):
        cls = "win" if t.get("pnl", 0) >= 0 else "loss"
        html += f"""        <tr>
          <td>{i+1}</td>
          <td style="color:{'#22c55e' if t.get('type')=='BUY' else '#ef4444'};">{t.get('type','')}</td>
          <td>{t.get('entry','')}</td>
          <td>{t.get('exit_price','')}</td>
          <td>{t.get('tp','')}</td>
          <td>{t.get('sl','')}</td>
          <td>{t.get('lot_size','')}</td>
          <td>{t.get('rr','')}</td>
          <td class="{cls}">${t.get('pnl',0)}</td>
          <td>{t.get('exit_reason','')}</td>
        </tr>
"""

    if len(trades) > 100:
        html += f'        <tr><td colspan="10" style="text-align:center;color:#7f849c;">... {len(trades)-100} more trades</td></tr>\n'

    html += f"""      </tbody>
    </table>
  </div>
</div>

<div class="footer">
  Generated by Whilber-AI Strategy Builder | {now}<br>
  This report is for educational purposes only. Past performance does not guarantee future results.
</div>
</div>
</body>
</html>"""

    return html


def generate_summary_text(strategy, stats):
    """Generate plain text summary."""
    lines = [
        f"Strategy: {strategy.get('name','')}",
        f"Symbol: {strategy.get('symbol','')} | TF: {strategy.get('timeframe','')}",
        f"Total Trades: {stats.get('total',0)}",
        f"Win Rate: {stats.get('win_rate',0)}%",
        f"Profit Factor: {stats.get('profit_factor',0)}",
        f"Total PnL: ${stats.get('total_pnl',0)}",
        f"Max Drawdown: {stats.get('max_drawdown_pct',0)}%",
        f"Sharpe: {stats.get('sharpe',0)}",
        f"Avg R:R: {stats.get('avg_rr',0)}",
    ]
    return "\n".join(lines)
