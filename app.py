import streamlit as st
import pandas as pd
import ast
import os

# --- 1. 設定登入帳號密碼 (實際專案建議放在環境變數或資料庫) ---
ADMIN_USER = "admin"
ADMIN_PASSWORD = "1234"

# --- 2. 初始化 Session State (用來記憶登入狀態) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- 3. 定義登入頁面函式 ---
def login_page():
    st.title("🔐 使用者登入")
    
    # 建立一個置中的區塊
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        username = st.text_input("帳號")
        password = st.text_input("密碼", type="password") # type="password" 會隱藏輸入內容
        
        if st.button("登入"):
            if username == ADMIN_USER and password == ADMIN_PASSWORD:
                st.session_state['logged_in'] = True
                st.success("登入成功！正在跳轉...")
                st.rerun() # 重新執行頁面，進入主程式
            else:
                st.error("帳號或密碼錯誤")

# --- 4. 定義主程式函式 (原本的景點瀏覽器) ---
def main_app():
    # 側邊欄顯示登出按鈕
    with st.sidebar:
        st.write(f"歡迎回來，{ADMIN_USER}！")
        if st.button("登出"):
            st.session_state['logged_in'] = False
            st.rerun() # 重新執行，回到登入頁

    # === 以下是原本的景點瀏覽器程式碼 ===
    st.title("台灣景點圖片瀏覽器 📸")

    # 取得檔案路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'taiwan_attractions_distinct_classes.csv')

    try:
        df = pd.read_csv(file_path)
        
        # --- 第一層：選擇縣市 ---
        city_list = df['City'].unique().tolist()
        selected_city = st.selectbox("請選擇縣市：", city_list)
        
        # --- 第二層：選擇區/鄉/鎮 (根據縣市篩選) ---
        df_city_filtered = df[df['City'] == selected_city]
        district_list = df_city_filtered['District'].unique().tolist()
        selected_district = st.selectbox("請選擇區/鄉/鎮：", district_list)
        
        # --- 第三層：選擇景點 (根據區域篩選) ---
        df_final_filtered = df_city_filtered[df_city_filtered['District'] == selected_district]
        spot_list = df_final_filtered['ScenicSpotName'].unique().tolist()
        selected_spot = st.selectbox("請選擇景點：", spot_list)

        # 顯示對應的圖片
        if selected_spot:
            spot_data = df_final_filtered[df_final_filtered['ScenicSpotName'] == selected_spot].iloc[0]
            picture_str = spot_data['Picture']
            
            try:
                if pd.notna(picture_str) and picture_str != "{}":
                    pic_dict = ast.literal_eval(picture_str)
                    img_url = pic_dict.get('PictureUrl1')
                    img_desc = pic_dict.get('PictureDescription1', selected_spot)
                    
                    if img_url:
                        st.image(img_url, caption=img_desc, use_container_width=True)
                        st.success(f"目前顯示：{selected_city} {selected_district} - {selected_spot}")
                    else:
                        st.warning("這個景點沒有提供圖片連結。")
                else:
                    st.info("資料庫中沒有此景點的圖片資料。")
                    
            except Exception as e:
                st.error(f"解析圖片資料時發生錯誤：{e}")
                
            with st.expander("查看詳細資訊"):
                st.write(f"**地址：** {spot_data.get('Address', '無')}")
                st.write(f"**分類：** {spot_data.get('Class1', '無')} ")
                st.write(f"**介紹：** {spot_data.get('DescriptionDetail', '無介紹')}")

    except FileNotFoundError:
        st.error("找不到 CSV 檔案，請確認 'taiwan_attractions_classified.csv' 是否在同一資料夾中。")

# --- 5. 程式流程控制 ---
if not st.session_state['logged_in']:
    login_page()
else:
    main_app()