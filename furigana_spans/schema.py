"""Dataclass schema for structured ruby analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReadingCandidate:
    """A candidate reading for one token or span."""

    reading: str
    score: float | None = None
    source: str = ""
    is_selected: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RubyDifficulty:
    """Ruby annotation necessity / reading-risk score."""

    score: float = 0.0
    reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class RubyToken:
    """A token-level analysis result."""

    surface: str
    start: int
    end: int
    pos: tuple[str, ...]
    base_form: str | None = None
    normalized_form: str | None = None
    reading: str | None = None
    pronunciation: str | None = None
    is_oov: bool = False
    dictionary_id: int | None = None
    candidates: list[ReadingCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    difficulty: RubyDifficulty | None = None


@dataclass(slots=True)
class RubySpan:
    """A span-level ruby prediction returned to callers."""

    surface: str
    reading: str
    start: int
    end: int
    token_indices: list[int] = field(default_factory=list)
    pos: tuple[str, ...] = field(default_factory=tuple)
    normalized_form: str | None = None
    source: str = ""
    candidates: list[ReadingCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    difficulty: RubyDifficulty | None = None


@dataclass(slots=True)
class RubyAnalysis:
    """Structured output for one input sentence."""

    text: str
    normalized_text: str
    tokens: list[RubyToken]
    spans: list[RubySpan]
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)