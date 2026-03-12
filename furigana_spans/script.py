"""Utilities for script conversion and character class inspection."""

from __future__ import annotations

import re
import unicodedata

_LATIN_TO_KATAKANA = {
    "A": "エー",
    "B": "ビー",
    "C": "シー",
    "D": "ディー",
    "E": "イー",
    "F": "エフ",
    "G": "ジー",
    "H": "エイチ",
    "I": "アイ",
    "J": "ジェー",
    "K": "ケー",
    "L": "エル",
    "M": "エム",
    "N": "エヌ",
    "O": "オー",
    "P": "ピー",
    "Q": "キュー",
    "R": "アール",
    "S": "エス",
    "T": "ティー",
    "U": "ユー",
    "V": "ブイ",
    "W": "ダブリュー",
    "X": "エックス",
    "Y": "ワイ",
    "Z": "ゼット",
}

_KANJI_RE = re.compile(r"[一-龯々〆ヵヶ]")
_KANA_RE = re.compile(r"[ぁ-ゖァ-ヺー]")
_DIGIT_RE = re.compile(r"[0-9０-９〇零一二三四五六七八九十百千万億兆]")
_ALPHA_RE = re.compile(r"[A-Za-zＡ-Ｚａ-ｚ]")


def katakana_to_hiragana(text: str) -> str:
    """Convert Katakana to Hiragana."""
    chars: list[str] = []
    for char in text:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def hiragana_to_katakana(text: str) -> str:
    """Convert Hiragana to Katakana."""
    chars: list[str] = []
    for char in text:
        code = ord(char)
        if 0x3041 <= code <= 0x3096:
            chars.append(chr(code + 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def normalize_reading(text: str, reading_script: str) -> str:
    """Normalize a reading into the requested script."""
    if reading_script == "hiragana":
        return katakana_to_hiragana(text)
    if reading_script == "katakana":
        return hiragana_to_katakana(text)
    raise ValueError(f"Unsupported reading_script: {reading_script}")


def normalize_surface(text: str) -> str:
    """Normalize input surface text for rules and dictionary matching."""
    return unicodedata.normalize("NFKC", text)


def contains_kanji(text: str) -> bool:
    """Return whether the text contains at least one Kanji-like character."""
    return bool(_KANJI_RE.search(text))


def contains_number(text: str) -> bool:
    """Return whether the text contains decimal or Japanese numerals."""
    return bool(_DIGIT_RE.search(text))


def contains_alpha(text: str) -> bool:
    """Return whether the text contains Latin alphabet characters."""
    return bool(_ALPHA_RE.search(text))


def is_kana_only(text: str) -> bool:
    """Return whether the text is composed only of kana-like characters."""
    if not text:
        return False
    return all(bool(_KANA_RE.fullmatch(char)) for char in text)


def latin_to_katakana(text: str) -> str:
    """Spell out Latin letters in Katakana.

    This is intentionally conservative and treats alphabetic text as an
    acronym-like sequence. It is suitable only as an OOV fallback.
    """
    normalized = normalize_surface(text).upper()
    pieces: list[str] = []
    for char in normalized:
        pieces.append(_LATIN_TO_KATAKANA.get(char, char))
    return "".join(pieces)
