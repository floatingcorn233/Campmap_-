# 這個檔案是 Flask 專案的初始化入口，主要負責建立 app、載入設定、初始化擴充功能，並註冊各個功能模組（Blueprint）。

from flask import Flask  # 匯入 Flask 類別，用來建立整個網站應用
from .extensions import db, login_manager  # 匯入資料庫 db 和登入管理 login_manager
from flask_migrate import Migrate  # 匯入 Flask-Migrate，用來管理資料庫遷移
from .recommend import recommend_bp  # 匯入推薦模組的藍圖（Blueprint）


# 先建立 Migrate 物件，後面會再和 app、db 綁定，讓資料表變更可以用 migration 管理。
migrate = Migrate()

# create_app 是 Flask 的工廠函式，作用是把整個網站後端需要的元件組裝起來。
def create_app():
    # 這一段在建立 Flask app，並載入整個專案的設定檔。
    app = Flask(__name__)  # 建立 Flask 應用實例
    app.config.from_object("app.config.Config")  # 從 app.config.Config 載入設定（如資料庫、密鑰等）

    # 這一段在初始化 Flask 的擴充功能，讓資料庫、登入系統、migration 都能和目前 app 連接。
    db.init_app(app)  # 初始化資料庫，將 db 綁定到目前的 app
    login_manager.init_app(app)  # 初始化登入管理系統，讓 Flask-Login 可以管理使用者登入狀態
    migrate.init_app(app, db)   # 初始化資料庫遷移功能，之後可用 flask db 指令更新資料表

    # 這一段在匯入各個功能模組的 Blueprint，準備註冊到主 app。
    # 注册蓝图...
    from .main import main_bp  # 匯入主頁模組的藍圖
    from .auth import auth_bp  # 匯入登入 / 註冊模組的藍圖
    from .map import map_bp  # 匯入地圖模組的藍圖
    from .recommend import recommend_bp  # 匯入推薦模組的藍圖

    # 這一段在註冊 Blueprint，讓不同功能的路由正式加入到 Flask app。
    app.register_blueprint(main_bp)  # 註冊主頁藍圖，不加前綴，通常對應首頁
    app.register_blueprint(auth_bp, url_prefix="/auth")  # 註冊 auth 藍圖，所有登入註冊路由前面加 /auth
    app.register_blueprint(map_bp, url_prefix="/map")  # 註冊 map 藍圖，所有地圖功能路由前面加 /map
    app.register_blueprint(recommend_bp, url_prefix="/recommend")  # 註冊 recommend 藍圖，所有推薦功能路由前面加 /recommend

    # 最後回傳建立完成的 app，讓外部程式可以啟動整個網站。
    return app