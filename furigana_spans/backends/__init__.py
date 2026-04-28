"""Tokenizer backend implementations."""

from __future__ import annotations

from furigana_spans.backends.base import BaseTokenizerBackend

__all__ = ["BaseTokenizerBackend", "SudachiBackend"]


def __getattr__(name: str):
    """Lazily import optional backend implementations."""
    if name == "SudachiBackend":
        from furigana_spans.backends.sudachi_backend import SudachiBackend

        return SudachiBackend
    raise AttributeError(name)
