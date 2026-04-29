# 课题搭子自动化抓取系统

自动从科研人网站抓取最新课题，写入课题搭子小程序后台，无需人工干预。

## 项目结构

```
keyan_spider/
├── main.py                    # 主入口，定时调度
├── config.py                  # 所有配置（账号/URL/间隔）
├── .env                       # 敏感账号（不提交 Git）
├── requirements.txt           # Python 依赖
│
├── scraper/
│   ├── keyan_login.py         # 登录科研人，返回 Session
│   └── keyan_fetcher.py       # 抓取课题列表和详情
│
├── parser/
│   └── topic_parser.py        # 字段清洗、日期/金额格式化
│
├── uploader/
│   ├── backend_login.py       # 登录课题搭子后台
│   └── topic_uploader.py      # Playwright 自动填表提交
│
├── storage/
│   ├── db.py                  # 已处理课题 ID 的读写封装
│   └── seen_ids.json          # 持久化去重数据（自动生成）
│
└── logs/
    └── run.log                # 运行日志（自动生成）
```

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置账号
复制 `.env.example` 为 `.env`，填入账号密码：
```bash
cp .env.example .env
```

### 3. 运行
```bash
python main.py
```

启动后会立即执行一次，之后每 30 分钟自动执行。

## 开发前必做：抓包确认接口

在动手写代码前，先用浏览器 F12 → Network 标签确认：

1. **科研人课题列表接口 URL**（看 XHR/Fetch 请求）
2. **接口返回的字段名**（title / deadline / amount 等叫什么）
3. **课题搭子后台表单字段**（手动操作一次，记录每个输入框的 label）

把以上信息补充到 `config.py` 的注释 TODO 处，再开始开发。

## 各模块说明

| 模块 | 文件 | 说明 |
|------|------|------|
| 调度 | main.py | 每 30 分钟触发一次完整流程 |
| 抓取 | scraper/ | 登录科研人 → 获取课题数据 |
| 解析 | parser/ | 清洗字段，统一日期/金额格式 |
| 写入 | uploader/ | Playwright 模拟浏览器操作后台 |
| 去重 | storage/ | 已写入课题不重复提交 |
