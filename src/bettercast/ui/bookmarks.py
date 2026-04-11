from __future__ import annotations

from textual.binding import Binding
from textual.widgets import Static


class BookmarkOverlay(Static, can_focus=True):
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
        lines = ["\u250c\u2500\u2500\u2500 Bookmarks \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510"]
        for i, (time, label) in enumerate(self._bookmarks):
            m, s = divmod(int(time), 60)
            h, m = divmod(m, 60)
            if h > 0:
                ts = f"{h}:{m:02d}:{s:02d}"
            else:
                ts = f"{m:02d}:{s:02d}"
            marker = "\u25b6" if i == self._selected else " "
            lines.append(f"\u2502 {marker} {ts}  {label:<20s} \u2502")
        lines.append("\u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524")
        lines.append("\u2502 Enter: jump  d: delete  Esc: close\u2502")
        lines.append("\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518")
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
