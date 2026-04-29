"""
scraper/keyan_login.py — 科研人登录模块

职责：
  登录科研人网站，返回一个携带登录态 Cookie 的 requests.Session。
  后续所有抓取请求都复用这个 Session，无需重复登录。

TODO（开发前需确认）：
  1. 打开科研人登录页，F12 → Network → 找到登录请求（通常是 POST /login 或 /api/login）
  2. 确认请求体字段名（是 username/password 还是 phone/pwd 还是其他）
  3. 确认登录成功的判断方式（返回 token？还是 Set-Cookie？还是跳转？）
  4. 把确认好的信息填入下方 TODO 处
"""

import logging
import requests
from config import KEYAN_USER, KEYAN_PASS, REQUEST_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def login_keyan() -> requests.Session:
    """
    登录科研人，返回已登录的 Session。
    失败时抛出异常，由 main.py 的 try/except 统一捕获。
    """
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)

    login_url = "https://keyanpro.com/api/demo/Register/login"

    payload = {
        "user_login": KEYAN_USER,
        "user_pass":  KEYAN_PASS,
    }

    logger.info("正在登录科研人...")
    resp = session.post(login_url, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    # 登录成功后响应体是空的，服务端通过 Set-Cookie 维持 Session
    # 返回 200 即表示登录成功（非 200 会触发 raise_for_status）
    logger.info("科研人登录成功")
    return session
