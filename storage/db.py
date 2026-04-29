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
from datetime import datetime

logger = logging.getLogger(__name__)


class SeenStorage:
    def __init__(self, path: str = "storage/seen_ids.json"):
        self.path = path
        self._records: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {uid: {"id": uid} for uid in data}
            if isinstance(data, dict):
                return data
            return {}
        except Exception as e:
            logger.warning(f"读取去重文件失败，重置为空：{e}")
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._records, f, ensure_ascii=False, indent=2)
        self._export_html()

    def _export_html(self):
        html_path = os.path.join(os.path.dirname(self.path), "seen_topics.html")
        records = []
        for i, (uid, rec) in enumerate(reversed(self._records.items()), 1):
            records.append({
                "no": i,
                "title": rec.get("title", ""),
                "source": rec.get("source", ""),
                "destination": rec.get("destination", ""),
                "marked_at": rec.get("marked_at", ""),
            })
        import json as _json
        data_js = _json.dumps(records, ensure_ascii=False)
        total = len(records)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>课题抓取记录</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
        background: #f5f7fa;
        padding: 30px 20px;
    }}
    .container {{
        max-width: 1000px;
        margin: 0 auto;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        overflow: hidden;
    }}
    .header {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        padding: 24px 30px;
    }}
    .header h1 {{
        font-size: 22px;
        font-weight: 600;
    }}
    .header .count {{
        margin-top: 6px;
        font-size: 14px;
        opacity: 0.85;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }}
    th {{
        background: #f8f9fc;
        color: #606266;
        font-size: 14px;
        font-weight: 600;
        text-align: left;
        padding: 12px 12px;
        border-bottom: 2px solid #e4e7ed;
    }}
    td {{
        padding: 12px 12px;
        font-size: 14px;
        color: #303133;
        border-bottom: 1px solid #ebeef5;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    th:nth-child(1), td:nth-child(1) {{ width: 50px; }}
    th:nth-child(2), td:nth-child(2) {{ white-space: normal; word-break: break-all; }}
    th:nth-child(3), td:nth-child(3) {{ width: 75px; }}
    th:nth-child(4), td:nth-child(4) {{ width: 85px; }}
    th:nth-child(5), td:nth-child(5) {{ width: 155px; }}
    .table-wrapper {{
        overflow-x: auto;
    }}
    tr:hover td {{
        background: #f5f7fa;
    }}
    .title-cell {{
        font-weight: 500;
    }}
    .empty {{
        text-align: center;
        padding: 60px 20px;
        color: #909399;
        font-size: 15px;
    }}
    .pagination {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        padding: 20px;
        flex-wrap: wrap;
    }}
    .pagination button {{
        min-width: 36px;
        height: 36px;
        padding: 0 12px;
        border: 1px solid #dcdfe6;
        border-radius: 6px;
        background: #fff;
        color: #606266;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .pagination button:hover:not(:disabled) {{
        color: #667eea;
        border-color: #667eea;
    }}
    .pagination button.active {{
        background: #667eea;
        color: #fff;
        border-color: #667eea;
    }}
    .pagination button:disabled {{
        opacity: 0.4;
        cursor: not-allowed;
    }}
    .pagination .info {{
        font-size: 13px;
        color: #909399;
        margin: 0 8px;
    }}
    .footer {{
        text-align: center;
        padding: 16px;
        color: #c0c4cc;
        font-size: 12px;
    }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📋 课题抓取记录</h1>
        <div class="count">共 {total} 条已提交课题</div>
    </div>
    <div class="table-wrapper">
    <table>
        <thead><tr><th>序号</th><th>课题名称</th><th>数据来源</th><th>存入位置</th><th>提交时间</th></tr></thead>
        <tbody id="table-body"></tbody>
    </table>
    </div>
    <div id="empty-msg" class="empty" style="display:none;">暂无记录</div>
    <div class="pagination" id="pager"></div>
    <div class="footer">自动生成 · 每次提交后更新</div>
</div>
<script>
var DATA = {data_js};
var PAGE_SIZE = 20;
var currentPage = 1;
var totalPages = Math.ceil(DATA.length / PAGE_SIZE) || 1;

function render() {{
    var tbody = document.getElementById('table-body');
    var empty = document.getElementById('empty-msg');
    var pager = document.getElementById('pager');
    if (DATA.length === 0) {{
        tbody.innerHTML = '';
        empty.style.display = '';
        pager.innerHTML = '';
        return;
    }}
    empty.style.display = 'none';
    var start = (currentPage - 1) * PAGE_SIZE;
    var end = Math.min(start + PAGE_SIZE, DATA.length);
    var html = '';
    for (var i = start; i < end; i++) {{
        var r = DATA[i];
        html += '<tr><td>' + r.no + '</td><td class="title-cell">' + r.title + '</td><td>' + r.source + '</td><td>' + r.destination + '</td><td>' + r.marked_at + '</td></tr>';
    }}
    tbody.innerHTML = html;

    var btnHtml = '';
    btnHtml += '<button onclick="goPage(1)" ' + (currentPage === 1 ? 'disabled' : '') + '>首页</button>';
    btnHtml += '<button onclick="goPage(currentPage - 1)" ' + (currentPage === 1 ? 'disabled' : '') + '>上一页</button>';
    var startPg = Math.max(1, currentPage - 2);
    var endPg = Math.min(totalPages, currentPage + 2);
    for (var p = startPg; p <= endPg; p++) {{
        btnHtml += '<button class="' + (p === currentPage ? 'active' : '') + '" onclick="goPage(' + p + ')">' + p + '</button>';
    }}
    btnHtml += '<button onclick="goPage(currentPage + 1)" ' + (currentPage === totalPages ? 'disabled' : '') + '>下一页</button>';
    btnHtml += '<button onclick="goPage(totalPages)" ' + (currentPage === totalPages ? 'disabled' : '') + '>末页</button>';
    btnHtml += '<span class="info">第 ' + currentPage + ' / ' + totalPages + ' 页</span>';
    pager.innerHTML = btnHtml;
}}

function goPage(p) {{
    if (p < 1 || p > totalPages) return;
    currentPage = p;
    render();
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

render();
</script>
</body>
</html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

    def contains(self, unique_id: str) -> bool:
        return unique_id in self._records

    def mark(self, unique_id: str, title: str = "", source: str = "", destination: str = ""):
        self._records[unique_id] = {
            "id": unique_id,
            "title": title,
            "source": source,
            "destination": destination,
            "marked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        while len(self._records) > 60:
            oldest_key = next(iter(self._records))
            del self._records[oldest_key]
            logger.info(f"自动清理最旧记录：{oldest_key}")
        self._save()

    def count(self) -> int:
        return len(self._records)
