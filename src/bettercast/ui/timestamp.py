from __future__ import annotations

from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, Static


def parse_timestamp(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    parts = value.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if any(n < 0 for n in nums):
        return None
    if len(nums) == 1:
        return nums[0]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


class TimestampOverlay(Horizontal):
    DEFAULT_CSS = """
    TimestampOverlay {
        dock: bottom;
        height: 1;
        display: none;
        background: #333333;
        color: #ffffff;
    }
    TimestampOverlay Static {
        width: auto;
        padding: 0 1;
        color: #aaaaaa;
    }
    TimestampOverlay Input {
        width: 1fr;
        border: none;
        padding: 0;
        background: #333333;
        color: #ffffff;
    }
    TimestampOverlay Input:focus {
        border: none;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    def compose(self):
        yield Static("Go to:")
        yield Input(placeholder="MM:SS or H:MM:SS")

    def action_dismiss(self) -> None:
        self.query_one(Input).value = ""
        self.display = False
        self.app.query_one("#terminal").focus()
