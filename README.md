# Bilibili 热门视频数据抓取项目

这个项目用于抓取 B站热门视频数据，并把结果保存为 CSV、JSON 和 SQLite，后续可以通过 Flask 接口查看数据。

## 项目结构

```text
dynamicData/
├── bilibiliapi/
│   ├── __main__.py          # 支持 python -m bilibiliapi 运行
│   ├── main.py              # 主流程入口：抓取、解析、清洗、保存
│   ├── core/
│   │   └── fetcher.py       # 请求配置读取和 B站接口抓取
│   ├── pipelines/
│   │   ├── parser.py        # 从原始 JSON 提取字段
│   │   ├── cleaner.py       # 数据清洗
│   │   └── saver.py         # 保存 CSV、JSON、SQLite
│   └── web/
│       ├── app.py           # Flask Web/API 入口
│       └── db.py            # SQLite 查询函数
├── check_db.py              # 查看 SQLite 表和字段
├── settings.yaml            # 项目配置
├── requirements.txt         # Python 依赖
└── README.md
```

运行后会生成以下数据文件：

```text
data/
├── raw_popular.json
└── cleaned/
    ├── bilibili_popular_top200.csv
    ├── bilibili_popular_top200.json
    └── bilibili_data.db
```

## 环境准备

建议使用虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 运行爬虫

在项目根目录执行：

```powershell
python -m bilibiliapi
```

这个命令会完成三件事：

1. 请求 B站热门视频接口。
2. 提取视频标题、UP主、播放量、发布时间等字段。
3. 保存到 `data/cleaned/` 目录。

爬虫参数在 `settings.yaml` 中配置：

```yaml
spider:
  max_pages: 100
  page_size: 20
```

当前主流程默认最多保存 200 条数据，对应 `bilibiliapi/main.py` 里的 `MAX_ITEMS = 200`。

## 检查数据库

爬虫运行成功后，可以查看 SQLite 中有哪些表和字段：

```powershell
python check_db.py
```

如果提示数据库不存在，先运行：

```powershell
python -m bilibiliapi
```

## 启动 Web API

先确认已经生成数据库，然后运行：

```powershell
python -m bilibiliapi.web.app
```

浏览器访问：

```text
http://127.0.0.1:5000/
http://127.0.0.1:5000/api/videos
```

`/api/videos` 会返回 SQLite 中的热门视频 JSON 数据。

## 常见问题

如果运行时提示 `ModuleNotFoundError`，通常是因为没有安装依赖或没有在项目根目录运行。先确认已经执行：

```powershell
pip install -r requirements.txt
```

如果 `/api/videos` 返回空列表，通常是因为还没有生成数据库。先运行：

```powershell
python -m bilibiliapi
```

如果抓取失败，先检查网络是否能访问 B站接口，并降低请求量。这个项目只做普通学习用途，不做高频请求。

## Git 提交建议

这次整理适合单独提交一次：

```powershell
git add .
git commit -m "Refactor project structure and add README"
```
