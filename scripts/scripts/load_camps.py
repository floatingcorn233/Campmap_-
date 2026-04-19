import csv
from app import create_app
from app.extensions import db
from app.models import Camp

app = create_app()

def run():
    with app.app_context():
        db.drop_all()
        db.create_all()

        with open("app/data/camps_gd.csv", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                camp = Camp(
                    poi_id=(row.get("poi_id") or "").strip() or None,
                    name=row.get("name"),
                    address=row.get("address"),
                    city=row.get("city"),
                    district=row.get("district"),
                    province=row.get("province"),
                    tel=(row.get("tel") or "").strip() or None,
                    longitude=float(row.get("lng") or 0),
                    latitude=float(row.get("lat") or 0),
                    price_per_night=float(row.get("price_per_night") or 0),

                    tag_1=row.get("tag_1"),
                    tag_2=row.get("tag_2"),
                    tag_3=row.get("tag_3"),

                    photo_1=row.get("photo_1"),
                    photo_2=row.get("photo_2"),
                    photo_3=row.get("photo_3"),
                )

                db.session.add(camp)

        db.session.commit()
        print("✅ 数据导入完成")

if __name__ == "__main__":
    run()
