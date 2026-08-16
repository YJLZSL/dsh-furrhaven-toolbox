"""正则工坊：规则库 + 测试台 + 排序陷阱检查。

事实基线：FC 统一渲染 v2.3 模板包（15 条，14 启用 + 1 禁用）。
排序铁律：全匹配 wrapper 规则必须最后（否则 ^/$ 锚到 HTML 边界）；
单双星号互斥用 `(?<!\\*)\\*(?!\\*)`。
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .model import RegexRule


def load_rules(path: Path | str) -> list[RegexRule]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"正则规则文件不存在：{p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    rules: list[RegexRule] = []
    if isinstance(data, dict):
        data = data.get("rules", [])
    for item in data or []:
        rules.append(RegexRule(
            id=str(item.get("id", item.get("name", f"r{len(rules) + 1}"))),
            name=str(item.get("name", "")),
            find=str(item.get("find", "")),
            replace=str(item.get("replace", "")),
            flags=[str(f) for f in (item.get("flags") or [])],
            scope=str(item.get("scope", "ai_reply")),
            order=int(item.get("order", 10) or 10),
            enabled=bool(item.get("enabled", True)),
            dialect=str(item.get("dialect", "fc")),
            notes=str(item.get("notes", "")),
        ))
    return sorted(rules, key=lambda r: r.order)


@dataclass
class RenderResult:
    output: str
    hits: list[tuple[RegexRule, int]]  # (规则, 命中次数)


def apply_rules(rules: list[RegexRule], text: str, scope: str = "ai_reply") -> RenderResult:
    out = text
    hits: list[tuple[RegexRule, int]] = []
    for rule in rules:
        if rule.scope != scope:
            continue
        rendered, n = rule.apply(out)
        if n == -1:
            hits.append((rule, -1))  # 正则错误
            continue
        if n:
            hits.append((rule, n))
            out = rendered
    return RenderResult(output=out, hits=hits)


def render_html_preview(result: RenderResult) -> str:
    """Markdown/HTML 双视图里的 HTML 视图：按命中高亮显示。"""
    body = html.escape(result.output)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:serif;max-width:760px;margin:24px auto;padding:0 16px;"
        "white-space:pre-wrap;line-height:1.7;background:#faf6ee;color:#333}</style></head>"
        f"<body>{body}</body></html>"
    )


@dataclass
class RegexWarning:
    rule: RegexRule
    rule_id: str
    message: str


def check_rules(rules: list[RegexRule]) -> list[RegexWarning]:
    warnings: list[RegexWarning] = []
    enabled = [r for r in rules if r.enabled]
    for r in enabled:
        try:
            re.compile(r.find, r.pattern_flags)
        except re.error as e:
            warnings.append(RegexWarning(r, "REGEX-COMPILE", f"正则无法编译：{e}"))
    # 全匹配 wrapper 必须在最后
    wrappers = [r for r in enabled if r.find in ("^([\\s\\S]+)$", "^(.*)$", "^[\\s\\S]*$", "^.*$")]
    if wrappers:
        last_enabled = enabled[-1]
        for w in wrappers:
            if w.id != last_enabled.id:
                warnings.append(RegexWarning(w, "REGEX-WRAPPER-LAST", f"全匹配 wrapper「{w.id}」必须排在最后（否则 ^/$ 锚到 HTML 边界）"))
    # 单双星号互斥
    for r in enabled:
        has_star = "\\*" in r.find or "*" in r.find
        has_dstar = "**" in r.find.replace("\\**", "") or "\\*\\*" in r.find
        if has_star and has_dstar and "(?<!\\*)\\*(?!\\*)" not in r.find:
            warnings.append(RegexWarning(r, "REGEX-STAR-CONFLICT", f"「{r.id}」同时匹配单/双星号，建议用 (?<!\\*)\\*(?!\\*) 互斥"))
    # 规则间覆盖冲突（同一输入区间的粗查）
    for i, a in enumerate(enabled):
        for b in enabled[i + 1 :]:
            if a.find == b.find:
                warnings.append(RegexWarning(b, "REGEX-OVERLAP", f"「{b.id}」与「{a.id}」find 完全一致，后规则覆盖前规则"))
    return warnings


def rules_to_markdown(rules: list[RegexRule]) -> str:
    lines = ["# 正则脚本 — Furrhaven 导出", "", f"规则总数：{len(rules)} 条", ""]
    for r in sorted(rules, key=lambda x: x.order):
        state = "启用" if r.enabled else "禁用"
        lines += [f"## {r.order}. {r.name}（{state}）", "",
                  f"- 查找：`{r.find}`", f"- 替换为：`{r.replace}`",
                  f"- 匹配选项：`{''.join(r.flags)}`", f"- 作用范围：{r.scope}", ""]
    return "\n".join(lines).rstrip() + "\n"


def bundled_rules_path() -> Path:
    return Path(__file__).resolve().parent / "resources" / "regex_v23.yaml"


def load_bundled_rules() -> list[RegexRule]:
    return load_rules(bundled_rules_path())
