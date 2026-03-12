"""Integration tests for numeric reading rules."""

from __future__ import annotations

from furigana_spans import AnalyzerConfig, RubyAnalyzer
from furigana_spans.japanese_numbers import parse_number


def test_number_rule_builds_compound_span() -> None:
    analyzer = RubyAnalyzer(AnalyzerConfig())
    analysis = analyzer.analyze("3人で行く")

    span = next(span for span in analysis.spans if span.surface == "3人")
    assert span.reading == "さんにん"


def test_number_rule_marks_compound_tokens() -> None:
    analyzer = RubyAnalyzer(AnalyzerConfig())
    analysis = analyzer.analyze("3人で行く")

    token = next(token for token in analysis.tokens if token.metadata.get("compound_reading") == "さんにん")
    assert token.metadata["compound_surface"] == "3人"


def test_parse_number_accepts_mixed_full_width_and_kanji_numerals() -> None:
    assert parse_number("１万") == 10_000
    assert parse_number("３百") == 300
    assert parse_number("1万") == 10_000
    assert parse_number("3百") == 300
