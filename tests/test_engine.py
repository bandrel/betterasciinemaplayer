from unittest.mock import PropertyMock, patch

import pyte
from pyte.screens import Char

from bettercast.engine import PlaybackEngine
from bettercast.formats.base import CastHeader, Event, Recording


class TestEngineInit:
    def test_initial_state(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.position == 0.0
        assert engine.speed == 1.0
        assert engine.playing is False
        assert engine.duration == 4.0

    def test_screen_dimensions(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.screen.columns == 80
        assert engine.screen.lines == 24


class TestEngineSeek:
    def test_seek_to_start(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.0)
        assert engine.position == 0.0
        assert engine.screen.display[0].strip() == ""

    def test_seek_to_middle(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        assert engine.position == 2.0
        assert "echo hello" in engine.screen.display[0]
        assert engine.screen.display[1].strip() == "hello"
        assert engine.screen.display[2].startswith("$ ")

    def test_seek_to_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(4.0)
        assert engine.position == 4.0
        assert "Python 3.12.0" in engine.screen.display[3]
        assert engine.screen.display[4].startswith("$ ")

    def test_seek_clamps_to_zero(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(-5.0)
        assert engine.position == 0.0

    def test_seek_clamps_to_duration(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(100.0)
        assert engine.position == 4.0

    def test_seek_resets_screen(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(4.0)
        assert "Python" in engine.screen.display[3]
        engine.seek(0.0)
        assert engine.screen.display[3].strip() == ""


class TestEngineAdvance:
    def test_advance_while_paused_returns_false(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.advance(1.0) is False
        assert engine.position == 0.0

    def test_advance_applies_events(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        changed = engine.advance(1.0)
        assert changed is True
        assert engine.position == 1.0
        assert "$ " in engine.screen.display[0]

    def test_advance_respects_speed(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.speed = 2.0
        engine.advance(1.0)
        assert engine.position == 2.0
        assert "echo hello" in engine.screen.display[0]

    def test_advance_pauses_at_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.advance(10.0)
        assert engine.playing is False
        assert engine.position == 4.0

    def test_advance_returns_false_when_no_events(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.seek(4.0)
        engine.playing = True
        changed = engine.advance(1.0)
        assert changed is False


class TestEngineControls:
    def test_play(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.play()
        assert engine.playing is True

    def test_pause(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.pause()
        assert engine.playing is False

    def test_toggle(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.toggle()
        assert engine.playing is True
        engine.toggle()
        assert engine.playing is False

    def test_set_speed(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(2.0)
        assert engine.speed == 2.0

    def test_set_speed_clamps_low(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(0.1)
        assert engine.speed == 0.5

    def test_set_speed_clamps_high(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(20.0)
        assert engine.speed == 8.0


class TestEngineSearch:
    def test_build_search_index(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert len(engine._search_index) > 0

    def test_search_index_deduplicates(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        texts = [text for _, text, _ in engine._search_index]
        assert len(texts) == len(set(texts))

    def test_next_match_finds_text(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        match_time = engine.next_match("python")
        assert match_time is not None
        assert match_time >= 3.0

    def test_next_match_case_insensitive(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        match_time = engine.next_match("HELLO")
        assert match_time is not None
        assert match_time >= 1.0

    def test_next_match_returns_none_past_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 4.1
        assert engine.next_match("hello") is None

    def test_prev_match_finds_text(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 4.0
        match_time = engine.prev_match("hello")
        assert match_time is not None
        assert match_time <= 4.0

    def test_prev_match_returns_none_at_start(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        assert engine.prev_match("hello") is None

    def test_next_match_empty_query_returns_none(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert engine.next_match("") is None

    def test_count_matches(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        count = engine.count_matches("python")
        assert count >= 1

    def test_count_matches_empty_query(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert engine.count_matches("") == 0


class TestFrameStepping:
    def test_step_forward_moves_to_next_output_event(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.0)
        engine.step_forward()
        # First output event is at t=0.5
        assert engine.position == 0.5

    def test_step_forward_skips_to_second_event(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.5)
        engine.step_forward()
        # Next output event after 0.5 is at t=1.0
        assert engine.position == 1.0

    def test_step_forward_pauses_playback(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.step_forward()
        assert engine.playing is False

    def test_step_forward_at_end_is_noop(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(4.0)
        engine.step_forward()
        assert engine.position == 4.0

    def test_step_forward_feeds_event_data(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.step_forward()  # t=0.5: "$ "
        assert "$ " in engine.screen.display[0]

    def test_step_backward_moves_to_previous_output_event(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(1.5)
        engine.step_backward()
        # Previous output event before 1.5 is at t=1.0
        assert engine.position == 1.0

    def test_step_backward_pauses_playback(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        engine.playing = True
        engine.step_backward()
        assert engine.playing is False

    def test_step_backward_at_start_is_noop(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.0)
        engine.step_backward()
        assert engine.position == 0.0

    def test_step_backward_renders_correct_screen(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        engine.step_backward()
        # At t=1.0: "echo hello\r\n" was just output
        assert "echo hello" in engine.screen.display[0]


class TestLoopMode:
    def test_looping_defaults_to_false(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.looping is False

    def test_advance_loops_when_enabled(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.looping = True
        engine.playing = True
        engine.seek(3.9)
        engine.playing = True
        engine.advance(1.0)
        assert engine.playing is True
        assert engine.position < 1.0

    def test_advance_stops_at_end_when_not_looping(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.looping = False
        engine.playing = True
        engine.advance(10.0)
        assert engine.playing is False
        assert engine.position == 4.0

    def test_loop_resets_position_to_zero(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.looping = True
        engine.playing = True
        engine.seek(3.99)
        engine.playing = True
        engine.advance(0.1)
        assert engine.position < 1.0


def _make_recording(events_data: list[tuple[float, str]], width=80, height=24):
    """Build a Recording from a list of (time, output_data) tuples."""
    header = CastHeader(
        version=2,
        width=width,
        height=height,
        duration=events_data[-1][0] if events_data else 0.0,
        timestamp=None,
    )
    events = [Event(time=t, type="o", data=d) for t, d in events_data]
    return Recording(header=header, events=events)


class TestIdleCompression:
    def _make_idle_recording(self):
        """Recording with a 4.5s idle gap between t=1.5 and t=6.0."""
        return _make_recording([
            (0.5, "$ "),
            (1.0, "echo start\r\n"),
            (1.5, "start\r\n$ "),
            (6.0, "echo after gap\r\n"),
            (6.5, "after gap\r\n$ "),
            (7.0, "echo end\r\n"),
            (7.5, "end\r\n$ "),
        ])

    def test_idle_threshold_defaults_to_infinity(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        assert engine.idle_threshold == float("inf")

    def test_advance_skips_idle_gap(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        engine.idle_threshold = 2.0
        engine.playing = True
        engine.seek(1.5)
        engine.playing = True
        changed = engine.advance(0.1)
        assert engine.position >= 5.5

    def test_advance_does_not_skip_small_gap(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        engine.idle_threshold = 2.0
        engine.playing = True
        engine.seek(0.5)
        engine.playing = True
        engine.advance(0.1)
        assert engine.position == 0.6

    def test_no_compression_when_threshold_is_infinity(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        engine.idle_threshold = float("inf")
        engine.playing = True
        engine.seek(1.5)
        engine.playing = True
        engine.advance(0.1)
        assert engine.position == 1.6

    def test_custom_threshold(self):
        recording = self._make_idle_recording()
        engine = PlaybackEngine(recording)
        engine.idle_threshold = 5.0
        engine.playing = True
        engine.seek(1.5)
        engine.playing = True
        engine.advance(0.1)
        assert engine.position == 1.6


class TestSearchIndexEmptyCharFallback:
    """Tests for build_search_index handling pyte's IndexError on Char
    entries with empty data, which certain escape sequences can produce."""

    def test_build_search_index_with_display_indexerror(self):
        """When pyte's screen.display raises IndexError, the engine falls
        back to reading the buffer directly and still builds the index."""
        recording = _make_recording([
            (0.5, "$ "),
            (1.0, "hello\r\n"),
        ])
        engine = PlaybackEngine(recording)

        original_display = pyte.Screen.display.fget

        call_count = 0

        def flaky_display(screen):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise IndexError("string index out of range")
            return original_display(screen)

        with patch.object(pyte.Screen, "display", new_callable=lambda: property(flaky_display)):
            engine.build_search_index()

        assert len(engine._search_index) > 0
        texts = " ".join(text for _, text, _ in engine._search_index)
        assert "hello" in texts

    def test_fallback_replaces_empty_data_with_space(self):
        """The buffer fallback path replaces empty Char.data with spaces
        so the search text remains well-formed."""
        recording = _make_recording([
            (0.5, "abc"),
        ], width=10, height=2)
        engine = PlaybackEngine(recording)

        original_display = pyte.Screen.display.fget

        def crashing_display(screen):
            # Inject an empty-data Char into the buffer, then crash
            screen.buffer[0][5] = Char(
                "", "default", "default",
                False, False, False, False, False, False,
            )
            raise IndexError("string index out of range")

        with patch.object(pyte.Screen, "display", new_callable=lambda: property(crashing_display)):
            engine.build_search_index()

        assert len(engine._search_index) == 1
        text = engine._search_index[0][1]
        # Column 5 should be a space (replacing empty data), not empty
        first_line = text.split("\n")[0]
        assert first_line[5] == " "
        # Original text is still present
        assert first_line.startswith("abc")

    def test_search_works_after_fallback(self):
        """Search (next_match, prev_match, count_matches) works correctly
        even when the index was built via the fallback path."""
        recording = _make_recording([
            (0.5, "$ "),
            (1.0, "searchable text\r\n"),
            (2.0, "more output\r\n"),
        ])
        engine = PlaybackEngine(recording)

        original_display = pyte.Screen.display.fget

        def always_crash(screen):
            raise IndexError("string index out of range")

        with patch.object(pyte.Screen, "display", new_callable=lambda: property(always_crash)):
            engine.build_search_index()

        assert engine.count_matches("searchable") >= 1

        engine.position = 0.0
        match_time = engine.next_match("searchable")
        assert match_time is not None
        assert match_time >= 1.0

        engine.position = 3.0
        match_time = engine.prev_match("searchable")
        assert match_time is not None

    def test_build_search_index_with_wide_characters(self):
        """CJK wide characters (which naturally create empty adjacent
        Char entries) don't crash build_search_index."""
        recording = _make_recording([
            (0.5, "hello "),
            (1.0, "漢字テスト"),
            (2.0, "\r\n$ "),
        ])
        engine = PlaybackEngine(recording)
        engine.build_search_index()
        assert len(engine._search_index) > 0

    def test_build_search_index_with_complex_escape_sequences(self):
        """Escape sequences that set colors, move the cursor, and use
        wide characters don't crash build_search_index."""
        recording = _make_recording([
            (0.5, "\x1b[38;2;153;153;153mStep\x1b[1Cforward"),
            (1.0, "\x1b[0m\r\n"),
            (1.5, "漢字\x1b[1;4HX"),
            (2.0, "\r\n$ "),
        ])
        engine = PlaybackEngine(recording)
        engine.build_search_index()
        assert len(engine._search_index) > 0
        texts = " ".join(text for _, text, _ in engine._search_index)
        assert "Step" in texts
