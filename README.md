# 📋 剪贴板历史管理器

> Clipboard History Manager — 自动记录剪贴板文字与图片，随时回溯、搜索、复用。

一个轻量级的 Windows 剪贴板历史管理工具，后台静默运行，自动捕获你复制过的所有文字和图片，支持搜索、分类、置顶，点击即可回贴。

---

## ✨ 功能特性

- **自动记录** — 后台监控剪贴板，文字和图片（截图、复制的图片文件）自动入库
- **一键回贴** — 点击历史记录卡片，内容立即复制回剪贴板，窗口自动隐藏
- **🔍 搜索筛选** — 支持关键词搜索 + 按「全部 / 文字 / 图片」分类查看
- **📌 置顶保护** — 重要记录可置顶，不会被自动清理
- **⏱️ 智能清理** — 超过 **7 天**的记录自动过期；总记录数超过 **500 条**时删除最旧的未置顶记录
- **🖥️ 系统托盘** — 关闭窗口即最小化到托盘，后台持续运行不打扰
- **⌨️ 全局快捷键** — `Ctrl+Shift+V` 一键呼出/隐藏面板（自动选择可用组合键）
- **🔌 开机自启** — 托盘菜单一键开关，重启电脑自动运行
- **🔒 单实例运行** — 重复启动自动激活已有窗口，不会多开
- **🎨 清爽 UI** — 淡蓝色主题，卡片式布局，圆角阴影，时间友好显示（刚刚 / N 分钟前 / 昨天）

## 🖼️ 界面预览

| 主窗口 | 系统托盘菜单 |
|:---:|:---:|
| 搜索框 + 分类标签 + 卡片列表 | 打开面板 / 清空历史 / 开机自启 / 退出 |

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| **Python 3.10+** | 主语言 |
| **PySide6** (Qt for Python) | GUI 界面、系统托盘、事件循环 |
| **SQLite** | 本地数据存储 |
| **pywin32** | Windows 剪贴板 API、全局快捷键注册 |
| **Pillow** | 图片处理（格式转换、缩略图、模糊预览） |
| **PyInstaller** | 打包为独立 exe |

## 📦 安装与运行

### 方式一：直接运行 exe（推荐）

从 [Releases](../../releases) 下载 `ClipboardManager.exe`，双击运行即可，无需安装任何依赖。

### 方式二：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/<你的用户名>/clipboard-manager.git
cd clipboard-manager

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

### 方式三：自行打包

```bash
pip install pyinstaller
pyinstaller ClipboardManager.spec
# 输出在 dist/ClipboardManager/ 目录下
```

## 📖 使用说明

| 操作 | 方式 |
|------|------|
| 打开面板 | 双击 exe / 左键点击托盘图标 / 按 `Ctrl+Shift+V` |
| 隐藏面板 | 点窗口 ✕ / 点击面板外部 / 再按 `Ctrl+Shift+V` |
| 复制历史记录 | 点击任意卡片，内容即复制到剪贴板，窗口自动收起 |
| 搜索 | 在顶部搜索框输入关键词（仅搜索文字内容） |
| 分类筛选 | 点击「全部」「📝 文字」「🖼️ 图片」切换 |
| 置顶 | 点击卡片右侧 📍 按钮，变为 📌 即已置顶 |
| 删除 | 点击卡片右侧 ✕ 按钮，确认后删除 |
| 清空全部 | 右键托盘图标 → 🗑️ 清空全部历史 |
| 开机自启 | 右键托盘图标 → 🔌 开机自动启动（打勾即启用） |
| 退出程序 | 右键托盘图标 → ❌ 退出 |

> **注意：** 关闭窗口（点 ✕ 或 Alt+F4）仅隐藏到托盘，程序继续在后台运行。要完全退出请通过托盘菜单。

## 📁 文件结构

```
clipboard-manager/
├── main.py                 # 程序入口，初始化所有模块
├── main_window.py          # 主窗口 UI（搜索框、分类栏、卡片列表）
├── clipboard_monitor.py    # 剪贴板监控（每 500ms 轮询）
├── data_store.py           # SQLite 数据库操作与自动清理
├── card_widget.py          # 单条记录的卡片组件
├── image_utils.py          # 图片抓取、保存、缩略图、回贴
├── tray_manager.py         # 系统托盘图标与右键菜单
├── hotkey_manager.py       # 全局快捷键注册与管理
├── requirements.txt        # Python 依赖
├── ClipboardManager.spec   # PyInstaller 打包配置
└── README.md
```

## 💾 数据存储

所有数据保存在：

```
%APPDATA%\ClipboardManager\
├── clipboard.db            # SQLite 数据库
├── images\                 # 原始图片
├── thumbnails\             # 模糊缩略图
└── error.log               # 异常日志（如有）
```

## 🔧 依赖

```
PySide6 >= 6.5.0
pywin32 >= 306
Pillow >= 10.0.0
```

## 📝 License

MIT License

## 👤 作者

**Ronny** — © 2026

---

如果这个工具对你有帮助，欢迎点个 ⭐ Star！
