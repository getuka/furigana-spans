"""Public package interface for structured furigana span analysis."""

from furigana_spans.analyzer import RubyAnalyzer
from furigana_spans.config import AnalyzerConfig
from furigana_spans.schema import ReadingCandidate, RubyAnalysis, RubySpan, RubyToken

__all__ = [
    "AnalyzerConfig",
    "ReadingCandidate",
    "RubyAnalysis",
    "RubyAnalyzer",
    "RubySpan",
    "RubyToken",
]
