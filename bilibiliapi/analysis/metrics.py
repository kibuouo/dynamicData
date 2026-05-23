def rate_metrics(df):
    df=df.copy()
    df["点赞率"] = df["点赞数"] / df["播放量"]
    df["投币率"] = df["投币数"] / df["播放量"]
    df["收藏率"] = df["收藏数"] / df["播放量"]
    df["弹幕率"] = df["弹幕数"] / df["播放量"]
    return df
