"""
parser/topic_parser.py — 数据清洗与解析模块

职责：
  接收 scraper 层返回的原始字典，输出干净、格式统一的字典。
  包括：日期格式统一、金额提取、字段重命名、生成去重用的唯一 ID。

不依赖网络，纯本地逻辑，可以独立单元测试。

TODO（开发前需确认）：
  1. 科研人返回的原始字段名是什么（title? name? projectName?）
  2. 日期格式是什么（"2024-06-30" / "2024年6月30日" / 时间戳？）
  3. 金额格式是什么（"50万元" / "500000" / "50"单位万？）
  把确认好的字段名填入 _extract_raw_fields() 的 TODO 处。
"""

import re
import hashlib
import logging
import dateparser

logger = logging.getLogger(__name__)


class TopicParser:

    def parse(self, raw: dict) -> dict | None:
        """
        清洗一条原始课题数据。
        成功返回标准字典，失败返回 None（由 main.py 跳过）。
        """
        try:
            fields = self._extract_raw_fields(raw)
            return {
                "unique_id": self._make_unique_id(fields),
                "title":     fields["title"],
                "deadline":  self._parse_date(fields.get("deadline", "")),
                "amount":    self._parse_amount(fields.get("amount", "")),
                "category":  fields.get("category", "").strip(),
                # 保留原始数据，方便调试
                "_raw": raw,
            }
        except Exception as e:
            logger.warning(f"解析失败，跳过该条数据：{e} | 原始数据：{raw}")
            return None

    # ── 字段提取 ─────────────────────────────────────────────────────────────
    def _extract_raw_fields(self, raw: dict) -> dict:
        """
        从原始字典中提取标准字段。
        字段映射基于科研人接口的实际返回。
        """
        return {
            "title":    raw.get("PROJECT_NAME", ""),
            "deadline": raw.get("PROJECT_DATE_END", ""),
            "amount":   raw.get("PROJECT_FUNDS") or raw.get("PROJECT_FUNDS_AUTO", ""),
            "category": raw.get("PROJECT_TYPE", ""),
            "source_id": str(raw.get("IN_PROJECT_GOV_ID", "")),
        }

    # ── 日期解析 ─────────────────────────────────────────────────────────────
    def _parse_date(self, text: str) -> str:
        """
        将各种格式的日期文本统一为 YYYY-MM-DD。
        支持："2024-06-30" / "2024年6月30日" / "6月30日" / 时间戳（毫秒）
        """
        if not text:
            return ""

        # 如果是数字时间戳（毫秒）
        if str(text).isdigit():
            from datetime import datetime
            ts = int(text) / 1000 if len(str(text)) == 13 else int(text)
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

        # 用 dateparser 解析自然语言日期
        dt = dateparser.parse(str(text), languages=["zh"])
        if dt:
            return dt.strftime("%Y-%m-%d")

        logger.warning(f"日期解析失败，保留原始值：{text}")
        return str(text)

    # ── 金额解析 ─────────────────────────────────────────────────────────────
    def _parse_amount(self, text: str) -> str:
        """
        提取金额数字，统一为元为单位的整数字符串。
        例如："50万元" → "500000"，"100" → "100"
        """
        if not text:
            return ""

        text = str(text)
        nums = re.findall(r"[\d.]+", text)
        if not nums:
            return text  # 解析不出数字，原样返回

        val = float(nums[0])
        if "万" in text:
            val *= 10000
        elif "亿" in text:
            val *= 100_000_000

        return str(int(val))

    # ── 唯一 ID 生成 ─────────────────────────────────────────────────────────
    def _make_unique_id(self, fields: dict) -> str:
        """
        生成用于去重的唯一标识。
        优先用原始 source_id；若没有，用「标题+截止日期」的 MD5。
        """
        if fields.get("source_id"):
            return fields["source_id"]

        # fallback：用标题+截止日期组合哈希
        key = f"{fields['title']}_{fields.get('deadline', '')}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()
