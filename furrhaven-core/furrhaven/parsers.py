"""宽容解析器：不同人写卡方式不同，IR 解析器必须认得出。

支持三种输入：
1. 模块化 IR（cards/<slug>/card.yaml + 分区 md + worldbook/*.md）——首选创作方式；
2. 完整角色卡单文件（card.md：卡体 + 世界书 + 组件 + 正则一把梭）——「完整卡模式」；
3. 导入外部产物：FD JSON、SillyTavern/RisuAI V2/V3 JSON 与 PNG、自由模式 md
   （参考项目 `# name / # personality` 风格）——不同平台、不同作者的写法都尽量认。

设计原则：解析永远宽容（缺的字段留空、警告不中断），校验交给 lint 门禁。
"""
from __future__ import annotations

import base64
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .model import Card, Component, QuickReply, RegexRule, WorldBookEntry

# ── 标题别名表：规范字段 ← 各种作者写法（中英混用、平台风格） ─────────────────
FIELD_ALIASES: dict[str, list[str]] = {
    "name": ["name", "角色名", "角色名称", "姓名", "character name", "char_name"],
    "title": ["title", "标题", "故事标题", "卡名"],
    "description": ["description", "简介", "角色简介", "描述", "卡片简介", "list description"],
    "personality": [
        "personality", "人设", "性格", "性格设定", "人设性格", "角色设定", "角色人设",
        "personality summary", "character definition", "角色定义",
    ],
    "scenario": ["scenario", "场景", "场景设定", "情境", "背景", "当前场景", "scenario prompt"],
    "world_view": ["world_view", "worldview", "世界观", "世界设定", "世界背景", "lore"],
    "first_mes": ["first_mes", "first message", "firstmes", "开场白", "首次对话", "问候语", "开场", "greeting"],
    "mes_example": ["mes_example", "mesexample", "对话示例", "对话范例", "示例对话", "example dialogue", "examples"],
    "response_format": ["response_format", "responseformat", "回复格式", "输出格式", "回复模板", "格式规范", "output format"],
    "creator_notes": ["creator_notes", "creator notes", "创作者备注", "作者备注", "备注", "创作笔记", "creator comment"],
    "system_prompt": ["system_prompt", "systemprompt", "系统提示词", "系统prompt", "全局提示词"],
    "post_history_instructions": ["post_history_instructions", "posthistoryinstructions", "越狱提示", "后置指令", "jailbreak", "ujb"],
    "category": ["category", "分类", "题材", "类型"],
    "species": ["species", "种族", "物种"],
    "age": ["age", "年龄"],
    "occupation": ["occupation", "职业", "身份"],
    "worldbook": ["worldbook", "world_book", "world info", "world_info", "世界书", "世界设定条目", "lorebook", "character_book", "角色书"],
    "components": ["components", "组件", "组件定义", "组件源码"],
    "quick_replies": ["quick_replies", "quickreplies", "快捷回复", "快捷选项", "快捷按钮"],
    "regex": ["regex", "regex_scripts", "正则", "正则脚本", "正则规则", "regex rules"],
    "tags": ["tags", "标签", "tag"],
    "nickname": ["nickname", "昵称", "称呼"],
}


def normalize_heading(text: str) -> str:
    """去掉序号、括号注解、标点、空白后的小写串，让别名匹配容错。"""
    t = re.sub(r"^#+\s*", "", text)
    t = re.sub(r"^[\[【（(].*?[\]】）)]\s*", "", t)       # [人设/性格]
    t = re.sub(r"[（(][^）)]*[）)]", "", t)               # 人设/性格（personality）
    t = re.sub(r"[#*_`|:：/\-—\s]", "", t).lower()
    return t


def _alias_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for canonical, aliases in FIELD_ALIASES.items():
        for a in aliases:
            out[normalize_heading(a)] = canonical
    return out


ALIAS_MAP = _alias_map()


@dataclass
class ParseResult:
    card: Card
    warnings: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def warn(result: ParseResult, message: str) -> None:
    result.warnings.append(message)


