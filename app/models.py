"""数据模型定义。

包含四个核心模型：
- User：管理员账户（单用户，Flask-Login 用户载体）
- Category：笔记分类（「学习笔记」「日常随笔」等）
- Post：博客文章（Markdown 原文 + 渲染缓存 + 元数据）
- UploadedFile：上传文件元数据记录
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


# ------------------------------------------------------------------
# 分类常量：预设的两个顶级分类，便于在初始化时预置
# ------------------------------------------------------------------
CATEGORY_STUDY = "学习笔记"
CATEGORY_DAILY = "日常随笔"
# 预置分类：sort_order 越小越靠前。用户也可在编辑页内联新建。
DEFAULT_CATEGORIES = [
    {"name": "学习笔记", "description": "编程、数学等技术学习笔记", "sort_order": 1},
    {"name": "编程开发", "description": "语言、框架、工程实践", "sort_order": 2},
    {"name": "数学算法", "description": "数学推导、算法与数据结构", "sort_order": 3},
    {"name": "读书笔记", "description": "技术书与闲书的阅读摘抄", "sort_order": 4},
    {"name": "日常随笔", "description": "工作经历、项目经历、风景评价等日常随笔", "sort_order": 5},
    {"name": "工作项目", "description": "工作记录与项目复盘", "sort_order": 6},
    {"name": "风光游记", "description": "旅行风景与地点评价", "sort_order": 7},
    {"name": "杂感随笔", "description": "零散想法与生活感悟", "sort_order": 8},
]


class User(UserMixin, db.Model):
    """管理员账户模型。

    单用户博客系统不需要注册功能，仅通过 CLI 命令 `flask init-admin` 创建。
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(64))
    is_admin = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # 关联：用户上传的文件与文章
    posts = db.relationship("Post", backref="author", lazy="dynamic")
    files = db.relationship("UploadedFile", backref="uploader", lazy="dynamic")

    # ---- 密码处理：只存哈希，永不存明文 ----
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Flask-Login 用户加载回调。"""
    return db.session.get(User, int(user_id))


class Category(db.Model):
    """笔记分类。"""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.String(256))
    # 排序权重，数值越小越靠前
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    posts = db.relationship("Post", backref="category", lazy="dynamic")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category {self.name}>"

    @property
    def post_count(self) -> int:
        return self.posts.filter_by(is_published=True).count()


class Post(db.Model):
    """博客文章模型。

    同时保存 Markdown 原文与渲染后的 HTML，
    避免每次请求都重新渲染（写作频率远低于阅读频率）。
    """

    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    # URL 友好的短标识，用于美化详情页 URL
    slug = db.Column(db.String(200), unique=True, index=True)
    summary = db.Column(db.String(500))  # 摘要，可由 AI 生成
    content_md = db.Column(db.Text, nullable=False)          # Markdown 原文
    content_html = db.Column(db.Text)                        # 渲染缓存
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)  # 是否置顶

    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True
    )
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    # 标签：用简单字符串存储，逗号分隔，避免引入关联表的复杂度
    tags = db.Column(db.String(256), default="")

    view_count = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Post {self.id}: {self.title}>"

    @property
    def tag_list(self) -> list[str]:
        """将逗号分隔的标签字符串拆分为列表。"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def increment_view(self) -> None:
        """浏览数自增（避免在 Python 端读改写造成的并发问题）。"""
        self.view_count = (self.view_count or 0) + 1


class UploadedFile(db.Model):
    """上传文件的元数据记录。

    实际文件存储在本地 uploads 目录，数据库仅记录元信息，
    便于在后台管理与 Markdown 中引用。
    """

    __tablename__ = "uploaded_files"

    id = db.Column(db.Integer, primary_key=True)
    # 原始文件名（用户上传时的名字）
    original_name = db.Column(db.String(255), nullable=False)
    # 重命名后存储在服务器上的文件名（防止冲突与路径穿越）
    stored_name = db.Column(db.String(255), unique=True, nullable=False)
    # 相对 uploads 目录的子路径，如 "images/2026/07/abc.png"
    relative_path = db.Column(db.String(512), nullable=False)
    # 访问 URL，如 /uploads/images/2026/07/abc.png
    url = db.Column(db.String(512), nullable=False)
    mime_type = db.Column(db.String(128))
    size = db.Column(db.BigInteger, nullable=False)  # 字节数
    # 扩展名（小写，不带点）
    extension = db.Column(db.String(16), index=True)
    is_image = db.Column(db.Boolean, default=False, nullable=False)

    uploader_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UploadedFile {self.id}: {self.original_name}>"
