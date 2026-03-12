"""User dictionary loading for candidate injection and override."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from furigana_spans.script import normalize_reading, normalize_surface


@dataclass(slots=True)
class UserDictionaryEntry:
    """One external user dictionary entry."""

    surface: str
    reading: str
    base_form: str | None = None
    pos_prefix: tuple[str, ...] = ()
    source: str = "user_dict"

    def matches(self, surface: str, base_form: str | None, pos: tuple[str, ...]) -> bool:
        """Return whether this entry matches a token."""
        if normalize_surface(surface) != normalize_surface(self.surface):
            return False
        if self.base_form and base_form and self.base_form != base_form:
            return False
        if self.pos_prefix and tuple(pos[: len(self.pos_prefix)]) != self.pos_prefix:
            return False
        return True


class UserDictionary:
    """Load and query JSON / JSONL user dictionaries."""

    def __init__(self, paths: tuple[str, ...], reading_script: str) -> None:
        self._entries: list[UserDictionaryEntry] = []
        self._reading_script = reading_script
        for path in paths:
            self._entries.extend(self._load_file(Path(path)))

    def lookup(
        self,
        surface: str,
        base_form: str | None,
        pos: tuple[str, ...],
    ) -> list[UserDictionaryEntry]:
        """Return matching user dictionary entries."""
        return [
            entry
            for entry in self._entries
            if entry.matches(surface=surface, base_form=base_form, pos=pos)
        ]

    def _load_file(self, path: Path) -> Iterable[UserDictionaryEntry]:
        suffix = path.suffix.lower()
        if suffix == ".jsonl":
            return self._load_jsonl(path)
        if suffix == ".json":
            return self._load_json(path)
        raise ValueError(f"Unsupported user dictionary format: {path}")

    def _load_json(self, path: Path) -> Iterable[UserDictionaryEntry]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"User dictionary JSON must be a list: {path}")
        return [self._parse_entry(item) for item in payload]

    def _load_jsonl(self, path: Path) -> Iterable[UserDictionaryEntry]:
        entries: list[UserDictionaryEntry] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entries.append(self._parse_entry(json.loads(line)))
        return entries

    def _parse_entry(self, item: dict) -> UserDictionaryEntry:
        pos_prefix = tuple(item.get("pos_prefix", []))
        reading = normalize_reading(
            normalize_surface(item["reading"]),
            self._reading_script,
        )
        return UserDictionaryEntry(
            surface=normalize_surface(item["surface"]),
            reading=reading,
            base_form=item.get("base_form"),
            pos_prefix=pos_prefix,
            source=item.get("source", "user_dict"),
        )
