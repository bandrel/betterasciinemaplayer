from __future__ import annotations

import pyte

from .formats.base import Recording


class PlaybackEngine:
    def __init__(self, recording: Recording) -> None:
        self.recording = recording
        self.screen = pyte.Screen(recording.header.width, recording.header.height)
        self._stream = pyte.Stream(self.screen)
        self.position: float = 0.0
        self.speed: float = 1.0
        self.playing: bool = False
        self._event_index: int = 0
        self._search_index: list[tuple[float, str]] = []

    @property
    def duration(self) -> float:
        return self.recording.header.duration

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

    def build_search_index(self) -> None:
        screen = pyte.Screen(self.recording.header.width, self.recording.header.height)
        stream = pyte.Stream(screen)
        self._search_index = []
        prev_text = ""
        for event in self.recording.events:
            if event.type == "o":
                stream.feed(event.data)
                text = "\n".join(screen.display)
                if text != prev_text:
                    self._search_index.append((event.time, text))
                    prev_text = text

    def next_match(self, query: str) -> float | None:
        if not query:
            return None
        query_lower = query.lower()
        for time, text in self._search_index:
            if time > self.position and query_lower in text.lower():
                return time
        return None

    def prev_match(self, query: str) -> float | None:
        if not query:
            return None
        query_lower = query.lower()
        for time, text in reversed(self._search_index):
            if time < self.position and query_lower in text.lower():
                return time
        return None

    def count_matches(self, query: str) -> int:
        if not query:
            return 0
        query_lower = query.lower()
        return sum(1 for _, text in self._search_index if query_lower in text.lower())
