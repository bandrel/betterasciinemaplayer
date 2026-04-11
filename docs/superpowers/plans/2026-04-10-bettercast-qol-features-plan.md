# Bettercast QoL Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 7 quality-of-life features to Bettercast: frame stepping, auto-restart, loop mode, idle compression, jump to timestamp, bookmarks, and copy text.

**Architecture:** Features are organized into 3 parallel groups by layer (engine, UI, cross-cutting). Each task is designed for isolated worktree execution. Tasks within a group can run in parallel. Group C tasks depend on Group A being merged first.

**Tech Stack:** Python 3.12+, Textual 3.0+, pyte 0.8+, Click 8.0+, pytest + pytest-asyncio

**Note:** Feature "Escape to dismiss search" from the original spec is already implemented (see `src/bettercast/ui/search.py:27-29` and integration tests in `test_integration.py:196-214`). Skipped in this plan.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/bettercast/engine.py` | Modify | Add step_forward, step_backward, looping, idle_threshold, bookmark methods |
| `src/bettercast/cli.py` | Modify | Add --idle-threshold and --no-idle-compress CLI flags |
| `src/bettercast/ui/app.py` | Modify | Add keybindings and action methods for all features |
| `src/bettercast/ui/progress.py` | Modify | Show loop icon, bookmark markers, flash messages |
| `src/bettercast/ui/help.py` | Modify | Update help text with all new keybindings |
| `src/bettercast/ui/timestamp.py` | Create | TimestampOverlay widget |
| `src/bettercast/ui/bookmarks.py` | Create | BookmarkOverlay widget |
| `tests/test_engine.py` | Modify | Unit tests for all new engine methods |
| `tests/test_integration.py` | Modify | E2E tests for all new features |
| `tests/test_cli.py` | Modify | CLI flag tests for idle compression |
| `tests/test_overlays.py` | Modify | Unit tests for new overlay widgets |
| `tests/fixtures/idle_gaps.cast` | Create | Test fixture with >2s gaps for idle compression |

---

## Group A: Engine Features (Parallel)

### Task 1: Frame-by-Frame Stepping

**Files:**
- Modify: `src/bettercast/engine.py`
- Modify: `src/bettercast/ui/app.py`
- Modify: `tests/test_engine.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Write failing unit tests for step_forward**

Add to `tests/test_engine.py`:

```python
class TestFrameStepping:
    def test_step_forward_moves_to_next_output_event(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.0)
        engine.step_forward()
        # First output event is at t=0.5
        assert engine.position == 0.5

    def test_step_forward_skips_to_second_event(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.5)
        engine.step_forward()
        # Next output event after 0.5 is at t=1.0
        assert engine.position == 1.0

    def test_step_forward_pauses_playback(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.step_forward()
        assert engine.playing is False

    def test_step_forward_at_end_is_noop(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(4.0)
        engine.step_forward()
        assert engine.position == 4.0

    def test_step_forward_feeds_event_data(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.step_forward()  # t=0.5: "$ "
        assert "$ " in engine.screen.display[0]

    def test_step_backward_moves_to_previous_output_event(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(1.5)
        engine.step_backward()
        # Previous output event before 1.5 is at t=1.0
        assert engine.position == 1.0

    def test_step_backward_pauses_playback(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        engine.playing = True
        engine.step_backward()
        assert engine.playing is False

    def test_step_backward_at_start_is_noop(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.0)
        engine.step_backward()
        assert engine.position == 0.0

    def test_step_backward_renders_correct_screen(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        engine.step_backward()
        # At t=1.0: "echo hello\r\n" was just output
        assert "echo hello" in engine.screen.display[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py::TestFrameStepping -v`
Expected: FAIL with `AttributeError: 'PlaybackEngine' object has no attribute 'step_forward'`

- [ ] **Step 3: Implement step_forward and step_backward in engine**

Add to `src/bettercast/engine.py` in the `PlaybackEngine` class, after the `set_speed` method:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine.py::TestFrameStepping -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Write failing integration tests for keybindings**

Add to `tests/test_integration.py`:

```python
class TestFrameSteppingE2E:
    @pytest.mark.asyncio
    async def test_dot_steps_forward(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("full_stop")
            assert engine.position == 0.5

    @pytest.mark.asyncio
    async def test_comma_steps_backward(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")  # seek to 4.0
            await pilot.press("comma")
            assert engine.position == 3.5

    @pytest.mark.asyncio
    async def test_step_forward_pauses_playback(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("space")
            assert engine.playing is True
            await pilot.press("full_stop")
            assert engine.playing is False

    @pytest.mark.asyncio
    async def test_step_forward_updates_display(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("full_stop")  # t=0.5: "$ "
            terminal = app.query_one("#terminal", TerminalDisplay)
            # Verify position moved
            assert engine.position == 0.5
```

- [ ] **Step 6: Add keybindings and actions to app.py**

Add to the `BINDINGS` list in `src/bettercast/ui/app.py`:

```python
Binding("full_stop", "step_forward", "Step forward"),
Binding("comma", "step_backward", "Step backward"),
```

Add action methods to the `BettercastApp` class, after the seek actions:

```python
def action_step_forward(self) -> None:
    self.engine.step_forward()
    self._refresh_display()

def action_step_backward(self) -> None:
    self.engine.step_backward()
    self._refresh_display()
```

- [ ] **Step 7: Run all tests to verify everything passes**

Run: `pytest tests/test_engine.py::TestFrameStepping tests/test_integration.py::TestFrameSteppingE2E -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/bettercast/engine.py src/bettercast/ui/app.py tests/test_engine.py tests/test_integration.py
git commit -m "feat: add frame-by-frame stepping with . and , keys"
```

