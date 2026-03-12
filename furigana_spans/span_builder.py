"""Span construction from token-level analysis."""

from __future__ import annotations

from furigana_spans.config import AnalyzerConfig
from furigana_spans.schema import RubySpan, RubyToken
from furigana_spans.script import contains_kanji, contains_number


class SpanBuilder:
    """Build external ruby spans from internal tokens."""

    def __init__(self, config: AnalyzerConfig) -> None:
        self._config = config

    def build(self, text: str, tokens: list[RubyToken]) -> list[RubySpan]:
        """Build span results from token list."""
        spans: list[RubySpan] = []
        for index, token in enumerate(tokens):
            if token.metadata.get("merged_into_previous"):
                continue
            compound_span = self._build_compound_span(index, token, tokens)
            if compound_span is not None:
                spans.append(compound_span)
                continue
            if not self._should_emit(token):
                continue
            spans.append(
                RubySpan(
                    surface=token.surface,
                    reading=token.reading or "",
                    start=token.start,
                    end=token.end,
                    token_indices=[index],
                    pos=token.pos,
                    normalized_form=token.normalized_form,
                    source=_select_source(token),
                    candidates=token.candidates,
                    metadata={"span_type": "word"},
                )
            )
        return spans

    def _build_compound_span(
        self,
        index: int,
        token: RubyToken,
        tokens: list[RubyToken],
    ) -> RubySpan | None:
        reading = token.metadata.get("compound_reading")
        surface = token.metadata.get("compound_surface")
        end = token.metadata.get("compound_end")
        count = token.metadata.get("compound_token_count")
        if not isinstance(reading, str) or not isinstance(surface, str):
            return None
        if not isinstance(end, int) or not isinstance(count, int):
            return None
        indices = list(range(index, min(index + count, len(tokens))))
        return RubySpan(
            surface=surface,
            reading=reading,
            start=token.start,
            end=end,
            token_indices=indices,
            pos=token.pos,
            normalized_form=token.normalized_form,
            source="number_rules",
            candidates=[
                candidate
                for candidate in token.candidates
                if candidate.reading == reading
            ]
            or token.candidates,
            metadata={"span_type": "number_counter"},
        )

    def _should_emit(self, token: RubyToken) -> bool:
        if not token.reading:
            return False
        if self._config.include_tokens_without_kanji:
            return True
        return contains_kanji(token.surface) or contains_number(token.surface)


def _select_source(token: RubyToken) -> str:
    """Select the representative source for a token span."""
    for candidate in token.candidates:
        if candidate.is_selected:
            return candidate.source
    return token.candidates[0].source if token.candidates else ""
