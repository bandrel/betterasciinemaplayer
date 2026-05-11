import pytest

from bettercast.engine import PlaybackEngine
from bettercast.ui.app import BettercastApp
from bettercast.ui.help import HelpOverlay
from bettercast.ui.progress import PlaybackProgressBar
from bettercast.ui.search import SearchOverlay
from bettercast.ui.terminal import TerminalDisplay
from bettercast.ui.toast import ConfirmationToast


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

    @pytest.mark.asyncio
    async def test_app_mounts_confirmation_toast(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test():
            assert app.query_one("#toast", ConfirmationToast)

    @pytest.mark.asyncio
    async def test_question_mark_shows_toast_first(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            help_overlay = app.query_one("#help", HelpOverlay)
            toast = app.query_one("#toast", ConfirmationToast)
            assert help_overlay.display is False
            assert toast.is_pending is False
            await pilot.press("question_mark")
            assert toast.is_pending is True
            assert toast.display is True
            assert help_overlay.display is False

    @pytest.mark.asyncio
    async def test_second_question_mark_opens_help(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            help_overlay = app.query_one("#help", HelpOverlay)
            toast = app.query_one("#toast", ConfirmationToast)
            await pilot.press("question_mark")
            await pilot.press("question_mark")
            assert help_overlay.display is True
            assert toast.is_pending is False
            assert toast.display is False

    @pytest.mark.asyncio
    async def test_question_mark_closes_open_help(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        app = BettercastApp(engine)
        async with app.run_test() as pilot:
            help_overlay = app.query_one("#help", HelpOverlay)
            toast = app.query_one("#toast", ConfirmationToast)
            help_overlay.display = True
            await pilot.press("question_mark")
            assert help_overlay.display is False
            assert toast.is_pending is False
