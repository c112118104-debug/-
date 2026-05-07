taiwan_attractions_with_images = "some_value"  # Or whatever you intended.
import pandas as pd
import requests
import json 
import time
import os
import ast 

# ================= 設定區 =================
API_KEY = 'AIzaSyBCO-HW7lE-v7srY6UaxYIRvKBNoIrOrjk'        # ★ 請填入您的 API Key
SEARCH_ENGINE_ID = 'e1d31d7d8aa63426b'                     # ★ 請填入您的 Search Engine ID (cx)
INPUT_FILE = 'taiwan_attractions.csv'
OUTPUT_FILE = 'taiwan_attractions_with_images.csv'
# =========================================

def search_image(query):
    """
    使用 Google Custom Search API 搜尋圖片
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': API_KEY,
        'cx': SEARCH_ENGINE_ID,
        'q': query,
        'searchType': 'image',  # 指定搜尋圖片
        'num': 1,               # 只抓第一張
        'safe': 'active'        # 開啟安全搜尋
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # 檢查是否有結果
        if 'items' in data and len(data['items']) > 0:
            return data['items'][0]['link']
        else:
            return None
    except Exception as e:
        print(f"搜尋錯誤: {e}")
        return None

def main():
    # 路徑設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, INPUT_FILE)
    output_path = os.path.join(script_dir, OUTPUT_FILE)
    
    print(f"讀取檔案: {input_path}")

    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print("找不到檔案，請確認 CSV 檔名是否正確。")
        return

    # 找出 Picture 是空白或 {} 的資料
    # 我們定義 "空白" 為 NaN, 空字串, 或是 "{}"
    mask = df['Picture'].isnull() | (df['Picture'] == '{}') | (df['Picture'] == '')
    
    missing_count = mask.sum()
    print(f"共有 {missing_count} 筆資料缺少圖片，準備開始搜尋...")
    
    processed_count = 0
    
    for index, row in df[mask].iterrows():
        spot_name = row['ScenicSpotName']
        city = row['City']
        
        # 搜尋關鍵字：縣市 + 景點名稱 (增加準確度)
        query = f"{city} {spot_name}"
        
        print(f"正在搜尋: {query} ...", end="")
        
        img_url = search_image(query)
        
        if img_url:
            # 建立符合格式的字典字串
            # 格式範例: {'PictureUrl1': 'http...', 'PictureDescription1': '景點名'}
            pic_data = {
                'PictureUrl1': img_url,
                'PictureDescription1': spot_name
            }
            df.at[index, 'Picture'] = str(pic_data)
            print(" 成功!")
        else:
            print(" 找不到圖片")
            
        processed_count += 1
        
        # ★ 重要：API 限制保護
        time.sleep(0.5) 
        
        # 建議先測試跑前 98 筆就好，以免額度用光
        if processed_count >= 98:
            print("測試模式：已完成 98 筆，停止執行。")
            break

    # 重新計算目前仍然沒有圖片的筆數
    remaining_mask = df['Picture'].isnull() | (df['Picture'] == '{}') | (df['Picture'] == '')
    remaining_count = remaining_mask.sum()
    print(f"\n目前仍有 {remaining_count} 筆資料無法取得圖片。")

    # 存檔
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"完成！結果已儲存為: {output_path}")

if __name__ == "__main__":
    main()
