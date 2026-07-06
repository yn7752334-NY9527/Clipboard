"""
Clipboard History Manager - Entry Point

Features:
- Double-click exe: opens the main window; closing it hides to system tray
- Auto-captures all copied text and images
- Ctrl+Shift+V to toggle the history panel
- Search, pin, delete, category filter
- 7-day auto-expiry, 500-item cap
"""

import sys
import os
import ctypes
import traceback

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from data_store import DataStore
from clipboard_monitor import ClipboardMonitor
from main_window import MainWindow
from tray_manager import TrayManager


# ── 单实例检测（基于文件锁 + PID 验证）───────────

LOCK_FILE = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    'ClipboardManager', '.instance.lock'
)


def _pid_is_running(pid: int) -> bool:
    """Check if a process with the given PID is running (via ctypes, no pywintypes)."""
    try:
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_INFORMATION = 0x0400
        handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
        if handle and handle != 0:
            kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    return False


def check_single_instance() -> bool:
    """
    Check if another instance is already running using a PID lock file.
    If the lock file's PID is no longer alive, the lock is stale and overwritten.
    Returns True if this instance should continue, False if another is running.
    """
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                old_pid_str = f.read().strip()
            try:
                old_pid = int(old_pid_str)
            except ValueError:
                old_pid = None

            if old_pid and _pid_is_running(old_pid):
                return False
            # Stale lock (process died without cleanup) — overwrite
    except Exception:
        pass

    # Write current PID to lock file
    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    return True


def release_lock():
    """Remove the lock file on clean exit."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


def bring_existing_window_to_front():
    """Find and activate the existing instance's window."""
    try:
        import win32gui
        import win32con

        def find_window_callback(hwnd, found):
            if win32gui.GetWindowText(hwnd).startswith("剪贴板历史"):
                found.append(hwnd)
            return True

        found = []
        win32gui.EnumWindows(find_window_callback, found)
        if found:
            hwnd = found[0]
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def main():
    # ── Prevent duplicate instances ────────────────
    if not check_single_instance():
        bring_existing_window_to_front()
        sys.exit(0)

    # ── Global crash logger (writes to file) ─────
    def log_error(msg):
        try:
            log_path = os.path.join(
                os.environ.get('APPDATA', os.path.expanduser('~')),
                'ClipboardManager', 'error.log'
            )
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(f"[{__import__('datetime').datetime.now()}] {msg}\n")
        except Exception:
            pass

    try:
        # ── 高 DPI 适配 ──────────────────────────────
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName("ClipboardManager")
        app.setApplicationDisplayName("剪贴板历史管理器")
        app.setQuitOnLastWindowClosed(False)

        # ── 初始化数据层 ─────────────────────────────
        data_store = DataStore()

        # ── 初始化主窗口 ─────────────────────────────
        main_window = MainWindow(data_store)
        log_error("MainWindow created OK")

        # ── 初始化系统托盘 ───────────────────────────
        def show_window():
            main_window.show_and_focus()

        def clear_history():
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                None,
                "确认清空",
                "确定要清空所有剪贴板历史记录吗？\n此操作不可恢复。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                data_store.clear_all()
                main_window.refresh_cards()

        def quit_app():
            monitor.stop()
            release_lock()
            QApplication.quit()

        tray = TrayManager(
            show_callback=show_window,
            clear_callback=clear_history,
            quit_callback=quit_app,
        )
        log_error("TrayManager created OK")

        # ── 初始化剪贴板监控 ─────────────────────────
        monitor = ClipboardMonitor()

        def on_content_captured(content_type, data):
            if content_type == 'text':
                data_store.add_text(data)
            elif content_type == 'image':
                image_path, thumb_path = data
                data_store.add_image(image_path, thumb_path)

            # Always try to refresh — if window is hidden, next open will show content
            main_window.refresh_requested.emit()

        monitor.content_captured.connect(on_content_captured)
        monitor.start()
        log_error("Monitor started OK")

        # ── 启动时显示窗口 + 托盘通知 ────────────────
        show_window()
        log_error("show_window() called OK")
        # 延迟 1.5 秒弹出气泡通知（等托盘图标完全初始化）
        QTimer.singleShot(1500, lambda: tray.show_notification(
            "剪贴板历史管理器",
            "已开始记录剪贴板内容\n右键托盘图标可打开面板"
        ))

        # ── 启动事件循环 ─────────────────────────────
        sys.exit(app.exec())

    except Exception:
        log_error(f"FATAL ERROR:\n{traceback.format_exc()}")


if __name__ == '__main__':
    main()
