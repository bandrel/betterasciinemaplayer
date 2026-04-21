from __future__ import annotations

from functools import lru_cache

from textual.widgets import Static
from rich.style import Style
from rich.text import Text

from bettercast.engine import PlaybackEngine


def pyte_color_to_rich(color: str) -> str | None:
    if color == "default":
        return None
    try:
        return f"color({int(color)})"
    except ValueError:
        pass
    if len(color) == 6:
        try:
            int(color, 16)
            return f"#{color}"
        except ValueError:
            pass
    return color


@lru_cache(maxsize=2048)
def _cached_style(key: tuple) -> Style:
    fg = pyte_color_to_rich(key[0])
    bg = pyte_color_to_rich(key[1])
    return Style(
        color=fg,
        bgcolor=bg,
        bold=key[2] if key[2] else None,
        italic=key[3] if key[3] else None,
        underline=key[4] if key[4] else None,
        strike=key[5] if key[5] else None,
        reverse=key[6] if key[6] else None,
    )


def char_to_style(char) -> Style:
    key = (char.fg, char.bg, char.bold, char.italics, char.underscore, char.strikethrough, char.reverse)
    return _cached_style(key)


def _render_row(screen, row: int) -> Text:
    """Render a single row from the pyte screen buffer to a Rich Text."""
    row_text = Text()
    for col in range(screen.columns):
        char = screen.buffer[row][col]
        try:
            style = char_to_style(char)
        except Exception:
            style = Style()
        if char.data:
            row_text.append(char.data, style=style)
    return row_text


class TerminalDisplay(Static, can_focus=True):
    DEFAULT_CSS = """
    TerminalDisplay {
        height: 1fr;
        overflow: hidden;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._row_cache: dict[int, Text] = {}
        self._last_screen_id: int | None = None

    def render_engine_screen(self, engine: PlaybackEngine) -> Text:
        screen = engine.screen
        screen_id = id(screen)

        # If the screen object changed (resize), invalidate entire cache
        if screen_id != self._last_screen_id:
            self._row_cache.clear()
            self._last_screen_id = screen_id

        # Only re-render dirty rows
        dirty = screen.dirty
        for row in dirty:
            if 0 <= row < screen.lines:
                self._row_cache[row] = _render_row(screen, row)
        dirty.clear()

        # Assemble full output from cached rows
        output = Text()
        for row in range(screen.lines):
            if row > 0:
                output.append("\n")
            cached = self._row_cache.get(row)
            if cached is not None:
                output.append_text(cached)
        return output

    def update_from_engine(self, engine: PlaybackEngine) -> None:
        content = self.render_engine_screen(engine)
        self.update(content)
