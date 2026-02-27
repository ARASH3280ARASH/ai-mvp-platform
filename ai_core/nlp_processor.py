"""
NLP Processor — Market sentiment analysis and text classification.

Analyzes trading-related text (news headlines, strategy descriptions,
market commentary) to extract sentiment signals and classify market
conditions. Supports both English and Persian (Farsi) text.

Uses a lexicon-based approach for fast, dependency-light sentiment scoring
with optional transformer model upgrade path.

Typical usage:
    >>> nlp = NLPProcessor()
    >>> result = nlp.analyze_sentiment("Bitcoin surges past $70K on ETF inflows")
    >>> print(result.sentiment, result.score)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ai_core.config import AIConfig, NLPConfig

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Output of sentiment analysis."""

    sentiment: str  # "bullish", "bearish", "neutral"
    score: float  # -1.0 (most bearish) to +1.0 (most bullish)
    confidence: float  # 0.0 to 1.0
    keywords_found: Dict[str, List[str]]  # category → matched keywords
    word_count: int


@dataclass
class TextClassification:
    """Output of text classification."""

    category: str  # "market_analysis", "trade_signal", "news", "education"
    confidence: float
    entities: List[str]  # extracted symbols, indicators, etc.


@dataclass
class MarketSentimentAggregation:
    """Aggregated sentiment across multiple text sources."""

    overall_sentiment: str
    overall_score: float
    n_sources: int
    bullish_pct: float
    bearish_pct: float
    neutral_pct: float
    trending_keywords: List[Tuple[str, int]]