---

### Task 2: Loop Mode

**Files:**
- Modify: `src/bettercast/engine.py`
- Modify: `src/bettercast/ui/app.py`
- Modify: `src/bettercast/ui/progress.py`
- Modify: `tests/test_engine.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Write failing unit tests for loop mode**

Add to `tests/test_engine.py`:

```python
class TestLoopMode:
    def test_looping_defaults_to_false(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.looping is False

    def test_advance_loops_when_enabled(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.looping = True
        engine.playing = True
        engine.seek(3.9)
        engine.playing = True
        engine.advance(1.0)
        # Should have looped back to start and still be playing
        assert engine.playing is True
        assert engine.position < 1.0

    def test_advance_stops_at_end_when_not_looping(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.looping = False
        engine.playing = True
        engine.advance(10.0)
        assert engine.playing is False
        assert engine.position == 4.0

    def test_loop_resets_position_to_zero(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.looping = True
        engine.playing = True
        engine.seek(3.99)
        engine.playing = True
        engine.advance(0.1)
        # After looping, position should be near start
        assert engine.position < 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py::TestLoopMode -v`
Expected: FAIL with `AttributeError: 'PlaybackEngine' object has no attribute 'looping'`

- [ ] **Step 3: Implement loop mode in engine**

In `src/bettercast/engine.py`, add to `__init__`:

```python
self.looping: bool = False
```

Modify the `advance` method. Replace the block at the end:

```python
        self.position = target
        if target >= self.duration:
            self.playing = False
        return changed
```

with:

```python
        self.position = target
        if target >= self.duration:
            if self.looping:
                self.seek(0.0)
                self.playing = True
            else:
                self.playing = False
        return changed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine.py::TestLoopMode -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Write failing integration tests**

Add to `tests/test_integration.py`:

```python
class TestLoopModeE2E:
    @pytest.mark.asyncio
    async def test_l_toggles_loop_mode(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.looping is False
            await pilot.press("l")
            assert engine.looping is True
            await pilot.press("l")
            assert engine.looping is False

    @pytest.mark.asyncio
    async def test_loop_icon_shows_in_progress_bar(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            progress = app.query_one("#progress", PlaybackProgressBar)
            rendered = str(progress.render())
            assert "\u27F3" in rendered
```

- [ ] **Step 6: Add keybinding and action to app.py**

Add to the `BINDINGS` list in `src/bettercast/ui/app.py`:

```python
Binding("l", "toggle_loop", "Loop"),
```

Add action method:

```python
def action_toggle_loop(self) -> None:
    self.engine.looping = not self.engine.looping
```

- [ ] **Step 7: Update progress bar to show loop icon**

In `src/bettercast/ui/progress.py`, add a new reactive property:

```python
looping = reactive(False)
```

Modify the `render` method. Replace:

```python
        icon = "\u25b6" if self.playing else "\u23f8"
```

with:

```python
        play_icon = "\u25b6" if self.playing else "\u23f8"
        loop_icon = " \u27f3" if self.looping else ""
        icon = f"{play_icon}{loop_icon}"
```

Update the `_tick` method in `app.py` to pass the looping state. Add this line after `self._progress_bar.speed = self.engine.speed`:

```python
self._progress_bar.looping = self.engine.looping
```

- [ ] **Step 8: Run all tests**

Run: `pytest tests/test_engine.py::TestLoopMode tests/test_integration.py::TestLoopModeE2E -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add src/bettercast/engine.py src/bettercast/ui/app.py src/bettercast/ui/progress.py tests/test_engine.py tests/test_integration.py
git commit -m "feat: add loop mode toggled with l key"
```

---

### Task 3: Idle Time Compression

**Files:**
- Modify: `src/bettercast/engine.py`
- Modify: `src/bettercast/cli.py`
- Modify: `tests/test_engine.py`
- Modify: `tests/test_integration.py`
- Modify: `tests/test_cli.py`
- Create: `tests/fixtures/idle_gaps.cast`

- [ ] **Step 1: Create test fixture with idle gaps**

Create `tests/fixtures/idle_gaps.cast`:

```
{"version": 2, "width": 80, "height": 24}
[0.5, "o", "$ "]
[1.0, "o", "echo start\r\n"]
[1.5, "o", "start\r\n$ "]
[6.0, "o", "echo after gap\r\n"]
[6.5, "o", "after gap\r\n$ "]
[7.0, "o", "echo end\r\n"]
[7.5, "o", "end\r\n$ "]
```

This has a 4.5s gap between t=1.5 and t=6.0, which exceeds the default 2.0s threshold.

- [ ] **Step 2: Write failing unit tests**

Add to `tests/test_engine.py`:

```python
class TestIdleCompression:
    def _make_idle_recording(self):
        """Recording with a 4.5s idle gap between t=1.5 and t=6.0."""
        return _make_recording([
            (0.5, "$ "),
            (1.0, "echo start\r\n"),
            (1.5, "start\r\n$ "),
            (6.0, "echo after gap\r\n"),
            (6.5, "after gap\r\n$ "),
            (7.0, "echo end\r\n"),
            (7.5, "end\r\n$ "),
        ])

    def test_idle_threshold_defaults_to_infinity(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        assert engine.idle_threshold == float("inf")

    def test_advance_skips_idle_gap(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        engine.idle_threshold = 2.0
        engine.playing = True
        engine.seek(1.5)
        engine.playing = True
        # Advance a small amount — should skip the 4.5s gap
        changed = engine.advance(0.1)
        # Position should jump to just before the next event (6.0 - 0.5 = 5.5)
        assert engine.position >= 5.5

    def test_advance_does_not_skip_small_gap(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        engine.idle_threshold = 2.0
        engine.playing = True
        engine.seek(0.5)
        engine.playing = True
        # Gap from 0.5 to 1.0 is only 0.5s — should not skip
        engine.advance(0.1)
        assert engine.position == 0.6

    def test_no_compression_when_threshold_is_infinity(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        engine.idle_threshold = float("inf")
        engine.playing = True
        engine.seek(1.5)
        engine.playing = True
        engine.advance(0.1)
        # Should NOT skip — position advances normally
        assert engine.position == 1.6

    def test_custom_threshold(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        engine.idle_threshold = 5.0
        engine.playing = True
        engine.seek(1.5)
        engine.playing = True
        engine.advance(0.1)
        # Gap is 4.5s, threshold is 5.0 — should NOT skip
        assert engine.position == 1.6
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_engine.py::TestIdleCompression -v`
Expected: FAIL with `AttributeError: 'PlaybackEngine' object has no attribute 'idle_threshold'`

- [ ] **Step 4: Implement idle compression in engine**

In `src/bettercast/engine.py`, add to `__init__`:

```python
self.idle_threshold: float = float("inf")
```

Modify the `advance` method. After `virtual_dt = real_dt * self.speed` and before `target = min(...)`, add idle gap detection:

```python
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
```

Note: This implementation assumes Task 2 (loop mode) has been merged. If implementing in isolation before Task 2, use the original end-of-playback logic:

```python
        if target >= self.duration:
            self.playing = False
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_engine.py::TestIdleCompression -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Write failing CLI tests**

Add to `tests/test_cli.py`:

```python
class TestIdleCompressionFlags:
    def test_idle_threshold_flag(self):
        runner = CliRunner()
        with patch("bettercast.cli.BettercastApp.run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--idle-threshold", "3.0"])
        assert result.exit_code == 0

    def test_no_idle_compress_flag(self):
        runner = CliRunner()
        with patch("bettercast.cli.BettercastApp.run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--no-idle-compress"])
        assert result.exit_code == 0

    def test_idle_threshold_sets_engine_value(self):
        runner = CliRunner()
        constructed_apps = []
        original_init = None

        def capture_init(self, engine):
            constructed_apps.append(engine)
            original_init(self, engine)

        from bettercast.ui.app import BettercastApp
        original_init = BettercastApp.__init__

        with patch.object(BettercastApp, "__init__", capture_init), \
             patch.object(BettercastApp, "run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--idle-threshold", "3.0"])

        assert result.exit_code == 0
        engine = constructed_apps[0]
        assert engine.idle_threshold == 3.0

    def test_no_idle_compress_sets_infinity(self):
        runner = CliRunner()
        constructed_apps = []
        original_init = None

        def capture_init(self, engine):
            constructed_apps.append(engine)
            original_init(self, engine)

        from bettercast.ui.app import BettercastApp
        original_init = BettercastApp.__init__

        with patch.object(BettercastApp, "__init__", capture_init), \
             patch.object(BettercastApp, "run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--no-idle-compress"])

        assert result.exit_code == 0
        engine = constructed_apps[0]
        assert engine.idle_threshold == float("inf")
