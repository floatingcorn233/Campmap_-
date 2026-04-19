from flask import Blueprint  # 藍圖工具
map_bp = Blueprint("map", __name__)  # 建立 map 藍圖
from . import routes  # 載入路由