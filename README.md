# 🌟 智慧旅遊推薦系統 (Smart Tourism Recommendation System)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Gemini](https://img.shields.io/badge/AI-Gemini_2.0_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)

這是一個基於 **Python** 與 **Streamlit** 框架開發的個人化旅遊規劃平台。本系統旨在解決現代旅遊資訊過載（Information Overload）的痛點，透過整合大型語言模型（LLM）與多源實時 API，為使用者提供精準、流暢且具備環境感知能力的行程方案 。

---

## 🚀 核心功能亮點

* **🤖 AI 智慧行程規劃**：整合 **Google Gemini 2.0 Flash** 模型進行語義分析，自動生成符合邏輯且時程連續的客製化行程 。
* **☁️ 實時天氣感知與避險**：串接 **Open-Meteo API**，系統能根據旅遊期間的降雨機率，自動觸發「雨天避險邏輯」，將戶外景點替換為室內備案 。
* **📍 地理資訊視覺化**：整合 **Google Maps Platform** (Places, Geocoding)，提供即時景點評論、星級、營業時間檢查，並支援一鍵啟動導航。
* **🚌 智慧交通耗時估算**：結合 **TDX (Transport Data eXchange)** 資料，根據地理座標精確計算景點間的移動與交通時間。
* **🔐 使用者管理系統**：具備帳號註冊、登入功能，並能完整紀錄使用者的歷史行程與天氣資訊 。
* **📊 流程圖渲染**：使用 **Graphviz** 將行程路徑轉化為視覺化流程圖，方便掌握空間動線 。

---

## 🛠️ 技術棧 (Tech Stack)

* **開發框架**：Streamlit 
* **核心語言**：Python 3.11+ 
* **AI 模型**：Google Gemini 2.0 Flash
* **API 整合**：
    * Google Maps API (Details, Photos, Autocomplete, Geocoding) 
    * Open-Meteo API (即時與預測天氣) 
    * TDX (Transport Data eXchange) 交通資訊 
* **資料處理與視覺化**：Pandas, Graphviz 

---
## 📐系統架構圖

```mermaid
%%{init: {'theme': 'default', 'themeVariables': {'darkMode': false, 'lineColor': '#555555', 'edgeLabelBackground': '#ffffff'}}}%%
flowchart LR
    %% --- 巨型背景畫布：強制填滿淺灰色底色 ---
    subgraph Canvas [" "]
        direction LR

        %% --- 第一區塊：前端 ---
        subgraph L1 ["🌐 一、前端介面層 Frontend Layer"]
            direction LR
            A1("使用者認證<br>登入/註冊/密碼")
            A2("AI 規劃對話<br>旅遊偏好輸入")
            A3("手動自由配<br>自訂行程檢索")
            A4("視覺化與互動反饋<br>動態排版/地圖連結")
        end

        %% --- 右側隱形容器 ---
        subgraph RightSide [" "]
            direction TB
            
            subgraph L2 ["🧠 二、核心邏輯層 Core Logic Layer"]
                direction LR
                B1("Google Gemini 2.0<br>自然語言與行程生成")
                B2("加權排序演算法<br>地理位置/主題過濾")
                B3("雨天避險邏輯<br>動態替換室內景點")
                B4("交通耗時估算<br>經緯度與車速換算")
                B5("穿搭建議模型<br>溫差與天氣警報")
            end

            subgraph L3 ["🔗 三、外部感知層 External APIs"]
                direction LR
                C1("Google Maps Platform<br>Places/Geocoding API")
                C2("Open-Meteo API<br>即時與預報天氣")
                C3("TDX 交通資料庫<br>大眾運輸資訊")
            end

            subgraph L4 ["🗄️ 四、資料儲存層 Data Storage"]
                direction LR
                D1[("taipei_attractions2.csv<br>本地景點資料庫")]
                D2[("users_db.json<br>使用者資料庫")]
                D3[("history_db.json<br>歷史行程紀錄")]
            end
            
            L2 <==>|"2. API 請求 / 回傳感知數據"| L3
            L2 <==>|"3. 讀寫快取與存檔"| L4
        end

        L1 <==>|"1. 請求參數 / 4. 視覺化結果"| L2
    end

    %% 直接綁定樣式，避開 class 解析錯誤
    style L1 fill:#ffffff,stroke:#0288d1,stroke-width:2px,color:#333333;
    style L2 fill:#ffffff,stroke:#7b1fa2,stroke-width:2px,color:#333333;
    style L3 fill:#ffffff,stroke:#388e3c,stroke-width:2px,color:#333333;
    style L4 fill:#ffffff,stroke:#f57c00,stroke-width:2px,color:#333333;
    style RightSide fill:none,stroke:none;
    style Canvas fill:#f4f5f7,stroke:none;
```
---
## 🎬 系統操作 Demo

[![智慧旅遊推薦系統 Demo](https://img.youtube.com/vi/RH8X2HhWbgo/maxresdefault.jpg)](https://www.youtube.com/watch?v=RH8X2HhWbgo&t=1s)

> 💡 **點擊上方圖片即可觀看完整的系統操作與功能展示影片。**
---
## ⚙️ 本地端快速啟動指南

為了確保系統的完整功能（AI 規劃與地圖資訊），您需要自備 Google Gemini 與 Google Maps 的 API 金鑰。
#### 請打開終端機（Terminal），跟著以下步驟一氣呵成完成設定：

### 1. 完整安裝指令
#### 請在終端機依序輸入以下指令，完成專案下載與環境建置：
```bash
# 下載專案並進入資料夾
git clone [https://github.com/您的GitHub帳號/您的專案名稱.git](https://github.com/您的GitHub帳號/您的專案名稱.git)
cd 您的專案資料夾名稱

# 安裝環境依賴套件
pip install -r requirements.txt

# 建立金鑰存放的隱藏資料夾
mkdir .streamlit
```
---
### 2. 🔑 填寫 API 金鑰
#### 資料夾建立後，請在 .streamlit 資料夾內手動新增一個名為 secrets.toml 的檔案，並填入您的金鑰
```bash
GOOGLE_API_KEY = "您的_Gemini_API_Key"
GOOGLE_MAPS_API_KEY = "您的_Google_Maps_API_Key"
```
---
### 3. 🚀 啟動系統
#### 金鑰存檔後，回到終端機輸入以下指令啟動網站：
```bash
streamlit run taipei.py
```

## 📂 專案結構

```text
.
├── .streamlit/
│   └── secrets.toml           # (本地端) API 金鑰設定檔，務必加入 .gitignore
├── taipei.py                   # 系統主程式
├── requirements.txt            # 環境依賴套件清單
├── taipei_attractions2.csv     # 基礎景點資料庫 (包含描述、分類與座標)
├── users_db.json               # 使用者帳號資料 (系統自動生成)
├── history_db.json             # 旅遊歷史紀錄資料 (系統自動生成)
└── README.md                   # 專案說明文件
```
---

## ✍️ 開發者資訊 (Developer)


---
感謝您的閱讀！如果您對本專案有任何建議或合作意願，歡迎隨時聯繫。
