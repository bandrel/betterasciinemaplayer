from bettercast.ui.progress import format_time


class TestFormatTime:
    def test_zero(self):
        assert format_time(0.0) == "00:00"

    def test_seconds(self):
        assert format_time(45.0) == "00:45"

    def test_minutes(self):
        assert format_time(125.0) == "02:05"

    def test_hours(self):
        assert format_time(3661.0) == "1:01:01"

    def test_fractional_seconds_truncated(self):
        assert format_time(59.9) == "00:59"

    def test_exactly_one_hour(self):
        assert format_time(3600.0) == "1:00:00"
