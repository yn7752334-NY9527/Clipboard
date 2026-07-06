项目简介
这是一个 Windows 剪贴板历史管理器（Clipboard History Manager），用 Python 编写，基于 PySide6（Qt for Python）构建。

它能做什么
自动记录剪贴板内容 — 只要程序在运行，它会自动捕获你复制（Ctrl+C）的所有文字和图片，保存到本地 SQLite 数据库中。
历史面板 — 打开主窗口可以看到所有历史记录，按时间倒序排列，置顶的排在前面。
搜索 — 支持关键词搜索文字内容。
分类筛选 — 可按"全部 / 文字 / 图片"分类查看。
点击即复制 — 点击任意卡片，内容会自动复制回剪贴板，然后窗口自动隐藏。
置顶 — 重要的记录可以置顶，不会被自动清理。
删除 — 支持单条删除和全部清空。
自动清理 — 超过 7 天的记录会自动清除；超过 500 条上限时，最旧的未置顶记录会被自动删除。
系统托盘 — 关闭窗口后程序最小化到系统托盘，不会退出，继续在后台监控剪贴板。
单实例运行 — 重复打开 exe 会自动激活已有窗口，不会启动多个实例。
技术栈
技术	用途
Python 3	主语言
PySide6 (Qt)	GUI 界面（主窗口、卡片列表、搜索框、托盘图标）
SQLite	本地数据存储（记录文字和图片路径）
pywin32	访问 Windows 剪贴板 API
Pillow	图片处理（截图保存、缩略图生成）
PyInstaller	打包成单个 exe 文件
如何安装和使用
方式一：直接运行 exe（最简单）

dist/ 目录下应该有打包好的 ClipboardManager.exe，双击即可运行。
运行后主窗口出现，系统托盘也有图标，右键托盘图标可进行清空/退出操作。
方式二：从源码运行


# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行
python main.py
方式三：自己打包成 exe


pip install pyinstaller
pyinstaller ClipboardManager.spec
快捷键
关闭窗口 — 点 X 或 Alt+F4 会最小化到托盘，不会退出程序
要真正退出，右键系统托盘图标 → 退出
文件结构
文件	作用
main.py	入口，初始化所有模块、单实例检测
main_window.py	主窗口界面（搜索、分类、卡片列表）
clipboard_monitor.py	剪贴板监控（每 500ms 轮询）
data_store.py	SQLite 数据库操作（增删改查、自动清理）
card_widget.py	每条记录的可点击卡片组件
image_utils.py	图片保存、缩略图、复制到剪贴板
tray_manager.py	系统托盘图标和菜单
hotkey_manager.py	快捷键管理
数据存储位置
所有数据（数据库、图片、缩略图）保存在：


%APPDATA%\ClipboardManager\
即 C:\Users\你的用户名\AppData\Roaming\ClipboardManager\
