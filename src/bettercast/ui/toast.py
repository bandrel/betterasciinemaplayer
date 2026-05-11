from __future__ import annotations

from typing import Callable

from textual.widgets import Static


class ConfirmationToast(Static):
    """Transient popup that arms a one-shot confirmation callback.

    Modeled on Textual's Ctrl+C → "Press Ctrl+Q to quit" prompt: show a brief
    message, and if the caller's confirm key is pressed again while pending,
    invoke the stored callback. Auto-dismisses after ``timeout`` seconds.
    """

    DEFAULT_CSS = """
    ConfirmationToast {
        layer: overlay;
        display: none;
        dock: bottom;
        height: 1;
        width: 100%;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._on_confirm: Callable[[], None] | None = None
        self._timer = None
        self.message: str = ""

    @property
    def is_pending(self) -> bool:
        return self._on_confirm is not None

    def prompt(
        self,
        message: str,
        on_confirm: Callable[[], None],
        timeout: float = 3.0,
    ) -> None:
        self._cancel_timer()
        self._on_confirm = on_confirm
        self.message = message
        self.update(message)
        self.display = True
        if self.is_mounted:
            self._timer = self.set_timer(timeout, self._expire)

    def confirm(self) -> None:
        if not self.is_pending:
            return
        callback = self._on_confirm
        self._dismiss()
        callback()

    def _expire(self) -> None:
        if self.is_pending:
            self._dismiss()

    def _dismiss(self) -> None:
        self._cancel_timer()
        self._on_confirm = None
        self.display = False

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
