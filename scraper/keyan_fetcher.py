"""
scraper/keyan_fetcher.py — 课题抓取模块

职责：
  使用已登录的 Session 抓取科研人课题列表，返回原始字段字典列表。
  只负责"拿数据"，不做任何清洗，清洗交给 parser 层。

两种模式（根据抓包结果选择其一）：
  模式 A：接口直接返回 JSON  → 用 fetch_by_api()       ← 优先
  模式 B：页面 HTML 渲染     → 用 fetch_by_html()      ← 备选

TODO（开发前需确认）：
  1. 打开科研人网站，F12 → Network → XHR/Fetch，找课题列表请求
  2. 如果有 JSON 接口 → 填写 API_URL，使用 fetch_by_api
  3. 如果只有 HTML  → 用浏览器"检查元素"找到列表容器的 CSS class，
     填写 fetch_by_html 里的选择器
"""

import logging
import requests
from config import KEYAN_API_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class KeyanFetcher:
    def __init__(self, session: requests.Session):
        self.session = session

    def fetch_by_api(self, page: int = 1, limit: int = 30) -> list[dict]:
        """
        调用课题列表 JSON 接口，返回原始字典列表。
        """
        payload = {
            "release_time_seven": "",
            "pro_id": "",
            "project_industry_id": "",
            "release_time_thirty": "",
            "type_id": "",
            "project_status_end": "",
            "project_status": "",
            "help_money_start": "",
            "help_money_end": "",
            "limit": limit,
            "page": page,
            "title": "",
            "user_id": 15494,
            "hits": "",
            "funds_order": "",
            "date_order": "",
            "dete_end_order": "",
        }
        resp = self.session.post(KEYAN_API_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        raw_list = data.get("data", {}).get("data", [])

        logger.info(f"接口返回 {len(raw_list)} 条课题（第 {page} 页）")
        return raw_list

    def fetch_all_by_api(self) -> list[dict]:
        """只取第一页最新课题（10条）。"""
        batch = self.fetch_by_api(page=1)
        logger.info(f"共抓取 {len(batch)} 条课题")
        return batch
