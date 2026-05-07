import pandas as pd
import numpy as np

# 1. 讀取原始檔案
df = pd.read_csv('taiwan_attractions.csv')

# 2. 準備新的一筆資料
new_row = {
    'ID': df['ID'].max() + 1,  # 自動取得最後一個 ID + 1
    'City': '新北市',
    'District': '板橋區',
    'ScenicSpotName': '板橋後站商圈(府中商圈)',
    'Address': '新北市板橋區中山路一段',
    'Description': '府中商圈位於舊板橋車站後站，原為板橋後站商圈，在舊車站拆除後人潮驟減，後由於四鐵共構並設有名為「府中站」之捷運出口，並經商家積極規劃，已再次成為遊客指定前往的大台北地區商圈之一。',
    'OpenTime': '全天候開放',
    'Phone': '886-2-29686911',
    'TravelInfo': '搭乘捷運板南線至府中站下車。',
    'WebsiteUrl': np.nan,
    'Class1': '購物娛樂類',
    'Class2': np.nan,
    'Class3': np.nan,
    'Keyword': '板橋區,府中商圈,購物,美食',
    'ParkingInfo': '府後立體停車場、板橋國小地下停車場',
    'Position': "{'PositionLon': 121.4592, 'PositionLat': 25.0089, 'GeoHash': ''}",
    'Level': np.nan,
    'Picture': "{}",  # 若無圖片則維持空字典字串
    'MapUrl': np.nan,
    'DescriptionDetail': '府中商圈集合精品時尚、流行文化和多元美食於一體，是新北市境內唯一與現代、流行及年輕族群接軌的商圈，加上鄰近三鐵共構的板橋車站，串聯週邊商場、美食，結合新舊商圈不同的特性，創造出從老人到小孩都愛的逛街環境。'
}

# 3. 加入資料並存檔
new_df = pd.DataFrame([new_row])
df_updated = pd.concat([df, new_df], ignore_index=True)
df_updated.to_csv('taiwan_attractions_updated.csv', index=False)

print("新增成功！")