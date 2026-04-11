"""Visual regression tests using Textual SVG screenshots.

Each test renders the app at a specific state and compares the SVG
screenshot against a saved reference. If the reference doesn't exist,
it's created automatically (first run). On subsequent runs, differences
are flagged as test failures.

To update references after intentional UI changes:
    rm tests/snapshots/*.svg
    pytest tests/test_screenshots.py
"""

import asyncio
from pathlib import Path

import pytest

from bettercast.engine import PlaybackEngine
from bettercast.formats.v2 import V2Parser
from bettercast.ui.app import BettercastApp
from bettercast.ui.search import SearchOverlay
from bettercast.ui.help import HelpOverlay
from bettercast.ui.bookmarks import BookmarkOverlay
from bettercast.ui.timestamp import TimestampOverlay
from textual.widgets import Input

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def _wait_for_workers(app, timeout=2.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while app.workers and asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.05)


def _compare_snapshot(name: str, svg: str) -> None:
    """Compare SVG against saved reference. Create reference if missing."""
    ref_path = SNAPSHOTS_DIR / f"{name}.svg"
    if not ref_path.exists():
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(svg)
        pytest.skip(f"Reference snapshot created: {ref_path}")
    reference = ref_path.read_text()
    assert svg == reference, (
        f"Screenshot '{name}' differs from reference.\n"
        f"To update: rm {ref_path} && pytest tests/test_screenshots.py::{name}"
    )


class TestScreenshots:
    """Visual regression tests comparing SVG screenshots to references."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """App at startup — paused at position 0, terminal empty."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("initial_state", svg)

    @pytest.mark.asyncio
    async def test_playing_at_middle(self):
        """Seeked to middle of recording — terminal has content."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("right")  # seek +5s, clamps to 4.0
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("seeked_to_end", svg)

    @pytest.mark.asyncio
    async def test_search_overlay_open(self):
        """Search overlay visible with query typed."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "hello"
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("search_open", svg)

    @pytest.mark.asyncio
    async def test_help_hud_visible(self):
        """Help HUD panel toggled on."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("question_mark")
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("help_hud", svg)

    @pytest.mark.asyncio
    async def test_timestamp_overlay_open(self):
        """Timestamp jump overlay visible."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("g")
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("timestamp_open", svg)

    @pytest.mark.asyncio
    async def test_bookmark_overlay_open(self):
        """Bookmark list overlay with bookmarks."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            # Add bookmarks then open list
            engine.add_bookmark(1.0)
            engine.add_bookmark(3.0)
            await pilot.press("b")
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("bookmarks_open", svg)

    @pytest.mark.asyncio
    async def test_playing_state(self):
        """Playing state — play icon visible in progress bar."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("space")
            await pilot.pause(delay=0.15)
            await pilot.press("space")  # pause to freeze state
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("after_play_pause", svg)

    @pytest.mark.asyncio
    async def test_loop_mode_indicator(self):
        """Loop mode on — loop icon visible in progress bar."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("l")
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("loop_mode_on", svg)

    @pytest.mark.asyncio
    async def test_speed_changed(self):
        """Speed increased — speed indicator shows 2.0x."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("right_square_bracket")
            await pilot.press("right_square_bracket")
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("speed_2x", svg)

    @pytest.mark.asyncio
    async def test_frame_stepped(self):
        """Frame stepped forward twice — specific terminal content."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("full_stop")
            await pilot.press("full_stop")
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("frame_stepped", svg)

    @pytest.mark.asyncio
    async def test_bookmark_markers_on_progress_bar(self):
        """Progress bar shows bookmark markers."""
        recording = V2Parser().parse(FIXTURES_DIR / "sample.cast")
        engine = PlaybackEngine(recording)
        app = BettercastApp(engine)
        async with app.run_test(size=(80, 24)) as pilot:
            engine.add_bookmark(1.0)
            engine.add_bookmark(2.5)
            engine.add_bookmark(3.5)
            # Trigger progress bar update
            app._sync_bookmark_times()
            await pilot.pause(delay=0.1)
            svg = app.export_screenshot()
            _compare_snapshot("bookmark_markers", svg)
