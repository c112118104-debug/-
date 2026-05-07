import streamlit as st
import requests

st.set_page_config(page_title="智慧旅遊 - 天氣建議", page_icon="🌤", layout="centered")
st.title("🌤 智慧旅遊 - 天氣建議（即時溫度 + 降雨率）")

API_KEY = "8f221f75fe6487b247ef3dbcdd22b1c4"

# 建議用經緯度最穩（台灣縣市名稱常常查不到）
city_map = {
    "臺北市": {"lat": 25.0330, "lon": 121.5654},
    "新北市": {"lat": 25.0169, "lon": 121.4628},
    "桃園市": {"lat": 24.9937, "lon": 121.3010},
    "臺中市": {"lat": 24.1477, "lon": 120.6736},
    "臺南市": {"lat": 22.9999, "lon": 120.2269},
    "高雄市": {"lat": 22.6273, "lon": 120.3014},
    "基隆市": {"lat": 25.1276, "lon": 121.7392},
    "新竹市": {"lat": 24.8138, "lon": 120.9675},
    "新竹縣": {"lat": 24.8397, "lon": 121.0020},
    "苗栗縣": {"lat": 24.5602, "lon": 120.8214},
    "彰化縣": {"lat": 24.0518, "lon": 120.5161},
    "南投縣": {"lat": 23.9609, "lon": 120.9719},
    "雲林縣": {"lat": 23.7092, "lon": 120.4313},
    "嘉義市": {"lat": 23.4801, "lon": 120.4491},
    "嘉義縣": {"lat": 23.4518, "lon": 120.2555},
    "屏東縣": {"lat": 22.5519, "lon": 120.5488},
    "宜蘭縣": {"lat": 24.7021, "lon": 121.7378},
    "花蓮縣": {"lat": 23.9872, "lon": 121.6015},
    "臺東縣": {"lat": 22.7972, "lon": 121.0714},
    "澎湖縣": {"lat": 23.5711, "lon": 119.5793},
    "金門縣": {"lat": 24.4329, "lon": 118.3186},
    "連江縣": {"lat": 26.1605, "lon": 119.9499},
}

city_zh = st.selectbox("📍 請選擇旅遊城市", list(city_map.keys()))
lat = city_map[city_zh]["lat"]
lon = city_map[city_zh]["lon"]