# ── front-matter / 元数据 ────────────────────────────────────────────────────
def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    meta: dict[str, Any] = {}
    body = text.lstrip("\ufeff")
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            try:
                meta = yaml.safe_load(body[3:end]) or {}
            except yaml.YAMLError:
                meta = {}
            body = body[end + 4 :]
    return meta, body


def _coerce_meta(meta: dict[str, Any], card: Card) -> None:
    str_fields = [
        "name", "title", "nickname", "description", "personality", "scenario",
        "world_view", "first_mes", "mes_example", "response_format",
        "creator_notes", "system_prompt", "post_history_instructions",
        "category", "species", "age", "occupation", "creator", "character_version",
    ]
    for k in str_fields:
        if k in meta and meta[k] is not None:
            setattr(card, k, str(meta[k]))
    if "type" in meta:
        card.type = str(meta["type"])
    if "component_set" in meta:
        card.component_set = str(meta["component_set"])
    if "component_theme" in meta and isinstance(meta["component_theme"], dict):
        card.component_theme = {str(k): str(v) for k, v in meta["component_theme"].items()}
    for k in ("tags", "alternate_greetings", "group_only_greetings"):
        if k in meta and isinstance(meta[k], list):
            setattr(card, k, [str(x) for x in meta[k]])
    if "avatar" in meta:
        card.avatar = str(meta["avatar"])
    if "slug" in meta:
        card.slug = str(meta["slug"])
    if "character_book" in meta and isinstance(meta["character_book"], dict):
        card.lorebook = meta["character_book"]
    if "extensions" in meta and isinstance(meta["extensions"], dict):
        card.extensions = meta["extensions"]


# ── 完整卡 md 解析（多写法宽容） ─────────────────────────────────────────────
def parse_card_text(text: str, slug: str | None = None, source_path: Path | None = None) -> ParseResult:
    meta, body = split_front_matter(text)
    card = Card(slug=slug or meta.get("slug") or "unnamed")
    result = ParseResult(card=card, meta=meta)
    _coerce_meta(meta, card)
    card.source_path = source_path
    card.authoring_mode = "full"

    # 第一遍：按标题切成 section；section 名为 canonical 字段名
    sections: list[tuple[str, str, str]] = []  # (canonical, raw_heading, content)
    current: list[str] = []
    current_key = "personality"
    lines = body.splitlines()
    in_fence = False
    fence_char = ""

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                fence_char = stripped[:3]
            elif stripped[:3] == fence_char:
                in_fence = False
            if current is not None:
                current.append(line)
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m and not in_fence and len(m.group(1)) <= 2:
            # 只把 1-2 级标题当作字段边界；世界书/组件里的 ### 条目标题永不分段
            norm = normalize_heading(m.group(2))
            if norm in ALIAS_MAP and norm not in ("worldbook", "components", "regex", "quick_replies"):
                if current_key is not None:
                    sections.append((current_key, "", "\n".join(current)))
                current_key = ALIAS_MAP[norm]
                current = []
                continue
            # 世界书/组件/正则：交给专用解析，但先作为 section 存下
            if norm in ("worldbook", "components", "regex", "quick_replies"):
                if current_key is not None:
                    sections.append((current_key, "", "\n".join(current)))
                current_key = norm
                current = []
                continue
        if current is not None:
            current.append(line)
    if current_key is not None:
        sections.append((current_key, "", "\n".join(current)))

    # 第二遍：灌入字段
    for key, _raw, content in sections:
        content = content.strip("\n")
        if key == "worldbook":
            _parse_worldbook_section(content, card, result)
        elif key == "components":
            _parse_components_section(content, card, result)
        elif key == "regex":
            _parse_regex_section(content, card, result)
        elif key == "quick_replies":
            _parse_quick_replies_section(content, card, result)
        elif key in ("tags",):
            _parse_tags(content, card)
        else:
            setattr(card, key, content.strip())

    _apply_key_value_fallback(card, body, result)
    _apply_implicit_name(card, meta, result)
    return result


def _apply_implicit_name(card: Card, meta: dict[str, Any], result: ParseResult) -> None:
    """很多作者把角色名写在首行 # 标题 而不是 front-matter。"""
    if meta.get("name") is not None or (card.name and card.name != card.slug):
        return
    body_first = ""
    if card.personality:
        first = card.personality.splitlines()
        for line in first:
            t = line.strip()
            if t:
                body_first = t
                break
    if body_first and len(body_first) <= 40:
        card.name = body_first
    else:
        warn(result, "未识别到角色名：请在 front-matter 或正文首行写明 name/角色名")


