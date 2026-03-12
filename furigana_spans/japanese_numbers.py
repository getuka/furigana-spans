"""Japanese numeral parsing and reading generation."""

from __future__ import annotations

import re
import unicodedata

from furigana_spans.script import katakana_to_hiragana

_DIGIT_TABLE = str.maketrans("０１２３４５６７８９", "0123456789")
_SIMPLE_KANJI = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_SMALL_UNITS = {"十": 10, "百": 100, "千": 1000}
_BIG_UNITS = {"万": 10_000, "億": 100_000_000, "兆": 1_000_000_000_000}
_NUMBER_RE = re.compile(r"^[0-9０-９〇零一二三四五六七八九十百千万億兆]+$")


def is_number_like(text: str) -> bool:
    """Return whether the string looks like a Japanese numeral."""
    return bool(_NUMBER_RE.fullmatch(text))


def parse_number(text: str) -> int | None:
    """Parse ASCII / full-width / simple Kanji numerals."""
    normalized = unicodedata.normalize("NFKC", text).translate(_DIGIT_TABLE)
    if normalized.isdigit():
        return int(normalized)
    if not is_number_like(text):
        return None
    return _parse_kanji_number(normalized)


def to_sino_kana(number: int) -> str:
    """Convert an integer into a Sino-Japanese Hiragana reading."""
    if number == 0:
        return "ぜろ"
    if number < 0:
        raise ValueError("Negative numbers are not supported")
    parts: list[str] = []
    for unit_value, unit_reading in (
        (1_000_000_000_000, "ちょう"),
        (100_000_000, "おく"),
        (10_000, "まん"),
    ):
        if number >= unit_value:
            high = number // unit_value
            parts.append(_under_10000_to_kana(high))
            parts.append(unit_reading)
            number %= unit_value
    if number:
        parts.append(_under_10000_to_kana(number))
    return "".join(parts)


def _parse_kanji_number(text: str) -> int:
    total = 0
    chunk = 0
    digit = 0
    arabic_digits = ""
    for char in text:
        if char.isdigit():
            arabic_digits += char
            continue
        if char in _SIMPLE_KANJI:
            digit = _SIMPLE_KANJI[char]
            continue
        if char in _SMALL_UNITS:
            unit = _SMALL_UNITS[char]
            value = int(arabic_digits) if arabic_digits else digit
            chunk += (value or 1) * unit
            digit = 0
            arabic_digits = ""
            continue
        if char in _BIG_UNITS:
            unit = _BIG_UNITS[char]
            value = int(arabic_digits) if arabic_digits else digit
            chunk += value
            total += (chunk or 1) * unit
            chunk = 0
            digit = 0
            arabic_digits = ""
            continue
        raise ValueError(f"Unsupported numeral character: {char}")
    value = int(arabic_digits) if arabic_digits else digit
    return total + chunk + value


def _under_10000_to_kana(number: int) -> str:
    parts: list[str] = []
    thousands = number // 1000
    hundreds = (number % 1000) // 100
    tens = (number % 100) // 10
    ones = number % 10

    if thousands:
        parts.append({1: "せん", 3: "さんぜん", 8: "はっせん"}.get(thousands, _digit_kana(thousands) + "せん"))
    if hundreds:
        parts.append({1: "ひゃく", 3: "さんびゃく", 6: "ろっぴゃく", 8: "はっぴゃく"}.get(hundreds, _digit_kana(hundreds) + "ひゃく"))
    if tens:
        parts.append("じゅう" if tens == 1 else _digit_kana(tens) + "じゅう")
    if ones:
        parts.append(_digit_kana(ones))
    return "".join(parts)


def _digit_kana(number: int) -> str:
    return {
        0: "ぜろ",
        1: "いち",
        2: "に",
        3: "さん",
        4: "よん",
        5: "ご",
        6: "ろく",
        7: "なな",
        8: "はち",
        9: "きゅう",
    }[number]


def to_counter_reading(number: int, counter: str) -> str | None:
    """Return a counter reading for supported counters."""
    special = _SPECIAL_COUNTERS.get(counter)
    if special is not None:
        if number in special:
            return special[number]
        base = to_sino_kana(number)
        suffix = _GENERIC_COUNTER_SUFFIX.get(counter)
        if suffix is not None:
            return base + suffix
    return None


_SPECIAL_COUNTERS = {
    "人": {1: "ひとり", 2: "ふたり"},
    "日": {
        1: "ついたち",
        2: "ふつか",
        3: "みっか",
        4: "よっか",
        5: "いつか",
        6: "むいか",
        7: "なのか",
        8: "ようか",
        9: "ここのか",
        10: "とおか",
        14: "じゅうよっか",
        20: "はつか",
        24: "にじゅうよっか",
    },
    "本": {1: "いっぽん", 3: "さんぼん", 6: "ろっぽん", 8: "はっぽん", 10: "じゅっぽん"},
    "匹": {1: "いっぴき", 3: "さんびき", 6: "ろっぴき", 8: "はっぴき", 10: "じゅっぴき"},
    "杯": {1: "いっぱい", 3: "さんばい", 6: "ろっぱい", 8: "はっぱい", 10: "じゅっぱい"},
    "分": {1: "いっぷん", 3: "さんぷん", 4: "よんぷん", 6: "ろっぷん", 8: "はっぷん", 10: "じゅっぷん"},
    "回": {1: "いっかい", 6: "ろっかい", 8: "はっかい", 10: "じゅっかい"},
    "階": {1: "いっかい", 3: "さんがい", 6: "ろっかい", 8: "はっかい", 10: "じゅっかい"},
    "冊": {1: "いっさつ", 8: "はっさつ", 10: "じゅっさつ"},
    "個": {1: "いっこ", 6: "ろっこ", 8: "はっこ", 10: "じゅっこ"},
    "歳": {1: "いっさい", 8: "はっさい", 10: "じゅっさい", 20: "はたち"},
}

_GENERIC_COUNTER_SUFFIX = {
    "人": "にん",
    "日": "にち",
    "本": "ほん",
    "匹": "ひき",
    "杯": "はい",
    "分": "ふん",
    "回": "かい",
    "階": "かい",
    "冊": "さつ",
    "枚": "まい",
    "個": "こ",
    "年": "ねん",
    "歳": "さい",
}
