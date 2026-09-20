"""在云端低频采集，并把完整快照同步到 Sites；失败时不覆盖旧数据。"""

import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from bilibiliapi.analysis.metrics import rate_metrics
from bilibiliapi.pipelines.cleaner import Cleaner
from bilibiliapi.pipelines.parser import Parser
from bilibiliapi.spiders.popular_spider import Spider


def require_items(response, label):
    if not isinstance(response, dict) or response.get("code") != 0:
        code = response.get("code") if isinstance(response, dict) else None
        raise RuntimeError(f"{label}请求失败（code={code}），保留上次云端数据")
    items = response.get("data", {}).get("list")
    if not isinstance(items, list):
        raise RuntimeError(f"{label}响应缺少视频列表")
    return items


def build_capture(popular, ranking, fetched_at):
    if not popular:
        raise RuntimeError("热门列表为空，不上传不完整快照")
    ranks = {item["bvid"]: (i, item.get("score")) for i, item in enumerate(ranking, 1)}
    frame = rate_metrics(Cleaner.clean_videos(Parser.parse_popular_items(popular + ranking)))
    # pandas 将缺失值输出为 null，避免 JSON 出现 NaN / Infinity。
    rows = json.loads(frame.to_json(orient="records", date_format="iso", force_ascii=False))
    videos = []
    for row in rows:
        rank, score = ranks.get(row["bvid"], (None, None))
        videos.append({
            "bvid": row["bvid"], "aid": row["aid"], "cid": row["cid"],
            "title": row["视频标题"], "up": row["UP主"], "category": row["分区"],
            "pubDate": row["pub_date"], "url": row["视频链接"],
            "cover": row["封面链接"], "duration": row["时长"],
            "views": row["播放量"], "danmaku": row["弹幕数"], "replies": row["评论数"],
            "likes": row["点赞数"], "coins": row["投币数"], "favorites": row["收藏数"],
            "heat": row["综合热度"], "rank": rank, "score": score,
        })
    if not videos:
        raise RuntimeError("清洗后没有有效的热门数据")
    return {
        "id": "scheduled-" + fetched_at, "fetchedAt": fetched_at,
        "source": "GitHub Actions / Bilibili popular" + (" + ranking/v2" if ranking else " (ranking unavailable)"),
        "rankingAvailable": bool(ranking), "videos": videos,
    }


def collect_capture(max_items=200, spider=None, sleep=time.sleep):
    if not 1 <= max_items <= 400:
        raise ValueError("max_items 必须在 1 到 400 之间")
    spider = spider or Spider()
    popular = []
    for page in range(1, (max_items + spider.page_size - 1) // spider.page_size + 1):
        if page > 1:
            sleep(1)
        items = require_items(spider.get_popular_page(page), f"热门第 {page} 页")
        popular.extend(items)
        if len(popular) >= max_items or not items:
            break
    sleep(1)
    try:
        ranking = require_items(spider.get_ranking(rid=0, ranking_type="all"), "全站排行榜")[:100]
    except RuntimeError as error:
        logging.warning("排行榜不可用，本次仅更新热门视频：%s", error)
        ranking = []
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return build_capture(popular[:max_items], ranking, fetched_at)


def upload_capture(capture, site_url, token):
    if not site_url.startswith("https://") or not token:
        raise ValueError("请配置 HTTPS SITES_URL 和 SITES_SYNC_TOKEN")
    response = requests.post(
        site_url.rstrip("/") + "/api/ingest",
        json=capture, headers={"Authorization": f"Bearer {token}"},
        timeout=90, allow_redirects=False,
    )
    if response.status_code != 200:
        raise RuntimeError(f"云端同步失败（HTTP {response.status_code}），请查看站点日志")
    result = response.json()
    if result.get("id") != capture["id"] or result.get("videoCount") != len(capture["videos"]):
        raise RuntimeError("云端返回的快照信息与上传内容不一致")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-items", type=int, default=200)
    parser.add_argument("--output", type=Path, default=Path("data/cloud_capture.json"))
    parser.add_argument("--no-upload", action="store_true", help="仅采集和保存本地 JSON")
    args = parser.parse_args()
    site_url, token = os.getenv("SITES_URL", ""), os.getenv("SITES_SYNC_TOKEN", "")
    if not args.no_upload and (not site_url or not token):
        parser.error("未配置 SITES_URL 或 SITES_SYNC_TOKEN")
    capture = collect_capture(args.max_items)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(capture, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    if not args.no_upload:
        upload_capture(capture, site_url, token)
    print(f"采集完成：{len(capture['videos'])} 条；UTC 时间：{capture['fetchedAt']}；上传：{not args.no_upload}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
