"""
storage/db.py — 去重存储模块

职责：
  持久化记录已成功提交的课题唯一 ID，防止重复写入后台。
  用 JSON 文件存储，简单可靠，无需数据库。

文件位置：storage/seen_ids.json（自动创建）
"""

import json
import os
import logging

logger = logging.getLogger(__name__)


class SeenStorage:
    def __init__(self, path: str = "storage/seen_ids.json"):
        self.path = path
        self._ids: set[str] = self._load()

    def _load(self) -> set[str]:
        """从文件加载已处理的 ID 集合。文件不存在时返回空集合。"""
        if not os.path.exists(self.path):
            return set()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data)
        except Exception as e:
            logger.warning(f"读取去重文件失败，重置为空：{e}")
            return set()

    def _save(self):
        """将当前 ID 集合写入文件。"""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(list(self._ids), f, ensure_ascii=False, indent=2)

    def contains(self, unique_id: str) -> bool:
        """检查某个课题 ID 是否已处理过。"""
        return unique_id in self._ids

    def mark(self, unique_id: str):
        """标记某个课题 ID 为已处理，并持久化。"""
        self._ids.add(unique_id)
        self._save()

    def count(self) -> int:
        """返回已处理的课题总数。"""
        return len(self._ids)
