"""认证路由：单用户登录与登出。

无需注册功能，管理员账户通过 `flask init-admin` 命令预置创建。
未登录用户以游客身份浏览公开内容，编辑/增删/上传必须登录。
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from app.forms import LoginForm
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """管理员登录。"""
    # 已登录则直接回到首页
    if current_user.is_authenticated:
        return redirect(url_for("blog.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        # 统一错误提示，避免用户名枚举
        if user is None or not user.check_password(form.password.data):
            flash("用户名或密码错误。", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=form.remember.data)
        flash(f"欢迎回来，{user.display_name or user.username}！", "success")

        # 安全跳转：仅允许相对路径，防止开放重定向
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("blog.index"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """登出。"""
    logout_user()
    flash("已安全退出。", "info")
    return redirect(url_for("blog.index"))
