"""AI 大模型代理客户端。

通过 OpenAI SDK 兼容接口同时支持 DeepSeek 与智谱 GLM，
统一封装为 `chat_complete()`，使上层路由无需关心服务商差异。
API Key 仅在服务端使用，前端通过 Flask 路由代理转发，保护密钥安全。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from flask import current_app
from openai import OpenAI


@dataclass
class ProviderConfig:
    """单个 AI 服务商的配置。"""

    name: str
    api_key: str
    base_url: str
    model: str


def _resolve_provider(provider: str | None = None) -> ProviderConfig:
    """根据 provider 名称解析出对应的配置。

    :param provider: 'deepseek' / 'glm'，为空时读取默认 AI_PROVIDER
    :raises ValueError: provider 非法或未配置 API Key
    """
    cfg = current_app.config
    name = (provider or cfg.get("AI_PROVIDER", "deepseek")).lower()

    if name == "deepseek":
        api_key = cfg.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("DeepSeek API Key 未配置，请在 .env 中设置 DEEPSEEK_API_KEY。")
        return ProviderConfig(
            name="deepseek",
            api_key=api_key,
            base_url=cfg.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            model=cfg.get("DEEPSEEK_MODEL", "deepseek-chat"),
        )

    if name == "glm":
        api_key = cfg.get("GLM_API_KEY", "")
        if not api_key:
            raise ValueError("GLM API Key 未配置，请在 .env 中设置 GLM_API_KEY。")
        return ProviderConfig(
            name="glm",
            api_key=api_key,
            base_url=cfg.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
            model=cfg.get("GLM_MODEL", "glm-4-flash"),
        )

    raise ValueError(f"不支持的 AI 服务商：{name}（仅支持 deepseek / glm）")


def chat_complete(
    messages: Iterable[dict],
    *,
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    """调用大模型并返回纯文本结果。

    :param messages: OpenAI 消息格式 [{"role": ..., "content": ...}, ...]
    :param provider: 指定服务商，默认使用配置中的 AI_PROVIDER
    :param model: 指定模型，默认使用服务商配置中的模型
    :param temperature: 采样温度
    :param max_tokens: 最大输出 token 数
    :return: 模型回复的文本内容
    """
    pc = _resolve_provider(provider)
    client = OpenAI(api_key=pc.api_key, base_url=pc.base_url)

    kwargs = {
        "model": model or pc.model,
        "messages": list(messages),
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


# ------------------------------------------------------------------
# 预设的 AI 助手「动作」：润色、摘要、续写
# 每个动作对应一组系统提示词与温度参数，前端按钮直接调用。
# ------------------------------------------------------------------
AI_ACTIONS: dict[str, dict] = {
    "polish": {
        "label": "润色文章",
        "system_prompt": (
            "你是一位资深的中文写作编辑。请对用户提供的 Markdown 文章进行润色："
            "修正错别字与语病，优化句式与段落衔接，提升表达的流畅度与准确性，"
            "但不要改变原文的核心观点与结构。保留原有的 Markdown 语法与代码块，"
            "直接输出润色后的完整 Markdown 正文，不要添加任何解释性文字。"
        ),
        "temperature": 0.5,
    },
    "summary": {
        "label": "生成摘要",
        "system_prompt": (
            "你是一位内容编辑助手。请为用户提供的 Markdown 文章生成一段 80-150 字的中文摘要，"
            "概括文章的核心内容与要点。只输出摘要正文，不要包含「摘要：」之类的前缀，"
            "不要使用 Markdown 标记。"
        ),
        "temperature": 0.3,
    },
    "continue": {
        "label": "续写",
        "system_prompt": (
            "你是一位善于延续作者风格的写作助手。请根据用户提供的 Markdown 文章，"
            "顺其思路自然续写一段内容，保持语气、视角与主题一致。"
            "直接输出续写部分的 Markdown 正文，不要重复原文，不要添加解释性文字。"
        ),
        "temperature": 0.8,
    },
}
