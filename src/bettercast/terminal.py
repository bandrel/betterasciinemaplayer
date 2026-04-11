"""Extended pyte Screen with alternate screen buffer support.

pyte 0.8.2 does not implement DEC private modes 47, 1047, or 1049
(alternate screen buffer). This module subclasses pyte.Screen to add
that support, which is essential for correctly rendering recordings
of TUI applications (vim, htop, Claude Code, etc.).
"""

from __future__ import annotations

import copy
from typing import Any

import pyte
from pyte import modes as mo

# DEC private mode codes, shifted by 5 bits (pyte convention).
_ALT_SCREEN = 47 << 5       # Switch to alternate buffer
_ALT_SCREEN_1047 = 1047 << 5  # xterm: switch + clear on enter
_ALT_SCREEN_1049 = 1049 << 5  # xterm: switch + save cursor + clear


class AltScreen(pyte.Screen):
    """pyte.Screen with alternate screen buffer (modes 47/1047/1049)."""

    def __init__(self, columns: int, lines: int) -> None:
        super().__init__(columns, lines)
        self._alt_buffer: dict | None = None
        self._alt_cursor: pyte.screens.Cursor | None = None
        self._in_alt_screen: bool = False

    def set_mode(self, *modes: int, **kwargs: Any) -> None:
        super().set_mode(*modes, **kwargs)
        if kwargs.get("private"):
            shifted = [mode << 5 for mode in modes]
            for code in shifted:
                if code in (_ALT_SCREEN, _ALT_SCREEN_1047, _ALT_SCREEN_1049):
                    self._enter_alt_screen(save_cursor=code == _ALT_SCREEN_1049)
                    break

    def reset_mode(self, *modes: int, **kwargs: Any) -> None:
        super().reset_mode(*modes, **kwargs)
        if kwargs.get("private"):
            shifted = [mode << 5 for mode in modes]
            for code in shifted:
                if code in (_ALT_SCREEN, _ALT_SCREEN_1047, _ALT_SCREEN_1049):
                    self._leave_alt_screen(restore_cursor=code == _ALT_SCREEN_1049)
                    break

    def _enter_alt_screen(self, save_cursor: bool = False) -> None:
        if self._in_alt_screen:
            return
        # Save the main screen buffer and cursor.
        self._alt_buffer = copy.deepcopy(dict(self.buffer))
        if save_cursor:
            self._alt_cursor = copy.copy(self.cursor)
        self._in_alt_screen = True
        # Clear the alternate screen.
        self.erase_in_display(2)
        self.cursor_position()

    def _leave_alt_screen(self, restore_cursor: bool = False) -> None:
        if not self._in_alt_screen:
            return
        # Restore the main screen buffer.
        if self._alt_buffer is not None:
            self.buffer.clear()
            self.buffer.update(self._alt_buffer)
            self._alt_buffer = None
        if restore_cursor and self._alt_cursor is not None:
            self.cursor = self._alt_cursor
            self._alt_cursor = None
        self._in_alt_screen = False
        self.dirty.update(range(self.lines))

    def reset(self) -> None:
        super().reset()
        self._alt_buffer = None
        self._alt_cursor = None
        self._in_alt_screen = False