def _apply_key_value_fallback(card: Card, body: str, result: ParseResult) -> None:
    """标题解析失败时，认 `字段：值` 行（常见简写写法）。"""
    simple = {
        "角色名": "name", "姓名": "name", "标题": "title", "简介": "description",
        "性格": "personality", "人设": "personality", "场景": "scenario",
        "世界观": "world_view", "开场白": "first_mes",
    }
    for line in body.splitlines():
        m = re.match(r"^\s*([^#:\n]{1,12})[:：]\s*(.{1,200})\s*$", line)
        if not m:
            continue
        label, value = m.group(1).strip(), m.group(2).strip()
        attr = simple.get(label)
        if attr and not getattr(card, attr):
            setattr(card, attr, value)


# ── 世界书 section：三种写法 ────────────────────────────────────────────────
def _parse_worldbook_section(content: str, card: Card, result: ParseResult) -> None:
    content = content.strip()
    if not content:
        return
    # 写法 A：fenced YAML / JSON 列表
    m = re.search(r"```(?:ya?ml|json)?\s*\n(.*?)```", content, re.S)
    if m:
        raw = m.group(1).strip()
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = None
        if isinstance(data, dict):
            data = data.get("entries", data.get("world_info", []))
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    card.worldbook.append(_entry_from_dict(item))
            return
        warn(result, "世界书列表格式无法解析，跳过该区块")
        return

    # 写法 B：### 条目名 + YAML front-matter + 正文
    blocks = re.split(r"^###\s+(.*)$", content, flags=re.M)
    if len(blocks) > 1:
        # blocks = [前言, 标题1, 内容1, 标题2, 内容2...]
        for i in range(1, len(blocks), 2):
            name = blocks[i].strip()
            chunk = blocks[i + 1] if i + 1 < len(blocks) else ""
            fm, entry_body = split_front_matter(chunk.strip())
            fm["name"] = fm.get("name", name)
            card.worldbook.append(entry_from_frontmatter(fm, entry_body.strip()))
        return

    # 写法 C：`- keys: ...` YAML 行内条目
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        data = None
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                card.worldbook.append(_entry_from_dict(item))
    else:
        warn(result, "世界书区块未识别出条目（支持 fenced YAML/JSON 或 ### 条目）")


def entry_from_frontmatter(fm: dict[str, Any], body: str) -> WorldBookEntry:
    keys = fm.get("keys", [])
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split(",") if k.strip()]
    return WorldBookEntry(
        id=fm.get("id", 0),
        keys=[str(k) for k in keys],
        content=body or str(fm.get("content", "")),
        name=str(fm.get("name", "")),
        depth=int(fm.get("depth", 3) or 3),
        priority=int(fm.get("priority", 500) or 500),
        constant=bool(fm.get("constant", False)),
        probability=int(fm.get("probability", 100) or 100),
        scope=str(fm.get("scope", "card")),
        enabled=bool(fm.get("enabled", True)),
        secondary_keys=list(fm.get("secondary_keys", []) or []),
        selective=bool(fm.get("selective", False)),
        use_regex=bool(fm.get("use_regex", False)),
        case_sensitive=bool(fm.get("case_sensitive", False)),
        comment=str(fm.get("comment", "")),
    )


def _entry_from_dict(d: dict[str, Any]) -> WorldBookEntry:
    keys = d.get("keys", [])
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split(",") if k.strip()]
    return WorldBookEntry(
        id=d.get("id", 0),
        keys=[str(k) for k in keys],
        content=str(d.get("content", "")),
        name=str(d.get("name", "")),
        depth=int(d.get("depth", 3) or 3),
        priority=int(d.get("priority", 500) or 500),
        constant=bool(d.get("constant", False)),
        probability=int(d.get("probability", 100) or 100),
        enabled=bool(d.get("enabled", True)),
        secondary_keys=list(d.get("secondary_keys", []) or []),
        selective=bool(d.get("selective", False)),
        use_regex=bool(d.get("use_regex", d.get("useRegex", False))),
        case_sensitive=bool(d.get("case_sensitive", d.get("caseSensitive", False))),
        comment=str(d.get("comment", "")),
    )


