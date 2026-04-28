"""Rule-based reading disambiguation."""

from __future__ import annotations

from dataclasses import replace

from furigana_spans.config import AnalyzerConfig
from furigana_spans.lexicon import AmbiguityProfile, BUILTIN_AMBIGUITY_PROFILES
from furigana_spans.schema import ReadingCandidate, RubyToken
from furigana_spans.script import normalize_reading, normalize_surface


class AmbiguityResolver:
    """Select one reading from multiple candidates using light rules."""

    def __init__(self, config: AnalyzerConfig) -> None:
        self._config = config
        self._profiles_by_surface: dict[str, list[AmbiguityProfile]] = {}
        for profile in BUILTIN_AMBIGUITY_PROFILES:
            surface = normalize_surface(profile.surface)
            self._profiles_by_surface.setdefault(surface, []).append(profile)

    def resolve(self, text: str, tokens: list[RubyToken]) -> list[RubyToken]:
        """Resolve ambiguous token readings in sentence context."""
        resolved: list[RubyToken] = []
        for token in tokens:
            if len(token.candidates) <= 1:
                resolved.append(token)
                continue
            profiles = self._profiles_by_surface.get(normalize_surface(token.surface))
            if not profiles:
                resolved.append(self._select_highest(token))
                continue
            scored = [self._score_candidate(text, token, candidate, profiles) for candidate in token.candidates]
            scored.sort(
                key=lambda item: item.score if item.score is not None else -1.0,
                reverse=True,
            )
            for candidate in scored:
                candidate.is_selected = False
            scored[0].is_selected = True
            resolved.append(
                replace(
                    token,
                    reading=scored[0].reading,
                    pronunciation=scored[0].reading,
                    candidates=scored,
                    metadata={**token.metadata, "resolved_by": "ambiguity_rules"},
                )
            )
        return resolved

    def _score_candidate(
        self,
        text: str,
        token: RubyToken,
        candidate: ReadingCandidate,
        profiles: list[AmbiguityProfile],
    ) -> ReadingCandidate:
        """Score one reading candidate in sentence context."""
        score = candidate.score if candidate.score is not None else 0.5
        for profile in profiles:
            profile_reading = normalize_reading(profile.reading, self._config.reading_script)
            if profile_reading != candidate.reading:
                continue
            # For curated ambiguous surfaces, the backend's primary reading is
            # only a weak prior. Sudachi often returns a high-confidence
            # default reading even when the sentence context clearly indicates
            # another reading, e.g. 大阪の日本橋 -> にっぽんばし. Use the
            # profile score as the main prior and add only a small stability
            # bias for the backend reading.
            score = profile.base_score
            if token.reading == candidate.reading:
                score += 0.03
            for keyword in profile.positive_keywords:
                if keyword in text:
                    score += 0.12
            for keyword in profile.negative_keywords:
                if keyword in text:
                    score -= 0.10
        return replace(candidate, score=round(max(score, 0.0), 6))

    @staticmethod
    def _select_highest(token: RubyToken) -> RubyToken:
        candidates = sorted(
            [replace(item, is_selected=False) for item in token.candidates],
            key=lambda item: item.score if item.score is not None else -1.0,
            reverse=True,
        )
        candidates[0].is_selected = True
        return replace(
            token,
            reading=candidates[0].reading,
            pronunciation=candidates[0].reading,
            candidates=candidates,
        )
