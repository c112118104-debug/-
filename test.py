import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import ast
import graphviz 

# --- 1. 設定頁面配置 ---
st.set_page_config(page_title="AI 旅遊行程規劃師 (最終完成版)", page_icon="✨", layout="wide")

# --- 2. CSS 樣式注入 ---
st.markdown("""
<style>
    /* 輸入框標題樣式 */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stMultiSelect label, .stTextArea label {
        color: #5D6D7E; font-weight: bold;
    }
    
    /* 按鈕樣式 */
    .stButton button { width: 100%; border-radius: 20px; font-weight: bold; }
    
    /* 行程文字區塊樣式 (統一化) */
    .itinerary-box {
        font-family: "Microsoft JhengHei", sans-serif;
        line-height: 1.8;
        background-color: #FAFAFA;
        padding: 25px;
        border-radius: 10px;
        border: 1px solid #EEEEEE;
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
    
    /* 統一景點與交通的文字樣式 */
    .itinerary-item, .itinerary-transport {
        font-size: 15px !important;  /* 統一大小 */
        color: #555555 !important;   /* 統一顏色 (深灰) */
        margin-bottom: 8px;
    }
    
    /* 讓景點名稱稍微粗體，區分層次 */
    .itinerary-item strong {
        color: #333333 !important; 
    }

    .itinerary-transport {
        margin-left: 24px; /* 縮排表示層級 */
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 設定 API ---
# ⚠️ 警告：真實發布時請務必使用 secrets.toml
GOOGLE_API_KEY = "AIzaSyBGwFSHPMTyc-yJlPuXwDZpYqS-WlJsVQo"

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"API 設定錯誤：{e}")

# --- 4. 初始化 Session State ---
if 'submitted' not in st.session_state:
    st.session_state['submitted'] = False
if 'schedule_df' not in st.session_state:
    st.session_state['schedule_df'] = None

# --- 5. 讀取並處理景點資料庫 ---
@st.cache_data
def load_attractions():
    try:
        df = pd.read_csv("taiwan_attractions.csv")
        return df
    except Exception as e:
        return None

attractions_db = load_attractions()

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
        
    if not priority_rows.empty:
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

# --- 6. 生成用於顯示的 HTML (統一格式) ---
def generate_html_display(df):
    html_content = '<div class="itinerary-box">'
    df = df[df['Place'].notna() & (df['Place'] != "")]
    df = df.sort_values(by=["Day", "Order"])
    
    current_day = 0
    for index, row in df.iterrows():
        day_val = int(row['Day']) if pd.notna(row['Day']) else 1
        if day_val != current_day:
            current_day = day_val
            html_content += f'<div class="itinerary-day">📅 Day {current_day}</div>'
        
        place = row['Place']
        city = row['City'] if pd.notna(row['City']) else ""
        district = row['District'] if pd.notna(row['District']) else ""
        loc_str = f"({city} {district})" if city or district else ""
        
        html_content += f'<div class="itinerary-item">📍 <strong>{place}</strong> {loc_str}</div>'
        
        if row['Transport'] and str(row['Transport']) != "None" and str(row['Transport']) != "":
            html_content += f'<div class="itinerary-transport">└─ 🚌 {row["Transport"]}</div>'
            
    html_content += '</div>'
    return html_content

# --- 7. 生成純文字 (.txt) ---
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

# --- 8. Graphviz DOT ---
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

# --- 9. 顯示景點詳細資訊 ---
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

# --- 10. 輸入介面 ---
def render_input_form(container):
    with container:
        # 首頁維持置中
        left_co, cent_co, last_co = st.columns([1, 2, 1])
        
        with cent_co:
            if not st.session_state['submitted']:
                st.markdown("<h1 style='text-align: center;'>🛫 開始規劃您的旅程</h1>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray;'>AI 驅動・智慧校正・圖文並茂</p>", unsafe_allow_html=True)
                st.markdown("---")
            else:
                st.header("⚙️ 修改行程設定")
            
            destination = st.text_input("想去哪裡玩？", value="臺北市", key="input_dest")
            days = st.number_input("旅遊天數", min_value=1, max_value=10, value=3, key="input_days")
            budget = st.selectbox("預算等級", ["經濟實惠 (背包客)", "中等預算 (舒適)", "奢華享受 (豪華)"], key="input_budget")
            
            transportation = st.multiselect(
                "偏好交通方式",
                ["大眾運輸", "自行開車", "計程車", "步行"],
                default=["大眾運輸"],
                key="input_trans"
            )
            companions = st.multiselect("旅伴類型", ["獨旅", "情侶", "家庭", "朋友"], default=["獨旅"], key="input_comp")
            
            st.markdown("👇 **行程偏好與必去景點** (系統會自動校正「夜市」名稱)")
            user_input = st.text_area(
                "輸入範例：喜歡大自然, 必去台北101, 士林夜市", 
                value="喜歡拍照, 台北101, 士林夜市, 想要輕鬆一點", 
                key="input_mixed",
                height=100
            )
            
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("✨ 開始規劃" if not st.session_state['submitted'] else "🔄 重新生成", use_container_width=True):
                st.session_state['submitted'] = True
                st.session_state['schedule_df'] = None 
                st.rerun()

# --- 11. 主程式邏輯 ---
if not st.session_state['submitted']:
    # 移除 toast
    render_input_form(st.container())

else:
    with st.sidebar:
        render_input_form(st.sidebar)
    
    st.title(f"🗺️ {st.session_state['input_dest']} - 專屬行程表")

    # [Step A] 規劃
    if st.session_state['schedule_df'] is None:
        with st.spinner('🔍 AI 正在智慧分析您的需求並規劃路線...'):
            try:
                priority_list, context_str, status = get_attraction_data(
                    st.session_state['input_dest'], 
                    st.session_state['input_mixed'] 
                )
                
                if status.get("error") == "no_data":
                    st.error(f"❌ 找不到任何有圖片的景點資料。")
                    st.stop()
                
                if status["matched"]:
                    st.success(f"✅ **系統已鎖定 {len(status['matched'])} 個必去景點 ：**\n" + 
                               ", ".join([f"「{k}」➜ {v}" for k, v in status["matched"].items()]))
                
                mandatory_instruction = ""
                if priority_list:
                    mandatory_instruction = f"""
                    **🔴 絕對強制指令**: 必須將以下景點排入行程：{json.dumps(priority_list, ensure_ascii=False)}
                    """
                
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

    # [Step B] 顯示
    if st.session_state['schedule_df'] is not None:
        
        st.subheader("✏️ 1. 行程管理表格")
        
        edited_df = st.data_editor(
            st.session_state['schedule_df'],
            num_rows="dynamic", 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Day": st.column_config.NumberColumn("Day", min_value=1, width="small"),
                "Order": st.column_config.NumberColumn("序", min_value=1, width="small"),
                "City": st.column_config.TextColumn("縣市", width="small"),
                "District": st.column_config.TextColumn("行政區", width="small"),
                "Place": st.column_config.TextColumn("景點名稱", required=True, width="medium"),
                "Transport": st.column_config.TextColumn("詳細交通指引", width="large")
            },
            key="editor"
        )
        try:
            if not edited_df.equals(st.session_state['schedule_df']):
                 st.session_state['schedule_df'] = edited_df.sort_values(by=["Day", "Order"]).reset_index(drop=True)
                 st.rerun()
        except: pass
        
        col_empty, col_btn = st.columns([3, 1])
        with col_btn:
            if st.button("🚗 重新計算交通", type="primary", use_container_width=True):
                with st.spinner("AI 正在查詢公車與捷運路線..."):
                     current_json = edited_df.to_json(orient="records", force_ascii=False)
                     re_prompt = f"""
                     行程 JSON：{current_json}
                     任務：保留其他欄位，只更新 "Transport" 欄位。
                     交通工具：{','.join(st.session_state['input_trans'])}。
                     要求：詳細交通指引。
                     回傳 JSON List。
                     """
                     try:
                         resp = model.generate_content(re_prompt)
                         st.session_state['schedule_df'] = pd.DataFrame(json.loads(resp.text))
                         st.success("更新完成！")
                         st.rerun()
                     except: st.error("計算失敗")

        st.markdown("---")

        st.subheader("📸 2. 景點詳細圖文介紹")
        
        if not edited_df.empty:
            place_options = edited_df['Place'].unique().tolist()
            selected_place = st.selectbox("👇 請選擇您想查看詳情的景點：", place_options)
            st.markdown("---")
            if selected_place:
                display_attraction_details(selected_place)
        else:
            st.info("請先規劃行程。")

        st.markdown("---")
        
        st.subheader("📄 3. 文字行程")
        
        html_content = generate_html_display(edited_df)
        with st.expander("點擊展開/收合詳細文字行程", expanded=True):
             st.markdown(html_content, unsafe_allow_html=True)
        
        txt_content = generate_plain_text(edited_df)
        col_empty_dl, col_dl = st.columns([3, 1])
        with col_dl:
            st.download_button(
                label="📥 下載行程文字檔 (.txt)",
                data=txt_content,
                file_name=f"{st.session_state['input_dest']}_行程.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        st.markdown("---")

        st.subheader("📊 4. 流程圖")
        
        dot_code = generate_dot_from_df(edited_df)
        if dot_code:
            st.graphviz_chart(dot_code, use_container_width=True)
            
            col_empty_dot, col_dot = st.columns([3, 1])
            with col_dot:
                jpg_data = None
                try:
                    graph = graphviz.Source(dot_code)                    
                    st.download_button(
                        label="📥 下載流程圖原始檔 (.dot)",
                        data=dot_code,
                        file_name=f"{st.session_state['input_dest']}_流程圖.dot",
                        mime="text/plain",
                        use_container_width=True
                    )
                except Exception as e:
                    st.download_button(
                        label="📥 下載流程圖原始檔 (.dot)",
                        data=dot_code,
                        file_name=f"{st.session_state['input_dest']}_流程圖.dot",
                        mime="text/plain",
                        use_container_width=True
                    )