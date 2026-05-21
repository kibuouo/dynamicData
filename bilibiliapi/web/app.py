from flask import Flask, jsonify, render_template
from bilibiliapi.web.db import query_all_videos
app = Flask(__name__)
@app.route("/")
def index():
    return "B站热门视频数据看板启动成功"


@app.route("/api/videos")
def videos():
    data = query_all_videos()
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)