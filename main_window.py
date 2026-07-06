"""
主窗口模块

剪贴板历史管理器的核心界面：
- 无边框弹出式窗口，圆角阴影
- 搜索框 + 分类标签（全部 / 文字 / 图片）
- 可滚动的卡片列表
- 点击卡片复制内容，点击外部自动隐藏
"""

import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QScrollArea, QLabel,
    QApplication, QMessageBox,
)

from data_store import DataStore
from card_widget import CardWidget
from image_utils import copy_text_to_clipboard, copy_image_to_clipboard


# ── 淡蓝色主题色板 ────────────────────────────────

PRIMARY = "#4A90D9"         # 主色 — 按钮、选中态
PRIMARY_LIGHT = "#E8F0FE"   # 浅色 — 背景悬浮
PRIMARY_DARK = "#2E6DB4"    # 深色 — 按下态
BACKGROUND = "#F0F4F8"      # 窗口背景
CARD_BG = "#FFFFFF"         # 卡片背景
TEXT_PRIMARY = "#333333"    # 主文字
TEXT_SECONDARY = "#888888"  # 辅助文字
BORDER = "#DDE4ED"          # 边框


class MainWindow(QWidget):
    """
    主窗口 — 剪贴板历史面板。

    以无边框弹出窗口形式呈现，失去焦点时自动隐藏。
    """

    # 数据变更信号（外部触发刷新）
    refresh_requested = Signal()

    def __init__(self, data_store: DataStore):
        super().__init__()
        self.data_store = data_store
        self._category = 'all'
        self._cards: list[CardWidget] = []

        self._init_window()
        self._build_ui()
        self._apply_theme()

        self.refresh_requested.connect(self.refresh_cards)
        QTimer.singleShot(100, self.refresh_cards)

    # ── 窗口设置 ──────────────────────────────────

    def _init_window(self):
        """Standard window with taskbar icon, minimize, and close-to-tray."""
        self.setWindowTitle("剪贴板历史 v1.0.0 - Ronny © 2026")
        # Normal window: shows in taskbar + Alt+Tab, has title bar with min/max/close
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(420, 500)
        self.resize(480, 620)

        # Position near bottom-right
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 20,
                      geo.bottom() - self.height() - 20)

    # ── UI 构建 ────────────────────────────────────

    def _build_ui(self):
        """构建完整界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # ── 搜索框 ─────────────────────────
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  搜索剪贴板历史...")
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self._on_search)
        main_layout.addWidget(self.search_input)

        # ── 分类标签 ───────────────────────
        category_bar = self._create_category_bar()
        main_layout.addWidget(category_bar)

        # ── 卡片列表区域 ───────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("scrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.card_container = QWidget()
        self.card_container.setObjectName("cardContainer")
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(6)
        self.card_layout.addStretch()

        self.scroll_area.setWidget(self.card_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # ── 底部状态栏 ─────────────────────
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)

    def _create_category_bar(self) -> QWidget:
        """分类标签栏：全部 / 文字 / 图片"""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.cat_buttons = {}

        categories = [
            ('all', '全部'),
            ('text', '📝 文字'),
            ('image', '🖼️ 图片'),
        ]

        for key, label in categories:
            btn = QPushButton(label)
            btn.setObjectName("catBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_category(k))
            self.cat_buttons[key] = btn
            layout.addWidget(btn)

        # 默认选中"全部"
        self.cat_buttons['all'].setChecked(True)

        layout.addStretch()
        return bar

    def _create_status_bar(self) -> QWidget:
        """底部状态栏：记录条数"""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addStretch()
        layout.addWidget(self.status_label)
        return bar

    # ── 主题样式 ──────────────────────────────────

    def _apply_theme(self):
        """应用淡蓝色主题 QSS"""
        self.setStyleSheet(f"""
            MainWindow {{
                background-color: {BACKGROUND};
            }}
            #searchInput {{
                background-color: {CARD_BG};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: {TEXT_PRIMARY};
            }}
            #searchInput:focus {{
                border-color: {PRIMARY};
            }}
            #catBtn {{
                background-color: {CARD_BG};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                color: {TEXT_PRIMARY};
            }}
            #catBtn:hover {{
                border-color: {PRIMARY};
                background-color: {PRIMARY_LIGHT};
            }}
            #catBtn:checked {{
                background-color: {PRIMARY};
                color: white;
                border-color: {PRIMARY};
            }}
            #scrollArea {{
                background: transparent;
                border: none;
            }}
            #cardContainer {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: #ccd6e0;
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {PRIMARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    # ── 窗口关闭逻辑 ─────────────────────────────

    def closeEvent(self, event):
        """点 X 或 Alt+F4 → 最小化到系统托盘，程序继续运行"""
        self.hide()
        event.ignore()

    # ── 卡片刷新 ─────────────────────────────────

    def refresh_cards(self):
        """根据当前分类和搜索条件，重新加载卡片列表"""
        # 清除现有卡片
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        # 移除 stretch（如果有的话）
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 查询数据
        search_text = self.search_input.text()
        items = self.data_store.get_items(
            category=self._category,
            search=search_text,
            limit=500,
        )

        # 创建卡片
        for item in items:
            card = CardWidget(item)
            card.clicked.connect(self._on_card_clicked)
            card.pin_toggled.connect(self._on_pin_toggled)
            card.delete_requested.connect(self._on_delete_requested)
            self.card_layout.addWidget(card)
            self._cards.append(card)

        # 底部弹簧
        self.card_layout.addStretch()

        # 更新状态栏
        count = len(items)
        cat_name = {'all': '全部', 'text': '文字', 'image': '图片'}[self._category]
        self.status_label.setText(f"共 {count} 条记录 · {cat_name}")

    # ── 事件处理 ─────────────────────────────────

    def _on_search(self, text: str):
        """搜索文本变化 → 刷新卡片"""
        self.refresh_cards()

    def _on_category(self, category: str):
        """切换分类"""
        self._category = category
        # 更新按钮状态
        for key, btn in self.cat_buttons.items():
            btn.setChecked(key == category)
        self.refresh_cards()

    def _on_card_clicked(self, item: dict):
        """点击卡片 → 复制内容到剪贴板"""
        item_id = item['id']
        item_type = item['type']

        success = False
        if item_type == 'text':
            content = item.get('content', '')
            success = copy_text_to_clipboard(content)
        elif item_type == 'image':
            image_path = item.get('image_path', '')
            if image_path and os.path.exists(image_path):
                success = copy_image_to_clipboard(image_path)

        if success:
            # 短暂显示"已复制"提示
            self.status_label.setText("✅ 已复制到剪贴板！")
            QTimer.singleShot(2000, lambda: self.refresh_cards())
        else:
            self.status_label.setText("❌ 复制失败")
            QTimer.singleShot(2000, lambda: self.refresh_cards())

        # 复制后自动隐藏窗口
        QTimer.singleShot(150, self.hide)

    def _on_pin_toggled(self, item_id: int):
        """置顶/取消置顶"""
        self.data_store.toggle_pin(item_id)
        self.refresh_cards()

    def _on_delete_requested(self, item_id: int):
        """删除确认"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这条记录吗？\n（图片记录会同时删除图片文件）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.data_store.delete_item(item_id)
            self.refresh_cards()

    def show_and_focus(self):
        """Show window and focus the search box."""
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()
        self.search_input.selectAll()
        self.refresh_cards()
