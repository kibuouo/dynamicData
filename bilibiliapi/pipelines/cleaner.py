import pandas as pd


class Cleaner:
    """负责把解析后的列表转成 DataFrame，并做基础清洗。"""

    @staticmethod
    def clean_videos(parsed_data):
        """接收视频列表，返回清洗后的 DataFrame。"""
        if not parsed_data:
            return pd.DataFrame()

        df = pd.DataFrame(parsed_data)

        # 把接口返回的 Unix 时间戳转换成 pandas 能识别的日期时间。
        df["pub_date"] = pd.to_datetime(
            df["pub_date"],
            unit="s",
            errors="coerce",
        )

        # 同一个视频只保留一条记录。
        df = df.drop_duplicates(subset=["bvid"])

        # 过滤播放量为空或播放量为 0 的异常数据。
        df = df[df["播放量"].fillna(0) > 0]

        return df
