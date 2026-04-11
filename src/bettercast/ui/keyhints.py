from __future__ import annotations

from textual.widgets import Static
from rich.text import Text


class KeyHintBar(Static):
    DEFAULT_CSS = """
    KeyHintBar {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
    }
    """

    def render(self) -> Text:
        hints = "Space:play  ←→:seek  []:speed  .,: step  /:search  g:goto  m:mark  b:bookmarks  c:copy  ?:help  q:quit"
        return Text(f" {hints}", style="dim")
