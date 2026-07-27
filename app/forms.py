"""WTForms 表单定义。

使用 Flask-WTF 提供表单验证与 CSRF 保护。
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    BooleanField,
    SelectField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, Optional, Email

from app.config import Config


class LoginForm(FlaskForm):
    """管理员登录表单。"""

    username = StringField(
        "用户名",
        validators=[DataRequired(message="请输入用户名"), Length(1, 64)],
        render_kw={"placeholder": "用户名", "autofocus": True},
    )
    password = PasswordField(
        "密码",
        validators=[DataRequired(message="请输入密码"), Length(1, 128)],
        render_kw={"placeholder": "密码"},
    )
    remember = BooleanField("记住我（7天）")
    submit = SubmitField("登录")


class PostForm(FlaskForm):
    """文章编辑表单。"""

    title = StringField(
        "标题",
        validators=[DataRequired(message="请输入标题"), Length(1, 200)],
        render_kw={"placeholder": "给这篇笔记起个标题…"},
    )
    category_id = SelectField(
        "分类",
        coerce=int,
        validators=[DataRequired(message="请选择分类")],
    )
    tags = StringField(
        "标签",
        validators=[Optional(), Length(0, 256)],
        render_kw={"placeholder": "用逗号分隔多个标签，如：Python, Flask"},
    )
    summary = TextAreaField(
        "摘要",
        validators=[Optional(), Length(0, 500)],
        render_kw={"placeholder": "一句话概括（可留空，也可用 AI 生成）", "rows": 1},
    )
    content_md = TextAreaField(
        "正文（Markdown）",
        validators=[DataRequired(message="正文不能为空")],
        render_kw={"placeholder": "在此输入 Markdown 内容…", "rows": 20},
    )
    is_published = BooleanField("发布", default=True)
    is_pinned = BooleanField("置顶", default=False)
    submit = SubmitField("保存")


class CategoryForm(FlaskForm):
    """新建分类表单（编辑页内联调用）。"""

    name = StringField(
        "分类名称",
        validators=[DataRequired(message="请输入分类名"), Length(1, 64)],
        render_kw={"placeholder": "如：算法笔记", "autofocus": True},
    )
    description = StringField(
        "描述",
        validators=[Optional(), Length(0, 256)],
        render_kw={"placeholder": "可选，一句话描述这个分类"},
    )
    submit = SubmitField("添加")


class UploadForm(FlaskForm):
    """文件上传表单。

    通过 FileAllowed 动态读取允许的扩展名列表。
    """

    file = FileField(
        "选择文件",
        validators=[
            FileRequired(message="请选择文件"),
            FileAllowed(
                list(Config.ALLOWED_EXTENSIONS),
                message="不支持的文件类型。",
            ),
        ],
    )
    submit = SubmitField("上传")
