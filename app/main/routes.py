from flask import render_template, current_app  # 渲染頁面、讀取目前 Flask 設定
from . import main_bp

@main_bp.route("/")  # 首頁路由
def index():
    return render_template(
        "index.html",  # 回傳首頁模板
        amap_key=current_app.config.get("AMAP_WEB_KEY", ""),  # 傳入高德地圖 Web API Key
        amap_security_js_code=current_app.config.get("AMAP_SECURITY_JS_CODE", "")  # 傳入高德安全碼
    )