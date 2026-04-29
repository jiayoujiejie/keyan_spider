"""
main.py — 主入口与定时调度

运行方式：
  python main.py

行为：
  1. 启动时立即执行一次完整流程
  2. 之后每 POLL_INTERVAL_MINUTES 分钟自动执行一次
  3. Ctrl+C 退出

完整流程：
  登录科研人 → 抓取课题列表 → 过滤已处理 → 解析清洗 → 写入后台 → 记录去重
"""

import logging
import os
import schedule
import time

from config import POLL_INTERVAL_MINUTES
from scraper.keyan_login import login_keyan
from scraper.keyan_fetcher import KeyanFetcher
from parser.topic_parser import TopicParser
from uploader.topic_uploader import TopicUploader
from storage.db import SeenStorage

# ── 日志配置 ─────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/run.log", encoding="utf-8"),
        logging.StreamHandler(),   # 同时输出到控制台
    ]
)
logger = logging.getLogger(__name__)


# ── 核心任务 ──────────────────────────────────────────────────────────────────
def run_once():
    """执行一次完整的抓取→解析→写入流程。"""
    logger.info("=" * 50)
    logger.info("开始本轮任务")
    logger.info("=" * 50)

    storage  = SeenStorage()
    parser   = TopicParser()
    uploader = TopicUploader()

    try:
        # 1. 登录科研人，获取 Session
        session = login_keyan()
        fetcher = KeyanFetcher(session)

        # 2. 抓取课题列表
        # TODO: 根据抓包结果选择 fetch_by_api() 或 fetch_by_html()
        raw_topics = fetcher.fetch_all_by_api()
        # raw_topics = fetcher.fetch_by_html()

        # 3. 过滤已处理课题
        new_topics = []
        for raw in raw_topics:
            parsed = parser.parse(raw)
            if parsed is None:
                continue
            if storage.contains(parsed["unique_id"]):
                logger.debug(f"跳过已处理：{parsed['title']}")
                continue
            new_topics.append(parsed)

        logger.info(f"共抓取 {len(raw_topics)} 条，新增待写入 {len(new_topics)} 条")

        if not new_topics:
            logger.info("无新课题，本轮结束")
            return

        # 4. 启动浏览器，逐条写入后台
        uploader.start()
        success_count = 0
        for topic in new_topics:
            ok = uploader.submit_topic(topic)
            if ok:
                storage.mark(topic["unique_id"])
                success_count += 1

        logger.info(f"本轮完成：成功 {success_count} 条，失败 {len(new_topics) - success_count} 条")
        logger.info(f"累计已处理课题：{storage.count()} 条")

    except Exception as e:
        logger.error(f"任务异常终止：{e}", exc_info=True)

    finally:
        uploader.stop()
        logger.info("本轮任务结束")


# ── 调度器 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"课题搭子自动化脚本启动，每 {POLL_INTERVAL_MINUTES} 分钟执行一次")

    # 启动时立即执行一次
    run_once()

    # 注册定时任务
    schedule.every(POLL_INTERVAL_MINUTES).minutes.do(run_once)

    # 保持运行
    while True:
        schedule.run_pending()
        time.sleep(60)
