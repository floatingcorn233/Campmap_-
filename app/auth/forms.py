# 這個檔案是在定義登入／註冊頁面中，使用者需要填寫哪些輸入欄位，以及這些欄位要如何驗證

from flask_wtf import FlaskForm  # Flask-WTF 提供的表單基底類別
from wtforms import StringField, PasswordField, SubmitField  # 文字輸入框、密碼輸入框、提交按鈕
from wtforms.validators import DataRequired, Length, EqualTo  # 常用驗證器：必填、長度限制、欄位一致性驗證


class RegisterForm(FlaskForm):  # 註冊表單
    username = StringField("使用者名稱", validators=[DataRequired(), Length(min=2, max=50)])  # 使用者名稱：必填，長度 2~50
    email = StringField("電子郵件", validators=[DataRequired(), Length(max=120)])  # 電子郵件：必填，最長 120
    password = PasswordField("密碼", validators=[DataRequired(), Length(min=6, max=128)])  # 密碼：必填，長度 6~128
    confirm_password = PasswordField(
        "確認密碼",
        validators=[DataRequired(), EqualTo("password", message="兩次輸入的密碼不一致")]  # 必填，且必須與 password 欄位一致
    )
    submit = SubmitField("註冊")  # 註冊按鈕


class LoginForm(FlaskForm):  # 登入表單
    email = StringField("電子郵件", validators=[DataRequired(), Length(max=120)])  # 電子郵件：必填
    password = PasswordField("密碼", validators=[DataRequired()])  # 密碼：必填
    submit = SubmitField("登入")  # 登入按鈕