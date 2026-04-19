# 這個檔案是專案的設定檔，負責集中管理 Flask、資料庫和高德地圖 API 的參數。

import os
from dotenv import load_dotenv

load_dotenv()  # 載入 .env 裡的環境變數，避免把 key 直接寫死在程式裡。

class Config:
    # Flask 和資料庫的基本設定
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")  # Flask 密鑰，用於登入狀態和安全驗證。
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///campmap.db")  # 資料庫連線設定，預設使用本地 SQLite。
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 關閉額外追蹤功能，減少不必要負擔。

    # 高德地圖 API 設定
    AMAP_WEB_KEY = os.getenv("AMAP_WEB_KEY", "")  # 高德地圖 API Key。
    AMAP_SECURITY_CODE = os.getenv("AMAP_SECURITY_CODE", "")  # 高德地圖安全碼。