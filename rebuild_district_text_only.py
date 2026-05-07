import pandas as pd
import re

# === 檔名設定 ===
INPUT_FILE = "taiwan_attractions_with_images_with_district.csv"
OUTPUT_FILE = "taiwan_attractions_with_images_district_text_clean.csv"
MISSING_FILE = "taiwan_attractions_with_images_district_missing_after_text_clean.csv"


def extract_district_from_address(addr: str):
    """從地址字串中解析出『某某鄉 / 鎮 / 市 / 區』(純文字，不含數字)"""
    if pd.isna(addr):
        return None

    s = str(addr).strip()
    if not s:
        return None

    # 去掉開頭的「台灣 / 臺灣」
    s = re.sub(r"^(台灣|臺灣)", "", s)

    # 去掉開頭的郵遞區號 (3~5 碼數字，包含全形數字)
    s = re.sub(r"^[0-9０-９]{3,5}", "", s)

    # 規則 1：先找「縣 / 市」後面的「XX鄉 / 鎮 / 市 / 區」
    m = re.search(r"[縣市]([^0-9縣市]{1,6}[鄉鎮市區])", s)
    if m:
        return m.group(1).strip()

    # 規則 2：整串裡面第一個以「鄉 / 鎮 / 市 / 區」結尾的中文字片段
    # 例如：大安區、鼓山區、鹿港鎮、竹東鎮……
    m = re.search(r"([^0-9]{1,6}[鄉鎮市區])", s)
    if m:
        return m.group(1).strip()

    return None


def main():
    print(f"讀取檔案：{INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    # 找欄位名稱（不分大小寫）
    cols_lower = {c.lower(): c for c in df.columns}
    addr_col = cols_lower.get("address", "Address")
    dist_col = cols_lower.get("district", "District")

    # 原本空值數量
    mask_before = df[dist_col].isna() | (df[dist_col].astype(str).str.strip() == "")
    print(f"原本 District 為空的筆數：{mask_before.sum()} / {len(df)}")

    # 從 Address 重新解析一次 District
    new_dist = df[addr_col].apply(extract_district_from_address)

    # 只填補「目前是空的」那幾筆，不動已經有值的
    df.loc[mask_before, dist_col] = new_dist[mask_before]

    # 再算一次剩下多少空值
    mask_after = df[dist_col].isna() | (df[dist_col].astype(str).str.strip() == "")
    print(f"套用文字規則後，District 仍為空的筆數：{mask_after.sum()} / {len(df)}")

    # 輸出主檔
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"已輸出整理後的檔案：{OUTPUT_FILE}")

    # 另外把仍然沒抓到 District 的資料另存一份
    df[mask_after].to_csv(MISSING_FILE, index=False, encoding="utf-8-sig")
    print(f"仍為空的資料已另外輸出：{MISSING_FILE}")


if __name__ == "__main__":
    main()
