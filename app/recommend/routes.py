from flask import render_template, jsonify, request  # 匯入模板渲染、回傳 JSON、讀取前端參數的工具
from flask_login import current_user  # current_user 代表「目前正在訪問網站的使用者」
from .services import get_default_camps, get_personalized_camps  # 匯入推薦邏輯函式（真正計算推薦在 services.py）
from . import recommend_bp  # 匯入推薦模組的藍圖（Blueprint）


# 這個檔案負責推薦頁的頁面顯示和推薦 API 回傳。
# 頁面先載入基礎內容，真正的個人化推薦由前端再呼叫 API 取得。

@recommend_bp.route("/")  # 訪問 /recommend/ 時，進入這個頁面路由
def index():
    results = get_default_camps(limit=6)  # 先準備 6 筆預設營地，避免頁面剛打開時是空白
    return render_template("recommend/index.html", results=results)  # 把預設營地傳給前端模板頁面


@recommend_bp.route("/api/personalized")  # 訪問 /recommend/api/personalized 時，進入這個 API
def api_personalized():
    print("=== HIT /recommend/api/personalized ===")  # 控制台輸出：確認前端確實有請求到這個 API

    if current_user.is_authenticated:  # 判斷目前使用者是否已登入
        user_id = current_user.id  # 如果已登入，就拿目前使用者的 id 做個人化推薦
    else:
        user_id = None  # 如果沒登入，就設為 None，後端走訪客推薦邏輯

    print("=== user_id ===", user_id)  # 輸出目前 user_id，方便除錯

    # 從前端讀取參數：
    # tag = 目前想聚焦的興趣標籤
    # seed = 用來讓「換一批」有變化感
    focus_tag = (request.args.get("tag") or "").strip() or None  # 從 URL 參數取 tag，去掉前後空白；如果最後是空字串，就變成 None
    seed = request.args.get("seed", type=int)  # 從 URL 參數取 seed，並自動轉成整數；如果沒有就回傳 None

    # 呼叫推薦邏輯
    results, interest_tags, selected_tag = get_personalized_camps(  # 呼叫 services.py 裡的核心推薦函式
        user_id=user_id,  # 把目前使用者 id 傳進去（已登入使用者有值，訪客是 None）
        limit=6,  # 最多回傳 6 筆推薦結果
        focus_tag=focus_tag,  # 目前聚焦的興趣標籤（例如「親子」「湖景」）
        seed=seed  # 用於「換一批」時打散結果，讓推薦更有變化
    )

    # 整理成前端更好使用的 JSON 結構
    safe_results = []  # 準備一個新列表，專門存「可安全回傳給前端」的結果

    for item in results:  # 逐筆處理每一條推薦結果
        camp = item["camp"]  # 取出這一筆結果裡的 Camp 物件（資料庫中的營地物件）

        safe_results.append({  # 把目前這一筆結果整理成普通字典後加入列表
            "score": round(float(item.get("score", 0)), 1),  # 取推薦分數，轉成 float 並保留 1 位小數；沒有就預設 0
            "camp": {  # Camp 物件不能直接 jsonify，所以手動挑出前端需要的欄位
                "id": camp.id,  # 營地 id
                "name": camp.name,  # 營地名稱
                "city": camp.city,  # 城市
                "district": camp.district,  # 區域
                "address": camp.address,  # 詳細地址
                "tel": camp.tel,  # 聯絡電話
                "price_per_night": camp.price_per_night,  # 每晚價格
                "photo_1": camp.photo_1,  # 第一張展示圖片
                "longitude": camp.longitude,  # 經度（地圖用）
                "latitude": camp.latitude,  # 緯度（地圖用）
            }
        })

    return jsonify({  # 把 Python 字典轉成 JSON 回傳給前端 JavaScript
        "selected_tag": selected_tag,  # 目前實際選中的標籤（前端用來高亮標籤）
        "interest_tags": interest_tags,  # 興趣標籤列表（前端用來渲染「猜你喜歡」標籤）
        "results": safe_results,  # 整理好的推薦結果列表（前端用來渲染營地卡片）
    })