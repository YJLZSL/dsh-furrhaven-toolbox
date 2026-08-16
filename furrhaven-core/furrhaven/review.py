"""审阅双向流 + 状态机锁（防 export 覆盖未回写改动事故）。

状态：IDLE → export(生成审阅稿并加锁) → EDITING → apply(校验→回写 IR→
fh check→解锁) → IDLE。EDITING 期间 build/export 拒绝，apply 失败回滚备份。
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

import yaml

from .lint import EXIT_OK, run_lints
from .model import Card, WorldBookEntry
from .parsers import export_full_card_md, load_card, split_front_matter
from .worldbook import entry_from_frontmatter

STATE_FILE = ".review-state.yaml"
FIELD_ORDER = [
    "name", "title", "description", "personality", "scenario", "world_view",
    "first_mes", "mes_example", "response_format", "creator_notes", "category",
]

FILE_MAP = {
    "personality": "personality.md",
    "scenario": "scenario.md",
    "world_view": "world_view.md",
    "first_mes": "first_mes.md",
    "mes_example": "mes_example.md",
    "response_format": "response_format.md",
    "creator_notes": "creator_notes.md",
    "description": "description.md",
}

SECTION_MARK = "<!-- fh-review:field:{field} -->"
WB_MARK = "<!-- fh-review:wb:{ident} -->"


def state_path(project) -> Path:
    return project.reviews_dir / STATE_FILE


def read_state(project) -> dict[str, Any]:
    p = state_path(project)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_state(project, data: dict[str, Any]) -> None:
    project.reviews_dir.mkdir(parents=True, exist_ok=True)
    with open(state_path(project), "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def assert_not_editing(project, slug: str | None = None, action: str = "build/export") -> None:
    state = read_state(project)
    for key, st in state.items():
        if st.get("status") == "EDITING" and (slug is None or key == slug):
            raise RuntimeError(
                f"{action} 被拒：{key} 处于审阅 EDITING 状态（先 fh review apply 回写或 fh review abort）"
            )


def _export_markdown(card: Card, components_meta: list[dict[str, Any]]) -> str:
    lines = [
        f"# {card.name} · 文字审阅稿",
        "",
        "> 由 `fh review export` 单向生成。改稿后运行 `fh review apply --card <slug>` 回写 IR。",
        "> **EDITING 期间禁止 build/export**（状态机锁）。",
        "",
    ]
    for field in FIELD_ORDER:
        value = getattr(card, field, "")
        lines += [SECTION_MARK.format(field=field), f"## {field}", "", (value or "").strip(), ""]
    lines += ["# 世界书", ""]
    for e in card.worldbook:
        ident = e.id or e.trigger_keys_text()
        lines += [WB_MARK.format(ident=ident),
                  f"## {e.name or ident}",
                  f"- keys: {e.trigger_keys_text()}",
                  f"- constant: {str(e.constant).lower()}",
                  f"- priority: {e.priority}",
                  "", e.content.strip(), ""]
    lines += ["# 快捷回复", ""]
    for q in card.quick_replies:
        lines += [f"## {q.label or q.id}",
                  f"- message: {q.message}",
                  f"- intimacy_requirement: {q.intimacy_requirement}",
                  f"- cooldown_minutes: {q.cooldown_minutes}", ""]
    lines += ["# 组件清单", ""]
    for c in components_meta:
        lines.append(f"- {c}")
    return "\n".join(lines).rstrip() + "\n"


def review_export(project, slug: str | None = None) -> list[Path]:
    from .build import load_project_cards, resolve_components
    cards = load_project_cards(project, slug)
    if not cards:
        raise RuntimeError("没有可导出的卡")
    state = read_state(project)
    written: list[Path] = []
    for card in cards:
        if state.get(card.slug, {}).get("status") == "EDITING":
            raise RuntimeError(f"{card.slug} 已在 EDITING：先 apply 回写或 abort")
        comps = resolve_components(card, project)
        meta = [{"name": c.name, "source_bytes": c.source_bytes} for c in comps]
        out = project.reviews_dir / f"{card.slug}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_export_markdown(card, meta), encoding="utf-8", newline="\n")
        state[card.slug] = {
            "status": "EDITING",
            "exported_at": int(time.time()),
            "source": str(card.source_path or ""),
        }
        written.append(out)
    write_state(project, state)
    return written


def _parse_review(text: str) -> dict[str, str | list[tuple[str, dict[str, Any], str]]]:
    fields: dict[str, str] = {}
    entries: list[tuple[str, dict[str, Any], str]] = []
    # 切分：字段标记 + 世界书标记
    parts: list[tuple[str, str]] = []
    for mark in [SECTION_MARK.format(field=f) for f in FIELD_ORDER]:
        idx = text.find(mark)
        if idx != -1:
            parts.append((mark, idx))
    parts.sort(key=lambda x: x[1])
    for i, (mark, idx) in enumerate(parts):
        end = parts[i + 1][1] if i + 1 < len(parts) else len(text)
        chunk = text[idx + len(mark):end]
        field = mark.split("field:", 1)[1].strip(" ->")
        # 去掉 `## field` 标题
        lines = chunk.splitlines()
        body = "\n".join(lines[1:]).strip() if lines else ""
        fields[field] = body
    # 世界书：按 WB_MARK 切
    wb_idx = [m.start() for m in _find_marks(text, "wb:")]
    for i, idx in enumerate(wb_idx):
        end = wb_idx[i + 1] if i + 1 < len(wb_idx) else len(text)
        chunk = text[idx:end]
        ident = chunk.split("-->", 1)[0].split("wb:")[1].strip()
        lines = chunk.splitlines()
        # 前 4 行是 meta，之后正文
        meta: dict[str, Any] = {}
        body_lines: list[str] = []
        for line in lines[1:]:
            if line.startswith("- keys:"):
                meta["keys"] = [k.strip() for k in line.split(":", 1)[1].split(",") if k.strip()]
            elif line.startswith("- constant:"):
                meta["constant"] = line.split(":", 1)[1].strip().lower() == "true"
            elif line.startswith("- priority:"):
                try:
                    meta["priority"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("## ") and not body_lines:
                meta["name"] = line[3:].strip()
            else:
                body_lines.append(line)
        entries.append((ident, meta, "\n".join(body_lines).strip()))
    return {"fields": fields, "worldbook": entries}  # type: ignore[return-value]


def _find_marks(text: str, kind: str):
    import re
    return list(re.finditer(rf"<!-- fh-review:{re.escape(kind)}(.*?)-->", text))


def _write_field(card: Card, attr: str, text: str) -> None:
    if attr == "name" and text:
        card.name = text.strip().splitlines()[0].strip()[:60]
    else:
        setattr(card, attr, text)


def _apply_modular(card: Card, parsed, card_dir: Path) -> None:
    for attr, text in parsed["fields"].items():
        if attr == "name":
            continue
        fname = FILE_MAP.get(attr)
        if not fname:
            continue
        fp = card_dir / fname
        if fp.exists():
            fp.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")
    wb_dir = card_dir / "worldbook"
    for ident, meta, body in parsed["worldbook"]:
        if not body and meta.get("name") is None:
            continue
        # 按文件名/name 匹配现有条目
        target = None
        for fp in sorted(wb_dir.glob("*.md")) if wb_dir.exists() else []:
            fm, _ = split_front_matter(fp.read_text(encoding="utf-8"))
            if str(fm.get("id")) == str(ident) or fm.get("name") == meta.get("name"):
                target = fp
                break
        if target is None:
            from .worldbook import next_entry_id, write_entry_file
            entry = WorldBookEntry(
                id=int(time.time() * 1000) if not str(ident).isdigit() else int(ident),
                keys=meta.get("keys", []), content=body,
                name=meta.get("name", "") or ident,
                constant=meta.get("constant", False),
                priority=meta.get("priority", 500),
            )
            wb_dir.mkdir(parents=True, exist_ok=True)
            write_entry_file(wb_dir / f"{len(list(wb_dir.glob('*.md')))+1:02d}-{entry.name}.md", entry)
        else:
            from .worldbook import entry_from_frontmatter, write_entry_file
            fm, _ = split_front_matter(target.read_text(encoding="utf-8"))
            entry = entry_from_frontmatter(fm, body)
            if meta.get("keys"):
                entry.keys = meta["keys"]
            if "constant" in meta:
                entry.constant = meta["constant"]
            if meta.get("priority"):
                entry.priority = meta["priority"]
            write_entry_file(target, entry)


def review_apply(project, slug: str) -> None:
    review = project.reviews_dir / f"{slug}.md"
    if not review.exists():
        raise RuntimeError(f"审阅稿不存在：{review}（先 fh review export）")
    state = read_state(project)
    if state.get(slug, {}).get("status") != "EDITING":
        raise RuntimeError(f"{slug} 不处于 EDITING（先 export）")
    result = load_card(project.cards_dir / slug, project)
    card = result.card
    backup = project.reviews_dir / f".backup-{slug}-{int(time.time())}.md"
    backup.write_text(review.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    parsed = _parse_review(review.read_text(encoding="utf-8"))
    try:
        if card.authoring_mode == "full":
            for attr, text in parsed["fields"].items():
                _write_field(card, attr, text)
            for ident, meta, body in parsed["worldbook"]:
                updated = False
                for e in card.worldbook:
                    if str(e.id) == str(ident) or e.name == meta.get("name"):
                        e.content = body
                        if meta.get("keys"):
                            e.keys = meta["keys"]
                        if "constant" in meta:
                            e.constant = meta["constant"]
                        updated = True
                if not updated and body:
                    card.worldbook.append(WorldBookEntry(
                        id=int(ident) if str(ident).isdigit() else int(time.time() * 1000),
                        keys=meta.get("keys", []), content=body,
                        name=meta.get("name", "") or ident,
                        constant=meta.get("constant", False),
                    ))
            card_dir = project.cards_dir / slug
            card_dir.mkdir(parents=True, exist_ok=True)
            (card_dir / "card.md").write_text(export_full_card_md(card), encoding="utf-8", newline="\n")
        else:
            card_dir = project.cards_dir / slug
            _apply_modular(card, parsed, card_dir)
    except Exception:
        # 回滚审阅稿；IR 分区多为单文件写，失败时以状态机保留 EDITING 阻断 build
        review.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        raise
    # 门禁：apply 后必须 check 通过才解锁
    from .build import load_project_cards, resolve_components
    cards = load_project_cards(project, slug)
    if not cards:
        raise RuntimeError(f"{slug} 回写后无法重新加载")
    comps = resolve_components(cards[0], project)
    report = run_lints(cards[0], comps, project.platforms, project,
                       platforms=["fd"], enabled_packs={"quality-core": False, "genre-furry": False,
                                                        "type-simulator": False, "type-bigworld": False})
    if report.exit_code != EXIT_OK:
        raise RuntimeError(f"{slug} apply 后门禁未过：\n{report.render()}")
    state[slug] = {"status": "IDLE", "applied_at": int(time.time())}
    write_state(project, state)


def review_abort(project, slug: str) -> None:
    state = read_state(project)
    state[slug] = {"status": "IDLE", "aborted_at": int(time.time())}
    write_state(project, state)
