REQUIRED_COLUMNS = ["播放量", "弹幕数", "点赞数", "投币数", "收藏数"]


def rate_metrics(df):
    df = df.copy()
    if df.empty:
        return df

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(f"计算指标缺少必要字段: {missing_columns}")

    df["点赞率"] = df["点赞数"] / df["播放量"]
    df["投币率"] = df["投币数"] / df["播放量"]
    df["收藏率"] = df["收藏数"] / df["播放量"]
    df["弹幕率"] = df["弹幕数"] / df["播放量"]
   
    df["综合热度"] = (
        df["点赞率"] * 0.4
        + df["投币率"] * 0.1
        + df["收藏率"] * 0.1
        + df["弹幕率"] * 0.4
    )
    df["疑似异常"] = (
        (df["播放量"] > df["播放量"].quantile(0.8)) &
        (df["弹幕率"] < df["弹幕率"].quantile(0.1)) |
        (0.13 < df["综合热度"]) & (df["综合热度"] < 0.20)
    )
    return df
