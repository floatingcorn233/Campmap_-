from app.models import Camp, Favorite, ViewHistory  # 匯入營地、收藏紀錄、瀏覽紀錄三個資料表模型
from collections import Counter  # Counter 適合做「標籤 -> 分數」的累計統計
import math  # 用於開平方（餘弦相似度要用）
import random  # 用於「換一批」時做可控隨機


# 整個推薦系統統一使用的標籤空間
# 使用者興趣和營地特徵都會映射到這 9 個標籤上
TAG_SPACE = [
    "亲子友好",
    "公园露营",
    "可过夜",
    "团建场地",
    "城市露营",
    "小众秘境",
    "烧烤餐饮",
    "网红打卡",
    "自然生态",
]


# 清洗單個標籤值，過濾掉無效內容
def normalize_tag(value):
    if not value:  # 空值（None、空字串等）直接視為無效
        return None

    text = str(value).strip()  # 統一轉成字串，並去掉首尾空白
    if text in ["/", "-", "None", "none", "null", "Null", "nan", "NaN"]:  # 一些常見「偽空值」也過濾掉
        return None

    return text  # 回傳清洗後的有效標籤


# 從單個營地裡提取有效標籤
# 目前每個營地有 tag_1 / tag_2 / tag_3 三個欄位
def get_camp_tags(camp):
    tags = []  # 用來收集這個營地的有效標籤

    for field in ["tag_1", "tag_2", "tag_3"]:  # 依序讀取營地的三個標籤欄位
        if hasattr(camp, field):  # 保險一點，先確認這個欄位確實存在
            v = normalize_tag(getattr(camp, field))  # getattr(camp, field) = 動態取 camp.tag_1 / tag_2 / tag_3
            if v:
                tags.append(v)  # 只保留清洗後有效的標籤

    return tags  # 回傳這個營地的標籤列表


# 把營地映射成固定 9 維向量
# 有這個標籤記為 1，沒有記為 0
def build_camp_vector(camp):
    vec = [0] * len(TAG_SPACE)  # 先生成一個全 0 的 9 維向量
    tags = get_camp_tags(camp)  # 取出目前營地的標籤列表

    for t in tags:
        if t in TAG_SPACE:  # 只處理在統一標籤空間裡的標籤
            idx = TAG_SPACE.index(t)  # 找到這個標籤在 9 維空間中的位置
            vec[idx] = 1  # 有這個標籤就把對應維度設為 1

    return vec


# 建立使用者興趣分數表（tag -> score）
# 收藏權重大，瀏覽權重較低但會結合停留時間加權
def build_user_tag_scores(user_id):
    tag_scores = Counter()  # Counter 本質像字典，但做「累加計分」更方便

    print("\n========== USER VECTOR ==========")
    print("user_id =", user_id)
    print("TAG_SPACE =", TAG_SPACE)

    # 收藏紀錄：強興趣，權重 +3
    favorites = Favorite.query.filter_by(user_id=user_id).all()  # 取出這個使用者的所有收藏紀錄
    print(f"\n[FAVORITES] 共 {len(favorites)} 條")

    for fav in favorites:
        camp = Camp.query.get(fav.camp_id)  # 根據收藏紀錄裡的 camp_id 找到對應營地
        if not camp:
            continue  # 如果營地不存在（被刪了等），就跳過

        tags = get_camp_tags(camp)  # 取出這個收藏營地的標籤
        camp_vec = build_camp_vector(camp)  # 生成營地向量

        print("[FAV]", camp.name, tags)
        print("      camp_vector =", camp_vec)

        for t in tags:
            if t in TAG_SPACE:
                tag_scores[t] += 3.0  # 每收藏一次，對應標籤加 3 分（強興趣）

    # 瀏覽紀錄：弱興趣，基礎 + 停留時長加權
    views = ViewHistory.query.filter_by(user_id=user_id).all()  # 取出這個使用者的所有瀏覽紀錄
    print(f"\n[VIEWS] 共 {len(views)} 條")

    for v in views:
        camp = Camp.query.get(v.camp_id)  # 根據瀏覽紀錄裡的 camp_id 找到對應營地
        if not camp:
            continue

        tags = get_camp_tags(camp)  # 取出這個瀏覽營地的標籤
        camp_vec = build_camp_vector(camp)  # 同樣生成向量

        dwell = min(v.dwell_seconds or 0, 30)   # 停留時長最多按 30 秒算，避免極端值影響過大
        weight = 0.2 + dwell / 50.0             # 瀏覽基礎分 1.0；每多停留 1 秒，加 0.02

        print("[VIEW]", camp.name, tags, "dwell=", dwell)
        print("       camp_vector =", camp_vec)
        print("       weight =", round(weight, 2))

        for t in tags:
            if t in TAG_SPACE:
                tag_scores[t] += weight  # 瀏覽行為按停留時長給標籤累計分數

    print("\ntag_scores =", dict(tag_scores))
    print("================================\n")

    return tag_scores  # 回傳


