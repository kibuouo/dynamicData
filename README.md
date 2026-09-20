# Bilibili 热门视频数据抓取项目

## 云端运行和定时更新

线上看板：https://bili-insight-2026.glitterkibo.chatgpt.site

部署分为两部分：

- **GitHub Actions** 运行本仓库的 Python 采集程序，不依赖个人电脑开机。
- **Sites** 运行 `sites/` 中的 Web 看板，使用持久化 D1 数据库保存视频和历史快照。

Sites 的 Worker 环境不直接运行 Flask / pandas，所以不把本地 Flask 启动命令当作站点部署命令。原有 Flask 看板继续用于本地运行。

`.github/workflows/refresh-data.yml` 每 6 小时运行一次：北京时间每天 **02:17、08:17、14:17、20:17**。GitHub 的定时任务可能排队延迟，并非精确计时服务。网站每 5 分钟重新读取一次已保存的数据，不会因访客访问而抓取 B 站。

每次最多采集 200 条热门视频和 100 条全站排行榜视频，去重后同步。翻页请求间隔 1 秒；上游拒绝请求时不绕过限制、不密集重试。热门采集失败时任务失败并保留云端旧数据；仅排行榜失败时更新热门数据，页面明确提示排行榜不可用，不冒用历史排名。

### 已配置的云端参数

| 位置 | 名称 | 用途 |
| --- | --- | --- |
| GitHub Actions → Variables | `SITES_URL` | 上述站点地址 |
| GitHub Actions → Secrets | `SITES_SYNC_TOKEN` | 写入云端数据的专用密钥 |
| Sites 生产环境 → Secret | `SITES_SYNC_TOKEN` | 与 GitHub 相同的密钥 |

密钥不保存在源码或前端中。`POST /api/ingest` 验证密钥、数据结构和时间戳，再以一个数据库事务保存快照；重复请求不重复写入。`GET /api/videos` 仅展示最近一批成功采集的数据，历史数据仍保存在数据库中。

### 手动更新与排查

在 GitHub 的 **Actions → Refresh cloud data → Run workflow** 可立即运行一次。失败时展开运行日志查看采集或同步步骤；数据源拒绝访问时等待下一次计划运行，不要高频重试。成功采集的 JSON 保存在 Actions artifact 中 7 天。

本地只测试采集而不上传：

```powershell
python -m bilibiliapi.cloud_sync --no-upload --max-items 20
```

运行验证：

```powershell
python -m unittest discover -s tests -v
cd sites
npm ci
npm test
npm run build
```

`sites/.openai/hosting.json` 绑定现有站点；`sites/server/` 是云端接口，`sites/dist/` 是页面源文件，`sites/drizzle/` 是数据库迁移。Sites 另有平台管理的发布仓库，修改 GitHub 中的 `sites/` **不会自动发布页面**，需要用 Sites 发布流程同步源文件、构建并部署；日常数据更新通过接口完成，无需重新发布页面。不要在已部署的数据库上改写旧迁移。

公开仓库连续 60 天没有活动时，GitHub 可能自动停用定时工作流；可在 Actions 中重新启用。数据长时间不更新时先检查工作流是否启用、运行日志、上游接口可用性和密钥是否一致。

参考：[GitHub 定时触发说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)、[Cloudflare D1 数据库事务批处理](https://developers.cloudflare.com/d1/worker-api/d1-database/#batch)。


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
