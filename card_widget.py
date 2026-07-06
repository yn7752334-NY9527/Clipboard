"""
卡片组件模块

单条剪贴板记录的可视化卡片。
- 文字类型：显示文字预览（截断）、时间戳
- 图片类型：显示模糊缩略图、时间戳
- 通用操作：置顶按钮、删除按钮
- 点击卡片将内容复制回剪贴板
"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSizePolicy, QApplication,
)


class CardWidget(QFrame):
    """
    剪贴板记录卡片组件。

    Signals:
        clicked: 用户点击卡片主体（用于复制内容）
        pin_toggled: 用户点击置顶按钮 (item_id)
        delete_requested: 用户点击删除按钮 (item_id)
    """

    clicked = Signal(object)          # item dict
    pin_toggled = Signal(int)         # item_id
    delete_requested = Signal(int)    # item_id

    CARD_STYLE = """
        CardWidget {
            background-color: #ffffff;
            border: 1px solid #e0e8f0;
            border-radius: 8px;
            padding: 2px;
        }
        CardWidget:hover {
            border-color: #4A90D9;
            background-color: #f5f9fd;
        }
    """

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setStyleSheet(self.CARD_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(72)
        self._build_ui()

    def _build_ui(self):
        """构建卡片内部布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(10)

        # ── 左侧：内容预览 ─────────────────────────
        if self.item['type'] == 'image':
            preview = self._create_image_preview()
        else:
            preview = self._create_text_preview()

        main_layout.addWidget(preview, stretch=1)

        # ── 中间：时间戳 ───────────────────────────
        time_label = QLabel(self._format_time(self.item['created_at']))
        time_label.setStyleSheet("color: #999; font-size: 11px;")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        time_label.setFixedWidth(130)
        main_layout.addWidget(time_label)

        # ── 右侧：操作按钮 ─────────────────────────
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        # 置顶按钮
        is_pinned = self.item.get('is_pinned', 0)
        self.pin_btn = QPushButton("📌" if is_pinned else "📍")
        self.pin_btn.setFixedSize(28, 28)
        self.pin_btn.setToolTip("置顶 / 取消置顶")
        self.pin_btn.setStyleSheet(self._pin_btn_style(is_pinned))
        self.pin_btn.clicked.connect(self._on_pin_clicked)
        btn_layout.addWidget(self.pin_btn)

        # 删除按钮
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("删除此记录")
        del_btn.setStyleSheet(self._delete_btn_style())
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.item['id']))
        btn_layout.addWidget(del_btn)

        main_layout.addLayout(btn_layout)

    def _create_text_preview(self) -> QLabel:
        """创建文字预览标签"""
        content = self.item.get('content', '')
        # 截断显示，最多两行
        if len(content) > 200:
            content = content[:200] + '...'
        # 单行时截断到 ~80 字符
        display = content.replace('\n', ' ').replace('\r', '')
        if len(display) > 80:
            display = display[:80] + '...'

        label = QLabel(display)
        label.setWordWrap(True)
        label.setStyleSheet("color: #333; font-size: 13px; padding: 4px;")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setMaximumHeight(56)
        return label

    def _create_image_preview(self) -> QLabel:
        """创建图片缩略图预览"""
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedHeight(56)

        thumb_path = self.item.get('thumb_path', '')
        if thumb_path and self._file_exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    80, 56,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(scaled)
        else:
            label.setText("🖼️ 图片")
            label.setStyleSheet("color: #888; font-size: 13px;")

        return label

    def _format_time(self, time_str: str) -> str:
        """格式化时间显示"""
        try:
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            diff = now - dt

            if diff.days == 0:
                if diff.seconds < 60:
                    return '刚刚'
                if diff.seconds < 3600:
                    return f'{diff.seconds // 60} 分钟前'
                return f'{diff.seconds // 3600} 小时前'
            elif diff.days == 1:
                return '昨天 ' + dt.strftime('%H:%M')
            elif diff.days < 7:
                return f'{diff.days} 天前'
            else:
                return dt.strftime('%m-%d %H:%M')
        except Exception:
            return time_str or ''

    def _pin_btn_style(self, is_pinned: bool) -> str:
        """置顶按钮样式"""
        if is_pinned:
            return """
                QPushButton {
                    background-color: #e8f0fe; border: 1px solid #4A90D9;
                    border-radius: 4px; font-size: 12px;
                }
                QPushButton:hover { background-color: #d0e2f9; }
            """
        return """
            QPushButton {
                background-color: #f5f5f5; border: 1px solid #ddd;
                border-radius: 4px; font-size: 12px;
            }
            QPushButton:hover { background-color: #e8f0fe; border-color: #4A90D9; }
        """

    def _delete_btn_style(self) -> str:
        """删除按钮样式"""
        return """
            QPushButton {
                background-color: #f5f5f5; border: 1px solid #ddd;
                border-radius: 4px; font-size: 12px; color: #999;
            }
            QPushButton:hover {
                background-color: #ffe8e8; border-color: #e88; color: #c44;
            }
        """

    def _on_pin_clicked(self):
        """置顶按钮点击"""
        self.pin_toggled.emit(self.item['id'])

    def mousePressEvent(self, event: QMouseEvent):
        """点击卡片主体 → 复制内容到剪贴板"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item)
        super().mousePressEvent(event)

    @staticmethod
    def _file_exists(path: str) -> bool:
        """检查文件是否存在"""
        import os
        return bool(path and os.path.exists(path))