# ── 组件 section：### 组件名 + fenced html/css/js ────────────────────────────
def _parse_components_section(content: str, card: Card, result: ParseResult) -> None:
    content = content.strip()
    if not content:
        return
    # fenced YAML 列表（组件引用名）
    m = re.search(r"```(?:ya?ml|json)?\s*\n(.*?)```", content, re.S)
    if m:
        try:
            data = yaml.safe_load(m.group(1).strip())
        except yaml.YAMLError:
            data = None
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            card.components = list(data)
            return
        if isinstance(data, dict):
            names = data.get("components", [])
            card.component_set = str(data.get("set", card.component_set))
            card.component_theme = {str(k): str(v) for k, v in (data.get("theme") or {}).items()}
            if isinstance(names, list) and all(isinstance(x, str) for x in names):
                card.components = names
            return
    blocks = re.split(r"^###\s+(.*)$", content, flags=re.M)
    if len(blocks) > 1:
        for i in range(1, len(blocks), 2):
            name = blocks[i].strip()
            chunk = blocks[i + 1] if i + 1 < len(blocks) else ""
            card.components.append(_component_from_chunk(name, chunk))
        return
    # 纯文本 = 组件引用清单（每行一个）
    names = [x.strip().lstrip("- ").strip() for x in content.splitlines() if x.strip()]
    card.components = [n for n in names if n]


def _component_from_chunk(name: str, chunk: str) -> Component:
    fm, body = split_front_matter(chunk.strip())
    comp = Component(name=name, label=str(fm.get("label", name)))
    if "meta" in fm:
        comp.meta = fm["meta"]
    comp.label = str(fm.get("label", comp.label))
    comp.ai_prompt = str(fm.get("ai_prompt", ""))
    comp.description = str(fm.get("description", ""))
    comp.theme = {str(k): str(v) for k, v in (fm.get("theme") or {}).items()}
    # fenced code blocks：```html / ```css / ```js|javascript|script
    for m in re.finditer(r"```(html|css|js|javascript|script|meta|json)\s*\n(.*?)```", body, re.S):
        lang, code = m.group(1).lower(), m.group(2).strip("\n")
        if lang == "html":
            comp.html = code
        elif lang == "css":
            comp.css = code
        elif lang in ("js", "javascript", "script"):
            comp.script = code
        elif lang == "json":
            try:
                comp.meta.update(json.loads(code))
            except json.JSONDecodeError:
                pass
    return comp


# ── 正则 / 快捷回复 section ─────────────────────────────────────────────────
def _parse_regex_section(content: str, card: Card, result: ParseResult) -> None:
    content = content.strip()
    if not content:
        return
    data: Any = None
    m = re.search(r"```(?:ya?ml|json)?\s*\n(.*?)```", content, re.S)
    if m:
        try:
            data = yaml.safe_load(m.group(1).strip())
        except yaml.YAMLError:
            try:
                data = json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                data = None
    else:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            data = None
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                card.regex_rules.append(RegexRule(
                    id=str(item.get("id", item.get("name", f"r{len(card.regex_rules) + 1}"))),
                    name=str(item.get("name", "")),
                    find=str(item.get("find", "")),
                    replace=str(item.get("replace", "")),
                    flags=list(item.get("flags", []) or []),
                    scope=str(item.get("scope", "ai_reply")),
                    order=int(item.get("order", 10) or 10),
                    enabled=bool(item.get("enabled", True)),
                    dialect=str(item.get("dialect", "fc")),
                    notes=str(item.get("notes", "")),
                ))
    elif data is not None:
        warn(result, "正则区块应为规则列表（fenced YAML）")
    else:
        warn(result, "正则区块无法解析（支持 fenced YAML 列表）")