```

- [ ] **Step 7: Implement CLI flags**

Modify `src/bettercast/cli.py`:

```python
@click.command()
@click.argument("cast_file", type=click.Path(exists=True, path_type=Path))
@click.option("--speed", default=1.0, type=float, help="Initial playback speed (default: 1.0)")
@click.option("--idle-threshold", default=2.0, type=float, help="Skip idle gaps longer than this (seconds, default: 2.0)")
@click.option("--no-idle-compress", is_flag=True, default=False, help="Disable idle time compression")
def main(cast_file: Path, speed: float, idle_threshold: float, no_idle_compress: bool) -> None:
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
    engine.idle_threshold = float("inf") if no_idle_compress else idle_threshold

    app = BettercastApp(engine)
    app.run()
```

- [ ] **Step 8: Run all tests**

Run: `pytest tests/test_engine.py::TestIdleCompression tests/test_cli.py::TestIdleCompressionFlags -v`
Expected: All tests PASS

- [ ] **Step 9: Write E2E integration test**

Add to `tests/test_integration.py`:

```python
class TestIdleCompressionE2E:
    @pytest.mark.asyncio
    async def test_idle_gap_is_compressed_during_playback(self):
        """Play a recording with a >2s gap and verify playback compresses it."""
        from bettercast.formats.v2 import V2Parser
        from pathlib import Path
        parser = V2Parser()
        recording = parser.parse(Path(__file__).parent / "fixtures" / "idle_gaps.cast")
        engine = PlaybackEngine(recording)
        engine.idle_threshold = 2.0
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            engine.seek(1.4)
            engine.playing = True
            # Wait for a few ticks — the 4.5s gap should be compressed
            await pilot.pause(delay=0.3)
            # Position should have jumped past the gap
            assert engine.position > 5.0
```

- [ ] **Step 10: Run full test suite**

Run: `pytest tests/test_engine.py::TestIdleCompression tests/test_cli.py::TestIdleCompressionFlags tests/test_integration.py::TestIdleCompressionE2E -v`
Expected: All tests PASS

- [ ] **Step 11: Commit**

```bash
git add src/bettercast/engine.py src/bettercast/cli.py tests/test_engine.py tests/test_cli.py tests/test_integration.py tests/fixtures/idle_gaps.cast
git commit -m "feat: add idle time compression with --idle-threshold flag"
```

---

## Group B: UI Features (Parallel with Group A)

### Task 4: Auto-Restart at End

**Files:**
- Modify: `src/bettercast/ui/app.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Write failing integration tests**

