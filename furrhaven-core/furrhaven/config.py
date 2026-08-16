"""项目配置：fh.config.yaml + platforms.yaml 口径表。"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from . import PLATFORMS_SCHEMA_VERSION


def _resource_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "resources" / name


def load_bundled_platforms() -> dict[str, Any]:
    with open(_resource_path("platforms.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


DEFAULT_CONFIG: dict[str, Any] = {
    "project": {
        "name": "furrhaven-workspace",
        "platforms": ["fd", "st", "fc", "fb"],
        "card_types": ["character", "simulator", "bigworld"],
        "authoring_modes": ["modular", "full"],
    },
    "rulepacks": {
        "quality-core": True,
        "genre-furry": False,
        "type-simulator": "auto",
        "type-bigworld": "auto",
    },
    "lexicon": {
        # genre-furry 包参数：跨卡专属词雷区表（非兽人项目留空即可）
        "forbidden_words": [],
        "exclusive_word_map": {},
        "dead_metaphors": ["金属板", "蓝宝石", "山峦", "星海", "星辰大海"],
    },
    "play": {
        "api_base": "",
        "api_key": "",
        "model": "",
        "user_name": "我",
        "temperature": 1.0,
        "max_tokens": 2048,
    },
    "vision": {
        "api_base": "",
        "api_key": "",
        "model": "",
    },
    "model_roles": {
        "lint": "flash",
        "draft": "flash",
        "rewrite": "v4-pro max",
    },
}


class Project:
    """fh init 生成的 L3 工作区。"""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.config_path = self.root / "fh.config.yaml"
        self.platforms = load_bundled_platforms()
        self.reload()

    # ── 目录 ────────────────────────────────────────────────────────────────
    @property
    def cards_dir(self) -> Path:
        return self.root / "cards"

    @property
    def shared_dir(self) -> Path:
        return self.root / "shared"

    @property
    def components_dir(self) -> Path:
        return self.root / "components"

    @property
    def regex_dir(self) -> Path:
        return self.root / "regex"

    @property
    def assets_dir(self) -> Path:
        return self.root / "assets"

    @property
    def dist_dir(self) -> Path:
        return self.root / "dist"

    @property
    def reviews_dir(self) -> Path:
        return self.root / "reviews"

    # ── 加载 ────────────────────────────────────────────────────────────────
    def reload(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            self.config = deep_merge(DEFAULT_CONFIG, user)
        local = self.root / "platforms.local.yaml"
        if local.exists():
            with open(local, encoding="utf-8") as f:
                override = yaml.safe_load(f) or {}
            self.platforms = deep_merge(self.platforms, override)

    @classmethod
    def discover(cls, start: str | Path | None = None) -> "Project | None":
        """向上查找 fh.config.yaml；找不到返回 None（供 --card 单卡模式）。"""
        cur = Path(start or Path.cwd()).resolve()
        if cur.is_file():
            cur = cur.parent
        for p in [cur, *cur.parents]:
            if (p / "fh.config.yaml").exists():
                return cls(p)
        return None

    def is_enabled(self, platform: str) -> bool:
        return platform in (self.config.get("project", {}).get("platforms") or [])

    def rulepack_on(self, pack: str, card_type: str | None = None) -> bool:
        rp = self.config.get("rulepacks", {})
        value = rp.get(pack, False)
        if value == "auto":
            if pack == "type-simulator":
                return card_type == "simulator"
            if pack == "type-bigworld":
                return card_type == "bigworld"
            return False
        return bool(value)

    # ── 组件库 ──────────────────────────────────────────────────────────────
    def find_component(self, name: str):
        from .components import load_component_dir
        target = self.components_dir / name
        if (target / "meta.json").exists() or (target / "html.html").exists():
            return load_component_dir(target)
        return None

    def load_component_set(self, set_name: str | None = None):
        from .components import load_component_set
        return load_component_set(self, set_name)

    # ── 口径查询 ────────────────────────────────────────────────────────────
    def platform_limits(self, platform: str) -> dict[str, Any]:
        p = self.platforms.get("platforms", {}).get(platform, {})
        return copy.deepcopy(p)

    def platform_calib_version(self) -> str:
        return str(self.platforms.get("version", PLATFORMS_SCHEMA_VERSION))


def save_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
