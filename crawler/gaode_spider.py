import os
import time
import json
import csv
from typing import Dict, Any, List, Tuple, Optional
import requests

"""
深圳露營地採集（高德 Web 服務 POI 文字搜尋 + 詳情圖片）
- 第一步：/v3/place/text 抓 POI 清單（深圳 + citylimit + types=080504）
- 第二步：對每個 poi_id 呼叫 /v3/place/detail 補抓 photos
- 匯出：JSON（含 photos） + CSV（含 photo_1..photo_N）
"""

# 先讀取環境變數中的高德 API Key；如果沒設，就用預設值
AMAP_KEY = os.getenv("AMAP_KEY", "55300acc56a669540b5cb0cc2f477085").strip()

# 如果最後還是沒有 Key，就直接中止程式
if not AMAP_KEY:
    raise SystemExit("Missing AMAP_KEY. Please set environment variable AMAP_KEY to your AMap Web Service key.")

# 高德中「露營地」對應的類型碼
CAMP_TYPE = "080504"

# 用這幾組關鍵字分別搜尋，增加召回率
KEYWORDS = ["露營地", "露營", "營地"]

# 每頁抓取筆數（高德 text search 單頁上限通常為 25）
OFFSET = 25

# 每個關鍵字最多翻到幾頁，避免無限抓
MAX_PAGES = 80

# 兩種 API 的呼叫間隔（避免太快被限流）
SLEEP_SEC_LIST = 0.8   # 清單接口限速
SLEEP_SEC_DETAIL = 0.6 # 詳情接口限速（可調大，避免 10021）
RETRY = 3              # 詳情接口失敗時最多重試次數

# CSV 最多輸出幾張圖片欄位（photo_1 ~ photo_N）
MAX_PHOTOS = int(os.getenv("MAX_PHOTOS", "20"))

# 輸出資料夾與檔名
OUT_DIR = "output"
OUT_JSON = os.path.join(OUT_DIR, "amap_shenzhen_camping_with_photos.json")
OUT_CSV = os.path.join(OUT_DIR, "amap_shenzhen_camping_with_photos.csv")


def amap_text_search(city: str, keywords: str, page: int, types: str) -> Dict[str, Any]:
    """
    呼叫高德文字搜尋 API，取得指定城市 + 關鍵字 + 類型的 POI 清單
    """
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "key": AMAP_KEY,
        "keywords": keywords,
        "types": types,
        "city": city,
        "citylimit": "true",   # 限定只搜尋該城市
        "offset": str(OFFSET), # 每頁筆數
        "page": str(page),     # 第幾頁
        "extensions": "all",   # 盡量拿完整資訊
    }
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()  # HTTP 失敗直接拋錯
    return r.json()


def amap_place_detail(poi_id: str) -> Dict[str, Any]:
    """
    呼叫高德詳情 API，根據 poi_id 補抓單一 POI 的詳細資訊（主要用來拿 photos）
    """
    url = "https://restapi.amap.com/v3/place/detail"
    params = {
        "key": AMAP_KEY,
        "id": poi_id,
        "extensions": "all",
    }
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def parse_location(loc: str) -> Tuple[Optional[float], Optional[float]]:
    """
    把高德回傳的 location 字串（例如 '114.123,22.456'）
    轉成 (lng, lat) 浮點數；失敗就回傳 (None, None)
    """
    if not loc or "," not in loc:
        return None, None

    lng_s, lat_s = loc.split(",", 1)

    try:
        return float(lng_s), float(lat_s)
    except ValueError:
        return None, None


def safe_photo_urls(detail_json: Dict[str, Any]) -> List[str]:
    """
    從 detail API 回傳結果中安全提取圖片 URL 清單
    並做去重（保留原順序）
    """
    pois = detail_json.get("pois") or []
    if not pois:
        return []

    photos = pois[0].get("photos") or []
    urls: List[str] = []

    for p in photos:
        u = (p.get("url") or "").strip()
        if u:
            urls.append(u)

    # 去重但保持原本順序
    seen = set()
    uniq = []

    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)

    return uniq


def normalize_poi(poi: Dict[str, Any]) -> Dict[str, Any]:
    """
    把高德原始 POI 資料整理成我們自己統一的欄位格式
    方便後續匯出 JSON / CSV
    """
    lng, lat = parse_location(poi.get("location", ""))

    # 有些資料 cityname 可能為空或格式不一致，這裡做保底修正
    city = (poi.get("cityname") or "").strip()
    if not city or "深圳" not in city:
        city = "深圳市"

    return {
        "poi_id": poi.get("id", ""),
        "name": poi.get("name", ""),
        "address": poi.get("address", ""),
        "province": poi.get("pname", ""),
        "city": city,
        "district": poi.get("adname", ""),
        "location": poi.get("location", ""),
        "lng": lng,
        "lat": lat,
        "tel": poi.get("tel", ""),
        "type": poi.get("type", ""),
        "typecode": poi.get("typecode", ""),
        "business_area": poi.get("business_area", ""),
        "price": None,     # 高德通常沒有可靠價格，先留空
        "photos": [],      # 後面 detail API 補抓圖片 URL 清單
    }


