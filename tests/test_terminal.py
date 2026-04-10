import pyte
from rich.style import Style

from bettercast.engine import PlaybackEngine
from bettercast.ui.terminal import TerminalDisplay, pyte_color_to_rich, char_to_style


class TestPyteColorConversion:
    def test_default_returns_none(self):
        assert pyte_color_to_rich("default") is None

    def test_named_color_passes_through(self):
        assert pyte_color_to_rich("red") == "red"

    def test_256_color_index(self):
        assert pyte_color_to_rich("196") == "color(196)"

    def test_hex_color(self):
        assert pyte_color_to_rich("ff5500") == "#ff5500"


class TestCharToStyle:
    def test_default_char(self):
        char = pyte.screens.Char(" ")
        style = char_to_style(char)
        assert style == Style()

    def test_bold_char(self):
        char = pyte.screens.Char("x", bold=True)
        style = char_to_style(char)
        assert style.bold is True


class TestTerminalDisplay:
    def test_render_from_engine(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        widget = TerminalDisplay()
        content = widget.render_engine_screen(engine)
        plain = content.plain
        assert "echo hello" in plain
        assert "hello" in plain
