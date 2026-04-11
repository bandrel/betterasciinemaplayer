from __future__ import annotations

from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, Static


class SearchOverlay(Horizontal):
    DEFAULT_CSS = """
    SearchOverlay {
        layer: overlay;
        dock: bottom;
        height: 1;
        display: none;
        background: $surface;
    }
    SearchOverlay Input {
        width: 1fr;
        border: none;
        padding: 0;
    }
    SearchOverlay #match-count {
        width: auto;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close search", show=False),
    ]

    def compose(self):
        yield Input(placeholder="Search...")
        yield Static("", id="match-count")

    def update_match_count(self, count: int) -> None:
        label = self.query_one("#match-count", Static)
        if count > 0:
            label.update(f"[{count} matches]")
        else:
            label.update("[no matches]")

    def action_dismiss(self) -> None:
        self.query_one(Input).value = ""
        self.display = False
        self.app.query_one("#terminal").focus()
