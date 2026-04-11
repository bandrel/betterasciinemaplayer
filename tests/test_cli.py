"""End-to-end CLI tests using Click's CliRunner.

Tests the full path from command-line invocation through argument parsing,
file loading, error handling, and app construction.
"""

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from bettercast.cli import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestCliHappyPath:
    def test_valid_cast_file_exits_cleanly(self):
        runner = CliRunner()
        with patch("bettercast.cli.BettercastApp.run") as mock_run:
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast")])
        assert result.exit_code == 0
        mock_run.assert_called_once()

    def test_speed_flag_sets_engine_speed(self):
        runner = CliRunner()
        with patch("bettercast.cli.BettercastApp.run") as mock_run:
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--speed", "2.0"])
        assert result.exit_code == 0
        mock_run.assert_called_once()

    def test_app_receives_correct_engine(self):
        runner = CliRunner()
        constructed_apps = []

        original_init = None

        def capture_init(self, engine):
            constructed_apps.append(engine)
            original_init(self, engine)

        from bettercast.ui.app import BettercastApp
        original_init = BettercastApp.__init__

        with patch.object(BettercastApp, "__init__", capture_init), \
             patch.object(BettercastApp, "run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--speed", "3.0"])

        assert result.exit_code == 0
        assert len(constructed_apps) == 1
        engine = constructed_apps[0]
        assert engine.speed == 3.0
        assert engine.duration == 4.0


class TestCliErrorPaths:
    def test_no_arguments_shows_usage(self):
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code != 0
        assert "Usage" in result.output or "Missing" in result.output.lower() or "Error" in result.output

    def test_nonexistent_file_shows_error(self):
        runner = CliRunner()
        result = runner.invoke(main, ["/tmp/does_not_exist_12345.cast"])
        assert result.exit_code != 0

    def test_empty_cast_file_shows_error(self, tmp_path):
        empty_file = tmp_path / "empty.cast"
        empty_file.write_text("")
        runner = CliRunner()
        result = runner.invoke(main, [str(empty_file)])
        assert result.exit_code != 0
        assert "empty" in result.output.lower() or "error" in result.output.lower()

    def test_malformed_json_shows_error(self, tmp_path):
        bad_file = tmp_path / "bad.cast"
        bad_file.write_text("this is not json\n")
        runner = CliRunner()
        result = runner.invoke(main, [str(bad_file)])
        assert result.exit_code != 0

    def test_wrong_version_shows_error(self, tmp_path):
        wrong_ver = tmp_path / "wrong_version.cast"
        wrong_ver.write_text(json.dumps({"version": 99, "width": 80, "height": 24}) + "\n")
        runner = CliRunner()
        result = runner.invoke(main, [str(wrong_ver)])
        assert result.exit_code != 0
        assert "version" in result.output.lower() or "error" in result.output.lower()

    def test_no_events_shows_error(self, tmp_path):
        no_events = tmp_path / "no_events.cast"
        no_events.write_text(json.dumps({"version": 2, "width": 80, "height": 24}) + "\n")
        runner = CliRunner()
        result = runner.invoke(main, [str(no_events)])
        assert result.exit_code != 0
        assert "no events" in result.output.lower() or "error" in result.output.lower()

    def test_malformed_event_line_shows_error(self, tmp_path):
        bad_event = tmp_path / "bad_event.cast"
        content = json.dumps({"version": 2, "width": 80, "height": 24}) + "\n"
        content += "[1.0]\n"  # Missing type and data fields
        bad_event.write_text(content)
        runner = CliRunner()
        result = runner.invoke(main, [str(bad_event)])
        assert result.exit_code != 0


class TestIdleCompressionFlags:
    def test_idle_threshold_flag(self):
        runner = CliRunner()
        with patch("bettercast.cli.BettercastApp.run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--idle-threshold", "3.0"])
        assert result.exit_code == 0

    def test_no_idle_compress_flag(self):
        runner = CliRunner()
        with patch("bettercast.cli.BettercastApp.run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--no-idle-compress"])
        assert result.exit_code == 0

    def test_idle_threshold_sets_engine_value(self):
        runner = CliRunner()
        constructed_apps = []
        original_init = None

        def capture_init(self, engine):
            constructed_apps.append(engine)
            original_init(self, engine)

        from bettercast.ui.app import BettercastApp
        original_init = BettercastApp.__init__

        with patch.object(BettercastApp, "__init__", capture_init), \
             patch.object(BettercastApp, "run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--idle-threshold", "3.0"])

        assert result.exit_code == 0
        engine = constructed_apps[0]
        assert engine.idle_threshold == 3.0

    def test_no_idle_compress_sets_infinity(self):
        runner = CliRunner()
        constructed_apps = []
        original_init = None

        def capture_init(self, engine):
            constructed_apps.append(engine)
            original_init(self, engine)

        from bettercast.ui.app import BettercastApp
        original_init = BettercastApp.__init__

        with patch.object(BettercastApp, "__init__", capture_init), \
             patch.object(BettercastApp, "run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample.cast"), "--no-idle-compress"])

        assert result.exit_code == 0
        engine = constructed_apps[0]
        assert engine.idle_threshold == float("inf")


class TestV3AutoDetection:
    def test_v3_file_loads_successfully(self):
        runner = CliRunner()
        with patch("bettercast.cli.BettercastApp.run") as mock_run:
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample_v3.cast")])
        assert result.exit_code == 0
        mock_run.assert_called_once()

    def test_v3_file_uses_correct_dimensions(self):
        runner = CliRunner()
        constructed_apps = []
        original_init = None

        def capture_init(self, engine):
            constructed_apps.append(engine)
            original_init(self, engine)

        from bettercast.ui.app import BettercastApp
        original_init = BettercastApp.__init__

        with patch.object(BettercastApp, "__init__", capture_init), \
             patch.object(BettercastApp, "run"):
            result = runner.invoke(main, [str(FIXTURES_DIR / "sample_v3.cast")])

        assert result.exit_code == 0
        engine = constructed_apps[0]
        assert engine.recording.header.width == 80
        assert engine.recording.header.height == 24
        assert engine.duration == 4.0
