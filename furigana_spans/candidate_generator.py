"""Candidate enrichment for ruby readings."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from furigana_spans.backends.base import BaseTokenizerBackend
from furigana_spans.config import AnalyzerConfig
from furigana_spans.lexicon import BUILTIN_AMBIGUITY_PROFILES
from furigana_spans.schema import ReadingCandidate, RubyToken
from furigana_spans.script import contains_kanji, normalize_reading, normalize_surface
from furigana_spans.user_dict import UserDictionary


class CandidateGenerator:
    """Attach or refine reading candidates.

    Candidate sources:
    - backend primary reading
    - backend dictionary lookup
    - built-in ambiguity lexicon
    - optional user dictionary
    """

    def __init__(self, config: AnalyzerConfig, backend: BaseTokenizerBackend) -> None:
        self._config = config
        self._backend = backend
        self._profiles_by_surface: dict[str, list[str]] = defaultdict(list)
        for profile in BUILTIN_AMBIGUITY_PROFILES:
            self._profiles_by_surface[profile.surface].append(profile.reading)
        self._user_dict = None
        if config.enable_user_dictionary and config.user_dictionary_paths:
            self._user_dict = UserDictionary(
                config.user_dictionary_paths,
                config.reading_script,
            )

    def enrich(self, tokens: list[RubyToken]) -> list[RubyToken]:
        """Attach extra reading candidates to tokens."""
        enriched: list[RubyToken] = []
        for token in tokens:
            candidates = self._collect_candidates(token)
            enriched.append(self._replace_candidates(token, candidates))
        return enriched

    def _collect_candidates(self, token: RubyToken) -> list[ReadingCandidate]:
        table: dict[str, ReadingCandidate] = {}

        for candidate in token.candidates:
            self._upsert_candidate(table, candidate)

        if contains_kanji(token.surface):
            for reading in self._backend.lookup_readings(token.surface):
                self._upsert_candidate(
                    table,
                    ReadingCandidate(
                        reading=reading,
                        score=0.72,
                        source="sudachi_lookup",
                    ),
                )

        for reading in self._profiles_by_surface.get(normalize_surface(token.surface), []):
            reading = normalize_reading(reading, self._config.reading_script)
            self._upsert_candidate(
                table,
                ReadingCandidate(
                    reading=reading,
                    score=0.6,
                    source="ambiguity_lexicon",
                ),
            )

        if self._user_dict is not None:
            for entry in self._user_dict.lookup(token.surface, token.base_form, token.pos):
                self._upsert_candidate(
                    table,
                    ReadingCandidate(
                        reading=entry.reading,
                        score=0.95,
                        source=entry.source,
                    ),
                )

        ranked = sorted(
            table.values(),
            key=lambda item: (item.score is not None, item.score or -1.0),
            reverse=True,
        )
        limited = ranked[: self._config.candidate_limit]
        _mark_selected_from_primary(limited, token.reading)
        return limited

    @staticmethod
    def _upsert_candidate(
        table: dict[str, ReadingCandidate],
        candidate: ReadingCandidate,
    ) -> None:
        existing = table.get(candidate.reading)
        if existing is None:
            table[candidate.reading] = replace(candidate)
            return
        existing_score = existing.score if existing.score is not None else -1.0
        new_score = candidate.score if candidate.score is not None else -1.0
        if new_score > existing_score:
            existing.score = candidate.score
            existing.source = candidate.source
        existing.is_selected = existing.is_selected or candidate.is_selected

    def _replace_candidates(
        self,
        token: RubyToken,
        candidates: list[ReadingCandidate],
    ) -> RubyToken:
        selected = next((item for item in candidates if item.is_selected), None)
        reading = token.reading
        if reading is None and selected is not None:
            reading = selected.reading
        pronunciation = token.pronunciation or reading
        return replace(
            token,
            reading=reading,
            pronunciation=pronunciation,
            candidates=candidates,
        )


def _mark_selected_from_primary(
    candidates: list[ReadingCandidate],
    reading: str | None,
) -> None:
    selected_any = False
    for candidate in candidates:
        candidate.is_selected = candidate.reading == reading if reading else False
        selected_any = selected_any or candidate.is_selected
    if not candidates:
        return
    if not selected_any:
        candidates[0].is_selected = True
