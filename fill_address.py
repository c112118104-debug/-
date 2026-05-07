import pandas as pd
import googlemaps
import ast
import time
import os  # 新增這個模組

# ================= 設定區 =================
API_KEY = 'AIzaSyDOWRKrLXXbHfY7vxsOD2gKoBSn71TL94s'  # ★★★ 請記得填回您的 Key ★★★
INPUT_FILE = 'taiwan_attractions.csv'
OUTPUT_FILE = 'taiwan_attractions_with_address.csv'
# =========================================

def get_address_from_latlon(gmaps_client, lat, lon):
    try:
        results = gmaps_client.reverse_geocode((lat, lon), language='zh-TW')
        if results:
            return results[0].get('formatted_address', '')
        else:
            return None
    except Exception as e:
        print(f"API 呼叫錯誤: {e}")
        return None

def main():
    # ★★★ 關鍵修改開始 ★★★
    # 取得目前這個 python 程式檔案所在的資料夾路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 組合出檔案的絕對路徑
    input_path = os.path.join(script_dir, INPUT_FILE)
    output_path = os.path.join(script_dir, OUTPUT_FILE)
    
    print(f"程式所在資料夾: {script_dir}")
    print(f"預計讀取檔案路徑: {input_path}")
    # ★★★ 關鍵修改結束 ★★★

    try:
        gmaps = googlemaps.Client(key=API_KEY)
    except ValueError:
        print("錯誤: 請檢查您是否已填入正確的 API Key。")
        return

    try:
        # 這裡改用 input_path (絕對路徑) 來讀取
        df = pd.read_csv(input_path)
        print(f"成功讀取檔案，共 {len(df)} 筆資料")
    except FileNotFoundError:
        print(f"錯誤: 依然找不到檔案。")
        print(f"請確認 '{INPUT_FILE}' 是否真的在 '{script_dir}' 這個資料夾裡面。")
        return

    missing_mask = df['Address'].isnull() | (df['Address'] == '')
    missing_count = missing_mask.sum()
    print(f"共有 {missing_count} 筆資料缺少地址，準備開始補填...")

    if missing_count == 0:
        print("沒有需要補填的地址。")
        return

    processed_count = 0
    
    for index, row in df[missing_mask].iterrows():
        position_str = row['Position']
        try:
            pos_dict = ast.literal_eval(position_str)
            lat = pos_dict.get('PositionLat')
            lon = pos_dict.get('PositionLon')
            
            if lat and lon:
                print(f"正在查詢 ID {row['ID']} ({row['ScenicSpotName']})...", end="")
                new_address = get_address_from_latlon(gmaps, lat, lon)
                
                if new_address:
                    df.at[index, 'Address'] = new_address
                    print(f" 成功 -> {new_address}")
                else:
                    print(" 失敗 (無結果)")
                
                processed_count += 1
                time.sleep(0.1) 
                
        except Exception as e:
            print(f"處理 ID {row['ID']} 時發生錯誤: {e}")

    # 這裡改用 output_path (絕對路徑) 來存檔
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n處理完成！已更新 {processed_count} 筆地址。")
    print(f"結果已儲存為: {output_path}")

if __name__ == "__main__":
    main()