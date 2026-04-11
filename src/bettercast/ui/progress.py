from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static
from rich.text import Text


def format_time(seconds: float) -> str:
    total = int(seconds)
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class PlaybackProgressBar(Static):
    DEFAULT_CSS = """
    PlaybackProgressBar {
        height: 1;
        dock: bottom;
        background: $surface;
    }
    """

    position = reactive(0.0)
    duration = reactive(0.0)
    speed = reactive(1.0)
    playing = reactive(False)
    looping = reactive(False)
    bookmark_times: reactive[list[float]] = reactive(list, always_update=True)

    def render(self) -> Text:
        play_icon = "\u25b6" if self.playing else "\u23f8"
        loop_icon = " \u27f3" if self.looping else ""
        icon = f"{play_icon}{loop_icon}"
        current = format_time(self.position)
        total = format_time(self.duration)
        speed_str = f"{self.speed:.1f}x"

        prefix = f" {icon} {current} / {total} "
        suffix = f" {speed_str} "
        bar_width = max(0, self.size.width - len(prefix) - len(suffix))

        if bar_width > 0 and self.duration > 0:
            ratio = min(self.position / self.duration, 1.0)
            filled = int(bar_width * ratio)
            remaining = bar_width - filled
            bar_chars = list("\u2501" * filled + "\u2500" * remaining)
            for bm_time in self.bookmark_times:
                bm_pos = int(bar_width * min(bm_time / self.duration, 1.0))
                if 0 <= bm_pos < len(bar_chars):
                    bar_chars[bm_pos] = "\u2502"
            bar = "".join(bar_chars)
        else:
            bar = ""

        return Text(f"{prefix}{bar}{suffix}")
