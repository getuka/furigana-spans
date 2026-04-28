#!/usr/bin/env python3
"""Normalize an NBDC/JST-style term CSV into library domain TSV.

The upstream NBDC MeCab CSV variants may differ in headers and column order.
This converter therefore uses configurable column names. Prepare a headered CSV
or TSV, then map the relevant columns with command-line flags.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


_TAG_ALIASES = {
    "mesh": "medical_term",
    "j-global mesh": "medical_term",
    "nikkaji": "chemical_term",
    "日化辞": "chemical_term",
    "thesaurus": "technical_term;science_term",
    "jst": "technical_term;science_term",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a domain-term table into furigana-spans TSV."
    )
    parser.add_argument("--input", required=True, help="Input CSV/TSV path.")
    parser.add_argument("--output", required=True, help="Output TSV path.")
    parser.add_argument("--encoding", default="shift_jis")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--surface-col", required=True)
    parser.add_argument("--base-form-col", default=None)
    parser.add_argument("--source-dictionary-col", default=None)
    parser.add_argument("--category-code-col", default=None)
    parser.add_argument("--headword-flag-col", default=None)
    parser.add_argument("--common-word-flag-col", default=None)
    parser.add_argument("--tags-col", default=None)
    parser.add_argument("--score-col", default=None)
    parser.add_argument(
        "--default-source-dictionary",
        default="NBDC",
        help="Source label when no source column is available.",
    )
    parser.add_argument(
        "--default-tags",
        default="technical_term",
        help="Semicolon-separated tags when no tags can be inferred.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = _read_rows(Path(args.input), args.encoding, args.delimiter)
    normalized = []
    for row in rows:
        surface = _get(row, args.surface_col)
        if not surface:
            continue
        source = _get(row, args.source_dictionary_col) or args.default_source_dictionary
        tags = _get(row, args.tags_col)
        if not tags:
            tags = _infer_tags(source) or args.default_tags
        normalized.append(
            {
                "surface": surface,
                "base_form": _get(row, args.base_form_col),
                "source_dictionary": source,
                "category_code": _get(row, args.category_code_col),
                "headword_flag": _get(row, args.headword_flag_col),
                "common_word_flag": _get(row, args.common_word_flag_col),
                "tags": tags,
                "score": _get(row, args.score_col),
            }
        )
    _write_rows(Path(args.output), normalized)


def _read_rows(path: Path, encoding: str, delimiter: str) -> list[dict[str, str]]:
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [dict(row) for row in reader]


def _write_rows(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "surface",
        "base_form",
        "source_dictionary",
        "category_code",
        "headword_flag",
        "common_word_flag",
        "tags",
        "score",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _get(row: dict[str, str], column: str | None) -> str:
    if not column:
        return ""
    value = row.get(column)
    if value is None:
        return ""
    return value.strip()


def _infer_tags(source_dictionary: str) -> str:
    normalized = source_dictionary.strip().lower()
    for key, tags in _TAG_ALIASES.items():
        if key in normalized:
            return tags
    return ""


if __name__ == "__main__":
    main()
