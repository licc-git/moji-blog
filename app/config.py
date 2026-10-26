"""应用配置模块。

采用「开发/生产配置分离」的设计：
- Config：基类，存放所有环境通用的配置项
- DevelopmentConfig：开发环境（默认开启 DEBUG）
- ProductionConfig：生产环境（关闭 DEBUG，强化安全）
- TestingConfig：测试环境（使用内存数据库）

通过环境变量 FLASK_ENV 或环境变量直接覆盖各项配置。
"""

import os
from pathlib import Path

# 项目根目录：app/config.py 的父目录的父目录
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """基础配置，所有环境共享。"""

    # ===== Flask 核心 =====
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key")

    # ===== 数据库 =====
    # 默认使用本地 MySQL，可通过 DATABASE_URL 环境变量覆盖
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://bloguser:blogpass@localhost:3306/my_blog?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # 连接前检测是否存活，避免长连接断开报错
        "pool_recycle": 280,    # MySQL 默认 wait_timeout 28800s，提前回收
    }

    # ===== 文件上传 =====
    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.environ.get("UPLOAD_FOLDER", "uploads"))
    # 允许的文件扩展名（小写，不带点）
    ALLOWED_EXTENSIONS = {
        # 图片
        "jpg", "jpeg", "png", "gif", "webp", "svg", "bmp",
        # 文档
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        # 压缩包与其他
        "zip", "rar", "7z", "tar", "gz",
        # 文本/代码
        "txt", "md", "csv", "json", "yaml", "yml",
    }
    # 单文件最大体积，默认 16MB
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    # ===== 会话与 Cookie =====
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 天

    # ===== Markdown 渲染 =====
    MARKDOWN_EXTENSIONS = [
        "extra",        # tables, fenced_code, footnotes, attr_list 等
        "codehilite",   # 代码高亮（配合 Pygments）
        "toc",          # 自动生成目录
        "nl2br",        # 换行转 <br>
        "sane_lists",   # 更合理的列表解析
    ]
    MARKDOWN_EXTENSION_CONFIGS = {
        "codehilite": {
            "css_class": "highlight",
            "guess_lang": True,
            "linenums": False,
        },
        "toc": {
            "permalink": "¶",
        },
    }

    # ===== AI 大模型 =====
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "deepseek")
    AI_TIMEOUT = 60  # 单次请求超时（秒）

    # DeepSeek
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    # 智谱 GLM
    GLM_API_KEY = os.environ.get("GLM_API_KEY", "")
    GLM_BASE_URL = os.environ.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    GLM_MODEL = os.environ.get("GLM_MODEL", "glm-4-flash")

    # ===== 管理员账户（首次初始化时使用）=====
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-this-password")


class DevelopmentConfig(Config):
    """开发环境配置。"""

    DEBUG = True
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = False
    TEMPLATES_AUTO_RELOAD = True   # 改模板即时生效，无需重启


class ProductionConfig(Config):
    """生产环境配置。"""

    DEBUG = False
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() in ("1", "true", "yes")


class TestingConfig(Config):
    """测试环境配置。"""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


# 配置映射表：通过 FLASK_ENV 选择
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(env: str | None = None) -> type[Config]:
    """根据环境名称返回对应的配置类。"""
    env = env or os.environ.get("FLASK_ENV", "development")
    return config_map.get(env.lower(), config_map["default"])
