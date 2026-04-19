from flask import render_template, request, jsonify, current_app, redirect, url_for, flash  # 頁面渲染、接收請求、回傳 JSON、讀取設定、跳轉與提示訊息
from flask_login import login_required, current_user  # 登入保護與目前使用者
from . import map_bp
from ..models import Camp, Favorite, ViewHistory
from ..extensions import db


@map_bp.route("/")  # 地圖找營主頁
def map_view():
    return render_template(
        "map/index.html",
        amap_key=current_app.config.get("AMAP_WEB_KEY", ""),  # 傳給前端的高德地圖金鑰
        amap_security_js_code=current_app.config.get("AMAP_SECURITY_JS_CODE", "")  # 高德安全碼
    )


@map_bp.route("/api/camps")  # 地圖頁取得營地資料的 API
def camps_api():
    kw = (request.args.get("kw") or "").strip()  # 關鍵字
    city = (request.args.get("city") or "").strip()  # 城市篩選
    district = (request.args.get("district") or "").strip()  # 區域篩選
    max_price = request.args.get("max_price", type=float)  # 價格上限

    q = Camp.query

    # 關鍵字模糊搜尋：名稱、地址、城市、區域
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            (Camp.name.ilike(like)) |
            (Camp.address.ilike(like)) |
            (Camp.city.ilike(like)) |
            (Camp.district.ilike(like))
        )

    # 其他條件篩選
    if city:
        q = q.filter(Camp.city == city)
    if district:
        q = q.filter(Camp.district == district)
    if max_price is not None:
        q = q.filter(Camp.price_per_night <= max_price)

    camps = q.limit(800).all()  # 最多回傳 800 筆，避免地圖一次載入過多資料
    return jsonify([c.to_dict() for c in camps])  # 轉成 JSON 給前端地圖使用


@map_bp.route("/camp/<int:camp_id>")  # 單一營地詳情頁
def camp_detail(camp_id):
    camp = Camp.query.get_or_404(camp_id)  # 若找不到營地就回傳 404

    # 整理圖片：有圖就用資料庫圖片，沒有就補預設圖，固定顯示 3 張
    placeholder_photo = "/static/images/home-bg.png"
    photos = []
    for k in ["photo_1", "photo_2", "photo_3"]:
        v = getattr(camp, k, None)
        if v and str(v).strip():
            photos.append(str(v).strip())
    if not photos:
        photos = []
    while len(photos) < 3:
        photos.append(placeholder_photo)
    photos = photos[:3]

    # 若使用者已登入，檢查這個營地是否已被收藏
    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = Favorite.query.filter_by(
            user_id=current_user.id, camp_id=camp.id
        ).first() is not None

    return render_template("map/camp_detail.html", camp=camp, photos=photos, is_favorited=is_favorited)


@map_bp.route("/camp/<int:camp_id>/favorite", methods=["POST"])  # 收藏／取消收藏
@login_required
def toggle_favorite(camp_id):
    camp = Camp.query.get_or_404(camp_id)

    fav = Favorite.query.filter_by(user_id=current_user.id, camp_id=camp.id).first()
    if fav:
        db.session.delete(fav)  # 已收藏就取消收藏
        flash("已取消收藏", "info")
    else:
        db.session.add(Favorite(user_id=current_user.id, camp_id=camp.id))  # 未收藏就新增收藏
        flash("收藏成功", "success")

    db.session.commit()
    return redirect(url_for("map.camp_detail", camp_id=camp.id))  # 操作後回到營地詳情頁


@map_bp.route("/favorites")  # 我的收藏頁
@login_required
def my_favorites():
    favs = (
        db.session.query(Camp)
        .join(Favorite, Favorite.camp_id == Camp.id)  # 把 Camp 和 Favorite 連接起來
        .filter(Favorite.user_id == current_user.id)  # 只取目前使用者的收藏
        .order_by(Favorite.created_at.desc())  # 最新收藏排前面
        .all()
    )
    return render_template("map/favorites.html", camps=favs)


@map_bp.route("/debug-data")  # 除錯用：查看目前使用者的收藏與瀏覽紀錄
@login_required
def debug_data():
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    views = ViewHistory.query.filter_by(user_id=current_user.id).all()

    return {
        "favorites": [
            {"camp_id": f.camp_id, "created_at": str(f.created_at)}
            for f in favs
        ],
        "views": [
            {
                "camp_id": v.camp_id,
                "dwell_seconds": v.dwell_seconds,
                "created_at": str(v.created_at)
            }
            for v in views
        ]
    }


@map_bp.route("/record-view/<int:camp_id>", methods=["POST"])  # 記錄使用者瀏覽行為
@login_required
def record_view(camp_id):
    dwell_seconds = request.form.get("dwell_seconds", type=float, default=0)  # 前端傳來的停留秒數

    vh = ViewHistory(
        user_id=current_user.id,
        camp_id=camp_id,
        dwell_seconds=dwell_seconds
    )
    db.session.add(vh)
    db.session.commit()

    return ("", 204)  # 回傳空內容，表示記錄成功但不需要刷新頁面