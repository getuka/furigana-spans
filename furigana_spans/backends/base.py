"""Abstract tokenizer backend definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from furigana_spans.schema import RubyToken


class BaseTokenizerBackend(ABC):
    """Abstract tokenizer backend."""

    @abstractmethod
    def tokenize(self, text: str) -> list[RubyToken]:
        """Tokenize input text and return structured tokens."""

    def lookup_readings(self, surface: str) -> list[str]:
        """Look up candidate readings for a surface string.

        Backends may override this method if the underlying analyzer provides a
        lexicon lookup API.
        """
        return []
