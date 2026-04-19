import os
import sys
import csv

# 把專案根目錄加入 Python 搜尋路徑，方便從 scripts/ 目錄匯入 app 模組
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Camp


def _norm(v: object) -> str:
    """
    統一清洗欄位值：
    - None 轉成空字串
    - 其他值轉成字串後去除前後空白
    """
    if v is None:
        return ""
    return str(v).strip()


def _meaningful(v: str) -> bool:
    """
    判斷欄位值是否有效
    排除空字串與常見的無效佔位符號
    """
    return bool(v) and v not in {"/", "-", "—"}


def _maybe_set(obj, attr: str, new_value: str) -> bool:
    """
    只有在「新值有效」且「目前欄位還沒有有效值」時，才更新欄位
    避免把原本已經有資料的欄位覆蓋掉
    """
    current_value = _norm(getattr(obj, attr, ""))
    if _meaningful(new_value) and not _meaningful(current_value):
        setattr(obj, attr, new_value)
        return True
    return False


def run():
    # 優先讀取 camps_gd.csv，若不存在則退回 camps_gd_final.csv
    if os.path.exists("app/data/camps_gd.csv"):
        csv_path = "app/data/camps_gd.csv"
    else:
        csv_path = "app/data/camps_gd_final.csv"

    # 建立 Flask app，進入 app context 後才能使用資料庫
    app = create_app()
    with app.app_context():
        updated = 0   # 成功更新資料的筆數
        matched = 0   # 成功在資料庫中找到對應 Camp 的筆數
        skipped = 0   # 找不到對應 Camp、被跳過的筆數

        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # 先從 CSV 讀取關鍵欄位
                poi_id = _norm(row.get("poi_id"))
                name = _norm(row.get("name") or row.get("camp_name"))
                city = _norm(row.get("city"))

                camp = None

                # 優先用 poi_id 精準匹配
                if poi_id:
                    camp = Camp.query.filter_by(poi_id=poi_id).first()

                # 如果 poi_id 沒找到，再退回用 name + city 匹配
                if camp is None and name and city:
                    camp = Camp.query.filter_by(name=name, city=city).first()

                # 如果還是找不到，就跳過這筆
                if camp is None:
                    skipped += 1
                    continue

                matched += 1
                changed = False

                # 只在原欄位沒有有效值時，回填電話與圖片
                changed |= _maybe_set(camp, "tel", _norm(row.get("tel")))
                changed |= _maybe_set(camp, "photo_1", _norm(row.get("photo_1")))
                changed |= _maybe_set(camp, "photo_2", _norm(row.get("photo_2")))
                changed |= _maybe_set(camp, "photo_3", _norm(row.get("photo_3")))

                # 如果這筆有更新，就加入 session 等待提交
                if changed:
                    updated += 1
                    db.session.add(camp)

        # 統一提交所有變更到資料庫
        db.session.commit()

        # 印出回填結果摘要
        print(f"Backfill done. matched={matched}, updated={updated}, skipped={skipped}, csv={csv_path}")


if __name__ == "__main__":
    run()