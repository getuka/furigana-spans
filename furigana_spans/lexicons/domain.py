"""Domain-term lexicon provider for ruby difficulty estimation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from furigana_spans.script import normalize_surface


@dataclass(slots=True, frozen=True)
class DomainTermMatch:
    """Domain-term lexicon evidence for a surface form."""

    surface: str
    source_dictionary: str
    tags: tuple[str, ...] = ()
    base_form: str | None = None
    category_code: str | None = None
    headword_flag: str | None = None
    common_word_flag: str | None = None
    score: float | None = None


class DomainLexiconProvider:
    """Lookup normalized domain lexicon TSV files."""

    def __init__(self, entries: list[DomainTermMatch]) -> None:
        self._by_surface: dict[str, list[DomainTermMatch]] = {}
        self._by_base_form: dict[str, list[DomainTermMatch]] = {}
        for entry in entries:
            self._by_surface.setdefault(_key(entry.surface), []).append(entry)
            if entry.base_form:
                self._by_base_form.setdefault(_key(entry.base_form), []).append(entry)

    @classmethod
    def from_paths(cls, paths: tuple[str, ...] | list[str]) -> "DomainLexiconProvider":
        """Load one or more normalized domain lexicon TSV files."""
        entries: list[DomainTermMatch] = []
        for path in paths:
            entries.extend(_load_domain_tsv(Path(path)))
        return cls(entries)

    def lookup(
        self,
        surface: str,
        base_form: str | None = None,
    ) -> list[DomainTermMatch]:
        """Return exact domain-term matches for a surface/base form."""
        results: list[DomainTermMatch] = []
        seen: set[tuple[str, str, tuple[str, ...]]] = set()
        for match in self._by_surface.get(_key(surface), ()): 
            key = (match.surface, match.source_dictionary, match.tags)
            if key not in seen:
                results.append(match)
                seen.add(key)
        if base_form and base_form != surface:
            for match in self._by_base_form.get(_key(base_form), ()): 
                key = (match.surface, match.source_dictionary, match.tags)
                if key not in seen:
                    results.append(match)
                    seen.add(key)
        return results


def _load_domain_tsv(path: Path) -> list[DomainTermMatch]:
    entries: list[DomainTermMatch] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            return entries
        for row in reader:
            surface = _get(row, "surface")
            if not surface:
                continue
            entries.append(
                DomainTermMatch(
                    surface=surface,
                    base_form=_get(row, "base_form") or None,
                    source_dictionary=_get(row, "source_dictionary") or "",
                    category_code=_get(row, "category_code") or None,
                    headword_flag=_get(row, "headword_flag") or None,
                    common_word_flag=_get(row, "common_word_flag") or None,
                    tags=_parse_tags(_get(row, "tags")),
                    score=_parse_float(_get(row, "score")),
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


def _parse_tags(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    raw_tags = value.replace(",", ";").split(";")
    return tuple(tag.strip() for tag in raw_tags if tag.strip())


def _parse_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None
