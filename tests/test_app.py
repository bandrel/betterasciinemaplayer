import pytest

from bettercast.engine import PlaybackEngine
from bettercast.ui.app import BettercastApp
from bettercast.ui.help import HelpOverlay
from bettercast.ui.progress import PlaybackProgressBar
from bettercast.ui.search import SearchOverlay
from bettercast.ui.terminal import TerminalDisplay


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
