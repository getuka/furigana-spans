"""Configuration models for the ruby analyzer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class AnalyzerConfig:
    """Runtime configuration for ruby prediction.

    Attributes:
        dictionary: Sudachi dictionary selection. Usually ``small``, ``core``,
            ``full``, or an absolute path to a compiled dictionary.
        split_mode: Sudachi split mode. ``A``/``B``/``C``.
        reading_script: Output script for readings.
        include_tokens_without_kanji: Whether spans may be emitted for tokens
            that do not include Kanji.
        enable_number_rules: Apply numeric and counter rules.
        enable_ambiguity_resolution: Apply rule-based ambiguity resolution.
        enable_oov_fallback: Apply limited fallback reading estimation.
        enable_user_dictionary: Load external user dictionary files.
        user_dictionary_paths: JSON/JSONL user dictionary files.
        candidate_limit: Keep at most this many candidates per token/span.
    """

    dictionary: str = "core"
    split_mode: Literal["A", "B", "C"] = "C"
    reading_script: Literal["hiragana", "katakana"] = "hiragana"
    include_tokens_without_kanji: bool = False
    enable_number_rules: bool = True
    enable_ambiguity_resolution: bool = True
    enable_oov_fallback: bool = True
    enable_user_dictionary: bool = False
    user_dictionary_paths: tuple[str, ...] = ()
    candidate_limit: int = 8
