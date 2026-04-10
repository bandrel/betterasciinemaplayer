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


def char_to_style(char) -> Style:
    fg = pyte_color_to_rich(char.fg)
    bg = pyte_color_to_rich(char.bg)
    return Style(
        color=fg,
        bgcolor=bg,
        bold=char.bold if char.bold else None,
        italic=char.italics if char.italics else None,
        underline=char.underscore if char.underscore else None,
        strike=char.strikethrough if char.strikethrough else None,
        reverse=char.reverse if char.reverse else None,
    )


class TerminalDisplay(Static):
    DEFAULT_CSS = """
    TerminalDisplay {
        height: 1fr;
        overflow: hidden;
    }
    """

    def render_engine_screen(self, engine: PlaybackEngine) -> Text:
        screen = engine.screen
        output = Text()
        for row in range(screen.lines):
            if row > 0:
                output.append("\n")
            for col in range(screen.columns):
                char = screen.buffer[row][col]
                style = char_to_style(char)
                output.append(char.data, style=style)
        return output

    def update_from_engine(self, engine: PlaybackEngine) -> None:
        content = self.render_engine_screen(engine)
        self.update(content)
