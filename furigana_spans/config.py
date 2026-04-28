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
        enable_difficulty_scoring: Attach ruby difficulty scores and reasons.
        difficulty_candidate_margin_threshold: Maximum top-2 candidate score
            gap treated as low-margin reading selection.
        difficulty_long_kanji_threshold: Minimum Kanji count treated as a
            long Kanji compound.
        enable_frequency_difficulty: Use normalized frequency TSV files to add
            low-frequency difficulty reasons.
        frequency_dictionary_paths: Normalized frequency TSV files.
        frequency_low_rank_threshold: Rank at or above this value is treated as
            a low-frequency word. Rank is 1-based, where larger rank is less
            frequent.
        frequency_very_low_rank_threshold: Rank at or above this value is
            treated as a very-low-frequency word.
        frequency_unknown_as_reason: Add ``unknown_frequency`` when frequency
            lookup misses. Disabled by default to avoid over-triggering.
        frequency_units: Unit priority for frequency lookup, e.g. ``luw`` then
            ``suw`` for BCCWJ long/short unit lists.
        enable_domain_difficulty: Use normalized domain lexicon TSV files to
            add technical/domain-term difficulty reasons.
        domain_lexicon_paths: Normalized domain lexicon TSV files.
        domain_min_surface_len: Ignore domain terms shorter than this length.
        domain_ignore_common_words: Ignore domain matches marked as common
            words unless they also carry a specific domain tag.
        domain_exact_match_only: Reserved for future partial/substring
            matching. The current implementation performs exact matching.
        enable_lexicon_compound_spans: Merge consecutive token spans when a
            longer surface is found in the configured frequency/domain lexicons.
        lexicon_compound_max_tokens: Maximum token n-gram length considered for
            lexicon compound span merging.
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
    enable_difficulty_scoring: bool = True
    difficulty_candidate_margin_threshold: float = 0.15
    difficulty_long_kanji_threshold: int = 3
    enable_frequency_difficulty: bool = False
    frequency_dictionary_paths: tuple[str, ...] = ()
    frequency_low_rank_threshold: int = 20_000
    frequency_very_low_rank_threshold: int = 50_000
    frequency_unknown_as_reason: bool = False
    frequency_units: tuple[str, ...] = ("luw", "suw")
    enable_domain_difficulty: bool = False
    domain_lexicon_paths: tuple[str, ...] = ()
    domain_min_surface_len: int = 2
    domain_ignore_common_words: bool = True
    domain_exact_match_only: bool = True
    enable_lexicon_compound_spans: bool = True
    lexicon_compound_max_tokens: int = 6