@st.cache_data(ttl=600)
def get_current_weather(lat, lon, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=zh_tw"
    return requests.get(url, timeout=15).json()

@st.cache_data(ttl=600)
def get_forecast_5day_3hour(lat, lon, api_key):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=zh_tw"
    return requests.get(url, timeout=15).json()

current = get_current_weather(lat, lon, API_KEY)
forecast = get_forecast_5day_3hour(lat, lon, API_KEY)

# 基本錯誤處理
if str(current.get("cod")) != "200":
    st.error("❌ 目前天氣取得失敗（請確認 API Key）")
    st.stop()
if str(forecast.get("cod")) != "200":
    st.error("❌ 預報資料取得失敗（請確認 API Key）")
    st.stop()

temp = float(current["main"]["temp"])
desc = current["weather"][0]["description"]

# 取「未來 12 小時」(每 3 小時一筆 → 4 筆) 的最大降雨率 pop
next_entries = forecast["list"][:4]
pops = [float(item.get("pop", 0.0)) for item in next_entries]
pop_max = max(pops) if pops else 0.0
pop_percent = round(pop_max * 100)

st.write(f"🌡 目前溫度：**{temp:.1f}°C**（{desc}）")
st.write(f"🌧 未來 12 小時最高降雨率：**{pop_percent}%**")


# === 1) 降雨率分級建議（以 60% 為室內/室外界線） ===
# pop_percent 是 0~100 的整數（例如 73 代表 73%）
if pop_percent < 10:
    st.success(
        "🌤 **降雨率 < 10%｜室外活動最佳**\n\n"
        "✅ 輕裝上陣，準備週邊薄外套即可。\n"
        "- 適合安排戶外景點、步行路線、自然景點\n"
        "- 仍可帶折疊傘以防突發短暫降雨"
    )

elif pop_percent < 30:
    st.success(
        "⛅ **降雨率 10–29%｜大致適合室外**\n\n"
        "✅ 輕裝上陣，準備週邊薄外套即可。\n"
        "🔹 建議：可攜帶輕便雨具備用（折疊傘/薄雨衣）"
    )

elif pop_percent < 50:
    st.info(
        "🌦 **降雨率 30–49%｜室外可行（請備雨具）**\n\n"
        "☔ 攜帶雨具備用。\n"
        "- 室外行程建議保留彈性（可快速轉室內）\n"
        "- 戶外停留時間可稍微縮短，避免遇到突降雨"
    )

elif pop_percent < 60:
    st.warning(
        "🌧 **降雨率 50–59%｜偏高（室外仍可，但要隨時切換）**\n\n"
        "☔ 建議攜帶雨具，並留意天氣變化。\n"
        "- 戶外景點建議安排在較短時段\n"
        "- 同步準備 1–2 個室內備案（商場/展覽/博物館）"
    )

else:  # pop_percent >= 60
    st.error(
        "⛈ **降雨率 ≥ 60%｜建議優先安排室內行程**\n\n"
        "☔ 必須攜帶雨具，並留意是否有大雨特報（24 小時累積雨量 80 毫米以上）。\n\n"
        "🏠 **行程建議（室內優先）**\n"
        "- 優先安排室內景點（博物館、展覽、商場、室內市集、美食行程）\n"
        "- 若一定要戶外：縮短停留時間、選擇有遮蔽路線、避免山區與河岸等風險地點\n"
        "- 行程保留彈性：雨勢趨緩再安排戶外點"
    )

st.divider()

# === 2) 溫度建議（你之前的四段版：悶熱/稍熱/舒適/過冷） ===
if temp > 30:
    st.warning(
        "🥵 **悶熱天氣（> 30°C）｜高溫因應與行程調整建議**\n\n"
        "目前天氣悶熱，體感溫度高，長時間戶外活動容易造成疲勞與中暑風險：\n\n"
        "🧴 **健康與防護**\n"
        "- 加強防曬（帽子、陽傘、防曬乳），避免正中午曝曬\n"
        "- 建議每 30 分鐘補充水分，避免脫水或熱衰竭\n\n"
        "🗺 **行程調整建議**\n"
        "- 戶外景點優先安排於清晨或傍晚\n"
        "- 中午時段改為室內景點（博物館、商場、展覽）\n"
        "- 若行程密集，建議適度刪減戶外停留時間\n\n"
        "🎒 **裝備提醒**\n"
        "- 攜帶隨身水壺、涼感毛巾、替換衣物"
    )

elif 26 <= temp <= 30:
    st.info(
        "😓 **稍熱天氣（26–30°C）｜體力管理與節奏安排**\n\n"
        "氣溫偏高但仍適合活動，建議注意行程節奏與休息安排：\n\n"
        "🗺 **行程安排建議**\n"
        "- 戶外與室內景點交錯安排，避免連續曝曬\n"
        "- 行程中預留彈性休息時間或咖啡、美食停留點\n\n"
        "💧 **補水與防護**\n"
        "- 戶外活動前後補充水分，避免長時間缺水\n"
        "- 可準備帽子或薄外套，減少陽光直射不適感\n\n"
        "🎯 **旅遊型態建議**\n"
        "- 適合城市漫遊、文化景點、半日戶外行程"
    )

elif 18 <= temp <= 25:
    st.success(
        "🌤 **舒適天氣（18–25°C）｜戶外行程最佳狀態**\n\n"
        "目前氣溫舒適，非常適合多數旅遊與戶外活動：\n\n"
        "🗺 **行程建議**\n"
        "- 可安排較多戶外景點與長時間步行路線\n"
        "- 適合自然景點、市集、街區探索與拍照行程\n\n"
        "🎒 **基本準備**\n"
        "- 建議攜帶飲水與輕便外套，以應對早晚溫差\n\n"
        "✨ **體驗加分**\n"
        "- 是戶外體驗與攝影的最佳時機，可延長戶外停留時間"
    )

else:  # temp < 18
    st.info(
        "🥶 **偏冷天氣（< 18°C）｜保暖與行程調整建議**\n\n"
        "氣溫偏低，部分時段體感寒冷，建議注意保暖與行程選擇：\n\n"
        "🧥 **保暖建議**\n"
        "- 攜帶外套或保暖衣物，留意早晚溫差\n"
        "- 山區或海邊地區體感溫度可能更低\n\n"
        "🗺 **行程安排建議**\n"
        "- 可增加室內景點比例（博物館、展覽、咖啡廳）\n"
        "- 戶外行程建議縮短停留時間\n\n"
        "☕ **旅遊體驗建議**\n"
        "- 適合安排美食行程、溫泉或靜態文化活動"
    )

