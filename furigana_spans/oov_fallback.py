"""Fallback logic for OOV readings."""

from __future__ import annotations

from dataclasses import replace

from furigana_spans.config import AnalyzerConfig
from furigana_spans.japanese_numbers import parse_number, to_sino_kana
from furigana_spans.schema import ReadingCandidate, RubyToken
from furigana_spans.script import (
    contains_alpha,
    contains_number,
    is_kana_only,
    latin_to_katakana,
    normalize_reading,
    normalize_surface,
)


class OovFallback:
    """Estimate readings for tokens without reliable dictionary output."""

    def __init__(self, config: AnalyzerConfig) -> None:
        self._config = config

    def apply(self, text: str, tokens: list[RubyToken]) -> list[RubyToken]:
        """Apply fallback reading estimation to tokens."""
        resolved: list[RubyToken] = []
        for token in tokens:
            if token.reading:
                resolved.append(token)
                continue
            fallback = self._estimate_reading(token.surface)
            if fallback is None:
                resolved.append(token)
                continue
            candidates = list(token.candidates)
            candidates.insert(
                0,
                ReadingCandidate(
                    reading=fallback,
                    score=0.35,
                    source="oov_fallback",
                    is_selected=True,
                ),
            )
            for candidate in candidates[1:]:
                candidate.is_selected = False
            resolved.append(
                replace(
                    token,
                    reading=fallback,
                    pronunciation=fallback,
                    candidates=candidates[: self._config.candidate_limit],
                    metadata={**token.metadata, "fallback_applied": True},
                )
            )
        return resolved

    def _estimate_reading(self, surface: str) -> str | None:
        normalized = normalize_surface(surface)
        if is_kana_only(normalized):
            return normalize_reading(normalized, self._config.reading_script)
        if contains_alpha(normalized) and not any("一" <= char <= "龯" for char in normalized):
            katakana = latin_to_katakana(normalized)
            return normalize_reading(katakana, self._config.reading_script)
        if contains_number(normalized) and normalized.isdigit():
            parsed = parse_number(normalized)
            if parsed is not None:
                return normalize_reading(to_sino_kana(parsed), self._config.reading_script)
        return None
