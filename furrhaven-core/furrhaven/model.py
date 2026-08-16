"""IR 数据模型：单一事实源。

Card 是全部平台的公共中间表示（IR）。平台产物（FD JSON / FC 包 / FB md /
ST V2+V3 PNG）全部由 Card 派生，禁止把平台产物当编辑源。
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import IR_SCHEMA_VERSION, SUPPORTED_CARD_TYPES


# ── 世界书条目 ──────────────────────────────────────────────────────────────
@dataclass
class WorldBookEntry:
    id: int | str = 0
    keys: list[str] = field(default_factory=list)
    content: str = ""
    name: str = ""
    depth: int = 3
    priority: int = 500
    constant: bool = False
    probability: int = 100
    scope: str = "card"                 # card | shared
    enabled: bool = True
    position: str = "before_char"       # ST: before_char | after_char
    secondary_keys: list[str] = field(default_factory=list)
    selective: bool = False
    use_regex: bool = False
    case_sensitive: bool = False
    comment: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def trigger_keys_text(self) -> str:
        return ",".join(self.keys)

    def is_system(self) -> bool:
        return any(k.startswith("系统-") for k in self.keys)

    def to_fd(self, next_id: int | None = None) -> dict[str, Any]:
        eid = self.id if self.id not in (0, "", None) else next_id
        return {
            "id": eid,
            "keys": self.trigger_keys_text(),
            "content": self.content,
            "enabled": self.enabled,
            "expanded": self.constant,
            "priority": self.priority,
            "position": 0,
            "constant": self.constant,
            "selective": self.selective,
            "caseSensitive": self.case_sensitive,
            "matchWholeWords": False,
            "useRegex": self.use_regex,
            "probability": self.probability,
            "depth": self.depth,
            **({"name": self.name} if self.name else {}),
        }

    def to_st(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "keys": self.keys,
            "content": self.content,
            "extensions": {},
            "enabled": self.enabled,
            "insertion_order": self.priority,
            "case_sensitive": self.case_sensitive,
            "use_regex": self.use_regex,
            "constant": self.constant,
            **({"name": self.name} if self.name else {}),
            **({"priority": self.priority} if self.priority else {}),
            **({"id": self.id} if self.id not in (0, "", None) else {}),
            **({"comment": self.comment} if self.comment else {}),
            **({"selective": self.selective} if self.selective else {}),
            **({"secondary_keys": self.secondary_keys} if self.secondary_keys else {}),
            **({"position": self.position} if self.position else {}),
        }
        return out

    @classmethod
    def from_fd(cls, d: dict[str, Any]) -> "WorldBookEntry":
        keys = str(d.get("keys", "")).split(",") if d.get("keys") else []
        return cls(
            id=d.get("id", 0),
            keys=[k.strip() for k in keys if k.strip()],
            content=d.get("content", ""),
            name=d.get("name", ""),
            depth=int(d.get("depth", 3) or 0),
            priority=int(d.get("priority", 500) or 500),
            constant=bool(d.get("constant", False)),
            probability=int(d.get("probability", 100) or 100),
            enabled=bool(d.get("enabled", True)),
            selective=bool(d.get("selective", False)),
            use_regex=bool(d.get("useRegex", False)),
            case_sensitive=bool(d.get("caseSensitive", False)),
        )

    @classmethod
    def from_st(cls, d: dict[str, Any]) -> "WorldBookEntry":
        return cls(
            id=d.get("id", 0),
            keys=[str(k) for k in d.get("keys", [])],
            content=d.get("content", ""),
            name=d.get("name", ""),
            priority=int(d.get("priority", d.get("insertion_order", 500)) or 500),
            constant=bool(d.get("constant", False)),
            enabled=bool(d.get("enabled", True)),
            selective=bool(d.get("selective", False)),
            secondary_keys=list(d.get("secondary_keys", []) or []),
            use_regex=bool(d.get("use_regex", False)),
            case_sensitive=bool(d.get("case_sensitive", False)),
            position=d.get("position", "before_char") or "before_char",
            comment=d.get("comment", ""),
        )


# ── 组件 ────────────────────────────────────────────────────────────────────
@dataclass
class Component:
    name: str
    label: str = ""
    html: str = ""
    css: str = ""
    script: str = ""
    ai_prompt: str = ""
    description: str = ""
    id: str = ""                       # FD 要求 id 字符串且 = name
    meta: dict[str, Any] = field(default_factory=dict)
    theme: dict[str, str] = field(default_factory=dict)
    render: str = "iframe"

    def __post_init__(self) -> None:
        self.id = self.id or self.name

    @property
    def source(self) -> str:
        script = self.script.strip("\n")
        return f"{self.html.rstrip()}\n\n<style>\n{self.css.rstrip()}\n</style>\n\n<script>\n  {script}\n</script>"

    @property
    def source_bytes(self) -> int:
        return len(self.source.encode("utf-8"))

    def apply_theme(self, theme: dict[str, str]) -> "Component":
        """A5 主题色泛化：把 %KEY% 占位符替换为主题色，不改原件。"""
        if not theme:
            return self
        out = copy.deepcopy(self)
        for key, value in theme.items():
            token = f"%{key.upper()}%"
            out.css = out.css.replace(token, value)
            out.script = out.script.replace(token, value)
            out.html = out.html.replace(token, value)
        return out

    def to_fd(self, theme: dict[str, str] | None = None) -> dict[str, Any]:
        c = self.apply_theme(theme or self.theme or {})
        return {
            "id": c.id,
            "name": c.name,
            "label": c.label or c.name,
            "html": c.html,
            "css": c.css,
            "script": c.script,
            "source": c.source,
            "ai_prompt": c.ai_prompt,
            "description": c.description,
        }

    def to_st_extension(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "html": self.html,
            "css": self.css,
            "script": self.script,
            "ai_prompt": self.ai_prompt,
            "description": self.description,
            "theme": self.theme,
            "render": self.render,
        }


# ── 正则规则 ────────────────────────────────────────────────────────────────
@dataclass
class RegexRule:
    id: str
    name: str = ""
    find: str = ""
    replace: str = ""
    flags: list[str] = field(default_factory=list)
    scope: str = "ai_reply"            # ai_reply | user_input | world_info
    order: int = 10
    enabled: bool = True
    dialect: str = "fc"                # fc | st | fd-legacy
    notes: str = ""

    @property
    def pattern_flags(self) -> int:
        import re
        out = 0
        for f in self.flags:
            flag = getattr(re, f.upper(), None)
            if isinstance(flag, int):
                out |= flag
        return out

    def apply(self, text: str) -> tuple[str, int]:
        if not self.enabled or not self.find:
            return text, 0
        try:
            pattern = re.compile(self.find, self.pattern_flags)
            # FC/JS 方言用 $1 反向引用；Python 用 \1
            py_replace = re.sub(r"\$(\d+)", r"\\\1", self.replace)
            return pattern.subn(py_replace, text)
        except re.error:
            return text, -1


# ── 快捷回复 ────────────────────────────────────────────────────────────────
@dataclass
class QuickReply:
    id: str
    label: str
    message: str
    icon: str = ""
    intimacy_requirement: int = 0
    cooldown_minutes: int = 10
    mood_effects: dict[str, int] = field(default_factory=dict)
    description: str = ""

    def to_fd(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "icon": self.icon,
            "intimacy_requirement": self.intimacy_requirement,
            "cooldown_minutes": self.cooldown_minutes,
            "mood_effects": self.mood_effects,
            "description": self.description,
            "message": self.message,
        }


# ── 角色卡 IR ───────────────────────────────────────────────────────────────
@dataclass
class Card:
    slug: str
    type: str = "character"
    # 卡体核心字段（V1/V2/V3 公共面）
    name: str = ""
    nickname: str = ""
    description: str = ""
    personality: str = ""
    scenario: str = ""
    world_view: str = ""
    first_mes: str = ""
    mes_example: str = ""
    creator_notes: str = ""
    response_format: str = ""
    system_prompt: str = ""
    post_history_instructions: str = ""
    alternate_greetings: list[str] = field(default_factory=list)
    group_only_greetings: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    creator: str = ""
    character_version: str = ""
    creation_date: int | None = None
    modification_date: int | None = None
    # 平台展示位（FD）
    title: str = ""
    category: str = ""
    species: str = ""
    age: str = ""
    occupation: str = ""
    emotional_arc: list[str] = field(default_factory=list)
    emotional_development_nodes: list[str] = field(default_factory=list)
    # 世界书
    worldbook: list[WorldBookEntry] = field(default_factory=list)
    lorebook: dict[str, Any] = field(default_factory=dict)
    # 组件（名字引用组件库；完整模式直接内嵌）
    components: list[Component | str] = field(default_factory=list)
    component_set: str = "vn4"
    component_theme: dict[str, str] = field(default_factory=dict)
    quick_replies: list[QuickReply] = field(default_factory=list)
    regex_rules: list[RegexRule] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
    # 资产
    avatar: str = ""                   # 相对项目路径；ST PNG 用其承载
    assets: list[dict[str, Any]] = field(default_factory=list)
    # 溯源
    source_path: Path | None = None
    authoring_mode: str = "modular"    # modular | full | imported
    ir_schema_version: str = IR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.type not in SUPPORTED_CARD_TYPES:
            raise ValueError(f"未知卡型：{self.type}（支持 {SUPPORTED_CARD_TYPES}）")
        if not self.name and self.slug:
            self.name = self.slug

    # ── 世界书便捷方法 ──────────────────────────────────────────────────────
    def constant_entries(self, include_shared: bool = True) -> list[WorldBookEntry]:
        return [e for e in self.worldbook if e.enabled and e.constant]

    def system_entries(self) -> list[WorldBookEntry]:
        return [e for e in self.worldbook if e.is_system()]

    def named_components(self, project=None) -> list[Component]:
        out: list[Component] = []
        for c in self.components:
            if isinstance(c, Component):
                out.append(c)
            elif project is not None:
                found = project.find_component(c)
                if found is not None:
                    out.append(found)
        return out

    def core_text_fields(self) -> dict[str, str]:
        return {
            "personality": self.personality,
            "scenario": self.scenario,
            "world_view": self.world_view,
            "mes_example": self.mes_example,
            "response_format": self.response_format,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "type": self.type,
            "name": self.name,
            "nickname": self.nickname,
            "title": self.title,
            "description": self.description,
            "personality": self.personality,
            "scenario": self.scenario,
            "world_view": self.world_view,
            "first_mes": self.first_mes,
            "mes_example": self.mes_example,
            "creator_notes": self.creator_notes,
            "response_format": self.response_format,
            "system_prompt": self.system_prompt,
            "post_history_instructions": self.post_history_instructions,
            "alternate_greetings": self.alternate_greetings,
            "group_only_greetings": self.group_only_greetings,
            "tags": self.tags,
            "creator": self.creator,
            "character_version": self.character_version,
            "category": self.category,
            "species": self.species,
            "age": self.age,
            "occupation": self.occupation,
            "worldbook": [e.__dict__ for e in self.worldbook],
            "components": [
                c if isinstance(c, str) else c.to_st_extension() for c in self.components
            ],
            "quick_replies": [q.__dict__ for q in self.quick_replies],
            "regex_rules": [r.__dict__ for r in self.regex_rules],
            "avatar": self.avatar,
        }