Add to `tests/test_integration.py`:

```python
class TestAutoRestartE2E:
    @pytest.mark.asyncio
    async def test_space_restarts_from_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            # Seek to end
            await pilot.press("end")
            assert engine.position == 4.0
            assert engine.playing is False
            # Press space — should restart from beginning
            await pilot.press("space")
            assert engine.position == 0.0
            assert engine.playing is True

    @pytest.mark.asyncio
    async def test_space_at_middle_just_toggles(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")  # seek to 4.0 (clamped from +5)
            await pilot.press("left")   # seek back to 0.0 (clamped from -5)
            # Not at end, so space should just toggle
            await pilot.press("space")
            assert engine.playing is True
            assert engine.position == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_integration.py::TestAutoRestartE2E -v`
Expected: FAIL — `test_space_restarts_from_end` will fail because space at the end doesn't seek to 0.

- [ ] **Step 3: Implement auto-restart in app.py**

Modify `action_toggle_play` in `src/bettercast/ui/app.py`:

```python
def action_toggle_play(self) -> None:
    if self.query_one("#search", SearchOverlay).display:
        return
    if not self.engine.playing and self.engine.position >= self.engine.duration:
        self.engine.seek(0.0)
        self._refresh_display()
    self.engine.toggle()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_integration.py::TestAutoRestartE2E -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Run existing playback tests to check for regressions**

Run: `pytest tests/test_integration.py::TestPlaybackFlow tests/test_app.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/bettercast/ui/app.py tests/test_integration.py
git commit -m "feat: auto-restart playback from end when pressing Space"
```

---

### Task 5: Jump to Timestamp

**Files:**
- Create: `src/bettercast/ui/timestamp.py`
- Modify: `src/bettercast/ui/app.py`
- Modify: `tests/test_overlays.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Write failing unit tests for TimestampOverlay**

Add to `tests/test_overlays.py`:

```python
from bettercast.ui.timestamp import TimestampOverlay, parse_timestamp


class TestTimestampParsing:
    def test_parse_mm_ss(self):
        assert parse_timestamp("01:30") == 90.0

    def test_parse_h_mm_ss(self):
        assert parse_timestamp("1:01:30") == 3690.0

    def test_parse_ss_only(self):
        assert parse_timestamp("45") == 45.0

    def test_parse_invalid_returns_none(self):
        assert parse_timestamp("abc") is None

    def test_parse_empty_returns_none(self):
        assert parse_timestamp("") is None

    def test_parse_negative_returns_none(self):
        assert parse_timestamp("-1:00") is None


class TestTimestampOverlay:
    def test_default_display_is_none(self):
        assert "display: none" in TimestampOverlay.DEFAULT_CSS

    def test_has_dismiss_action(self):
        overlay = TimestampOverlay()
        assert hasattr(overlay, "action_dismiss")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_overlays.py::TestTimestampParsing -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bettercast.ui.timestamp'`

- [ ] **Step 3: Create TimestampOverlay widget**

Create `src/bettercast/ui/timestamp.py`:

```python
from __future__ import annotations

from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, Static


def parse_timestamp(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    parts = value.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if any(n < 0 for n in nums):
        return None
    if len(nums) == 1:
        return nums[0]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


class TimestampOverlay(Horizontal):
    DEFAULT_CSS = """
    TimestampOverlay {
        dock: bottom;
        height: 1;
        display: none;
        background: $surface;
    }
    TimestampOverlay Static {
        width: auto;
        padding: 0 1;
    }
    TimestampOverlay Input {
        width: 1fr;
        border: none;
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    def compose(self):
        yield Static("Go to:")
        yield Input(placeholder="MM:SS or H:MM:SS")

    def action_dismiss(self) -> None:
        self.query_one(Input).value = ""
        self.display = False
        self.app.query_one("#terminal").focus()
```

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `pytest tests/test_overlays.py::TestTimestampParsing tests/test_overlays.py::TestTimestampOverlay -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Write failing integration tests**

Add to `tests/test_integration.py`:

```python
from bettercast.ui.timestamp import TimestampOverlay


