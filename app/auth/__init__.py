from flask import Blueprint  # 导入 Flask 的 Blueprint，用来把不同功能模块分开管理路由

auth_bp = Blueprint("auth", __name__)  # 创建一个名为 auth 的蓝图，后面登录/注册相关路由都会挂在这里

from . import routes  # 导入当前模块下的 routes.py，让里面的路由函数真正注册到 auth_bp 上