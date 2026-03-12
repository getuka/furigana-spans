"""Main analyzer implementation."""

from __future__ import annotations

from furigana_spans.ambiguity import AmbiguityResolver
from furigana_spans.backends.base import BaseTokenizerBackend
from furigana_spans.backends.sudachi_backend import SudachiBackend
from furigana_spans.candidate_generator import CandidateGenerator
from furigana_spans.config import AnalyzerConfig
from furigana_spans.normalizer import TextNormalizer
from furigana_spans.number_rules import NumberRuleEngine
from furigana_spans.oov_fallback import OovFallback
from furigana_spans.schema import RubyAnalysis
from furigana_spans.span_builder import SpanBuilder


class RubyAnalyzer:
    """Structured ruby analyzer.

    This class performs tokenization and ruby prediction, and returns only
    structured results. Rendering is out of scope for this package.
    """

    def __init__(
        self,
        config: AnalyzerConfig | None = None,
        backend: BaseTokenizerBackend | None = None,
    ) -> None:
        """Initialize analyzer subcomponents."""
        self._config = config or AnalyzerConfig()
        self._normalizer = TextNormalizer()
        self._backend = backend or SudachiBackend(self._config)
        self._candidate_generator = CandidateGenerator(self._config, self._backend)
        self._ambiguity_resolver = AmbiguityResolver(self._config)
        self._number_rules = NumberRuleEngine(self._config)
        self._oov_fallback = OovFallback(self._config)
        self._span_builder = SpanBuilder(self._config)

    def analyze(self, text: str) -> RubyAnalysis:
        """Analyze one sentence and predict ruby spans."""
        normalized_text = self._normalizer.normalize(text)
        warnings: list[str] = []
        tokens = self._backend.tokenize(text)
        tokens = self._candidate_generator.enrich(tokens)
        if self._config.enable_number_rules:
            tokens = self._number_rules.apply(text, tokens)
        if self._config.enable_ambiguity_resolution:
            tokens = self._ambiguity_resolver.resolve(text, tokens)
        if self._config.enable_oov_fallback:
            tokens = self._oov_fallback.apply(text, tokens)
        spans = self._span_builder.build(text, tokens)
        if any(token.reading is None for token in tokens if token.surface.strip()):
            warnings.append("Some tokens have no resolved reading.")
        return RubyAnalysis(
            text=text,
            normalized_text=normalized_text,
            tokens=tokens,
            spans=spans,
            warnings=warnings,
            metadata={
                "reading_script": self._config.reading_script,
            },
        )
