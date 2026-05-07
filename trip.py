import streamlit as st
import pandas as pd
import ast
import os
import json
import time
import random
import string
import re
import graphviz
import google.generativeai as genai
import urllib.parse
from datetime import datetime, timedelta, date
import requests
from io import BytesIO
import math

# --- 1. 設定頁面配置 (必須放在最前面) ---
st.set_page_config(page_title="台灣旅遊小幫手", page_icon="✨", layout="wide")

# --- 2. API 設定 ---
# ⚠️ 請將此處換成您真實有效的 Google Gemini API Key
GOOGLE_API_KEY = "AIzaSyBGwFSHPMTyc-yJlPuXwDZpYqS-WlJsVQo"

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 1. 行程生成 (使用 2.5 Pro 以確保邏輯與格式精準)
    model = genai.GenerativeModel('models/gemini-2.5-pro', generation_config={"response_mime_type": "application/json"})
    
    # 2. 聊天對話 (使用 3 Flash Preview 以確保回應極快)
    chat_model = genai.GenerativeModel('models/gemini-3-flash-preview') 
    
except Exception as e:
    st.error(f"API 設定錯誤：{e}")

# --- 設定 ---
USER_DB_FILE = 'users_db.json'
HISTORY_DB_FILE = 'history_db.json'
CSV_FILE_NAME = 'taiwan_attractions.csv'

# --- 3. Session State 初始化 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'login'
if 'user_nickname' not in st.session_state:
    st.session_state['user_nickname'] = None
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = None
if 'trip_schedule' not in st.session_state:
    st.session_state['trip_schedule'] = {1: []}
if 'trip_days' not in st.session_state:
    st.session_state['trip_days'] = 1
if 'trip_start_date' not in st.session_state:
    st.session_state['trip_start_date'] = date.today()
if 'trip_end_date' not in st.session_state:
    st.session_state['trip_end_date'] = date.today()
if 'reset_email' not in st.session_state:
    st.session_state['reset_email'] = None
if 'reset_code' not in st.session_state:
    st.session_state['reset_code'] = None
if 'mode' not in st.session_state:
    st.session_state['mode'] = 'menu'
# [新增] 用於儲存 AI 模式的天氣資料
if 'ai_weather_df' not in st.session_state:
    st.session_state['ai_weather_df'] = None

# [新增] 用於儲存手動模式的快取 (包含特徵值與資料表)
if 'manual_weather_cache' not in st.session_state:
    st.session_state['manual_weather_cache'] = {"signature": "", "df": None}
# AI 模式專用 State
if 'ai_submitted' not in st.session_state:
    st.session_state['ai_submitted'] = False
if 'schedule_df' not in st.session_state:
    st.session_state['schedule_df'] = None
if 'input_dest' not in st.session_state:
    st.session_state['input_dest'] = "臺北市" # 預設值
if 'input_days' not in st.session_state:
    st.session_state['input_days'] = 1
if 'ai_start_date' not in st.session_state:
    st.session_state['ai_start_date'] = date.today()
if 'ai_end_date' not in st.session_state:
    st.session_state['ai_end_date'] = date.today()
if 'input_trans' not in st.session_state:
    st.session_state['input_trans'] = ["大眾運輸"]
if 'input_mixed' not in st.session_state:
    st.session_state['input_mixed'] = ""
if 'input_budget' not in st.session_state:
    st.session_state['input_budget'] = "中等預算 (舒適)"
if 'input_trans' not in st.session_state:
    st.session_state['input_trans'] = ["大眾運輸"]
if 'input_mixed' not in st.session_state:
    st.session_state['input_mixed'] = ""

# 對話紀錄
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [
        {"role": "assistant", "content": "你好！我是你的 AI 旅遊顧問。告訴我您預計什麼時候出發？想去哪裡？想怎麼玩？"}
    ]

