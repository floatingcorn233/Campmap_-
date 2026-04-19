import os
import sys
import csv

# 把專案根目錄加入 Python 搜尋路徑，方便從 scripts/ 匯入 app 模組
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Camp

# ===== 設定 =====
# True：以 CSV 為準（先清空 Camp 表再重新匯入）
# False：增量更新（保留舊資料，不刪除）
FULL_REPLACE = True

# 優先讀取 camps_gd.csv，若不存在則改讀 camps_gd_final.csv
if os.path.exists("app/data/camps_gd.csv"):
    CSV_PATH = "app/data/camps_gd.csv"
else:
    CSV_PATH = "app/data/camps_gd_final.csv"


def parse_float(v, default=None):
    """
    嘗試把欄位轉成 float
    若為空值或轉換失敗，回傳預設值
    """
    try:
        if v is None:
            return default
        s = str(v).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def parse_price(v):
    """
    解析價格欄位：
    - 去掉 ￥ 符號與逗號
    - 轉成 float
    - 若無法解析則回傳 0.0
    """
    if not v:
        return 0.0
    s = str(v).replace("￥", "").replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def run():
    # 建立 Flask app，進入 app context 後才能操作資料庫
    app = create_app()
    with app.app_context():
        created = 0          # 新增的營地數
        updated = 0          # 更新的營地數
        skipped_no_name = 0  # 因為沒有名稱而跳過的筆數
        skipped_no_key = 0   # 增量模式下缺少匹配條件而跳過的筆數
        total = 0            # CSV 總筆數

        abs_csv = os.path.abspath(CSV_PATH)
        print("Using CSV:", abs_csv)

        # 1) 全量覆蓋模式：先清空 Camp 表
        if FULL_REPLACE:
            deleted = Camp.query.delete()
            db.session.commit()
            print(f"Deleted old camps: {deleted}")

        # 2) 讀取 CSV 並匯入資料
        with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            print("CSV headers:", reader.fieldnames)

            for row in reader:
                total += 1

                # 先讀取關鍵欄位
                poi_id = (row.get("poi_id") or "").strip()
                name = (row.get("name") or row.get("camp_name") or "").strip()

                # 沒有名稱就無法建立營地，直接跳過
                if not name:
                    skipped_no_name += 1
                    continue

                # 相容不同 CSV 欄位名稱（lng/longitude、lat/latitude）
                lng = parse_float(row.get("lng") or row.get("longitude"))
                lat = parse_float(row.get("lat") or row.get("latitude"))

                # FULL_REPLACE 模式下通常都是新建
                # 增量模式下才需要先找舊資料來更新
                camp = None
                if not FULL_REPLACE:
                    # 優先用 poi_id 精準匹配
                    if poi_id:
                        camp = Camp.query.filter_by(poi_id=poi_id).first()
                    else:
                        # 沒有 poi_id 時，退回用 name + city 匹配
                        city = (row.get("city") or "").strip()
                        if city:
                            camp = Camp.query.filter_by(name=name, city=city).first()
                        else:
                            skipped_no_key += 1
                            continue

                # 找不到舊資料就新建，找到就更新
                if not camp:
                    camp = Camp()
                    created += 1
                else:
                    updated += 1

                # 基本欄位寫入
                camp.poi_id = poi_id or camp.poi_id
                camp.name = name
                camp.address = (row.get("address") or "").strip()
                camp.district = (row.get("district") or "").strip()
                camp.city = (row.get("city") or "").strip()
                camp.province = (row.get("province") or "").strip()
                camp.tel = (row.get("tel") or "").strip()

                # 座標有值才覆蓋，避免把原本資料清成空值
                if lng is not None:
                    camp.longitude = lng
                if lat is not None:
                    camp.latitude = lat

                # 其他欄位寫入（相容不同 CSV 欄位命名）
                camp.camp_type = (row.get("type") or row.get("camp_type") or "").strip()
                camp.typecode = (row.get("typecode") or "").strip()
                camp.business_area = (row.get("business_ar") or row.get("business_area") or "").strip()
                camp.price_per_night = parse_price(row.get("price") or row.get("price_per_night"))

                # 圖片欄位
                camp.photo_1 = (row.get("photo_1") or "").strip()
                camp.photo_2 = (row.get("photo_2") or "").strip()
                camp.photo_3 = (row.get("photo_3") or "").strip()

                # 加入 session，等待最後統一提交
                db.session.add(camp)

        # 統一提交所有變更
        db.session.commit()

        # 印出匯入結果摘要
        print(
            f"Import done. total={total}, created={created}, updated={updated}, "
            f"skipped_no_name={skipped_no_name}, skipped_no_key={skipped_no_key}, "
            f"mode={'FULL_REPLACE' if FULL_REPLACE else 'INCREMENTAL'}"
        )


if __name__ == "__main__":
    run()