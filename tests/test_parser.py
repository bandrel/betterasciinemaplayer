import io
from pathlib import Path

import pytest

from bettercast.formats.base import CastHeader, Event, Recording
from bettercast.formats.v2 import V2Parser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_cast_header_construction():
    header = CastHeader(version=2, width=80, height=24, duration=4.0)
    assert header.version == 2
    assert header.width == 80
    assert header.height == 24
    assert header.duration == 4.0
    assert header.timestamp is None
    assert header.title is None
    assert header.env == {}


def test_event_construction():
    event = Event(time=1.5, type="o", data="hello\r\n")
    assert event.time == 1.5
    assert event.type == "o"
    assert event.data == "hello\r\n"


def test_recording_construction():
    header = CastHeader(version=2, width=80, height=24, duration=0.0)
    events = [Event(time=0.5, type="o", data="$ ")]
    recording = Recording(header=header, events=events)
    assert recording.header.width == 80
    assert len(recording.events) == 1


class TestV2Parser:
    def test_parse_valid_file(self):
        parser = V2Parser()
        recording = parser.parse(FIXTURES_DIR / "sample.cast")
        assert recording.header.version == 2
        assert recording.header.width == 80
        assert recording.header.height == 24
        assert recording.header.timestamp == 1234567890
        assert recording.header.duration == 4.0
        assert len(recording.events) == 7

    def test_parse_events_sorted_by_time(self):
        parser = V2Parser()
        recording = parser.parse(FIXTURES_DIR / "sample.cast")
        times = [e.time for e in recording.events]
        assert times == sorted(times)

    def test_parse_event_content(self):
        parser = V2Parser()
        recording = parser.parse(FIXTURES_DIR / "sample.cast")
        assert recording.events[0] == Event(time=0.5, type="o", data="$ ")
        assert recording.events[2] == Event(time=1.5, type="o", data="hello\r\n")

    def test_parse_from_text_stream(self):
        cast_text = '{"version": 2, "width": 40, "height": 10}\n[0.1, "o", "hi"]\n'
        parser = V2Parser()
        recording = parser.parse(io.StringIO(cast_text))
        assert recording.header.width == 40
        assert len(recording.events) == 1

    def test_parse_computes_duration_from_last_event(self):
        cast_text = '{"version": 2, "width": 80, "height": 24}\n[1.0, "o", "a"]\n[5.5, "o", "b"]\n'
        parser = V2Parser()
        recording = parser.parse(io.StringIO(cast_text))
        assert recording.header.duration == 5.5

    def test_parse_empty_file_raises(self):
        parser = V2Parser()
        with pytest.raises(ValueError, match="Empty cast file"):
            parser.parse(io.StringIO(""))

    def test_parse_wrong_version_raises(self):
        cast_text = '{"version": 1, "width": 80, "height": 24}\n'
        parser = V2Parser()
        with pytest.raises(ValueError, match="Unsupported version"):
            parser.parse(io.StringIO(cast_text))

    def test_parse_missing_width_raises(self):
        cast_text = '{"version": 2, "height": 24}\n'
        parser = V2Parser()
        with pytest.raises(ValueError, match="Missing required"):
            parser.parse(io.StringIO(cast_text))

    def test_parse_no_events_returns_zero_duration(self):
        cast_text = '{"version": 2, "width": 80, "height": 24}\n'
        parser = V2Parser()
        recording = parser.parse(io.StringIO(cast_text))
        assert recording.header.duration == 0.0
        assert len(recording.events) == 0

    def test_parse_malformed_json_raises(self):
        parser = V2Parser()
        with pytest.raises(Exception):
            parser.parse(io.StringIO("{not json"))
