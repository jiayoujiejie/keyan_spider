"""
uploader/topic_uploader.py — 自动写入课题搭子后台

职责：
  用 Playwright 模拟浏览器，登录课题搭子后台（Streamlit 应用），
  自动填写并提交课题表单。

为什么用 Playwright 而不是直接调接口：
  课题搭子后台是 Streamlit 应用（端口 8501），Streamlit 的交互
  通过 WebSocket 实现，没有标准 REST API，只能模拟浏览器点击。

TODO（开发前必须手动操作后台一次，记录以下信息）：
  1. 登录页面的输入框 label（"用户名"还是"账号"？"密码"？）
  2. 登录按钮的文字（"登录"还是"Login"？）
  3. 进入新增课题页面的菜单路径（侧边栏点什么？）
  4. 新增表单的各字段 label（和 config.py 里 BACKEND_FORM_FIELDS 对应）
  5. 提交按钮的文字

调试技巧：
  把 config.py 里 BROWSER_HEADLESS 改为 False，
  可以看到浏览器实际操作过程，方便确认步骤是否正确。
"""

import logging
from playwright.sync_api import sync_playwright, Page, TimeoutError as PwTimeout
from config import (
    BACKEND_URL, BACKEND_USER, BACKEND_PASS,
    BACKEND_FORM_FIELDS, BROWSER_HEADLESS
)

logger = logging.getLogger(__name__)

WAIT_TIMEOUT = 15_000


class TopicUploader:
    def __init__(self):
        self._pw      = None
        self._browser = None
        self._page: Page = None

    def start(self):
        self._pw      = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=BROWSER_HEADLESS)
        self._page    = self._browser.new_page()
        self._login()

    def stop(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception as e:
            logger.warning(f"关闭浏览器时出错（可忽略）：{e}")

    def _login(self):
        page = self._page
        logger.info("正在打开课题搭子后台...")
        page.goto(BACKEND_URL, timeout=30_000)
        page.wait_for_load_state("networkidle")

        try:
            page.wait_for_selector("#loginUsername", timeout=WAIT_TIMEOUT)
            page.locator("#loginUsername").fill(BACKEND_USER)
            page.locator("#loginPassword").fill(BACKEND_PASS)
            page.locator("button.btn.btn-primary:has-text('登录')").click()
            page.wait_for_load_state("networkidle")
            logger.info("后台登录成功")
        except PwTimeout:
            logger.warning("未找到登录表单，可能已登录或后台无需登录，继续执行")

    def submit_topic(self, topic: dict) -> bool:
        page = self._page
        logger.info(f"开始提交课题：{topic['title']}")

        try:
            self._navigate_to_add_page()
            self._fill_form(topic)
            self._submit_form()
            logger.info(f"✅ 提交成功：{topic['title']}")
            return True

        except Exception as e:
            logger.error(f"❌ 提交失败：{topic['title']} | 原因：{e}")
            try:
                screenshot_path = f"logs/error_{topic.get('unique_id', 'unknown')}.png"
                page.screenshot(path=screenshot_path)
                logger.info(f"错误截图已保存：{screenshot_path}")
            except Exception:
                pass
            return False

    def _navigate_to_add_page(self):
        page = self._page
        page.locator("text=新增项目").first.click()
        page.wait_for_load_state("networkidle")

    def _fill_form(self, topic: dict):
        page = self._page
        fields = BACKEND_FORM_FIELDS
        raw = topic.get("_raw", {})

        page.locator(f"#{fields['title']}").fill(topic["title"])

        institution = raw.get("PROJECT_GOVERNMENT", "")
        if institution:
            page.locator(f"#{fields['institution']}").fill(institution)

        project_url = raw.get("PROJECT_URL", "")
        if project_url:
            page.locator(f"#{fields['link']}").fill(project_url)

        if topic.get("deadline"):
            page.locator(f"#{fields['deadline']}").fill(topic["deadline"])

        start_ts = raw.get("PROJECT_DATE_START")
        if start_ts:
            from datetime import datetime
            start_str = datetime.fromtimestamp(int(start_ts)).strftime("%Y-%m-%d")
            page.locator(f"#{fields['start_time']}").fill(start_str)

        content = raw.get("PROJECT_CONTENT", "")
        if content:
            page.locator(f"#{fields['description']}").fill(content[:2000])

        page.locator("#aiGenerateText").click()
        page.wait_for_timeout(2000)

    def _submit_form(self):
        page = self._page
        page.locator("button.btn.btn-primary:has-text('创建项目')").click()
        page.wait_for_load_state("networkidle")
