from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from .base import CastHeader, Event, Recording


class V3Parser:
    def parse(self, source: Path | TextIO) -> Recording:
        if isinstance(source, (str, Path)):
            with open(source) as f:
                return self._parse_stream(f)
        return self._parse_stream(source)

    def _parse_stream(self, stream: TextIO) -> Recording:
        first_line = stream.readline().strip()
        if not first_line:
            raise ValueError("Empty cast file")

        header_data = json.loads(first_line)
        version = header_data.get("version")
        if version != 3:
            raise ValueError(f"Unsupported version: {version}")

        term = header_data.get("term", {})
        width = term.get("cols")
        height = term.get("rows")
        if width is None or height is None:
            raise ValueError("Missing required header fields: term.cols, term.rows")

        events: list[Event] = []
        absolute_time = 0.0
        for line in stream:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            try:
                delta = float(raw[0])
                event_type = str(raw[1])
                data = str(raw[2])
            except (IndexError, KeyError, TypeError) as e:
                raise ValueError(f"Malformed event line: {line!r}") from e
            absolute_time += delta
            events.append(Event(time=absolute_time, type=event_type, data=data))

        duration = absolute_time if events else 0.0

        header = CastHeader(
            version=header_data["version"],
            width=width,
            height=height,
            duration=duration,
            timestamp=header_data.get("timestamp"),
            title=header_data.get("title"),
            env=header_data.get("env", {}),
        )

        return Recording(header=header, events=events)
