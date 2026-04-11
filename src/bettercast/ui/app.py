from __future__ import annotations

import platform
import subprocess

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, Static
from textual.worker import Worker, WorkerState

from bettercast.engine import PlaybackEngine
from bettercast.ui.bookmarks import BookmarkOverlay
from bettercast.ui.help import HelpOverlay
from bettercast.ui.keyhints import KeyHintBar
from bettercast.ui.progress import PlaybackProgressBar
from bettercast.ui.search import SearchOverlay
from bettercast.ui.terminal import TerminalDisplay
from bettercast.ui.timestamp import TimestampOverlay, parse_timestamp


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
        Binding("down", "next_match", "Next match", show=False),
        Binding("up", "prev_match", "Prev match", show=False),
        Binding("full_stop", "step_forward", "Step forward"),
        Binding("comma", "step_backward", "Step backward"),
        Binding("l", "toggle_loop", "Loop"),
        Binding("g", "open_timestamp", "Go to time"),
        Binding("m", "add_bookmark", "Bookmark"),
        Binding("b", "open_bookmarks", "Bookmarks list"),
        Binding("left_curly_bracket", "prev_bookmark", "Prev bookmark"),
        Binding("right_curly_bracket", "next_bookmark_jump", "Next bookmark"),
        Binding("c", "copy_text", "Copy"),
        Binding("question_mark", "toggle_help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, engine: PlaybackEngine) -> None:
        super().__init__()
        self.engine = engine
        self._search_query: str = ""

    def compose(self) -> ComposeResult:
        yield TerminalDisplay(id="terminal")
        yield BookmarkOverlay(id="bookmarks")
        yield KeyHintBar(id="keyhints")
        yield PlaybackProgressBar(id="progress")
        yield SearchOverlay(id="search")
        yield TimestampOverlay(id="timestamp")
        yield HelpOverlay(id="help")

    def on_mount(self) -> None:
        self._terminal = self.query_one("#terminal", TerminalDisplay)
        self._search_worker = self.run_worker(self.engine.build_search_index, thread=True)
        self._search_ready = False
        self._refresh_display()
        self._progress_bar = self.query_one("#progress", PlaybackProgressBar)
        self._progress_bar.duration = self.engine.duration
        self._timer = self.set_interval(1 / 30, self._tick)
        self._terminal.focus()

    def _tick(self) -> None:
        changed = self.engine.advance(1 / 30)
        if changed:
            self._refresh_display()
        if not self._search_ready:
            self._progress_bar.flash_message = "Indexing..."
        self._progress_bar.position = self.engine.position
        self._progress_bar.playing = self.engine.playing
        self._progress_bar.speed = self.engine.speed
        self._progress_bar.looping = self.engine.looping
        self._progress_bar.bookmark_times = [t for t, _ in self.engine.bookmarks]

    def _refresh_display(self) -> None:
        self._terminal.update_from_engine(self.engine)

    def on_resize(self, event) -> None:
        terminal = self.query_one("#terminal", TerminalDisplay)
        w = terminal.size.width
        h = terminal.size.height
        if w > 0 and h > 0:
            self.engine.resize(w, h)
            self._refresh_display()

    # --- Playback actions ---

    def action_toggle_play(self) -> None:
        if self.query_one("#search", SearchOverlay).display:
            return
        if not self.engine.playing and self.engine.position >= self.engine.duration:
            self.engine.seek(0.0)
            self._refresh_display()
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

    def action_step_forward(self) -> None:
        self.engine.step_forward()
        self._refresh_display()

    def action_step_backward(self) -> None:
        self.engine.step_backward()
        self._refresh_display()

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

    def action_open_timestamp(self) -> None:
        ts = self.query_one("#timestamp", TimestampOverlay)
        if ts.display:
            return
        ts.display = True
        ts_input = ts.query_one(Input)
        ts_input.value = ""
        ts_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
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
            if not self._search_ready:
                label = search.query_one("#match-count", Static)
                label.update("[indexing...]")
            else:
                count = self.engine.count_matches(event.value)
                search.update_match_count(count)

    def action_toggle_loop(self) -> None:
        self.engine.looping = not self.engine.looping

    # --- Bookmarks ---

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

    # --- Worker events ---

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS and not self._search_ready:
            self._search_ready = True
            if self._progress_bar.flash_message == "Indexing...":
                self._progress_bar.flash_message = ""
            # Update match count if search overlay is open
            search = self.query_one("#search", SearchOverlay)
            if search.display:
                search_input = search.query_one(Input)
                count = self.engine.count_matches(search_input.value)
                search.update_match_count(count)

    # --- Help ---

    def action_toggle_help(self) -> None:
        help_overlay = self.query_one("#help", HelpOverlay)
        help_overlay.display = not help_overlay.display

    # --- Copy ---

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
