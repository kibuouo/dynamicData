def analyze_category(df):
    result = {
        df.groupby("分区").agg(
            视频数量=("bvid", "count"),
            总播放量=("播放量", "sum"),
            平均播放量=("播放量", "mean"),
            平均点赞率=("点赞率", "mean"),
        ).sort_values("播放量", ascending=False).reset_index()
    }
    return result