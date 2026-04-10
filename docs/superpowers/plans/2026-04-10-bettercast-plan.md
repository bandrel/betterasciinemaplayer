# Bettercast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a keyboard-driven CLI asciinema player with seeking, speed control, text search, and a Textual-based TUI.

**Architecture:** Three layers — Cast Parser (reads .cast files into data types), Playback Engine (manages state + pyte virtual terminal), TUI Shell (Textual app with widgets for display, progress, help, search). Data flows Parser → Engine → TUI; commands flow TUI → Engine.

**Tech Stack:** Python 3.12+, uv (packaging), Textual (TUI), pyte (virtual terminal), click (CLI), pytest + pytest-asyncio (testing)

**Spec:** `docs/superpowers/specs/2026-04-10-bettercast-design.md`

---

## File Structure

```
betterasciinemaplayer/
├── pyproject.toml              # uv project config, CLI entry point
├── .gitignore
├── src/
│   └── bettercast/
│       ├── __init__.py
│       ├── __main__.py         # python -m bettercast support
│       ├── cli.py              # CLI argument parsing (click)
│       ├── formats/
│       │   ├── __init__.py
│       │   ├── base.py         # CastFormat protocol, Recording, Event, CastHeader
│       │   └── v2.py           # asciicast v2 parser
│       ├── engine.py           # PlaybackEngine
│       └── ui/
│           ├── __init__.py
│           ├── app.py          # BettercastApp (Textual App)
│           ├── terminal.py     # TerminalDisplay widget
│           ├── progress.py     # PlaybackProgressBar widget
│           ├── help.py         # HelpOverlay widget
│           └── search.py       # SearchOverlay widget
├── tests/
│   ├── conftest.py             # shared fixtures
│   ├── test_parser.py
│   ├── test_engine.py
│   ├── test_ui.py
│   └── fixtures/
│       └── sample.cast
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/bettercast/__init__.py`
- Create: `src/bettercast/formats/__init__.py`
- Create: `src/bettercast/ui/__init__.py`
- Create: `tests/__init__.py` (empty, not needed but conventional)

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "bettercast"
version = "0.1.0"
description = "A better asciinema player for the terminal"
requires-python = ">=3.12"
dependencies = [
    "textual>=3.0",
    "pyte>=0.8",
    "click>=8.0",
]

[project.scripts]
bettercast = "bettercast.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/bettercast"]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
.env
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 3: Create empty package files**

Create these files, all empty:
- `src/bettercast/__init__.py`
- `src/bettercast/formats/__init__.py`
- `src/bettercast/ui/__init__.py`

- [ ] **Step 4: Install dependencies**

Run: `uv sync`

Expected: Creates `.venv/`, installs all dependencies. Output includes `textual`, `pyte`, `click`, `pytest`.

- [ ] **Step 5: Verify setup**

Run: `uv run python -c "import textual; import pyte; import click; print('OK')"`

Expected: Prints `OK`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore src/ uv.lock
git commit -m "feat: project scaffolding with uv, textual, pyte, click"
```

---

### Task 2: Data Types + Test Fixture

**Files:**
- Create: `src/bettercast/formats/base.py`
- Create: `tests/fixtures/sample.cast`
- Create: `tests/test_parser.py` (initial data type tests only)

- [ ] **Step 1: Create data types in base.py**

```python
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
```

- [ ] **Step 2: Create sample.cast fixture**

Create `tests/fixtures/sample.cast`:

```
{"version": 2, "width": 80, "height": 24, "timestamp": 1234567890}
[0.5, "o", "$ "]
[1.0, "o", "echo hello\r\n"]
[1.5, "o", "hello\r\n"]
[2.0, "o", "$ "]
[3.0, "o", "python --version\r\n"]
[3.5, "o", "Python 3.12.0\r\n"]
[4.0, "o", "$ "]
```

This recording is 4 seconds, 7 events, exercises basic output with newlines and searchable text ("hello", "python", "Python 3.12.0").

- [ ] **Step 3: Write test for data type construction**

```python
from bettercast.formats.base import CastHeader, Event, Recording