def _parse_quick_replies_section(content: str, card: Card, result: ParseResult) -> None:
    data: Any = None
    m = re.search(r"```(?:ya?ml|json)?\s*\n(.*?)```", content, re.S)
    if m:
        try:
            data = yaml.safe_load(m.group(1).strip())
        except yaml.YAMLError:
            try:
                data = json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                data = None
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                card.quick_replies.append(QuickReply(
                    id=str(item.get("id", "")),
                    label=str(item.get("label", "")),
                    message=str(item.get("message", "")),
                    icon=str(item.get("icon", "")),
                    intimacy_requirement=int(item.get("intimacy_requirement", 0) or 0),
                    cooldown_minutes=int(item.get("cooldown_minutes", 10) or 10),
                    mood_effects={str(k): int(v) for k, v in (item.get("mood_effects") or {}).items()},
                    description=str(item.get("description", "")),
                ))
    elif data:
        warn(result, "快捷回复区块格式未识别（支持 fenced YAML 列表）")


def _parse_tags(content: str, card: Card) -> None:
    text = content.strip().strip("[]")
    tags = [t.strip().strip("\"'") for t in re.split(r"[,，\n]", text) if t.strip()]
    card.tags = tags


# ── 模块化 IR 读取 ───────────────────────────────────────────────────────────
def load_card_dir(card_dir: Path) -> ParseResult:
    slug = card_dir.name
    card = Card(slug=slug)
    result = ParseResult(card=card)
    card.source_path = card_dir
    card.authoring_mode = "modular"

    card_yaml = card_dir / "card.yaml"
    if not card_yaml.exists() and (card_dir / "card.md").exists():
        # 完整卡模式
        return parse_card_text(
            (card_dir / "card.md").read_text(encoding="utf-8"), slug, card_dir / "card.md"
        )
    if not card_yaml.exists():
        raise FileNotFoundError(f"卡片目录缺少 card.yaml 或 card.md：{card_dir}")

    meta = load_yaml_safe(card_yaml)
    result.meta = meta
    _coerce_meta(meta, card)

    file_map = {
        "personality.md": "personality", "scenario.md": "scenario",
        "world_view.md": "world_view", "first_mes.md": "first_mes",
        "mes_example.md": "mes_example", "response_format.md": "response_format",
        "creator_notes.md": "creator_notes", "system_prompt.md": "system_prompt",
        "post_history_instructions.md": "post_history_instructions",
        "description.md": "description",
    }
    for fname, attr in file_map.items():
        fp = card_dir / fname
        if fp.exists():
            setattr(card, attr, fp.read_text(encoding="utf-8").strip())

    wb_dir = card_dir / "worldbook"
    if wb_dir.exists():
        for fp in sorted(wb_dir.glob("*.md")):
            text = fp.read_text(encoding="utf-8")
            fm, body = split_front_matter(text)
            if "id" not in fm and not body:
                continue
            card.worldbook.append(entry_from_frontmatter(fm, body.strip()))

    comps_yaml = card_dir / "components.yaml"
    if comps_yaml.exists():
        data = load_yaml_safe(comps_yaml)
        if isinstance(data, dict):
            card.component_set = str(data.get("set", card.component_set))
            card.component_theme = {str(k): str(v) for k, v in (data.get("theme") or {}).items()}
            names = data.get("components", [])
        else:
            names = data
        card.components = [str(x) for x in (names or [])]

    qr_yaml = card_dir / "quick_replies.yaml"
    if qr_yaml.exists():
        data = load_yaml_safe(qr_yaml) or []
        if isinstance(data, dict):
            data = data.get("items", [])
        for item in data:
            if isinstance(item, dict):
                card.quick_replies.append(QuickReply(
                    id=str(item.get("id", "")), label=str(item.get("label", "")),
                    message=str(item.get("message", "")), icon=str(item.get("icon", "")),
                    intimacy_requirement=int(item.get("intimacy_requirement", 0) or 0),
                    cooldown_minutes=int(item.get("cooldown_minutes", 10) or 10),
                    mood_effects={str(k): int(v) for k, v in (item.get("mood_effects") or {}).items()},
                    description=str(item.get("description", "")),
                ))

    regex_yaml = card_dir / "regex.yaml"
    if regex_yaml.exists():
        _parse_regex_section(regex_yaml.read_text(encoding="utf-8"), card, result)
    return result


