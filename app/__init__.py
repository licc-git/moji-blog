"""Flask 应用工厂模块。

核心入口 `create_app()` 负责：
1. 创建 Flask 实例并加载配置
2. 初始化扩展（db、login、migrate、csrf）
3. 注册蓝图（auth / blog / upload / ai）
4. 注册上下文处理器、错误处理、CLI 命令
5. 确保上传目录存在

遵循 Application Factory Pattern，支持开发与生产配置分离，
也便于在测试中创建独立的应用实例。
"""

from __future__ import annotations

import os

from flask import Flask, render_template

from app.config import get_config
from app.extensions import db, login_manager, migrate, csrf


def create_app(config_name: str | None = None) -> Flask:
    """创建并配置 Flask 应用实例。

    :param config_name: 配置环境名称（development/production/testing），
                        为空时读取 FLASK_ENV 环境变量
    :return: 配置完成的 Flask 应用
    """
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(get_config(config_name))

    # 确保上传目录存在
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ---- 初始化扩展 ----
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ---- 注册蓝图 ----
    from app.auth.views import auth_bp
    from app.blog.views import blog_bp
    from app.upload.views import upload_bp
    from app.ai.views import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(ai_bp, url_prefix="/ai")

    # ---- 上下文处理器：向所有模板注入全局变量 ----
    @app.context_processor
    def inject_globals():
        from app.models import Category
        return {
            "site_name": "墨记 · MoJi",
            "site_tagline": "记录学习与生活的点滴",
            "nav_categories": Category.query.order_by(Category.sort_order, Category.id).all()
            if app.config.get("SQLALCHEMY_DATABASE_URI")
            else [],
        }

    # ---- 错误处理 ----
    register_error_handlers(app)

    # ---- CLI 命令 ----
    from app.cli import register_cli_commands

    register_cli_commands(app)

    # ---- 壳命令：flask shell 自动导入常用对象 ----
    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, Post, Category, UploadedFile
        return {"db": db, "User": User, "Post": Post, "Category": Category,
                "UploadedFile": UploadedFile}

    return app


def register_error_handlers(app: Flask) -> None:
    """注册统一的错误页面处理。"""

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/500.html"), 500
