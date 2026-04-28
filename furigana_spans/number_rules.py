"""Number and counter reading rules."""

from __future__ import annotations

import re
from dataclasses import replace

from furigana_spans.config import AnalyzerConfig
from furigana_spans.japanese_numbers import (
    is_irregular_counter_reading,
    is_number_like,
    parse_number,
    to_counter_reading,
)
from furigana_spans.schema import ReadingCandidate, RubyToken
from furigana_spans.script import contains_number, normalize_reading

_COMPOUND_COUNTER_RE = re.compile(
    r"^(?P<number>[0-9０-９〇零一二三四五六七八九十百千万億兆]+)(?P<counter>人|日|本|匹|杯|分|回|階|冊|枚|個|年|歳)$"
)
_SUPPORTED_COUNTERS = {"人", "日", "本", "匹", "杯", "分", "回", "階", "冊", "枚", "個", "年", "歳"}


class NumberRuleEngine:
    """Apply reading overrides for numeric-counter expressions."""

    def __init__(self, config: AnalyzerConfig) -> None:
        self._config = config

    def apply(self, text: str, tokens: list[RubyToken]) -> list[RubyToken]:
        """Apply number reading rules to token list."""
        updated = list(tokens)
        index = 0
        while index < len(updated):
            token = updated[index]
            compound = self._match_single_token_compound(token)
            if compound is not None:
                updated[index] = compound
                index += 1
                continue
            if index + 1 < len(updated):
                merged = self._match_two_token_compound(updated[index], updated[index + 1])
                if merged is not None:
                    first, second = merged
                    updated[index] = first
                    updated[index + 1] = second
                    index += 2
                    continue
            index += 1
        return updated

    def _match_single_token_compound(self, token: RubyToken) -> RubyToken | None:
        match = _COMPOUND_COUNTER_RE.fullmatch(token.surface)
        if match is None:
            return None
        number_text = match.group("number")
        counter = match.group("counter")
        reading = self._build_counter_reading(number_text, counter)
        if reading is None:
            return None
        return _apply_compound_to_single_token(token, reading)

    def _match_two_token_compound(
        self,
        first: RubyToken,
        second: RubyToken,
    ) -> tuple[RubyToken, RubyToken] | None:
        if not is_number_like(first.surface):
            return None
        if second.surface not in _SUPPORTED_COUNTERS:
            return None
        reading = self._build_counter_reading(first.surface, second.surface)
        if reading is None:
            return None
        merged_surface = first.surface + second.surface
        first_token = replace(
            first,
            metadata={
                **first.metadata,
                "compound_surface": merged_surface,
                "compound_reading": reading,
                "compound_end": second.end,
                "compound_token_count": 2,
                "compound_counter": second.surface,
                "irregular_counter_reading": _is_irregular_counter(
                    first.surface,
                    second.surface,
                ),
            },
        )
        second_token = replace(
            second,
            metadata={
                **second.metadata,
                "merged_into_previous": True,
                "merged_reason": "number_counter",
            },
        )
        return first_token, second_token

    def _build_counter_reading(self, number_text: str, counter: str) -> str | None:
        number = parse_number(number_text)
        if number is None:
            return None
        reading = to_counter_reading(number, counter)
        if reading is None:
            return None
        return normalize_reading(reading, self._config.reading_script)

def _is_irregular_counter(number_text: str, counter: str) -> bool:
    number = parse_number(number_text)
    if number is None:
        return False
    return is_irregular_counter_reading(number, counter)


def _apply_compound_to_single_token(token: RubyToken, reading: str) -> RubyToken:
    match = _COMPOUND_COUNTER_RE.fullmatch(token.surface)
    irregular = False
    if match is not None:
        irregular = _is_irregular_counter(match.group("number"), match.group("counter"))
    candidates = [
        ReadingCandidate(
            reading=reading,
            score=0.99,
            source="number_rules",
            is_selected=True,
        )
    ]
    return replace(
        token,
        reading=reading,
        pronunciation=reading,
        candidates=candidates,
        metadata={
            **token.metadata,
            "compound_surface": token.surface,
            "compound_reading": reading,
            "compound_end": token.end,
            "compound_token_count": 1,
            "irregular_counter_reading": irregular,
        },
    )
