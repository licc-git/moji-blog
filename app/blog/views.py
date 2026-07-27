"""博客核心路由：首页、详情、新建、编辑、删除、导出 Markdown。

权限策略：
- 列表与详情对游客公开（仅展示已发布文章）
- 新建、编辑、删除、导出需要登录
"""

from __future__ import annotations

from urllib.parse import quote

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
    request,
    jsonify,
    Response,
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.forms import PostForm
from app.models import Post, Category
from app.utils.markdown_utils import render_markdown, build_export_markdown

blog_bp = Blueprint("blog", __name__)


# ------------------------------------------------------------------
# 首页与列表
# ------------------------------------------------------------------
@blog_bp.route("/")
def index():
    """首页：卡片式展示最新笔记，支持分类 / 关键词 / 标签 / 年月筛选。"""
    page = request.args.get("page", 1, type=int)
    per_page = 9

    category_id = request.args.get("category", type=int)
    q = request.args.get("q", "", type=str).strip()
    tag = request.args.get("tag", "", type=str).strip()
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    query = Post.query.filter_by(is_published=True)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if q:
        # 在标题、摘要、正文、标签中搜索（摘要搜索即此 q 命中 summary）
        like = f"%{q}%"
        query = query.filter(
            or_(
                Post.title.like(like),
                Post.summary.like(like),
                Post.content_md.like(like),
                Post.tags.like(like),
            )
        )
    if tag:
        # 标签筛选：tags 字段逗号分隔，like 模糊匹配（数据量小可接受）
        query = query.filter(Post.tags.like(f"%{tag}%"))
    if year:
        query = query.filter(db.extract("year", Post.created_at) == year)
        if month:
            query = query.filter(db.extract("month", Post.created_at) == month)

    # 置顶优先，再按创建时间倒序
    query = query.order_by(Post.is_pinned.desc(), Post.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    categories = Category.query.order_by(Category.sort_order, Category.id).all()
    current_category = next((c for c in categories if c.id == category_id), None)

    # 标签云 + 月份归档（侧栏筛选入口）
    tag_cloud = _build_tag_cloud()
    archives = _build_archives()

    return render_template(
        "blog/index.html",
        posts=pagination.items,
        pagination=pagination,
        categories=categories,
        current_category=current_category,
        keyword=q,
        tag_cloud=tag_cloud,
        archives=archives,
        current_tag=tag,
        current_year=year,
        current_month=month,
    )


@blog_bp.route("/post/<int:post_id>")
@blog_bp.route("/post/<int:post_id>-<slug>")
def detail(post_id, slug=None):
    """文章详情页。"""
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)
    # 未发布文章仅作者可见
    if not post.is_published and not (current_user.is_authenticated and current_user.is_admin):
        abort(404)

    # 浏览数 +1（游客也计入）
    post.increment_view()
    db.session.commit()

    # 相关文章：同分类的其他已发布文章
    related = (
        Post.query.filter(
            Post.category_id == post.category_id,
            Post.id != post.id,
            Post.is_published == True,
        )
        .order_by(Post.created_at.desc())
        .limit(3)
        .all()
    )

    return render_template("blog/detail.html", post=post, related=related)


# ------------------------------------------------------------------
# 新建 / 编辑 / 删除（需登录）
# ------------------------------------------------------------------
@blog_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    """新建文章。"""
    form = PostForm()
    form.category_id.choices = _category_choices()

    if form.validate_on_submit():
        content_md = form.content_md.data
        post = Post(
            title=form.title.data.strip(),
            category_id=form.category_id.data,
            tags=form.tags.data.strip(),
            summary=form.summary.data.strip() or None,
            content_md=content_md,
            content_html=render_markdown(content_md),
            is_published=form.is_published.data,
            is_pinned=form.is_pinned.data,
            author=current_user,
        )
        db.session.add(post)
        db.session.commit()

        # AJAX 保存（Ctrl+S / 自动保存）：返回 JSON，前端不跳转
        if request.headers.get("Accept") == "application/json":
            edit_url = url_for("blog.edit", post_id=post.id)
            return jsonify({"ok": True, "post_id": post.id, "is_new": True, "redirect_url": edit_url})
        flash("文章已保存。", "success")
        # 普通提交：留在编辑页（而非跳转到详情页）
        return redirect(url_for("blog.edit", post_id=post.id))

    return render_template("blog/edit.html", form=form, mode="create")


