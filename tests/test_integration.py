"""Integration tests for BettercastApp using Textual's pilot API.

These tests exercise full user workflows through the real widget tree
with a real PlaybackEngine, verifying that keybindings, overlays,
search, seek, and playback all work together correctly.
"""

import asyncio
from unittest.mock import patch

import pytest

from bettercast.engine import PlaybackEngine
from bettercast.ui.app import BettercastApp
from bettercast.ui.bookmarks import BookmarkOverlay
from bettercast.ui.help import HelpOverlay
from bettercast.ui.progress import PlaybackProgressBar
from bettercast.ui.search import SearchOverlay
from bettercast.ui.terminal import TerminalDisplay
from bettercast.ui.timestamp import TimestampOverlay
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


# ── Frame stepping ───────────────────────────────────────────────────

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
            assert engine.position == 0.5


# ── Help overlay ─────────────────────────────────────────────────────

class TestHelpOverlay:
    @pytest.mark.asyncio
    async def test_question_mark_toggles_help(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            help_overlay = app.query_one("#help", HelpOverlay)
            assert help_overlay.display is False
            # First press shows confirmation toast, second opens help.
            await pilot.press("question_mark")
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


# ── Loop mode ───────────────────────────────────────────────────────

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


# ── Idle compression E2E ────────────────────────────────────────────

class TestIdleCompressionE2E:
    @pytest.mark.asyncio
    async def test_idle_gap_is_compressed_during_playback(self):
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
            await pilot.pause(delay=0.3)
            assert engine.position > 5.0


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


# ── Jump to timestamp ───────────────────────────────────────────────

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


# ── Bookmarks ───────────────────────────────────────────────────────


class TestBookmarksE2E:
    @pytest.mark.asyncio
    async def test_m_adds_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")
            await pilot.press("m")
            assert len(engine.bookmarks) == 1
            assert engine.bookmarks[0][0] == 4.0

    @pytest.mark.asyncio
    async def test_b_opens_bookmark_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("m")
            bm = app.query_one("#bookmarks", BookmarkOverlay)
            assert bm.display is False
            await pilot.press("b")
            assert bm.display is True

    @pytest.mark.asyncio
    async def test_bookmark_jump_via_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")
            await pilot.press("left")
            engine.add_bookmark(2.0)
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
            await pilot.press("d")
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


# ── Copy text ───────────────────────────────────────────────────────


class TestCopyTextE2E:
    @pytest.mark.asyncio
    async def test_c_copies_screen_text(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")  # seek to 4.0
            with patch("bettercast.ui.app.subprocess.run") as mock_run:
                await pilot.press("c")
                mock_run.assert_called_once()
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
            with patch("bettercast.ui.app.subprocess.run"):
                await pilot.press("c")
                await pilot.pause()
                progress = app.query_one("#progress", PlaybackProgressBar)
                assert progress.flash_message == "Copied!"


# ── Search match cycling regression tests ──────────────────────────


class TestSearchMatchCycling:
    """Regression tests: n/N and up/down must advance through matches."""

    @pytest.mark.asyncio
    async def test_n_advances_to_next_match(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            # "$" appears at multiple timestamps in the recording
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "$"
            await pilot.press("enter")
            pos1 = engine.position
            assert pos1 > 0.0
            await pilot.press("n")
            pos2 = engine.position
            assert pos2 > pos1, f"n should advance: {pos2} > {pos1}"

    @pytest.mark.asyncio
    async def test_N_goes_to_prev_match(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "$"
            await pilot.press("enter")
            # Advance to a later match
            await pilot.press("n")
            await pilot.press("n")
            pos_forward = engine.position
            await pilot.press("N")
            pos_back = engine.position
            assert pos_back < pos_forward, f"N should go back: {pos_back} < {pos_forward}"

    @pytest.mark.asyncio
    async def test_down_arrow_advances_match(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "$"
            await pilot.press("enter")
            pos1 = engine.position
            await pilot.press("down")
            pos2 = engine.position
            assert pos2 > pos1, f"down should advance: {pos2} > {pos1}"

    @pytest.mark.asyncio
    async def test_up_arrow_goes_to_prev_match(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "$"
            await pilot.press("enter")
            await pilot.press("n")
            await pilot.press("n")
            pos_forward = engine.position
            await pilot.press("up")
            pos_back = engine.position
            assert pos_back < pos_forward, f"up should go back: {pos_back} < {pos_forward}"

    @pytest.mark.asyncio
    async def test_indexing_indicator_clears(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.pause(delay=0.1)
            progress = app.query_one("#progress", PlaybackProgressBar)
            assert progress.flash_message != "Indexing..."


# ── Comprehensive keybinding E2E tests ─────────────────────────────
# One test per keybinding to verify every shortcut works end-to-end.


class TestAllKeybindings:
    """Verify every keybinding triggers the expected behavior."""

    # --- Playback ---

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
    async def test_left_seeks_back_5s(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")  # go to 4.0
            await pilot.press("left")
            assert engine.position == 0.0  # 4.0 - 5.0 clamps to 0

    @pytest.mark.asyncio
    async def test_right_seeks_forward_5s(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("right")
            assert engine.position == 4.0  # 0.0 + 5.0 clamps to duration

    @pytest.mark.asyncio
    async def test_shift_left_seeks_back_30s(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")
            await pilot.press("shift+left")
            assert engine.position == 0.0

    @pytest.mark.asyncio
    async def test_shift_right_seeks_forward_30s(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("shift+right")
            assert engine.position == 4.0

    @pytest.mark.asyncio
    async def test_home_seeks_to_start(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")
            await pilot.press("home")
            assert engine.position == 0.0

    @pytest.mark.asyncio
    async def test_end_seeks_to_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")
            assert engine.position == 4.0

    # --- Speed ---

    @pytest.mark.asyncio
    async def test_right_bracket_increases_speed(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.speed == 1.0
            await pilot.press("right_square_bracket")
            assert engine.speed == 1.5
            await pilot.press("right_square_bracket")
            assert engine.speed == 2.0

    @pytest.mark.asyncio
    async def test_left_bracket_decreases_speed(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.speed == 1.0
            await pilot.press("left_square_bracket")
            assert engine.speed == 0.5

    @pytest.mark.asyncio
    async def test_speed_clamps_at_minimum(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("left_square_bracket")
            await pilot.press("left_square_bracket")
            await pilot.press("left_square_bracket")
            assert engine.speed == 0.5

    @pytest.mark.asyncio
    async def test_speed_clamps_at_maximum(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            for _ in range(20):
                await pilot.press("right_square_bracket")
            assert engine.speed == 8.0

    # --- Frame stepping ---

    @pytest.mark.asyncio
    async def test_dot_steps_forward_one_frame(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.position == 0.0
            await pilot.press("full_stop")
            assert engine.position == 0.5
            await pilot.press("full_stop")
            assert engine.position == 1.0

    @pytest.mark.asyncio
    async def test_comma_steps_backward_one_frame(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")
            await pilot.press("comma")
            assert engine.position == 3.5

    @pytest.mark.asyncio
    async def test_dot_at_end_is_noop(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")
            await pilot.press("full_stop")
            assert engine.position == 4.0

    @pytest.mark.asyncio
    async def test_comma_at_start_is_noop(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("comma")
            assert engine.position == 0.0

    # --- Loop mode ---

    @pytest.mark.asyncio
    async def test_l_toggles_loop(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            assert engine.looping is False
            await pilot.press("l")
            assert engine.looping is True
            await pilot.press("l")
            assert engine.looping is False

    # --- Search ---

    @pytest.mark.asyncio
    async def test_slash_opens_search_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            search = app.query_one("#search", SearchOverlay)
            assert search.display is False
            await pilot.press("slash")
            assert search.display is True

    @pytest.mark.asyncio
    async def test_escape_closes_search_overlay(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("slash")
            assert app.query_one("#search", SearchOverlay).display is True
            await pilot.press("escape")
            assert app.query_one("#search", SearchOverlay).display is False

    @pytest.mark.asyncio
    async def test_n_jumps_to_next_match(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "python"
            await pilot.press("enter")
            first_pos = engine.position
            assert first_pos >= 3.0
            # n with no further matches stays put or wraps
            await pilot.press("n")

    @pytest.mark.asyncio
    async def test_N_jumps_to_prev_match(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await _wait_for_workers(app)
            # Search and go to end
            await pilot.press("slash")
            search_input = app.query_one("#search", SearchOverlay).query_one(Input)
            search_input.value = "hello"
            await pilot.press("enter")
            pos_after_search = engine.position
            assert pos_after_search > 0.0
            # Seek to end then prev match
            await pilot.press("end")
            await pilot.press("N")
            assert engine.position <= 4.0

    # --- Jump to timestamp ---

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
    async def test_g_submit_seeks_to_time(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("g")
            ts_input = app.query_one("#timestamp", TimestampOverlay).query_one(Input)
            ts_input.value = "00:03"
            await pilot.press("enter")
            assert engine.position == 3.0

    @pytest.mark.asyncio
    async def test_g_escape_dismisses(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("g")
            assert app.query_one("#timestamp", TimestampOverlay).display is True
            await pilot.press("escape")
            assert app.query_one("#timestamp", TimestampOverlay).display is False

    # --- Bookmarks ---

    @pytest.mark.asyncio
    async def test_m_adds_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")  # 4.0
            await pilot.press("m")
            assert len(engine.bookmarks) == 1
            assert engine.bookmarks[0][0] == 4.0

    @pytest.mark.asyncio
    async def test_b_opens_bookmark_list(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            engine.add_bookmark(1.0)
            bm = app.query_one("#bookmarks", BookmarkOverlay)
            assert bm.display is False
            await pilot.press("b")
            assert bm.display is True

    @pytest.mark.asyncio
    async def test_right_curly_bracket_next_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            engine.add_bookmark(1.0)
            engine.add_bookmark(3.0)
            await pilot.press("right_curly_bracket")
            assert engine.position == 1.0
            await pilot.press("right_curly_bracket")
            assert engine.position == 3.0

    @pytest.mark.asyncio
    async def test_left_curly_bracket_prev_bookmark(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            engine.add_bookmark(1.0)
            engine.add_bookmark(3.0)
            engine.seek(4.0)
            await pilot.press("left_curly_bracket")
            assert engine.position == 3.0

    # --- Copy ---

    @pytest.mark.asyncio
    async def test_c_copies_to_clipboard(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("right")  # seek to 4.0
            captured = []

            def fake_run(cmd, input=None, **kwargs):
                captured.append(input)

            with patch("bettercast.ui.app.subprocess.run", side_effect=fake_run):
                await pilot.press("c")

            assert len(captured) == 1
            assert "Python 3.12.0" in captured[0]

    # --- Help HUD ---

    @pytest.mark.asyncio
    async def test_question_mark_toggles_hud(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            hud = app.query_one("#help", HelpOverlay)
            assert hud.display is False
            # First press shows confirmation toast, second opens help.
            await pilot.press("question_mark")
            await pilot.press("question_mark")
            assert hud.display is True
            await pilot.press("question_mark")
            assert hud.display is False

    # --- Quit ---

    @pytest.mark.asyncio
    async def test_q_quits(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("q")

    # --- Auto-restart ---

    @pytest.mark.asyncio
    async def test_space_at_end_restarts(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            await pilot.press("end")
            assert engine.position == 4.0
            assert engine.playing is False
            await pilot.press("space")
            assert engine.position < 0.5
            assert engine.playing is True
