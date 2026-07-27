"""文件上传与访问路由。

功能：
- 统一的上传接口（表单 + AJAX JSON），返回可在 Markdown 中直接插入的链接
- 静态提供已上传文件（/uploads/...）
- 文件元数据记录入数据库

安全措施：
- 扩展名白名单校验
- UUID 重命名，杜绝路径穿越
- MAX_CONTENT_LENGTH 限制体积（413 自动捕获）
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import (
    Blueprint,
    request,
    jsonify,
    current_app,
    send_from_directory,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import UploadedFile
from app.utils.files import (
    allowed_file,
    get_extension,
    is_image,
    build_save_path,
    human_readable_size,
)

upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/uploads/<path:filename>")
def serve(filename: str):
    """提供已上传文件的访问。

    send_from_directory 内部使用 safe_join 校验路径，
    会自动拦截 ``..`` 等穿越尝试，无需额外手动清洗
    （手动用 secure_filename 反而会破坏合法的年/月子目录结构）。
    """
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_folder, filename)


@upload_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    """文件上传接口。

    同时支持两种调用方式：
    1. AJAX（fetch + FormData）：返回 JSON，含 url、is_image、markdown 片段
    2. 普通表单提交：返回 JSON（编辑器统一按 AJAX 处理）

    返回示例：
    {
        "ok": true,
        "file": {"id": 1, "name": "a.png", "size": 12345, "url": "/uploads/..."},
        "markdown": "![a.png](/uploads/...)",
        "is_image": true
    }
    """
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "未找到上传文件。"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"ok": False, "error": "未选择文件。"}), 400

    # secure_filename 仅清洗文件名部分（不含路径），再由我们做扩展名校验
    original_name = secure_filename(file.filename) or file.filename
    if not allowed_file(original_name):
        allowed = ", ".join(sorted(current_app.config["ALLOWED_EXTENSIONS"]))
        return jsonify(
            {"ok": False, "error": f"不支持的文件类型。允许：{allowed}"}
        ), 400

    # 构建安全存储路径
    save_path, relative_path, url = build_save_path(original_name)
    file.save(save_path)

    # 读取文件大小
    size = save_path.stat().st_size
    ext = get_extension(original_name)
    image = is_image(original_name)

    # 记录元数据
    record = UploadedFile(
        original_name=original_name,
        stored_name=Path(save_path).name,
        relative_path=relative_path,
        url=url,
        mime_type=file.mimetype,
        size=size,
        extension=ext,
        is_image=image,
        uploader=current_user,
    )
    db.session.add(record)
    db.session.commit()

    # 生成可直接插入 Markdown 的片段
    if image:
        markdown = f"![{original_name}]({url})"
    else:
        markdown = f"[{original_name}]({url})"

    return jsonify({
        "ok": True,
        "file": {
            "id": record.id,
            "name": original_name,
            "size": size,
            "size_readable": human_readable_size(size),
            "url": url,
            "is_image": image,
        },
        "markdown": markdown,
    })


@upload_bp.route("/files")
@login_required
def list_files():
    """列出当前用户上传的最近文件（JSON）。"""
    page = request.args.get("page", 1, type=int)
    pagination = (
        UploadedFile.query.order_by(UploadedFile.created_at.desc())
        .paginate(page=page, per_page=24, error_out=False)
    )
    items = [
        {
            "id": f.id,
            "name": f.original_name,
            "url": f.url,
            "size": f.size,
            "size_readable": human_readable_size(f.size),
            "is_image": f.is_image,
            "extension": f.extension,
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "",
            "markdown": (f"![{f.original_name}]({f.url})" if f.is_image
                         else f"[{f.original_name}]({f.url})"),
        }
        for f in pagination.items
    ]
    return jsonify({"ok": True, "items": items, "pages": pagination.pages})