@blog_bp.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit(post_id):
    """编辑文章。"""
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)

    form = PostForm()
    form.category_id.choices = _category_choices()

    if form.validate_on_submit():
        content_md = form.content_md.data
        post.title = form.title.data.strip()
        post.category_id = form.category_id.data
        post.tags = form.tags.data.strip()
        post.summary = form.summary.data.strip() or None
        post.content_md = content_md
        post.content_html = render_markdown(content_md)
        post.is_published = form.is_published.data
        post.is_pinned = form.is_pinned.data
        db.session.commit()

        # AJAX 保存（Ctrl+S / 自动保存）：返回 JSON，前端不跳转
        if request.headers.get("Accept") == "application/json":
            return jsonify({"ok": True, "post_id": post.id, "is_new": False})
        flash("修改已保存。", "success")
        # 普通提交：留在编辑页（而非跳转到详情页）
        return redirect(url_for("blog.edit", post_id=post.id))

    # GET 请求：回填表单
    if request.method == "GET":
        form.title.data = post.title
        form.category_id.data = post.category_id
        form.tags.data = post.tags
        form.summary.data = post.summary
        form.content_md.data = post.content_md
        form.is_published.data = post.is_published
        form.is_pinned.data = post.is_pinned

    return render_template("blog/edit.html", form=form, mode="edit", post=post)


@blog_bp.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete(post_id):
    """删除文章。"""
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)
    title = post.title
    db.session.delete(post)
    db.session.commit()
    flash(f"文章「{title}」已删除。", "info")
    return redirect(url_for("blog.index"))


@blog_bp.route("/categories/new", methods=["POST"])
@login_required
def new_category():
    """新建分类（编辑页内联 AJAX 调用）。

    返回 JSON：{ok, category:{id,name,description}} 或 {ok:false, error}。
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "分类名不能为空"}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({"ok": False, "error": f"分类「{name}」已存在"}), 400

    # sort_order 接在现有最大值之后，保证新分类排在末尾
    max_order = db.session.query(db.func.max(Category.sort_order)).scalar() or 0
    cat = Category(name=name, description=description or None, sort_order=max_order + 1)
    db.session.add(cat)
    db.session.commit()
    return jsonify({
        "ok": True,
        "category": {"id": cat.id, "name": cat.name, "description": cat.description or ""},
    })


# ------------------------------------------------------------------
# 导出 Markdown
# ------------------------------------------------------------------
@blog_bp.route("/post/<int:post_id>/export")
def export(post_id):
    """导出文章为带 frontmatter 的 .md 文件。"""
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)
    if not post.is_published and not (current_user.is_authenticated and current_user.is_admin):
        abort(404)

    md_text = build_export_markdown(post)

    # 构造下载文件名：同时提供 ASCII 兜底与 UTF-8 名称（RFC 5987），
    # 避免 HTTP 头以 latin-1 编码中文时崩溃。
    ascii_fallback = "".join(
        c for c in post.title if (c.isascii() and (c.isalnum() or c in "_-"))
    ).strip() or "post"
    utf8_name = f"{post.title.strip() or 'post'}.md"

    return Response(
        md_text,
        mimetype="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{ascii_fallback}.md\"; "
                f"filename*=UTF-8''{quote(utf8_name, safe='')}"
            )
        },
    )


# ------------------------------------------------------------------
# Markdown 实时预览接口（供编辑页前端调用）
# ------------------------------------------------------------------
@blog_bp.route("/preview", methods=["POST"])
@login_required
def preview():
    """将提交的 Markdown 渲染为 HTML，用于编辑页实时预览。"""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    return jsonify({"html": render_markdown(text)})


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------
def _category_choices() -> list[tuple[int, str]]:
    """构造分类下拉选项。"""
    cats = Category.query.order_by(Category.sort_order, Category.id).all()
    return [(c.id, c.name) for c in cats]


def _build_tag_cloud() -> list[dict]:
    """聚合所有已发布文章的标签，返回 [{tag, count}]，按计数降序，最多 30 个。"""
    from collections import Counter

    counter: Counter[str] = Counter()
    rows = Post.query.filter_by(is_published=True).with_entities(Post.tags).all()
    for (tags_str,) in rows:
        if not tags_str:
            continue
        for t in tags_str.split(","):
            t = t.strip()
            if t:
                counter[t] += 1
    return [{"tag": t, "count": c} for t, c in counter.most_common(30)]


def _build_archives() -> list[dict]:
    """按年月聚合已发布文章数，返回 [{year, month, count}]，倒序。"""
    rows = (
        db.session.query(
            db.extract("year", Post.created_at).label("y"),
            db.extract("month", Post.created_at).label("m"),
            db.func.count(Post.id).label("c"),
        )
        .filter(Post.is_published.is_(True))
        .group_by("y", "m")
        .order_by(db.text("y DESC, m DESC"))
        .all()
    )
    return [{"year": int(r.y), "month": int(r.m), "count": int(r.c)} for r in rows]
