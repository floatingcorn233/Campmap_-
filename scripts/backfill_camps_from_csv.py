import os
import sys
import csv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Camp


def _norm(v: object) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _meaningful(v: str) -> bool:
    return bool(v) and v not in {"/", "-", "—"}


def _maybe_set(obj, attr: str, new_value: str) -> bool:
    current_value = _norm(getattr(obj, attr, ""))
    if _meaningful(new_value) and not _meaningful(current_value):
        setattr(obj, attr, new_value)
        return True
    return False


def run():
    if os.path.exists("app/data/camps_gd.csv"):
        csv_path = "app/data/camps_gd.csv"
    else:
        csv_path = "app/data/camps_gd_final.csv"

    app = create_app()
    with app.app_context():
        updated = 0
        matched = 0
        skipped = 0

        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                poi_id = _norm(row.get("poi_id"))
                name = _norm(row.get("name") or row.get("camp_name"))
                city = _norm(row.get("city"))

                camp = None
                if poi_id:
                    camp = Camp.query.filter_by(poi_id=poi_id).first()
                if camp is None and name and city:
                    camp = Camp.query.filter_by(name=name, city=city).first()

                if camp is None:
                    skipped += 1
                    continue

                matched += 1

                changed = False
                changed |= _maybe_set(camp, "tel", _norm(row.get("tel")))
                changed |= _maybe_set(camp, "photo_1", _norm(row.get("photo_1")))
                changed |= _maybe_set(camp, "photo_2", _norm(row.get("photo_2")))
                changed |= _maybe_set(camp, "photo_3", _norm(row.get("photo_3")))

                if changed:
                    updated += 1
                    db.session.add(camp)

        db.session.commit()
        print(f"Backfill done. matched={matched}, updated={updated}, skipped={skipped}, csv={csv_path}")


if __name__ == "__main__":
    run()

