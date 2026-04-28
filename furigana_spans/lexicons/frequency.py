"""Frequency lexicon provider for ruby difficulty estimation."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from furigana_spans.script import normalize_surface


@dataclass(slots=True, frozen=True)
class FrequencyInfo:
    """Frequency evidence for a lexical item.

    Rank is 1-based: lower rank means more frequent, larger rank means less
    frequent. ``unit`` is intentionally open-ended; BCCWJ users will typically
    use ``luw`` for long-unit words and ``suw`` for short-unit words.
    """

    surface: str
    unit: str
    frequency: float | None = None
    rank: int | None = None
    log_frequency: float | None = None
    source: str = ""
    base_form: str | None = None
    reading: str | None = None
    pos: str | None = None
    register: str | None = None


class FrequencyProvider:
    """Lookup normalized frequency TSV files."""

    def __init__(
        self,
        entries: list[FrequencyInfo],
        unit_priority: tuple[str, ...] = ("luw", "suw"),
    ) -> None:
        self._unit_priority = unit_priority
        self._by_surface: dict[str, list[FrequencyInfo]] = {}
        self._by_base_form: dict[str, list[FrequencyInfo]] = {}
        for entry in entries:
            surface_key = _key(entry.surface)
            self._by_surface.setdefault(surface_key, []).append(entry)
            if entry.base_form:
                base_key = _key(entry.base_form)
                self._by_base_form.setdefault(base_key, []).append(entry)

    @classmethod
    def from_paths(
        cls,
        paths: tuple[str, ...] | list[str],
        unit_priority: tuple[str, ...] = ("luw", "suw"),
    ) -> "FrequencyProvider":
        """Load one or more normalized frequency TSV files."""
        entries: list[FrequencyInfo] = []
        for path in paths:
            entries.extend(_load_frequency_tsv(Path(path)))
        return cls(entries, unit_priority=unit_priority)

    def lookup(
        self,
        surface: str,
        base_form: str | None = None,
        unit: str | None = None,
    ) -> FrequencyInfo | None:
        """Return the best matching frequency entry for a surface/base form."""
        candidates: list[FrequencyInfo] = []
        candidates.extend(self._by_surface.get(_key(surface), ()))
        if base_form and base_form != surface:
            candidates.extend(self._by_base_form.get(_key(base_form), ()))
        if unit:
            candidates = [candidate for candidate in candidates if candidate.unit == unit]
        if not candidates:
            return None
        return min(candidates, key=self._sort_key)

    def _sort_key(self, info: FrequencyInfo) -> tuple[int, int, float, str]:
        try:
            unit_rank = self._unit_priority.index(info.unit)
        except ValueError:
            unit_rank = len(self._unit_priority)
        rank = info.rank if info.rank is not None else 10**12
        frequency_sort = -info.frequency if info.frequency is not None else 0.0
        return (unit_rank, rank, frequency_sort, info.surface)


def _load_frequency_tsv(path: Path) -> list[FrequencyInfo]:
    entries: list[FrequencyInfo] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            return entries
        for row in reader:
            surface = _get(row, "surface")
            if not surface:
                continue
            frequency = _parse_float(_get(row, "frequency"))
            log_frequency = _parse_float(_get(row, "log_frequency"))
            if log_frequency is None and frequency is not None:
                log_frequency = math.log1p(max(frequency, 0.0))
            entries.append(
                FrequencyInfo(
                    surface=surface,
                    base_form=_get(row, "base_form") or None,
                    reading=_get(row, "reading") or None,
                    pos=_get(row, "pos") or None,
                    unit=_get(row, "unit") or "",
                    frequency=frequency,
                    rank=_parse_int(_get(row, "rank")),
                    log_frequency=log_frequency,
                    source=_get(row, "source") or "",
                    register=_get(row, "register") or None,
                )
            )
    return entries


def _key(text: str) -> str:
    return normalize_surface(text.strip())


def _get(row: dict[str, str | None], name: str) -> str:
    value = row.get(name)
    if value is None:
        return ""
    return value.strip()


def _parse_int(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(float(value.replace(",", "")))
    except ValueError:
        return None


def _parse_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None