class NLPProcessor:
    """Market-focused NLP for sentiment analysis and text classification.

    Parameters
    ----------
    config : AIConfig, optional
        Uses the ``nlp`` sub-config.
    """

    def __init__(self, config: Optional[AIConfig] = None) -> None:
        self._cfg = (config or AIConfig()).nlp
        self._lexicon = self._build_lexicon()

    # ------------------------------------------------------------------
    # Sentiment Analysis
    # ------------------------------------------------------------------

    def analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze the sentiment of a single text.

        Parameters
        ----------
        text : str
            Market-related text (headline, commentary, etc.).

        Returns
        -------
        SentimentResult
        """
        if not text or not text.strip():
            return SentimentResult(
                sentiment="neutral", score=0.0, confidence=0.0,
                keywords_found={}, word_count=0,
            )

        clean = self._preprocess(text)
        words = clean.split()
        word_count = len(words)

        score = 0.0
        matches: Dict[str, List[str]] = {"bullish": [], "bearish": [], "volatility": []}

        # Lexicon scoring
        for word in words:
            if word in self._lexicon:
                val, cat = self._lexicon[word]
                score += val
                if cat in matches:
                    matches[cat].append(word)

        # Bigram matching for phrases
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if bigram in self._lexicon:
                val, cat = self._lexicon[bigram]
                score += val
                if cat in matches:
                    matches[cat].append(bigram)

        # Normalize score to [-1, 1]
        max_possible = max(word_count * 0.3, 1.0)
        normalized = np.clip(score / max_possible, -1.0, 1.0)

        # Negation detection
        negation_words = {"not", "no", "never", "don't", "doesn't", "won't", "can't", "isn't"}
        for i, word in enumerate(words):
            if word in negation_words and i + 1 < len(words):
                normalized *= -0.5  # partial negation flip

        # Classify
        if normalized > self._cfg.bullish_threshold:
            sentiment = "bullish"
        elif normalized < self._cfg.bearish_threshold:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        total_kw = sum(len(v) for v in matches.values())
        confidence = min(1.0, total_kw / max(word_count * 0.15, 1.0))

        return SentimentResult(
            sentiment=sentiment,
            score=round(float(normalized), 4),
            confidence=round(confidence, 4),
            keywords_found={k: v for k, v in matches.items() if v},
            word_count=word_count,
        )

    def analyze_batch(self, texts: List[str]) -> MarketSentimentAggregation:
        """Aggregate sentiment across multiple text sources.

        Parameters
        ----------
        texts : list[str]
            Collection of market texts.

        Returns
        -------
        MarketSentimentAggregation
        """
        results = [self.analyze_sentiment(t) for t in texts if t and t.strip()]

        if not results:
            return MarketSentimentAggregation(
                overall_sentiment="neutral", overall_score=0.0, n_sources=0,
                bullish_pct=0.0, bearish_pct=0.0, neutral_pct=0.0,
                trending_keywords=[],
            )

        scores = [r.score for r in results]
        sentiments = [r.sentiment for r in results]
        n = len(results)

        overall_score = float(np.mean(scores))
        bullish_pct = sentiments.count("bullish") / n * 100
        bearish_pct = sentiments.count("bearish") / n * 100
        neutral_pct = sentiments.count("neutral") / n * 100

        if overall_score > self._cfg.bullish_threshold:
            overall = "bullish"
        elif overall_score < self._cfg.bearish_threshold:
            overall = "bearish"
        else:
            overall = "neutral"

        # Trending keywords
        kw_freq: Dict[str, int] = {}
        for r in results:
            for cat_words in r.keywords_found.values():
                for w in cat_words:
                    kw_freq[w] = kw_freq.get(w, 0) + 1

        trending = sorted(kw_freq.items(), key=lambda kv: kv[1], reverse=True)[:10]

        return MarketSentimentAggregation(
            overall_sentiment=overall,
            overall_score=round(overall_score, 4),
            n_sources=n,
            bullish_pct=round(bullish_pct, 1),
            bearish_pct=round(bearish_pct, 1),
            neutral_pct=round(neutral_pct, 1),
            trending_keywords=trending,
        )

    # ------------------------------------------------------------------
    # Text Classification
    # ------------------------------------------------------------------

    def classify_text(self, text: str) -> TextClassification:
        """Classify text into trading-related categories.

        Parameters
        ----------
        text : str
            Input text.

        Returns
        -------
        TextClassification
        """
        clean = self._preprocess(text)

        # Pattern-based classification
        categories = {
            "trade_signal": [
                r"\b(buy|sell|long|short|entry|exit)\b",
                r"\b(tp|sl|take profit|stop loss)\b",
                r"\b(target|signal)\b",
            ],
            "market_analysis": [
                r"\b(analysis|technical|fundamental|outlook)\b",
                r"\b(support|resistance|trend|pattern)\b",
                r"\b(fibonacci|ichimoku|elliott)\b",
            ],
            "news": [
                r"\b(breaking|report|data|release|announce)\b",
                r"\b(fed|ecb|gdp|cpi|nfp|fomc)\b",
                r"\b(regulation|policy|inflation)\b",
            ],
            "education": [
                r"\b(learn|tutorial|guide|how to|strategy)\b",
                r"\b(beginner|advanced|concept|explain)\b",
            ],
        }

        scores: Dict[str, float] = {}
        for cat, patterns in categories.items():
            match_count = sum(
                len(re.findall(p, clean, re.IGNORECASE)) for p in patterns
            )
            scores[cat] = match_count

        total = sum(scores.values())
        if total == 0:
            return TextClassification(category="unknown", confidence=0.0, entities=[])

        best_cat = max(scores, key=scores.get)  # type: ignore
        confidence = scores[best_cat] / total

        entities = self._extract_entities(clean)

        return TextClassification(
            category=best_cat,
            confidence=round(confidence, 4),
            entities=entities,
        )

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def _extract_entities(self, text: str) -> List[str]:
        """Extract trading-related entities (symbols, indicators)."""
        entities: List[str] = []

        # Symbol patterns
        symbol_pattern = r"\b(BTC|ETH|XAU|EUR|GBP|USD|JPY|AUD|NZD|CAD|CHF|SOL|XRP|ADA|DOGE)\b"
        symbols = re.findall(symbol_pattern, text.upper())
        entities.extend([f"SYMBOL:{s}" for s in set(symbols)])

        # Indicator patterns
        indicator_pattern = r"\b(RSI|MACD|SMA|EMA|ADX|ATR|CCI|BB|Bollinger|Ichimoku|Stochastic)\b"
        indicators = re.findall(indicator_pattern, text, re.IGNORECASE)
        entities.extend([f"INDICATOR:{i.upper()}" for i in set(indicators)])

        # Price levels
        price_pattern = r"\$[\d,]+\.?\d*|\d+\.?\d*\s*(?:USD|EUR|GBP)"
        prices = re.findall(price_pattern, text)
        entities.extend([f"PRICE:{p.strip()}" for p in prices[:5]])

        return entities

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess(text: str) -> str:
        """Clean and normalize text."""
        text = text.lower().strip()
        text = re.sub(r"https?://\S+", "", text)  # remove URLs
        text = re.sub(r"@\w+", "", text)  # remove mentions
        text = re.sub(r"#(\w+)", r"\1", text)  # remove # but keep word
        text = re.sub(r"[^\w\s\-/.]", " ", text)  # remove special chars
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _build_lexicon(self) -> Dict[str, Tuple[float, str]]:
        """Build the sentiment lexicon from config keywords."""
        lexicon: Dict[str, Tuple[float, str]] = {}

        for word in self._cfg.keyword_categories.get("bullish", []):
            lexicon[word.lower()] = (1.0, "bullish")

        for word in self._cfg.keyword_categories.get("bearish", []):
            lexicon[word.lower()] = (-1.0, "bearish")

        for word in self._cfg.keyword_categories.get("volatility", []):
            lexicon[word.lower()] = (-0.3, "volatility")

        # Additional trading-specific terms
        extra_bullish = {
            "moon": 0.8, "pump": 0.6, "recovery": 0.7, "growth": 0.5,
            "outperform": 0.7, "golden cross": 1.0, "oversold": 0.6,
            "reversal up": 0.8, "strong": 0.4, "upgrade": 0.6,
        }
        for term, val in extra_bullish.items():
            lexicon[term] = (val, "bullish")

        extra_bearish = {
            "dump": -0.6, "collapse": -0.9, "death cross": -1.0,
            "overbought": -0.6, "reversal down": -0.8, "downgrade": -0.6,
            "weak": -0.4, "loss": -0.3, "declining": -0.5,
        }
        for term, val in extra_bearish.items():
            lexicon[term] = (val, "bearish")

        return lexicon
