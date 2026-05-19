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
