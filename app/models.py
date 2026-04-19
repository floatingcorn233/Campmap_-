# 這個檔案是專案的資料模型檔，主要用來定義資料庫中有哪些表（table），
# 例如使用者、營地、收藏紀錄與瀏覽紀錄。這些模型會決定網站資料怎麼被儲存和查詢。

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager


# User 模型對應 users 資料表，負責儲存使用者帳號資訊。
# 因為繼承了 UserMixin，所以可以直接配合 Flask-Login 做登入狀態管理。
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)  # 使用者主鍵 id
    username = db.Column(db.String(50), unique=True, nullable=False)  # 使用者名稱，不可重複
    email = db.Column(db.String(120), unique=True, nullable=False)  # 電子郵件，不可重複
    phone = db.Column(db.String(20), unique=True, index=True)  # 電話，可建立索引方便查詢
    password_hash = db.Column(db.String(255), nullable=False)  # 儲存加密後的密碼，而不是明文密碼

    # 註冊或修改密碼時使用，把原始密碼轉成雜湊值後再存入資料庫，提高安全性。
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    # 登入時使用，檢查輸入密碼是否和資料庫中的雜湊值相符。
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


# Camp 模型對應 camps 資料表，負責儲存營地的基本資訊、位置、圖片和部分標籤資料。
# 這個表可以理解成網站的核心內容資料表，地圖頁和推薦頁都會依賴它。
class Camp(db.Model):
    __tablename__ = "camps"

    id = db.Column(db.Integer, primary_key=True)  # 營地主鍵 id
    poi_id = db.Column(db.String(64), unique=True, index=True)  # 高德 POI id，作為外部資料來源的唯一識別
    name = db.Column(db.String(150), nullable=False, index=True)  # 營地名稱
    address = db.Column(db.String(255))  # 地址
    district = db.Column(db.String(80), index=True)  # 區 / 區縣
    city = db.Column(db.String(80), index=True)  # 城市
    province = db.Column(db.String(80), index=True)  # 省份
    tel = db.Column(db.String(64))  # 電話
    tag_1 = db.Column(db.String(50))
    tag_2 = db.Column(db.String(50))
    tag_3 = db.Column(db.String(50))

    photo_1 = db.Column(db.String(500))
    photo_2 = db.Column(db.String(500))
    photo_3 = db.Column(db.String(500))
    longitude = db.Column(db.Float, nullable=False, index=True)  # 經度，地圖顯示需要
    latitude = db.Column(db.Float, nullable=False, index=True)  # 緯度，地圖顯示需要

    # 這次前端沒有顯示這個字段，留作之後優化使用
    camp_type = db.Column(db.String(120))  # 營地類型
    typecode = db.Column(db.String(32))  # 高德類型編碼
    business_area = db.Column(db.String(120))  # 商圈或業務區域
    price_per_night = db.Column(db.Float, default=0.0)  # 每晚價格，預設為 0

    description = db.Column(db.Text)  # 營地描述，可存較長文字

    # 這個方法會把 Camp 物件轉成前端比較好使用的字典格式，方便 API 回傳 JSON。
    def to_dict(self):
        tel = (self.tel or "").strip()
        if tel in {"/", "-", "—"}:
            tel = ""
        return {
            "id": self.id,
            "poi_id": self.poi_id,
            "name": self.name,
            "address": self.address or "",
            "district": self.district or "",
            "city": self.city or "",
            "province": self.province or "",
            "tel": tel,
            "lng": self.longitude,
            "lat": self.latitude,
            "camp_type": self.camp_type or "",
            "typecode": self.typecode or "",
            "business_area": self.business_area or "",
            "price_per_night": self.price_per_night or 0,
        }


# Favorite 模型對應 favorites 資料表，用來記錄「哪個使用者收藏了哪個營地」。
# 它本質上是一張關聯表，連接 users 和 camps，支撐收藏功能。
class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)  # 對應 users 表
    camp_id = db.Column(db.Integer, db.ForeignKey("camps.id"), nullable=False, index=True)  # 對應 camps 表
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # 收藏時間，預設為目前時間

    __table_args__ = (
        db.UniqueConstraint("user_id", "camp_id", name="uq_user_camp_fav"),  # 同一使用者不能重複收藏同一營地
    )


# ViewHistory 模型對應 view_history 資料表，用來記錄使用者看過哪些營地，以及停留時間。
# 這些資料之後可以作為個人化推薦的重要依據。
class ViewHistory(db.Model):
    __tablename__ = "view_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)  # 哪個使用者看過
    camp_id = db.Column(db.Integer, db.ForeignKey("camps.id"), nullable=False, index=True)  # 看的是哪個營地
    dwell_seconds = db.Column(db.Float, default=0.0)  # 停留秒數，可用來衡量興趣程度
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # 瀏覽時間


# 這一段是 Flask-Login 需要的 user_loader。
# 作用是：當系統記住某個使用者 id 時，可以透過這個函式把對應的 User 物件再查回來。
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))