# 這個檔案是 recommend 模組的初始化檔，主要用來建立推薦功能的 Blueprint，

from flask import Blueprint

recommend_bp = Blueprint("recommend", __name__, url_prefix="/recommend")  # 建立推薦模組的 Blueprint，之後這個模組底下的路由都會自動加上 /recommend 前綴

from . import routes  # 匯入 routes，讓這個模組中的路由函式能被 Flask 載入