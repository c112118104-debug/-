import pandas as pd
import requests
import time

# 1. 這裡貼上你的 API KEY
API_KEY = "AIzaSyDOWRKrLXXbHfY7vxsOD2gKoBSn71TL94s"   # ← 換成你自己的金鑰

URL = "https://maps.googleapis.com/maps/api/geocode/json"

# 2. 檔名：輸入檔 & 輸出檔
INPUT_FILE = "taiwan_attractions_with_images_with_district_cleaned.csv"
OUTPUT_FILE = "taiwan_attractions_with_images_district_geocoded.csv"


def get_district_from_google(addr: str):
    """給一個地址，呼叫 Google Geocoding API 回傳行政區名稱（鄉鎮市區）"""
    if not isinstance(addr, str) or addr.strip() == "":
        return None

    params = {
        "address": addr,
        "key": API_KEY,
        "language": "zh-TW",
        "region": "tw",
    }

    r = requests.get(URL, params=params)
    data = r.json()

    status = data.get("status")
    if status != "OK":
        print(f"查詢失敗：{status}，地址：{addr}")
        return None

    comps = data["results"][0]["address_components"]
    district = None

    # 嘗試從 components 裡找出「行政區」相關欄位
    for c in comps:
        types = c["types"]
        if (
            "administrative_area_level_3" in types
            or "sublocality_level_1" in types
            or "sublocality" in types
        ):
            district = c["long_name"]
            break

    return district


def main():
    # 讀取 CSV
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")
    cols_lower = {c.lower(): c for c in df.columns}
    addr_col = cols_lower.get("address", "Address")
    dist_col = cols_lower.get("district", "District")

    # 找出 District 是空的資料列
    mask = df[dist_col].isna() | (df[dist_col].astype(str).str.strip() == "")
    to_fix = df[mask]

    print(f"總筆數：{len(df)}")
    print(f"District 為空的筆數：{len(to_fix)}")

    # 先測試「最多 30 筆」，確定沒問題再跑全部
    for count, idx in enumerate(to_fix.index):
        if count >= 30:  # 想跑全部時，把這兩行刪掉
            break

        addr = df.at[idx, addr_col]
        print(f"\n處理第 {idx} 筆，地址：{addr}")
        dist = get_district_from_google(addr)
        print("→ 取得 District：", dist)

        if dist:
            df.at[idx, dist_col] = dist

        # 避免打 API 太快
        time.sleep(0.2)

    # 存檔
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n處理完成，已輸出：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
