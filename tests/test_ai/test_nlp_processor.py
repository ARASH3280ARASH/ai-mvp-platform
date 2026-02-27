"""Tests for the NLP processor module."""

import pytest

from ai_core.nlp_processor import NLPProcessor


@pytest.fixture
def nlp() -> NLPProcessor:
    return NLPProcessor()


class TestNLPProcessor:
    def test_bullish_sentiment(self, nlp: NLPProcessor) -> None:
        result = nlp.analyze_sentiment("Bitcoin surges on massive rally and breakout")
        assert result.sentiment == "bullish"
        assert result.score > 0

    def test_bearish_sentiment(self, nlp: NLPProcessor) -> None:
        result = nlp.analyze_sentiment("Market crash fears grow, selloff accelerates")
        assert result.sentiment == "bearish"
        assert result.score < 0

    def test_neutral_sentiment(self, nlp: NLPProcessor) -> None:
        result = nlp.analyze_sentiment("Markets traded sideways today with low volume")
        assert result.sentiment == "neutral"

    def test_empty_text(self, nlp: NLPProcessor) -> None:
        result = nlp.analyze_sentiment("")
        assert result.sentiment == "neutral"
        assert result.score == 0.0
        assert result.confidence == 0.0

    def test_batch_analysis(self, nlp: NLPProcessor) -> None:
        texts = [
            "Strong rally in crypto markets",
            "Stocks crash amid recession fears",
            "Markets unchanged on quiet session",
        ]
        agg = nlp.analyze_batch(texts)
        assert agg.n_sources == 3
        assert agg.bullish_pct + agg.bearish_pct + agg.neutral_pct == pytest.approx(100.0)

    def test_entity_extraction(self, nlp: NLPProcessor) -> None:
        result = nlp.classify_text("BTC RSI shows oversold, MACD crossing bullish")
        assert any("BTC" in e for e in result.entities)
        assert any("RSI" in e for e in result.entities)

    def test_text_classification(self, nlp: NLPProcessor) -> None:
        result = nlp.classify_text("Buy EURUSD at 1.0850 with SL at 1.0800 and TP at 1.0950")
        assert result.category == "trade_signal"
        assert result.confidence > 0