# 餘弦相似度
# 用來比較「使用者興趣方向」和「營地方向」是否接近
def cosine(a, b):
    dot_val = sum(x * y for x, y in zip(a, b))  # 點積：同方向重合越多，值越大
    norm_a = math.sqrt(sum(x * x for x in a))  # 向量 a 的長度
    norm_b = math.sqrt(sum(x * x for x in b))  # 向量 b 的長度

    if norm_a == 0 or norm_b == 0:  # 任一向量全 0 時，無法比較方向，直接回傳 0
        return 0

    return dot_val / (norm_a * norm_b)  # 餘弦相似度範圍通常在 0~1（你這裡向量非負）


# 預設推薦：未登入 / 無足夠行為資料時使用
def get_default_camps(limit=6):
    camps = Camp.query.limit(limit).all()  # 直接取前 limit 筆營地（簡單兜底邏輯）
    return [{"camp": c, "score": 0} for c in camps]  # 包裝成和個人化推薦一致的資料結構


# 帶 seed 的預設推薦：用於未登入時「換一批」；邏輯是：隨機打亂，取前六個
def get_default_camps_seeded(limit=6, seed=None):
    if seed is None:  # 如果沒傳 seed，就直接走普通預設推薦
        return get_default_camps(limit)

    camps = Camp.query.all()  # 取出全部營地
    rng = random.Random(seed)  # 用固定 seed 建立隨機物件：同一個 seed 會得到同樣的打亂結果
    rng.shuffle(camps)  # 原地打亂營地順序
    camps = camps[:limit]  # 取前 limit 筆

    return [{"camp": c, "score": 0} for c in camps]  # 仍然保持統一回傳格式


# 個人化推薦主函式
# interest_tags = 使用者整體「喜歡什麼」
# focus_tag = 前端這次「想看哪一類」
# selected_tag = 後端最終「決定這輪按哪一類篩」
def get_personalized_camps(user_id=None, limit=6, focus_tag=None, seed=None):
    print("=== ENTER get_personalized_camps ===")

    # 沒登入：不做個人化，直接走預設推薦
    if not user_id:
        return get_default_camps_seeded(limit, seed=seed), [], None  # 遊客回傳：推薦結果 + 空興趣標籤 + 無選中標籤

    # 已登入：先建立使用者興趣向量
    tag_scores = build_user_tag_scores(user_id)  # 先得到每個標籤的累計興趣分數
    user_vec = [tag_scores.get(tag, 0) for tag in TAG_SPACE]  # 按 TAG_SPACE 順序轉成固定 9 維使用者向量
    print("user_vec (for recommendation) =", user_vec)

    # 提取使用者目前有興趣的標籤列表（按分數高低排序）
    interest_tags = [
        tag for tag, score in tag_scores.most_common()  # most_common() 會按分數從高到低回傳
        if score > 0 and tag in TAG_SPACE
    ][:3]  # 只取分數最高的前 3 個標籤，給前端顯示「猜你喜歡」

    # 如果前端傳來的標籤有效，就作為本輪推薦主題
    # 否則不按標籤篩選，保持全域個人化排序
    if focus_tag and focus_tag in interest_tags:  # 只有「前端傳了」且「確實在使用者興趣標籤裡」才接受
        selected_tag = focus_tag  # 本輪按這個標籤聚焦推薦
    else:
        selected_tag = None   # 否則保持全域個人化推薦，不強制按標籤篩選

    camps = Camp.query.all()  # 取出所有營地，後面逐個打分
    scored = []  # 用來存放「營地 + 推薦分數」

    for c in camps:
        # 如果本輪有選中的標籤，就先篩掉不包含這個標籤的營地
        # 這樣後面的推薦會更聚焦
        if selected_tag and selected_tag not in get_camp_tags(c):
            continue  # 目前營地不屬於這類標籤，就跳過

        camp_vec = build_camp_vector(c)  # 把目前營地也轉成 9 維向量

        # 用 cosine 算匹配度，再映射成 3~5 分
        # cosine 越接近 1，說明營地標籤方向越接近使用者興趣方向
        score = 3 + cosine(user_vec, camp_vec) * 2  # 這樣最終分數範圍大致落在 3~5 分之間

        scored.append({
            "camp": c,
            "score": round(score, 1)  # 推薦分數保留 1 位小數
        })

    # 分數高的排前面
    scored.sort(key=lambda x: x["score"], reverse=True)  # 按 score 從高到低排序

    # 如果目前有選中標籤 + 有 seed
    # 就只在高分池裡輕微打亂，保證「有變化」但不至於太亂
    if seed is not None and selected_tag is not None:
        rng = random.Random(seed)  # 用 seed 控制這次「換一批」的隨機順序
        top_pool = scored[: min(len(scored), max(limit * 6, limit))]  # 只取前面一小段高分池來打亂，避免低品質結果混進來
        rng.shuffle(top_pool)  # 只打亂高分池內部順序
        scored = top_pool + scored[len(top_pool):]  # 打亂後的高分池 + 後面未打亂部分重新拼回去

    print("\n====== TOP RESULTS ======")
    for x in scored[:5]:
        print(x["camp"].name, x["score"])  # 列印前 5 筆結果，方便看推薦效果
    print("========================\n")

    # 回傳前 limit 筆 + 興趣標籤列表 + 本輪實際選中的標籤
    return scored[:limit], interest_tags, selected_tag  # 前端最終會拿這三個值分別渲染卡片、標籤、高亮狀態