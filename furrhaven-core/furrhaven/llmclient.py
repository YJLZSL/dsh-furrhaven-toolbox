"""极简 OpenAI 兼容 LLM 客户端（纯标准库，引擎可独立跑识图/扮演模式）。"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class LLMError(RuntimeError):
    pass


def chat_completion(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 1.0,
    max_tokens: int = 2048,
    timeout: int = 300,
) -> str:
    if not api_base or not model:
        raise LLMError(
            "未配置模型接口：在 fh.config.yaml 填 play/vision 的 api_base·api_key·model，"
            "或用环境变量 FH_LLM_API_BASE / FH_LLM_API_KEY / FH_LLM_MODEL"
        )
    url = api_base.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:500]
        except Exception:
            pass
        raise LLMError(f"模型接口 HTTP {e.code}：{detail}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"模型接口不可达：{e.reason}") from e
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"模型接口返回结构异常：{json.dumps(data, ensure_ascii=False)[:500]}") from e


def resolve_llm_cfg(project, section: str) -> dict[str, Any]:
    """fh.config.yaml 优先，环境变量 FH_LLM_* 其次。"""
    import os
    cfg: dict[str, Any] = {}
    if project is not None:
        cfg.update(project.config.get(section, {}) or {})
    env_base = os.environ.get("FH_LLM_API_BASE", "")
    env_key = os.environ.get("FH_LLM_API_KEY", "")
    env_model = os.environ.get("FH_LLM_MODEL", "")
    if not cfg.get("api_base"):
        cfg["api_base"] = env_base
    if not cfg.get("api_key"):
        cfg["api_key"] = env_key
    if not cfg.get("model"):
        cfg["model"] = env_model
    return cfg
