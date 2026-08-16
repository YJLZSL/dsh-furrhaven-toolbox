"""多平台导出器：FD / FC / FB / SillyTavern(V2+V3 PNG) / RisuAI / 类脑。

全部从 IR（model.Card）派生。平台产物永远不是编辑源。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .model import Card, Component


def _json_dump(obj: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    # 复验（平台 JSON 只许脚本读写 + 写回必复验的铁律）
    with open(path, encoding="utf-8") as f:
        json.load(f)
    return path


# ── FD ───────────────────────────────────────────────────────────────────────
def fd_card(card: Card, components: list[Component] | None = None) -> dict[str, Any]:
    """FD 平台 V3 JSON（自由模式口径）。"""
    comps = [c for c in (components or [])]
    next_id = int(time.time() * 1000)
    used_ids: set[int] = set()
    world_info: list[dict[str, Any]] = []
    for e in card.worldbook:
        eid = int(e.id) if str(e.id).isdigit() else next_id
        if eid in used_ids:
            next_id += 1
            eid = next_id
        used_ids.add(eid)
        next_id = max(next_id, eid + 1)
        world_info.append(e.to_fd(eid))
    lorebook_config = {
        "scan_depth": int(card.lorebook.get("scan_depth", 2) or 2),
        "recursive_scanning": bool(card.lorebook.get("recursive_scanning", True)),
        "max_recursion_depth": int(card.lorebook.get("max_recursion_depth", 1) or 1),
        "token_budget": int(card.lorebook.get("token_budget", 0) or 0),
    }
    out: dict[str, Any] = {
        "name": card.title or card.name,
        "avatar": "",
        "cover_image": "",
        "portrait": "",
        "image_copyright": "",
        "image_author": "",
        "char_copyright": "",
        "char_author": "",
        "personality": card.personality,
        "scenario": card.scenario if card.type != "character" else "",
        "world_view": card.world_view if card.type != "character" else "",
        "first_mes": card.first_mes,
        "mes_example": card.mes_example,
        "response_format": card.response_format,
        "creator_notes": card.creator_notes,
        "character_name": card.name,
        "category": card.category or "其他",
        "related_characters": [],
        "bgm_list": [],
        "world_info": world_info,
        "regex_scripts": [],
        "quick_replies": [q.to_fd() for q in card.quick_replies],
        "vn_mode_enabled": False,
        "vn_assets": {},
        "vn_settings": {},
        "lorebook_config": lorebook_config,
        "materials": [],
        "components": [c.to_fd(card.component_theme) for c in comps],
        "description": card.description,
        "title": card.title or card.name,
        "species": card.species,
        "age": card.age,
        "occupation": card.occupation,
        "version": card.character_version,
        "emotional_arc": card.emotional_arc,
        "emotional_development_nodes": card.emotional_development_nodes,
        "interactive_components": {},
        "lorebook_entries": world_info,
    }
    # 自由模式：scenario / world_view 并入 personality 三区（内容已在模板完成，不重复拼接）
    return out


# ── FC ───────────────────────────────────────────────────────────────────────
def fc_markdown(card: Card) -> str:
    """FC 角色卡 md（平台卡体）。"""
    parts: list[str] = []
    if card.title:
        parts.append(f"# {card.title}\n")
    if card.name:
        parts.append(f"## 角色名\n{card.name}\n")
    if card.description:
        parts.append(f"## 角色简介\n{card.description}\n")
    if card.personality:
        parts.append(f"## 性格设定\n{card.personality}\n")
    if card.scenario:
        parts.append(f"## 场景设定\n{card.scenario}\n")
    if card.world_view:
        parts.append(f"## 世界观\n{card.world_view}\n")
    if card.mes_example:
        parts.append(f"## 对话示例\n{card.mes_example}\n")
    if card.creator_notes:
        parts.append(f"## 创作者备注\n{card.creator_notes}\n")
    return "\n".join(parts).rstrip() + "\n"


def fc_regex_markdown(card: Card) -> str:
    rules = sorted(card.regex_rules, key=lambda r: r.order)
    lines = ["# 正则脚本 — Furrhaven 导出", ""]
    for r in rules:
        state = "启用" if r.enabled else "禁用"
        lines += [f"## {r.order}. {r.name}（{state}）", "",
                  f"- 查找：`{r.find}`", f"- 替换为：`{r.replace}`",
                  f"- 匹配选项：`{''.join(r.flags)}`", f"- 作用范围：仅 AI 回复", ""]
    return "\n".join(lines).rstrip() + "\n"


def fc_pack(card: Card, dist_root: Path) -> dict[str, Path]:
    """FC 上传资料包 8 目录结构。"""
    pack = dist_root / "fc" / f"{card.slug}-fc-pack"
    sub = {
        "01-角色卡": (f"{card.name}.md", fc_markdown(card)),
        "02-开场白": (f"{card.name}_开场白.md", (card.first_mes or "").rstrip() + "\n"),
        "03-角色简介": (f"{card.name}_简介.md", (card.description or "").rstrip() + "\n"),
        "04-世界书": (f"{card.name}_世界书.md", _fc_worldbook_md(card)),
        "05-正则脚本": (f"{card.name}_正则.md", fc_regex_markdown(card)),
        "06-回复格式": (f"{card.name}_回复格式.md", (card.response_format or "").rstrip() + "\n"),
        "07-角色故事线名称": (f"{card.name}_故事线.txt", f"{card.title or card.name}\n"),
    }
    written: dict[str, Path] = {}
    for dirname, (fname, content) in sub.items():
        d = pack / dirname
        d.mkdir(parents=True, exist_ok=True)
        p = d / fname
        p.write_text(content, encoding="utf-8", newline="\n")
        written[dirname] = p
    # 08-JSON导入文件：用 FD 结构 JSON 作 FC 导入源（平台兼容）
    d = pack / "08-JSON导入文件"
    d.mkdir(parents=True, exist_ok=True)
    p = _json_dump(fd_card(card, components=[]), d / f"{card.name}.json")
    written["08-JSON导入文件"] = p
    return written


def _fc_worldbook_md(card: Card) -> str:
    if not card.worldbook:
        return "# 世界书\n\n（无条目）\n"
    lines = ["# 世界书", ""]
    for e in card.worldbook:
        lines += [f"## {e.name or e.trigger_keys_text()}",
                  f"- 触发词：{e.trigger_keys_text()}", "", e.content.strip(), ""]
    return "\n".join(lines).rstrip() + "\n"


# ── FB ───────────────────────────────────────────────────────────────────────
def fb_markdown(card: Card) -> str:
    """FB 卡：精简 md（引用去重结构见世界书区块）。"""
    parts: list[str] = []
    if card.name:
        parts.append(f"# {card.name}\n")
    if card.title and card.title != card.name:
        parts.append(f"> {card.title}\n")
    if card.description:
        parts.append(f"## 简介\n{card.description}\n")
    if card.personality:
        parts.append(f"## 设定\n{card.personality}\n")
    if card.scenario:
        parts.append(f"## 场景\n{card.scenario}\n")
    if card.world_view:
        parts.append(f"## 世界观\n{card.world_view}\n")
    if card.worldbook:
        parts.append("## 设定详条\n")
        for e in card.worldbook:
            parts.append(f"### {e.name or e.trigger_keys_text()}\n{e.content.strip()}\n")
    if card.first_mes:
        parts.append(f"## 开场\n{card.first_mes}\n")
    if card.mes_example:
        parts.append(f"## 示例\n{card.mes_example}\n")
    return "\n".join(parts).rstrip() + "\n"


# ── SillyTavern / RisuAI V2 V3 ──────────────────────────────────────────────
def st_v2(card: Card) -> dict[str, Any]:
    now = int(time.time())
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": card.name,
            "description": card.description,
            "personality": card.personality,
            "scenario": card.scenario,
            "first_mes": card.first_mes,
            "mes_example": card.mes_example,
            "creator_notes": card.creator_notes,
            "system_prompt": card.system_prompt,
            "post_history_instructions": card.post_history_instructions,
            "alternate_greetings": list(card.alternate_greetings),
            "character_book": _st_character_book(card, v3=False),
            "tags": list(card.tags),
            "creator": card.creator,
            "character_version": card.character_version,
            "extensions": _st_extensions(card, now),
        },
    }


def st_v3(card: Card) -> dict[str, Any]:
    now = int(time.time())
    assets = list(card.assets) or [{"type": "icon", "uri": "ccdefault:", "name": "main", "ext": "png"}]
    return {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "name": card.name,
            "nickname": card.nickname or card.name,
            "description": card.description,
            "personality": card.personality,
            "scenario": card.scenario,
            "first_mes": card.first_mes,
            "mes_example": card.mes_example,
            "creator_notes": card.creator_notes,
            "system_prompt": card.system_prompt,
            "post_history_instructions": card.post_history_instructions,
            "alternate_greetings": list(card.alternate_greetings),
            "group_only_greetings": list(card.group_only_greetings),
            "character_book": _st_character_book(card, v3=True),
            "tags": list(card.tags),
            "creator": card.creator,
            "character_version": card.character_version,
            "extensions": _st_extensions(card, now),
            "assets": assets,
            "creation_date": card.creation_date or now,
            "modification_date": now,
            "source": ["furrhaven-toolbox"],
        },
    }


def _st_character_book(card: Card, v3: bool) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for i, e in enumerate(card.worldbook):
        item = e.to_st()
        if not v3:
            item.pop("use_regex", None)
        item["insertion_order"] = i
        entries.append(item)
    return {
        "name": f"{card.name} 世界书",
        "description": card.lorebook.get("description", "") if isinstance(card.lorebook, dict) else "",
        "scan_depth": int(card.lorebook.get("scan_depth", 2) or 2) if isinstance(card.lorebook, dict) else 2,
        "token_budget": int(card.lorebook.get("token_budget", 0) or 0) if isinstance(card.lorebook, dict) else 0,
        "recursive_scanning": bool(card.lorebook.get("recursive_scanning", True)) if isinstance(card.lorebook, dict) else True,
        "extensions": {},
        "entries": entries,
    }


def _st_extensions(card: Card, now: int) -> dict[str, Any]:
    """扩展位：组件 / 正则 / 回复格式 随卡走（不破坏未知扩展）。"""
    fh = {
        "type": card.type,
        "title": card.title or card.name,
        "response_format": card.response_format,
        "world_view": card.world_view,
        "category": card.category,
        "component_set": card.component_set,
        "component_theme": card.component_theme or {},
        "components": [c.to_st_extension() if isinstance(c, Component) else {"name": c} for c in card.components],
        "regex_rules": [r.__dict__ for r in card.regex_rules],
        "quick_replies": [q.to_fd() for q in card.quick_replies],
        "exported_at": now,
    }
    ext = dict(card.extensions or {})
    ext["furrhaven"] = fh
    return ext


def st_regex_json(card: Card) -> list[dict[str, Any]]:
    """ST regex 脚本 JSON（findRegex/ replaceString / trimStrings / placement）。"""
    out = []
    for r in sorted([x for x in card.regex_rules if x.enabled], key=lambda x: x.order):
        flags = "".join(r.flags).replace("s", "").replace("m", "")
        out.append({
            "id": r.id,
            "scriptName": r.name or r.id,
            "findRegex": r.find,
            "replaceString": r.replace,
            "trimStrings": [],
            "placement": [1] if r.scope == "ai_reply" else [0],
            "disabled": False,
            "markdownOnly": False,
            "promptOnly": False,
            "runOnEdit": False,
            "substituteRegex": 0,
            "minDepth": None,
            "maxDepth": None,
        })
        _ = flags  # ST 方言标志由 JS 内联，YAML flags 仅作文档
    return out


# ── 统一导出入口 ─────────────────────────────────────────────────────────────
def export_card(
    card: Card,
    platform: str,
    dist_root: Path,
    components: list[Component] | None = None,
    avatar_path: Path | None = None,
) -> dict[str, Path]:
    """导出单卡到 dist/<platform>/。返回产物路径表。"""
    dist_root = Path(dist_root)
    if platform == "fd":
        d = dist_root / "fd"
        p = _json_dump(fd_card(card, components), d / f"角色卡_{card.name}_V3.json")
        return {"card": p}
    if platform == "fc":
        return fc_pack(card, dist_root)
    if platform == "fb":
        d = dist_root / "fb"
        p = d / f"{card.name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(fb_markdown(card), encoding="utf-8", newline="\n")
        return {"card": p}
    if platform == "st":
        d = dist_root / "st"
        v2_json = _json_dump(st_v2(card), d / f"{card.slug}.v2.json")
        v3_json = _json_dump(st_v3(card), d / f"{card.slug}.v3.json")
        avatar = avatar_path or (Path(card.source_path.parent if card.source_path else Path.cwd()) / card.avatar if card.avatar else None)
        v2_png = d / f"{card.slug}.v2.png"
        v3_png = d / f"{card.slug}.v3.png"
        from .png import write_card_png
        write_card_png(st_v2(card), v2_png, avatar, include_v2=True, include_v3=False)
        write_card_png(st_v3(card), v3_png, avatar, include_v2=False, include_v3=True)
        regex_path = _json_dump(st_regex_json(card), d / f"{card.slug}.regex.json")
        return {"v2_json": v2_json, "v3_json": v3_json, "v2_png": v2_png, "v3_png": v3_png, "regex_json": regex_path}
    if platform in ("risu", "leinao"):
        d = dist_root / platform
        p = _json_dump(st_v3(card), d / f"{card.slug}.v3.json")
        return {"v3_json": p}
    raise ValueError(f"不支持的平台：{platform}")
