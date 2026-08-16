"""字节口径引擎：口径表驱动，UTF-8 字节核算。

口径 v3.0（FD，参考项目 2026-08-04 平台实测）：
  卡已使用 = personality + scenario + world_view + mes_example + response_format
            + 组件 ai_prompt（平台口径含组件 ai_prompt；v3.1 显示口径只算
            personality+response_format，本引擎默认取更严的 v3.0 保守口径）。
  不计入：first_mes / quick_replies / 正则 / 组件源码 / world_info / 标题简介。
  世界书独立 30,000 字节（可超，超出部分计入卡额度）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model import Card, Component


def utf8_len(text: str) -> int:
    return len((text or "").encode("utf-8"))


@dataclass
class BudgetReport:
    platform: str
    limit: int
    used: int
    remaining: int
    fields: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    over: bool = False

    def table(self) -> str:
        lines = [
            f"[{self.platform}] 已使用 {self.used} / {self.limit} 字节（余 {self.remaining}）"
            + ("  ⚠ 超限" if self.over else "  ✓"),
        ]
        for k, v in self.fields.items():
            lines.append(f"  {k}: {v}")
        for n in self.notes:
            lines.append(f"  · {n}")
        return "\n".join(lines)


def _fd_budget(card: Card, components: list[Component], limits: dict[str, Any]) -> BudgetReport:
    counted = list(limits.get("counted_fields") or [])
    fields: dict[str, int] = {}
    used = 0
    core = card.core_text_fields()
    for key in counted:
        n = utf8_len(core.get(key, ""))
        fields[key] = n
        used += n
    ai_prompt_total = 0
    for c in components:
        ai_prompt_total += utf8_len(c.ai_prompt)
    if limits.get("component_ai_prompt_counted", True):
        fields["components.ai_prompt"] = ai_prompt_total
        used += ai_prompt_total
    limit = int(limits.get("card_limit_bytes", 50000))
    report = BudgetReport(platform="fd", limit=limit, used=used, remaining=limit - used, fields=fields)
    wb_bytes = sum(utf8_len(e.content) for e in card.worldbook)
    wb_limit = int(limits.get("worldbook_limit_bytes", 30000))
    report.notes.append(f"世界书 content 合计 {wb_bytes} / {wb_limit} 字节（独立额度）")
    if wb_bytes > wb_limit:
        overflow = wb_bytes - wb_limit
        report.notes.append(f"世界书超独立额度 {overflow} 字节，将计入卡总预算")
        report.used += overflow
        report.remaining = limit - report.used
    for c in components:
        src = c.source_bytes
        src_limit = int(limits.get("component_source_limit_bytes", 20000))
        if src > src_limit:
            report.notes.append(f"组件 {c.name} source {src} > {src_limit} 字节（平台硬限）")
    report.over = report.used > limit
    return report


def _simple_budget(card: Card, platform: str, limits: dict[str, Any]) -> BudgetReport:
    limit = int(limits.get("card_limit_bytes", 0) or 0)
    # FC：卡+开场白+简介+回复格式；FB：整卡 md
    if platform == "fc":
        from .exporters import fc_markdown
        used = utf8_len(fc_markdown(card)) + utf8_len(card.first_mes) + utf8_len(card.description) + utf8_len(card.response_format)
        fields = {"卡md": utf8_len(fc_markdown(card)), "first_mes": utf8_len(card.first_mes),
                  "description": utf8_len(card.description), "response_format": utf8_len(card.response_format)}
    else:
        from .exporters import fb_markdown
        used = utf8_len(fb_markdown(card))
        fields = {"整卡md": used}
    return BudgetReport(platform=platform, limit=limit, used=used, remaining=limit - used,
                        fields=fields, over=limit > 0 and used > limit)


def compute_budget(card: Card, platform: str, platforms_cfg: dict[str, Any],
                   components: list[Component] | None = None) -> BudgetReport:
    limits = (platforms_cfg.get("platforms") or {}).get(platform, {})
    if platform == "fd":
        return _fd_budget(card, components or [], limits)
    return _simple_budget(card, platform, limits)


def audit_project(cards: list[tuple[Card, list[Component]]], platforms_cfg: dict[str, Any],
                  platforms: list[str] | None = None) -> list[BudgetReport]:
    reports = []
    for card, comps in cards:
        for p in platforms or ["fd", "fc", "fb"]:
            reports.append(compute_budget(card, p, platforms_cfg, comps))
    return reports
