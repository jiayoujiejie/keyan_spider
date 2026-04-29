"""
config.py — 全局配置
所有可变参数集中在这里管理，敏感字段从 .env 读取。
"""
import os
from dotenv import load_dotenv

load_dotenv()  # 自动读取 .env 文件

# ─── 科研人（数据来源） ────────────────────────────────────────────────────────
KEYAN_HOME_URL = "https://keyanpro.com/pc/content/reportingGuidelines"

KEYAN_API_URL  = "https://keyanpro.com/api/demo/ProjectGov/list"

KEYAN_USER = os.getenv("KEYAN_USER", "")
KEYAN_PASS = os.getenv("KEYAN_PASS", "")

# ─── 课题搭子后台 ─────────────────────────────────────────────────────────────
BACKEND_URL  = "http://8.137.124.187:5001/crud_manager_modern_v2.html"
BACKEND_USER = os.getenv("BACKEND_USER", "admin")
BACKEND_PASS = os.getenv("BACKEND_PASS", "mBaklVZNt4")

# TODO: 抓包/手动操作后，填入后台表单的字段 label（中文名）
# 例如后台表单里写的是"项目名称"还是"课题标题"，要和实际界面一致
BACKEND_FORM_FIELDS = {
    "title":       "createTitle",
    "institution": "createSource",
    "link":        "createUrl",
    "start_time":  "createStartTime",
    "deadline":    "createDeadline",
    "description": "createFulltext",
}

# ─── 调度配置 ─────────────────────────────────────────────────────────────────
POLL_INTERVAL_MINUTES = 30   # 每隔多少分钟执行一次

# ─── 存储 ────────────────────────────────────────────────────────────────────
SEEN_IDS_FILE = "storage/seen_ids.json"

# ─── 请求配置 ────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT    = 15    # 单次请求超时秒数
REQUEST_MAX_RETRY  = 3     # 最大重试次数
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ─── Playwright ───────────────────────────────────────────────────────────────
# 调试时改为 False，可以看到浏览器界面，方便确认操作是否正确
BROWSER_HEADLESS = False