def load_yaml_safe(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ── 自动发现入口 ─────────────────────────────────────────────────────────────
def load_card(path: str | Path, project=None) -> ParseResult:
    p = Path(path)
    if p.is_dir():
        return load_card_dir(p)
    if p.suffix.lower() == ".json":
        return ParseResult(card=import_st_json(p.read_text(encoding="utf-8")), meta={})
    if p.suffix.lower() == ".png":
        from .png import read_card_png
        obj = read_card_png(p)
        return ParseResult(card=import_st_json(obj), meta={})
    return parse_card_text(p.read_text(encoding="utf-8"), p.stem, p)


def discover_cards(project) -> list[Path]:
    if not project.cards_dir.exists():
        return []
    out = [d for d in project.cards_dir.iterdir() if d.is_dir()]
    out.extend(project.cards_dir.glob("*.md"))
    return sorted(out)


# ── ST/RisuAI V2/V3 JSON 导入 ────────────────────────────────────────────────
def import_st_json(data: str | dict[str, Any], slug: str | None = None) -> Card:
    obj = json.loads(data) if isinstance(data, str) else data
    spec = obj.get("spec", "")
    payload = obj.get("data", obj) if isinstance(obj, dict) else {}
    slug = slug or _slugify(str(payload.get("name", "imported")))
    card = Card(slug=slug)
    card.authoring_mode = "imported"
    for attr in [
        "name", "description", "personality", "scenario", "first_mes", "mes_example",
        "creator_notes", "system_prompt", "post_history_instructions", "nickname",
        "creator", "character_version",
    ]:
        if payload.get(attr) is not None:
            setattr(card, attr, str(payload.get(attr)))
    if payload.get("tags"):
        card.tags = [str(x) for x in payload["tags"]]
    if payload.get("alternate_greetings"):
        card.alternate_greetings = [str(x) for x in payload["alternate_greetings"]]
    if payload.get("group_only_greetings"):
        card.group_only_greetings = [str(x) for x in payload["group_only_greetings"]]
    if payload.get("extensions"):
        card.extensions = payload["extensions"]
        fh = card.extensions.get("furrhaven", {})
        if isinstance(fh, dict):
            card.type = str(fh.get("type", card.type))
            card.title = str(fh.get("title", card.title or card.name))
            card.response_format = str(fh.get("response_format", card.response_format))
            for wb in fh.get("worldbook", []) or []:
                card.worldbook.append(WorldBookEntry.from_st(wb))
            for comp in fh.get("components", []) or []:
                card.components.append(Component(
                    name=str(comp.get("name", "")), label=str(comp.get("label", "")),
                    html=str(comp.get("html", "")), css=str(comp.get("css", "")),
                    script=str(comp.get("script", "")), ai_prompt=str(comp.get("ai_prompt", "")),
                    description=str(comp.get("description", "")),
                ))
    # character_book（V2/V3 lorebook）
    book = payload.get("character_book") or {}
    if isinstance(book, dict):
        card.lorebook = book
        for e in book.get("entries", []) or []:
            card.worldbook.append(WorldBookEntry.from_st(e))
    # FD 平台 JSON（无 spec 字段）：实测口径 name=故事名，character_name=角色名
    if spec == "" and "personality" in payload and "world_info" in payload:
        card.name = str(payload.get("character_name") or payload.get("name") or slug)
        card.title = str(payload.get("title") or payload.get("name") or "")
        card.response_format = str(payload.get("response_format", ""))
        card.category = str(payload.get("category", ""))
        for e in payload.get("world_info", []) or []:
            card.worldbook.append(WorldBookEntry.from_fd(e))
        for c in payload.get("components", []) or []:
            card.components.append(Component(
                name=str(c.get("name", "")), label=str(c.get("label", "")),
                html=str(c.get("html", "")), css=str(c.get("css", "")),
                script=str(c.get("script", "")), ai_prompt=str(c.get("ai_prompt", "")),
                description=str(c.get("description", "")),
            ))
        for q in payload.get("quick_replies", []) or []:
            card.quick_replies.append(QuickReply(
                id=str(q.get("id", "")), label=str(q.get("label", "")),
                message=str(q.get("message", "")), icon=str(q.get("icon", "")),
                intimacy_requirement=int(q.get("intimacy_requirement", 0) or 0),
                cooldown_minutes=int(q.get("cooldown_minutes", 10) or 10),
                mood_effects={str(k): int(v) for k, v in (q.get("mood_effects") or {}).items()},
                description=str(q.get("description", "")),
            ))
        if payload.get("lorebook_config"):
            card.lorebook = payload["lorebook_config"]
        card.extensions.setdefault("source_platform", "fd")
    if payload.get("assets"):
        card.assets = list(payload["assets"])
    return card


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name.strip()).strip("-")
    return slug or "imported"


