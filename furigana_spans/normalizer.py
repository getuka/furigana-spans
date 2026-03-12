"""Input normalization helpers."""

from __future__ import annotations

import unicodedata


class TextNormalizer:
    """Normalize input text while preserving the original output contract."""

    def normalize(self, text: str) -> str:
        """Return a lightly normalized form of the input text."""
        return unicodedata.normalize("NFKC", text)
