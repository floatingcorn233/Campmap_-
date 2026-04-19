import os
import sys
import csv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Camp

# ===== 配置 =====
# True: 以CSV为准（先清空Camp表再导入）
# False: 增量更新（不删旧数据）
FULL_REPLACE = True

# 优先读取 camps_gd.csv，不存在则读取 camps_gd_final.csv
if os.path.exists("app/data/camps_gd.csv"):
    CSV_PATH = "app/data/camps_gd.csv"
else:
    CSV_PATH = "app/data/camps_gd_final.csv"


def parse_float(v, default=None):
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
    if not v:
        return 0.0
    s = str(v).replace("￥", "").replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def run():
    app = create_app()
    with app.app_context():
        created = 0
        updated = 0
        skipped_no_name = 0
        skipped_no_key = 0
        total = 0

        abs_csv = os.path.abspath(CSV_PATH)
        print("Using CSV:", abs_csv)

        # 1) 全量覆盖：先清空
        if FULL_REPLACE:
            deleted = Camp.query.delete()
            db.session.commit()
            print(f"Deleted old camps: {deleted}")

        # 2) 读取CSV导入
        with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            print("CSV headers:", reader.fieldnames)

            for row in reader:
                total += 1

                poi_id = (row.get("poi_id") or "").strip()
                name = (row.get("name") or row.get("camp_name") or "").strip()
                if not name:
                    skipped_no_name += 1
                    continue

                # 兼容有/无坐标列
                lng = parse_float(row.get("lng") or row.get("longitude"))
                lat = parse_float(row.get("lat") or row.get("latitude"))

                # FULL_REPLACE模式下基本都是新建；增量模式下按poi_id或name+city更新
                camp = None
                if not FULL_REPLACE:
                    if poi_id:
                        camp = Camp.query.filter_by(poi_id=poi_id).first()
                    else:
                        city = (row.get("city") or "").strip()
                        if city:
                            camp = Camp.query.filter_by(name=name, city=city).first()
                        else:
                            skipped_no_key += 1
                            continue

                if not camp:
                    camp = Camp()
                    created += 1
                else:
                    updated += 1

                camp.poi_id = poi_id or camp.poi_id
                camp.name = name
                camp.address = (row.get("address") or "").strip()
                camp.district = (row.get("district") or "").strip()
                camp.city = (row.get("city") or "").strip()
                camp.province = (row.get("province") or "").strip()
                camp.tel = (row.get("tel") or "").strip()

                # 有值才覆盖，避免把已有值清成空
                if lng is not None:
                    camp.longitude = lng
                if lat is not None:
                    camp.latitude = lat

                camp.camp_type = (row.get("type") or row.get("camp_type") or "").strip()
                camp.typecode = (row.get("typecode") or "").strip()
                camp.business_area = (row.get("business_ar") or row.get("business_area") or "").strip()
                camp.price_per_night = parse_price(row.get("price") or row.get("price_per_night"))

                camp.photo_1 = (row.get("photo_1") or "").strip()
                camp.photo_2 = (row.get("photo_2") or "").strip()
                camp.photo_3 = (row.get("photo_3") or "").strip()

                db.session.add(camp)

        db.session.commit()

        print(
            f"Import done. total={total}, created={created}, updated={updated}, "
            f"skipped_no_name={skipped_no_name}, skipped_no_key={skipped_no_key}, "
            f"mode={'FULL_REPLACE' if FULL_REPLACE else 'INCREMENTAL'}"
        )


if __name__ == "__main__":
    run()