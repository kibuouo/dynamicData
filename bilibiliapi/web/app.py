from flask import Flask, jsonify, render_template, request

from bilibiliapi.web.db import (
    query_all_videos,
    query_category_summary,
    query_video_summary,
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


def create_app():
    """创建 Flask 应用。"""
    app = Flask(__name__)
    app.jinja_env.filters["number"] = format_number
    app.jinja_env.filters["duration"] = format_duration

    @app.route("/")
    def index():
        videos = query_all_videos(limit=50)
        summary = query_video_summary()
        categories = query_category_summary(limit=8)
        return render_template(
            "index.html",
            videos=videos,
            summary=summary,
            categories=categories,
        )

    @app.route("/api/videos")
    def videos():
        limit = request.args.get("limit", default=200, type=int)
        limit = min(max(limit, 1), 500)
        data = query_all_videos(limit=limit)
        return jsonify(data)

    @app.route("/api/summary")
    def summary():
        data = {
            "summary": query_video_summary(),
            "categories": query_category_summary(limit=10),
        }
        return jsonify(data)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
