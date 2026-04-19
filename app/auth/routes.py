import re
from flask import render_template, request, redirect, url_for, flash  # 頁面渲染、接收表單資料、跳轉、生成網址、提示訊息
from flask_login import login_user, logout_user, login_required  # 登入、登出、登入保護
from . import auth_bp
from ..extensions import db
from ..models import User

# 用正則表達式檢查輸入格式
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^1\d{10}$")
PWD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$")


@auth_bp.route("/login", methods=["GET", "POST"])  # 同一個頁面同時處理登入與註冊
def login():
    tab = request.args.get("tab", "login")  # 決定目前預設顯示登入分頁還是註冊分頁

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()  # 判斷這次提交的是登入還是註冊

        # 登入：支援使用電子郵件或手機號登入
        if action == "login":
            account = (request.form.get("account") or "").strip()
            password = request.form.get("password") or ""

            user = None
            if EMAIL_RE.match(account):
                user = User.query.filter_by(email=account).first()  # 如果像電子郵件，就用 email 查詢
            elif PHONE_RE.match(account):
                user = User.query.filter_by(phone=account).first()  # 如果像手機號，就用 phone 查詢
            else:
                flash("请输入正确的邮箱或手机号", "error")
                return render_template("auth/auth_tabs.html", tab="login")

            if not user or not user.check_password(password):  # 使用者不存在，或密碼驗證失敗
                flash("账号或密码错误", "error")
                return render_template("auth/auth_tabs.html", tab="login")

            login_user(user)  # 登入成功後，把目前使用者狀態記錄到 session
            flash("登录成功", "success")
            return redirect(url_for("main.index"))  # 登入後跳回首頁

        # 註冊
        elif action == "register":
            username = (request.form.get("username") or "").strip()
            email = (request.form.get("email") or "").strip()
            phone = (request.form.get("phone") or "").strip()
            password = request.form.get("password") or ""
            confirm = request.form.get("confirm_password") or ""

            # 先做基本格式驗證
            if not EMAIL_RE.match(email):
                flash("邮箱格式不正确，请检查后缀", "error")
                return render_template("auth/auth_tabs.html", tab="register")
            if not PHONE_RE.match(phone):
                flash("手机号格式不正确，应为11位中国大陆手机号", "error")
                return render_template("auth/auth_tabs.html", tab="register")
            if not PWD_RE.match(password):
                flash("密码至少6位，且必须包含字母和数字", "error")
                return render_template("auth/auth_tabs.html", tab="register")
            if password != confirm:
                flash("两次输入密码不一致", "error")
                return render_template("auth/auth_tabs.html", tab="register")

            # 再檢查資料庫裡是否已經存在重複帳號資料
            if User.query.filter_by(email=email).first():
                flash("该邮箱已注册", "error")
                return render_template("auth/auth_tabs.html", tab="register")
            if User.query.filter_by(phone=phone).first():
                flash("该手机号已注册", "error")
                return render_template("auth/auth_tabs.html", tab="register")
            if User.query.filter_by(username=username).first():
                flash("用户名已存在", "error")
                return render_template("auth/auth_tabs.html", tab="register")

            # 建立新使用者並寫入資料庫
            user = User(username=username, email=email, phone=phone)
            user.set_password(password)  # 先把明文密碼加密後再存入 password_hash
            db.session.add(user)
            db.session.commit()

            flash("注册成功，请登录", "success")
            return redirect(url_for("auth.login", tab="login"))  # 註冊成功後切回登入分頁

        else:
            flash("请求无效，请重试", "error")
            return render_template("auth/auth_tabs.html", tab="login")

    return render_template("auth/auth_tabs.html", tab=tab)  # GET 請求時直接顯示頁面


@auth_bp.route("/logout")
@login_required  # 只有已登入使用者才能登出
def logout():
    logout_user()  # 清除目前登入狀態
    flash("已退出登录", "success")
    return redirect(url_for("main.index"))  # 登出後回到首頁