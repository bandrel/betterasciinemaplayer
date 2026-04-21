"""Tests for AltScreen — alternate screen buffer support."""

import pyte

from bettercast.terminal import AltScreen


class TestAltScreenEnterLeave:
    def test_enter_alt_screen_clears_display(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Hello main")
        assert "Hello main" in screen.display[0]
        stream.feed("\x1b[?1049h")
        assert screen.display[0].strip() == ""

    def test_leave_alt_screen_restores_main(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Hello main")
        stream.feed("\x1b[?1049h")
        stream.feed("Alt content")
        stream.feed("\x1b[?1049l")
        assert "Hello main" in screen.display[0]

    def test_alt_screen_content_not_visible_after_leave(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Main")
        stream.feed("\x1b[?1049h")
        stream.feed("SECRET ALT TEXT")
        stream.feed("\x1b[?1049l")
        full_display = "\n".join(screen.display)
        assert "SECRET ALT TEXT" not in full_display

    def test_in_alt_screen_flag(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        assert screen._in_alt_screen is False
        stream.feed("\x1b[?1049h")
        assert screen._in_alt_screen is True
        stream.feed("\x1b[?1049l")
        assert screen._in_alt_screen is False

    def test_double_enter_is_noop(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Main content")
        stream.feed("\x1b[?1049h")
        stream.feed("Alt content")
        stream.feed("\x1b[?1049h")  # second enter
        assert "Alt content" in screen.display[0]  # content preserved

    def test_double_leave_is_noop(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Main content")
        stream.feed("\x1b[?1049h")
        stream.feed("\x1b[?1049l")
        assert "Main content" in screen.display[0]
        stream.feed("\x1b[?1049l")  # second leave
        assert "Main content" in screen.display[0]


class TestAltScreenMode47:
    def test_mode_47_enters_alt_screen(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Main")
        stream.feed("\x1b[?47h")
        assert screen._in_alt_screen is True
        assert screen.display[0].strip() == ""

    def test_mode_47_leaves_alt_screen(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Main")
        stream.feed("\x1b[?47h")
        stream.feed("\x1b[?47l")
        assert screen._in_alt_screen is False
        assert "Main" in screen.display[0]


class TestAltScreenMode1047:
    def test_mode_1047_enters_alt_screen(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Main")
        stream.feed("\x1b[?1047h")
        assert screen._in_alt_screen is True

    def test_mode_1047_leaves_alt_screen(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Main")
        stream.feed("\x1b[?1047h")
        stream.feed("\x1b[?1047l")
        assert "Main" in screen.display[0]


class TestAltScreenCursorSaveRestore:
    def test_mode_1049_saves_and_restores_cursor(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[5;10H")  # move cursor to row 5, col 10
        saved_x, saved_y = screen.cursor.x, screen.cursor.y
        stream.feed("\x1b[?1049h")
        stream.feed("\x1b[1;1H")  # move cursor in alt screen
        assert screen.cursor.x != saved_x or screen.cursor.y != saved_y
        stream.feed("\x1b[?1049l")
        assert screen.cursor.x == saved_x
        assert screen.cursor.y == saved_y

    def test_mode_47_does_not_restore_cursor(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[5;10H")
        stream.feed("\x1b[?47h")
        stream.feed("\x1b[1;1H")  # move in alt screen
        stream.feed("\x1b[?47l")
        # Cursor should NOT be restored for mode 47
        assert screen.cursor.x == 0
        assert screen.cursor.y == 0


class TestAltScreenReset:
    def test_reset_clears_alt_state(self):
        screen = AltScreen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[?1049h")
        assert screen._in_alt_screen is True
        screen.reset()
        assert screen._in_alt_screen is False
        assert screen._alt_buffer is None
        assert screen._alt_cursor is None


class TestAltScreenWithEngine:
    def test_engine_renders_alt_screen_content(self):
        """TUI app enters alt screen — engine should show alt screen content."""
        from bettercast.engine import PlaybackEngine
        from bettercast.formats.base import CastHeader, Event, Recording

        header = CastHeader(version=2, width=80, height=24, duration=3.0)
        events = [
            Event(time=0.5, type="o", data="$ "),
            Event(time=1.0, type="o", data="\x1b[?1049h"),  # enter alt screen
            Event(time=1.5, type="o", data="\x1b[2;5HTUI App Title"),  # write in alt
            Event(time=2.0, type="o", data="\x1b[?1049l"),  # leave alt screen
            Event(time=2.5, type="o", data="back to main\r\n"),
        ]
        recording = Recording(header=header, events=events)
        engine = PlaybackEngine(recording)

        # At t=1.5, should see alt screen content
        engine.seek(1.5)
        assert "TUI App Title" in engine.screen.display[1]

        # At t=2.5, should see main screen restored
        engine.seek(2.5)
        assert "$ " in engine.screen.display[0]
        assert "back to main" in engine.screen.display[0]

    def test_seek_through_alt_screen_transition(self):
        """Seeking past alt screen enter/leave produces correct state."""
        from bettercast.engine import PlaybackEngine
        from bettercast.formats.base import CastHeader, Event, Recording

        header = CastHeader(version=2, width=80, height=24, duration=4.0)
        events = [
            Event(time=0.5, type="o", data="Main line 1\r\n"),
            Event(time=1.0, type="o", data="\x1b[?1049h"),
            Event(time=1.5, type="o", data="Alt content"),
            Event(time=2.0, type="o", data="\x1b[?1049l"),
            Event(time=2.5, type="o", data="Main line 2\r\n"),
        ]
        recording = Recording(header=header, events=events)
        engine = PlaybackEngine(recording)

        # Seek to after alt screen leave
        engine.seek(3.0)
        display = "\n".join(engine.screen.display)
        assert "Main line 1" in display
        assert "Main line 2" in display
        assert "Alt content" not in display
