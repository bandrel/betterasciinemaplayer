# Bettercast Quality-of-Life Features Design

## Overview

Eight quality-of-life features for the Bettercast asciinema player, organized into three layers for parallel implementation.

## Layer 1: Engine Features

### 1a. Frame-by-Frame Stepping

Add `step_forward()` and `step_backward()` methods to `PlaybackEngine`.

- `step_forward()`: advances to the next output event (type `"o"`), sets `position` to that event's timestamp, auto-pauses playback.
- `step_backward()`: seeks to the last output event whose timestamp is strictly before the current position, auto-pauses playback. At position 0.0, this is a no-op.
- Skips non-`"o"` events when stepping.
- Keybindings: `.` (forward), `,` (backward).

### 1b. Auto-Restart at End

When playback reaches the end and pauses, pressing Space should restart from the beginning instead of requiring Home then Space.

- Implementation lives in `action_toggle_play` in `app.py`: if `position >= duration` when the user presses space, seek to `0.0` before toggling play.
- No engine state changes needed — this is a UI-level convenience.
- Note: despite being a UI change, this is grouped with Layer 1 because it depends on engine state (position/duration) and is conceptually a playback behavior.

### 1c. Loop Mode

Add a `looping: bool` property to `PlaybackEngine` (default `False`).

- When `advance()` reaches the end and `looping` is `True`, seek to `0.0` and continue playing instead of setting `playing = False`.
- Toggled with `l` key.
- Progress bar displays a loop icon (&#x27F3;) when active.

### 1d. Idle Time Compression

Add an `idle_threshold: float` property to `PlaybackEngine` (default `2.0` seconds).

- During `advance()`, when the gap between the current position and the next event exceeds the threshold, fast-forward to `next_event.time - 0.5s` (landing just before the action resumes).
- Transparent to the user — long pauses feel shorter.
- CLI flag `--idle-threshold <seconds>` controls the threshold value.
- CLI flag `--no-idle-compress` disables compression entirely (sets threshold to infinity).

## Layer 2: UI Features

### 2a. Escape to Dismiss Search

- Pressing `Escape` while the search input is focused hides the `SearchOverlay` and restores focus to the terminal.
- Does not execute a search or change the current `_search_query`.
- Existing `n`/`N` navigation continues to work with the previous query.

### 2b. Jump to Timestamp

- `g` keybinding opens a `TimestampOverlay` — a small input overlay (similar to search) with a label "Go to: ".
- User types a timestamp in `MM:SS` or `H:MM:SS` format.
- On submit, parse the time, seek to it, and close the overlay.
- Invalid input silently closes the overlay without seeking.
- New `TimestampOverlay` widget in `ui/timestamp.py`, lives on the overlay layer alongside search and help.

## Layer 3: Cross-Cutting Features

### 3a. Bookmarks

**Engine side** (`engine.py`):

- `bookmarks: list[tuple[float, str]]` — stores `(timestamp, label)` pairs.
- `add_bookmark(time: float, label: str = "")` — adds a bookmark; auto-generates label as "Bookmark N" if empty.
- `remove_bookmark(index: int)` — removes bookmark by index.
- `next_bookmark(from_time: float) -> float | None` — returns timestamp of next bookmark after `from_time`.
- `prev_bookmark(from_time: float) -> float | None` — returns timestamp of previous bookmark before `from_time`.

**UI side** (`app.py` + new `ui/bookmarks.py`):

- `m` — bookmark the current position.
- `b` — open `BookmarkOverlay` listing all bookmarks with timestamps. User selects one to jump to it, or presses `d` to delete the highlighted bookmark.
- `{` (Shift+`[`) — jump to previous bookmark.
- `}` (Shift+`]`) — jump to next bookmark.

**Progress bar** (`progress.py`):

- Bookmark positions rendered as `|` markers on the progress bar.
- Requires the progress bar to accept a list of bookmark timestamps from the app.

### 3b. Copy Terminal Text

- `c` keybinding copies the full visible terminal text (from the pyte screen buffer) to the system clipboard.
- Uses subprocess calls to platform-native clipboard tools: `pbcopy` (macOS), `xclip` or `xsel` (Linux). No external Python dependency.
- A brief flash message ("Copied!") appears in the progress bar area for ~1 second as confirmation.
- Copies the entire visible frame — no text selection or mouse interaction.

## Parallel Execution Strategy

Features are grouped by layer to minimize merge conflicts when executed by parallel agents:

| Group | Features | Primary Files | Agent Isolation |
|-------|----------|--------------|-----------------|
| Layer 1 | Frame stepping, auto-restart, loop mode, idle compression | `engine.py`, `cli.py`, `app.py` bindings | Worktree per feature; engine methods don't overlap |
| Layer 2 | Escape dismiss, jump to timestamp | `ui/search.py`, new `ui/timestamp.py`, `app.py` bindings | Worktree per feature; different widgets |
| Layer 3 | Bookmarks, copy text | `engine.py`, new `ui/bookmarks.py`, `ui/progress.py`, `ui/terminal.py`, `app.py` | Worktree per feature; bookmarks and copy touch different engine/UI areas |

**Merge order:** Layer 1 and Layer 2 can execute fully in parallel. Layer 3 should begin after Layer 1 engine work is merged (bookmarks add engine methods; copy reads engine screen). Within each layer, features can run in parallel via worktrees.

**Shared file coordination** (`app.py`, `help.py`):

- Each agent adds its own `Binding` entries and action methods to `app.py`. These are additive and unlikely to conflict if agents append to different sections.
- `help.py` keybinding text is updated as a final integration step after all features merge.

## Keybinding Summary

| Key | Action |
|-----|--------|
| `.` | Step forward one frame |
| `,` | Step backward one frame |
| `l` | Toggle loop mode |
| `g` | Jump to timestamp |
| `m` | Add bookmark |
| `b` | Open bookmark list |
| `{` | Previous bookmark |
| `}` | Next bookmark |
| `c` | Copy terminal text |
| `Escape` | Dismiss search overlay |

## Testing Strategy

Each feature gets three levels of testing:

1. **Unit tests** — for engine methods (step_forward, step_backward, loop mode, idle compression, bookmark CRUD, etc.). Located in `test_engine.py`.
2. **Widget/integration tests** — for UI behavior (overlay show/hide, keybinding responses, progress bar rendering). Located in feature-specific or existing test files.
3. **End-to-end CLI tests** — for each feature, a test in `test_cli.py` that launches the full `BettercastApp` with a sample `.cast` file and simulates the complete user workflow via Textual's pilot API. E2E tests verify the feature works through the full stack (CLI args -> engine -> UI -> visible output).

Tests are written alongside implementation using TDD — tests first, then implementation.

### E2E Test Coverage Per Feature

| Feature | E2E Test |
|---------|----------|
| Frame stepping | Launch app, pause, press `.`/`,`, verify position advances/retreats by one event |
| Auto-restart | Play to end, verify paused, press Space, verify position resets to 0 and playing |
| Loop mode | Press `l`, play to end, verify playback continues from 0 instead of pausing |
| Idle compression | Load a recording with a >2s gap, play through, verify the gap is compressed |
| Escape dismiss search | Open search with `/`, press Escape, verify overlay hidden and previous query intact |
| Jump to timestamp | Press `g`, type "00:05", submit, verify position is 5.0s |
| Bookmarks | Press `m` to add, `b` to open list, select to jump, `d` to delete, verify all |
| Copy text | Press `c`, verify clipboard contains current screen text |
