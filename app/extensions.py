# 這個檔案是專案的擴充功能初始化檔，負責集中建立資料庫、資料庫遷移與登入管理物件，

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# 這一段先建立 Flask 常用的擴充功能物件，之後會在 create_app() 中再和 app 綁定。
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# 這一段是在設定登入系統的基本行為，讓需要登入的頁面能正確跳轉。
login_manager.login_view = "auth.login"  # 如果使用者未登入，會自動跳轉到 auth 藍圖中的 login 路由
login_manager.login_message = "请先登录后再访问该页面"  # 未登入時顯示的提示訊息
