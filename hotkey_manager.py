"""
全局快捷键管理模块

使用 Windows API (RegisterHotKey) 注册全局热键 Ctrl+Shift+V，
通过 Qt NativeEventFilter 捕获 WM_HOTKEY 消息。
"""

import os
import ctypes
from ctypes import wintypes

import win32con
import win32gui

from PySide6.QtCore import QAbstractNativeEventFilter


# ── Windows MSG 结构体定义 ─────────────────────────

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


# ── 快捷键管理类 ───────────────────────────────────

class HotkeyManager(QAbstractNativeEventFilter):
    """
    全局快捷键管理器。

    用法:
        hotkey = HotkeyManager(callback)
        hotkey.register()
        ...
        hotkey.unregister()
    """

    HOTKEY_ID = 0xCB01  # Clipboard 的简写

    def __init__(self, callback):
        """
        Args:
            callback: 快捷键触发时调用的无参函数
        """
        super().__init__()
        self.callback = callback
        self._registered = False
        self._hotkey_label = "Ctrl+Shift+V"  # Default, updated on success

    @property
    def hotkey_label(self) -> str:
        """Return the human-readable hotkey label."""
        return self._hotkey_label

    def register(self):
        """注册全局快捷键 — 依次尝试多种组合直到找到可用的"""
        if self._registered:
            return

        # Try these combinations in order until one works
        # (Ctrl+Shift+V, Ctrl+Shift+H, Ctrl+Shift+B, Ctrl+Alt+V, Ctrl+Alt+H)
        candidates = [
            (win32con.MOD_CONTROL | win32con.MOD_SHIFT, 0x56, "Ctrl+Shift+V"),  # V
            (win32con.MOD_CONTROL | win32con.MOD_SHIFT, 0x48, "Ctrl+Shift+H"),  # H
            (win32con.MOD_CONTROL | win32con.MOD_SHIFT, 0x42, "Ctrl+Shift+B"),  # B
            (win32con.MOD_CONTROL | win32con.MOD_ALT,   0x56, "Ctrl+Alt+V"),   # Alt+V
            (win32con.MOD_CONTROL | win32con.MOD_ALT,   0x48, "Ctrl+Alt+H"),   # Alt+H
            (win32con.MOD_CONTROL | win32con.MOD_SHIFT, 0x7A, "Ctrl+Shift+F11"),# F11
        ]

        import win32api

        for modifiers, vk_code, label in candidates:
            try:
                # Unregister any previous attempt
                try:
                    win32gui.UnregisterHotKey(0, self.HOTKEY_ID)
                except Exception:
                    pass

                result = win32gui.RegisterHotKey(0, self.HOTKEY_ID, modifiers, vk_code)
                if result:
                    self._registered = True
                    self._hotkey_label = label
                    from PySide6.QtWidgets import QApplication
                    QApplication.instance().installNativeEventFilter(self)
                    return  # Success!
            except Exception:
                continue

        # All failed — log details
        try:
            log_path = os.path.join(
                os.environ.get('APPDATA', os.path.expanduser('~')),
                'ClipboardManager', 'hotkey_error.log'
            )
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a') as f:
                f.write("All hotkey candidates failed\n")
        except Exception:
            pass

    def unregister(self):
        """注销全局快捷键"""
        if not self._registered:
            return

        try:
            win32gui.UnregisterHotKey(0, self.HOTKEY_ID)
            self._registered = False
        except Exception:
            pass

    def nativeEventFilter(self, eventType, message):
        """
        Qt 原生事件过滤器 — 捕获 WM_HOTKEY。
        eventType: bytes (e.g., b'windows_generic_MSG')
        message: pointer to MSG struct
        """
        if eventType == b'windows_generic_MSG':
            msg = MSG.from_address(int(message))
            if msg.message == win32con.WM_HOTKEY and msg.wParam == self.HOTKEY_ID:
                if self.callback:
                    self.callback()
                return True, 0
        return False, 0
