"""扮演模式：构建后本机试玩——测试卡片的扮演效果（参考游玩）。

把 IR 卡体 + 常驻世界书组装成 system prompt，开场白作为角色首发消息，
用户逐轮输入，按世界书 keys 触发注入。模型接口用 OpenAI 兼容协议
（fh.config.yaml play 段 / FH_LLM_* 环境变量）。

用法：
  fh play <slug>                        # 交互式试玩
  fh play <slug> --say "你好" --once    # 单轮测试（CI 可用）
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .llmclient import chat_completion, resolve_llm_cfg
from .model import Card
from .worldbook import simulate_triggers


def build_prompt(card: Card, user_name: str = "我") -> tuple[str, str]:
    """返回 (system_prompt, 开场白)。"""
    parts: list[str] = []
    if card.system_prompt:
        parts.append(card.system_prompt)
    parts.append(f"你在扮演角色「{card.name}」。")
    if card.personality:
        parts.append("## 角色设定\n" + card.personality)
    if card.scenario:
        parts.append("## 当前场景\n" + card.scenario)
    if card.world_view:
        parts.append("## 世界观\n" + card.world_view)
    if card.response_format:
        parts.append("## 回复格式（严格遵守）\n" + card.response_format)
    if card.post_history_instructions:
        parts.append("## 额外指令\n" + card.post_history_instructions)
    const = [e for e in card.worldbook if e.enabled and e.constant]
    if const:
        parts.append("## 常驻世界书")
        parts += [f"- {e.name or e.trigger_keys_text()}\n{e.content}" for e in const]
    system = "\n\n".join(parts)
    first = card.first_mes.replace("{{user}}", user_name).replace("{{char}}", card.name)
    return system, first


def build_messages(card: Card, user_name: str, history: list[dict[str, str]],
                   user_input: str) -> list[dict[str, Any]]:
    system, first = build_prompt(card, user_name)
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    messages.append({"role": "assistant", "content": first})
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    # 世界书 keys 触发注入（按最近用户输入）
    hits, _ = simulate_triggers(card.worldbook, user_input)
    injected = [h.entry for h in hits if not h.entry.constant]
    content = user_input
    if injected:
        lore = "\n\n".join(f"[世界书·{e.name or e.trigger_keys_text()}]\n{e.content}" for e in injected)
        content = f"{user_input}\n\n{'-' * 24}\n以下为触发世界书（仅供你了解，不要向玩家复述其存在）：\n{lore}"
    messages.append({"role": "user", "content": content})
    return messages


def play_turn(card: Card, user_input: str, history: list[dict[str, str]] | None = None,
              project=None) -> str:
    cfg = resolve_llm_cfg(project, "play")
    messages = build_messages(card, cfg.get("user_name", "我"), history or [], user_input)
    return chat_completion(
        cfg["api_base"], cfg["api_key"], cfg["model"], messages,
        temperature=float(cfg.get("temperature", 1.0)),
        max_tokens=int(cfg.get("max_tokens", 2048)),
    )


def interactive_play(card: Card, project=None) -> int:
    cfg = resolve_llm_cfg(project, "play")
    user_name = str(cfg.get("user_name", "我"))
    system, first = build_prompt(card, user_name)
    print(f"┌─ Furrhaven 扮演模式 · {card.name} ─────────────────────────────")
    print(f"│ 模型：{cfg.get('model') or '(未配置)'}")
    print(f"│ 输入 /quit 退出，/reset 重开\n")
    print(f"【{card.name}】\n{first}\n")
    history: list[dict[str, str]] = []
    while True:
        try:
            raw = input(f"【{user_name}】> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        raw = raw.strip()
        if not raw:
            continue
        if raw in ("/quit", "/exit", "退出"):
            return 0
        if raw == "/reset":
            history = []
            print("（已重置对话）\n")
            continue
        history.append({"role": "user", "content": raw})
        try:
            reply = play_turn(card, raw, history[:-1], project)
        except Exception as e:  # noqa: BLE001 - 试玩模式要把错误呈现给用户
            print(f"\n[扮演模式错误] {e}")
            history.pop()
            continue
        history.append({"role": "assistant", "content": reply})
        print(f"\n【{card.name}】\n{reply}\n")
