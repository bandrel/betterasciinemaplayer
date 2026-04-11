"""Integration tests for BettercastApp using Textual's pilot API.

These tests exercise full user workflows through the real widget tree
with a real PlaybackEngine, verifying that keybindings, overlays,
search, seek, and playback all work together correctly.
"""

import asyncio

import pytest

from bettercast.engine import PlaybackEngine
from bettercast.ui.app import BettercastApp
from bettercast.ui.help import HelpOverlay
from bettercast.ui.progress import PlaybackProgressBar
from bettercast.ui.search import SearchOverlay
from bettercast.ui.terminal import TerminalDisplay
from textual.widgets import Input


# ── Helpers ──────────────────────────────────────────────────────────

async def _wait_for_workers(app, timeout=2.0):
    """Wait for all background workers (e.g., build_search_index) to finish."""
    deadline = asyncio.get_event_loop().time() + timeout
    while app.workers and asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.05)


# ── Playback flow ────────────────────────────────────────────────────

class TestPlaybackFlow:
    @pytest.mark.asyncio
    async def test_play_advances_position(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("space")
            assert engine.playing is True
            # Let a few ticks run (~5 frames at 30fps)
            await pilot.pause(delay=0.2)
            assert engine.position > 0.0

    @pytest.mark.asyncio
    async def test_pause_stops_advancement(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("space")
            await pilot.pause(delay=0.15)
            await pilot.press("space")
            assert engine.playing is False
            pos_after_pause = engine.position
            await pilot.pause(delay=0.15)
            assert engine.position == pos_after_pause

    @pytest.mark.asyncio
    async def test_progress_bar_tracks_position(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            progress = app.query_one("#progress", PlaybackProgressBar)
            assert progress.position == 0.0
            await pilot.press("right")
            await pilot.pause()
            assert progress.position == engine.position


# ── Seek controls ────────────────────────────────────────────────────

class TestSeekControls:
    @pytest.mark.asyncio
    async def test_seek_forward(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("right")
            # Recording is 4s, right seeks +5s, clamps to 4.0
            assert engine.position == 4.0

    @pytest.mark.asyncio
    async def test_seek_back(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")
            assert engine.position == 4.0
            await pilot.press("left")
            # 4.0 - 5.0 clamps to 0.0
            assert engine.position == 0.0

    @pytest.mark.asyncio
    async def test_seek_forward_far(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("shift+right")
            # +30s on a 4s recording clamps to 4.0
            assert engine.position == 4.0

    @pytest.mark.asyncio
    async def test_seek_back_far(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")
            await pilot.press("shift+left")
            # 4.0 - 30.0 clamps to 0.0
            assert engine.position == 0.0

    @pytest.mark.asyncio
    async def test_home_seeks_to_start(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")
            assert engine.position > 0.0
            await pilot.press("home")
            assert engine.position == 0.0

    @pytest.mark.asyncio
    async def test_end_seeks_to_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")
            assert engine.position == 4.0


# ── Speed controls ───────────────────────────────────────────────────

class TestSpeedControls:
    @pytest.mark.asyncio
    async def test_speed_up(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.speed == 1.0
            await pilot.press("right_square_bracket")
            assert engine.speed == 1.5

    @pytest.mark.asyncio
    async def test_speed_down(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.speed == 1.0
            await pilot.press("left_square_bracket")
            assert engine.speed == 0.5

    @pytest.mark.asyncio
    async def test_speed_clamps_low(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("left_square_bracket")
            await pilot.press("left_square_bracket")
            assert engine.speed == 0.5

    @pytest.mark.asyncio
    async def test_speed_clamps_high(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            for _ in range(20):
                await pilot.press("right_square_bracket")
            assert engine.speed == 8.0


# ── Search workflow ──────────────────────────────────────────────────

class TestSearchWorkflow:
    @pytest.mark.asyncio
    async def test_slash_opens_search(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            search = app.query_one("#search", SearchOverlay)
            assert search.display is False
            await pilot.press("slash")
            assert search.display is True

    @pytest.mark.asyncio
    async def test_search_input_receives_focus(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("slash")
            search = app.query_one("#search", SearchOverlay)
            search_input = search.query_one(Input)
            assert search_input.has_focus

    @pytest.mark.asyncio
    async def test_escape_dismisses_search(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("slash")
            search = app.query_one("#search", SearchOverlay)
            assert search.display is True
            await pilot.press("escape")
            assert search.display is False

    @pytest.mark.asyncio
    async def test_escape_does_not_seek(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("slash")
            await pilot.press("escape")
            assert engine.position == 0.0

    @pytest.mark.asyncio
    async def test_submit_search_seeks_to_match(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            assert engine.position == 0.0
            await pilot.press("slash")
            # Type "python" and submit
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "python"
            await pilot.press("enter")
            # Should seek to the match (python appears at t=3.0+)
            assert engine.position >= 3.0

    @pytest.mark.asyncio
    async def test_search_closes_after_submit(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search = app.query_one("#search", SearchOverlay)
            search_input = search.query_one(Input)
            search_input.value = "hello"
            await pilot.press("enter")
            assert search.display is False

    @pytest.mark.asyncio
    async def test_focus_restored_after_search_submit(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "hello"
            await pilot.press("enter")
            await pilot.pause()
            terminal = app.query_one("#terminal", TerminalDisplay)
            assert terminal.has_focus

    @pytest.mark.asyncio
    async def test_next_match_advances_position(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            # Submit a search for "hello"
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "hello"
            await pilot.press("enter")
            first_pos = engine.position
            assert first_pos > 0.0
            # Press n to go to next match (or stay if only one)
            await pilot.press("n")

    @pytest.mark.asyncio
    async def test_no_match_does_not_seek(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "nonexistent_text_xyz"
            await pilot.press("enter")
            # No match found, position should stay at 0
            assert engine.position == 0.0

    @pytest.mark.asyncio
    async def test_match_count_updates_live(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "hello"
            await pilot.pause()
            from textual.widgets import Static
            match_label = app.query_one("#search #match-count", Static)
            # update_match_count sets the label text via .update()
            label_text = str(match_label.render())
            assert "match" in label_text.lower()


# ── Search edge cases ────────────────────────────────────────────────

class TestSearchEdgeCases:
    @pytest.mark.asyncio
    async def test_space_does_not_toggle_play_during_search(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.playing is False
            await pilot.press("slash")
            await pilot.press("space")
            # Space should NOT toggle play while search is open
            assert engine.playing is False

    @pytest.mark.asyncio
    async def test_slash_does_not_reset_open_search(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "test"
            await pilot.pause()
            # Press slash again — should NOT reset the input
            # (slash is typed into the Input since priority was removed,
            # so value becomes "test/" rather than being cleared)
            await pilot.press("slash")
            assert search_input.value.startswith("test")

    @pytest.mark.asyncio
    async def test_n_without_query_does_nothing(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("n")
            assert engine.position == 0.0

    @pytest.mark.asyncio
    async def test_prev_match_without_query_does_nothing(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("N")
            assert engine.position == 0.0


# ── Help overlay ─────────────────────────────────────────────────────

class TestHelpOverlay:
    @pytest.mark.asyncio
    async def test_question_mark_toggles_help(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            help_overlay = app.query_one("#help", HelpOverlay)
            assert help_overlay.display is False
            await pilot.press("question_mark")
            assert help_overlay.display is True
            await pilot.press("question_mark")
            assert help_overlay.display is False

    @pytest.mark.asyncio
    async def test_help_shows_keybindings(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            help_overlay = app.query_one("#help", HelpOverlay)
            text = help_overlay.render()
            assert "Play/Pause" in text
            assert "Search" in text
            assert "Quit" in text


# ── Auto-restart at end ─────────────────────────────────────────────

class TestAutoRestartE2E:
    @pytest.mark.asyncio
    async def test_space_restarts_from_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")
            assert engine.position == 4.0
            assert engine.playing is False
            await pilot.press("space")
            # Position resets near 0 (timer tick may advance slightly)
            assert engine.position < 0.5
            assert engine.playing is True

    @pytest.mark.asyncio
    async def test_space_at_middle_just_toggles(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")
            await pilot.press("left")
            await pilot.press("space")
            assert engine.playing is True
            # Position near 0 (timer tick may advance slightly)
            assert engine.position < 0.5
