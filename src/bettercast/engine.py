from __future__ import annotations

import pyte

from .formats.base import Recording
from .terminal import AltScreen


class PlaybackEngine:
    def __init__(self, recording: Recording) -> None:
        self.recording = recording
        self.screen = AltScreen(recording.header.width, recording.header.height)
        self._stream = pyte.Stream(self.screen)
        self.position: float = 0.0
        self.speed: float = 1.0
        self.playing: bool = False
        self.looping: bool = False
        self._event_index: int = 0
        self._search_index: list[tuple[float, str, str]] = []
        self.idle_threshold: float = float("inf")
        self.bookmarks: list[tuple[float, str]] = []
        self._bookmark_counter: int = 0

    @property
    def duration(self) -> float:
        return self.recording.header.duration

    def resize(self, width: int, height: int) -> None:
        self.screen.resize(height, width)
        self._stream = pyte.Stream(self.screen)
        # Re-seek to rebuild screen state at new dimensions
        pos = self.position
        self._event_index = 0
        self.screen.reset()
        self.screen.resize(height, width)
        self._stream = pyte.Stream(self.screen)
        for i, event in enumerate(self.recording.events):
            if event.time > pos:
                self._event_index = i
                break
            if event.type == "o":
                self._stream.feed(event.data)
        else:
            self._event_index = len(self.recording.events)
        self.position = pos

    def seek(self, time: float) -> None:
        time = max(0.0, min(time, self.duration))
        self.screen.reset()
        self._stream = pyte.Stream(self.screen)
        self._event_index = 0
        for i, event in enumerate(self.recording.events):
            if event.time > time:
                self._event_index = i
                break
            if event.type == "o":
                self._stream.feed(event.data)
        else:
            self._event_index = len(self.recording.events)
        self.position = time

    def advance(self, real_dt: float) -> bool:
        if not self.playing:
            return False
        virtual_dt = real_dt * self.speed
        # Idle compression: if next event is beyond threshold, skip ahead
        if self._event_index < len(self.recording.events):
            next_event = self.recording.events[self._event_index]
            gap = next_event.time - self.position
            if gap > self.idle_threshold:
                self.position = next_event.time - 0.5
        target = min(self.position + virtual_dt, self.duration)
        changed = False
        while self._event_index < len(self.recording.events):
            event = self.recording.events[self._event_index]
            if event.time > target:
                break
            if event.type == "o":
                self._stream.feed(event.data)
                changed = True
            self._event_index += 1
        self.position = target
        if target >= self.duration:
            if self.looping:
                self.seek(0.0)
                self.playing = True
            else:
                self.playing = False
        return changed

    def play(self) -> None:
        self.playing = True

    def pause(self) -> None:
        self.playing = False

    def toggle(self) -> None:
        self.playing = not self.playing

    def set_speed(self, speed: float) -> None:
        self.speed = max(0.5, min(speed, 8.0))

    def step_forward(self) -> None:
        self.playing = False
        for i in range(self._event_index, len(self.recording.events)):
            event = self.recording.events[i]
            if event.type == "o":
                self._stream.feed(event.data)
                self._event_index = i + 1
                self.position = event.time
                return

    def step_backward(self) -> None:
        self.playing = False
        for i in range(len(self.recording.events) - 1, -1, -1):
            event = self.recording.events[i]
            if event.type == "o" and event.time < self.position:
                self.seek(event.time)
                return

    def build_search_index(self) -> None:
        screen = AltScreen(self.recording.header.width, self.recording.header.height)
        stream = pyte.Stream(screen)
        index: list[tuple[float, str, str]] = []
        prev_text = ""
        last_snapshot_time = -1.0
        min_interval = 0.3  # snapshot at most every 300ms
        cols = screen.columns
        rows = screen.lines

        events = self.recording.events
        for i, event in enumerate(events):
            if event.type != "o":
                continue
            stream.feed(event.data)

            is_last = i + 1 >= len(events)
            next_far = not is_last and events[i + 1].time - event.time > min_interval
            enough_time = event.time - last_snapshot_time >= min_interval

            if not (enough_time or next_far or is_last):
                continue

            # Fast buffer read — bypass screen.display property
            lines = []
            buf = screen.buffer
            for row in range(rows):
                row_buf = buf[row]
                line_chars = []
                for col in range(cols):
                    data = row_buf[col].data
                    line_chars.append(data if data else " ")
                lines.append("".join(line_chars))
            text = "\n".join(lines)

            if text != prev_text:
                index.append((event.time, text, text.lower()))
                prev_text = text
            last_snapshot_time = event.time

        self._search_index = index

    def next_match(self, query: str) -> float | None:
        if not query:
            return None
        query_lower = query.lower()
        for time, text, text_lower in self._search_index:
            if time > self.position and query_lower in text_lower:
                return time
        return None

    def prev_match(self, query: str) -> float | None:
        if not query:
            return None
        query_lower = query.lower()
        for time, text, text_lower in reversed(self._search_index):
            if time < self.position and query_lower in text_lower:
                return time
        return None

    def count_matches(self, query: str) -> int:
        if not query:
            return 0
        query_lower = query.lower()
        return sum(1 for _, _, text_lower in self._search_index if query_lower in text_lower)

    def add_bookmark(self, time: float, label: str = "") -> None:
        self._bookmark_counter += 1
        if not label:
            label = f"Bookmark {self._bookmark_counter}"
        self.bookmarks.append((time, label))
        self.bookmarks.sort(key=lambda b: b[0])

    def remove_bookmark(self, index: int) -> None:
        if 0 <= index < len(self.bookmarks):
            self.bookmarks.pop(index)

    def next_bookmark(self, from_time: float) -> float | None:
        for time, _ in self.bookmarks:
            if time > from_time:
                return time
        return None

    def prev_bookmark(self, from_time: float) -> float | None:
        for time, _ in reversed(self.bookmarks):
            if time < from_time:
                return time
        return None
