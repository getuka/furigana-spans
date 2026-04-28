"""Difficulty estimation for ruby annotations."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from furigana_spans.config import AnalyzerConfig
from furigana_spans.lexicons.domain import DomainLexiconProvider, DomainTermMatch
from furigana_spans.lexicons.frequency import FrequencyInfo, FrequencyProvider
from furigana_spans.schema import ReadingCandidate, RubyDifficulty, RubySpan, RubyToken
from furigana_spans.script import contains_alpha, contains_kanji, contains_number

REASON_AMBIGUOUS_READING = "ambiguous_reading"
REASON_RESOLVED_BY_CONTEXT_RULE = "resolved_by_context_rule"
REASON_LOW_CANDIDATE_MARGIN = "low_candidate_margin"
REASON_PROPER_NOUN = "proper_noun"
REASON_PERSON_NAME = "person_name"
REASON_PLACE_NAME = "place_name"
REASON_ORGANIZATION_NAME = "organization_name"
REASON_PRODUCT_NAME = "product_name"
REASON_WORK_TITLE = "work_title"
REASON_RARE_NAME = "rare_name"
REASON_OOV = "oov"
REASON_FALLBACK_READING = "fallback_reading"
REASON_NUMBER_COUNTER = "number_counter"
REASON_IRREGULAR_COUNTER_READING = "irregular_counter_reading"
REASON_LONG_KANJI_COMPOUND = "long_kanji_compound"
REASON_ALPHABETIC = "alphabetic"
REASON_MIXED_SCRIPT = "mixed_script"
REASON_USER_DICTIONARY = "user_dictionary"
REASON_DOMAIN_TERM = "domain_term"
REASON_TECHNICAL_TERM = "technical_term"
REASON_MEDICAL_TERM = "medical_term"
REASON_CHEMICAL_TERM = "chemical_term"
REASON_SCIENCE_TERM = "science_term"
REASON_COMPUTER_TERM = "computer_term"
REASON_LOW_FREQUENCY_WORD = "low_frequency_word"
REASON_VERY_LOW_FREQUENCY_WORD = "very_low_frequency_word"
REASON_UNKNOWN_FREQUENCY = "unknown_frequency"
REASON_LOW_FREQUENCY_COMPOUND = "low_frequency_compound"
REASON_MANUAL_DIFFICULTY_OVERRIDE = "manual_difficulty_override"
REASON_ALWAYS_RUBY = "always_ruby"

REASON_ORDER = (
    REASON_ALWAYS_RUBY,
    REASON_MANUAL_DIFFICULTY_OVERRIDE,
    REASON_OOV,
    REASON_FALLBACK_READING,
    REASON_AMBIGUOUS_READING,
    REASON_RESOLVED_BY_CONTEXT_RULE,
    REASON_LOW_CANDIDATE_MARGIN,
    REASON_PROPER_NOUN,
    REASON_PERSON_NAME,
    REASON_PLACE_NAME,
    REASON_ORGANIZATION_NAME,
    REASON_PRODUCT_NAME,
    REASON_WORK_TITLE,
    REASON_RARE_NAME,
    REASON_USER_DICTIONARY,
    REASON_DOMAIN_TERM,
    REASON_TECHNICAL_TERM,
    REASON_MEDICAL_TERM,
    REASON_CHEMICAL_TERM,
    REASON_SCIENCE_TERM,
    REASON_COMPUTER_TERM,
    REASON_LOW_FREQUENCY_WORD,
    REASON_VERY_LOW_FREQUENCY_WORD,
    REASON_UNKNOWN_FREQUENCY,
    REASON_LOW_FREQUENCY_COMPOUND,
    REASON_NUMBER_COUNTER,
    REASON_IRREGULAR_COUNTER_READING,
    REASON_LONG_KANJI_COMPOUND,
    REASON_ALPHABETIC,
    REASON_MIXED_SCRIPT,
)

REASON_WEIGHTS = {
    REASON_ALWAYS_RUBY: 1.00,
    REASON_MANUAL_DIFFICULTY_OVERRIDE: 0.00,
    REASON_OOV: 0.30,
    REASON_FALLBACK_READING: 0.30,
    REASON_AMBIGUOUS_READING: 0.30,
    REASON_RESOLVED_BY_CONTEXT_RULE: 0.10,
    REASON_LOW_CANDIDATE_MARGIN: 0.15,
    REASON_PROPER_NOUN: 0.20,
    REASON_PERSON_NAME: 0.25,
    REASON_PLACE_NAME: 0.25,
    REASON_ORGANIZATION_NAME: 0.20,
    REASON_PRODUCT_NAME: 0.20,
    REASON_WORK_TITLE: 0.20,
    REASON_RARE_NAME: 0.35,
    REASON_USER_DICTIONARY: 0.25,
    REASON_DOMAIN_TERM: 0.30,
    REASON_TECHNICAL_TERM: 0.25,
    REASON_MEDICAL_TERM: 0.30,
    REASON_CHEMICAL_TERM: 0.30,
    REASON_SCIENCE_TERM: 0.25,
    REASON_COMPUTER_TERM: 0.25,
    REASON_LOW_FREQUENCY_WORD: 0.20,
    REASON_VERY_LOW_FREQUENCY_WORD: 0.30,
    REASON_UNKNOWN_FREQUENCY: 0.10,
    REASON_LOW_FREQUENCY_COMPOUND: 0.25,
    REASON_NUMBER_COUNTER: 0.25,
    REASON_IRREGULAR_COUNTER_READING: 0.20,
    REASON_LONG_KANJI_COMPOUND: 0.15,
    REASON_ALPHABETIC: 0.10,
    REASON_MIXED_SCRIPT: 0.10,
}


REASON_FAMILIES = {
    "manual": (
        REASON_ALWAYS_RUBY,
        REASON_MANUAL_DIFFICULTY_OVERRIDE,
    ),
    "oov": (
        REASON_OOV,
        REASON_FALLBACK_READING,
    ),
    "reading_uncertainty": (
        REASON_AMBIGUOUS_READING,
        REASON_RESOLVED_BY_CONTEXT_RULE,
        REASON_LOW_CANDIDATE_MARGIN,
    ),
    "named_entity": (
        REASON_PROPER_NOUN,
        REASON_PERSON_NAME,
        REASON_PLACE_NAME,
        REASON_ORGANIZATION_NAME,
        REASON_PRODUCT_NAME,
        REASON_WORK_TITLE,
        REASON_RARE_NAME,
    ),
    "lexical": (
        REASON_USER_DICTIONARY,
    ),
    "domain": (
        REASON_DOMAIN_TERM,
        REASON_TECHNICAL_TERM,
        REASON_MEDICAL_TERM,
        REASON_CHEMICAL_TERM,
        REASON_SCIENCE_TERM,
        REASON_COMPUTER_TERM,
    ),
    "lexical_frequency": (
        REASON_LOW_FREQUENCY_WORD,
        REASON_VERY_LOW_FREQUENCY_WORD,
        REASON_UNKNOWN_FREQUENCY,
        REASON_LOW_FREQUENCY_COMPOUND,
    ),
    "numeric": (
        REASON_NUMBER_COUNTER,
        REASON_IRREGULAR_COUNTER_READING,
    ),
    "orthographic": (
        REASON_LONG_KANJI_COMPOUND,
        REASON_ALPHABETIC,
        REASON_MIXED_SCRIPT,
    ),
}

# Families are combined with Noisy-OR, but each family needs a different
# intra-family policy. Hierarchical families such as named entities use max
# to avoid stacking proper_noun + person_name + rare_name. Families where one
# reason intensifies another, such as number_counter + irregular_counter_reading
# or oov + fallback_reading, use a capped sum.
FAMILY_AGGREGATION = {
    "oov": "capped_sum",
    "reading_uncertainty": "capped_sum",
    "named_entity": "max",
    "lexical": "capped_sum",
    "domain": "capped_sum",
    "lexical_frequency": "capped_sum",
    "numeric": "capped_sum",
    "orthographic": "max",
}

FAMILY_SCORE_CAPS = {
    "oov": 0.45,
    "reading_uncertainty": 0.45,
    "lexical": 0.45,
    "domain": 0.45,
    "lexical_frequency": 0.40,
    "numeric": 0.45,
}

_NAMED_ENTITY_REASON_ALIASES = {
    "person": REASON_PERSON_NAME,
    "person_name": REASON_PERSON_NAME,
    "name": REASON_PERSON_NAME,
    "human_name": REASON_PERSON_NAME,
    "place": REASON_PLACE_NAME,
    "place_name": REASON_PLACE_NAME,
    "location": REASON_PLACE_NAME,
    "location_name": REASON_PLACE_NAME,
    "地名": REASON_PLACE_NAME,
    "人名": REASON_PERSON_NAME,
    "組織": REASON_ORGANIZATION_NAME,
    "organization": REASON_ORGANIZATION_NAME,
    "organization_name": REASON_ORGANIZATION_NAME,
    "org": REASON_ORGANIZATION_NAME,
    "product": REASON_PRODUCT_NAME,
    "product_name": REASON_PRODUCT_NAME,
    "work": REASON_WORK_TITLE,
    "work_title": REASON_WORK_TITLE,
    "title": REASON_WORK_TITLE,
    "rare_name": REASON_RARE_NAME,
}

_DOMAIN_TAGS = {
    "domain",
    "domain_term",
    "technical",
    "technical_term",
    "specialized",
    "science_term",
    "medical_term",
    "chemical_term",
    "computer_term",
    "専門語",
}

_DOMAIN_TAG_REASON_ALIASES = {
    "domain": REASON_DOMAIN_TERM,
    "domain_term": REASON_DOMAIN_TERM,
    "technical": REASON_TECHNICAL_TERM,
    "technical_term": REASON_TECHNICAL_TERM,
    "specialized": REASON_TECHNICAL_TERM,
    "専門語": REASON_TECHNICAL_TERM,
    "science": REASON_SCIENCE_TERM,
    "science_term": REASON_SCIENCE_TERM,
    "medical": REASON_MEDICAL_TERM,
    "medical_term": REASON_MEDICAL_TERM,
    "medicine": REASON_MEDICAL_TERM,
    "chemical": REASON_CHEMICAL_TERM,
    "chemical_term": REASON_CHEMICAL_TERM,
    "chemistry": REASON_CHEMICAL_TERM,
    "computer": REASON_COMPUTER_TERM,
    "computer_term": REASON_COMPUTER_TERM,
    "it": REASON_COMPUTER_TERM,
}

_NAMED_ENTITY_SUBTYPE_REASONS = {
    REASON_PERSON_NAME,
    REASON_PLACE_NAME,
    REASON_ORGANIZATION_NAME,
    REASON_PRODUCT_NAME,
    REASON_WORK_TITLE,
    REASON_RARE_NAME,
}

_PERSON_CONTEXT_SUFFIXES = (
    "さん",
    "氏",
    "様",
    "君",
    "ちゃん",
    "先生",
    "教授",
    "博士",
)

_PLACE_SUFFIXES = (
    "都",
    "道",
    "府",
    "県",
    "市",
    "区",
    "町",
    "村",
    "郡",
    "駅",
    "空港",
    "港",
    "山",
    "川",
    "湖",
    "島",
    "湾",
    "海峡",
    "温泉",
    "神社",
    "寺",
    "城",
)

_ORGANIZATION_SUFFIXES = (
    "株式会社",
    "有限会社",
    "合同会社",
    "会社",
    "大学院",
    "大学",
    "高等学校",
    "高校",
    "中学校",
    "小学校",
    "研究室",
    "研究所",
    "病院",
    "銀行",
    "協会",
    "学会",
    "財団",
    "法人",
    "機構",
    "庁",
    "省",
    "委員会",
    "センター",
    "社",
)

_WORK_TITLE_LEFT_QUOTES = "「『《〈【"
_WORK_TITLE_RIGHT_QUOTES = "」』》〉】"
_PRODUCT_CODE_PATTERN = re.compile(
    r"(?:[A-Za-z]{2,}[-_ ]?\d|\d+[A-Za-z]{2,}|[A-Z]{2,}(?:[-_][A-Z0-9]+)+)"
)


class DifficultyEstimator:
    """Estimate ruby annotation necessity for tokens and spans.

    The score is a heuristic reading-risk score in the closed interval
    ``[0.0, 1.0]``. It intentionally does not reuse
    :class:`ReadingCandidate.score`, because candidate confidence and ruby
    necessity are different signals.
    """

    def __init__(self, config: AnalyzerConfig) -> None:
        self._config = config
        self._frequency_provider = (
            FrequencyProvider.from_paths(
                config.frequency_dictionary_paths,
                unit_priority=config.frequency_units,
            )
            if config.enable_frequency_difficulty and config.frequency_dictionary_paths
            else None
        )
        self._domain_provider = (
            DomainLexiconProvider.from_paths(config.domain_lexicon_paths)
            if config.enable_domain_difficulty and config.domain_lexicon_paths
            else None
        )

    def score_tokens(self, text: str, tokens: list[RubyToken]) -> list[RubyToken]:
        """Attach token-level difficulty estimates."""
        del text
        scored_tokens: list[RubyToken] = []
        for token in tokens:
            difficulty, evidence = self._score_token(token)
            metadata = dict(token.metadata)
            metadata.update(evidence)
            scored_tokens.append(
                replace(token, difficulty=difficulty, metadata=metadata)
            )
        return scored_tokens

    def score_spans(
        self,
        text: str,
        tokens: list[RubyToken],
        spans: list[RubySpan],
    ) -> list[RubySpan]:
        """Attach span-level difficulty estimates."""
        spans = self._augment_lexicon_compound_spans(text, tokens, spans)
        scored_spans: list[RubySpan] = []
        for span in spans:
            difficulty, evidence = self._score_span(text, span, tokens)
            metadata = dict(span.metadata)
            metadata.update(evidence)
            scored_spans.append(
                replace(span, difficulty=difficulty, metadata=metadata)
            )
        return scored_spans

    def _augment_lexicon_compound_spans(
        self,
        text: str,
        tokens: list[RubyToken],
        spans: list[RubySpan],
    ) -> list[RubySpan]:
        """Merge token spans when a longer lexicon entry is available.

        Frequency/domain dictionaries often contain long-unit terms such as
        ``深層強化学習`` while a tokenizer may split the same string into
        ``深層``/``強化``/``学習``. This pass creates a single span for the
        longer lexicon hit so that difficulty reasons and downstream ruby
        insertion operate at the useful phrase level.
        """
        if not self._config.enable_lexicon_compound_spans:
            return spans
        if self._frequency_provider is None and self._domain_provider is None:
            return spans
        if len(tokens) < 2:
            return spans

        compound_by_start: dict[int, RubySpan] = {}
        covered_indices: set[int] = set()
        max_tokens = max(2, self._config.lexicon_compound_max_tokens)
        index = 0
        while index < len(tokens):
            if index in covered_indices or tokens[index].metadata.get("merged_into_previous"):
                index += 1
                continue
            compound = self._find_longest_lexicon_compound(
                text,
                tokens,
                index,
                max_tokens,
            )
            if compound is None:
                index += 1
                continue
            compound_by_start[index] = compound
            for token_index in compound.token_indices:
                covered_indices.add(token_index)
            index = compound.token_indices[-1] + 1

        if not compound_by_start:
            return spans

        result: list[RubySpan] = []
        emitted_compounds: set[int] = set()
        for span in spans:
            first_index = span.token_indices[0] if span.token_indices else -1
            if first_index in compound_by_start and first_index not in emitted_compounds:
                result.append(compound_by_start[first_index])
                emitted_compounds.add(first_index)
                continue
            if any(token_index in covered_indices for token_index in span.token_indices):
                continue
            result.append(span)
        for first_index, compound in compound_by_start.items():
            if first_index not in emitted_compounds:
                result.append(compound)
        result.sort(key=lambda item: (item.start, item.end))
        return result

    def _find_longest_lexicon_compound(
        self,
        text: str,
        tokens: list[RubyToken],
        start_index: int,
        max_tokens: int,
    ) -> RubySpan | None:
        upper = min(len(tokens), start_index + max_tokens)
        for end_index in range(upper, start_index + 1, -1):
            ngram = tokens[start_index:end_index]
            if any(token.metadata.get("merged_into_previous") for token in ngram):
                continue
            surface = "".join(token.surface for token in ngram)
            if not surface or text[ngram[0].start : ngram[-1].end] != surface:
                continue
            if (
                not self._config.include_tokens_without_kanji
                and not contains_kanji(surface)
                and not contains_number(surface)
            ):
                continue
            if not self._is_lexicon_compound_surface(surface):
                continue
            reading = "".join(token.reading or "" for token in ngram)
            if not reading:
                continue
            return RubySpan(
                surface=surface,
                reading=reading,
                start=ngram[0].start,
                end=ngram[-1].end,
                token_indices=list(range(start_index, end_index)),
                pos=ngram[0].pos,
                normalized_form=surface,
                source="lexicon_compound",
                candidates=[],
                metadata={
                    "span_type": "lexicon_compound",
                    "compound_token_count": len(ngram),
                },
            )
        return None

    def _is_lexicon_compound_surface(self, surface: str) -> bool:
        if self._domain_provider is not None:
            matches = self._domain_provider.lookup(surface, base_form=surface)
            if any(self._keep_domain_match(match) for match in matches):
                return True
        if _kanji_count(surface) < self._config.difficulty_long_kanji_threshold:
            return False
        if self._frequency_provider is not None:
            info = self._frequency_provider.lookup(surface, base_form=surface)
            if info is not None and info.rank is not None:
                return info.rank >= self._config.frequency_low_rank_threshold
        return False

    def _score_token(self, token: RubyToken) -> tuple[RubyDifficulty, dict[str, Any]]:
        reasons: list[str] = []
        overrides: list[float] = []
        evidence: dict[str, Any] = {}

        if _has_multiple_readings(token.candidates):
            reasons.append(REASON_AMBIGUOUS_READING)
        if token.metadata.get("resolved_by") == "ambiguity_rules":
            reasons.append(REASON_RESOLVED_BY_CONTEXT_RULE)
        if _has_low_candidate_margin(
            token.candidates,
            self._config.difficulty_candidate_margin_threshold,
        ):
            reasons.append(REASON_LOW_CANDIDATE_MARGIN)
        if _is_proper_noun(token.pos):
            reasons.append(REASON_PROPER_NOUN)
        reasons.extend(_proper_noun_subtype_reasons(token.pos))
        if token.is_oov:
            reasons.append(REASON_OOV)
        if token.metadata.get("fallback_applied") is True:
            reasons.append(REASON_FALLBACK_READING)
        if _kanji_count(token.surface) >= self._config.difficulty_long_kanji_threshold:
            reasons.append(REASON_LONG_KANJI_COMPOUND)
        if contains_alpha(token.surface):
            reasons.append(REASON_ALPHABETIC)
        if _is_mixed_script(token.surface):
            reasons.append(REASON_MIXED_SCRIPT)
        if _uses_user_dictionary(token.candidates):
            reasons.append(REASON_USER_DICTIONARY)
        _collect_user_dictionary_signals(token.candidates, reasons, overrides)
        self._collect_frequency_signals(
            surface=token.surface,
            base_form=token.base_form or token.normalized_form,
            reasons=reasons,
            evidence=evidence,
            is_compound=False,
            token_count=1,
        )
        self._collect_domain_signals(
            surface=token.surface,
            base_form=token.base_form or token.normalized_form,
            reasons=reasons,
            evidence=evidence,
        )
        _promote_named_entity_reasons(reasons)

        ordered_reasons = _normalize_reasons(reasons)
        return (
            RubyDifficulty(
                score=_score_from_reasons(ordered_reasons, overrides),
                reasons=ordered_reasons,
            ),
            evidence,
        )

    def _score_span(
        self,
        text: str,
        span: RubySpan,
        tokens: list[RubyToken],
    ) -> tuple[RubyDifficulty, dict[str, Any]]:
        reasons: list[str] = []
        overrides: list[float] = []
        evidence: dict[str, Any] = {}
        span_tokens: list[RubyToken] = []
        for token_index in span.token_indices:
            if token_index < 0 or token_index >= len(tokens):
                continue
            token = tokens[token_index]
            span_tokens.append(token)
            token_difficulty = token.difficulty
            if token_difficulty is not None:
                reasons.extend(token_difficulty.reasons)
            _collect_user_dictionary_signals(token.candidates, reasons, overrides)

        if span.metadata.get("span_type") == "number_counter":
            reasons.append(REASON_NUMBER_COUNTER)
        if span.metadata.get("irregular_counter_reading") is True:
            reasons.append(REASON_IRREGULAR_COUNTER_READING)
        if _uses_user_dictionary(span.candidates):
            reasons.append(REASON_USER_DICTIONARY)
        _collect_user_dictionary_signals(span.candidates, reasons, overrides)
        reasons.extend(_proper_noun_subtype_reasons(span.pos))
        reasons.extend(_named_entity_surface_reasons(text, span, tokens))
        _promote_named_entity_reasons(reasons)
        if _is_mixed_script(span.surface):
            reasons.append(REASON_MIXED_SCRIPT)
        if contains_alpha(span.surface):
            reasons.append(REASON_ALPHABETIC)
        if _kanji_count(span.surface) >= self._config.difficulty_long_kanji_threshold:
            reasons.append(REASON_LONG_KANJI_COMPOUND)

        self._collect_frequency_signals(
            surface=span.surface,
            base_form=span.normalized_form,
            reasons=reasons,
            evidence=evidence,
            is_compound=len(span_tokens) >= 2,
            token_count=len(span_tokens),
        )
        self._collect_domain_signals(
            surface=span.surface,
            base_form=span.normalized_form,
            reasons=reasons,
            evidence=evidence,
        )

        ordered_reasons = _normalize_reasons(reasons)
        return (
            RubyDifficulty(
                score=_score_from_reasons(ordered_reasons, overrides),
                reasons=ordered_reasons,
            ),
            evidence,
        )

    def _collect_frequency_signals(
        self,
        surface: str,
        base_form: str | None,
        reasons: list[str],
        evidence: dict[str, Any],
        is_compound: bool,
        token_count: int,
    ) -> None:
        if self._frequency_provider is None:
            return
        info = self._frequency_provider.lookup(surface, base_form=base_form)
        if info is None:
            if self._config.frequency_unknown_as_reason:
                reasons.append(REASON_UNKNOWN_FREQUENCY)
            if is_compound and token_count >= 2 and _kanji_count(surface) >= 4:
                reasons.append(REASON_LOW_FREQUENCY_COMPOUND)
            return

        evidence["difficulty_frequency"] = _frequency_info_to_metadata(info)
        if info.rank is None:
            return
        if info.rank >= self._config.frequency_very_low_rank_threshold:
            reasons.append(REASON_VERY_LOW_FREQUENCY_WORD)
        elif info.rank >= self._config.frequency_low_rank_threshold:
            reasons.append(REASON_LOW_FREQUENCY_WORD)

    def _collect_domain_signals(
        self,
        surface: str,
        base_form: str | None,
        reasons: list[str],
        evidence: dict[str, Any],
    ) -> None:
        if self._domain_provider is None:
            return
        if len(surface) < self._config.domain_min_surface_len:
            return
        matches = self._domain_provider.lookup(surface, base_form=base_form)
        filtered = [match for match in matches if self._keep_domain_match(match)]
        if not filtered:
            return

        evidence["difficulty_domain_terms"] = [
            _domain_match_to_metadata(match) for match in filtered
        ]
        reasons.append(REASON_DOMAIN_TERM)
        for match in filtered:
            if match.tags:
                for tag in match.tags:
                    reasons.append(_domain_tag_to_reason(tag))
            else:
                reasons.append(REASON_TECHNICAL_TERM)

    def _keep_domain_match(self, match: DomainTermMatch) -> bool:
        if not self._config.domain_ignore_common_words:
            return True
        if str(match.common_word_flag).strip().lower() not in {"1", "true", "t"}:
            return True
        generic_reasons = {REASON_TECHNICAL_TERM, REASON_SCIENCE_TERM}
        return any(_domain_tag_to_reason(tag) not in generic_reasons for tag in match.tags)


def _frequency_info_to_metadata(info: FrequencyInfo) -> dict[str, Any]:
    return {
        "surface": info.surface,
        "base_form": info.base_form,
        "unit": info.unit,
        "frequency": info.frequency,
        "rank": info.rank,
        "log_frequency": info.log_frequency,
        "source": info.source,
        "register": info.register,
    }


def _domain_match_to_metadata(match: DomainTermMatch) -> dict[str, Any]:
    return {
        "surface": match.surface,
        "base_form": match.base_form,
        "source_dictionary": match.source_dictionary,
        "category_code": match.category_code,
        "headword_flag": match.headword_flag,
        "common_word_flag": match.common_word_flag,
        "tags": list(match.tags),
        "score": match.score,
    }


def _domain_tag_to_reason(tag: str) -> str:
    return _DOMAIN_TAG_REASON_ALIASES.get(str(tag), REASON_TECHNICAL_TERM)


def _has_multiple_readings(candidates: list[ReadingCandidate]) -> bool:
    readings = {candidate.reading for candidate in candidates if candidate.reading}
    return len(readings) >= 2


def _has_low_candidate_margin(
    candidates: list[ReadingCandidate],
    threshold: float,
) -> bool:
    scored = sorted(
        (
            candidate.score
            for candidate in candidates
            if candidate.score is not None
        ),
        reverse=True,
    )
    if len(scored) < 2:
        return False
    return scored[0] - scored[1] <= threshold


def _is_proper_noun(pos: tuple[str, ...]) -> bool:
    return "固有名詞" in pos


def _proper_noun_subtype_reasons(pos: tuple[str, ...]) -> list[str]:
    reasons: list[str] = []
    pos_set = set(pos)
    if "人名" in pos_set or "姓" in pos_set or "名" in pos_set:
        reasons.append(REASON_PERSON_NAME)
    if "地名" in pos_set or "国" in pos_set:
        reasons.append(REASON_PLACE_NAME)
    if "組織" in pos_set or "組織名" in pos_set or "団体" in pos_set:
        reasons.append(REASON_ORGANIZATION_NAME)
    return reasons


def _named_entity_surface_reasons(
    text: str,
    span: RubySpan,
    tokens: list[RubyToken],
) -> list[str]:
    """Infer named-entity subtype reasons from surface and local context.

    These heuristics are intentionally conservative. Place/person suffixes are
    only trusted for already proper-noun-like spans. Organization and product
    patterns may promote non-POS proper nouns when the surface itself carries
    strong evidence such as ``東京大学`` or ``RTX4090``.
    """
    reasons: list[str] = []
    surface = span.surface
    proper_like = _is_proper_noun(span.pos) or _uses_user_dictionary(span.candidates)

    if _is_quoted_work_title(text, span.start, span.end):
        reasons.append(REASON_WORK_TITLE)
    if _looks_like_product_name(surface):
        reasons.append(REASON_PRODUCT_NAME)
    if _has_prefixed_suffix(surface, _ORGANIZATION_SUFFIXES):
        reasons.append(REASON_ORGANIZATION_NAME)
    if proper_like and _has_prefixed_suffix(surface, _PLACE_SUFFIXES):
        reasons.append(REASON_PLACE_NAME)
    if proper_like and _has_person_context_suffix(text, span.end):
        reasons.append(REASON_PERSON_NAME)
    if proper_like and _has_next_token_person_suffix(span, tokens):
        reasons.append(REASON_PERSON_NAME)

    return reasons


def _promote_named_entity_reasons(reasons: list[str]) -> None:
    if any(reason in _NAMED_ENTITY_SUBTYPE_REASONS for reason in reasons):
        reasons.append(REASON_PROPER_NOUN)


def _has_prefixed_suffix(surface: str, suffixes: tuple[str, ...]) -> bool:
    for suffix in suffixes:
        if surface.endswith(suffix) and len(surface) > len(suffix):
            return True
    return False


def _has_person_context_suffix(text: str, end: int) -> bool:
    tail = text[end : min(len(text), end + 8)].lstrip()
    return any(tail.startswith(suffix) for suffix in _PERSON_CONTEXT_SUFFIXES)


def _has_next_token_person_suffix(span: RubySpan, tokens: list[RubyToken]) -> bool:
    if not span.token_indices:
        return False
    next_index = max(span.token_indices) + 1
    if next_index >= len(tokens):
        return False
    return tokens[next_index].surface in _PERSON_CONTEXT_SUFFIXES


def _is_quoted_work_title(text: str, start: int, end: int) -> bool:
    if start <= 0 or end >= len(text):
        return False
    left = text[start - 1]
    right = text[end]
    if left not in _WORK_TITLE_LEFT_QUOTES:
        return False
    left_index = _WORK_TITLE_LEFT_QUOTES.index(left)
    return right == _WORK_TITLE_RIGHT_QUOTES[left_index]


def _looks_like_product_name(surface: str) -> bool:
    if not contains_alpha(surface):
        return False
    return bool(_PRODUCT_CODE_PATTERN.search(surface))


def _uses_user_dictionary(candidates: list[ReadingCandidate]) -> bool:
    for candidate in candidates:
        if _is_user_dictionary_candidate(candidate):
            return True
    return False


def _is_user_dictionary_candidate(candidate: ReadingCandidate) -> bool:
    if candidate.source.startswith("user_dict"):
        return True
    return "user_dictionary" in candidate.metadata


def _collect_user_dictionary_signals(
    candidates: list[ReadingCandidate],
    reasons: list[str],
    overrides: list[float],
) -> None:
    for candidate in candidates:
        payload = candidate.metadata.get("user_dictionary")
        if not isinstance(payload, dict):
            continue
        reasons.append(REASON_USER_DICTIONARY)
        _collect_manual_reasons(payload, reasons)
        score = payload.get("difficulty_score")
        if score is not None:
            reasons.append(REASON_MANUAL_DIFFICULTY_OVERRIDE)
            overrides.append(float(score))
        if payload.get("always_ruby") is True:
            reasons.append(REASON_ALWAYS_RUBY)
            overrides.append(1.0)


def _collect_manual_reasons(payload: dict[str, Any], reasons: list[str]) -> None:
    for reason in payload.get("difficulty_reasons", ()) or ():
        reasons.append(str(reason))
    entity_type = payload.get("named_entity_type")
    if entity_type:
        reason = _NAMED_ENTITY_REASON_ALIASES.get(str(entity_type))
        if reason:
            reasons.append(reason)
    tags = tuple(str(tag) for tag in payload.get("tags", ()) or ())
    for tag in tags:
        reason = _NAMED_ENTITY_REASON_ALIASES.get(tag)
        if reason:
            reasons.append(reason)
        if tag in _DOMAIN_TAGS:
            reasons.append(REASON_DOMAIN_TERM)
            reasons.append(_domain_tag_to_reason(tag))


def _is_mixed_script(text: str) -> bool:
    script_count = sum(
        [
            contains_kanji(text),
            contains_number(text),
            contains_alpha(text),
            _contains_kana(text),
        ]
    )
    return script_count >= 2


def _contains_kana(text: str) -> bool:
    return any("ぁ" <= char <= "ゖ" or "ァ" <= char <= "ヺ" for char in text)


def _kanji_count(text: str) -> int:
    return sum(1 for char in text if "一" <= char <= "龯" or char in "々〆ヵヶ")


def _normalize_reasons(reasons: list[str]) -> tuple[str, ...]:
    reason_set = set(reasons)
    ordered = [reason for reason in REASON_ORDER if reason in reason_set]
    extras = sorted(reason for reason in reason_set if reason not in REASON_ORDER)
    return tuple(ordered + extras)


def _score_from_reasons(
    reasons: tuple[str, ...],
    overrides: list[float] | None = None,
) -> float:
    """Compose a difficulty score from reason families.

    Correlated reasons are first aggregated within each family, then
    independent family scores are combined with Noisy-OR. Manual overrides
    are applied as lower bounds, and ``always_ruby`` forces ``1.0``.
    """
    if REASON_ALWAYS_RUBY in reasons:
        return 1.0

    score = _score_from_reason_families(reasons)
    if overrides:
        score = max(score, *overrides)
    return round(min(max(score, 0.0), 1.0), 6)


def _score_from_reason_families(reasons: tuple[str, ...]) -> float:
    family_scores: list[float] = []
    reason_set = set(reasons)

    for family_name, family_reasons in REASON_FAMILIES.items():
        if family_name == "manual":
            continue
        matched = reason_set.intersection(family_reasons)
        if not matched:
            continue
        family_scores.append(_score_family(family_name, matched))

    return _noisy_or(family_scores)


def _score_family(family_name: str, matched: set[str]) -> float:
    scores = [REASON_WEIGHTS.get(reason, 0.0) for reason in matched]
    if not scores:
        return 0.0
    aggregation = FAMILY_AGGREGATION.get(family_name, "max")
    if aggregation == "capped_sum":
        return min(sum(scores), FAMILY_SCORE_CAPS.get(family_name, 1.0))
    return max(scores)


def _noisy_or(scores: list[float]) -> float:
    remaining = 1.0
    for score in scores:
        bounded_score = min(max(score, 0.0), 1.0)
        remaining *= 1.0 - bounded_score
    return 1.0 - remaining
