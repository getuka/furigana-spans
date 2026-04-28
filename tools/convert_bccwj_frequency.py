#!/usr/bin/env python3
"""Normalize a generic BCCWJ-like frequency table into library TSV.

The original BCCWJ frequency list has multiple distributions and column names.
This script intentionally accepts explicit column names instead of hard-coding a
single upstream format.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable, Iterator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a frequency table into furigana-spans TSV."
    )
    parser.add_argument("--input", required=True, help="Input TSV/CSV path.")
    parser.add_argument("--output", required=True, help="Output TSV path.")
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--delimiter", default="\t")
    parser.add_argument("--surface-col", required=True)
    parser.add_argument("--freq-col", required=True)
    parser.add_argument("--unit", default="luw")
    parser.add_argument("--source", default="BCCWJ")
    parser.add_argument("--base-form-col", default=None)
    parser.add_argument("--reading-col", default=None)
    parser.add_argument("--pos-col", default=None)
    parser.add_argument("--rank-col", default=None)
    parser.add_argument("--register-col", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = _normalize_rows(args)
    if args.rank_col:
        _write_rows(Path(args.output), rows)
        return

    normalized = list(rows)
    if any(row["rank"] is None for row in normalized):
        sorted_rows = sorted(
            normalized,
            key=lambda row: (-float(row["frequency"]), str(row["surface"])),
        )
        for index, row in enumerate(sorted_rows, start=1):
            if row["rank"] is None:
                row["rank"] = index

    _write_rows(Path(args.output), normalized)


def _normalize_rows(args: argparse.Namespace) -> Iterator[dict[str, object]]:
    for row in _iter_rows(Path(args.input), args.encoding, args.delimiter):
        surface = _get(row, args.surface_col)
        frequency = _parse_float(_get(row, args.freq_col))
        if not surface or frequency is None:
            continue
        yield {
            "surface": surface,
            "base_form": _get(row, args.base_form_col),
            "reading": _get(row, args.reading_col),
            "pos": _get(row, args.pos_col),
            "unit": args.unit,
            "frequency": frequency,
            "rank": _parse_int(_get(row, args.rank_col)) if args.rank_col else None,
            "log_frequency": math.log1p(max(frequency, 0.0)),
            "source": args.source,
            "register": _get(row, args.register_col),
        }


def _iter_rows(path: Path, encoding: str, delimiter: str) -> Iterator[dict[str, str]]:
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            yield dict(row)


def _write_rows(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "surface",
        "base_form",
        "reading",
        "pos",
        "unit",
        "frequency",
        "rank",
        "log_frequency",
        "source",
        "register",
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


def _parse_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _parse_int(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(float(value.replace(",", "")))
    except ValueError:
        return None


if __name__ == "__main__":
    main()
