"""Integration tests for ambiguity candidate handling."""

from __future__ import annotations

from furigana_spans import AnalyzerConfig, RubyAnalyzer


def test_ambiguity_marks_resolution_and_keeps_alternative_candidates() -> None:
    analyzer = RubyAnalyzer(AnalyzerConfig())
    analysis = analyzer.analyze("大阪の日本橋に行く")

    span = next(span for span in analysis.spans if span.surface == "日本橋")
    token = next(token for token in analysis.tokens if token.surface == "日本橋")

    assert span.reading == "にほんばし"
    assert token.reading == "にほんばし"
    assert token.metadata["resolved_by"] == "ambiguity_rules"
    assert {candidate.reading for candidate in token.candidates} == {"にほんばし", "にっぽんばし"}
