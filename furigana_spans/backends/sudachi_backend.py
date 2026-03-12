"""Sudachi backend implementation for ruby analysis."""

from __future__ import annotations

from typing import Iterable

from furigana_spans.backends.base import BaseTokenizerBackend
from furigana_spans.config import AnalyzerConfig
from furigana_spans.schema import ReadingCandidate, RubyToken
from furigana_spans.script import normalize_reading

from sudachipy import Config, Dictionary, SplitMode

_FIELD_SET = {
    "pos",
    "normalized_form",
    "dictionary_form",
    "reading_form",
}


class SudachiBackend(BaseTokenizerBackend):
    """Tokenizer backend backed by SudachiPy."""

    def __init__(self, config: AnalyzerConfig) -> None:
        """Initialize the Sudachi tokenizer."""

        self._config = config
        self._split_mode = getattr(SplitMode, config.split_mode)
        dictionary = self._build_dictionary(config)
        self._tokenizer = dictionary.create(mode=self._split_mode, fields=_FIELD_SET)
        self._dictionary = dictionary

    def tokenize(self, text: str) -> list[RubyToken]:
        """Tokenize input text into RubyToken objects."""
        result: list[RubyToken] = []
        morphemes = self._tokenizer.tokenize(text)
        for morpheme in morphemes:
            raw_reading = morpheme.reading_form() or ""
            normalized = normalize_reading(raw_reading, self._config.reading_script)
            candidates: list[ReadingCandidate] = []
            if normalized:
                candidates.append(
                    ReadingCandidate(
                        reading=normalized,
                        score=0.9,
                        source="sudachi",
                        is_selected=True,
                    )
                )
            token = RubyToken(
                surface=morpheme.surface(),
                start=morpheme.begin(),
                end=morpheme.end(),
                pos=tuple(morpheme.part_of_speech()),
                base_form=morpheme.dictionary_form(),
                normalized_form=morpheme.normalized_form(),
                reading=normalized or None,
                pronunciation=normalized or None,
                is_oov=bool(morpheme.is_oov()),
                dictionary_id=morpheme.dictionary_id(),
                candidates=candidates,
                metadata={},
            )
            result.append(token)
        return result

    def lookup_readings(self, surface: str) -> list[str]:
        """Look up candidate readings for a surface string."""
        try:
            morphemes = self._dictionary.lookup(surface)
        except Exception:  # pragma: no cover
            return []
        readings: list[str] = []
        for morpheme in morphemes:
            raw_reading = morpheme.reading_form() or ""
            normalized = normalize_reading(raw_reading, self._config.reading_script)
            if normalized:
                readings.append(normalized)
        return _deduplicate_preserve_order(readings)

    @staticmethod
    def _build_dictionary(config: AnalyzerConfig):
        """Construct a Sudachi dictionary with optional user dictionaries."""
        if config.enable_user_dictionary and config.user_dictionary_paths:
            sudachi_config = Config(system=config.dictionary, user=list(config.user_dictionary_paths))
            return Dictionary(config=sudachi_config)
        return Dictionary(dict=config.dictionary)


def _deduplicate_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
