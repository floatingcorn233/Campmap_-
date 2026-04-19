from flask import Blueprint  # 匯入 Flask 的藍圖工具

main_bp = Blueprint("main", __name__)  # 建立 main 模組的藍圖

from . import routes  # 載入 routes.py，讓首頁等路由註冊到這個藍圖