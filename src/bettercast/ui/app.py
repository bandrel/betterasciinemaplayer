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
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("left", "seek_back", "Seek -5s"),
        Binding("right", "seek_forward", "Seek +5s"),
        Binding("shift+left", "seek_back_far", "Seek -30s"),
        Binding("shift+right", "seek_forward_far", "Seek +30s"),
        Binding("left_square_bracket", "speed_down", "Speed -0.5x"),
        Binding("right_square_bracket", "speed_up", "Speed +0.5x"),
        Binding("home", "seek_start", "Start"),
        Binding("end", "seek_end", "End"),
        Binding("slash", "open_search", "Search"),
        Binding("n", "next_match", "Next match"),
        Binding("N", "prev_match", "Prev match"),
        Binding("l", "toggle_loop", "Loop"),
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
        self._terminal = self.query_one("#terminal", TerminalDisplay)
        self.run_worker(self.engine.build_search_index, thread=True)
        self._refresh_display()
        self._progress_bar = self.query_one("#progress", PlaybackProgressBar)
        self._progress_bar.duration = self.engine.duration
        self._timer = self.set_interval(1 / 30, self._tick)
        self._terminal.focus()

    def _tick(self) -> None:
        changed = self.engine.advance(1 / 30)
        if changed:
            self._refresh_display()
        self._progress_bar.position = self.engine.position
        self._progress_bar.playing = self.engine.playing
        self._progress_bar.speed = self.engine.speed
        self._progress_bar.looping = self.engine.looping

    def _refresh_display(self) -> None:
        self._terminal.update_from_engine(self.engine)

    # --- Playback actions ---

    def action_toggle_play(self) -> None:
        if self.query_one("#search", SearchOverlay).display:
            return
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
        if search.display:
            return
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
        self._terminal.focus()
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

    def action_toggle_loop(self) -> None:
        self.engine.looping = not self.engine.looping

    # --- Help ---

    def action_toggle_help(self) -> None:
        help_overlay = self.query_one("#help", HelpOverlay)
        help_overlay.display = not help_overlay.display