def test_cast_header_construction():
    header = CastHeader(version=2, width=80, height=24, duration=4.0)
    assert header.version == 2
    assert header.width == 80
    assert header.height == 24
    assert header.duration == 4.0
    assert header.timestamp is None
    assert header.title is None
    assert header.env == {}


def test_event_construction():
    event = Event(time=1.5, type="o", data="hello\r\n")
    assert event.time == 1.5
    assert event.type == "o"
    assert event.data == "hello\r\n"


def test_recording_construction():
    header = CastHeader(version=2, width=80, height=24, duration=0.0)
    events = [Event(time=0.5, type="o", data="$ ")]
    recording = Recording(header=header, events=events)
    assert recording.header.width == 80
    assert len(recording.events) == 1
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_parser.py -v`

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bettercast/formats/base.py tests/fixtures/sample.cast tests/test_parser.py
git commit -m "feat: add data types (CastHeader, Event, Recording) and test fixture"
```

---

### Task 3: V2 Parser (TDD)

**Files:**
- Create: `src/bettercast/formats/v2.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Write failing parser tests**

Add to `tests/test_parser.py`:

```python
import io
from pathlib import Path

import pytest

from bettercast.formats.base import CastHeader, Event, Recording
from bettercast.formats.v2 import V2Parser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# --- existing tests above ---


class TestV2Parser:
    def test_parse_valid_file(self):
        parser = V2Parser()
        recording = parser.parse(FIXTURES_DIR / "sample.cast")
        assert recording.header.version == 2
        assert recording.header.width == 80
        assert recording.header.height == 24
        assert recording.header.timestamp == 1234567890
        assert recording.header.duration == 4.0
        assert len(recording.events) == 7

    def test_parse_events_sorted_by_time(self):
        parser = V2Parser()
        recording = parser.parse(FIXTURES_DIR / "sample.cast")
        times = [e.time for e in recording.events]
        assert times == sorted(times)

    def test_parse_event_content(self):
        parser = V2Parser()
        recording = parser.parse(FIXTURES_DIR / "sample.cast")
        assert recording.events[0] == Event(time=0.5, type="o", data="$ ")
        assert recording.events[2] == Event(time=1.5, type="o", data="hello\r\n")

    def test_parse_from_text_stream(self):
        cast_text = '{"version": 2, "width": 40, "height": 10}\n[0.1, "o", "hi"]\n'
        parser = V2Parser()
        recording = parser.parse(io.StringIO(cast_text))
        assert recording.header.width == 40
        assert len(recording.events) == 1

    def test_parse_computes_duration_from_last_event(self):
        cast_text = '{"version": 2, "width": 80, "height": 24}\n[1.0, "o", "a"]\n[5.5, "o", "b"]\n'
        parser = V2Parser()
        recording = parser.parse(io.StringIO(cast_text))
        assert recording.header.duration == 5.5

    def test_parse_empty_file_raises(self):
        parser = V2Parser()
        with pytest.raises(ValueError, match="Empty cast file"):
            parser.parse(io.StringIO(""))

    def test_parse_wrong_version_raises(self):
        cast_text = '{"version": 1, "width": 80, "height": 24}\n'
        parser = V2Parser()
        with pytest.raises(ValueError, match="Unsupported version"):
            parser.parse(io.StringIO(cast_text))

    def test_parse_missing_width_raises(self):
        cast_text = '{"version": 2, "height": 24}\n'
        parser = V2Parser()
        with pytest.raises(ValueError, match="Missing required"):
            parser.parse(io.StringIO(cast_text))

    def test_parse_no_events_returns_zero_duration(self):
        cast_text = '{"version": 2, "width": 80, "height": 24}\n'
        parser = V2Parser()
        recording = parser.parse(io.StringIO(cast_text))
        assert recording.header.duration == 0.0
        assert len(recording.events) == 0

    def test_parse_malformed_json_raises(self):
        parser = V2Parser()
        with pytest.raises(Exception):
            parser.parse(io.StringIO("{not json"))
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_parser.py::TestV2Parser -v`

Expected: All tests FAIL with `ModuleNotFoundError: No module named 'bettercast.formats.v2'`

- [ ] **Step 3: Implement V2Parser**

Create `src/bettercast/formats/v2.py`:

```python
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

        duration = header_data.get("duration") or (events[-1].time if events else 0.0)

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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_parser.py -v`

Expected: All 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bettercast/formats/v2.py tests/test_parser.py
git commit -m "feat: implement asciicast v2 parser with validation"
```