# --- 4. CSS 樣式整合 ---
st.markdown("""
    <style>
    /* 側邊欄樣式 */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        display: flex !important;
    }
    .day-header {
        font-weight: bold;
        color: #ff4b4b;
        margin-top: 15px;
        margin-bottom: 8px;
        font-size: 1.1em;
        border-bottom: 1px solid #ddd;
    }
    /* 聊天室樣式 */
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    /* 行程表樣式 */
    .itinerary-box {
        font-family: "Microsoft JhengHei", sans-serif;
        line-height: 1.8;
        background-color: #FAFAFA;
        padding: 25px;
        border-radius: 10px;
        border: 1px solid #EEEEEE;
        margin-bottom: 20px;
    }
    .itinerary-day {
        font-size: 18px !important;
        font-weight: bold;
        color: #2E86C1 !important;
        margin-top: 20px;
        margin-bottom: 15px;
        border-bottom: 2px solid #EAEAEA;
        padding-bottom: 5px;
    }
    .itinerary-item, .itinerary-transport {
        font-size: 15px !important;
        color: #555555 !important;
        margin-bottom: 8px;
    }
    .itinerary-transport {
        margin-left: 24px;
        color: #28a745 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. 共用輔助函式 ---
def load_users():
    if not os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'w') as f:
            json.dump({}, f)
        return {}
    try:
        with open(USER_DB_FILE, 'r') as f:
            users = json.load(f)
        return users
    except json.JSONDecodeError:
        return {}

def save_user(email, password, nickname=None):
    users = load_users()
    if nickname is not None:
        users[email] = {"password": password, "nickname": nickname}
    elif email in users:
        users[email]["password"] = password
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f)

def authenticate(email, password):
    users = load_users()
    
    if email in users:
        user_data = users[email]
        
        # [修正] 增加格式檢查：如果是舊版(字串)或非字典，回傳特殊錯誤碼
        if not isinstance(user_data, dict):
            return "DB_FORMAT_ERROR"
            
        # 正常的驗證邏輯
        if user_data.get("password") == password:
            return user_data.get("nickname")
            
    return None
def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

# --- 歷史紀錄相關函式 ---
def load_history():
    if not os.path.exists(HISTORY_DB_FILE):
        with open(HISTORY_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
    try:
        with open(HISTORY_DB_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return history
    except json.JSONDecodeError:
        return []

def save_history_record(email, trip_name, days, schedule_data, mode_type, start_date_str=None, weather_data=None):
    """
    [修改] 新增 weather_data 參數以儲存天氣資訊
    """
    history = load_history()
    new_record = {
        "id": generate_verification_code(8),
        "email": email,
        "trip_name": trip_name,
        "days": days,
        "mode": mode_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start_date": start_date_str,
        "data": schedule_data,
        "weather_content": weather_data # 新增欄位：儲存當時的天氣資料
    }
    history.append(new_record)
    with open(HISTORY_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def update_history_name_in_db(record_id, new_name):
    history = load_history()
    updated = False
    for r in history:
        if r['id'] == record_id:
            r['trip_name'] = new_name
            updated = True
            break
    if updated:
        with open(HISTORY_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)    
    return updated

def delete_history_record(record_id):
    history = load_history()
    new_history = [r for r in history if r['id'] != record_id]
    with open(HISTORY_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, ensure_ascii=False, indent=4)

@st.cache_data
def load_attractions():
    try:
        df = pd.read_csv(CSV_FILE_NAME)
        return df
    except Exception as e:
        return None

attractions_db = load_attractions()
def get_weather_data(lat, lon, target_date_str):
    """
    根據經緯度和日期抓取天氣資料 (整合自 weather.py)。
    """
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"source": "Error", "temp_max": None, "desc": "日期錯誤"}

    today = datetime.now().date()
    days_diff = (target_date - today).days
    is_forecast = 0 <= days_diff <= 14
    
    data = {
        "source": "Forecast" if is_forecast else "History",
        "date_used": target_date_str,
        "temp_max": None,
        "temp_min": None,
        "precip": None, # 預報為機率(%)，歷史為雨量(mm)
        "unit": ""
    }
    
    try:
        if is_forecast:
            # --- Forecast API ---
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
                if daily.get("temperature_2m_max"):
                    data["temp_max"] = daily["temperature_2m_max"][0]
                    data["temp_min"] = daily["temperature_2m_min"][0]
                    data["precip"] = daily["precipitation_probability_max"][0]
                    data["unit"] = "% (降雨機率)"
        else:
            # --- History API (去年同期) ---
            try:
                past_date = target_date.replace(year=target_date.year - 1)
            except ValueError:
                past_date = target_date.replace(year=target_date.year - 1, day=28)
            
            past_date_str = past_date.strftime("%Y-%m-%d")
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
                if daily.get("temperature_2m_max"):
                    data["temp_max"] = daily["temperature_2m_max"][0]
                    data["temp_min"] = daily["temperature_2m_min"][0]
                    data["precip"] = daily["precipitation_sum"][0]
                    data["unit"] = "mm (歷史雨量)"
    except Exception as e:
        print(f"Weather API Error: {e}")
        
    return data

def get_lat_lon_by_name(place_name):
    """從 attractions_db 查詢景點的經緯度"""
    if attractions_db is None or not place_name:
        return None, None
    
    # 模糊比對名稱
    mask = attractions_db['ScenicSpotName'].str.contains(re.escape(place_name), na=False)
    matches = attractions_db[mask]
    
    if matches.empty:
        return None, None
    
    # 取第一筆資料
    row = matches.iloc[0]
    pos_str = row['Position']
    try:
        pos_dict = ast.literal_eval(pos_str)
        return pos_dict.get('PositionLat'), pos_dict.get('PositionLon')
    except:
        return None, None

def process_schedule_weather(schedule_df, start_date):
    """
    [修正版] 包含去重邏輯、增強關鍵字判斷 (醫館、藝術館等)
    """
    if schedule_df is None or schedule_df.empty:
        return pd.DataFrame()

    # [新增] 取得目前行程中所有的景點名稱，製作成 Set 供後續排除使用
    current_schedule_set = set(schedule_df['Place'].astype(str).unique())

    weather_results = []
    
    # A. 定義「室內」關鍵字
    indoor_keywords_check = [
        "博物館", "美術館", "藝術館", "紀念館", "文物館", "故事館", "科博館", "天文館", 
        "海生館", "水族館", "圖書館", "演藝廳", "音樂廳", "劇院", "兩廳院", "戲院", 
        "展覽", "中心", "廳", "館", "紀念堂", "公會堂","車站","茶行",
        "百貨", "購物", "商場", "影城", "地下街", "誠品", "蔦屋", "書店", 
        "OUTLET", "Outlet", "商城", "巨蛋", "娛樂城", "KTV", "湯姆熊",
        "觀光工廠", "酒廠", "醫館", "101", "大樓", "大廈", "展望台", "觀景台", "塔",
        "宮", "廟", "寺", "教堂", "道場", "精舍", "室內", "溫泉會館", "湯屋"
    ]
    
    # B. 定義「假室內」排除關鍵字
    outdoor_exclusion_check = ["夜市", "老街", "步道", "公園", "廟口", "廣場", "農場"]

    cache = {}
    
    # 用來記錄這趟旅程已經推薦過哪些備案，避免重複
    suggested_history = set()

    for _, row in schedule_df.iterrows():
        day_num = row['Day']
        place = row['Place']
        city = row['City'] if 'City' in row and pd.notna(row['City']) else ""
        
        try:
            target_date = start_date + timedelta(days=int(day_num) - 1)
            target_date_str = target_date.strftime("%Y-%m-%d")
        except:
            target_date_str = date.today().strftime("%Y-%m-%d")

        lat, lon = get_lat_lon_by_name(place)
        cache_key = f"{place}_{target_date_str}"
        
        if cache_key in cache:
            weather_data = cache[cache_key]
        else:
            if lat and lon:
                weather_data = get_weather_data(lat, lon, target_date_str)
            else:
                weather_data = {"temp_max": None, "unit": "無座標", "precip": 0}
            cache[cache_key] = weather_data
            
        # --- ☔ 雨天備案邏輯 ---
        note_str = ""
        if weather_data.get('source') == "History":
            note_str = "(歷史數據)"
        
        # 判斷下雨
        precip_val = weather_data.get('precip')
        is_raining = False
        if precip_val is not None:
            if weather_data.get('unit') and '%' in weather_data['unit']: 
                if precip_val >= 50: is_raining = True 
            else: 
                if precip_val >= 3.0: is_raining = True 
        
        if is_raining and lat and lon:
            has_indoor_keyword = any(k in place for k in indoor_keywords_check)
            has_outdoor_keyword = any(k in place for k in outdoor_exclusion_check)
            
            is_truly_indoor = has_indoor_keyword and not has_outdoor_keyword
            
            if not is_truly_indoor:
                # [修改] 傳入 current_schedule_set 以避免推薦已存在的景點
                backup_spot = find_nearest_indoor_spot(
                    lat, lon, city, 
                    exclude_name=place, 
                    used_suggestions=suggested_history,
                    existing_spots=current_schedule_set # 新增此參數
                )
                
                if backup_spot:
                    note_str += f" ⚠️易雨，建議改至室內：{backup_spot}"
                    suggested_history.add(backup_spot)
        # --- 結束 ---

        res = {
            "Day": int(day_num),
            "Date": target_date_str,
            "Place": place,
            "Temp": f"{weather_data['temp_min']}°C - {weather_data['temp_max']}°C" if weather_data['temp_max'] is not None else "N/A",
            "Rain": f"{weather_data['precip']} {weather_data['unit']}" if weather_data['precip'] is not None else "N/A",
            "Note": note_str.strip()
        }
        weather_results.append(res)
        
    return pd.DataFrame(weather_results)
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    計算兩點經緯度的距離 (單位: 公里)
    """
    R = 6371  # 地球半徑 (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_nearest_indoor_spot(current_lat, current_lon, city_name, exclude_name=None, used_suggestions=None, existing_spots=None):
    """
    [修正版] 尋找最近室內景點，並支援「排除重複推薦」、「排除戶外關鍵字」與「排除已存在行程」
    """
    if attractions_db is None: return None
    if used_suggestions is None: used_suggestions = set()
    if existing_spots is None: existing_spots = set() # [新增] 初始化
    
    # 1. 室內關鍵字 (正向)
    indoor_keywords = [
        "博物館", "美術館", "藝術館", "紀念館", "故事館", "文物館", "科博館", "天文館", 
        "海生館", "水族館", "圖書館", "演藝廳", "音樂廳", "劇院", "兩廳院", "戲院",
        "展覽", "中心", "百貨", "購物", "商場", "影城", "地下街", "誠品", "蔦屋", "書店", 
        "OUTLET", "Outlet", "商城", "巨蛋", "娛樂城",
        "酒廠", "觀光工廠", "醫館", "101", "大樓", "展望台", "觀景台", "塔",
        "宮", "廟", "教堂", "寺", "道場", "廳", "館", "紀念堂", "溫泉會館","車站","茶行"
    ]
    
    # 2. 必須排除的關鍵字 (負向)
    exclude_keywords = [
        "夜市", "老街", "商圈", "步道", "公園", "漁港", "碼頭", "遊客中心", "服務中心", 
        "廟口", "農場", "露營", "廣場"
    ]

    # 3. 建立篩選
    mask_city = attractions_db['City'] == city_name
    mask_indoor = attractions_db['ScenicSpotName'].str.contains('|'.join(indoor_keywords), na=False)
    mask_exclude = ~attractions_db['ScenicSpotName'].str.contains('|'.join(exclude_keywords), na=False)
    
    candidates = attractions_db[mask_city & mask_indoor & mask_exclude]
    
    if candidates.empty:
        candidates = attractions_db[mask_indoor & mask_exclude]
    
    if candidates.empty: return None

    nearest_spot = None
    min_dist = float('inf')

    # 4. 計算距離
    for _, row in candidates.iterrows():
        name = row['ScenicSpotName']
        
        # A. 排除自己 (原本的戶外景點)
        if exclude_name and (name == exclude_name or name in exclude_name or exclude_name in name):
            continue
            
        # B. 排除已經被推薦過的備案
        if name in used_suggestions:
            continue

        # C. [新增] 排除原本行程中已經存在的景點
        if name in existing_spots:
            continue
            
        try:
            pos_dict = ast.literal_eval(row['Position'])
            lat = pos_dict.get('PositionLat')
            lon = pos_dict.get('PositionLon')
            
            if lat and lon:
                dist = calculate_distance(current_lat, current_lon, lat, lon)
                if dist < min_dist:
                    min_dist = dist
                    nearest_spot = name
        except:
            continue
            
    return nearest_spot

def generate_clothing_advice(day_weather_df):
    """
    [進階版] 根據氣溫、溫差與降雨，提供包含材質、款式與配件的全方位穿搭建議。
    """
    if day_weather_df.empty:
        return "⚠️ 暫無數據，建議攜帶輕便雨具與薄外套以備不時之需。"

    min_temps = []
    max_temps = []
    rain_vals = []
    is_historical = False

    # --- 1. 數據解析 ---
    for _, row in day_weather_df.iterrows():
        # 解析氣溫 "18.5°C - 24.0°C"
        t_str = str(row['Temp'])
        if "N/A" not in t_str and "-" in t_str:
            try:
                parts = t_str.replace("°C", "").split("-")
                min_temps.append(float(parts[0].strip()))
                max_temps.append(float(parts[1].strip()))
            except: pass
        
        # 解析降雨 "30 % (降雨機率)" 或 "5.2 mm (歷史雨量)"
        r_str = str(row['Rain'])
        if "N/A" not in r_str:
            try:
                val = float(r_str.split()[0])
                rain_vals.append(val)
                if "歷史" in r_str: is_historical = True
            except: pass

    if not min_temps or not max_temps:
        return "⚠️ 氣溫資料不足，建議採取洋蔥式穿搭（短袖+薄外套）以應變。"

    # --- 2. 關鍵指標計算 ---
    day_min = min(min_temps)
    day_max = max(max_temps)
    day_avg = (day_min + day_max) / 2
    temp_diff = day_max - day_min # 溫差
    max_rain = max(rain_vals) if rain_vals else 0
    
    # 判斷降雨風險 (預報>40% 或 歷史>3mm)
    rain_risk = max_rain >= 40 if not is_historical else max_rain >= 3

    advice_blocks = []

    # --- 3. 🌡️ 氣溫感受與主體穿搭 ---
    # 台灣體感溫度修正：濕冷更冷，濕熱更熱
    
    body_advice = ""
    bottom_advice = ""
    
    if day_avg < 12: # 寒流等級
        body_advice = "🧥 **上身**：發熱衣/羊毛內搭 + 厚毛衣/大學T。外層建議穿著**羽絨外套**或防風厚大衣。"
        bottom_advice = "👖 **下身**：內刷毛長褲、厚磅牛仔褲或羊毛裙（搭配厚褲襪）。"
        status = "❄️ **急凍寒冷**"
    elif 12 <= day_avg < 18: # 偏冷
        body_advice = "🧥 **上身**：長袖棉T/針織衫 + **鋪棉外套/飛行外套**。建議多層次穿搭。"
        bottom_advice = "👖 **下身**：防風長褲、燈芯絨褲或牛仔褲。"
        status = "🌬️ **明顯涼意**"
    elif 18 <= day_avg < 24: # 舒適偏涼 (最常見的春/秋天氣)
        body_advice = "👕 **上身**：**薄長袖**、七分袖或短袖 + **針織罩衫/牛仔外套/風衣**。"
        bottom_advice = "👖 **下身**：一般長褲、休閒褲或長裙。"
        status = "🍂 **舒適涼爽**"
    elif 24 <= day_avg < 29: # 溫暖微熱
        body_advice = "👕 **上身**：**短袖上衣**、雪紡衫或透氣襯衫。早晚可備一件薄襯衫當外套。"
        bottom_advice = "🩳 **下身**：透氣長褲、寬褲、五分褲或短裙。"
        status = "😊 **溫暖舒適**"
    else: # >= 29 炎熱
        body_advice = "🎽 **上身**：**吸濕排汗**材質的短袖、背心。避免穿著厚重棉質以免流汗黏膩。"
        bottom_advice = "🩳 **下身**：短褲、涼感寬褲或透氣亞麻材質。"
        status = "🔥 **悶熱高溫**"

    advice_blocks.append(f"### {status} (均溫約 {day_avg:.1f}°C)")
    advice_blocks.append(body_advice)
    advice_blocks.append(bottom_advice)

    # --- 4. 🧥 溫差對策 (洋蔥式穿搭判斷) ---
    if temp_diff >= 8:
        advice_blocks.append(f"⚠️ **溫差警報**：單日高低溫差達 **{temp_diff:.1f}°C**！中午會熱、早晚會冷。**強烈建議「洋蔥式穿法」**，方便穿脫，避免感冒。")

    # --- 5. ☔ 降雨與鞋履對策 ---
    if rain_risk:
        if is_historical:
            rain_msg = f"🌧️ **有雨機率高** (歷史數據 {max_rain}mm)"
        else:
            rain_msg = f"🌧️ **降雨機率高** ({max_rain}%)"
        
        advice_blocks.append(f"{rain_msg}：請務必攜帶**折疊傘**。建議穿著**防水鞋、靴子或涼鞋**，避免穿著易吸水的帆布鞋或全白球鞋。")
        advice_blocks.append("💡 **小撇步**：下雨天濕氣重，建議避免穿著落地寬褲，以免褲腳全濕。")
    else:
        advice_blocks.append("👟 **鞋履建議**：天氣穩定，適合穿著**好走的運動鞋、休閒鞋**。若行程包含大量步行，請避免穿新鞋或高跟鞋。")

    # --- 6. 🕶️ 配件與其他建議 ---
    accessories = []
    if day_max >= 28 or (day_max >= 25 and not rain_risk):
        accessories.append("☀️ 紫外線強：**墨鏡、遮陽帽**")
        accessories.append("🧴 防曬乳")
    
    if day_min < 16:
        accessories.append("🧣 保暖：**圍巾**")
    if day_min < 12:
        accessories.append("🧤 保暖：**手套、毛帽**")
        accessories.append("🔥 **暖暖包**")

    if accessories:
        advice_blocks.append("🎒 **必備配件**：" + "、".join(accessories))

    return "\n\n".join(advice_blocks)
# --- [新增] 處理雨天備案替換的 UI 邏輯 ---
def render_rain_swap_ui(day_weather_df, mode='ai'):
    """
    偵測天氣資料中的建議備註，並產生替換按鈕。
    [修正重點] 加入強制的型別轉換與去空白邏輯，解決 "1.0"!= "1" 或 "景點 " != "景點" 的問題。
    """
    # 篩選出有「建議改至室內」的項目
    swap_candidates = day_weather_df[day_weather_df['Note'].str.contains("建議改至室內", na=False)]
    
    if not swap_candidates.empty:
        st.markdown("#### ☔ 雨天備案建議")
        for idx, row in swap_candidates.iterrows():
            original_spot = row['Place']
            note = row['Note']
            # 確保 day_val 是純整數
            try:
                day_val = int(float(row['Day']))
            except:
                day_val = 1
            
            # 解析備註文字，取出新景點名稱
            try:
                if "：" in note:
                    new_spot = note.split("：")[-1].strip()
                else:
                    continue
            except:
                continue

            col_msg, col_btn = st.columns([3, 1], vertical_alignment="center")
            with col_msg:
                st.warning(f"Day {day_val}: 偵測到 **{original_spot}** 可能下雨，建議更改為室內景點：**{new_spot}**")
            
            with col_btn:
                btn_key = f"swap_{mode}_{day_val}_{original_spot}_{new_spot}"
                if st.button(f"🔄 立即替換", key=btn_key, use_container_width=True):
                    
                    if mode == 'ai':
                        # A. 修改 AI 行程表
                        if st.session_state['schedule_df'] is not None:
                            df = st.session_state['schedule_df']
                            
                            # --- [核心修正] 建立高容錯的遮罩 ---
                            # 1. 處理 Day: 統一轉成 "整數的字串" (解決 1.0 vs 1 的問題)
                            # 先填補 NaN 為 0，轉 float 再轉 int 再轉 str，確保萬無一失
                            sch_days = df['Day'].fillna(0).astype(float).astype(int).astype(str)
                            tgt_day = str(int(day_val))
                            
                            # 2. 處理 Place: 統一轉字串並去除前後空白
                            sch_places = df['Place'].astype(str).str.strip()
                            tgt_place = str(original_spot).strip()
                            
                            # 3. 進行比對
                            mask = (sch_days == tgt_day) & (sch_places == tgt_place)
                            # ----------------------------------
                            
                            if mask.any():
                                st.session_state['schedule_df'].loc[mask, 'Place'] = new_spot
                                
                                # [同步修正] 更新天氣快取
                                if st.session_state['ai_weather_df'] is not None:
                                    w_df = st.session_state['ai_weather_df']
                                    
                                    # 天氣表也要用同樣邏輯處理
                                    w_days = w_df['Day'].fillna(0).astype(float).astype(int).astype(str)
                                    w_places = w_df['Place'].astype(str).str.strip()
                                    
                                    w_mask = (w_days == tgt_day) & (w_places == tgt_place)
                                    
                                    if w_mask.any():
                                        st.session_state['ai_weather_df'].loc[w_mask, 'Place'] = new_spot
                                        st.session_state['ai_weather_df'].loc[w_mask, 'Note'] = "✅ 已更換為室內行程"
                                
                                st.toast(f"✅ 已將 {original_spot} 替換為 {new_spot}")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                # 若真的找不到，可能是使用者在 Tab1 編輯器手動刪掉了
                                st.error(f"⚠️ 找不到對應行程 '{original_spot}'，可能已被手動修改或刪除。")
                            
                    elif mode == 'manual':
                        # B. 修改手動行程清單
                        day_list = st.session_state['trip_schedule'].get(day_val, [])
                        
                        # 手動模式比對比較簡單，但也加上去空白比較保險
                        found_idx = -1
                        for i, spot in enumerate(day_list):
                            if str(spot).strip() == str(original_spot).strip():
                                found_idx = i
                                break
                                
                        if found_idx != -1:
                            day_list[found_idx] = new_spot
                            st.session_state['trip_schedule'][day_val] = day_list
                            
                            # 更新手動模式的天氣快取
                            cache = st.session_state['manual_weather_cache']
                            if cache.get("df") is not None:
                                w_df = cache["df"]
                                w_days = w_df['Day'].fillna(0).astype(float).astype(int).astype(str)
                                w_places = w_df['Place'].astype(str).str.strip()
                                tgt_day = str(int(day_val))
                                tgt_place = str(original_spot).strip()
                                
                                w_mask = (w_days == tgt_day) & (w_places == tgt_place)
                                
                                if w_mask.any():
                                    w_df.loc[w_mask, 'Place'] = new_spot
                                    w_df.loc[w_mask, 'Note'] = "✅ 已更換為室內行程"
                                    st.session_state['manual_weather_cache']['df'] = w_df
                            
                            # 更新簽章
                            new_manual_data = []
                            sorted_days = sorted(st.session_state['trip_schedule'].keys())
                            for d in sorted_days:
                                spots = st.session_state['trip_schedule'][d]
                                for i, s in enumerate(spots):
                                    c, dist = "", ""
                                    if attractions_db is not None:
                                        r = attractions_db[attractions_db['ScenicSpotName'] == s]
                                        if not r.empty:
                                            c, dist = r.iloc[0]['City'], r.iloc[0]['District']
                                    t_key = f"{d}_{i}"
                                    t_val = st.session_state['manual_trans_data'].get(t_key, "自行開車")
                                    new_manual_data.append({"Day": int(d), "Order": i+1, "Place": s, "City": c, "District": dist, "Transport": t_val})
                            
                            new_sig = json.dumps(new_manual_data, sort_keys=True, ensure_ascii=False)
                            st.session_state['manual_weather_cache']['signature'] = new_sig
                            
                            st.toast(f"✅ 已將 {original_spot} 替換為 {new_spot}")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                             st.error(f"⚠️ 找不到手動行程中的 '{original_spot}'，可能已被刪除。")
# --- 7. AI 邏輯與圖表函式 ---

def extract_trip_info(chat_text):
    """
    用於從對話中提取旅遊參數的函式
    """
    today_str = date.today().strftime("%Y-%m-%d")
    prompt = f"""
    你是旅遊助手。現在是 {today_str}。
    請分析以下使用者的對話內容，並提取最新的旅遊需求。
    如果使用者提到相關資訊，請更新對應欄位；如果沒提到，請保持 null 或根據上下文推斷。
    
    對話內容：
    {chat_text}
    
    請回傳 JSON 格式：
    {{
        "destination": "地點 (例如: 臺南市, 台北)",
        "start_date": "YYYY-MM-DD (根據使用者說的日期推算，例如 '下週五')",
        "end_date": "YYYY-MM-DD (若只說天數，請依開始日期推算)",
        "days": int (天數),
        "transport": ["交通方式1", "交通方式2"] (例如: ["高鐵", "租車"]),
        "preferences": "想去的景點或偏好 (字串)"
    }}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except:
        return None

def process_user_keywords(user_input):
    if not user_input: return []
    keywords = re.split(r'[ ,、;，\n]', user_input)
    clean_keywords = [k.strip() for k in keywords if k.strip()]
    corrected = []
    for k in clean_keywords:
        if "夜市" in k and "觀光" not in k:
            k = k.replace("夜市", "觀光夜市")
        corrected.append(k)
    return corrected

def get_attraction_data(destination, user_input=""):
    # [修正] 統一回傳 3 個值，避免錯誤
    if attractions_db is None: return [], "", {}
    
    # 1. 統一 "台" -> "臺"
    destination = destination.replace("台", "臺")
    
    # 2. [關鍵修改] 切割關鍵字 (支援空白、逗號、頓號、分號、加號)
    # 讓 "花蓮 台東" 或 "花蓮,台東" 都能被正確識別為兩個地點
    dest_keywords = re.split(r'[ ,、;，+/]', destination)
    dest_keywords = [k.strip() for k in dest_keywords if k.strip()] # 移除空白
    
    if not dest_keywords:
        return [], "", {"error": "no_data"}

    # 3. 建立搜尋遮罩 (Mask)：只要符合任一關鍵字即可 (OR 邏輯)
    # 先建立一個全為 False 的遮罩
    mask_loc = pd.Series([False] * len(attractions_db))
    
    for kw in dest_keywords:
        # 只要 City, Address 或名稱中包含該關鍵字，就算符合
        current_mask = (
            attractions_db['City'].str.contains(kw, na=False) | 
            attractions_db['Address'].str.contains(kw, na=False) |
            attractions_db['ScenicSpotName'].str.contains(kw, na=False)
        )
        # 使用 OR (|) 累加符合的資料
        mask_loc = mask_loc | current_mask

    # 4. 必須有圖片才算有效景點
    mask_pic = attractions_db['Picture'].str.contains('PictureUrl1', na=False)
    
    # 取得初步資料池
    base_pool = attractions_db[mask_loc & mask_pic]
    
    if base_pool.empty: return [], "", {"error": "no_data"}

    # --- 以下維持原本的使用者偏好搜尋邏輯 ---
    keywords = process_user_keywords(user_input)
    priority_rows = pd.DataFrame()
    matched_keywords = {} 
    unmatched_keywords = [] 

    if keywords:
        for k in keywords:
            mask_name = base_pool['ScenicSpotName'].str.contains(re.escape(k), na=False)
            matches = base_pool[mask_name]
            if not matches.empty:
                best_match = matches.iloc[[0]] 
                priority_rows = pd.concat([priority_rows, best_match])
                matched_keywords[k] = best_match.iloc[0]['ScenicSpotName']
            else:
                unmatched_keywords.append(k)
    
    if not priority_rows.empty:
        priority_rows = priority_rows.drop_duplicates(subset=['ScenicSpotName'])
        remaining_pool = base_pool[~base_pool['ID'].isin(priority_rows['ID'])]
    else:
        remaining_pool = base_pool
        
    target_fill = 60
    if len(remaining_pool) > target_fill:
        general_rows = remaining_pool.sample(n=target_fill)
    else:
        general_rows = remaining_pool

    def format_list(df, is_priority=False):
        info = []
        for _, row in df.iterrows():
            name = row['ScenicSpotName']
            city = str(row['City'])
            dist = str(row['District'])
            prefix = "【必去(MUST VISIT)】" if is_priority else "- "
            info.append(f"{prefix}{name} (位於: {city}{dist})")
        return "\n".join(info)

    priority_str = format_list(priority_rows, is_priority=True)
    general_str = format_list(general_rows, is_priority=False)
    full_context_str = priority_str + "\n" + general_str
    priority_names = priority_rows['ScenicSpotName'].tolist() if not priority_rows.empty else []
    
    status_report = {"matched": matched_keywords, "unmatched": unmatched_keywords}
    
    return priority_names, full_context_str, status_report
def get_transport_icon(transport_str):
    """根據交通方式文字返回對應的 icon"""
    if not transport_str or str(transport_str) == "None":
        return "🚌" # 預設圖示
    
    t = str(transport_str)
    
    # 1. 先判斷軌道運輸
    if "高鐵" in t: return "🚅"
    if "火車" in t or "臺鐵" in t or "台鐵" in t: return "🚆"
    if "捷運" in t or "MRT" in t or "輕軌" in t: return "🚇"
    
    # 2. 判斷公路大眾運輸
    if "公車" in t or "客運" in t or "巴士" in t or "台灣好行" in t: return "🚌"
    
    # 3. [修正重點] 擴充開車的關鍵字：加入 "驅車"、"行駛"、"小客車"
    if ("開車" in t or "計程車" in t or "租車" in t or "Uber" in t or 
        "自駕" in t or "驅車" in t or "行駛" in t or "小客車" in t): 
        return "🚗"
        
    # 4. 其他
    if "機車" in t or "騎車" in t: return "🛵"
    if "腳踏車" in t or "單車" in t or "YouBike" in t: return "🚲"
    if "步行" in t or "走路" in t or "散步" in t: return "🚶"
    if "船" in t or "渡輪" in t: return "⛴️"
    if "飛機" in t: return "✈️"
    
    # 5. 若以上都沒抓到，預設回傳什麼？
    # 既然您主要設定是自行開車，這裡可以考慮改成預設回傳 🚗，或者維持 🚌
    # 如果希望「自行開車」模式下，未知的都顯示車子，可以把這裡改成 "🚗"
    return "🚌"
def estimate_travel_time(lat1, lon1, lat2, lon2, transport_str):
    """
    根據兩點距離與交通方式，估算交通時間
    """
    if not lat1 or not lon1 or not lat2 or not lon2:
        return None
        
    # 1. 計算距離 (公里)
    dist = calculate_distance(lat1, lon1, lat2, lon2)
    
    est_time = estimate_travel_time(lat1, lon1, lat2, lon2, row['Transport'])
    if est_time:
        time_style = "color: #e67e22;" # 預設橘色
                        
                        # 如果字串中包含 "小時" 且前面的數字 >= 2，則變紅色
        if "小時" in est_time:
            try:
                h_part = int(est_time.split("小時")[0].strip())
                if h_part >= 2:
                    time_style = "color: #e74c3c; font-weight: bold;" # 變紅色
                    est_time += " ⚠️ 拉車注意"
            except: pass
                            
    time_info = f"<span style='{time_style} font-size: 0.9em; margin-left: 10px;'>⏱️ 預估 {est_time}</span>"
def generate_html_display(df, start_date=None):
    """
    [修改版] 移除時間預估顯示
    """
    html_content = "" 
    
    # 1. 基本過濾與排序
    df = df[df['Place'].notna() & (df['Place'] != "")]
    df = df.sort_values(by=["Day", "Order"])
    
    # 2. 取得所有出現的天數
    unique_days = sorted(df['Day'].unique())
    
    for day in unique_days:
        day_val = int(day)
        
        # 每一天都開始一個獨立的 itinerary-box
        html_content += '<div class="itinerary-box">'
        
        # 顯示該天的日期標題
        date_info = ""
        if start_date:
            curr_date = start_date + timedelta(days=day_val - 1)
            date_info = f" <span style='font-size:0.8em; color:#666;'>({curr_date.strftime('%m/%d')})</span>"
        
        html_content += f'<div class="itinerary-day">🗓️ 第 {day_val} 天{date_info}</div>'
        
        # 篩選出這一天的所有行程項目
        day_items = df[df['Day'] == day]
        
        for _, row in day_items.iterrows():
            place = row['Place']
            city = row['City'] if pd.notna(row['City']) else ""
            district = row['District'] if pd.notna(row['District']) else ""
            loc_str = f"({city} {district})" if city or district else ""
            
            html_content += f'<div class="itinerary-item">📍 <strong>{place}</strong> {loc_str}</div>'
            
            # --- 交通方式顯示 (已移除時間計算) ---
            if row['Transport'] and str(row['Transport']) != "None" and str(row['Transport']) != "":
                icon = get_transport_icon(row['Transport'])
                
                # [修改] 這裡只顯示 icon 和交通方式文字，不再計算時間
                html_content += f'<div class="itinerary-transport">└─ {icon} {row["Transport"]}</div>'
            
        html_content += '</div>'
        
    return html_content
def estimate_travel_time(lat1, lon1, lat2, lon2, transport_str):
    """
    根據兩點距離與交通方式，估算交通時間
    """
    if not lat1 or not lon1 or not lat2 or not lon2:
        return None
        
    # 1. 計算距離 (公里)
    dist = calculate_distance(lat1, lon1, lat2, lon2)
    
    # 2. 判斷交通方式的平均時速 (km/h) - 經驗推估值
    speed = 40.0 # 預設 (開車/計程車)
    t_str = str(transport_str)
    
    if "步行" in t_str or "走路" in t_str or "散步" in t_str:
        speed = 4.0
    elif "腳踏車" in t_str or "單車" in t_str or "YouBike" in t_str:
        speed = 15.0
    elif "機車" in t_str or "騎車" in t_str:
        speed = 30.0 # 市區走走停停
    elif "高鐵" in t_str:
        speed = 120.0 # 考慮進出站的平均
    elif "火車" in t_str or "臺鐵" in t_str:
        speed = 60.0
    elif "捷運" in t_str or "公車" in t_str or "客運" in t_str or "大眾" in t_str:
        speed = 20.0 # 包含等車與靠站，均速較低
    
    # 3. 計算時間 (分鐘)
    # 加上 1.2 的係數作為道路彎曲修正 (非直線)
    minutes = int((dist * 1.2 / speed) * 60)
    
    # 最少顯示 1 分鐘
    if minutes < 1: minutes = 1
    
    # 4. 格式化輸出
    if minutes >= 60:
        h = minutes // 60
        m = minutes % 60
        return f"{h} 小時 {m} 分"
    else:
        return f"{minutes} 分鐘"
    
def generate_plain_text(df, start_date=None):
    txt_content = f"【{st.session_state.get('input_dest', '行程')} 旅遊規劃表】\n"
    txt_content += "="*30 + "\n\n"
    df = df[df['Place'].notna() & (df['Place'] != "")]
    df = df.sort_values(by=["Day", "Order"])
    current_day = 0
    for index, row in df.iterrows():
        day_val = int(row['Day']) if pd.notna(row['Day']) else 1
        if day_val != current_day:
            current_day = day_val
            date_str = ""
            if start_date:
                curr_date = start_date + timedelta(days=day_val - 1)
                date_str = f" ({curr_date.strftime('%Y-%m-%d')})"
            txt_content += f"\n[ Day {current_day}{date_str} ]\n"
            txt_content += "-"*15 + "\n"
        place = row['Place']
        city = row['City'] if pd.notna(row['City']) else ""
        district = row['District'] if pd.notna(row['District']) else ""
        loc_str = f"({city} {district})" if city or district else ""
        txt_content += f"📍 {place} {loc_str}\n"
        if row['Transport'] and str(row['Transport']) != "None" and str(row['Transport']) != "":
            icon = get_transport_icon(row['Transport']) # 加入這行
            txt_content += f"   └── {icon} 交通：{row['Transport']}\n" # 修改這行
        txt_content += "\n"
    return txt_content

def generate_dot_from_df(df):
    df = df[df['Place'].notna() & (df['Place'] != "")]
    if df.empty: return None
    df = df.sort_values(by=["Day", "Order"])
    dot = 'digraph G {\n'
    dot += '  graph [rankdir=LR, splines=polyline, fontname="Microsoft JhengHei", nodesep=1.2, ranksep=1.5];\n'
    dot += '  node [shape=box, style="filled,rounded", color="lightblue", fontname="Microsoft JhengHei"];\n'
    dot += '  edge [fontname="Microsoft JhengHei", fontsize=9];\n'
    days = sorted(df['Day'].dropna().unique())
    if not days: days = [1]
    for day in days:
        day = int(day)
        day_df = df[df['Day'] == day]
        if day_df.empty: continue
        dot += f'  subgraph cluster_day{day} {{\n'
        dot += f'    label="Day {day}";\n'
        dot += '    style="filled"; color="#f0f2f6";\n'
        prev_node = None
        for idx, row in day_df.iterrows():
            node_id = f"node_{idx}"
            place_name = row['Place']
            dot += f'    {node_id} [label=<<B>{place_name}</B>>];\n'
            if prev_node:
                transport = row['Transport'] if pd.notna(row['Transport']) and row['Transport'] else ""
                short_transport = transport[:15] + "..." if len(transport) > 15 else transport
                dot += f'    {prev_node} -> {node_id} [label="{short_transport}"];\n'
            prev_node = node_id
        dot += '  }\n'
    dot += '}'
    return dot

def display_attraction_details(place_name):
    if attractions_db is None or place_name is None: return
    mask = attractions_db['ScenicSpotName'].str.contains(place_name, na=False, regex=False)
    matches = attractions_db[mask]
    if matches.empty:
        st.warning(f"⚠️ 找不到「{place_name}」的資料。")
        return
    matches_with_pic = matches[matches['Picture'].str.contains('PictureUrl1', na=False)]
    row = matches_with_pic.iloc[0] if not matches_with_pic.empty else matches.iloc[0]

    col_img, col_desc = st.columns([1, 1.5])
    with col_img:
        img_url = None
        try:
            if pd.notna(row['Picture']):
                pic_dict = ast.literal_eval(row['Picture'])
                img_url = pic_dict.get('PictureUrl1')
        except: pass 
        if img_url:
            st.image(img_url, use_container_width=True, caption=row['ScenicSpotName'])
        else:
            st.warning("🖼️ 無法顯示圖片")
        # --- 🔴 修改結束 ---

    with col_desc:
        st.subheader(f"📍 {row['ScenicSpotName']}")
        st.caption(f"🏠 地址：{row['Address']}")
        st.caption(f"📞 電話：{row['Phone']}")
        st.caption(f"⏰ 開放時間：{row['OpenTime']}")
        desc_detail = row['DescriptionDetail']
        if pd.notna(desc_detail):
            with st.container(height=200): 
                st.write(desc_detail)
        else:
            st.write(row['Description'])

# --- 8. Auth Pages (Login/Signup/Forgot) ---
def signup_page():
    st.title("📝 註冊新帳號")
    with st.form("signup_form"):
        new_email = st.text_input("請輸入電子郵件")
        new_nickname = st.text_input("請輸入暱稱")
        new_password = st.text_input("請輸入密碼", type="password")
        confirm_password = st.text_input("請再次確認密碼", type="password")
        submitted = st.form_submit_button("註冊")
        if submitted:
            users = load_users()
            if not new_email or not new_password or not new_nickname:
                 st.error("所有欄位都必須填寫")
            elif "@" not in new_email:
                 st.error("請輸入有效的電子郵件")
            elif new_email in users:
                st.error("此電子郵件已被註冊")
            elif new_password != confirm_password:
                st.error("兩次輸入的密碼不相同")
            else:
                save_user(new_email, new_password, new_nickname)
                st.success("註冊成功！")
                time.sleep(1)
                st.session_state['current_page'] = 'login'
                st.rerun()
    st.write("---")
    if st.button("返回登入頁面"):
        st.session_state['current_page'] = 'login'
        st.rerun()

def forgot_password_page():
    st.title("🔑 忘記密碼")
    with st.form("forgot_password_form"):
        email = st.text_input("電子郵件")
        submitted = st.form_submit_button("發送驗證碼")
        if submitted:
            users = load_users()
            if email in users:
                code = generate_verification_code()
                st.session_state['reset_email'] = email
                st.session_state['reset_code'] = code
                st.info(f"您的驗證碼是：**{code}** (頁面將在 5 秒後自動跳轉)")
                time.sleep(5)
                st.session_state['current_page'] = 'reset_password'
                st.rerun()
            else:
                st.error("找不到此電子郵件")
    st.write("---")
    if st.button("返回登入頁面"):
        st.session_state['current_page'] = 'login'
        st.rerun()

def reset_password_page():
    st.title("🔄 重設密碼")
    with st.form("reset_password_form"):
        code_input = st.text_input("請輸入驗證碼")
        new_password = st.text_input("請輸入新密碼", type="password")
        confirm_password = st.text_input("請再次確認新密碼", type="password")
        submitted = st.form_submit_button("重設密碼")

        if submitted:
            if code_input != st.session_state['reset_code']:
                st.error("驗證碼錯誤")
            elif new_password != confirm_password:
                st.error("兩次密碼不相同")
            else:
                save_user(st.session_state['reset_email'], new_password)
                st.success("密碼重設成功！")
                time.sleep(1)
                st.session_state['current_page'] = 'login'
                st.rerun()
    st.write("---")
    if st.button("返回登入頁面"):
        st.session_state['current_page'] = 'login'
        st.rerun()

def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 使用者登入</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("電子郵件")
            password = st.text_input("密碼", type="password")
            submitted = st.form_submit_button("登入")
            if submitted:
                nickname = authenticate(email, password)
                
                # [新增] 針對格式錯誤的判斷
                if nickname == "DB_FORMAT_ERROR":
                    st.error("⚠️ 格式錯誤")
                
                elif nickname:
                    st.session_state['logged_in'] = True
                    st.session_state['user_nickname'] = nickname
                    st.session_state['user_email'] = email
                    st.session_state['mode'] = 'menu'
                    st.success(f"歡迎，{nickname}！")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ 登入失敗 (帳號或密碼錯誤)")
        col_forgot, col_signup = st.columns([1.5, 1])
        with col_forgot:
            if st.button("🤔 忘記密碼？"):
                st.session_state['current_page'] = 'forgot_password'
                st.rerun()
        if st.button("👉 前往註冊", use_container_width=True):
            st.session_state['current_page'] = 'signup'
            st.rerun()

# --- 9. 側邊欄 (包含手動排序與 AI 輸入) ---
def sidebar_component():
    with st.sidebar:
        st.header(f"👤 {st.session_state['user_nickname']}")
        
        # 導航按鈕
        if st.session_state['mode'] != 'menu':
            if st.button("🏠 回到主選單", use_container_width=True):
                st.session_state['mode'] = 'menu'
                st.session_state['ai_submitted'] = False # 重置 AI 狀態
                st.rerun()
        
        # 歷史紀錄按鈕
        if st.session_state['mode'] != 'history':
             if st.button("📜 我的歷史紀錄", use_container_width=True):
                st.session_state['mode'] = 'history'
                st.rerun()

        st.divider()

        # 根據模式顯示不同的側邊欄內容
        if st.session_state['mode'] == 'manual':
            # ... (手動模式的程式碼保持不變，省略以節省篇幅) ...
            st.subheader("📋 手動行程清單")
            if 'trip_start_date' in st.session_state:
                st.caption(f"📅 出發：{st.session_state['trip_start_date']}")

            has_spots = any(len(spots) > 0 for spots in st.session_state['trip_schedule'].values())
            
            if has_spots:
                for day in range(1, st.session_state['trip_days'] + 1):
                    day_spots = st.session_state['trip_schedule'].get(day, [])
                    if day_spots:
                        curr_date_str = ""
                        if 'trip_start_date' in st.session_state:
                            d = st.session_state['trip_start_date'] + timedelta(days=day-1)
                            curr_date_str = f" ({d.month}/{d.day})"
                        st.markdown(f"<div class='day-header'>Day {day}{curr_date_str}</div>", unsafe_allow_html=True)
                        
                        if len(day_spots) >= 1:
                            encoded_spots = [urllib.parse.quote(spot) for spot in day_spots]
                            map_url = f"https://www.google.com/maps/dir/{'/'.join(encoded_spots)}"
                            st.link_button(f"🗺️ 開啟導航", map_url, use_container_width=True)

                        for i, spot in enumerate(day_spots):
                            c1, c2, c3, c4 = st.columns([8, 3, 3, 3], vertical_alignment="center")
                            with c1: st.write(f"{i+1}.{spot}")
                            with c2:
                                if i > 0 and st.button("⬆️", key=f"up_{day}_{i}"):
                                    day_spots[i], day_spots[i-1] = day_spots[i-1], day_spots[i]
                                    st.rerun()
                            with c3:
                                if i < len(day_spots) - 1 and st.button("⬇️", key=f"down_{day}_{i}"):
                                    day_spots[i], day_spots[i+1] = day_spots[i+1], day_spots[i]
                                    st.rerun()
                            with c4:
                                if st.button("🗑️", key=f"del_{day}_{i}"):
                                    day_spots.pop(i)
                                    st.rerun()
                st.divider()
                if st.button("🗑️ 清空所有行程", type="primary", use_container_width=True):
                    st.session_state['trip_schedule'] = {d: [] for d in range(1, st.session_state['trip_days'] + 1)}
                    st.toast("行程已清空")
                    st.rerun()
            else:
                st.info("手動清單是空的，請從右側加入景點。")

        elif st.session_state['mode'] == 'ai_chat':
            # AI 模式：顯示輸入表單
            if st.session_state['ai_submitted']:
                # 若已經生成行程，這裡顯示可修改的參數 (對應原本的程式碼結構)
                st.markdown("### 🛠️ 調整行程參數")
                
                # 地點
                new_dest = st.text_input("旅遊地點", value=st.session_state['input_dest'])
                if new_dest != st.session_state['input_dest']:
                    st.session_state['input_dest'] = new_dest
                
                # 日期
                new_dates = st.date_input(
                    "日期區間", 
                    value=[st.session_state['ai_start_date'], st.session_state['ai_end_date']],
                    min_value=date.today()
                )
                if len(new_dates) == 2:
                    st.session_state['ai_start_date'] = new_dates[0]
                    st.session_state['ai_end_date'] = new_dates[1]
                    st.session_state['input_days'] = (new_dates[1] - new_dates[0]).days + 1
                
                # --- [修正區塊開始] ---
                # 1. 定義完整的選項清單 (加入租車、機車)
                trans_options = ["大眾運輸", "自行開車", "計程車", "步行", "租車", "機車"]
                
                # 2. 取得目前的設定值
                current_trans = st.session_state.get('input_trans', [])
                if not isinstance(current_trans, list):
                    current_trans = [current_trans]
                
                # 3. 安全過濾：只保留存在於 trans_options 裡的選項，防止報錯
                valid_defaults = [t for t in current_trans if t in trans_options]
                
                # 4. 顯示多選單
                new_trans = st.multiselect(
                    "交通方式", 
                    trans_options, 
                    default=valid_defaults
                )
                st.session_state['input_trans'] = new_trans
                # --- [修正區塊結束] ---
                
                # 想去的地方
                new_mixed = st.text_area("想去的景點或偏好", value=st.session_state['input_mixed'])
                st.session_state['input_mixed'] = new_mixed

                st.write("")
                if st.button("🔄 重新生成行程", type="primary", use_container_width=True):
                    st.session_state['schedule_df'] = None 
                    st.session_state['ai_weather_df'] = None  # ✨ [新增這行] 強制清空舊天氣資料
                    st.rerun()
        st.divider()
        if st.button("登出", use_container_width=True):
            st.session_state.clear()
            st.rerun()
# --- 10. 主要頁面功能區 ---

def menu_page():
    sidebar_component()
    st.title("🌟 歡迎來到台灣旅遊小幫手")
    col1, col2 = st.columns(2)
    with col1:
        st.info("🤖 **AI 對話排程**\n\n像聊天一樣告訴 AI 你的需求，自動生成完美行程。")
        if st.button("✨ 開始 AI 對話", use_container_width=True, type="primary"):
            st.session_state['mode'] = 'ai_chat'
            st.rerun()
    with col2:
        st.success("🗺️ **手動自由配**\n\n自訂旅遊天數，搜尋資料庫圖片，自由加入行程。")
        if st.button("🔍 自己搜尋瀏覽", use_container_width=True):
            st.session_state['mode'] = 'manual'
            st.rerun()

def render_ai_input_form(container):
    with container:
        if not st.session_state['ai_submitted']:
             st.markdown("### 🛫 規劃您的旅程")
        else:
             st.header("⚙️ 修改設定")
        
        # 地點輸入
        st.text_input("想去哪裡玩？", value=st.session_state['input_dest'], key="widget_dest", on_change=lambda: st.session_state.update({'input_dest': st.session_state.widget_dest}))
        
        # 日期選擇
        default_start = st.session_state.get('ai_start_date', date.today())
        default_end = st.session_state.get('ai_end_date', date.today() + timedelta(days=2))
        
        dates = st.date_input(
            "選擇旅遊日期區間", 
            value=[default_start, default_end],
            min_value=date.today(),
            help="請選擇開始與結束日期"
        )
        
        # 邏輯：根據日期算出天數
        if len(dates) == 2:
            start_d, end_d = dates
            delta_days = (end_d - start_d).days + 1
            st.session_state['input_days'] = delta_days
            st.session_state['ai_start_date'] = start_d
            st.session_state['ai_end_date'] = end_d
            st.caption(f"共計：{delta_days} 天")
        elif len(dates) == 1:
            st.caption("請選擇結束日期...")
            st.session_state['input_days'] = 1 
        
        # 交通 (這裡也加上安全選項)
        st.multiselect(
            "交通方式", 
            ["大眾運輸", "自行開車", "計程車", "步行", "租車", "機車"], 
            default=["大眾運輸"], 
            key="input_trans"
        )
                
        # 偏好
        st.text_area("偏好與必去景點", value=st.session_state['input_mixed'], key="widget_mixed", height=100, on_change=lambda: st.session_state.update({'input_mixed': st.session_state.widget_mixed}))
        
        st.write("")
        # 避免只選一天或未完成選擇時按按鈕
        btn_disabled = (len(dates) != 2)
        
        # 按鈕邏輯
        if st.button("✨ 開始規劃" if not st.session_state['ai_submitted'] else "🔄 重新生成", use_container_width=True, disabled=btn_disabled):
            st.session_state['ai_submitted'] = True
            st.session_state['schedule_df'] = None # 強制重跑
            st.session_state['ai_weather_df'] = None # ✨ [新增這行] 確保天氣也會重抓
            
            # 重置對話紀錄
            st.session_state['chat_history'] = [
                {"role": "assistant", "content": "你好！我是你的 AI 旅遊顧問。告訴我你想去哪裡？預計什麼時候出發？想怎麼玩？"}
            ]
            st.rerun()
# --- AI 對話與排程頁面 (核心修改區) ---
def ai_planning_page():
    # 安全初始化 (防止 KeyError)
    defaults = {
        'input_dest': '臺北市',
        'input_days': 1,
        'ai_start_date': date.today(),
        'ai_end_date': date.today(),
        'input_trans': ["大眾運輸"],
        'input_mixed': "",
        'chat_history': [],
        'ai_submitted': False,
        'schedule_df': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    sidebar_component()
    
    # 狀態 1: 對話與參數收集階段
    if not st.session_state['ai_submitted']:
        # ... (這部分保持不變) ...
        st.title("💬 AI 旅遊顧問")
        st.caption("請告訴我你想去哪裡？幾個人？想玩幾天？喜歡什麼類型的景點？")

        for msg in st.session_state['chat_history']:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("例如：我想去台南玩三天，下週五出發，想吃小吃"):
            st.session_state['chat_history'].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.spinner("AI 正在分析您的需求..."):
                full_text = "\n".join([m['content'] for m in st.session_state['chat_history']])
                extracted = extract_trip_info(full_text)
                
                if extracted:
                    # 1. 先更新地點與偏好
                    if extracted.get("destination"): st.session_state['input_dest'] = extracted["destination"]
                    if extracted.get("transport"): st.session_state['input_trans'] = extracted["transport"]
                    if extracted.get("preferences"): st.session_state['input_mixed'] = extracted["preferences"]

                    # 2. 更新日期物件 (如果有解析到的話)
                    if extracted.get("start_date"):
                        try: st.session_state['ai_start_date'] = datetime.strptime(extracted["start_date"], "%Y-%m-%d").date()
                        except: pass
                    if extracted.get("end_date"):
                        try: st.session_state['ai_end_date'] = datetime.strptime(extracted["end_date"], "%Y-%m-%d").date()
                        except: pass
                    
                    # 3. 更新天數 (最優先權)
                    if extracted.get("days"): 
                        st.session_state['input_days'] = int(extracted["days"])
                    
                    # --- [🔴 關鍵修正] 強制同步日期與天數 ---
                    # 邏輯 A: 如果有「明確天數」，強制重新計算結束日期 (避免 AI 給了2天卻沒給日期，導致結束日期卡在當天)
                    if extracted.get("days"):
                         st.session_state['ai_end_date'] = st.session_state['ai_start_date'] + timedelta(days=st.session_state['input_days'] - 1)
                    
                    # 邏輯 B: 如果只有「日期」沒有「天數」，則反推天數
                    elif extracted.get("start_date") and extracted.get("end_date"):
                         delta = (st.session_state['ai_end_date'] - st.session_state['ai_start_date']).days + 1
                         st.session_state['input_days'] = delta if delta > 0 else 1
                ai_reply_prompt = f"""
                你是親切的台灣旅遊專家。目前已知資訊：
                - 地點: {st.session_state['input_dest']}
                - 日期: {st.session_state['ai_start_date']} 到 {st.session_state['ai_end_date']}
                - 交通: {st.session_state['input_trans']}
                
                使用者剛說：{prompt}
                請簡短回應。若資訊足夠，請明確引導使用者點擊下方的「規劃行程」按鈕（請務必使用這個名稱，不要說成產出行程）。
                """
                response = chat_model.generate_content(ai_reply_prompt)
                ai_msg = response.text
                
                st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                with st.chat_message("assistant"):
                    st.markdown(ai_msg)
                
                st.rerun()

        if len(st.session_state['chat_history']) > 1:
            st.markdown("---")
            col_info, col_btn = st.columns([3, 1], vertical_alignment="center")
            with col_info:
                info_str = f"📍 **{st.session_state['input_dest']}** | 📅 **{st.session_state['ai_start_date']}** 出發 | ⏱️ **{st.session_state['input_days']}** 天"
                st.info(f"目前設定： {info_str}")
            with col_btn:
                if st.button("🚀 規劃行程", type="primary", use_container_width=True):
                    st.session_state['ai_submitted'] = True
                    st.session_state['schedule_df'] = None 
                    st.session_state['chat_history'] = [
                        {"role": "assistant", "content": "你好！我是你的 AI 旅遊顧問。告訴我你想去哪裡？預計什麼時候出發？想怎麼玩？"}
                    ]
                    st.rerun()

    # 狀態 2: 行程生成與展示階段
    else:
        start_d = st.session_state.get('ai_start_date', date.today())
        st.title(f"🗺️ {st.session_state['input_dest']} - AI 專屬行程")
        st.caption(f"📅 出發日期：{start_d.strftime('%Y-%m-%d')} (共 {st.session_state['input_days']} 天)")

        if st.session_state['schedule_df'] is None:
            with st.spinner('🔍 AI 正在智慧分析需求、查詢資料庫並規劃路線...'):
                try:
                    priority_list, context_str, status = get_attraction_data(
                        st.session_state['input_dest'], 
                        st.session_state['input_mixed'] 
                    )
                    st.session_state['schedule_df'] = df_temp
                    
                    # [新增] 生成行程後，立即查詢天氣並存入 Session State
                    with st.spinner("☁️ 正在同步查詢當地天氣資訊..."):
                        w_start_d = st.session_state.get('ai_start_date', date.today())
                        st.session_state['ai_weather_df'] = process_schedule_weather(df_temp, w_start_d)
                    
                except Exception as e:
                    if status.get("error") == "no_data":
                        st.error(f"❌ 找不到關於「{st.session_state['input_dest']}」的景點資料。")
                        if st.button("🔙 返回對話修改"):
                            st.session_state['ai_submitted'] = False
                            st.rerun()
                        st.stop()
                    
                    mandatory_instruction = ""
                    if priority_list:
                        mandatory_instruction = f"**絕對強制指令**: 必須將以下景點排入行程：{json.dumps(priority_list, ensure_ascii=False)}"
                    
                    user_preferences = st.session_state['input_mixed'] if st.session_state['input_mixed'] else "無特殊偏好"
                    
                    prompt = f"""
                    請規劃 {st.session_state['input_dest']} 的 {st.session_state['input_days']} 天行程。
                    **使用者偏好/風格**：{user_preferences}。
                    交通方式：{','.join(st.session_state['input_trans'])}。
                    {mandatory_instruction}
                    **重要規則 1**：同一趟旅程中，絕對不可以重複出現相同的景點名稱 (請務必去重)。
                    **重要規則 2**：請優化路線順序，確保每個景點之間的交通時間「不要超過 2 小時」，避免長途拉車。
                    **參考景點資料庫** (請從中選擇其他景點填補空檔)：
                    {context_str}
                    請回傳 JSON List：
                    - "Day": (數字)
                    - "Order": (數字)
                    - "City": (字串)
                    - "District": (字串)
                    - "Place": (字串, 必須使用資料庫中的完整名稱)
                    - "Transport": (字串, 詳細指引)
                    """
                    
                    response = model.generate_content(prompt)
                    data = json.loads(response.text)
                    
                    df_temp = pd.DataFrame(data)
                    
                    if not df_temp.empty and 'Place' in df_temp.columns:
                        df_temp = df_temp.drop_duplicates(subset=['Place'], keep='first')
                        if 'Day' in df_temp.columns:
                            df_temp = df_temp.sort_values(by=['Day', 'Order'])
                            df_temp['Order'] = df_temp.groupby('Day').cumcount() + 1
                    
                    st.session_state['schedule_df'] = df_temp
                    
                except Exception as e:
                    st.error(f"規劃失敗：{e}")
                    if st.button("重試"): st.rerun()
                    st.stop()

        if st.session_state['schedule_df'] is not None:
            tab1, tab2, tab3, tab4 = st.tabs(["✏️ 行程編輯", "📸 圖文詳情", "📊 流程圖","⛅ 旅遊當地天氣預報"])
            
            # --- [重點修改開始] 修改 tab1 的顯示方式 ---
            with tab1:
                st.markdown("### ✏️ 詳細行程表")
                
                # 準備資料
                current_df = st.session_state['schedule_df']
                
                if not current_df.empty:
                    # 確保按順序排列
                    current_df = current_df.sort_values(by=["Day", "Order"])
                    unique_days = sorted(current_df['Day'].unique())
                    
                    # 1. 先建立所有天數的標題清單
                    day_tabs_labels = []
                    for day in unique_days:
                        day_int = int(day)
                        try:
                            current_date = start_d + timedelta(days=day_int-1)
                            date_str = f"{current_date.month}/{current_date.day}"
                            day_tabs_labels.append(f"🗓️ Day {day_int} ({date_str})")
                        except:
                            day_tabs_labels.append(f"Day {day_int}")

                    # 2. 建立分頁元件 (Tabs)
                    day_tabs = st.tabs(day_tabs_labels)

                    # 暫存修改後的各天 DataFrame
                    edited_days_list = []
                    
                    # 3. 將每一天的內容填入對應的 Tab
                    for i, day in enumerate(unique_days):
                        day_int = int(day)
                        
                        # 使用對應的 Tab Context
                        with day_tabs[i]:
                            # 篩選該天資料
                            day_df = current_df[current_df['Day'] == day].reset_index(drop=True)
                            
                            # --- 功能按鈕區 (導航) ---
                            # 這裡不需要再顯示標題了，因為 Tab 上面已經有標題
                            col_space, col_nav = st.columns([3, 1]) 
                            with col_nav:
                                day_spots = day_df['Place'].tolist()
                                if day_spots:
                                    encoded_spots = [urllib.parse.quote(spot) for spot in day_spots]
                                    map_url = f"https://www.google.com/maps/dir/{'/'.join(encoded_spots)}"
                                    st.link_button(f"🗺️ 開啟 Day {day_int} 導航", map_url, use_container_width=True)
                            
                            # --- 獨立的編輯器 ---
                            edited_day_df = st.data_editor(
                                day_df,
                                key=f"editor_day_{day_int}", # 每個編輯器需要唯一的 key
                                num_rows="dynamic",
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Day": None, # 隱藏天數欄位
                                    "Order": st.column_config.NumberColumn("順序", width="small", min_value=1),
                                    "City": st.column_config.TextColumn("縣市", width="small"),
                                    "District": st.column_config.TextColumn("地區", width="small"),
                                    "Place": st.column_config.TextColumn("景點名稱", width="medium", required=True),
                                    "Transport": st.column_config.TextColumn("交通/備註", width="large")
                                }
                            )
                            
                            # 強制寫回正確的天數 (防止使用者新增列時 Day 為 NaN)
                            edited_day_df['Day'] = day_int
                            edited_days_list.append(edited_day_df)
                    
                    # --- 合併所有天數的修改 ---
                    if edited_days_list:
                        new_full_df = pd.concat(edited_days_list, ignore_index=True)
                        
                        # 檢查是否有變動，若有則更新 Session State 並重跑
                        old_comp = st.session_state['schedule_df'].sort_values(by=["Day", "Order"]).reset_index(drop=True)
                        new_comp = new_full_df.sort_values(by=["Day", "Order"]).reset_index(drop=True)
                        
                        if not new_comp.equals(old_comp):
                            st.session_state['schedule_df'] = new_comp
                            st.rerun()

                # 下載與存檔區塊 (保持在 Tabs 下方，作為全域功能)
                st.markdown("---")
                col_save, col_dl = st.columns(2)
                with col_save:
                    if st.button("💾 儲存此行程", type="primary", use_container_width=True):
                        # 1. 準備行程資料
                        save_data = st.session_state['schedule_df'].to_dict('records')
                        
                        # 2. [新增] 準備天氣資料 (當下直接抓取並凍結保存)
                        weather_save_data = []
                        try:
                            # 即使使用者還沒點開 Tab4，儲存時也要背景執行一次天氣查詢
                            w_df = process_schedule_weather(st.session_state['schedule_df'], start_d)
                            if not w_df.empty:
                                weather_save_data = w_df.to_dict('records')
                        except Exception as e:
                            print(f"Weather save error: {e}")

                        # 3. 儲存
                        save_history_record(
                            st.session_state.get('user_email'),
                            st.session_state['input_dest'],
                            st.session_state['input_days'],
                            save_data,
                            'ai',
                            start_date_str=start_d.strftime("%Y-%m-%d"),
                            weather_data=weather_save_data # 傳入天氣資料
                        )
                        st.toast("✅ 行程與天氣資訊已儲存成功！")
                
                with col_dl:
                    txt_content = generate_plain_text(st.session_state['schedule_df'], start_date=start_d)
                    st.download_button("📥 下載行程文字檔", txt_content, f"{st.session_state['input_dest']}_行程.txt", use_container_width=True)

                # 顯示美化的 HTML 行程卡片
                st.markdown("### 👓 行程預覽卡片")
                html_content = generate_html_display(st.session_state['schedule_df'], start_date=start_d)
                st.markdown(html_content, unsafe_allow_html=True)
            with tab2:
                # 這裡需要從完整的 DF 取得所有景點
                all_places = st.session_state['schedule_df']['Place'].unique().tolist() if st.session_state['schedule_df'] is not None else []
                selected_place = st.selectbox("查看詳情：", all_places)
                if selected_place:
                    display_attraction_details(selected_place)

            with tab3:
                dot_code = generate_dot_from_df(st.session_state['schedule_df'])
                if dot_code:
                    st.graphviz_chart(dot_code, use_container_width=True)

            # 🆕 Tab 4: 天氣預報邏輯
            with tab4:
                st.markdown("### ⛅ 旅遊當地天氣預報")
                st.info("系統已根據您的行程日期自動鎖定天氣預報。")
                
                # 直接檢查 Session State 是否有天氣資料
                weather_df = st.session_state.get('ai_weather_df')
                
                # 如果行程存在但天氣資料意外遺失 (例如舊 Session)，則補查一次
                if (weather_df is None or weather_df.empty) and st.session_state['schedule_df'] is not None:
                     with st.spinner("☁️ 正在抓取天氣資料..."):
                         weather_df = process_schedule_weather(st.session_state['schedule_df'], start_d)
                         st.session_state['ai_weather_df'] = weather_df

                if weather_df is not None and not weather_df.empty:
                    # 1. 取得所有天數並排序
                    unique_days = sorted(weather_df['Day'].unique())
                    
                    # 2. 準備 Tab 標籤
                    weather_tab_labels = []
                    for day in unique_days:
                        try:
                            date_str = weather_df[weather_df['Day'] == day]['Date'].iloc[0]
                            weather_tab_labels.append(f"🗓️ Day {int(day)} ({date_str})")
                        except:
                            weather_tab_labels.append(f"Day {int(day)}")
                    
                    # 3. 建立 Tabs
                    w_tabs = st.tabs(weather_tab_labels)
                    
                    # 4. 將資料填入對應 Tab
                    for i, day in enumerate(unique_days):
                        with w_tabs[i]:
                            # 注意：這裡原本定義的變數名稱是 day_weather
                            day_weather = weather_df[weather_df['Day'] == day]
                            
                            st.dataframe(
                                day_weather, # 這裡用 day_weather
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "Day": None, "Date": None,
                                    "Place": st.column_config.TextColumn("📍 景點"),
                                    "Temp": st.column_config.TextColumn("🌡️ 氣溫"),
                                    "Rain": st.column_config.TextColumn("☔ 降雨"),
                                    "Note": st.column_config.TextColumn("備註", width="large")
                                }
                            )

                            # 呼叫替換按鈕
                            render_rain_swap_ui(day_weather, mode='ai') # ✅ 修正為 ai
                            # --- [修正處] 顯示穿衣建議 ---
                            st.markdown("#### 👗 每日穿搭小幫手")
                            if 'generate_clothing_advice' in globals():
                                # ⚠️ 修正：這裡必須傳入 day_weather，而不是 day_weather_df
                                advice = generate_clothing_advice(day_weather) 
                                with st.container(border=True):
                                    st.markdown(advice)
                            # ---------------------------
# --- 歷史紀錄頁面 ---
def history_page():
    sidebar_component()
    st.title("📜 我的旅遊歷史紀錄")
    
    # 讀取資料
    all_history = load_history()
    user_email = st.session_state.get('user_email') 
    
    if not user_email:
        st.error("系統錯誤：無法識別使用者 Email，請重新登入。")
        return

    my_records = [r for r in all_history if r['email'] == user_email]
    
    if not my_records:
        st.info("目前沒有歷史紀錄。趕快去規劃一個行程並儲存吧！")
    else:
        # 按時間倒序排列
        my_records = sorted(my_records, key=lambda x: x['timestamp'], reverse=True)
        
        for record in my_records:
            trip_name = record.get('trip_name', '').strip()
            if not trip_name: display_title = "(未命名行程)"
            else: display_title = trip_name
            
            expander_title = f"📂 {display_title} 　🕒 {record['timestamp'][:10]}"
            
            with st.expander(expander_title):
                # --- 1. 編輯名稱區塊 ---
                st.caption("✏️ 編輯行程名稱")
                col_edit_input, col_edit_btn = st.columns([3, 1], vertical_alignment="bottom")
                with col_edit_input:
                    new_name_input = st.text_input("名稱", value=trip_name, key=f"input_name_{record['id']}", label_visibility="collapsed")
                with col_edit_btn:
                    if st.button("🖊️ 確認修改", key=f"btn_rename_{record['id']}", use_container_width=True):
                        if new_name_input != trip_name:
                            update_history_name_in_db(record['id'], new_name_input)
                            st.toast(f"✅ 名稱已更新為：{new_name_input}")
                            time.sleep(0.5)
                            st.rerun()
                st.divider()

                # --- 2. 準備基本資料 ---
                # 取得出發日期物件 (for 計算日期用)
                record_start_date_str = record.get('start_date')
                start_d = None
                if record_start_date_str:
                    try:
                        start_d = datetime.strptime(record_start_date_str, "%Y-%m-%d").date()
                    except: pass
                
                # --- 3. 顯示行程內容 (區分 AI / 手動) ---
                
                # [情況 A] AI 模式 - 使用分頁顯示
                if record['mode'] == 'ai':
                    data_content = record.get('data', [])
                    if data_content:
                        df_history = pd.DataFrame(data_content)
                        
                        # 建立三大分頁
                        h_tab1, h_tab2, h_tab3, h_tab4 = st.tabs(["🗓️ 行程表", "📸 圖文詳情", "📊 流程圖", "⛅ 當時天氣紀錄"])                        
                        # --- 分頁 1: 行程表 (含天數分頁) ---
                        with h_tab1:
                            if not df_history.empty and 'Day' in df_history.columns:
                                # 取得所有天數
                                unique_days = sorted(df_history['Day'].unique())
                                
                                # 建立天數分頁
                                day_tabs = st.tabs([f"Day {int(d)}" for d in unique_days])
                                
                                for i, day in enumerate(unique_days):
                                    with day_tabs[i]:
                                        # 篩選該天資料
                                        day_df = df_history[df_history['Day'] == day].sort_values(by="Order")
                                        
                                        # (A) 導航按鈕
                                        day_spots = day_df['Place'].tolist()
                                        if day_spots:
                                            encoded_spots = [urllib.parse.quote(spot) for spot in day_spots]
                                            map_url = f"https://www.google.com/maps/dir/{'/'.join(encoded_spots)}"
                                            
                                            # 計算日期標籤
                                            try:
                                                if start_d:
                                                    current_date = start_d + timedelta(days=int(day)-1)
                                                    date_label = f"{current_date.month}/{current_date.day}"
                                                else:
                                                    date_label = f"Day {day}"
                                            except:
                                                date_label = f"Day {day}"

                                            st.link_button(
                                                label=f"🗺️ 開啟 Day {int(day)} ({date_label}) 導航",
                                                url=map_url,
                                                use_container_width=True
                                            )
                                        
                                        # (B) 表格顯示 (唯讀)
                                        st.dataframe(
                                            day_df,
                                            hide_index=True,
                                            use_container_width=True,
                                            column_config={
                                                "Day": st.column_config.NumberColumn("Day", disabled=True),
                                                "Order": st.column_config.NumberColumn("序", min_value=1, width="small"),
                                                "Place": st.column_config.TextColumn("景點", width="medium"),
                                                "Transport": st.column_config.TextColumn("交通", width="large")
                                            }
                                        )
                                        
                                        # (C) 圖文卡片
                                        html_view = generate_html_display(day_df, start_date=start_d)
                                        st.markdown(html_view, unsafe_allow_html=True)
                            else:
                                st.warning("行程資料格式有誤或為空")

                            st.markdown("---")
                            # 下載文字檔
                            txt_hist = generate_plain_text(df_history, start_date=start_d)
                            file_name = f"history_{display_title}.txt"
                            st.download_button("📥 下載文字檔", txt_hist, file_name, key=f"dl_txt_{record['id']}", use_container_width=True)

                        # --- 分頁 2: 圖文詳情 ---
                        with h_tab2:
                            place_options = df_history['Place'].unique().tolist()
                            selected_place = st.selectbox("查看景點詳情：", place_options, key=f"sel_spot_{record['id']}")
                            if selected_place:
                                display_attraction_details(selected_place)
                        
                        # --- 分頁 3: 流程圖 ---
                        with h_tab3:
                            dot_code = generate_dot_from_df(df_history)
                            if dot_code:
                                st.graphviz_chart(dot_code, use_container_width=True)
                                st.download_button("📥 下載 DOT 檔", dot_code, f"{display_title}.dot", key=f"dl_dot_{record['id']}")
                        with h_tab4:
                            saved_weather = record.get('weather_content', [])
                            if saved_weather:
                                w_df_history = pd.DataFrame(saved_weather)
                                
                                if not w_df_history.empty and 'Day' in w_df_history.columns:
                                    # 1. 建立天數分頁
                                    u_days = sorted(w_df_history['Day'].unique())
                                    wh_tabs = st.tabs([f"Day {int(d)}" for d in u_days])
                                    
                                    for i, day in enumerate(u_days):
                                        with wh_tabs[i]:
                                            day_w_data = w_df_history[w_df_history['Day'] == day]
                                            
                                            # 顯示表格
                                            st.dataframe(
                                                day_w_data,
                                                hide_index=True,
                                                use_container_width=True,
                                                column_config={
                                                    "Day": None, "Date": None,
                                                    "Place": st.column_config.TextColumn("📍 景點"),
                                                    "Temp": st.column_config.TextColumn("🌡️ 氣溫"),
                                                    "Rain": st.column_config.TextColumn("☔ 降雨"),
                                                    "Note": st.column_config.TextColumn("備註")
                                                }
                                            )
                                            
                                            # 顯示穿衣建議 (重用邏輯，但不重新抓 API)
                                            # 因為 generate_clothing_advice 是解析文字字串，所以可以直接用儲存的資料跑分析
                                            st.markdown("#### 👗 當時穿搭建議")
                                            if 'generate_clothing_advice' in globals():
                                                advice = generate_clothing_advice(day_w_data)
                                                with st.container(border=True):
                                                    st.markdown(advice)
                                else:
                                    st.info("⚠️ 儲存的天氣資料格式有誤。")
                            else:
                                st.info("⚠️ 此紀錄未包含天氣資訊 (可能是舊版紀錄)。")

                    else:
                        st.warning("查無行程資料")
                
                # [情況 B] 手動模式 (維持條列式，因為資料結構不同)
                elif record['mode'] == 'manual':
                    st.info("此為手動規劃行程，格式較為簡易。")
                    schedule_dict = record.get('data', {})
                    txt_lines = []
                    
                    if schedule_dict:
                        sorted_days = sorted(schedule_dict.keys(), key=lambda x: int(x))
                        
                        for day in sorted_days:
                            spots = schedule_dict[day]
                            
                            date_suffix = ""
                            if start_d:
                                try:
                                    d = start_d + timedelta(days=int(day)-1)
                                    date_suffix = f" ({d.strftime('%Y-%m-%d')})"
                                except: pass
                                
                            st.markdown(f"**Day {day}{date_suffix}**")
                            
                            # 導航
                            if spots and len(spots) >= 1:
                                encoded_spots = [urllib.parse.quote(spot) for spot in spots]
                                map_url = f"https://www.google.com/maps/dir/{'/'.join(encoded_spots)}"
                                st.link_button(f"🗺️ Day {day} 導航", map_url)
                            
                            txt_lines.append(f"[Day {day}{date_suffix}]")
                            for i, spot in enumerate(spots):
                                st.write(f"{i+1}. {spot}")
                                txt_lines.append(f"{i+1}. {spot}")
                            st.divider()
                    else:
                        st.warning("查無行程資料")
                
                # --- 4. 底部刪除按鈕 ---
                if st.button("🗑️ 刪除此紀錄", key=f"del_{record['id']}", type="primary", use_container_width=True):
                    delete_history_record(record['id'])
                    st.toast("✅ 紀錄已刪除")
                    time.sleep(0.5)
                    st.rerun()
# --- 手動模式頁面 ---
def manual_page():
    sidebar_component()
    st.title("📸 台灣景點圖片瀏覽器 (手動模式)")
    
    # --- 0. 初始化交通方式儲存庫 ---
    # 使用字典儲存：Key 為 "Day_Index" (例如 "1_0"), Value 為 "交通方式"
    if 'manual_trans_data' not in st.session_state:
        st.session_state['manual_trans_data'] = {}

    # 定義交通選項
    trans_options = ["自行開車", "大眾運輸", "機車", "步行", "計程車", "高鐵", "火車", "捷運", "租車", "公車"]

    # --- 1. 日期與天數設定 ---
    col_days, col_info = st.columns([1.5, 2])
    with col_days:
        date_range = st.date_input(
            "📅 設定旅遊日期範圍", 
            value=[st.session_state['trip_start_date'], st.session_state['trip_end_date']],
            min_value=date.today()
        )
        if len(date_range) == 2:
            new_start, new_end = date_range
            new_days = (new_end - new_start).days + 1
            if new_days != st.session_state['trip_days'] or new_start != st.session_state['trip_start_date']:
                st.session_state['trip_start_date'] = new_start
                st.session_state['trip_end_date'] = new_end
                st.session_state['trip_days'] = new_days
                # 重置行程
                for d in range(1, new_days + 1):
                    if d not in st.session_state['trip_schedule']:
                        st.session_state['trip_schedule'][d] = []
                st.rerun()  
    with col_info:
        st.info(f"目前規劃： **{st.session_state['trip_days']} 天**")
    
    st.markdown("---")

    # --- 2. 搜尋與加入景點 ---
    df = attractions_db
    if df is not None:
        search_keyword = st.text_input("🔍 搜尋關鍵字 (輸入景點名稱)：")
        if search_keyword:
            search_keyword = search_keyword.replace("台", "臺")
            df = df[df['ScenicSpotName'].str.contains(search_keyword, case=False, na=False, regex=False)]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            city_list = df['City'].unique().tolist()
            selected_city = st.selectbox("縣市：", city_list)
            df_city = df[df['City'] == selected_city]
        with c2:
            district_list = df_city['District'].unique().tolist()
            selected_district = st.selectbox("地區：", district_list)
            df_final = df_city[df_city['District'] == selected_district]
        with c3:
            spot_list = df_final['ScenicSpotName'].unique().tolist()
            selected_spot = st.selectbox("景點：", spot_list)

        if selected_spot:
            display_attraction_details(selected_spot)
            
            # --- [修改] 加入行程區域 ---
            col_add_day, col_add_trans, col_add_btn = st.columns([2, 2, 2], vertical_alignment="bottom")
            
            with col_add_day:
                day_options = {}
                for d in range(1, st.session_state['trip_days'] + 1):
                    curr = st.session_state['trip_start_date'] + timedelta(days=d-1)
                    day_options[d] = f"Day {d} ({curr.strftime('%m/%d')})"
                target_day = st.selectbox("加入哪一天？", options=day_options.keys(), format_func=lambda x: day_options[x])
            
            with col_add_trans:
                # 新增：選擇交通方式
                selected_trans_mode = st.selectbox("前往此處的交通：", trans_options, index=0)

            with col_add_btn:
                if st.button(f"➕ 加入行程", type="primary", use_container_width=True):
                    if target_day not in st.session_state['trip_schedule']:
                        st.session_state['trip_schedule'][target_day] = []
                    
                    if selected_spot not in st.session_state['trip_schedule'][target_day]:
                        # 1. 加入景點
                        st.session_state['trip_schedule'][target_day].append(selected_spot)
                        # 2. 儲存交通方式 (Key 為 Day_Index)
                        new_idx = len(st.session_state['trip_schedule'][target_day]) - 1
                        st.session_state['manual_trans_data'][f"{target_day}_{new_idx}"] = selected_trans_mode
                        
                        st.toast(f"已加入 {selected_spot} ({selected_trans_mode})")
                        st.rerun()
                    else:
                        st.warning("該景點已在當天行程中")

    st.markdown("---")

    # --- 3. 行程顯示與進階功能 ---
    has_spots = any(len(spots) > 0 for spots in st.session_state['trip_schedule'].values())

    if has_spots:
        st.subheader("📋 行程總覽與分析")
        
        # 將資料轉換為 DataFrame (讀取 manual_trans_data)
        manual_data = []
        for day, spots in st.session_state['trip_schedule'].items():
            for idx, spot_name in enumerate(spots):
                city_str = ""
                dist_str = ""
                if attractions_db is not None:
                    row = attractions_db[attractions_db['ScenicSpotName'] == spot_name]
                    if not row.empty:
                        city_str = row.iloc[0]['City']
                        dist_str = row.iloc[0]['District']
                
                # 從 session_state 讀取交通方式，若無則預設"自行開車"
                t_key = f"{day}_{idx}"
                trans_val = st.session_state['manual_trans_data'].get(t_key, "自行開車")

                manual_data.append({
                    "Day": int(day),
                    "Order": idx + 1,
                    "Place": spot_name,
                    "City": city_str,
                    "District": dist_str,
                    "Transport": trans_val # 這裡填入選擇的值
                })
        
        manual_df = pd.DataFrame(manual_data)

        tab1, tab2, tab3, tab4 = st.tabs(["👓 行程預覽", "📸 圖文詳情", "📊 流程圖", "⛅ 天氣預報"])

        with tab1:
            # 1. 顯示美化的行程卡片 (維持原樣)
            html_view = generate_html_display(manual_df, start_date=st.session_state['trip_start_date'])
            st.markdown(html_view, unsafe_allow_html=True)
            
            # --- [新增功能 1] 下載行程文字檔 ---
            st.markdown("---")
            # 呼叫現有的文字產生函式
            txt_content = generate_plain_text(manual_df, start_date=st.session_state['trip_start_date'])
            st.download_button(
                label="📥 下載行程文字檔 (.txt)",
                data=txt_content,
                file_name=f"手動規劃行程_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
            # --- [修改功能 2] 編輯區塊加入導航 ---
            with st.expander("🛠️ 編輯排序、交通與刪除"):
                for day in range(1, st.session_state['trip_days'] + 1):
                    day_spots = st.session_state['trip_schedule'].get(day, [])
                    if day_spots:
                        # 使用 columns 讓「Day X」標題與「導航按鈕」排在同一排
                        col_day_title, col_nav_btn = st.columns([3, 1], vertical_alignment="center")
                        
                        with col_day_title:
                            st.markdown(f"**Day {day}**")
                        
                        with col_nav_btn:
                            # 產生 Google Maps 導航連結
                            if len(day_spots) >= 1:
                                encoded_spots = [urllib.parse.quote(spot) for spot in day_spots]
                                map_url = f"https://www.google.com/maps/dir/{'/'.join(encoded_spots)}"
                                st.link_button("🗺️ 開啟導航", map_url, use_container_width=True)
                        
                        # --- 以下維持原本的編輯清單邏輯 ---
                        for i, spot in enumerate(day_spots):
                            # 版面分配：名稱 | 交通選單 | 上 | 下 | 刪
                            c1, c2, c3, c4, c5 = st.columns([4, 3, 1, 1, 1], vertical_alignment="center")
                            
                            with c1: 
                                st.write(f"{i+1}. {spot}")
                            
                            with c2:
                                # 交通方式編輯
                                curr_key = f"{day}_{i}"
                                curr_val = st.session_state['manual_trans_data'].get(curr_key, "自行開車")
                                try:
                                    idx_opt = trans_options.index(curr_val)
                                except:
                                    idx_opt = 0
                                
                                new_trans = st.selectbox(
                                    "交通", 
                                    trans_options, 
                                    index=idx_opt, 
                                    key=f"edit_trans_{day}_{i}", 
                                    label_visibility="collapsed"
                                )
                                if new_trans != curr_val:
                                    st.session_state['manual_trans_data'][curr_key] = new_trans
                                    st.rerun()

                            with c3:
                                if i > 0 and st.button("⬆️", key=f"main_up_{day}_{i}"):
                                    # 交換順序
                                    day_spots[i], day_spots[i-1] = day_spots[i-1], day_spots[i]
                                    # 交換交通資料
                                    k_curr, k_prev = f"{day}_{i}", f"{day}_{i-1}"
                                    d = st.session_state['manual_trans_data']
                                    d[k_curr], d[k_prev] = d.get(k_prev, "自行開車"), d.get(k_curr, "自行開車")
                                    st.rerun()
                            with c4:
                                if i < len(day_spots) - 1 and st.button("⬇️", key=f"main_down_{day}_{i}"):
                                    # 交換順序
                                    day_spots[i], day_spots[i+1] = day_spots[i+1], day_spots[i]
                                    # 交換交通資料
                                    k_curr, k_next = f"{day}_{i}", f"{day}_{i+1}"
                                    d = st.session_state['manual_trans_data']
                                    d[k_curr], d[k_next] = d.get(k_next, "自行開車"), d.get(k_curr, "自行開車")
                                    st.rerun()
                            with c5:
                                if st.button("🗑️", key=f"main_del_{day}_{i}"):
                                    day_spots.pop(i)
                                    # 刪除並重整交通資料 key
                                    d = st.session_state['manual_trans_data']
                                    if f"{day}_{i}" in d: del d[f"{day}_{i}"]
                                    for k in range(i, len(day_spots)): 
                                        old_key = f"{day}_{k+1}"
                                        new_key = f"{day}_{k}"
                                        if old_key in d:
                                            d[new_key] = d[old_key]
                                            del d[old_key]
                                    st.rerun()
                        st.divider()
        with tab2:
            all_places = manual_df['Place'].unique().tolist()
            selected_place_view = st.selectbox("查看詳情：", all_places, key="manual_view_sel")
            if selected_place_view:
                display_attraction_details(selected_place_view)

        with tab3:
            st.info("💡 此圖表展示您的路線順序。")
            dot_code = generate_dot_from_df(manual_df)
            if dot_code:
                st.graphviz_chart(dot_code, use_container_width=True)

        with tab4:
            st.markdown("### ⛅ 旅遊當地天氣預報")
            
            if not manual_df.empty:
                # 1. 產生當前行程的「特徵簽章」(只要內容變動，字串就會變)
                # 使用 JSON dump 來將 list of dicts 轉成字串作為比對依據
                current_signature = json.dumps(manual_data, sort_keys=True, ensure_ascii=False)
                
                # 2. 檢查是否需要重新查詢
                # 如果快取是空的，或者簽章不符(行程有變)，就重新查詢
                cached_data = st.session_state.get('manual_weather_cache', {})
                if cached_data.get("signature") != current_signature:
                    start_d = st.session_state['trip_start_date']
                    with st.spinner("☁️ 行程有變動，正在更新天氣資料..."):
                        weather_df = process_schedule_weather(manual_df, start_d)
                        # 更新快取
                        st.session_state['manual_weather_cache'] = {
                            "signature": current_signature,
                            "df": weather_df
                        }
                else:
                    # 使用快取資料
                    weather_df = cached_data.get("df")

                # 3. 顯示資料 (邏輯同 AI 模式)
                if weather_df is not None and not weather_df.empty:
                    unique_days = sorted(weather_df['Day'].unique())
                    weather_tabs = st.tabs([f"Day {d}" for d in unique_days])
                    
                    for i, day in enumerate(unique_days):
                        with weather_tabs[i]:
                            day_weather = weather_df[weather_df['Day'] == day]
                            st.dataframe(
                                day_weather,
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "Day": None, "Date": None,
                                    "Place": st.column_config.TextColumn("📍 景點"),
                                    "Temp": st.column_config.TextColumn("🌡️ 氣溫"),
                                    "Rain": st.column_config.TextColumn("☔ 降雨"),
                                    "Note": st.column_config.TextColumn("備註", width="large")
                                }
                            )

                            # --- [插入點] 呼叫替換按鈕函式 ---
                            render_rain_swap_ui(day_weather, mode='manual')
                            # ------------------------------

                            st.markdown("#### 👗 每日穿搭小幫手")
                            if 'generate_clothing_advice' in globals():
                                advice = generate_clothing_advice(day_weather)
                                with st.container(border=True):
                                    st.markdown(advice)
            else:
                st.warning("請先加入景點以查看天氣。")

        st.markdown("---")
        if st.button("💾 儲存此行程", type="primary", use_container_width=True):
             save_data = manual_df.to_dict('records')
             
             # [新增] 準備天氣資料
             weather_save_data = []
             try:
                 w_df = process_schedule_weather(manual_df, st.session_state['trip_start_date'])
                 if not w_df.empty:
                     weather_save_data = w_df.to_dict('records')
             except: pass

             save_history_record(
                st.session_state.get('user_email'),
                f"手動規劃-{datetime.now().strftime('%m%d-%H%M')}",
                st.session_state['trip_days'],
                save_data,
                'ai', # 存成 ai 模式以保持格式統一
                start_date_str=st.session_state['trip_start_date'].strftime("%Y-%m-%d"),
                weather_data=weather_save_data # 傳入天氣資料
            )
             st.toast("✅ 行程與天氣資訊已儲存！")
    
    else:
        st.info("👋 目前行程表是空的，請從上方搜尋並加入景點。")
# --- 11. 路由控制 ---
def logged_in_interface():
    if st.session_state['mode'] == 'menu':
        menu_page()
    elif st.session_state['mode'] == 'ai_chat':
        ai_planning_page()
    elif st.session_state['mode'] == 'manual':
        manual_page()
    elif st.session_state['mode'] == 'history':
        history_page()

if st.session_state['logged_in']:
    logged_in_interface()
else:
    if st.session_state['current_page'] == 'signup':
        signup_page()
    elif st.session_state['current_page'] == 'forgot_password':
        forgot_password_page()
    elif st.session_state['current_page'] == 'reset_password':
        reset_password_page()
    else:
        login_page()