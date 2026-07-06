"""
数据存储模块 — 基于 SQLite

管理剪贴板记录的生命周期：
- 新增文字/图片记录
- 查询（支持分类筛选、搜索、排序）
- 置顶/取消置顶
- 删除
- 自动清理（超过 7 天 / 超过 500 条）
"""

import os
import sqlite3
import threading
from datetime import datetime, timedelta
from image_utils import get_data_dir


DB_PATH = os.path.join(get_data_dir(), 'clipboard.db')
MAX_ITEMS = 500
MAX_AGE_DAYS = 7


class DataStore:
    """剪贴板数据存储，线程安全"""

    def __init__(self):
        self._lock = threading.Lock()
        self._init_db()
        self.cleanup_expired()
        self.enforce_limit()

    # ── 数据库初始化 ─────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """建表（如果不存在）"""
        with self._lock:
            conn = self._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clipboard_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK(type IN ('text', 'image')),
                    content TEXT,
                    image_path TEXT,
                    thumb_path TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    is_pinned INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()

    # ── 增 ───────────────────────────────────────────

    def add_text(self, text: str) -> int | None:
        """
        添加文字记录。返回新记录的 ID。
        如果文字与最新一条记录相同，跳过并返回 None。
        """
        text = text.strip()
        if not text:
            return None

        with self._lock:
            conn = self._get_conn()

            # 检查是否与上一条相同（去重）
            last = conn.execute(
                "SELECT content FROM clipboard_items "
                "WHERE type='text' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if last and last['content'] == text:
                conn.close()
                return None

            cursor = conn.execute(
                "INSERT INTO clipboard_items (type, content) VALUES ('text', ?)",
                (text,)
            )
            item_id = cursor.lastrowid
            conn.commit()
            conn.close()

        self.enforce_limit()
        return item_id

    def add_image(self, image_path: str, thumb_path: str) -> int | None:
        """
        添加图片记录。返回新记录的 ID。
        """
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(
                "INSERT INTO clipboard_items (type, image_path, thumb_path) "
                "VALUES ('image', ?, ?)",
                (image_path, thumb_path)
            )
            item_id = cursor.lastrowid
            conn.commit()
            conn.close()

        self.enforce_limit()
        return item_id

    # ── 查 ───────────────────────────────────────────

    def get_items(self, category: str = 'all', search: str = '',
                  limit: int = 500) -> list[dict]:
        """
        获取剪贴板记录列表。

        Args:
            category: 'all' | 'text' | 'image'
            search: 搜索关键词（仅对文字内容生效）
            limit: 最大返回条数

        Returns:
            记录列表（字典格式），按置顶优先 + 时间倒序排列
        """
        with self._lock:
            conn = self._get_conn()

            conditions = []
            params = []

            if category == 'text':
                conditions.append("type = 'text'")
            elif category == 'image':
                conditions.append("type = 'image'")

            if search.strip():
                conditions.append("content LIKE ?")
                params.append(f"%{search.strip()}%")

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            query = (
                f"SELECT * FROM clipboard_items {where} "
                "ORDER BY is_pinned DESC, created_at DESC "
                "LIMIT ?"
            )
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            conn.close()

            return [dict(row) for row in rows]

    def get_item_by_id(self, item_id: int) -> dict | None:
        """根据 ID 获取单条记录"""
        with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM clipboard_items WHERE id = ?", (item_id,)
            ).fetchone()
            conn.close()
            return dict(row) if row else None

    # ── 改 ───────────────────────────────────────────

    def toggle_pin(self, item_id: int) -> bool:
        """
        切换置顶状态。返回切换后的状态（True = 已置顶）。
        """
        with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT is_pinned FROM clipboard_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not row:
                conn.close()
                return False

            new_state = 0 if row['is_pinned'] else 1
            conn.execute(
                "UPDATE clipboard_items SET is_pinned = ? WHERE id = ?",
                (new_state, item_id)
            )
            conn.commit()
            conn.close()
            return new_state == 1

    # ── 删 ───────────────────────────────────────────

    def delete_item(self, item_id: int) -> bool:
        """
        删除单条记录（包括关联的图片文件）。
        """
        with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM clipboard_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not row:
                conn.close()
                return False

            # 删除关联的图片文件
            if row['image_path'] and os.path.exists(row['image_path']):
                try:
                    os.remove(row['image_path'])
                except OSError:
                    pass
            if row['thumb_path'] and os.path.exists(row['thumb_path']):
                try:
                    os.remove(row['thumb_path'])
                except OSError:
                    pass

            conn.execute("DELETE FROM clipboard_items WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            return True

    def clear_all(self):
        """清空所有记录和图片文件"""
        with self._lock:
            conn = self._get_conn()
            rows = conn.execute("SELECT image_path, thumb_path FROM clipboard_items").fetchall()
            for row in rows:
                for path in (row['image_path'], row['thumb_path']):
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass
            conn.execute("DELETE FROM clipboard_items")
            conn.commit()
            conn.close()

    # ── 清理 ─────────────────────────────────────────

    def cleanup_expired(self):
        """
        清理超过 7 天的未置顶记录。
        """
        cutoff = (datetime.now() - timedelta(days=MAX_AGE_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
        with self._lock:
            conn = self._get_conn()

            # 先获取要删除的图片路径
            rows = conn.execute(
                "SELECT image_path, thumb_path FROM clipboard_items "
                "WHERE is_pinned = 0 AND created_at < ?",
                (cutoff,)
            ).fetchall()
            for row in rows:
                for path in (row['image_path'], row['thumb_path']):
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass

            conn.execute(
                "DELETE FROM clipboard_items WHERE is_pinned = 0 AND created_at < ?",
                (cutoff,)
            )
            conn.commit()
            conn.close()

    def enforce_limit(self):
        """
        确保总记录数不超过 MAX_ITEMS（500）。
        超出时删除最旧的未置顶记录。
        """
        with self._lock:
            conn = self._get_conn()
            count = conn.execute("SELECT COUNT(*) as cnt FROM clipboard_items").fetchone()['cnt']

            if count > MAX_ITEMS:
                excess = count - MAX_ITEMS
                # 找到最旧的未置顶记录
                rows = conn.execute(
                    "SELECT id, image_path, thumb_path FROM clipboard_items "
                    "WHERE is_pinned = 0 "
                    "ORDER BY created_at ASC LIMIT ?",
                    (excess,)
                ).fetchall()
                for row in rows:
                    for path in (row['image_path'], row['thumb_path']):
                        if path and os.path.exists(path):
                            try:
                                os.remove(path)
                            except OSError:
                                pass
                    conn.execute("DELETE FROM clipboard_items WHERE id = ?", (row['id'],))

            conn.commit()
            conn.close()
