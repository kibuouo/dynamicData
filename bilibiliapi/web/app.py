from threading import Lock

from flask import Flask, jsonify, render_template, request
from bilibiliapi.main import run as refresh_local_data
from bilibiliapi.spiders.popular_spider import Spider
from bilibiliapi.web.db import (
    query_all_videos,
    query_category_summary,
    query_online_ranking,
    query_ranking_summary,
    query_ranking_videos,
    query_video_summary,
    save_online_snapshots,
)


def format_number(value):
    """把较大的数字显示成更容易阅读的格式。"""
    if value is None:
        return "0"

    value = int(value)
    if value >= 10000:
        return f"{value / 10000:.1f}万"
    return f"{value:,}"


def format_duration(seconds):
    """把秒数转换成 mm:ss 格式。"""
    if seconds is None:
        return "-"

    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}"


def format_heat(value):
    """把综合热度这种小数显示成百分比。"""
    if value is None:
        return "-"

    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "-"


def is_anomaly(value):
    """判断 SQLite 里保存的疑似异常值是否代表 True。"""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "是"}
    return bool(value)


def create_app():
    """创建 Flask 应用。"""
    app = Flask(__name__)
    app.jinja_env.filters["number"] = format_number
    app.jinja_env.filters["duration"] = format_duration
    app.jinja_env.filters["heat"] = format_heat
    app.jinja_env.filters["anomaly"] = is_anomaly
    spider = Spider()
    refresh_lock = Lock()

    @app.route("/")
    def index():
        videos = query_all_videos(limit=50)
        ranking_videos = query_ranking_videos(limit=50)
        summary = query_video_summary()
        ranking_summary = query_ranking_summary()
        categories = query_category_summary(limit=8)
        online_ranking = query_online_ranking(limit=8)
        return render_template(
            "index.html",
            videos=videos,
            ranking_videos=ranking_videos,
            summary=summary,
            ranking_summary=ranking_summary,
            categories=categories,
            online_ranking=online_ranking,
            online_total_limit=spider.online_total_limit,
        )

    @app.route("/api/videos")
    def videos():
        limit = request.args.get("limit", default=200, type=int)
        limit = min(max(limit, 1), 500)
        order_by = request.args.get("order_by", default="播放量")
        if order_by not in {"播放量", "综合热度"}:
            order_by = "播放量"
        data = query_all_videos(limit=limit, order_by=order_by)
        return jsonify(data)

    @app.route("/api/summary")
    def summary():
        data = {
            "summary": query_video_summary(),
            "categories": query_category_summary(limit=10),
        }
        return jsonify(data)

    @app.route("/api/online-totals", methods=["POST"])
    def online_totals():
        videos = request.get_json(silent=True) or []
        videos = videos[:spider.online_total_limit]
        results = []

        for video in videos:
            bvid = video.get("bvid")
            cid = video.get("cid")
            aid = video.get("aid")

            if not bvid or not cid:
                results.append({
                    "success": False,
                    "bvid": bvid,
                    "count": None,
                    "message": "缺少 bvid 或 cid",
                })
                continue

            data = spider.get_video_online_total(
                bvid=bvid,
                cid=cid,
                aid=aid,
            )
            count = data.get("count") if data else None
            if count is not None:
                try:
                    count = int(count)
                except (TypeError, ValueError):
                    count = None

            results.append({
                "success": data is not None,
                "bvid": bvid,
                "cid": cid,
                "aid": aid,
                "count": count,
                "message": None if data else "获取在线人数失败",
            })

        save_online_snapshots(results)
        return jsonify(results)

    @app.route("/api/online-ranking")
    def online_ranking():
        limit = request.args.get("limit", default=10, type=int)
        limit = min(max(limit, 1), 50)
        return jsonify(query_online_ranking(limit=limit))

    @app.route("/api/ranking")
    def ranking():
        limit = request.args.get("limit", default=50, type=int)
        limit = min(max(limit, 1), 200)
        return jsonify({
            "summary": query_ranking_summary(),
            "videos": query_ranking_videos(limit=limit),
        })

    @app.route("/api/refresh-data", methods=["POST"])
    def refresh_data():
        if not refresh_lock.acquire(blocking=False):
            return jsonify({
                "success": False,
                "message": "数据更新正在进行中，请稍后再试。",
            }), 409

        try:
            refresh_local_data()
        except Exception as error:
            app.logger.exception("刷新数据失败")
            return jsonify({
                "success": False,
                "message": str(error),
            }), 500
        finally:
            refresh_lock.release()

        return jsonify({
            "success": True,
            "message": "数据已更新。",
        })

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
