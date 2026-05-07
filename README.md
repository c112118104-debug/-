# 🌟 智慧旅遊推薦系統 (Smart Tourism Recommendation System)

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Gemini](https://img.shields.io/badge/AI-Gemini_2.0_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)

[cite_start]這是一個基於 **Python** 與 **Streamlit** 框架開發的個人化旅遊規劃平台。本系統旨在解決現代旅遊資訊過載（Information Overload）的痛點，透過整合大型語言模型（LLM）與多源實時 API，為使用者提供精準、流暢且具備環境感知能力的行程方案 [cite: 2, 7]。

---

## 🚀 核心功能亮點

* [cite_start]**🤖 AI 智慧行程規劃**：整合 **Google Gemini 2.0 Flash** 模型進行語義分析，自動生成符合邏輯且時程連續的客製化行程 [cite: 12, 59]。
* [cite_start]**☁️ 實時天氣感知與避險**：串接 **Open-Meteo API**，系統能根據旅遊期間的降雨機率，自動觸發「雨天避險邏輯」，將戶外景點替換為室內備案 [cite: 7, 46, 59]。
* [cite_start]**📍 地理資訊視覺化**：整合 **Google Maps Platform** (Places, Geocoding)，提供即時景點評論、星級、營業時間檢查，並支援一鍵啟動導航 [cite: 2, 25, 66]。
* [cite_start]**🚌 智慧交通耗時估算**：結合 **TDX (Transport Data eXchange)** 資料，根據地理座標精確計算景點間的移動與交通時間 [cite: 7, 46, 59]。
* [cite_start]**🔐 使用者管理系統**：具備帳號註冊、登入功能，並能完整紀錄使用者的歷史行程與天氣資訊 [cite: 66]。
* [cite_start]**📊 流程圖渲染**：使用 **Graphviz** 將行程路徑轉化為視覺化流程圖，方便掌握空間動線 [cite: 46, 66]。

---

## 🛠️ 技術棧 (Tech Stack)

* [cite_start]**開發框架**：Streamlit [cite: 12]
* [cite_start]**核心語言**：Python 3.11+ [cite: 2]
* [cite_start]**AI 模型**：Google Gemini 2.0 Flash [cite: 59]
* **API 整合**：
    * [cite_start]Google Maps API (Details, Photos, Autocomplete, Geocoding) [cite: 2, 25]
    * [cite_start]Open-Meteo API (即時與預測天氣) [cite: 7, 46]
    * [cite_start]TDX (Transport Data eXchange) 交通資訊 [cite: 7, 46]
* [cite_start]**資料處理與視覺化**：Pandas, Graphviz [cite: 2, 46]

---

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
