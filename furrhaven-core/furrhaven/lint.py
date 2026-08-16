"""规则包引擎（lint）：题材与质量解耦，知识内化为检查器。

规则 ID 协议：
  IR-*        IR 结构
  FD-*        FD 平台硬知识
  WB-*        世界书
  COMP-*      组件五坑/拉长四禁
  REGEX-*     正则排序陷阱
  BYTE-*      字节口径
  CONTENT-*   内容残留
  PROSE-*     活人感文风（quality-core）
  FURRY-*     genre-furry 包（默认关）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .budget import compute_budget
from .components import check_component
from .model import Card, Component
from .regexlab import check_rules
from .worldbook import analyze_keys

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


@dataclass
class Problem:
    rule_id: str
    severity: str      # error | warning
    message: str
    card: str = ""
    fix_hint: str = ""

    def format(self) -> str:
        loc = f"[{self.card}] " if self.card else ""
        return f"{self.severity.upper()} {self.rule_id} {loc}{self.message}" + (
            f"  → 修复：{self.fix_hint}" if self.fix_hint else ""
        )


@dataclass
class LintReport:
    problems: list[Problem] = field(default_factory=list)

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.severity == "error"]

    @property
    def warnings(self) -> list[Problem]:
        return [p for p in self.problems if p.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def exit_code(self) -> int:
        return EXIT_OK if self.ok else EXIT_ERROR

    def render(self) -> str:
        if not self.problems:
            return "✓ 0 problems"
        lines = [f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"]
        lines += [p.format() for p in self.problems]
        return "\n".join(lines)


def _p(report: LintReport, rule_id: str, severity: str, message: str,
       card: str = "", fix_hint: str = "") -> None:
    report.problems.append(Problem(rule_id, severity, message, card, fix_hint))


# ── IR 结构 ──────────────────────────────────────────────────────────────────
def lint_ir(card: Card, report: LintReport) -> None:
    required = ["name", "personality", "first_mes", "response_format"]
    for attr in required:
        if not getattr(card, attr, "").strip():
            _p(report, "IR-REQUIRED", "error", f"缺少 {attr}（卡体核心字段）",
               card.slug, f"补全 cards/{card.slug} 对应分区")
    if card.type in ("character", "character.activity") and not card.scenario and not card.world_view:
        _p(report, "IR-FREEMODE", "warning",
           "自由模式卡 scenario/world_view 置空属正常，但世界观内容应并入 personality 分区",
           card.slug)
    if len(card.name) > 60:
        _p(report, "IR-NAME-LEN", "warning", f"角色名过长（{len(card.name)} 字符）", card.slug)


# ── FD 平台硬知识 ────────────────────────────────────────────────────────────
def lint_fd(card: Card, components: list[Component], platforms_cfg: dict[str, Any],
            report: LintReport) -> None:
    fd_limits = platforms_cfg.get("platforms", {}).get("fd", {})
    # 组件
    for c in components:
        for prob in check_component(c, platforms_cfg, node_check=True):
            _p(report, prob.rule, "error" if prob.fatal else "warning",
               f"组件 {c.name}：{prob.message}", card.slug)
    # 世界书条目字段
    ids = []
    for e in card.worldbook:
        if not str(e.id).isdigit():
            _p(report, "WB-ID", "error", f"世界书条目「{e.name or e.trigger_keys_text()}」id 不是数字（时间戳格式）",
               card.slug, "fh wb add 自动分配")
        else:
            ids.append(int(e.id))
        if not e.keys and not e.constant:
            _p(report, "WB-KEYS-MISSING", "error", f"世界书条目「{e.name}」缺少 keys",
               card.slug, "给条目配置逗号分隔触发词")
    if len(ids) != len(set(ids)):
        _p(report, "WB-DUP-ID", "error", "世界书存在重复 id（平台导入会互相覆盖）", card.slug)
    # 系统条目
    sys_needed = {"character": 5, "character.activity": 5, "simulator": 4, "bigworld": 6, "custom": 0}
    sys_count = len(card.system_entries())
    need = sys_needed.get(card.type, 0)
    if need and sys_count != need:
        _p(report, "WB-SYS-COUNT", "error" if sys_count == 0 else "warning",
           f"系统条目应有 {need} 个，实际 {sys_count} 个", card.slug,
           "fh new 模板预填系统条目；fh wb add --system 补")
    # 快捷回复
    for q in card.quick_replies:
        if not q.message:
            _p(report, "QR-MESSAGE", "error", f"快捷回复「{q.label or q.id}」缺少 message（按钮点击无响应）", card.slug)
    # 字节口径
    budget = compute_budget(card, "fd", platforms_cfg, components)
    if budget.over:
        _p(report, "BYTE-FD-OVER", "error",
           f"FD 卡字节超限：{budget.used}/{budget.limit}（口径 v3.0 保守）", card.slug,
           "fh budget --platform fd 看字段余量表，压缩 personality/response_format")
    report.problems.append(Problem("BYTE-FD-REPORT", "warning",
                                   f"FD 字节核算 {budget.used}/{budget.limit}（余 {budget.remaining}）", card.slug))


def lint_fc_fb(card: Card, platforms_cfg: dict[str, Any], report: LintReport,
               platforms: list[str] | None = None) -> None:
    for platform in platforms or ["fc", "fb"]:
        budget = compute_budget(card, platform, platforms_cfg)
        if budget.over:
            _p(report, f"BYTE-{platform.upper()}-OVER", "error",
               f"{platform.upper()} 字节超限：{budget.used}/{budget.limit}", card.slug,
               "FB 压缩链：跨章节去重→迁世界书→零损失删减")
        else:
            report.problems.append(Problem(f"BYTE-{platform.upper()}-REPORT", "warning",
                                           f"{platform.upper()} 字节 {budget.used}/{budget.limit}", card.slug))


# ── 世界书 keys 分析 ─────────────────────────────────────────────────────────
def lint_worldbook_keys(card: Card, project=None, report: LintReport | None = None) -> LintReport:
    report = report or LintReport()
    extra = []
    if project is not None:
        extra = list(project.config.get("lexicon", {}).get("forbidden_words") or [])
    for w in analyze_keys(card.worldbook, extra):
        _p(report, "WB-KEYS", "warning", f"「{w.entry.name or w.entry.trigger_keys_text()}」：{w.reason}",
           card.slug)
    return report


# ── 内容类（quality-core） ───────────────────────────────────────────────────
def lint_content(card: Card, config: dict[str, Any], report: LintReport) -> None:
    lexicon = config.get("lexicon", {})
    residue_words = ["TODO", "待补充", "示例文本", "占位", "XXX", "<示例>", "lorem ipsum"]
    dash_max = 1
    notab_max = 2

    def scan_field(name: str, text: str) -> None:
        if not text:
            return
        for word in residue_words:
            if word.lower() in text.lower():
                _p(report, "CONTENT-RESIDUE", "error", f"{name} 含模板残留词「{word}」", card.slug,
                   "整分区重写，勿逐段 patch（整体重写优先纪律）")
        paragraphs = [p for p in text.splitlines() if p.strip()]
        for p in paragraphs:
            if p.count("——") + p.count("—") > dash_max:
                _p(report, "PROSE-DASH", "warning", f"{name} 段落破折号超限：{p[:60]}…", card.slug,
                   "破折号能拆就拆，每段最多 1 个")
        notab = len(re.findall(r"不是[^，。；]{1,40}是", text))
        if notab > notab_max:
            _p(report, "PROSE-NOTAB", "warning", f"{name}「不是A是B」{notab} 次（限 {notab_max}）", card.slug)
        for word in lexicon.get("dead_metaphors", []):
            if word in text:
                _p(report, "PROSE-DEAD-METAPHOR", "warning", f"{name} 含死物比喻「{word}」", card.slug,
                   "全部改白描，或换成贴人设的活的比喻")

    for attr in ("personality", "scenario", "world_view", "first_mes", "mes_example", "creator_notes"):
        scan_field(attr, getattr(card, attr, ""))
    # 好感节奏铁令 12/13（character 恋爱向默认预填；仅提示缺失，不强制非恋爱卡）
    rf = card.response_format
    if card.type == "character":
        has12 = "<level>" in rf or "好感" in rf
        has13 = "<stage>" in rf or "stage1" in rf.lower()
        if not has12:
            _p(report, "QUALITY-AFFECTION-12", "warning", "response_format 未见好感铁令12（<level> 递增+冷却+禁跳涨）",
               card.slug, "新卡模板默认预填；非恋爱卡可在 card.yaml 显式关闭 quality-affection")
        if not has13:
            _p(report, "QUALITY-AFFECTION-13", "warning", "response_format 未见好感铁令13（<stage> 逐级门控）",
               card.slug, "同铁令12")


# ── genre-furry 包（默认关） ─────────────────────────────────────────────────
def lint_genre_furry(card: Card, report: LintReport) -> None:
    text = "\n".join([
        card.personality, card.scenario, card.world_view, card.first_mes,
        card.mes_example, card.response_format,
    ])
    npc_prefix = re.compile(r"(NPC|路人|女性|女[角色生]|她?是[^。]{0,12}女)")
    for m in re.finditer(r"[^。\n]{0,40}(她|姑娘|女孩|小姐)[^。\n]{0,40}", text):
        ctx = m.group(0)
        if npc_prefix.search(ctx):
            continue
        _p(report, "FURRY-GENDER-REDLINE", "error",
           f"疑似女性指代玩家：{ctx.strip()[:80]}", card.slug,
           "玩家一律男性，指代用「他」；女性 NPC 才可用「她」")


# ── 正则规则 ─────────────────────────────────────────────────────────────────
def lint_regex(card: Card, report: LintReport) -> None:
    for w in check_rules(card.regex_rules):
        _p(report, w.rule_id, "error", f"正则「{w.rule.id}」：{w.message}", card.slug)


# ── 聚合入口 ─────────────────────────────────────────────────────────────────
def run_lints(card: Card, components: list[Component], platforms_cfg: dict[str, Any],
              project=None, platforms: list[str] | None = None,
              enabled_packs: set[str] | None = None) -> LintReport:
    report = LintReport()
    config = project.config if project is not None else {}
    packs = enabled_packs if enabled_packs is not None else {
        "quality-core": True, "genre-furry": False,
        "type-simulator": card.type == "simulator", "type-bigworld": card.type == "bigworld",
    }
    lint_ir(card, report)
    if "fd" in (platforms or ["fd"]):
        lint_fd(card, components, platforms_cfg, report)
    if any(p in (platforms or []) for p in ("fc", "fb")):
        lint_fc_fb(card, platforms_cfg, report, platforms)
    lint_worldbook_keys(card, project, report)
    if packs.get("quality-core", True):
        lint_content(card, config, report)
    if packs.get("genre-furry", False):
        lint_genre_furry(card, report)
    if card.regex_rules:
        lint_regex(card, report)
    return report
