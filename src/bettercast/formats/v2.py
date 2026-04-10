from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from .base import CastHeader, Event, Recording


class V2Parser:
    def parse(self, source: Path | TextIO) -> Recording:
        if isinstance(source, (str, Path)):
            with open(source) as f:
                return self._parse_stream(f)
        return self._parse_stream(source)

    def _parse_stream(self, stream: TextIO) -> Recording:
        content = stream.read().strip()
        if not content:
            raise ValueError("Empty cast file")

        lines = content.split("\n")

        header_data = json.loads(lines[0])
        version = header_data.get("version")
        if version != 2:
            raise ValueError(f"Unsupported version: {version}")
        if "width" not in header_data or "height" not in header_data:
            raise ValueError("Missing required header fields: width, height")

        events: list[Event] = []
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            events.append(Event(
                time=float(raw[0]),
                type=str(raw[1]),
                data=str(raw[2]),
            ))

        events.sort(key=lambda e: e.time)

        duration = header_data.get("duration")
        if duration is None:
            duration = events[-1].time if events else 0.0

        header = CastHeader(
            version=header_data["version"],
            width=header_data["width"],
            height=header_data["height"],
            duration=duration,
            timestamp=header_data.get("timestamp"),
            title=header_data.get("title"),
            env=header_data.get("env", {}),
        )

        return Recording(header=header, events=events)
