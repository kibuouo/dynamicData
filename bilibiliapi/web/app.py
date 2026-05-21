from flask import Flask, jsonify

from bilibiliapi.web.db import query_all_videos


def create_app():
    """创建 Flask 应用。"""
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "B站热门视频数据看板启动成功"

    @app.route("/api/videos")
    def videos():
        data = query_all_videos()
        return jsonify(data)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
