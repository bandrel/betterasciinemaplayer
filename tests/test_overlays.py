from bettercast.ui.help import HelpOverlay, HELP_TEXT
from bettercast.ui.search import SearchOverlay
from bettercast.ui.timestamp import TimestampOverlay, parse_timestamp


class TestHelpOverlay:
    def test_render_contains_keybindings(self):
        widget = HelpOverlay()
        text = widget.render()
        assert "Play/Pause" in text
        assert "Search" in text
        assert "Quit" in text

    def test_help_text_has_all_bindings(self):
        assert "Space" in HELP_TEXT
        assert "Home/End" in HELP_TEXT
        assert "n / N" in HELP_TEXT
        assert "?" in HELP_TEXT
        assert "q" in HELP_TEXT


class TestSearchOverlay:
    def test_has_update_match_count(self):
        overlay = SearchOverlay()
        assert hasattr(overlay, "update_match_count")

    def test_has_dismiss_action(self):
        overlay = SearchOverlay()
        assert hasattr(overlay, "action_dismiss")

    def test_default_display_is_set(self):
        # SearchOverlay CSS sets display: none by default
        # Verify the class has DEFAULT_CSS that references display
        assert "display: none" in SearchOverlay.DEFAULT_CSS


class TestTimestampParsing:
    def test_parse_mm_ss(self):
        assert parse_timestamp("01:30") == 90.0

    def test_parse_h_mm_ss(self):
        assert parse_timestamp("1:01:30") == 3690.0

    def test_parse_ss_only(self):
        assert parse_timestamp("45") == 45.0

    def test_parse_invalid_returns_none(self):
        assert parse_timestamp("abc") is None

    def test_parse_empty_returns_none(self):
        assert parse_timestamp("") is None

    def test_parse_negative_returns_none(self):
        assert parse_timestamp("-1:00") is None


class TestTimestampOverlay:
    def test_default_display_is_none(self):
        assert "display: none" in TimestampOverlay.DEFAULT_CSS

    def test_has_dismiss_action(self):
        overlay = TimestampOverlay()
        assert hasattr(overlay, "action_dismiss")
