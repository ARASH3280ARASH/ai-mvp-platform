# %% [markdown]
# # AI Analysis Pipeline Demo
#
# Demonstrates the full AI-enhanced analysis pipeline:
# feature engineering → ML prediction → regime detection →
# strategy recommendation → trade optimization.

# %% Imports
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_core.pipeline import AIPipeline
from ai_core.config import AIConfig
from ai_core.nlp_processor import NLPProcessor

# %% Load sample data
df = pd.read_csv(PROJECT_ROOT / "data" / "sample" / "sample_ohlcv.csv")
df["time"] = pd.to_datetime(df["time"])
df.set_index("time", inplace=True)
print(f"Loaded {len(df)} bars of BTCUSD H1 data")

trades_df = pd.read_csv(PROJECT_ROOT / "data" / "sample" / "sample_trades.csv")
print(f"Loaded {len(trades_df)} sample trades")

# %% Initialize pipeline
config = AIConfig()
pipeline = AIPipeline(config=config, account_balance=10_000)
print("Pipeline initialized")

# %% Train the pipeline
training_summary = pipeline.train(
    df=df,
    indicators=None,
    strategy_history=trades_df,
)
print("\nTraining Summary:")
for key, val in training_summary.items():
    print(f"  {key}: {val}")

# %% Run analysis
result = pipeline.analyze(
    symbol="BTCUSD",
    timeframe="H1",
    df=df,
    news_texts=[
        "Bitcoin surges past $65K on strong ETF inflows",
        "Crypto market shows bullish momentum with rising volumes",
        "Fed signals potential rate cuts, risk assets rally",
    ],
    current_price=float(df["close"].iloc[-1]),
)

print(f"\n{'='*60}")
print(f"  AI Analysis: BTCUSD H1")
print(f"{'='*60}")
print(f"  ML Signal:     {result.ml_signal}")
print(f"  Confidence:    {result.ml_confidence:.2%}")
print(f"  Regime:        {result.regime.regime if result.regime else 'N/A'}")
print(f"  Sentiment:     {result.sentiment.sentiment if result.sentiment else 'N/A'}")
print(f"  Processing:    {result.processing_time_ms:.1f}ms")

if result.trade_decision:
    d = result.trade_decision
    print(f"\n  Trade Decision: {d.action}")
    print(f"  Lot Size:      {d.lot_size}")
    print(f"  SL:            {d.sl_price}")
    print(f"  TP1:           {d.tp1_price}")
    print(f"  Risk:          ${d.risk_dollars:.2f} ({d.risk_pct:.1f}%)")
    print(f"  R:R:           1:{d.reward_risk_ratio:.1f}")

if result.recommendations:
    print(f"\n  Top Recommendations:")
    for i, rec in enumerate(result.recommendations[:3], 1):
        print(f"    {i}. {rec.strategy_id} — score={rec.composite_score:.3f} WR={rec.win_rate:.0%}")

# %% Standalone NLP demo
nlp = NLPProcessor()

headlines = [
    "BTC breaks key resistance, analysts target $75K",
    "Market crash fears grow as volatility spikes",
    "Gold steady amid uncertainty, dollar weakens",
    "Crypto adoption accelerates with new regulations",
]

print(f"\n{'='*60}")
print(f"  Sentiment Analysis")
print(f"{'='*60}")
for headline in headlines:
    s = nlp.analyze_sentiment(headline)
    bar = "+" * int(max(0, s.score) * 20) + "-" * int(max(0, -s.score) * 20)
    print(f"  [{s.sentiment:>8s}] {s.score:+.3f}  {bar:20s}  {headline[:50]}")