def main():
    # 確保輸出資料夾存在；不存在就自動建立
    os.makedirs(OUT_DIR, exist_ok=True)

    # seen_ids 用來做去重，避免不同關鍵字抓到同一個 POI
    seen_ids = set()

    # 最終整理好的露營地資料都放這裡
    results: List[Dict[str, Any]] = []

    city_query = "深圳"

    # --------- 1) 抓 POI 清單 ---------
    for kw in KEYWORDS:
        print(f"[Query] city={city_query} kw={kw} types={CAMP_TYPE}")

        # 每個關鍵字分頁抓取
        for page in range(1, MAX_PAGES + 1):
            data = amap_text_search(city_query, kw, page, types=CAMP_TYPE)

            # 高德 API 狀態異常就直接報錯
            if data.get("status") != "1":
                raise RuntimeError(
                    f"AMap text error: info={data.get('info')} infocode={data.get('infocode')} raw={data}"
                )

            pois = data.get("pois") or []

            # 這一頁沒資料就代表到底了
            if not pois:
                break

            added = 0

            for poi in pois:
                pid = (poi.get("id") or "").strip()

                # 沒 id 或已經抓過就跳過
                if not pid or pid in seen_ids:
                    continue

                seen_ids.add(pid)
                results.append(normalize_poi(poi))
                added += 1

            print(f"  page={page:02d} pois={len(pois)} added={added} total_unique={len(results)}")

            # 控速，避免太快被高德限流
            time.sleep(SLEEP_SEC_LIST)

    # --------- 2) 對每個 POI 補抓詳情 photos ---------
    print(f"\n[Detail] Fetch photos for {len(results)} POIs ...")

    for i, item in enumerate(results, start=1):
        poi_id = item["poi_id"]
        print(f"  [{i:03d}/{len(results)}] poi_id={poi_id} name={item.get('name', '')}")

        last_err: Optional[Exception] = None

        # 詳情接口做重試機制
        for attempt in range(1, RETRY + 1):
            try:
                detail = amap_place_detail(poi_id)

                if detail.get("status") != "1":
                    raise RuntimeError(
                        f"AMap detail error: info={detail.get('info')} infocode={detail.get('infocode')}"
                    )

                # 成功就把圖片 URL 填進去
                item["photos"] = safe_photo_urls(detail)
                last_err = None
                break

            except Exception as e:
                last_err = e

                # 失敗後等待更久再重試（簡單退避）
                wait = SLEEP_SEC_DETAIL * (attempt + 1) * 2
                print(f"    attempt {attempt}/{RETRY} failed: {e}. sleep {wait:.1f}s")
                time.sleep(wait)

        # 如果最後還是失敗，就保持空圖片
        if last_err is not None:
            item["photos"] = []

        # 控速，避免太快被高德限流
        time.sleep(SLEEP_SEC_DETAIL)

    # --------- 3) 匯出 JSON ---------
    # JSON 會保留完整 photos 陣列，方便後續再處理
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # --------- 4) 匯出 CSV（含 photo_1..photo_N） ---------
    # 先定義基本欄位
    base_fields = [
        "poi_id", "name", "address", "district", "city", "province",
        "tel", "location", "lng", "lat", "type", "typecode", "business_area", "price"
    ]

    # 再動態產生 photo_1 ~ photo_N 欄位
    photo_fields = [f"photo_{j}" for j in range(1, MAX_PHOTOS + 1)]

    fieldnames = base_fields + photo_fields

    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for row in results:
            # 先放基本欄位
            out = {k: row.get(k) for k in base_fields}

            # 再把圖片清單攤平成 photo_1 ~ photo_N
            photos = row.get("photos") or []
            for j in range(1, MAX_PHOTOS + 1):
                out[f"photo_{j}"] = photos[j - 1] if len(photos) >= j else ""

            w.writerow(out)

    print("\nDone.")
    print(f"- Total unique POIs: {len(results)}")
    print(f"- JSON: {OUT_JSON}")
    print(f"- CSV : {OUT_CSV}")


# 只有直接執行這個檔案時，才會開始跑 main()
if __name__ == "__main__":
    main()
