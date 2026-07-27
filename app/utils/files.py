"""文件处理工具：扩展名校验、安全重命名、按日期分目录存储。"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import current_app


# 常见图片扩展名（小写）
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"}


def allowed_file(filename: str) -> bool:
    """判断文件名扩展名是否在允许列表内。"""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def get_extension(filename: str) -> str:
    """获取文件扩展名（小写，不带点）。无扩展名返回空串。"""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def is_image(filename: str) -> bool:
    """判断是否为图片类型。"""
    return get_extension(filename) in IMAGE_EXTENSIONS


def generate_stored_name(filename: str) -> str:
    """生成安全的存储文件名。

    使用 UUID4 + 原扩展名，既避免冲突又防止路径穿越攻击
    （攻击者构造的 `../../etc/passwd` 之类的名字会被完全替换）。
    """
    ext = get_extension(filename)
    base = uuid.uuid4().hex
    return f"{base}.{ext}" if ext else base


def build_save_path(filename: str) -> tuple[Path, str, str]:
    """为上传文件构建完整的保存路径与访问 URL。

    按年/月子目录组织，避免单目录文件过多影响性能。

    :return: (绝对保存路径, 相对 uploads 的子路径, 访问 URL)
    """
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    now = datetime.utcnow()
    subdir = os.path.join("images" if is_image(filename) else "files",
                          f"{now.year}", f"{now.month:02d}")

    save_dir = upload_root / subdir
    save_dir.mkdir(parents=True, exist_ok=True)

    stored_name = generate_stored_name(filename)
    save_path = save_dir / stored_name

    # 相对 uploads 目录的路径（用于数据库记录）
    relative_path = os.path.join(subdir, stored_name).replace("\\", "/")
    # 访问 URL（upload 蓝图 serve 路由负责提供文件）
    url = f"/uploads/{relative_path}"

    return save_path, relative_path, url


def human_readable_size(size_bytes: int) -> str:
    """将字节数转为人类可读的字符串。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    units = ["KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    for unit in units:
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PB"
