from __future__ import annotations

from textual.widgets import Static


HELP_TEXT = """\
┌─── Keybindings ──────────────────┐
│ Space       Play/Pause           │
│ ← / →      Seek ±5s             │
│ Shift+←/→  Seek ±30s            │
│ [ / ]      Speed -/+ 0.5x       │
│ Home/End   Start/End             │
│ . / ,      Step forward/back     │
│ l          Toggle loop mode      │
│ g          Go to timestamp       │
│ /          Search                │
│ n/N or ↑/↓ Next/Prev match       │
│ m          Add bookmark          │
│ b          Bookmark list         │
│ { / }      Prev/Next bookmark    │
│ c          Copy screen text      │
│ ?          Toggle HUD            │
│ q          Quit                  │
└──────────────────────────────────┘"""


class HelpOverlay(Static):
    DEFAULT_CSS = """
    HelpOverlay {
        layer: overlay;
        display: none;
        dock: right;
        width: 38;
        height: auto;
        max-height: 100%;
        background: $surface 85%;
        padding: 0;
    }
    """

    def render(self) -> str:
        return HELP_TEXT
