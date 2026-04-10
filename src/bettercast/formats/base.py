from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, TextIO


@dataclass(frozen=True)
class CastHeader:
    version: int
    width: int
    height: int
    duration: float
    timestamp: int | None = None
    title: str | None = None
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Event:
    time: float
    type: str
    data: str


@dataclass
class Recording:
    header: CastHeader
    events: list[Event]


class CastFormat(Protocol):
    def parse(self, source: Path | TextIO) -> Recording: ...
