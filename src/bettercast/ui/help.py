from __future__ import annotations

from textual.widgets import Static


HELP_TEXT = """\
┌─── Keybindings ──────────────────┐
│ Space       Play/Pause           │
│ ← / →      Seek ±5s             │
│ Shift+←/→  Seek ±30s            │
│ [ / ]      Speed -/+ 0.5x       │
│ Home/End   Start/End             │
│ /          Search                │
│ n / N      Next/Prev match      │
│ ?          Toggle help           │
│ q          Quit                  │
└──────────────────────────────────┘"""


class HelpOverlay(Static):
    DEFAULT_CSS = """
    HelpOverlay {
        layer: overlay;
        display: none;
        content-align: center middle;
        width: 100%;
        height: 100%;
        background: $surface 80%;
    }
    """

    def render(self) -> str:
        return HELP_TEXT
