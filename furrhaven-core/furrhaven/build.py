"""构建引擎：IR → 平台产物 + 构建指纹锁（防漂移）。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from . import __version__, PLATFORMS_SCHEMA_VERSION
from .config import Project, save_yaml
from .exporters import export_card
from .model import Card, Component
from .parsers import load_card


def _canonical(card: Card) -> str:
    data = card.to_dict()
    data.pop("source_path", None)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)


def ir_fingerprint(card: Card, platform_calib_version: str) -> str:
    payload = _canonical(card) + f"|engine={__version__}|calib={platform_calib_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_project_cards(project: Project, only: str | None = None):
    """加载项目全部卡（module 与 full 两种写法自动识别）。"""
    from .parsers import discover_cards
    out: list[Card] = []
    for p in discover_cards(project):
        slug = p.stem if p.is_file() else p.name
        if only and only not in (slug, p.name):
            continue
        result = load_card(p, project)
        out.append(result.card)
    return out


def resolve_components(card: Card, project: Project | None) -> list[Component]:
    """把组件引用解析为实体：项目组件库 → 完整卡内嵌组件。"""
    if project is None:
        return [c for c in card.components if isinstance(c, Component)]
    out: list[Component] = []
    refs: list[Component | str] = card.components or []
    if not refs and card.component_set:
        refs = [card.component_set]  # 集合名整体解析
    for ref in refs:
        if isinstance(ref, Component):
            out.append(ref)
            continue
        if ref == card.component_set:
            out.extend(project.load_component_set(ref))
            continue
        found = project.find_component(ref)
        if found is not None:
            out.append(found)
    # 去重保序
    seen: set[str] = set()
    uniq: list[Component] = []
    for c in out:
        if c.name not in seen:
            seen.add(c.name)
            uniq.append(c)
    return uniq


def build_card(project: Project, card: Card, platforms: list[str] | None = None,
               dist_root: Path | None = None) -> dict[str, Any]:
    platforms = platforms or project.config.get("project", {}).get("platforms", ["fd", "st"])
    dist = dist_root or project.dist_dir
    components = resolve_components(card, project)
    avatar = None
    if card.avatar:
        cand = project.assets_dir / card.avatar
        if cand.exists():
            avatar = cand
    artifacts: dict[str, Any] = {}
    for platform in platforms:
        artifacts[platform] = export_card(card, platform, dist, components, avatar)
    return {"card": card, "components": components, "artifacts": artifacts}


def build_all(project: Project, only: str | None = None, platforms: list[str] | None = None,
              dist_root: Path | None = None) -> dict[str, Any]:
    cards = load_project_cards(project, only)
    if not cards:
        raise SystemExit("没有找到卡：先 fh new <slug> 或在 cards/ 放入 card.md")
    results: dict[str, Any] = {}
    for card in cards:
        results[card.slug] = build_card(project, card, platforms, dist_root)
    write_lock(project, results, platforms)
    return results


def write_lock(project: Project, results: dict[str, Any],
               platforms: list[str] | None = None) -> Path:
    lock: dict[str, Any] = {
        "engine": __version__,
        "calib": project.platform_calib_version(),
        "platforms": platforms or project.config.get("project", {}).get("platforms", []),
        "cards": {},
    }
    for slug, r in results.items():
        card: Card = r["card"]
        lock["cards"][slug] = {
            "fingerprint": ir_fingerprint(card, project.platform_calib_version()),
            "mode": card.authoring_mode,
        }
    path = project.root / ".fh-lock.yaml"
    save_yaml(path, lock)
    return path


def read_lock(project: Project) -> dict[str, Any]:
    p = project.root / ".fh-lock.yaml"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_drift(project: Project, only: str | None = None) -> list[str]:
    """改 IR 不重建 → check 报漂移。"""
    lock = read_lock(project)
    problems: list[str] = []
    cards = load_project_cards(project, only)
    locked = lock.get("cards", {})
    for card in cards:
        fp = ir_fingerprint(card, project.platform_calib_version())
        expected = locked.get(card.slug, {}).get("fingerprint") if locked else None
        if expected is None:
            problems.append(f"{card.slug}: 从未构建（先 fh build）")
        elif expected != fp:
            problems.append(f"{card.slug}: IR 与 dist 产物漂移（指纹 {expected[:8]}→{fp[:8]}，先 fh build）")
    return problems
