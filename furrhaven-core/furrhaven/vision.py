"""识图模式：用视觉模型读立绘/参考图/平台截图，产出外貌描述与排查线索。

用法：
  fh vision <图片>                  # 通用描述
  fh vision <图片> --card <slug>    # 把外貌描述写入 assets/<slug>_appearance.md
  fh vision <截图> --mode ui        # 平台截图排查：组件是否渲染/高度/色调
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from .llmclient import chat_completion, resolve_llm_cfg

VISION_PROMPT = (
    "你是角色卡立绘识图助手。请输出可直接写进角色卡的外貌描述：物种/性别呈现、"
    "毛色或发色、瞳色、体型、服装、配饰、标志物、气质、以及与常见描述冲突的细节。"
    "只写看到的事实，不编造。用中文，分条列出。"
)

UI_PROMPT = (
    "你是角色卡平台截图排查助手。请检查：①组件面板是否渲染（不是扁平无样式）；"
    "②顶部/底部是否有异常空白；③选项按钮是否可见可点；④色调/边框/天气/进度条状态；"
    "⑤参数是否显示为 -- 或 $xxx$（未替换）。逐项给结论：正常/异常+证据。"
)


def describe_image(path: str | Path, prompt: str | None = None, project=None) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    cfg = resolve_llm_cfg(project, "vision")
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    if mime not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        mime = "image/png"
    data_url = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt or VISION_PROMPT},
            {"type": "image_url", "image_url": {"url": data_url}},
        ],
    }]
    return chat_completion(cfg["api_base"], cfg["api_key"], cfg["model"], messages,
                           temperature=0.7, max_tokens=1024)


def vision_to_card(path: str | Path, project, prompt: str | None = None) -> tuple[str, Path]:
    text = describe_image(path, prompt, project)
    assets = project.assets_dir
    assets.mkdir(parents=True, exist_ok=True)
    out = assets / f"{Path(path).stem}_appearance.md"
    out.write_text(
        f"# 识图笔记（{Path(path).name}）\n\n> 由 `fh vision` 生成，供创作参考，非权威源。\n\n{text.strip()}\n",
        encoding="utf-8", newline="\n")
    return text, out
