from bettercast.ui.bookmarks import BookmarkOverlay
from bettercast.ui.help import HelpOverlay, HELP_TEXT
from bettercast.ui.search import SearchOverlay
from bettercast.ui.timestamp import TimestampOverlay, parse_timestamp
from bettercast.ui.toast import ConfirmationToast


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
        assert "n/N" in HELP_TEXT
        assert "?" in HELP_TEXT
        assert "q" in HELP_TEXT

    def test_help_text_has_new_bindings(self):
        assert "Step" in HELP_TEXT
        assert "loop" in HELP_TEXT.lower()
        assert "g" in HELP_TEXT
        assert "m" in HELP_TEXT
        assert "b" in HELP_TEXT
        assert "{ / }" in HELP_TEXT
        assert "c" in HELP_TEXT


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


class TestBookmarkOverlay:
    def test_default_display_is_none(self):
        assert "display: none" in BookmarkOverlay.DEFAULT_CSS

    def test_has_dismiss_action(self):
        overlay = BookmarkOverlay()
        assert hasattr(overlay, "action_dismiss")

    def test_update_bookmarks_stores_list(self):
        overlay = BookmarkOverlay()
        bookmarks = [(1.0, "Bookmark 1"), (3.0, "Bookmark 2")]
        overlay.update_bookmarks(bookmarks)
        assert overlay._bookmarks == bookmarks

    def test_selected_index_clamps(self):
        overlay = BookmarkOverlay()
        overlay._selected = 5
        overlay.update_bookmarks([(1.0, "only one")])
        assert overlay._selected == 0

    def test_move_up_decrements(self):
        overlay = BookmarkOverlay()
        overlay.update_bookmarks([(1.0, "a"), (2.0, "b")])
        overlay._selected = 1
        overlay.action_move_up()
        assert overlay._selected == 0

    def test_move_down_increments(self):
        overlay = BookmarkOverlay()
        overlay.update_bookmarks([(1.0, "a"), (2.0, "b")])
        overlay._selected = 0
        overlay.action_move_down()
        assert overlay._selected == 1

    def test_move_up_clamps_at_zero(self):
        overlay = BookmarkOverlay()
        overlay.update_bookmarks([(1.0, "a")])
        overlay._selected = 0
        overlay.action_move_up()
        assert overlay._selected == 0

    def test_move_down_clamps_at_end(self):
        overlay = BookmarkOverlay()
        overlay.update_bookmarks([(1.0, "a")])
        overlay._selected = 0
        overlay.action_move_down()
        assert overlay._selected == 0


class TestConfirmationToast:
    def test_default_display_is_none(self):
        assert "display: none" in ConfirmationToast.DEFAULT_CSS

    def test_is_pending_false_initially(self):
        toast = ConfirmationToast()
        assert toast.is_pending is False

    def test_prompt_arms_toast(self):
        toast = ConfirmationToast()
        toast.prompt("press X", on_confirm=lambda: None)
        assert toast.is_pending is True

    def test_prompt_renders_message(self):
        toast = ConfirmationToast()
        toast.prompt("press X to do thing", on_confirm=lambda: None)
        assert toast.message == "press X to do thing"

    def test_confirm_invokes_callback_when_pending(self):
        toast = ConfirmationToast()
        calls = []
        toast.prompt("press X", on_confirm=lambda: calls.append(1))
        toast.confirm()
        assert calls == [1]

    def test_confirm_clears_pending(self):
        toast = ConfirmationToast()
        toast.prompt("press X", on_confirm=lambda: None)
        toast.confirm()
        assert toast.is_pending is False

    def test_confirm_noop_when_not_pending(self):
        toast = ConfirmationToast()
        # No prompt() call; calling confirm() should be a safe no-op.
        toast.confirm()
        assert toast.is_pending is False

    def test_confirm_clears_callback(self):
        toast = ConfirmationToast()
        calls = []
        toast.prompt("press X", on_confirm=lambda: calls.append(1))
        toast.confirm()
        toast.confirm()
        assert calls == [1]
