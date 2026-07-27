"""AI 助手路由：作为后端代理转发大模型请求。

所有第三方 API 调用都在此蓝图内完成，前端只与本应用通信，
从而避免 API Key 暴露在浏览器端。

预设动作：润色 / 生成摘要 / 续写，由 AI_ACTIONS 字典统一定义。
也支持自由对话（action=chat，带 messages）。
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from app.utils.ai_client import chat_complete, AI_ACTIONS, _resolve_provider

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/actions")
@login_required
def actions():
    """返回可用的 AI 动作列表（供前端渲染按钮）。"""
    return jsonify({
        "ok": True,
        "provider": current_app.config.get("AI_PROVIDER", "deepseek"),
        "items": [
            {"key": k, "label": v["label"]}
            for k, v in AI_ACTIONS.items()
        ],
    })


@ai_bp.route("/assist", methods=["POST"])
@login_required
def assist():
    """执行一个 AI 助手动作。

    请求 JSON：
    {
        "action": "polish" | "summary" | "continue" | "chat",
        "text": "正文内容（polish/summary/continue 需要）",
        "messages": [{"role":"user","content":"..."}],  // action=chat 时使用
        "provider": "deepseek" | "glm"  // 可选，覆盖默认服务商
    }
    """
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip()
    provider = data.get("provider")

    # 校验服务商配置是否就绪，给出友好提示
    try:
        _resolve_provider(provider)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    if action in AI_ACTIONS:
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "正文内容不能为空。"}), 400

        cfg = AI_ACTIONS[action]
        messages = [
            {"role": "system", "content": cfg["system_prompt"]},
            {"role": "user", "content": text},
        ]
        try:
            result = chat_complete(
                messages,
                provider=provider,
                temperature=cfg["temperature"],
            )
        except Exception as e:  # 大模型调用失败时返回可读错误
            return jsonify({"ok": False, "error": f"AI 调用失败：{e}"}), 502
        return jsonify({"ok": True, "action": action, "result": result})

    if action == "chat":
        messages = data.get("messages") or []
        if not messages:
            return jsonify({"ok": False, "error": "messages 不能为空。"}), 400
        try:
            result = chat_complete(messages, provider=provider)
        except Exception as e:
            return jsonify({"ok": False, "error": f"AI 调用失败：{e}"}), 502
        return jsonify({"ok": True, "action": "chat", "result": result})

    return jsonify({"ok": False, "error": f"未知的动作：{action}"}), 400
