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

# --- 1. 設定頁面配置 (必須放在最前面) ---
st.set_page_config(page_title="台灣旅遊小幫手 (AI 整合版)", page_icon="✨", layout="wide")

# --- 2. API 設定 ---
# ⚠️ 建議：真實部署時請改用 st.secrets 或環境變數
GOOGLE_API_KEY = "AIzaSyBGwFSHPMTyc-yJlPuXwDZpYqS-WlJsVQo"

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"API 設定錯誤：{e}")

# --- 設定 ---
USER_DB_FILE = 'users_db.json'
CSV_FILE_NAME = 'taiwan_attractions.csv'

# --- 3. Session State 初始化 (合併兩個檔案的需求) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'login'
if 'user_nickname' not in st.session_state:
    st.session_state['user_nickname'] = None
if 'trip_schedule' not in st.session_state:
    st.session_state['trip_schedule'] = {1: []} # 手動模式的資料
if 'trip_days' not in st.session_state:
    st.session_state['trip_days'] = 1
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
    st.session_state['input_dest'] = "臺北市"
if 'input_days' not in st.session_state:
    st.session_state['input_days'] = 3

# --- 4. CSS 樣式整合 ---
st.markdown("""
    <style>
    /* --- app2.py 的側邊欄樣式 --- */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        display: flex !important;
    }
    [data-testid="stSidebar"] [data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
    }
    [data-testid="stSidebar"] [data-testid="column"]:nth-of-type(2) {
        align-items: flex-end !important;
    }
    [data-testid="stSidebar"] [data-testid="column"]:nth-of-type(1) {
        align-items: flex-start !important;
    }
    div.stButton > button:first-child {
        min-height: 38px;
    }
    .day-header {
        font-weight: bold;
        color: #ff4b4b;
        margin-top: 15px;
        margin-bottom: 8px;
        font-size: 1.1em;
        border-bottom: 1px solid #ddd;
    }

    /* --- test.py 的美化樣式 --- */
    /* 輸入框標題 */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stMultiSelect label, .stTextArea label {
        color: #5D6D7E; font-weight: bold;
    }
    /* 行程文字區塊 */
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
    .itinerary-item strong {
        color: #333333 !important; 
    }
    .itinerary-transport {
        margin-left: 24px;
        color: #28a745 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. 共用輔助函式 (使用者資料與 CSV) ---
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

# 快取 CSV 讀取 (供 AI 與 Manual 模式共用)
@st.cache_data
def load_attractions():
    try:
        df = pd.read_csv(CSV_FILE_NAME)
        return df
    except Exception as e:
        return None

attractions_db = load_attractions()

# --- 6. test.py 的 AI 邏輯函式 ---

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
    
    # 搜尋目的地
    mask_loc = (
        attractions_db['City'].str.contains(destination, na=False) | 
        attractions_db['Address'].str.contains(destination, na=False) |
        attractions_db['ScenicSpotName'].str.contains(destination, na=False)
    )
    # 必須要有圖片
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

def generate_html_display(df):
    html_content = '<div class="itinerary-box">'
    df = df[df['Place'].notna() & (df['Place'] != "")]
    df = df.sort_values(by=["Day", "Order"])
    
    current_day = 0
    for index, row in df.iterrows():
        day_val = int(row['Day']) if pd.notna(row['Day']) else 1
        if day_val != current_day:
            current_day = day_val
            html_content += f'<div class="itinerary-day">🗓️ 第 {current_day} 天</div>'
        
        place = row['Place']
        city = row['City'] if pd.notna(row['City']) else ""
        district = row['District'] if pd.notna(row['District']) else ""
        loc_str = f"({city} {district})" if city or district else ""
        
        html_content += f'<div class="itinerary-item">📍 <strong>{place}</strong> {loc_str}</div>'
        
        if row['Transport'] and str(row['Transport']) != "None" and str(row['Transport']) != "":
            html_content += f'<div class="itinerary-transport">└─ 🚌 {row["Transport"]}</div>'
            
    html_content += '</div>'
    return html_content

def generate_plain_text(df):
    txt_content = f"【{st.session_state.get('input_dest', '行程')} 旅遊規劃表】\n"
    txt_content += "="*30 + "\n\n"
    df = df[df['Place'].notna() & (df['Place'] != "")]
    df = df.sort_values(by=["Day", "Order"])
    current_day = 0
    for index, row in df.iterrows():
        day_val = int(row['Day']) if pd.notna(row['Day']) else 1
        if day_val != current_day:
            current_day = day_val
            txt_content += f"\n[ Day {current_day} ]\n"
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
    mask = attractions_db['ScenicSpotName'].str.contains(place_name, na=False)
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

# --- 7. Auth Pages (Login/Signup/Forgot) - 保持 app2.py 原樣 ---

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
                st.info(f"【模擬郵件】您的驗證碼是：**{code}**")
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

def login_page():
    st.title("🔐 使用者登入")
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

# --- 8. 側邊欄 (修正版：加入手動模式排序功能) ---
def sidebar_component():
    with st.sidebar:
        st.header(f"👤 {st.session_state['user_nickname']}")
        
        # 導航按鈕
        if st.session_state['mode'] != 'menu':
            if st.button("🏠 回到主選單", use_container_width=True):
                st.session_state['mode'] = 'menu'
                st.session_state['ai_submitted'] = False # 重置 AI 狀態
                st.rerun()
        
        st.divider()

        # 根據模式顯示不同的側邊欄內容
        if st.session_state['mode'] == 'manual':
            st.subheader("📋 手動行程清單")
            
            # 檢查是否有行程
            has_spots = any(len(spots) > 0 for spots in st.session_state['trip_schedule'].values())
            
            if has_spots:
                for day in range(1, st.session_state['trip_days'] + 1):
                    day_spots = st.session_state['trip_schedule'].get(day, [])
                    
                    if day_spots:
                        st.markdown(f"<div class='day-header'>Day {day}</div>", unsafe_allow_html=True)
                        
                        for i, spot in enumerate(day_spots):
                            # 使用 4 個欄位：名稱(大), 上, 下, 刪除(小)
                            c1, c2, c3, c4 = st.columns([8, 3, 3, 3], vertical_alignment="center")
                            
                            with c1:
                                st.write(f"{i+1}.{spot}")
                            
                            with c2:
                                # 第一個不能上移
                                if i > 0:
                                    if st.button("⬆️", key=f"up_{day}_{i}", help="上移"):
                                        day_spots[i], day_spots[i-1] = day_spots[i-1], day_spots[i]
                                        st.rerun()
                            
                            with c3:
                                # 最後一個不能下移
                                if i < len(day_spots) - 1:
                                    if st.button("⬇️", key=f"down_{day}_{i}", help="下移"):
                                        day_spots[i], day_spots[i+1] = day_spots[i+1], day_spots[i]
                                        st.rerun()
                                        
                            with c4:
                                if st.button("🗑️", key=f"del_{day}_{i}", help="刪除"):
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
            # AI 模式：顯示輸入表單 (如果是已提交狀態，方便修改)
            if st.session_state['ai_submitted']:
                render_ai_input_form(st.sidebar)

        st.divider()
        if st.button("登出", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# --- 9. 主要頁面功能區 ---

def menu_page():
    sidebar_component()
    st.title("🌟 歡迎來到台灣旅遊小幫手")
    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        st.info("🤖 **AI 智慧排程 (全新升級)**\n\nAI 自動為您推薦、排序、計算交通，並生成視覺化流程圖。")
        if st.button("✨ 使用 AI 自動排行程", use_container_width=True, type="primary"):
            st.session_state['mode'] = 'ai_chat'
            st.rerun()
    with col2:
        st.success("🗺️ **手動自由配**\n\n自訂旅遊天數，搜尋資料庫圖片，自由加入行程。")
        if st.button("🔍 自己搜尋瀏覽景點", use_container_width=True):
            st.session_state['mode'] = 'manual'
            st.rerun()

# --- AI 排程頁面 (整合 test.py) ---
def render_ai_input_form(container):
    with container:
        if not st.session_state['ai_submitted']:
             st.markdown("### 🛫 規劃您的旅程")
        else:
             st.header("⚙️ 修改設定")
        
        # 綁定 Session State
        st.text_input("想去哪裡玩？", key="input_dest")
        st.number_input("旅遊天數", min_value=1, max_value=10, key="input_days")
        st.selectbox("預算等級", ["經濟實惠 (背包客)", "中等預算 (舒適)", "奢華享受 (豪華)"], key="input_budget")
        st.multiselect("偏好交通", ["大眾運輸", "自行開車", "計程車", "步行"], default=["大眾運輸"], key="input_trans")
        st.text_area("偏好與必去景點 (如: 台北101, 士林夜市)", key="input_mixed", height=100)
        
        st.write("")
        if st.button("✨ 開始規劃" if not st.session_state['ai_submitted'] else "🔄 重新生成", use_container_width=True):
            st.session_state['ai_submitted'] = True
            st.session_state['schedule_df'] = None # 強制重跑
            st.rerun()

def ai_planning_page():
    sidebar_component()
    
    if not st.session_state['ai_submitted']:
        # 尚未提交：顯示大畫面輸入表單
        col_c, _ = st.columns([1, 0.1])
        with col_c:
            render_ai_input_form(st.container())
    else:
        # 已提交：顯示結果
        st.title(f"🗺️ {st.session_state['input_dest']} - AI 專屬行程")

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
                        st.stop()
                    
                    if status["matched"]:
                        st.success(f"✅ **已鎖定 {len(status['matched'])} 個必去景點**")
                    
                    mandatory_instruction = ""
                    if priority_list:
                        mandatory_instruction = f"**絕對強制指令**: 必須將以下景點排入行程：{json.dumps(priority_list, ensure_ascii=False)}"
                    
                    user_preferences = ", ".join(status["unmatched"]) if status["unmatched"] else "無特殊偏好"
                    
                    prompt = f"""
                    請規劃 {st.session_state['input_dest']} 的 {st.session_state['input_days']} 天行程。
                    預算：{st.session_state['input_budget']}。
                    **使用者偏好/風格**：{user_preferences}。
                    交通方式：{','.join(st.session_state['input_trans'])}。
                    {mandatory_instruction}
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
                    st.session_state['schedule_df'] = pd.DataFrame(data)
                    
                except Exception as e:
                    st.error(f"規劃失敗：{e}")
                    st.stop()

        # [Step B] 顯示結果介面
        if st.session_state['schedule_df'] is not None:
            
            # Tab 1: 編輯與列表
            tab1, tab2, tab3 = st.tabs(["✏️ 行程編輯", "📸 圖文詳情", "📊 流程圖"])
            
            with tab1:
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
                # 更新 State
                if not edited_df.equals(st.session_state['schedule_df']):
                     st.session_state['schedule_df'] = edited_df.sort_values(by=["Day", "Order"]).reset_index(drop=True)
                     st.rerun()
                
                # 文字行程預覽與下載
                st.markdown("---")
                html_content = generate_html_display(edited_df)
                st.markdown(html_content, unsafe_allow_html=True)
                
                txt_content = generate_plain_text(edited_df)
                st.download_button("📥 下載文字檔 (.txt)", txt_content, f"{st.session_state['input_dest']}_行程.txt")

            with tab2:
                place_options = edited_df['Place'].unique().tolist()
                selected_place = st.selectbox("查看詳情：", place_options)
                if selected_place:
                    display_attraction_details(selected_place)

            with tab3:
                dot_code = generate_dot_from_df(edited_df)
                if dot_code:
                    st.graphviz_chart(dot_code, use_container_width=True)
                    st.download_button("📥 下載 DOT 檔", dot_code, f"{st.session_state['input_dest']}.dot")

# --- 手動模式頁面 (保留 app2.py 邏輯) ---
def manual_page():
    sidebar_component()
    st.title("📸 台灣景點圖片瀏覽器 (手動模式)")

    col_days, col_info = st.columns([1, 2])
    with col_days:
        days_input = st.number_input("📅 設定旅遊天數", min_value=1, max_value=30, value=st.session_state['trip_days'])
        if days_input != st.session_state['trip_days']:
            st.session_state['trip_days'] = days_input
            for d in range(1, days_input + 1):
                if d not in st.session_state['trip_schedule']:
                    st.session_state['trip_schedule'][d] = []
            st.rerun()
    with col_info:
        st.info(f"目前規劃： **{st.session_state['trip_days']} 天**。")
    
    st.markdown("---")
    
    # 使用快取的 CSV 資料
    df = attractions_db
    if df is not None:
        search_keyword = st.text_input("🔍 搜尋關鍵字：")
        if search_keyword:
            df = df[df['ScenicSpotName'].str.contains(search_keyword, case=False, na=False)]

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
            
            # 加入手動清單邏輯
            col_add_day, col_add_btn = st.columns([1, 2])
            with col_add_day:
                target_day = st.selectbox("加入哪一天？", range(1, st.session_state['trip_days'] + 1))
            with col_add_btn:
                if st.button(f"➕ 加入第 {target_day} 天"):
                    if target_day not in st.session_state['trip_schedule']:
                        st.session_state['trip_schedule'][target_day] = []
                    st.session_state['trip_schedule'][target_day].append(selected_spot)
                    st.toast("已加入！")
                    st.rerun()
    else:
        st.error("找不到 CSV 資料檔。")

# --- 10. 路由控制 ---
def logged_in_interface():
    if st.session_state['mode'] == 'menu':
        menu_page()
    elif st.session_state['mode'] == 'ai_chat':
        ai_planning_page() # 替換成新的 AI 頁面
    elif st.session_state['mode'] == 'manual':
        manual_page()

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