---

### Task 4: Engine Core — Init + Seek (TDD)

**Files:**
- Create: `src/bettercast/engine.py`
- Create: `tests/conftest.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Create shared test fixtures**

Create `tests/conftest.py`:

```python
from pathlib import Path

import pytest

from bettercast.formats.base import Recording
from bettercast.formats.v2 import V2Parser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_recording() -> Recording:
    parser = V2Parser()
    return parser.parse(FIXTURES_DIR / "sample.cast")
```

- [ ] **Step 2: Write failing engine init + seek tests**

Create `tests/test_engine.py`:

```python
from bettercast.engine import PlaybackEngine


class TestEngineInit:
    def test_initial_state(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.position == 0.0
        assert engine.speed == 1.0
        assert engine.playing is False
        assert engine.duration == 4.0

    def test_screen_dimensions(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.screen.columns == 80
        assert engine.screen.lines == 24


class TestEngineSeek:
    def test_seek_to_start(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.0)
        assert engine.position == 0.0
        # No events applied, screen should be empty
        assert engine.screen.display[0].strip() == ""

    def test_seek_to_middle(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        assert engine.position == 2.0
        # Events at 0.5, 1.0, 1.5, 2.0 applied
        assert "echo hello" in engine.screen.display[0]
        assert engine.screen.display[1].strip() == "hello"
        assert engine.screen.display[2].startswith("$ ")

    def test_seek_to_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(4.0)
        assert engine.position == 4.0
        assert "Python 3.12.0" in engine.screen.display[3]
        assert engine.screen.display[4].startswith("$ ")

    def test_seek_clamps_to_zero(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(-5.0)
        assert engine.position == 0.0

    def test_seek_clamps_to_duration(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(100.0)
        assert engine.position == 4.0

    def test_seek_resets_screen(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(4.0)
        assert "Python" in engine.screen.display[3]
        engine.seek(0.0)
        assert engine.screen.display[3].strip() == ""
```

- [ ] **Step 3: Run tests to verify failure**

Run: `uv run pytest tests/test_engine.py -v`

Expected: All tests FAIL with `ModuleNotFoundError: No module named 'bettercast.engine'`

- [ ] **Step 4: Implement engine core**

Create `src/bettercast/engine.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify pass**

Run: `uv run pytest tests/test_engine.py -v`

Expected: All 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/bettercast/engine.py tests/conftest.py tests/test_engine.py
git commit -m "feat: playback engine with init and seek via pyte virtual terminal"
```

---

### Task 5: Engine — Advance + Playback Controls (TDD)

**Files:**
- Modify: `src/bettercast/engine.py`
- Modify: `tests/test_engine.py`

- [ ] **Step 1: Write failing advance + controls tests**

Add to `tests/test_engine.py`:

```python
class TestEngineAdvance:
    def test_advance_while_paused_returns_false(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.advance(1.0) is False
        assert engine.position == 0.0

    def test_advance_applies_events(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        # Advance 1 second at 1x speed — should apply event at 0.5
        changed = engine.advance(1.0)
        assert changed is True
        assert engine.position == 1.0
        assert "$ " in engine.screen.display[0]

    def test_advance_respects_speed(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.speed = 2.0
        # Advance 1 real second at 2x → 2 virtual seconds
        engine.advance(1.0)
        assert engine.position == 2.0
        assert "echo hello" in engine.screen.display[0]

    def test_advance_pauses_at_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.advance(10.0)
        assert engine.playing is False
        assert engine.position == 4.0

    def test_advance_returns_false_when_no_events(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.seek(4.0)
        engine.playing = True
        changed = engine.advance(1.0)
        assert changed is False


class TestEngineControls:
    def test_play(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.play()
        assert engine.playing is True

    def test_pause(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.pause()
        assert engine.playing is False

    def test_toggle(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.toggle()
        assert engine.playing is True
        engine.toggle()
        assert engine.playing is False

    def test_set_speed(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(2.0)
        assert engine.speed == 2.0

    def test_set_speed_clamps_low(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(0.1)
        assert engine.speed == 0.5

    def test_set_speed_clamps_high(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(20.0)
        assert engine.speed == 8.0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_engine.py::TestEngineAdvance tests/test_engine.py::TestEngineControls -v`

Expected: FAIL with `AttributeError: 'PlaybackEngine' object has no attribute 'advance'`

- [ ] **Step 3: Add advance and controls to engine**

Add these methods to the `PlaybackEngine` class in `src/bettercast/engine.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_engine.py -v`

Expected: All 19 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bettercast/engine.py tests/test_engine.py
git commit -m "feat: engine advance with speed control, play/pause/toggle"
```

---

### Task 6: Engine — Search Index (TDD)

**Files:**
- Modify: `src/bettercast/engine.py`
- Modify: `tests/test_engine.py`

- [ ] **Step 1: Write failing search tests**

Add to `tests/test_engine.py`:

```python
class TestEngineSearch:
    def test_build_search_index(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert len(engine._search_index) > 0

    def test_search_index_deduplicates(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        # Each entry should have unique text (only stored when text changes)
        texts = [text for _, text in engine._search_index]
        assert len(texts) == len(set(texts))

    def test_next_match_finds_text(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        match_time = engine.next_match("python")
        assert match_time is not None
        assert match_time >= 3.0

    def test_next_match_case_insensitive(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        match_time = engine.next_match("HELLO")
        assert match_time is not None
        assert match_time >= 1.0

    def test_next_match_returns_none_past_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 4.0
        assert engine.next_match("hello") is None

    def test_prev_match_finds_text(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 4.0
        match_time = engine.prev_match("hello")
        assert match_time is not None
        assert match_time < 4.0

    def test_prev_match_returns_none_at_start(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        assert engine.prev_match("hello") is None

    def test_next_match_empty_query_returns_none(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert engine.next_match("") is None

    def test_count_matches(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        count = engine.count_matches("python")
        assert count >= 1

    def test_count_matches_empty_query(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert engine.count_matches("") == 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_engine.py::TestEngineSearch -v`

Expected: FAIL with `AttributeError: 'PlaybackEngine' object has no attribute 'build_search_index'`

- [ ] **Step 3: Add search methods to engine**

Add these methods to the `PlaybackEngine` class in `src/bettercast/engine.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_engine.py -v`

Expected: All 29 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bettercast/engine.py tests/test_engine.py
git commit -m "feat: search index with next/prev match and count"
```

---

### Task 7: TerminalDisplay Widget (TDD)

**Files:**
- Create: `src/bettercast/ui/terminal.py`
- Create: `tests/test_ui.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_ui.py`:

```python
import pytest

from bettercast.engine import PlaybackEngine
from bettercast.ui.terminal import TerminalDisplay, pyte_color_to_rich, char_to_style

import pyte
from rich.style import Style


class TestPyteColorConversion:
    def test_default_returns_none(self):
        assert pyte_color_to_rich("default") is None

    def test_named_color_passes_through(self):
        assert pyte_color_to_rich("red") == "red"

    def test_256_color_index(self):
        assert pyte_color_to_rich("196") == "color(196)"

    def test_hex_color(self):
        assert pyte_color_to_rich("ff5500") == "#ff5500"


class TestCharToStyle:
    def test_default_char(self):
        char = pyte.screens.Char(" ")
        style = char_to_style(char)
        assert style == Style()

    def test_bold_char(self):
        char = pyte.screens.Char("x", bold=True)
        style = char_to_style(char)
        assert style.bold is True


class TestTerminalDisplay:
    def test_render_from_engine(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        widget = TerminalDisplay()
        content = widget.render_engine_screen(engine)
        plain = content.plain
        assert "echo hello" in plain
        assert "hello" in plain
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_ui.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'bettercast.ui.terminal'`

- [ ] **Step 3: Implement TerminalDisplay**

Create `src/bettercast/ui/terminal.py`:

```python
from __future__ import annotations

from textual.widgets import Static
from rich.style import Style
from rich.text import Text

from bettercast.engine import PlaybackEngine

# Re-export for testing
__all__ = ["TerminalDisplay", "pyte_color_to_rich", "char_to_style"]


def pyte_color_to_rich(color: str) -> str | None:
    if color == "default":
        return None
    try:
        return f"color({int(color)})"
    except ValueError:
        pass
    if len(color) == 6:
        try:
            int(color, 16)
            return f"#{color}"
        except ValueError:
            pass
    return color


def char_to_style(char) -> Style:
    fg = pyte_color_to_rich(char.fg)
    bg = pyte_color_to_rich(char.bg)
    return Style(
        color=fg,
        bgcolor=bg,
        bold=char.bold if char.bold else None,
        italic=char.italics if char.italics else None,
        underline=char.underscore if char.underscore else None,
        strike=char.strikethrough if char.strikethrough else None,
        reverse=char.reverse if char.reverse else None,
    )


class TerminalDisplay(Static):
    DEFAULT_CSS = """
    TerminalDisplay {
        height: 1fr;
        overflow: hidden;
    }
    """

    def render_engine_screen(self, engine: PlaybackEngine) -> Text:
        screen = engine.screen
        output = Text()
        for row in range(screen.lines):
            if row > 0:
                output.append("\n")
            for col in range(screen.columns):
                char = screen.buffer[row][col]
                style = char_to_style(char)
                output.append(char.data, style=style)
        return output

    def update_from_engine(self, engine: PlaybackEngine) -> None:
        content = self.render_engine_screen(engine)
        self.update(content)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_ui.py -v`

Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bettercast/ui/terminal.py tests/test_ui.py
git commit -m "feat: TerminalDisplay widget renders pyte screen with Rich styles"
```

---

### Task 8: ProgressBar Widget (TDD)

**Files:**
- Create: `src/bettercast/ui/progress.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ui.py`:

```python
from bettercast.ui.progress import PlaybackProgressBar, format_time


class TestFormatTime:
    def test_zero(self):
        assert format_time(0.0) == "00:00"

    def test_seconds(self):
        assert format_time(45.0) == "00:45"

    def test_minutes(self):
        assert format_time(125.0) == "02:05"

    def test_hours(self):
        assert format_time(3661.0) == "1:01:01"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_ui.py::TestFormatTime -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'bettercast.ui.progress'`

- [ ] **Step 3: Implement ProgressBar**

Create `src/bettercast/ui/progress.py`:

```python
from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static
from rich.text import Text


def format_time(seconds: float) -> str:
    total = int(seconds)
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class PlaybackProgressBar(Static):
    DEFAULT_CSS = """
    PlaybackProgressBar {
        height: 1;
        dock: bottom;
        background: $surface;
    }
    """

    position = reactive(0.0)
    duration = reactive(0.0)
    speed = reactive(1.0)
    playing = reactive(False)

    def render(self) -> Text:
        icon = "\u25b6" if self.playing else "\u23f8"
        current = format_time(self.position)
        total = format_time(self.duration)
        speed_str = f"{self.speed:.1f}x"

        prefix = f" {icon} {current} / {total} "
        suffix = f" {speed_str} "
        bar_width = max(0, self.size.width - len(prefix) - len(suffix))

        if bar_width > 0 and self.duration > 0:
            ratio = min(self.position / self.duration, 1.0)
            filled = int(bar_width * ratio)
            remaining = bar_width - filled
            bar = "\u2501" * filled + "\u2500" * remaining
        else:
            bar = ""

        return Text(f"{prefix}{bar}{suffix}")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_ui.py -v`

Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bettercast/ui/progress.py tests/test_ui.py
git commit -m "feat: PlaybackProgressBar widget with time formatting"
```

---

### Task 9: HelpOverlay + SearchOverlay Widgets

**Files:**
- Create: `src/bettercast/ui/help.py`
- Create: `src/bettercast/ui/search.py`

- [ ] **Step 1: Implement HelpOverlay**

Create `src/bettercast/ui/help.py`:

```python
from __future__ import annotations

from textual.widgets import Static


HELP_TEXT = """\
┌─── Keybindings ──────────────────┐
│ Space       Play/Pause           │
│ ← / →      Seek ±5s             │
│ Shift+←/→  Seek ±30s            │
│ [ / ]      Speed -/+ 0.5x       │
│ Home/End   Start/End             │
│ /          Search                │
│ n / N      Next/Prev match      │
│ ?          Toggle help           │
│ q          Quit                  │
└──────────────────────────────────┘"""


class HelpOverlay(Static):
    DEFAULT_CSS = """
    HelpOverlay {
        layer: overlay;
        display: none;
        content-align: center middle;
        width: 100%;
        height: 100%;
        background: $surface 80%;
    }
    """

    def render(self) -> str:
        return HELP_TEXT
```

- [ ] **Step 2: Implement SearchOverlay**

Create `src/bettercast/ui/search.py`:

```python
from __future__ import annotations

from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, Static


class SearchOverlay(Horizontal):
    DEFAULT_CSS = """
    SearchOverlay {
        dock: bottom;
        height: 1;
        display: none;
        background: $surface;
    }
    SearchOverlay Input {
        width: 1fr;
        border: none;
        padding: 0;
    }
    SearchOverlay #match-count {
        width: auto;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close search", show=False),
    ]

    def compose(self):
        yield Input(placeholder="Search...")
        yield Static("", id="match-count")

    def update_match_count(self, count: int) -> None:
        label = self.query_one("#match-count", Static)
        if count > 0:
            label.update(f"[{count} matches]")
        else:
            label.update("[no matches]")

    def action_dismiss(self) -> None:
        self.query_one(Input).value = ""
        self.display = False
```

- [ ] **Step 3: Write tests for both widgets**

Add to `tests/test_ui.py`:

```python
from bettercast.ui.help import HelpOverlay, HELP_TEXT
from bettercast.ui.search import SearchOverlay


class TestHelpOverlay:
    def test_render_contains_keybindings(self):
        widget = HelpOverlay()
        text = widget.render()
        assert "Play/Pause" in text
        assert "Search" in text
        assert "Quit" in text


class TestSearchOverlay:
    def test_update_match_count_with_matches(self):
        overlay = SearchOverlay()
        # Can't test compose without mounting, but we can verify the class exists
        assert hasattr(overlay, "update_match_count")
        assert hasattr(overlay, "action_dismiss")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_ui.py -v`

Expected: All 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bettercast/ui/help.py src/bettercast/ui/search.py tests/test_ui.py
git commit -m "feat: HelpOverlay and SearchOverlay widgets"
```

---

### Task 10: App Assembly + Keybindings

**Files:**
- Create: `src/bettercast/ui/app.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Implement BettercastApp**

Create `src/bettercast/ui/app.py`:

```python
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input

from bettercast.engine import PlaybackEngine
from bettercast.ui.help import HelpOverlay
from bettercast.ui.progress import PlaybackProgressBar
from bettercast.ui.search import SearchOverlay
from bettercast.ui.terminal import TerminalDisplay


class BettercastApp(App):
    CSS = """
    Screen {
        layers: base overlay;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pause", priority=True),
        Binding("left", "seek_back", "Seek -5s"),
        Binding("right", "seek_forward", "Seek +5s"),
        Binding("shift+left", "seek_back_far", "Seek -30s"),
        Binding("shift+right", "seek_forward_far", "Seek +30s"),
        Binding("left_square_bracket", "speed_down", "Speed -0.5x"),
        Binding("right_square_bracket", "speed_up", "Speed +0.5x"),
        Binding("home", "seek_start", "Start"),
        Binding("end", "seek_end", "End"),
        Binding("slash", "open_search", "Search", priority=True),
        Binding("n", "next_match", "Next match"),
        Binding("N", "prev_match", "Prev match"),
        Binding("question_mark", "toggle_help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, engine: PlaybackEngine) -> None:
        super().__init__()
        self.engine = engine
        self._search_query: str = ""

    def compose(self) -> ComposeResult:
        yield TerminalDisplay(id="terminal")
        yield SearchOverlay(id="search")
        yield PlaybackProgressBar(id="progress")
        yield HelpOverlay(id="help")

    def on_mount(self) -> None:
        self.engine.build_search_index()
        self._refresh_display()
        progress = self.query_one("#progress", PlaybackProgressBar)
        progress.duration = self.engine.duration
        self._timer = self.set_interval(1 / 30, self._tick)

    def _tick(self) -> None:
        changed = self.engine.advance(1 / 30)
        if changed:
            self._refresh_display()
        progress = self.query_one("#progress", PlaybackProgressBar)
        progress.position = self.engine.position
        progress.playing = self.engine.playing
        progress.speed = self.engine.speed

    def _refresh_display(self) -> None:
        terminal = self.query_one("#terminal", TerminalDisplay)
        terminal.update_from_engine(self.engine)

    # --- Playback actions ---

    def action_toggle_play(self) -> None:
        self.engine.toggle()

    def action_seek_back(self) -> None:
        self.engine.seek(self.engine.position - 5.0)
        self._refresh_display()

    def action_seek_forward(self) -> None:
        self.engine.seek(self.engine.position + 5.0)
        self._refresh_display()

    def action_seek_back_far(self) -> None:
        self.engine.seek(self.engine.position - 30.0)
        self._refresh_display()

    def action_seek_forward_far(self) -> None:
        self.engine.seek(self.engine.position + 30.0)
        self._refresh_display()

    def action_speed_down(self) -> None:
        self.engine.set_speed(self.engine.speed - 0.5)

    def action_speed_up(self) -> None:
        self.engine.set_speed(self.engine.speed + 0.5)

    def action_seek_start(self) -> None:
        self.engine.seek(0.0)
        self._refresh_display()

    def action_seek_end(self) -> None:
        self.engine.seek(self.engine.duration)
        self._refresh_display()

    # --- Search actions ---

    def action_open_search(self) -> None:
        search = self.query_one("#search", SearchOverlay)
        search.display = True
        search_input = search.query_one(Input)
        search_input.value = ""
        search_input.focus()

    def action_next_match(self) -> None:
        if self._search_query:
            match_time = self.engine.next_match(self._search_query)
            if match_time is not None:
                self.engine.seek(match_time)
                self._refresh_display()

    def action_prev_match(self) -> None:
        if self._search_query:
            match_time = self.engine.prev_match(self._search_query)
            if match_time is not None:
                self.engine.seek(match_time)
                self._refresh_display()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._search_query = event.value
        search = self.query_one("#search", SearchOverlay)
        search.display = False
        if self._search_query:
            match_time = self.engine.next_match(self._search_query)
            if match_time is not None:
                self.engine.seek(match_time)
                self._refresh_display()

    def on_input_changed(self, event: Input.Changed) -> None:
        search = self.query_one("#search", SearchOverlay)
        if search.display:
            count = self.engine.count_matches(event.value)
            search.update_match_count(count)

    # --- Help ---

    def action_toggle_help(self) -> None:
        help_overlay = self.query_one("#help", HelpOverlay)
        help_overlay.display = not help_overlay.display
```

- [ ] **Step 2: Write app integration tests**

Add to `tests/test_ui.py`:

```python
from bettercast.ui.app import BettercastApp


class TestBettercastApp:
    @pytest.mark.asyncio
    async def test_app_mounts_all_widgets(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert app.query_one("#terminal", TerminalDisplay)
            assert app.query_one("#progress", PlaybackProgressBar)
            assert app.query_one("#search", SearchOverlay)
            assert app.query_one("#help", HelpOverlay)

    @pytest.mark.asyncio
    async def test_space_toggles_play(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.playing is False
            await pilot.press("space")
            assert engine.playing is True
            await pilot.press("space")
            assert engine.playing is False

    @pytest.mark.asyncio
    async def test_progress_bar_shows_duration(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            progress = app.query_one("#progress", PlaybackProgressBar)
            assert progress.duration == 4.0

    @pytest.mark.asyncio
    async def test_q_quits(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("q")
```

- [ ] **Step 3: Run tests to verify pass**

Run: `uv run pytest tests/test_ui.py -v`

Expected: All 17 tests PASS

Note: If any Textual key names are wrong (e.g., `left_square_bracket`), update the `BINDINGS` list in `app.py` to use the correct Textual key identifiers. Run `uv run python -c "from textual.keys import Keys; print([k for k in dir(Keys) if not k.startswith('_')])"` to list valid key names if needed.

- [ ] **Step 4: Commit**

```bash
git add src/bettercast/ui/app.py tests/test_ui.py
git commit -m "feat: BettercastApp with all keybindings and widget assembly"
```

---

### Task 11: CLI Entry Point

**Files:**
- Create: `src/bettercast/cli.py`
- Create: `src/bettercast/__main__.py`

- [ ] **Step 1: Implement CLI**

Create `src/bettercast/cli.py`:

```python
from __future__ import annotations

from pathlib import Path

import click

from bettercast.engine import PlaybackEngine
from bettercast.formats.v2 import V2Parser
from bettercast.ui.app import BettercastApp


@click.command()
@click.argument("cast_file", type=click.Path(exists=True, path_type=Path))
@click.option("--speed", default=1.0, type=float, help="Initial playback speed (default: 1.0)")
def main(cast_file: Path, speed: float) -> None:
    """Play asciinema recordings in a terminal UI."""
    parser = V2Parser()
    try:
        recording = parser.parse(cast_file)
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    if not recording.events:
        raise click.ClickException("Recording has no events.")

    engine = PlaybackEngine(recording)
    engine.set_speed(speed)

    app = BettercastApp(engine)
    app.run()
```

- [ ] **Step 2: Create __main__.py**

Create `src/bettercast/__main__.py`:

```python
from bettercast.cli import main

main()
```

- [ ] **Step 3: Verify CLI works**

Run: `uv run bettercast tests/fixtures/sample.cast`

Expected: The TUI launches showing the first frame of the recording. Press `q` to quit. Verify:
- Progress bar shows `00:00 / 00:04`
- Pressing `space` starts playback
- Pressing `?` shows help overlay
- Pressing `q` quits cleanly

Run: `uv run bettercast --help`

Expected: Shows usage message with `CAST_FILE` argument and `--speed` option.

Run: `uv run bettercast nonexistent.cast`

Expected: Error message about file not existing.

- [ ] **Step 4: Commit**

```bash
git add src/bettercast/cli.py src/bettercast/__main__.py
git commit -m "feat: CLI entry point with click argument parsing"
```

---

### Task 12: End-to-End Verification

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest tests/ -v`

Expected: All tests pass. Note the exact count.

- [ ] **Step 2: Manual smoke test — full playback**

Run: `uv run bettercast tests/fixtures/sample.cast`

Test each feature:
1. Press `space` — playback starts, progress bar moves, icon changes to ▶
2. Press `space` again — playback pauses
3. Press `→` — seeks forward 5 seconds
4. Press `←` — seeks back 5 seconds
5. Press `]` — speed increases (shown in progress bar)
6. Press `[` — speed decreases
7. Press `Home` — jumps to start
8. Press `End` — jumps to end
9. Press `/` — search overlay appears, type "hello", press Enter
10. Press `n` — jumps to next match
11. Press `?` — help overlay toggles
12. Press `q` — quits

- [ ] **Step 3: Test with --speed flag**

Run: `uv run bettercast tests/fixtures/sample.cast --speed 2.0`

Expected: Progress bar shows `2.0x`. Playback runs at double speed when started.

- [ ] **Step 4: Final commit**

Run: `uv run pytest tests/ -v` one more time. If all pass:

```bash
git add -A
git commit -m "feat: complete bettercast v0.1.0 — terminal asciinema player"
```

---

## Verification

To fully verify the implementation:

1. **Unit tests:** `uv run pytest tests/ -v` — all tests pass
2. **CLI help:** `uv run bettercast --help` — shows usage
3. **Error handling:** `uv run bettercast nonexistent.cast` — shows error
4. **Manual playback:** `uv run bettercast tests/fixtures/sample.cast` — TUI launches, all keybindings work
5. **Speed flag:** `uv run bettercast tests/fixtures/sample.cast --speed 0.5` — starts at half speed