def decode_embedded_card(raw: bytes) -> dict[str, Any] | None:
    """尝试把 PNG tEXt chunk 解码成 JSON（V1/V2 chara、V3 ccv3）。"""
    for enc in ("utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return None
    candidate = text
    if not text.lstrip().startswith("{"):
        try:
            candidate = base64.b64decode(text).decode("utf-8")
        except Exception:
            candidate = text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def export_full_card_md(card: Card) -> str:
    """完整角色卡单文件（卡体 + 世界书 + 组件 + 正则）——给喜欢一把梭的作者。"""
    import yaml as _yaml
    meta = {
        "slug": card.slug, "type": card.type, "name": card.name,
        "title": card.title or card.name, "description": card.description,
        "tags": card.tags, "component_set": card.component_set,
        "component_theme": card.component_theme or None,
    }
    meta = {k: v for k, v in meta.items() if v not in ("", None, [])}
    out = ["---", _yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).rstrip(), "---", ""]
    order = [
        ("personality", "人设 / 性格（personality）"),
        ("scenario", "场景（scenario）"),
        ("world_view", "世界观（world_view）"),
        ("first_mes", "开场白（first_mes）"),
        ("mes_example", "对话示例（mes_example）"),
        ("response_format", "回复格式（response_format）"),
        ("creator_notes", "创作者备注（creator_notes）"),
    ]
    for attr, heading in order:
        value = getattr(card, attr, "")
        if value:
            out += [f"# {heading}", "", value.strip(), ""]
    if card.worldbook:
        out += ["# 世界书（worldbook）", ""]
        for e in card.worldbook:
            fm = {
                "id": e.id or None, "keys": e.keys, "name": e.name or None,
                "depth": e.depth, "priority": e.priority, "constant": e.constant,
                "probability": e.probability,
            }
            fm = {k: v for k, v in fm.items() if v not in ("", None)}
            out += [f"### {e.name or e.trigger_keys_text()}", "---",
                    _yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).rstrip(),
                    "---", "", e.content.strip(), ""]
    if card.components:
        out += ["# 组件（components）", ""]
        if any(isinstance(c, Component) for c in card.components):
            for c in card.components:
                if not isinstance(c, Component):
                    continue
                out += [f"### {c.name}", "---",
                        _yaml.safe_dump({"label": c.label, "ai_prompt": c.ai_prompt,
                                         "description": c.description}, allow_unicode=True,
                                        sort_keys=False).rstrip(), "---", ""]
                if c.html:
                    out += ["```html", c.html.rstrip(), "```", ""]
                if c.css:
                    out += ["```css", c.css.rstrip(), "```", ""]
                if c.script:
                    out += ["```js", c.script.rstrip(), "```", ""]
        else:
            out += ["```yaml",
                    _yaml.safe_dump(
                        {"set": card.component_set, "theme": card.component_theme or {},
                         "components": [c if isinstance(c, str) else c.name for c in card.components]},
                        allow_unicode=True, sort_keys=False).rstrip(), "```", ""]
    if card.regex_rules:
        out += ["# 正则（regex）", "", "```yaml",
                _yaml.safe_dump([r.__dict__ for r in card.regex_rules], allow_unicode=True, sort_keys=False).rstrip(),
                "```", ""]
    if card.quick_replies:
        out += ["# 快捷回复（quick_replies）", "", "```yaml",
                _yaml.safe_dump([q.__dict__ for q in card.quick_replies], allow_unicode=True, sort_keys=False).rstrip(),
                "```", ""]
    return "\n".join(out).rstrip() + "\n"
