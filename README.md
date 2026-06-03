# Bilibili 热门视频数据抓取项目


## 主要功能

- 抓取 B 站热门视频列表
- 清洗视频标题、UP 主、播放量、发布时间等字段
- 保存数据到 `data/cleaned/`
- 使用 SQLite 保存视频信息和每次抓取的快照
- 启动本地 Web 看板查看表格和图表

## 环境准备

建议在项目根目录创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

如果在 WSL/Linux 中运行，请单独创建 Linux 的虚拟环境，不要复用 Windows 的 `.venv`。

## 运行爬虫

在项目根目录执行：

```powershell
python -m bilibiliapi
```

运行成功后，会生成：

```text
data/
├── raw_popular.json
└── cleaned/
    ├── bilibili_popular.csv
    ├── bilibili_popular.json
    └── bilibili_data.db
```

爬虫数量可以在 `settings.yaml` 中调整：

```yaml
spider:
  max_items: 1000
  max_pages: 100
  page_size: 20
```

## 启动 Web 看板

先运行爬虫生成数据库，然后执行：

```powershell
python -m bilibiliapi.web.app
```

浏览器访问：

```text
http://127.0.0.1:5000/
```

接口数据地址：

```text
http://127.0.0.1:5000/api/videos
```
