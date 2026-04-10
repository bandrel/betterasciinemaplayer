# Bettercast: A Better Asciinema Player for the Terminal

## Context

The existing `asciinema play` command provides basic sequential playback of `.cast` recordings but lacks the controls users expect from a media player: seeking, speed adjustment, search, and a visual timeline. Bettercast is a new CLI tool that plays asciinema recordings in a full keyboard-driven terminal UI with these capabilities.

## Overview

Bettercast is a Python CLI tool that replays asciicast v2 recordings in an interactive terminal UI built with Textual. It provides media-player-style controls (seek, speed, pause), text search across the recording timeline, and a visual progress bar — all driven by keyboard shortcuts.

**Package name:** `bettercast`
**CLI:** `bettercast <file.cast> [--speed 1.0]`
**Language:** Python, managed with `uv`

## Architecture

Three layers with one-directional data flow:

```
Cast Parser  -->  Playback Engine  -->  TUI Shell
(file I/O)       (state + vterm)       (Textual app)
                      ^                     |
                      |   commands          |
                      +---------------------+
```

1. **Cast Parser** — reads `.cast` files, produces a `Recording` object
2. **Playback Engine** — manages playback state and a virtual terminal (pyte)
3. **TUI Shell** — Textual app that renders the terminal and handles input

## Cast Parser

### Protocol

```python
class CastFormat(Protocol):
    def parse(self, source: Path | TextIO) -> Recording: ...
```

Any format implements this protocol. Start with asciicast v2; the protocol allows adding v1, ttyrec, etc. later.

### Data Types

```python
@dataclass(frozen=True)
class CastHeader:
    version: int
    width: int
    height: int
    duration: float | None  # computed if not in header
    timestamp: int | None
    title: str | None
    env: dict[str, str]

@dataclass(frozen=True)
class Event:
    time: float        # seconds from start
    type: str          # "o" (output) or "i" (input)
    data: str          # terminal data (escape sequences, text)

@dataclass
class Recording:
    header: CastHeader
    events: list[Event]  # sorted by time
```

### V2 Parser

- First line: JSON object (header). Must have `version: 2`, `width`, `height`.
- Subsequent lines: JSON arrays `[time, type, data]`.
- Validates header fields and event structure on load.
- Computes `duration` from the last event's timestamp if not in the header.

## Playback Engine

### Virtual Terminal

Uses `pyte.Screen` + `pyte.Stream` to process terminal escape sequences. At any point:
- `screen.display` gives current terminal content as `list[str]`
- `screen.buffer` gives character-level attributes (foreground, background, bold, italic, underline, etc.)

### State

- `position: float` — current time in seconds
- `speed: float` — playback speed multiplier (default 1.0)
- `playing: bool` — whether playback is active

### Seeking

To seek to time `T`:
1. Reset the pyte screen
2. Replay all events from `events[0]` up to time `T`
3. Update `position` to `T`

This is simple and fast for typical recordings (a few thousand events). Optimization with periodic snapshots can be added later if needed.

### Playback Loop

Async loop:
1. Find the next event after `position`
2. Wait `(event.time - position) / speed` seconds
3. Feed event data to pyte stream
4. Update `position`, notify TUI to re-render
5. At end of recording, pause on the last frame

### Search Index

Built on load by replaying all events and capturing the full screen text at each output event. Stored as a list of `(time, text)` tuples — only entries where the screen text actually changed from the previous snapshot are kept, to reduce memory. Enables:
- Find all timestamps where a query string appears on screen
- Navigate between matches with `n`/`N`

### Commands

```python
play() -> None
pause() -> None
toggle() -> None
seek(time: float) -> None
set_speed(speed: float) -> None
next_match(query: str) -> float | None   # returns timestamp or None
prev_match(query: str) -> float | None
```

## TUI Shell

### Layout

```
+---------------------------------------------+
|                                              |
|           Terminal Display                   |
|        (renders pyte screen buffer)          |
|                                              |
|                                              |
+---------------------------------------------+
| > 00:32 / 02:15  --------====------  1.0x   |  <- Progress/Status Bar
+---------------------------------------------+
```

### Widgets

- **TerminalDisplay** — renders the pyte screen buffer with character attributes (colors, bold, etc.) using Rich renderables inside a Textual Static widget
- **ProgressBar** — horizontal bar showing playback position, current time, total duration, and speed
- **HelpOverlay** — modal overlay toggled with `?`, lists all keybindings
- **SearchOverlay** — input bar toggled with `/`, shows query input and match count

### Keybindings

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `Left` / `Right` | Seek +/-5 seconds |
| `Shift+Left` / `Shift+Right` | Seek +/-30 seconds |
| `[` / `]` | Decrease/Increase speed by 0.5x |
| `Home` / `End` | Jump to start/end |
| `/` | Open search |
| `n` / `N` | Next/Previous search match |
| `?` | Toggle help overlay |
| `q` | Quit |

### Terminal Resize

Textual handles terminal resize events. The terminal display widget clips or centers the recorded content if the user's terminal is smaller/larger than the recording's dimensions.

## Project Structure

```
betterasciinemaplayer/
├── pyproject.toml              # uv project config, CLI entry point
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
│           ├── app.py          # Textual App class
│           ├── terminal.py     # TerminalDisplay widget
│           ├── progress.py     # ProgressBar widget
│           ├── help.py         # HelpOverlay widget
│           └── search.py       # SearchOverlay widget
├── tests/
│   ├── test_parser.py
│   ├── test_engine.py
│   └── fixtures/
│       └── sample.cast
└── .gitignore
```

## Dependencies

- `textual` — TUI framework
- `pyte` — virtual terminal emulator
- `click` — CLI argument parsing

Dev dependencies:
- `pytest` — test runner
- `pytest-asyncio` — async test support

## Error Handling

- **Invalid .cast file** — clear error message on malformed JSON, missing header, or unsupported version. Exit with non-zero status code.
- **Empty recording** — header present but no events: print message, exit cleanly.
- **Large recordings** — show a brief loading indicator while building the search index.
- **End of recording** — pause on last frame. User can seek back or quit.

## Testing Strategy

- **Parser tests** — fixture `.cast` files: valid v2, malformed JSON, missing header fields, empty events, edge cases.
- **Engine tests** — seeking accuracy (seek to time T, verify screen content matches expected), speed changes, search matching against known recordings.
- **UI tests** — Textual's `App.run_test()` for simulating key presses and verifying widget state (play/pause toggle, speed display, search results).

## Scope (MVP)

The first version includes:
- Asciicast v2 parsing with extensible parser protocol
- Full playback engine with pyte virtual terminal
- Seeking, speed control, play/pause
- Keyboard-driven TUI with progress bar and status
- Text search across recording timeline
- Help overlay

Deferred to future versions:
- Chapter markers / bookmarks
- Asciicast v1 or ttyrec format support
- Snapshot-based seeking optimization
- Configurable keybindings
- Themes / color scheme customization
