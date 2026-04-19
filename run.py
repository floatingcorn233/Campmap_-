# 這個檔案是專案的啟動入口，負責建立 app、初始化資料表，並啟動本機伺服器。

from app import create_app

if __name__ == "__main__":  # 只有直接執行這個檔案時才會啟動
    app = create_app()  # 建立 Flask app

    # 進入 app context，初始化資料庫資料表
    with app.app_context():
        from app.extensions import db
        db.create_all()

    app.run(debug=True)  # 啟動開發伺服器