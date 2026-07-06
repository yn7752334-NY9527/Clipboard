"""
系统托盘管理模块

提供系统托盘图标和右键菜单：
- 打开主界面
- 清空历史
- 开机自启开关
- 退出程序
"""

import os
import sys
import win32api
import win32con

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication


# ── 应用图标生成 ──────────────────────────────────

def create_app_icon() -> QIcon:
    """用 QPainter 绘制一个简洁的蓝色剪贴板图标"""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # 透明背景

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 剪贴板主体 — 蓝色圆角矩形
    painter.setBrush(QColor("#4A90D9"))
    painter.setPen(QColor("#2E6DB4"))
    painter.drawRoundedRect(12, 14, 40, 42, 5, 5)

    # 夹子 — 深蓝色
    painter.setBrush(QColor("#2E6DB4"))
    painter.setPen(QColor("#1E5080"))
    painter.drawRoundedRect(22, 4, 20, 14, 3, 3)

    # 三行白色横线（模拟文字）
    painter.setBrush(QColor("#FFFFFF"))
    painter.setPen(QColor("#FFFFFF"))
    painter.drawRoundedRect(18, 22, 28, 4, 2, 2)
    painter.drawRoundedRect(18, 30, 22, 4, 2, 2)
    painter.drawRoundedRect(18, 38, 26, 4, 2, 2)

    painter.end()
    return QIcon(pixmap)


# ── 开机自启管理 ──────────────────────────────────

# 注册表路径
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ClipboardManager"


def get_exe_path() -> str:
    """获取当前可执行文件的路径（开发模式返回 python 脚本路径）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return sys.executable
    else:
        # 开发模式 — 返回 main.py 路径
        import __main__
        if hasattr(__main__, '__file__'):
            return os.path.abspath(__main__.__file__)
        return sys.executable


def is_autostart_enabled() -> bool:
    """检查是否已设置开机自启"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_autostart(enable: bool):
    """设置或取消开机自启"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        if enable:
            exe_path = get_exe_path()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[AutoStart] 操作失败: {e}")
        return False


# ── 系统托盘管理器 ────────────────────────────────

class TrayManager:
    """管理系统托盘图标和菜单"""

    def __init__(self, show_callback, clear_callback, quit_callback):
        """
        Args:
            show_callback: 打开主窗口的回调
            clear_callback: 清空历史的回调
            quit_callback: 退出程序的回调
        """
        self.show_callback = show_callback
        self.clear_callback = clear_callback
        self.quit_callback = quit_callback

        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(create_app_icon())
        self.tray_icon.setToolTip("剪贴板历史管理器")

        # 左键点击 → 打开主界面
        self.tray_icon.activated.connect(self._on_activated)

        # 构建右键菜单
        self.menu = self._build_menu()
        self.tray_icon.setContextMenu(self.menu)

        # 显示托盘图标
        self.tray_icon.show()

    def _build_menu(self) -> QMenu:
        """构建托盘右键菜单"""
        menu = QMenu()

        # 打开主界面
        open_action = QAction("📋 打开剪贴板历史", menu)
        open_action.triggered.connect(self.show_callback)
        menu.addAction(open_action)

        menu.addSeparator()

        # 清空历史
        clear_action = QAction("🗑️ 清空全部历史", menu)
        clear_action.triggered.connect(self.clear_callback)
        menu.addAction(clear_action)

        menu.addSeparator()

        # 开机自启 — 可勾选
        self.autostart_action = QAction("🔌 开机自动启动", menu)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(is_autostart_enabled())
        self.autostart_action.triggered.connect(self._toggle_autostart)
        menu.addAction(self.autostart_action)

        menu.addSeparator()

        # 关于
        about_action = QAction("ℹ️ 关于", menu)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        menu.addSeparator()

        # 退出
        quit_action = QAction("❌ 退出", menu)
        quit_action.triggered.connect(self.quit_callback)
        menu.addAction(quit_action)

        return menu

    def _show_about(self):
        """显示关于对话框"""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(
            None,
            "关于 剪贴板历史管理器",
            "剪贴板历史管理器  v1.0.0 (2026.07)\n\n"
            "自动记录剪贴板文字与图片，\n"
            "支持搜索、置顶、分类筛选，\n"
            "7 天自动过期，500 条上限。\n\n"
            "作者：Ronny\n"
            "© 2026 Ronny"
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """托盘图标点击事件"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 左键单击 → 打开主界面
            self.show_callback()

    def _toggle_autostart(self, enabled: bool):
        """切换开机自启"""
        success = set_autostart(enabled)
        if not success:
            self.autostart_action.setChecked(not enabled)

    def update_autostart_state(self):
        """刷新开机自启菜单状态"""
        self.autostart_action.setChecked(is_autostart_enabled())

    def show_notification(self, title: str, message: str):
        """显示气泡通知"""
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
