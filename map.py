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

# --- 1. 設定頁面配置 (必須放在最前面) ---
st.set_page_config(page_title="台灣旅遊小幫手 (AI 對話版)", page_icon="✨", layout="wide")

# --- 2. API 設定 ---
# ⚠️ 請將此處換成您真實有效的 Google Gemini API Key
GOOGLE_API_KEY = "AIzaSyBGwFSHPMTyc-yJlPuXwDZpYqS-WlJsVQo"

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    # 用於產生 JSON 格式行程的模型
    model = genai.GenerativeModel('gemini-2.0-flash', generation_config={"response_mime_type": "application/json"})
    # 用於一般對話的模型
    chat_model = genai.GenerativeModel('gemini-2.0-flash') 
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
if 'input_budget' not in st.session_state:
    st.session_state['input_budget'] = "中等預算 (舒適)"
if 'input_mixed' not in st.session_state:
    st.session_state['input_mixed'] = ""

# 對話紀錄
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [
        {"role": "assistant", "content": "你好！我是你的 AI 旅遊顧問。告訴我你想去哪裡？預計什麼時候出發？想怎麼玩？"}
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
    if email in users and users[email]["password"] == password:
        return users[email]["nickname"]
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

def save_history_record(email, trip_name, days, schedule_data, mode_type, start_date_str=None):
    history = load_history()
    new_record = {
        "id": generate_verification_code(8),
        "email": email,
        "trip_name": trip_name,
        "days": days,
        "mode": mode_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start_date": start_date_str,
        "data": schedule_data
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

# --- 6. AI 邏輯與圖表函式 ---

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
    if attractions_db is None: return [], "", {}, []
    
    destination = destination.replace("台", "臺")
    
    mask_loc = (
        attractions_db['City'].str.contains(destination, na=False) | 
        attractions_db['Address'].str.contains(destination, na=False) |
        attractions_db['ScenicSpotName'].str.contains(destination, na=False)
    )
    mask_pic = attractions_db['Picture'].str.contains('PictureUrl1', na=False)
    base_pool = attractions_db[mask_loc & mask_pic]
    
    if base_pool.empty: return [], "", {"error": "no_data"}, []

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

def generate_html_display(df, start_date=None):
    html_content = '<div class="itinerary-box">'
    df = df[df['Place'].notna() & (df['Place'] != "")]
    df = df.sort_values(by=["Day", "Order"])
    
    current_day = 0
    for index, row in df.iterrows():
        day_val = int(row['Day']) if pd.notna(row['Day']) else 1
        if day_val != current_day:
            current_day = day_val
            date_info = ""
            if start_date:
                curr_date = start_date + timedelta(days=day_val - 1)
                date_info = f" <span style='font-size:0.8em; color:#666;'>({curr_date.strftime('%m/%d')})</span>"
            html_content += f'<div class="itinerary-day">🗓️ 第 {current_day} 天{date_info}</div>'
        
        place = row['Place']
        city = row['City'] if pd.notna(row['City']) else ""
        district = row['District'] if pd.notna(row['District']) else ""
        loc_str = f"({city} {district})" if city or district else ""
        
        html_content += f'<div class="itinerary-item">📍 <strong>{place}</strong> {loc_str}</div>'
        
        if row['Transport'] and str(row['Transport']) != "None" and str(row['Transport']) != "":
            html_content += f'<div class="itinerary-transport">└─ 🚌 {row["Transport"]}</div>'
            
    html_content += '</div>'
    return html_content

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
            txt_content += f"   └── 🚌 交通：{row['Transport']}\n"
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

# --- 7. Auth Pages (Login/Signup/Forgot) ---
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
                if nickname:
                    st.session_state['logged_in'] = True
                    st.session_state['user_nickname'] = nickname
                    st.session_state['user_email'] = email
                    st.session_state['mode'] = 'menu'
                    st.success(f"歡迎，{nickname}！")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("登入失敗")
        col_forgot, col_signup = st.columns([1.5, 1])
        with col_forgot:
            if st.button("🤔 忘記密碼？"):
                st.session_state['current_page'] = 'forgot_password'
                st.rerun()
        if st.button("👉 前往註冊", use_container_width=True):
            st.session_state['current_page'] = 'signup'
            st.rerun()

# --- 8. 側邊欄 (包含手動排序與 AI 輸入) ---
def sidebar_component():
    with st.sidebar:
        st.header(f"👤 {st.session_state['user_nickname']}")
        
        if st.session_state['mode'] != 'menu':
            if st.button("🏠 回到主選單", use_container_width=True):
                st.session_state['mode'] = 'menu'
                st.session_state['ai_submitted'] = False
                st.rerun()
        
        if st.session_state['mode'] != 'history':
             if st.button("📜 我的歷史紀錄", use_container_width=True):
                st.session_state['mode'] = 'history'
                st.rerun()

        st.divider()

        # AI 模式：行程確定後，側邊欄顯示可編輯的參數
        if st.session_state['mode'] == 'ai_chat' and st.session_state['ai_submitted']:
            st.markdown("### 🛠️ 調整行程參數")
            st.caption("AI 思考完畢，您可以在此微調：")
            
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
            
            # 交通
            new_trans = st.multiselect(
                "交通方式", 
                ["大眾運輸", "自行開車", "計程車", "步行"], 
                default=st.session_state['input_trans']
            )
            st.session_state['input_trans'] = new_trans
            
            # 想去的地方 (Preferences)
            new_mixed = st.text_area("想去的景點 (選填)", value=st.session_state['input_mixed'])
            st.session_state['input_mixed'] = new_mixed

            st.write("")
            if st.button("🔄 重新生成行程", type="primary", use_container_width=True):
                st.session_state['schedule_df'] = None # 清空舊資料
                st.rerun()

        elif st.session_state['mode'] == 'manual':
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
                if st.button("🗑️ 清空所有行程", type="primary"):
                    st.session_state['trip_schedule'] = {d: [] for d in range(1, st.session_state['trip_days'] + 1)}
                    st.rerun()
            else:
                st.info("手動清單是空的。")

        st.divider()
        if st.button("登出", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# --- 9. 主要頁面功能區 ---

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

# --- AI 對話與排程頁面 (核心修改區) ---
def ai_planning_page():
    sidebar_component()
    
    # 狀態 1: 對話與參數收集階段 (尚未生成最終行程)
    if not st.session_state['ai_submitted']:
        st.title("💬 AI 旅遊顧問")
        st.caption("請告訴我你想去哪裡？幾個人？想玩幾天？喜歡什麼類型的景點？")

        # 顯示對話歷史
        for msg in st.session_state['chat_history']:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 使用者輸入
        if prompt := st.chat_input("例如：我想去台南玩三天，下週五出發，想吃小吃"):
            # 1. 顯示使用者訊息
            st.session_state['chat_history'].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # 2. AI 思考與參數提取 (幕後執行)
            with st.spinner("AI 正在分析您的需求..."):
                # 呼叫提取函式
                full_text = "\n".join([m['content'] for m in st.session_state['chat_history']])
                extracted = extract_trip_info(full_text)
                
                # 更新 Session State
                if extracted:
                    if extracted.get("destination"): 
                        st.session_state['input_dest'] = extracted["destination"]
                    
                    if extracted.get("start_date"):
                        try:
                            st.session_state['ai_start_date'] = datetime.strptime(extracted["start_date"], "%Y-%m-%d").date()
                        except: 
                            pass
                            
                    if extracted.get("end_date"):
                        try:
                            st.session_state['ai_end_date'] = datetime.strptime(extracted["end_date"], "%Y-%m-%d").date()
                        except: 
                            pass
                    
                    if extracted.get("days"): 
                        st.session_state['input_days'] = int(extracted["days"])
                    
                    # 若有 end_date, 自動更新 days
                    if extracted.get("end_date") and extracted.get("start_date"):
                         try:
                             st.session_state['input_days'] = (st.session_state['ai_end_date'] - st.session_state['ai_start_date']).days + 1
                         except: pass
                    elif extracted.get("days") and extracted.get("start_date"):
                         st.session_state['ai_end_date'] = st.session_state['ai_start_date'] + timedelta(days=st.session_state['input_days']-1)
                    
                    if extracted.get("transport"): 
                        st.session_state['input_trans'] = extracted["transport"]
                    if extracted.get("preferences"): 
                        st.session_state['input_mixed'] = extracted["preferences"]

                # 3. AI 回覆 (Chat Model)
                ai_reply_prompt = f"""
                你是親切的台灣旅遊專家。
                目前已知的資訊：
                - 地點: {st.session_state['input_dest']}
                - 日期: {st.session_state['ai_start_date']} 到 {st.session_state['ai_end_date']} (共 {st.session_state['input_days']} 天)
                - 交通: {st.session_state['input_trans']}
                
                使用者剛說：{prompt}
                
                請簡短回應使用者。如果資訊足夠，請引導使用者按下「開始生成行程」按鈕。
                如果資訊不足（例如不知道地點或天數），請禮貌詢問。
                """
                response = chat_model.generate_content(ai_reply_prompt)
                ai_msg = response.text
                
                st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                with st.chat_message("assistant"):
                    st.markdown(ai_msg)
                
                st.rerun()

        # 顯示目前偵測到的參數狀態 (讓使用者知道 AI 聽懂了沒)
        st.markdown("---")
        col_info, col_btn = st.columns([3, 1], vertical_alignment="center")
        with col_info:
            info_str = f"📍 **{st.session_state['input_dest']}** | 📅 **{st.session_state['ai_start_date']}** 出發 | ⏱️ **{st.session_state['input_days']}** 天"
            st.info(f"目前設定： {info_str}")
        with col_btn:
            if st.button("🚀 開始生成行程", type="primary", use_container_width=True):
                st.session_state['ai_submitted'] = True
                st.rerun()

    # 狀態 2: 行程生成與展示階段
    else:
        # 此時參數已經移到 Sidebar 顯示與修改 (由 sidebar_component 處理)
        start_d = st.session_state.get('ai_start_date', date.today())
        
        st.title(f"🗺️ {st.session_state['input_dest']} - AI 專屬行程")
        st.caption(f"📅 出發日期：{start_d.strftime('%Y-%m-%d')} (共 {st.session_state['input_days']} 天)")

        # [Step A] 執行 AI 規劃邏輯
        if st.session_state['schedule_df'] is None:
            with st.spinner('🔍 AI 正在智慧分析需求、查詢資料庫並規劃路線...'):
                try:
                    priority_list, context_str, status = get_attraction_data(
                        st.session_state['input_dest'], 
                        st.session_state['input_mixed'] 
                    )
                    
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
                    預算：{st.session_state['input_budget']}。
                    **使用者偏好/風格**：{user_preferences}。
                    交通方式：{','.join(st.session_state['input_trans'])}。
                    {mandatory_instruction}
                    **參考景點資料庫** (請從中選擇其他景點填補空檔)：
                    {context_str}
                    請回傳 JSON List，包含每天的詳細行程：
                    - "Day": (數字)
                    - "Order": (數字)
                    - "City": (字串)
                    - "District": (字串)
                    - "Place": (字串, 必須使用資料庫中的完整名稱)
                    - "Transport": (字串, 詳細交通指引)
                    """
                    
                    response = model.generate_content(prompt)
                    data = json.loads(response.text)
                    st.session_state['schedule_df'] = pd.DataFrame(data)
                    
                except Exception as e:
                    st.error(f"規劃失敗：{e}")
                    if st.button("重試"): st.rerun()
                    st.stop()

        # [Step B] 顯示結果介面
        if st.session_state['schedule_df'] is not None:
            
            tab1, tab2, tab3 = st.tabs(["✏️ 行程編輯", "📸 圖文詳情", "📊 流程圖"])
            
            with tab1:
                st.markdown("### ✏️ 詳細行程表 ")
                # Google Maps 導航
                if st.session_state['schedule_df'] is not None and not st.session_state['schedule_df'].empty:
                    nav_df = st.session_state['schedule_df'].sort_values(by=["Day", "Order"])
                    unique_days = sorted(nav_df['Day'].unique())
                    cols = st.columns(min(len(unique_days), 4))
                    for idx, day in enumerate(unique_days):
                        day_spots = nav_df[nav_df['Day'] == day]['Place'].tolist()
                        if day_spots:
                            encoded_spots = [urllib.parse.quote(spot) for spot in day_spots]
                            google_maps_url = f"https://www.google.com/maps/dir/{'/'.join(encoded_spots)}"
                            try:
                                day_int = int(day)
                                current_date = start_d + timedelta(days=day_int-1)
                                date_label = f"{current_date.month}/{current_date.day}"
                            except:
                                date_label = f"Day {day}"
                            
                            with cols[idx % 4]:
                                st.link_button(label=f"🗺️ {date_label} 導航", url=google_maps_url, use_container_width=True)                  
                
                edited_df = st.data_editor(
                    st.session_state['schedule_df'],
                    num_rows="dynamic", use_container_width=True, hide_index=True,
                    column_config={
                        "Day": st.column_config.NumberColumn("Day", min_value=1, width="small"),
                        "Order": st.column_config.NumberColumn("序", min_value=1, width="small"),
                        "Place": st.column_config.TextColumn("景點", width="medium"),
                        "Transport": st.column_config.TextColumn("交通", width="large")
                    }
                )
                
                if not edited_df.equals(st.session_state['schedule_df']):
                     st.session_state['schedule_df'] = edited_df.sort_values(by=["Day", "Order"]).reset_index(drop=True)
                     st.rerun()
                
                st.markdown("---")
                if st.button("💾 儲存此行程", type="primary", use_container_width=True):
                    save_data = st.session_state['schedule_df'].to_dict('records')
                    save_history_record(
                        st.session_state.get('user_email'),
                        st.session_state['input_dest'],
                        st.session_state['input_days'],
                        save_data,
                        'ai',
                        start_date_str=start_d.strftime("%Y-%m-%d")
                    )
                    st.toast("✅ 行程已儲存成功！")

                html_content = generate_html_display(edited_df, start_date=start_d)
                st.markdown(html_content, unsafe_allow_html=True)
                
                txt_content = generate_plain_text(edited_df, start_date=start_d)
                st.download_button("📥 下載文字檔", txt_content, f"{st.session_state['input_dest']}_行程.txt")

            with tab2:
                place_options = edited_df['Place'].unique().tolist()
                selected_place = st.selectbox("查看詳情：", place_options)
                if selected_place:
                    display_attraction_details(selected_place)

            with tab3:
                dot_code = generate_dot_from_df(edited_df)
                if dot_code:
                    st.graphviz_chart(dot_code, use_container_width=True)

# --- 歷史紀錄頁面 (維持不變) ---
def history_page():
    sidebar_component()
    st.title("📜 我的旅遊歷史紀錄")
    all_history = load_history()
    user_email = st.session_state.get('user_email') 
    if not user_email:
        st.error("請重新登入。")
        return
    my_records = [r for r in all_history if r['email'] == user_email]
    if not my_records:
        st.info("目前沒有歷史紀錄。")
    else:
        my_records = sorted(my_records, key=lambda x: x['timestamp'], reverse=True)
        for record in my_records:
            trip_name = record.get('trip_name', '') or "(未命名)"
            expander_title = f"📂 {trip_name} 　🕒 {record['timestamp'][:10]}"
            with st.expander(expander_title):
                st.caption("✏️ 編輯行程名稱")
                c1, c2 = st.columns([3, 1])
                new_name = c1.text_input("名稱", value=trip_name, key=f"n_{record['id']}", label_visibility="collapsed")
                if c2.button("確認", key=f"b_{record['id']}"):
                    update_history_name_in_db(record['id'], new_name)
                    st.rerun()
                st.divider()
                st.json(record['data']) 
                if st.button("🗑️ 刪除", key=f"del_{record['id']}"):
                    delete_history_record(record['id'])
                    st.rerun()

# --- 手動模式頁面 (維持不變) ---
def manual_page():
    sidebar_component()
    st.title("📸 台灣景點圖片瀏覽器 (手動模式)")
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
                for d in range(1, new_days + 1):
                    if d not in st.session_state['trip_schedule']:
                        st.session_state['trip_schedule'][d] = []
                st.rerun()  
    with col_info:
        st.info(f"目前規劃： **{st.session_state['trip_days']} 天**")
    
    st.markdown("---")
    df = attractions_db
    if df is not None:
        search_keyword = st.text_input("🔍 搜尋關鍵字：")
        if search_keyword:
            search_keyword = search_keyword.replace("台", "臺")
            df = df[df['ScenicSpotName'].str.contains(search_keyword, case=False, na=False, regex=False)]
        city_list = df['City'].unique().tolist()
        selected_city = st.selectbox("縣市：", city_list)
        df_city = df[df['City'] == selected_city]
        district_list = df_city['District'].unique().tolist()
        selected_district = st.selectbox("地區：", district_list)
        df_final = df_city[df_city['District'] == selected_district]
        spot_list = df_final['ScenicSpotName'].unique().tolist()
        selected_spot = st.selectbox("景點：", spot_list)

        if selected_spot:
            display_attraction_details(selected_spot)
            col_add_day, col_add_btn = st.columns([1, 2])
            with col_add_day:
                day_options = {}
                for d in range(1, st.session_state['trip_days'] + 1):
                    curr = st.session_state['trip_start_date'] + timedelta(days=d-1)
                    day_options[d] = f"Day {d} ({curr.strftime('%m/%d')})"
                target_day = st.selectbox("加入哪一天？", options=day_options.keys(), format_func=lambda x: day_options[x])
            with col_add_btn:
                if st.button(f"➕ 加入行程"):
                    if target_day not in st.session_state['trip_schedule']:
                        st.session_state['trip_schedule'][target_day] = []
                    st.session_state['trip_schedule'][target_day].append(selected_spot)
                    st.toast("已加入！")
                    st.rerun()
    st.markdown("---")
    if any(st.session_state['trip_schedule'].values()):
        if st.button("💾 儲存手動行程", type="primary"):
             save_history_record(
                st.session_state.get('user_email'),
                f"手動規劃-{datetime.now().strftime('%m%d')}",
                st.session_state['trip_days'],
                st.session_state['trip_schedule'],
                'manual',
                start_date_str=st.session_state['trip_start_date'].strftime("%Y-%m-%d")
            )
             st.toast("✅ 已儲存！")

# --- 10. 路由控制 ---
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