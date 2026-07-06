# -*- coding: utf-8 -*-
"""
Clipboard Monitor - Polls Windows clipboard for text and image changes.

Uses QTimer (main thread) instead of QThread to avoid all threading issues.
Checks clipboard every 500ms.
"""

import hashlib
import os

import win32clipboard

from PySide6.QtCore import QObject, QTimer, Signal

from image_utils import save_clipboard_image


def _debug_log(msg: str):
    """Write debug info to log file."""
    try:
        log_path = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'ClipboardManager', 'monitor.log'
        )
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(f"[{__import__('datetime').datetime.now()}] {msg}\n")
    except Exception:
        pass


class ClipboardMonitor(QObject):
    """
    Clipboard monitor using QTimer (main thread, no threading issues).

    Emits content_captured(type, data) when new clipboard content is detected.
    """

    content_captured = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_clipboard)
        self._last_text = None
        self._last_image_hash = None  # Prevent duplicate image saves
        self._running = False

        _debug_log("=== Monitor initialized ===")

    def start(self):
        """Start polling clipboard every 500ms."""
        if self._running:
            return
        self._running = True
        # Snapshot current clipboard so we don't capture pre-existing content
        self._last_text = self._get_clipboard_text()
        self._timer.start(500)
        _debug_log(f"Monitor started. Initial clipboard text: {repr(self._last_text)[:100]}")

    def stop(self):
        """Stop polling."""
        self._running = False
        self._timer.stop()
        _debug_log("Monitor stopped")

    def _check_clipboard(self):
        """Check clipboard for new text or image content."""
        try:
            # Check for image first
            result = save_clipboard_image()
            if result is not None:
                image_path, thumb_path = result
                # Dedup: hash the image path stem (content-based)
                dedup_key = os.path.basename(image_path).rsplit('.', 1)[0]
                if dedup_key != self._last_image_hash:
                    _debug_log(f"Image detected: {os.path.basename(image_path)}")
                    self._last_image_hash = dedup_key
                    self._last_text = None
                    self.content_captured.emit('image', (image_path, thumb_path))
                return

            # Check for text
            text = self._get_clipboard_text()
            if text and text.strip():
                if text != self._last_text:
                    _debug_log(f"Text changed: {repr(text)[:100]}")
                    self._last_text = text
                    self._last_image_hash = None
                    self.content_captured.emit('text', text)
        except Exception as e:
            _debug_log(f"Check error: {e}")

    def _get_clipboard_text(self) -> str | None:
        """Get text content from Windows clipboard."""
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return data
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            _debug_log(f"Get text error: {e}")
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass
        return None
