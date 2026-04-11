from __future__ import annotations

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


_style_cache: dict[tuple, Style] = {}


def char_to_style(char) -> Style:
    key = (char.fg, char.bg, char.bold, char.italics, char.underscore, char.strikethrough, char.reverse)
    style = _style_cache.get(key)
    if style is not None:
        return style
    fg = pyte_color_to_rich(char.fg)
    bg = pyte_color_to_rich(char.bg)
    style = Style(
        color=fg,
        bgcolor=bg,
        bold=char.bold if char.bold else None,
        italic=char.italics if char.italics else None,
        underline=char.underscore if char.underscore else None,
        strike=char.strikethrough if char.strikethrough else None,
        reverse=char.reverse if char.reverse else None,
    )
    _style_cache[key] = style
    return style


class TerminalDisplay(Static, can_focus=True):
    DEFAULT_CSS = """
    TerminalDisplay {
        height: 1fr;
        overflow: hidden;
    }
    """

    def render_engine_screen(self, engine: PlaybackEngine) -> Text:
        screen = engine.screen
        visible_cols = min(screen.columns, self.size.width) if self.size.width > 0 else screen.columns
        visible_rows = min(screen.lines, self.size.height) if self.size.height > 0 else screen.lines
        # Show the bottom portion of the screen (most relevant for TUI apps)
        start_row = max(0, screen.lines - visible_rows)
        output = Text()
        for row in range(start_row, screen.lines):
            if row > start_row:
                output.append("\n")
            for col in range(visible_cols):
                char = screen.buffer[row][col]
                try:
                    style = char_to_style(char)
                except Exception:
                    style = Style()
                if char.data:
                    output.append(char.data, style=style)
        return output

    def update_from_engine(self, engine: PlaybackEngine) -> None:
        content = self.render_engine_screen(engine)
        self.update(content)
