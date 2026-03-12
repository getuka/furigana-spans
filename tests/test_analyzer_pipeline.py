"""Integration tests for the analyzer pipeline."""

from __future__ import annotations

from furigana_spans import AnalyzerConfig, RubyAnalyzer


def test_pipeline_builds_compound_span_with_sudachi() -> None:
    analyzer = RubyAnalyzer(AnalyzerConfig())
    analysis = analyzer.analyze("3人で行く")

    span = next(span for span in analysis.spans if span.surface == "3人")
    assert span.reading == "さんにん"
    assert span.metadata["span_type"] == "number_counter"


def test_pipeline_enriches_candidates_with_ambiguity_profiles() -> None:
    analyzer = RubyAnalyzer(AnalyzerConfig())
    analysis = analyzer.analyze("日本橋")

    token = next(token for token in analysis.tokens if token.surface == "日本橋")
    readings = {candidate.reading for candidate in token.candidates}
    assert {"にほんばし", "にっぽんばし"} <= readings


def test_pipeline_respects_reading_script_configuration() -> None:
    analyzer = RubyAnalyzer(AnalyzerConfig(reading_script="katakana"))
    analysis = analyzer.analyze("日本橋")

    span = next(span for span in analysis.spans if span.surface == "日本橋")
    assert span.reading == "ニホンバシ"
