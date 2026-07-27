"""Markdown 渲染与导出工具。

渲染使用 python-markdown + Pygments 代码高亮；
导出时生成带 frontmatter 的 .md 文件，便于在其他 Markdown 编辑器中复用。
"""

from __future__ import annotations

import markdown as md_lib
from flask import current_app


def render_markdown(text: str) -> str:
    """将 Markdown 文本渲染为 HTML。

    扩展与配置从 app.config 读取，保持与项目配置一致。
    """
    if not text:
        return ""
    extensions = current_app.config.get("MARKDOWN_EXTENSIONS", [])
    extension_configs = current_app.config.get("MARKDOWN_EXTENSION_CONFIGS", {})
    return md_lib.markdown(
        text,
        extensions=extensions,
        extension_configs=extension_configs,
        output_format="html5",
    )


def build_export_markdown(post) -> str:
    """为文章生成带 frontmatter 的完整 Markdown 文本，用于导出下载。

    :param post: Post 模型实例
    :return: 包含 frontmatter 的 Markdown 字符串
    """
    # frontmatter 元数据
    created = post.created_at.strftime("%Y-%m-%d %H:%M:%S") if post.created_at else ""
    updated = post.updated_at.strftime("%Y-%m-%d %H:%M:%S") if post.updated_at else ""
    category = post.category.name if post.category else "未分类"
    tags = ", ".join(post.tag_list)

    frontmatter_lines = [
        "---",
        f"title: {post.title}",
        f"category: {category}",
        f"date: {created}",
        f"updated: {updated}",
    ]
    if tags:
        frontmatter_lines.append(f"tags: [{tags}]")
    if post.summary:
        # 摘要中可能含冒号，用引号包裹更稳妥
        summary = post.summary.replace('"', '\\"')
        frontmatter_lines.append(f'summary: "{summary}"')
    frontmatter_lines.append("---")
    frontmatter_lines.append("")

    return "\n".join(frontmatter_lines) + (post.content_md or "")
