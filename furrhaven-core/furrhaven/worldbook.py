"""世界书工坊：条目 CRUD / keys 分析器 / 触发模拟器 / 预算。"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import Card, WorldBookEntry
from .parsers import entry_from_frontmatter, split_front_matter

# 泛词/单字黑名单（参考项目全流程文档 §四.3，题材中立的通用部分）
GENERIC_KEY_BLACKLIST = [
    "你", "我", "他", "她", "它", "车", "伞", "疤", "画", "老板", "教练", "同学",
    "老师", "朋友", "门", "窗", "路", "家", "学校", "公司", "手机", "电脑", "饭",
    "水", "雨", "雪", "风", "天", "地", "人", "钱", "书", "笔", "纸", "包", "灯",
]


@dataclass
class KeyWarning:
    entry: WorldBookEntry
    key: str
    reason: str


@dataclass
class TriggerHit:
    entry: WorldBookEntry
    matched_key: str
    via: str            # direct | constant | recursive
    depth: int = 0


def analyze_keys(entries: list[WorldBookEntry],
                 extra_blacklist: list[str] | None = None) -> list[KeyWarning]:
    black = set(GENERIC_KEY_BLACKLIST) | set(extra_blacklist or [])
    warnings: list[KeyWarning] = []
    seen: dict[str, str] = {}
    for e in entries:
        if not e.enabled:
            continue
        if e.constant:
            continue
        if not e.keys:
            warnings.append(KeyWarning(e, "", "条目没有触发词（非系统条目建议配 keys）"))
            continue
        for key in e.keys:
            if key in black:
                warnings.append(KeyWarning(e, key, "泛词/单字触发词，任何场景都会误触发"))
            if key in seen:
                warnings.append(KeyWarning(e, key, f"与「{seen[key]}」共用触发词，可能互抢"))
            else:
                seen[key] = e.name or str(e.id)
            if len(key) == 1:
                warnings.append(KeyWarning(e, key, "单字触发词误触发风险高"))
    # 覆盖度提示：正文关键概念未入 keys（简单启发式：正文首段名词短语）
    for e in entries:
        if e.constant or not e.content:
            continue
        first_line = e.content.splitlines()[0] if e.content.splitlines() else ""
        quoted = re.findall(r"[「『“]([^」』”]{2,8})[」』”]", first_line)
        for q in quoted[:3]:
            if q not in e.keys:
                warnings.append(KeyWarning(e, q, "正文高亮名词未进入 keys，可能漏触发"))
    return warnings


def simulate_triggers(entries: list[WorldBookEntry], user_text: str,
                      scan_depth: int = 2, recursive: bool = True,
                      max_recursion_depth: int = 1) -> tuple[list[TriggerHit], int]:
    """模拟平台触发：常数条目全注入；keys 命中注入；递归扫描 depth=1。"""
    hits: list[TriggerHit] = []
    seen_ids: set[int | str] = set()
    text = user_text or ""

    def add(entry: WorldBookEntry, key: str, via: str, depth: int) -> None:
        ident = entry.id if entry.id not in (0, "", None) else entry.content[:24]
        if ident in seen_ids or not entry.enabled:
            return
        seen_ids.add(ident)
        hits.append(TriggerHit(entry, key, via, depth))

    for e in entries:
        if e.constant and e.enabled:
            add(e, "(常驻)", "constant", 0)
    for e in entries:
        if e.constant or not e.enabled or not e.keys:
            continue
        for key in e.keys:
            if e.use_regex:
                try:
                    if re.search(key, text):
                        add(e, key, "direct", 0)
                        break
                except re.error:
                    continue
            elif key and key in text:
                add(e, key, "direct", 0)
                break
    if recursive:
        for _round in range(1, max_recursion_depth + 1):
            injected_text = "\n".join(h.entry.content for h in list(hits))
            new_hits: list[TriggerHit] = []
            for e in entries:
                if e.constant or not e.enabled or not e.keys:
                    continue
                ident = e.id if e.id not in (0, "", None) else e.content[:24]
                if ident in seen_ids:
                    continue
                for key in e.keys:
                    if key and key in injected_text:
                        new_hits.append(TriggerHit(e, key, "recursive", _round))
                        break
            for h in new_hits:
                add(h.entry, h.matched_key, h.via, h.depth)
    token_bytes = sum(len(h.entry.content.encode("utf-8")) for h in hits)
    return hits, token_bytes


def inject_entries(entries: list[WorldBookEntry], user_text: str,
                   lorebook_config: dict[str, Any] | None = None) -> tuple[str, list[TriggerHit], int]:
    cfg = lorebook_config or {}
    hits, token_bytes = simulate_triggers(
        entries, user_text,
        scan_depth=int(cfg.get("scan_depth", 2) or 2),
        recursive=bool(cfg.get("recursive_scanning", True)),
        max_recursion_depth=int(cfg.get("max_recursion_depth", 1) or 1),
    )
    ordered = sorted(hits, key=lambda h: (h.entry.priority, h.entry.id if isinstance(h.entry.id, int) else 0))
    injected = "\n\n".join(h.entry.content for h in ordered)
    return injected, ordered, token_bytes


def budget_tokens(entries: list[WorldBookEntry], factor_constant: float = 1.2,
                  factor_triggered: float = 0.5) -> int:
    const = sum(len(e.content.encode("utf-8")) for e in entries if e.enabled and e.constant)
    triggered = sum(len(e.content.encode("utf-8")) for e in entries if e.enabled and not e.constant)
    return int(const * factor_constant + triggered * factor_triggered)


# ── 条目 CRUD（模块化 IR 的 worldbook/*.md） ────────────────────────────────
def write_entry_file(path: Path, entry: WorldBookEntry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": entry.id or None,
        "keys": entry.keys,
        "name": entry.name or None,
        "depth": entry.depth,
        "priority": entry.priority,
        "constant": entry.constant,
        "probability": entry.probability,
        "scope": entry.scope,
    }
    fm = {k: v for k, v in fm.items() if v not in (None, "", [])}
    import yaml
    header = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).rstrip()
    path.write_text(f"---\n{header}\n---\n\n{entry.content.strip()}\n", encoding="utf-8", newline="\n")


def read_entry_file(path: Path) -> WorldBookEntry:
    text = path.read_text(encoding="utf-8")
    fm, body = split_front_matter(text)
    return entry_from_frontmatter(fm, body.strip())


def next_entry_id(card: Card) -> int:
    ids = [int(e.id) for e in card.worldbook if str(e.id).isdigit()]
    return max(ids, default=0) + 1 if ids else int(time.time() * 1000)
