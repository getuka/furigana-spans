"""External lexicon providers for difficulty estimation."""

from furigana_spans.lexicons.domain import DomainLexiconProvider, DomainTermMatch
from furigana_spans.lexicons.frequency import FrequencyInfo, FrequencyProvider

__all__ = [
    "DomainLexiconProvider",
    "DomainTermMatch",
    "FrequencyInfo",
    "FrequencyProvider",
]
