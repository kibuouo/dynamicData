import pandas as pd

class Cleaner:
    @staticmethod
    def clean_videos(parsed_data):
        """接收上一步的列表，转化为 DataFrame 并清洗】"""
        if not parsed_data:
            return pd.DataFrame()
            
        # 1. 转化为 DataFrame表格
        df = pd.DataFrame(parsed_data)
        
        # 2. 清洗逻辑：时间戳转换
        df['pub_date'] = pd.to_datetime(df['pub_timestamp'], unit='s')
        
        # 3. 清洗逻辑：去重
        df = df.drop_duplicates(subset=['bvid'])
        
        # 4. 清洗逻辑：过滤掉播放量为 0 的异常数据
        df = df[df['播放量'] > 0]
        
        return df