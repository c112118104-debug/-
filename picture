graph TD
    %% 定義樣式
    classDef frontend fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef logic fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef external fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef database fill:#fff3e0,stroke:#f57c00,stroke-width:2px;

    %% 前端介面層
    subgraph 前端介面層 [🌐 一、前端介面層 Frontend Layer (Streamlit)]
        direction row
        A1(使用者認證<br>登入/註冊/密碼)
        A2(AI 規劃對話<br>旅遊偏好輸入)
        A3(手動自由配<br>自訂行程檢索)
        A4(視覺化與互動反饋<br>動態排版/地圖連結)
    end
    class 前端介面層 frontend

    %% 核心邏輯層
    subgraph 核心邏輯層 [🧠 二、核心邏輯層 Core Logic Layer]
        direction row
        B1(Google Gemini 2.0 Flash<br>自然語言與行程生成)
        B2(加權排序演算法<br>地理位置/主題過濾)
        B3(雨天避險邏輯<br>動態替換室內景點)
        B4(交通耗時估算<br>經緯度與車速換算)
        B5(穿搭建議模型<br>溫差與天氣警報)
    end
    class 核心邏輯層 logic

    %% 外部感知層
    subgraph 外部感知層 [🔗 三、外部服務與感知層 External APIs]
        direction row
        C1(Google Maps Platform<br>Places / Geocoding API)
        C2(Open-Meteo API<br>即時與預報天氣)
        C3(TDX 交通資料庫<br>大眾運輸資訊)
    end
    class 外部感知層 external

    %% 資料儲存層
    subgraph 資料儲存層 [🗄️ 四、資料儲存層 Data Storage Layer]
        direction row
        D1[(taipei_attractions2.csv<br>本地景點資料庫)]
        D2[(users_db.json<br>使用者資料庫)]
        D3[(history_db.json<br>歷史行程紀錄)]
    end
    class 資料儲存層 database

    %% 資料流向 (箭頭)
    前端介面層 <==> |1. 使用者請求參數 / 4. 回傳視覺化結果| 核心邏輯層
    核心邏輯層 <==> |2. API 請求 / 回傳環境感知數據| 外部感知層
    核心邏輯層 <==> |3. 讀寫快取、資料檢索與存檔| 資料儲存層