class TestJumpToTimestampE2E:
    @pytest.mark.asyncio
    async def test_g_opens_timestamp_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            ts = app.query_one("#timestamp", TimestampOverlay)
            assert ts.display is False
            await pilot.press("g")
            assert ts.display is True

    @pytest.mark.asyncio
    async def test_submit_valid_timestamp_seeks(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("g")
            ts_input = app.query_one("#timestamp", TimestampOverlay).query_one(Input)
            ts_input.value = "00:03"
            await pilot.press("enter")
            assert engine.position == 3.0

    @pytest.mark.asyncio
    async def test_submit_invalid_timestamp_closes_without_seeking(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("g")
            ts_input = app.query_one("#timestamp", TimestampOverlay).query_one(Input)
            ts_input.value = "abc"
            await pilot.press("enter")
            assert engine.position == 0.0
            ts = app.query_one("#timestamp", TimestampOverlay)
            assert ts.display is False

    @pytest.mark.asyncio
    async def test_escape_dismisses_timestamp_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("g")
            ts = app.query_one("#timestamp", TimestampOverlay)
            assert ts.display is True
            await pilot.press("escape")
            assert ts.display is False

    @pytest.mark.asyncio
    async def test_focus_returns_to_terminal_after_submit(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("g")
            ts_input = app.query_one("#timestamp", TimestampOverlay).query_one(Input)
            ts_input.value = "00:02"
            await pilot.press("enter")
            await pilot.pause()
            terminal = app.query_one("#terminal", TerminalDisplay)
            assert terminal.has_focus
```

- [ ] **Step 6: Wire up TimestampOverlay in app.py**

In `src/bettercast/ui/app.py`, add the import:

```python
from bettercast.ui.timestamp import TimestampOverlay, parse_timestamp
```

Add to `compose`:

```python
yield TimestampOverlay(id="timestamp")
```

Add to `BINDINGS`:

```python
Binding("g", "open_timestamp", "Go to time"),
```

Add action and handler methods:

```python
def action_open_timestamp(self) -> None:
    ts = self.query_one("#timestamp", TimestampOverlay)
    if ts.display:
        return
    ts.display = True
    ts_input = ts.query_one(Input)
    ts_input.value = ""
    ts_input.focus()
```

Modify `on_input_submitted` to handle both search and timestamp inputs. Replace the existing method:

```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    # Determine which overlay the input belongs to
    search = self.query_one("#search", SearchOverlay)
    timestamp = self.query_one("#timestamp", TimestampOverlay)

    if timestamp.display:
        timestamp.display = False
        self._terminal.focus()
        parsed = parse_timestamp(event.value)
        if parsed is not None:
            self.engine.seek(parsed)
            self._refresh_display()
        return

    # Original search handling
    self._search_query = event.value
    search.display = False
    self._terminal.focus()
    if self._search_query:
        match_time = self.engine.next_match(self._search_query)
        if match_time is not None:
            self.engine.seek(match_time)
            self._refresh_display()
```

Also update `on_input_changed` to only update match count when search is visible:

```python
def on_input_changed(self, event: Input.Changed) -> None:
    search = self.query_one("#search", SearchOverlay)
    if search.display:
        count = self.engine.count_matches(event.value)
        search.update_match_count(count)
```

- [ ] **Step 7: Run all tests**

Run: `pytest tests/test_overlays.py::TestTimestampParsing tests/test_overlays.py::TestTimestampOverlay tests/test_integration.py::TestJumpToTimestampE2E -v`
Expected: All tests PASS

- [ ] **Step 8: Run existing tests to check for regressions**

Run: `pytest tests/test_integration.py::TestSearchWorkflow tests/test_integration.py::TestSearchEdgeCases -v`
Expected: All PASS (search still works correctly)

- [ ] **Step 9: Commit**

```bash
git add src/bettercast/ui/timestamp.py src/bettercast/ui/app.py tests/test_overlays.py tests/test_integration.py
git commit -m "feat: add jump-to-timestamp overlay with g key"
```

---

## Group C: Cross-Cutting Features (After Groups A & B merge)

### Task 6: Bookmarks

**Files:**
- Modify: `src/bettercast/engine.py`
- Create: `src/bettercast/ui/bookmarks.py`
- Modify: `src/bettercast/ui/app.py`
- Modify: `src/bettercast/ui/progress.py`
- Modify: `tests/test_engine.py`
- Modify: `tests/test_overlays.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Write failing unit tests for bookmark engine methods**

Add to `tests/test_engine.py`:

```python
class TestBookmarks:
    def test_bookmarks_initially_empty(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.bookmarks == []

    def test_add_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.5)
        assert len(engine.bookmarks) == 1
        assert engine.bookmarks[0] == (1.5, "Bookmark 1")

    def test_add_bookmark_with_label(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.5, "interesting part")
        assert engine.bookmarks[0] == (1.5, "interesting part")

    def test_add_bookmark_auto_labels_increment(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.0)
        engine.add_bookmark(2.0)
        engine.add_bookmark(3.0)
        assert engine.bookmarks[0][1] == "Bookmark 1"
        assert engine.bookmarks[1][1] == "Bookmark 2"
        assert engine.bookmarks[2][1] == "Bookmark 3"

    def test_remove_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.0)
        engine.add_bookmark(2.0)
        engine.remove_bookmark(0)
        assert len(engine.bookmarks) == 1
        assert engine.bookmarks[0] == (2.0, "Bookmark 2")

    def test_remove_bookmark_invalid_index_is_noop(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.0)
        engine.remove_bookmark(5)
        assert len(engine.bookmarks) == 1

    def test_next_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.0)
        engine.add_bookmark(3.0)
        result = engine.next_bookmark(0.5)
        assert result == 1.0

    def test_next_bookmark_skips_current(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.0)
        engine.add_bookmark(3.0)
        result = engine.next_bookmark(1.0)
        assert result == 3.0

    def test_next_bookmark_returns_none_past_all(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.0)
        result = engine.next_bookmark(2.0)
        assert result is None

    def test_prev_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.0)
        engine.add_bookmark(3.0)
        result = engine.prev_bookmark(3.5)
        assert result == 3.0

    def test_prev_bookmark_skips_current(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(1.0)
        engine.add_bookmark(3.0)
        result = engine.prev_bookmark(3.0)
        assert result == 1.0

    def test_prev_bookmark_returns_none_before_all(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(2.0)
        result = engine.prev_bookmark(1.0)
        assert result is None

    def test_bookmarks_sorted_by_time(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.add_bookmark(3.0)
        engine.add_bookmark(1.0)
        engine.add_bookmark(2.0)
        times = [t for t, _ in engine.bookmarks]
        assert times == [1.0, 2.0, 3.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py::TestBookmarks -v`
Expected: FAIL with `AttributeError: 'PlaybackEngine' object has no attribute 'bookmarks'`

- [ ] **Step 3: Implement bookmark methods in engine**

Add to `src/bettercast/engine.py` in `__init__`:

```python
self.bookmarks: list[tuple[float, str]] = []
self._bookmark_counter: int = 0
```

Add methods after `count_matches`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine.py::TestBookmarks -v`
Expected: All 14 tests PASS

- [ ] **Step 5: Create BookmarkOverlay widget**

Create `src/bettercast/ui/bookmarks.py`:

```python
from __future__ import annotations

from textual.binding import Binding
from textual.widgets import Static


class BookmarkOverlay(Static):
    DEFAULT_CSS = """
    BookmarkOverlay {
        layer: overlay;
        display: none;
        content-align: center middle;
        width: 100%;
        height: 100%;
        background: $surface 80%;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("d", "delete_selected", "Delete", show=False),
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("enter", "select_bookmark", "Select", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected: int = 0
        self._bookmarks: list[tuple[float, str]] = []

    def update_bookmarks(self, bookmarks: list[tuple[float, str]]) -> None:
        self._bookmarks = list(bookmarks)
        if self._selected >= len(self._bookmarks):
            self._selected = max(0, len(self._bookmarks) - 1)
        self._render_list()

    def _render_list(self) -> None:
        if not self._bookmarks:
            self.update("No bookmarks yet.\n\nPress Escape to close.")
            return
        lines = ["┌─── Bookmarks ────────────────────┐"]
        for i, (time, label) in enumerate(self._bookmarks):
            m, s = divmod(int(time), 60)
            h, m = divmod(m, 60)
            if h > 0:
                ts = f"{h}:{m:02d}:{s:02d}"
            else:
                ts = f"{m:02d}:{s:02d}"
            marker = "▶" if i == self._selected else " "
            lines.append(f"│ {marker} {ts}  {label:<20s} │")
        lines.append("├──────────────────────────────────┤")
        lines.append("│ Enter: jump  d: delete  Esc: close│")
        lines.append("└──────────────────────────────────┘")
        self.update("\n".join(lines))

    def action_dismiss(self) -> None:
        self.display = False
        self.app.query_one("#terminal").focus()

    def action_move_up(self) -> None:
        if self._bookmarks and self._selected > 0:
            self._selected -= 1
            self._render_list()

    def action_move_down(self) -> None:
        if self._bookmarks and self._selected < len(self._bookmarks) - 1:
            self._selected += 1
            self._render_list()

    def action_select_bookmark(self) -> None:
        if self._bookmarks and 0 <= self._selected < len(self._bookmarks):
            time, _ = self._bookmarks[self._selected]
            self.display = False
            self.app.query_one("#terminal").focus()
            self.app.engine.seek(time)
            self.app._refresh_display()

    def action_delete_selected(self) -> None:
        if self._bookmarks and 0 <= self._selected < len(self._bookmarks):
            self.app.engine.remove_bookmark(self._selected)
            self.update_bookmarks(self.app.engine.bookmarks)
```

- [ ] **Step 6: Write unit tests for BookmarkOverlay**

Add to `tests/test_overlays.py`:

```python
from bettercast.ui.bookmarks import BookmarkOverlay


class TestBookmarkOverlay:
    def test_default_display_is_none(self):
        assert "display: none" in BookmarkOverlay.DEFAULT_CSS

    def test_has_dismiss_action(self):
        overlay = BookmarkOverlay()
        assert hasattr(overlay, "action_dismiss")

    def test_update_bookmarks_stores_list(self):
        overlay = BookmarkOverlay()
        bookmarks = [(1.0, "Bookmark 1"), (3.0, "Bookmark 2")]
        overlay.update_bookmarks(bookmarks)
        assert overlay._bookmarks == bookmarks

    def test_selected_index_clamps(self):
        overlay = BookmarkOverlay()
        overlay._selected = 5
        overlay.update_bookmarks([(1.0, "only one")])
        assert overlay._selected == 0

    def test_move_up_decrements(self):
        overlay = BookmarkOverlay()
        overlay.update_bookmarks([(1.0, "a"), (2.0, "b")])
        overlay._selected = 1
        overlay.action_move_up()
        assert overlay._selected == 0

    def test_move_down_increments(self):
        overlay = BookmarkOverlay()
        overlay.update_bookmarks([(1.0, "a"), (2.0, "b")])
        overlay._selected = 0
        overlay.action_move_down()
        assert overlay._selected == 1

    def test_move_up_clamps_at_zero(self):
        overlay = BookmarkOverlay()
        overlay.update_bookmarks([(1.0, "a")])
        overlay._selected = 0
        overlay.action_move_up()
        assert overlay._selected == 0

    def test_move_down_clamps_at_end(self):
        overlay = BookmarkOverlay()
        overlay.update_bookmarks([(1.0, "a")])
        overlay._selected = 0
        overlay.action_move_down()
        assert overlay._selected == 0
```

- [ ] **Step 7: Run unit tests**

Run: `pytest tests/test_overlays.py::TestBookmarkOverlay tests/test_engine.py::TestBookmarks -v`
Expected: All PASS

- [ ] **Step 8: Wire up bookmarks in app.py**

Add imports to `src/bettercast/ui/app.py`:

```python
from bettercast.ui.bookmarks import BookmarkOverlay
```

Add to `compose`:

```python
yield BookmarkOverlay(id="bookmarks")
```

Add to `BINDINGS`:

```python
Binding("m", "add_bookmark", "Bookmark"),
Binding("b", "open_bookmarks", "Bookmarks list"),
Binding("left_curly_bracket", "prev_bookmark", "Prev bookmark"),
Binding("right_curly_bracket", "next_bookmark_jump", "Next bookmark"),
```

Add action methods:

```python
def action_add_bookmark(self) -> None:
    self.engine.add_bookmark(self.engine.position)

def action_open_bookmarks(self) -> None:
    bm = self.query_one("#bookmarks", BookmarkOverlay)
    if bm.display:
        return
    bm.update_bookmarks(self.engine.bookmarks)
    bm.display = True
    bm.focus()

def action_prev_bookmark(self) -> None:
    time = self.engine.prev_bookmark(self.engine.position)
    if time is not None:
        self.engine.seek(time)
        self._refresh_display()

def action_next_bookmark_jump(self) -> None:
    time = self.engine.next_bookmark(self.engine.position)
    if time is not None:
        self.engine.seek(time)
        self._refresh_display()
```

- [ ] **Step 9: Update progress bar to show bookmark markers**

In `src/bettercast/ui/progress.py`, add a new reactive property:

```python
bookmark_times: reactive[list[float]] = reactive(list, always_update=True)
```

Modify `render` to show bookmark markers. Replace the bar rendering block:

```python
        if bar_width > 0 and self.duration > 0:
            ratio = min(self.position / self.duration, 1.0)
            filled = int(bar_width * ratio)
            remaining = bar_width - filled
            bar = "\u2501" * filled + "\u2500" * remaining
        else:
            bar = ""
```

with:

```python
        if bar_width > 0 and self.duration > 0:
            ratio = min(self.position / self.duration, 1.0)
            filled = int(bar_width * ratio)
            remaining = bar_width - filled
            bar_chars = list("\u2501" * filled + "\u2500" * remaining)
            # Overlay bookmark markers
            for bm_time in self.bookmark_times:
                bm_pos = int(bar_width * min(bm_time / self.duration, 1.0))
                if 0 <= bm_pos < len(bar_chars):
                    bar_chars[bm_pos] = "\u2502"
            bar = "".join(bar_chars)
        else:
            bar = ""
```

Add this line to `_tick` in `app.py`, after the existing progress bar updates:

```python
self._progress_bar.bookmark_times = [t for t, _ in self.engine.bookmarks]
```

- [ ] **Step 10: Write E2E integration tests**

Add to `tests/test_integration.py`:

```python
from bettercast.ui.bookmarks import BookmarkOverlay


class TestBookmarksE2E:
    @pytest.mark.asyncio
    async def test_m_adds_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")  # seek to 4.0
            await pilot.press("m")
            assert len(engine.bookmarks) == 1
            assert engine.bookmarks[0][0] == 4.0

    @pytest.mark.asyncio
    async def test_b_opens_bookmark_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("m")  # add a bookmark first
            bm = app.query_one("#bookmarks", BookmarkOverlay)
            assert bm.display is False
            await pilot.press("b")
            assert bm.display is True

    @pytest.mark.asyncio
    async def test_bookmark_jump_via_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            # Add bookmark at position 2.0
            await pilot.press("right")  # seek to 4.0
            await pilot.press("left")   # seek back to 0.0
            engine.add_bookmark(2.0)
            # Open overlay and select
            await pilot.press("b")
            await pilot.press("enter")
            assert engine.position == 2.0

    @pytest.mark.asyncio
    async def test_curly_braces_jump_between_bookmarks(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            engine.add_bookmark(1.0)
            engine.add_bookmark(3.0)
            engine.seek(0.0)
            # Jump to next bookmark
            await pilot.press("right_curly_bracket")
            assert engine.position == 1.0
            await pilot.press("right_curly_bracket")
            assert engine.position == 3.0

    @pytest.mark.asyncio
    async def test_prev_bookmark_jump(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            engine.add_bookmark(1.0)
            engine.add_bookmark(3.0)
            engine.seek(4.0)
            await pilot.press("left_curly_bracket")
            assert engine.position == 3.0
            await pilot.press("left_curly_bracket")
            assert engine.position == 1.0

    @pytest.mark.asyncio
    async def test_delete_bookmark_from_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            engine.add_bookmark(1.0)
            engine.add_bookmark(2.0)
            await pilot.press("b")
            await pilot.press("d")  # delete first bookmark
            assert len(engine.bookmarks) == 1
            assert engine.bookmarks[0][0] == 2.0

    @pytest.mark.asyncio
    async def test_escape_closes_bookmark_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            engine.add_bookmark(1.0)
            await pilot.press("b")
            bm = app.query_one("#bookmarks", BookmarkOverlay)
            assert bm.display is True
            await pilot.press("escape")
            assert bm.display is False
```

- [ ] **Step 11: Run all bookmark tests**

Run: `pytest tests/test_engine.py::TestBookmarks tests/test_overlays.py::TestBookmarkOverlay tests/test_integration.py::TestBookmarksE2E -v`
Expected: All PASS

- [ ] **Step 12: Commit**

```bash
git add src/bettercast/engine.py src/bettercast/ui/bookmarks.py src/bettercast/ui/app.py src/bettercast/ui/progress.py tests/test_engine.py tests/test_overlays.py tests/test_integration.py
git commit -m "feat: add bookmark system with m/b/{/} keys"
```

---

### Task 7: Copy Terminal Text

**Files:**
- Modify: `src/bettercast/ui/app.py`
- Modify: `src/bettercast/ui/progress.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Write failing integration tests**

Add to `tests/test_integration.py`:

```python
import subprocess


class TestCopyTextE2E:
    @pytest.mark.asyncio
    async def test_c_copies_screen_text(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            # Seek to a position with visible text
            await pilot.press("right")  # seek to 4.0
            # Press c to copy
            with patch("subprocess.run") as mock_run:
                await pilot.press("c")
                mock_run.assert_called_once()
                # Verify pbcopy/xclip was called with screen text
                call_args = mock_run.call_args
                assert call_args[0][0][0] in ("pbcopy", "xclip", "xsel")

    @pytest.mark.asyncio
    async def test_c_sends_screen_content_to_clipboard(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")  # seek to 4.0 — has "Python 3.12.0"
            captured_input = []

            def fake_run(cmd, input=None, **kwargs):
                captured_input.append(input)

            with patch("subprocess.run", side_effect=fake_run):
                await pilot.press("c")

            assert len(captured_input) == 1
            assert "Python 3.12.0" in captured_input[0]

    @pytest.mark.asyncio
    async def test_c_shows_flash_message(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            with patch("subprocess.run"):
                await pilot.press("c")
                await pilot.pause()
                progress = app.query_one("#progress", PlaybackProgressBar)
                assert progress.flash_message == "Copied!"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_integration.py::TestCopyTextE2E -v`
Expected: FAIL — no `c` binding, no `flash_message` attribute.

- [ ] **Step 3: Add flash message support to progress bar**

In `src/bettercast/ui/progress.py`, add a reactive property:

```python
flash_message: reactive[str] = reactive("")
```

Modify `render` to show flash message when present. Replace the final return:

```python
        return Text(f"{prefix}{bar}{suffix}")
```

with:

```python
        if self.flash_message:
            return Text(f"{prefix}{bar} {self.flash_message} ")
        return Text(f"{prefix}{bar}{suffix}")
```

- [ ] **Step 4: Add copy action to app.py**

Add import at top of `src/bettercast/ui/app.py`:

```python
import platform
import subprocess
```

Add to `BINDINGS`:

```python
Binding("c", "copy_text", "Copy"),
```

Add action method:

```python
def action_copy_text(self) -> None:
    screen = self.engine.screen
    lines = []
    for row in range(screen.lines):
        line_chars = []
        for col in range(screen.columns):
            char = screen.buffer[row][col]
            line_chars.append(char.data if char.data else " ")
        lines.append("".join(line_chars).rstrip())
    text = "\n".join(lines).rstrip() + "\n"

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
        else:
            subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return

    self._progress_bar.flash_message = "Copied!"
    self.set_timer(1.0, self._clear_flash)

def _clear_flash(self) -> None:
    self._progress_bar.flash_message = ""
```

- [ ] **Step 5: Run all tests**

Run: `pytest tests/test_integration.py::TestCopyTextE2E -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Run full regression suite**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/bettercast/ui/app.py src/bettercast/ui/progress.py tests/test_integration.py
git commit -m "feat: add copy terminal text to clipboard with c key"
```

---

## Group D: Integration

### Task 8: Update Help Overlay

**Files:**
- Modify: `src/bettercast/ui/help.py`
- Modify: `tests/test_overlays.py`

- [ ] **Step 1: Write failing test for new keybindings in help**

Add to `tests/test_overlays.py` in `TestHelpOverlay`:

```python
    def test_help_text_has_new_bindings(self):
        assert ". / ," in HELP_TEXT or "Step" in HELP_TEXT
        assert "l" in HELP_TEXT
        assert "g" in HELP_TEXT
        assert "m" in HELP_TEXT
        assert "b" in HELP_TEXT
        assert "{ / }" in HELP_TEXT
        assert "c" in HELP_TEXT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_overlays.py::TestHelpOverlay::test_help_text_has_new_bindings -v`
Expected: FAIL

- [ ] **Step 3: Update help text**

Replace `HELP_TEXT` in `src/bettercast/ui/help.py`:

```python
HELP_TEXT = """\
┌─── Keybindings ──────────────────┐
│ Space       Play/Pause           │
│ ← / →      Seek ±5s             │
│ Shift+←/→  Seek ±30s            │
│ [ / ]      Speed -/+ 0.5x       │
│ Home/End   Start/End             │
│ . / ,      Step forward/back     │
│ l          Toggle loop mode      │
│ g          Go to timestamp       │
│ /          Search                │
│ n / N      Next/Prev match       │
│ m          Add bookmark          │
│ b          Bookmark list         │
│ { / }      Prev/Next bookmark    │
│ c          Copy screen text      │
│ ?          Toggle help           │
│ q          Quit                  │
└──────────────────────────────────┘"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_overlays.py::TestHelpOverlay -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite as final regression check**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/bettercast/ui/help.py tests/test_overlays.py
git commit -m "feat: update help overlay with all new keybindings"
```

---

## Parallel Execution Map

```
Time →
────────────────────────────────────────────────────

Group A (worktrees):
  Task 1: Frame Stepping     ████████
  Task 2: Loop Mode          ████████
  Task 3: Idle Compression   ██████████████

Group B (worktrees):
  Task 4: Auto-Restart       ████
  Task 5: Jump to Timestamp  ██████████

                              ── merge A & B ──

Group C (worktrees):
  Task 6: Bookmarks                    ██████████████
  Task 7: Copy Text                    ████████

                              ── merge C ──

Group D:
  Task 8: Help Overlay                            ████
```

Tasks within each group run in parallel. Groups A and B run in parallel with each other. Group C starts after A and B are merged. Group D is a quick final task after all merges.
