import requests
import pandas as pd
import json
import time

# 1. 定義目標 API URL
# 這是 TDX 平台的「公開版」API，不需要登入或金鑰
# 我們使用 $top=10000 嘗試一次抓取所有資料
api_url = "https://tdx.transportdata.tw/api/basic/v2/Tourism/ScenicSpot?%24top=10000&%24format=JSON"

# 2. 定義一個函數來獲取資料
def fetch_data(url):
    print("🚀 正在開始下載景點資料 (使用免登入公開 API)...")
    try:
        # 設定 headers 偽裝成瀏覽器，增加成功率
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        
        # 發送 GET 請求
        response = requests.get(url, headers=headers, timeout=30) # 設定 30 秒超時
        
        # 檢查 HTTP 狀態碼是否為 200 (成功)
        if response.status_code == 200:
            print("✅ 資料下載成功！")
            # 解析 JSON 資料
            data = response.json()
            return data
        else:
            print(f"❌ 下載失敗，狀態碼：{response.status_code}")
            print(f"錯誤訊息：{response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 請求發生錯誤：{e}")
        return None
    except json.JSONDecodeError:
        print("❌ 解析 JSON 失敗，可能非 JSON 格式或資料損毀。")
        return None

# 3. 定義一個函數來處理並儲存資料
def process_and_save(data, filename="taiwan_attractions.csv"):
    if data is None or not data:
        print("沒有資料可供處理。")
        return

    print("🔄 正在處理資料並轉換為 DataFrame...")
    
    try:
        df = pd.DataFrame(data)
        
        print(f"👍 資料轉換成功！總共 {len(df)} 筆景點。")
        
        # 4. 儲存為 CSV 檔案
        # 使用 encoding='utf-8-sig' 確保在 Excel 中打開中文不會亂碼
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"🎉 成功！資料已儲存至 {filename}")
        
    except Exception as e:
        print(f"❌ 資料處理或儲存時發生錯誤：{e}")


# --- 程式執行主體 ---
if __name__ == "__main__":
    start_time = time.time()
    
    # 執行獲取資料
    raw_data = fetch_data(api_url)
    
    # 執行處理和儲存
    process_and_save(raw_data)
    
    end_time = time.time()
    print(f"總共花費 {end_time - start_time:.2f} 秒。")