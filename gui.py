"""
gui.py — 课题搭子可视化抓取工具

双击运行即可，无需命令行。
支持：开始/停止定时抓取、设置抓取页数、设置定时间隔、一键查看记录。
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import logging
import os
import sys
import webbrowser
import traceback
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    KEYAN_HOME_URL, KEYAN_API_URL, KEYAN_USER, KEYAN_PASS,
    BACKEND_URL, BACKEND_USER, BACKEND_PASS,
    BACKEND_FORM_FIELDS, REQUEST_TIMEOUT, REQUEST_HEADERS,
    BROWSER_HEADLESS, POLL_INTERVAL_MINUTES
)
from scraper.keyan_login import login_keyan
from scraper.keyan_fetcher import KeyanFetcher
from parser.topic_parser import TopicParser
from uploader.topic_uploader import TopicUploader
from storage.db import SeenStorage

# ── 线程安全日志队列 ──────────────────────────────────────────────────────
log_queue = queue.Queue()


class QueueHandler(logging.Handler):
    def emit(self, record):
        log_queue.put(self.format(record))


# ── 主窗口 ────────────────────────────────────────────────────────────────
class SpiderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("课题搭子自动抓取工具 v1.0")
        self.root.geometry("820x680")
        self.root.minsize(700, 500)

        self.running = False
        self.worker_busy = False
        self.scheduled_job_id = None
        self.interval_minutes = tk.IntVar(value=POLL_INTERVAL_MINUTES)
        self.fetch_pages = tk.IntVar(value=1)
        self.fetch_limit = tk.IntVar(value=30)
        self.status_text = tk.StringVar(value="就绪")

        self._setup_logging()
        self._build_ui()
        self._start_log_consumer()
        self._check_playwright()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 日志 ──────────────────────────────────────────────────────────────
    def _setup_logging(self):
        os.makedirs("logs", exist_ok=True)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()

        fh = logging.FileHandler("logs/run.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
        root_logger.addHandler(fh)

        qh = QueueHandler()
        qh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"))
        root_logger.addHandler(qh)

        self.logger = logging.getLogger("GUI")

    def _start_log_consumer(self):
        while True:
            try:
                msg = log_queue.get_nowait()
                self._append_log(msg)
            except queue.Empty:
                break
        self.root.after(200, self._start_log_consumer)

    def _append_log(self, msg):
        self.log_area.config(state=tk.NORMAL)
        if "[ERROR]" in msg:
            tag = "ERROR"
        elif "[WARNING]" in msg or "[WARN" in msg:
            tag = "WARNING"
        elif "成功" in msg or "✅" in msg:
            tag = "SUCCESS"
        else:
            tag = "INFO"
        self.log_area.insert(tk.END, msg + "\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    # ── UI 构建 ───────────────────────────────────────────────────────────
    def _build_ui(self):
        main = ttk.Frame(self.root, padding="12")
        main.pack(fill=tk.BOTH, expand=True)

        # 标题
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="🕷️ 课题搭子自动抓取工具",
                  font=("Microsoft YaHei", 18, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, text="数据来源: 科研人  →  存入: 课题小搭子",
                  foreground="gray").pack(side=tk.RIGHT)

        # 设置区域
        settings = ttk.LabelFrame(main, text="抓取设置", padding="10")
        settings.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(settings)
        row1.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row1, text="抓取页数", width=10).pack(side=tk.LEFT)
        ttk.Spinbox(row1, from_=1, to=10, textvariable=self.fetch_pages,
                    width=6).pack(side=tk.LEFT)
        ttk.Label(row1, text="页  (第1页=最新)", foreground="gray").pack(side=tk.LEFT, padx=(4, 20))

        ttk.Label(row1, text="每页条数", width=10).pack(side=tk.LEFT)
        ttk.Combobox(row1, textvariable=self.fetch_limit, values=[10, 20, 30, 50],
                     width=4, state="readonly").pack(side=tk.LEFT)
        ttk.Label(row1, text="条", foreground="gray").pack(side=tk.LEFT, padx=(4, 0))

        row2 = ttk.Frame(settings)
        row2.pack(fill=tk.X)
        ttk.Label(row2, text="定时间隔", width=10).pack(side=tk.LEFT)
        ttk.Spinbox(row2, from_=5, to=120, increment=5,
                    textvariable=self.interval_minutes, width=6).pack(side=tk.LEFT)
        ttk.Label(row2, text="分钟  (到时间自动重复抓取)", foreground="gray").pack(side=tk.LEFT, padx=(4, 0))

        # 按钮区域
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_start = ttk.Button(btn_frame, text="▶  开始定时抓取",
                                    command=self.start, width=18)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop = ttk.Button(btn_frame, text="⏹  停止",
                                   command=self.stop, state=tk.DISABLED, width=10)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_once = ttk.Button(btn_frame, text="🔄  立即执行一次",
                                   command=self.run_once_now, width=16)
        self.btn_once.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(btn_frame, text="📋  查看抓取记录",
                   command=self.open_report, width=16).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(btn_frame, textvariable=self.status_text,
                  foreground="#667eea", font=("Microsoft YaHei", 10, "bold")).pack(
            side=tk.RIGHT, padx=(10, 0))

        # 进度条
        self.progress = ttk.Progressbar(btn_frame, mode="indeterminate", length=100)
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))

        # 日志区域
        log_frame = ttk.LabelFrame(main, text="运行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_area = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 10),
            state=tk.DISABLED, bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white", relief=tk.FLAT
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.tag_config("INFO", foreground="#d4d4d4")
        self.log_area.tag_config("WARNING", foreground="#e5c07b")
        self.log_area.tag_config("ERROR", foreground="#e06c75")
        self.log_area.tag_config("SUCCESS", foreground="#98c379")

    def _check_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
            p = sync_playwright().start()
            try:
                p.chromium.launch(headless=True).close()
            except Exception:
                self._append_log(
                    "[WARNING] 未检测到 Chromium 浏览器，正在自动安装...")
                import subprocess
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True, capture_output=True)
                self._append_log("[SUCCESS] Chromium 安装完成")
            finally:
                p.stop()
        except Exception as e:
            self._append_log(
                f"[WARNING] Playwright 环境检测失败: {e}，首次运行前请执行 一键安装.bat")

    # ── 按钮逻辑 ──────────────────────────────────────────────────────────
    def start(self):
        self.running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_once.config(state=tk.DISABLED)
        self.status_text.set("定时运行中")
        self.progress.start(10)

        self.logger.info("=" * 50)
        self.logger.info("🚀 定时抓取已启动")
        self.logger.info("   抓取页数: %d  每页 %d 条  间隔: %d 分钟",
                         self.fetch_pages.get(), self.fetch_limit.get(),
                         self.interval_minutes.get())
        self.logger.info("=" * 50)

        self._run_once()
        self._schedule_next()

    def stop(self):
        self.running = False
        if self.scheduled_job_id:
            self.root.after_cancel(self.scheduled_job_id)
            self.scheduled_job_id = None

        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_once.config(state=tk.NORMAL)
        self.status_text.set("已停止")
        self.progress.stop()
        self.logger.info("⏸ 定时抓取已停止")

    def run_once_now(self):
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_once.config(state=tk.DISABLED)
        self.status_text.set("执行中...")
        self.progress.start(10)

        def task():
            self._do_scrape()
            self.root.after(0, self._on_once_done)

        threading.Thread(target=task, daemon=True).start()

    def _on_once_done(self):
        self.btn_start.config(state=tk.NORMAL)
        self.btn_once.config(state=tk.NORMAL)
        self.progress.stop()
        if not self.running:
            self.status_text.set("就绪")

    def _schedule_next(self):
        if not self.running:
            return
        ms = self.interval_minutes.get() * 60 * 1000
        self.scheduled_job_id = self.root.after(ms, self._on_timer)

    def _on_timer(self):
        if not self.running:
            return
        self._run_once()
        self._schedule_next()

    def _run_once(self):
        threading.Thread(target=self._do_scrape, daemon=True).start()

    # ── 核心抓取逻辑 ──────────────────────────────────────────────────────
    def _do_scrape(self):
        logger = logging.getLogger("Spider")
        logger.info("=" * 50)
        logger.info("开始本轮任务")
        logger.info("=" * 50)

        storage = SeenStorage()
        parser = TopicParser()
        uploader = TopicUploader()

        try:
            session = login_keyan()
            fetcher = KeyanFetcher(session)

            pages = self.fetch_pages.get()
            limit = self.fetch_limit.get()
            all_raw = []
            for page in range(1, pages + 1):
                try:
                    batch = fetcher.fetch_by_api(page=page, limit=limit)
                    all_raw.extend(batch)
                    logger.info("第 %d 页获取 %d 条", page, len(batch))
                    if len(batch) < limit:
                        break
                except Exception as e:
                    logger.error("第 %d 页获取失败: %s", page, e)
                    break

            logger.info("共抓取 %d 条课题", len(all_raw))

            new_topics = []
            for raw in all_raw:
                parsed = parser.parse(raw)
                if parsed is None:
                    continue
                if storage.contains(parsed["unique_id"]):
                    continue
                new_topics.append(parsed)

            logger.info("新增待写入 %d 条", len(new_topics))

            if not new_topics:
                logger.info("无新课题，本轮结束")
                return

            uploader.start()
            success_count = 0
            for topic in new_topics:
                try:
                    ok = uploader.submit_topic(topic)
                    if ok:
                        storage.mark(topic["unique_id"], topic["title"],
                                     source="科研人", destination="课题小搭子")
                        success_count += 1
                except Exception as e:
                    logger.error("提交失败 [%s]: %s", topic["title"], e)

            logger.info("本轮完成：成功 %d 条，失败 %d 条",
                        success_count, len(new_topics) - success_count)
            logger.info("累计已处理课题：%d 条", storage.count())

        except Exception as e:
            logger.error("任务异常终止：%s", e)
            traceback.print_exc()
        finally:
            try:
                uploader.stop()
            except Exception:
                pass
            logger.info("本轮任务结束")

    # ── 查看记录 ──────────────────────────────────────────────────────────
    def open_report(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "storage", "seen_topics.html")
        if os.path.exists(path):
            webbrowser.open("file:///" + path.replace("\\", "/"))
        else:
            messagebox.showinfo("提示", "暂无记录文件，请先执行一次抓取。")

    def _on_close(self):
        self.running = False
        if self.scheduled_job_id:
            self.root.after_cancel(self.scheduled_job_id)
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = SpiderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()