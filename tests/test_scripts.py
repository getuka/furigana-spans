"""Tests for script conversion helpers."""

from __future__ import annotations

from furigana_spans.script import katakana_to_hiragana, latin_to_katakana, normalize_reading


def test_katakana_to_hiragana() -> None:
    assert katakana_to_hiragana("ニホンバシ") == "にほんばし"


def test_latin_to_katakana() -> None:
    assert latin_to_katakana("AI") == "エーアイ"


def test_normalize_reading() -> None:
    assert normalize_reading("ニホンバシ", "hiragana") == "にほんばし"
