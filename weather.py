import pandas as pd
import requests
import ast
from datetime import datetime, timedelta

# 設定目標日期 (請修改為您想查詢的日期)
TARGET_DATE_STR = "2025-12-26" 

def get_weather_data(lat, lon, target_date_str):
    """
    根據經緯度和日期抓取天氣資料。
    若日期在未來 14 天內，抓取預報（含降雨機率）。
    若超出範圍，抓取前一年同一天的歷史資料（含降雨量）。
    """
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    
    # 判斷是否在預報範圍內 (Open-Meteo 免費版預報約提供 7-14 天)
    days_diff = (target_date - today).days
    is_forecast = 0 <= days_diff <= 14
    
    data = {
        "source": "Forecast",
        "date_used": target_date_str,
        "temp_max": None,
        "temp_min": None,
        "precip_prob_or_sum": None, # 預報為機率(%)，歷史為雨量(mm)
        "unit": ""
    }
    
    try:
        if is_forecast:
            # --- 呼叫預報 API ---
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "start_date": target_date_str,
                "end_date": target_date_str
            }
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                res_json = response.json()
                daily = res_json.get("daily", {})
                data["temp_max"] = daily.get("temperature_2m_max", [None])[0]
                data["temp_min"] = daily.get("temperature_2m_min", [None])[0]
                data["precip_prob_or_sum"] = daily.get("precipitation_probability_max", [None])[0]
                data["unit"] = "% (機率)"
            else:
                print(f"Forecast API Error: {response.status_code}")
                
        else:
            # --- 呼叫歷史 API (前一年) ---
            # 計算前一年同一天
            try:
                past_date = target_date.replace(year=target_date.year - 1)
            except ValueError: # 處理 2/29 閏年問題
                past_date = target_date.replace(year=target_date.year - 1, day=28)
            
            past_date_str = past_date.strftime("%Y-%m-%d")
            data["source"] = "History (Fallback)"
            data["date_used"] = past_date_str
            
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": past_date_str,
                "end_date": past_date_str,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto"
            }
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                res_json = response.json()
                daily = res_json.get("daily", {})
                data["temp_max"] = daily.get("temperature_2m_max", [None])[0]
                data["temp_min"] = daily.get("temperature_2m_min", [None])[0]
                data["precip_prob_or_sum"] = daily.get("precipitation_sum", [None])[0]
                data["unit"] = "mm (雨量)"
            else:
                print(f"Archive API Error: {response.status_code}")

    except Exception as e:
        print(f"Error fetching data: {e}")

    return data

# 1. 讀取 CSV
df = pd.read_csv("taiwan_attractions.csv")

# 2. 解析經緯度 (Position 欄位是字串格式的字典，需解析)
def parse_position(pos_str):
    try:
        pos_dict = ast.literal_eval(pos_str)
        return pos_dict.get('PositionLat'), pos_dict.get('PositionLon')
    except:
        return None, None

df[['Lat', 'Lon']] = df['Position'].apply(lambda x: pd.Series(parse_position(x)))

# 3. 測試抓取前 5 筆資料的天氣 (避免大量呼叫導致等待過久)
# 若要跑全部資料，請移除 .head()
print(f"開始查詢日期: {TARGET_DATE_STR} 的天氣資訊...\n")

results = []
total_count = len(df) # 或是 len(df.head(5)) 如果您只跑前五筆

# 這裡建議移除 .head(5) 以執行全部，或是改用 .head(10) 測試
for index, row in df.iterrows(): 
    
    # 加入進度提示，每處理一筆就印出 (或是每 100 筆印一次以免太雜)
    # print(f"正在處理第 {index+1} 筆：{row['City']} {row['District']} - {row['ScenicSpotName']}...")

    if pd.notnull(row['Lat']) and pd.notnull(row['Lon']):
        weather = get_weather_data(row['Lat'], row['Lon'], TARGET_DATE_STR)
        
        # 判斷是否成功抓到資料 (檢查 temp_max 是否有值)
        status = "成功" if weather["temp_max"] is not None else "失敗"
        
        results.append({
            "城市": row['City'],          # <--- 新增：城市
            "區域": row['District'],      # <--- 新增：行政區
            "景點名稱": row['ScenicSpotName'],
            "抓取狀態": status,           # <--- 新增：狀態欄位方便檢查
            "最高溫": weather["temp_max"],
            "最低溫": weather["temp_min"],
            "降雨數據": weather["precip_prob_or_sum"],
            "單位": weather["unit"],
            "備註": ""
        })
    else:
        results.append({
            "城市": row['City'],
            "區域": row['District'],
            "景點名稱": row['ScenicSpotName'],
            "抓取狀態": "略過",
            "備註": "無座標資料"
        })

# 4. 顯示與檢查結果
result_df = pd.DataFrame(results)

# --- 驗證方法 A: 顯示各城市的成功筆數 ---
print("\n=== 執行結果統計 (依城市) ===")
# 統計每個城市有多少筆是「成功」的
success_summary = result_df[result_df['抓取狀態'] == '成功'].groupby('城市').size()
print(success_summary)

# --- 驗證方法 B: 檢查是否有失敗的案例 ---
failed_rows = result_df[result_df['抓取狀態'] == '失敗']
if not failed_rows.empty:
    print(f"\n警告：有 {len(failed_rows)} 筆資料抓取失敗，請檢查網路或 API 限制。")
else:
    print("\n完美！所有座標有效的景點皆已成功抓取資料。")

# 儲存結果
# result_df.to_csv("weather_results_with_city.csv", index=False, encoding="utf-8-sig")