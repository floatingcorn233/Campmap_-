from app import create_app
from app.extensions import db
from app.models import Camp
import csv
import os

app = create_app()

# ⚠️ 这里路径按你项目结构来
CSV_PATH = os.path.join("app", "data", "camps_gd.csv")

with app.app_context():
    # ===== 1. 重建数据库 =====
    db.drop_all()
    db.create_all()

    # ===== 2. 导入 CSV =====
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            camp = Camp(
                poi_id=(row.get("poi_id") or "").strip() or None,
                name=row.get("name"),
                city=row.get("city"),
                district=row.get("district"),
                address=row.get("address"),
                province=row.get("province"),
                tel=(row.get("tel") or "").strip() or None,

                longitude=float(row.get("lng") or 0),
                latitude=float(row.get("lat") or 0),

                # ⭐ 关键：tag
                tag_1=None if row.get("tag_1") in ("", "/", None) else row.get("tag_1"),
                tag_2=None if row.get("tag_2") in ("", "/", None) else row.get("tag_2"),
                tag_3=None if row.get("tag_3") in ("", "/", None) else row.get("tag_3"),

                photo_1=row.get("photo_1"),
                photo_2=row.get("photo_2"),
                photo_3=row.get("photo_3"),
            )

            db.session.add(camp)

    db.session.commit()

    # ===== 3. 验证 =====
    first = Camp.query.first()
    print("✅ 导入完成")
    print("数量:", Camp.query.count())
    if first:
        print("示例:", first.name, first.tag_1, first.tag_2, first.tag_3)
