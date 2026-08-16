"""Furrhaven 核心引擎单测。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from furrhaven.budget import compute_budget  # noqa: E402
from furrhaven.components import check_component  # noqa: E402
from furrhaven.config import load_bundled_platforms  # noqa: E402
from furrhaven.exporters import fd_card, st_v2, st_v3  # noqa: E402
from furrhaven.lint import LintReport, run_lints  # noqa: E402
from furrhaven.model import Card, Component, RegexRule, WorldBookEntry  # noqa: E402
from furrhaven.parsers import load_card, parse_card_text  # noqa: E402
from furrhaven.png import read_card_png, write_card_png  # noqa: E402
from furrhaven.regexlab import apply_rules, check_rules  # noqa: E402
from furrhaven.worldbook import analyze_keys, simulate_triggers  # noqa: E402

PLATFORMS = load_bundled_platforms()


def sample_card() -> Card:
    c = Card(slug="sample", name="灰野", title="测试卡")
    c.personality = "## 1. 基础\n灰狼少年。"
    c.scenario = ""
    c.world_view = ""
    c.first_mes = "你好。"
    c.response_format = "1. 面板。\n12. <level> 递增。\n13. <stage> 门控。"
    c.worldbook = [
        WorldBookEntry(id=1, keys=["系统-角色"], content="当前角色为灰野。", constant=True, priority=1, depth=0),
        WorldBookEntry(id=2, keys=["青澜", "城市"], content="青澜市是一座沿海城市。", priority=500, depth=3),
    ]
    return c


# ── 解析器：多写法宽容 ────────────────────────────────────────────────────────
def test_parse_full_card_with_worldbook():
    text = """---
name: 测试角色
type: character
---
# 性格设定
性格内核。

# 开场白
你好。

# 世界书
### 系统-角色
---
id: 1750000001
keys: [系统-角色]
constant: true
priority: 1
---
当前角色为测试角色。

### 城市
---
id: 1750000002
keys: [青澜, 城市]
---
青澜市是一座沿海城市。
"""
    r = parse_card_text(text, "test")
    assert r.card.name == "测试角色"
    assert r.card.personality.strip() == "性格内核。"
    assert len(r.card.worldbook) == 2
    assert r.card.worldbook[1].content == "青澜市是一座沿海城市。"


def test_parse_free_mode_style_headings():
    text = "# name\n灰野\n\n# personality\n灰狼。\n\n# first_mes\n你好。\n"
    r = parse_card_text(text, "free")
    assert r.card.name == "灰野"
    assert r.card.personality == "灰狼。"
    assert r.card.first_mes == "你好。"


def test_import_st_v3_json():
    obj = {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "name": "Test",
            "personality": "kind",
            "first_mes": "hi",
            "character_book": {
                "entries": [{"keys": ["k"], "content": "lore", "enabled": True, "insertion_order": 0, "constant": False}],
            },
            "extensions": {"furrhaven": {"type": "character", "response_format": "fmt"}},
        },
    }
    from furrhaven.parsers import import_st_json
    card = import_st_json(obj)
    assert card.name == "Test"
    assert card.worldbook[0].content == "lore"
    assert card.response_format == "fmt"


# ── 世界书工坊 ───────────────────────────────────────────────────────────────
def test_trigger_simulator_direct_and_constant():
    card = sample_card()
    hits, _ = simulate_triggers(card.worldbook, "我来到青澜")
    assert any(h.entry.id == 1 for h in hits)
    assert any(h.entry.id == 2 and h.via == "direct" for h in hits)


def test_trigger_simulator_recursive():
    a = WorldBookEntry(id=1, keys=["触发A"], content="触发A 的正文提到触发B。", priority=500)
    b = WorldBookEntry(id=2, keys=["触发B"], content="B 正文。", priority=500)
    hits, _ = simulate_triggers([a, b], "这是触发A")
    assert any(h.entry.id == 2 and h.via == "recursive" for h in hits)


def test_keys_analyzer_flags_generic_key():
    e = WorldBookEntry(id=1, keys=["你"], content="正文", constant=False)
    warns = analyze_keys([e])
    assert any(w.key == "你" for w in warns)


# ── 字节口径 ─────────────────────────────────────────────────────────────────
def test_fd_budget_utf8_bytes():
    card = sample_card()
    card.personality = "字" * 1000
    card.response_format = ""
    report = compute_budget(card, "fd", PLATFORMS, [])
    assert report.used == 3000  # 中文 1 字 = 3 UTF-8 字节
    assert report.remaining == 47000


def test_fc_budget_total_package_limit():
    card = sample_card()
    report = compute_budget(card, 'fc', PLATFORMS, [])
    assert report.limit == 40000  # 2026-08-16 用户口径：资料包总限
    assert '世界书' in report.fields and '正则' in report.fields


def test_fd_budget_worldbook_overflow_counts():
    card = sample_card()
    card.worldbook.append(WorldBookEntry(id=99, keys=["k"], content="字" * 20000))
    report = compute_budget(card, "fd", PLATFORMS, [])
    assert "世界书超独立额度" in "\n".join(report.notes)


# ── 组件工坊 ─────────────────────────────────────────────────────────────────
def test_component_five_pitfalls():
    bad = Component(name="bad", id="notbad", html="<style>x</style>", css=":root{}",
                    script="clean('$scene$'); setInterval(f, 1000);")
    probs = check_component(bad, PLATFORMS, node_check=False)
    ids = {p.rule for p in probs}
    assert "COMP-ID" in ids
    assert "COMP-HTML-TAG" in ids
    assert "COMP-CSS-ROOT" in ids
    assert "COMP-VAR-SCRIPT" in ids
    assert "COMP-STRETCH-INTERVAL" in ids


def test_component_source_limit():
    big = Component(name="big", html="x" * 21000, css="", script="")
    probs = check_component(big, PLATFORMS, node_check=False)
    assert any(p.rule == "COMP-SOURCE-LIMIT" for p in probs)


# ── 正则工坊 ─────────────────────────────────────────────────────────────────
def test_regex_apply_and_preview():
    rules = [RegexRule(id="bold", name="加粗", find=r"^>(.+)$", replace=r"**$1**",
                       flags=["MULTILINE"], order=1)]
    out = apply_rules(rules, ">你好\n正文", "ai_reply")
    assert out.output == "**你好**\n正文"
    assert out.hits[0][1] == 1


def test_regex_wrapper_last_check():
    rules = [
        RegexRule(id="wrap", name="容器", find=r"^([\s\S]+)$", replace="<div>$1</div>",
                  flags=["DOTALL"], order=1),
        RegexRule(id="bold", name="加粗", find=r"\*\*(.+?)\*\*", replace="$1", order=2),
    ]
    warns = check_rules(rules)
    assert any(w.rule_id == "REGEX-WRAPPER-LAST" for w in warns)


def test_bundled_regex_template():
    from furrhaven.regexlab import load_bundled_rules
    rules = load_bundled_rules()
    assert len(rules) == 15
    assert sum(r.enabled for r in rules) == 14
    assert rules[-1].order == 15  # wrapper 最后


# ── PNG 导出（酒馆本体 V2/V3） ───────────────────────────────────────────────
def test_png_v2_v3_roundtrip(tmp_path: Path):
    card = sample_card()
    p2 = write_card_png(st_v2(card), tmp_path / "v2.png", include_v2=True, include_v3=False)
    p3 = write_card_png(st_v3(card), tmp_path / "v3.png", include_v2=False, include_v3=True)
    v2 = read_card_png(p2)
    v3 = read_card_png(p3)
    assert v2["spec"] == "chara_card_v2"
    assert v3["spec"] == "chara_card_v3"
    assert v2["data"]["name"] == "灰野"
    assert v3["data"]["character_book"]["entries"][0]["keys"] == ["系统-角色"]


def test_st_v3_lorebook_shape():
    card = sample_card()
    v3 = st_v3(card)
    entry = v3["data"]["character_book"]["entries"][0]
    assert "use_regex" in entry
    assert entry["insertion_order"] == 0


# ── FD 导出 ──────────────────────────────────────────────────────────────────
def test_fd_card_structure_and_json_roundtrip(tmp_path: Path):
    card = sample_card()
    fd = fd_card(card, [])
    assert fd["vn_mode_enabled"] is False
    assert fd["world_info"][0]["id"] == 1
    assert fd["name"] == "测试卡"          # 实测口径：name=故事名，character_name=角色名
    assert fd["character_name"] == "灰野"
    p = tmp_path / "card.json"
    p.write_text(json.dumps(fd, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    assert json.loads(p.read_text(encoding="utf-8"))["character_name"] == "灰野"


# ── lint 门禁 ────────────────────────────────────────────────────────────────
def test_lint_gate_catches_quick_reply_and_byte():
    from furrhaven.model import QuickReply
    card = sample_card()
    card.quick_replies.append(QuickReply(id="q", label="按钮", message=""))
    report = run_lints(card, [], PLATFORMS, None, platforms=["fd"],
                       enabled_packs={"quality-core": False, "genre-furry": False,
                                      "type-simulator": False, "type-bigworld": False})
    assert any(p.rule_id == "QR-MESSAGE" for p in report.problems)


def test_lint_exit_code_protocol():
    card = sample_card()
    report = run_lints(card, [], PLATFORMS, None, platforms=["fd"],
                       enabled_packs={"quality-core": False, "genre-furry": False,
                                      "type-simulator": False, "type-bigworld": False})
    assert report.exit_code in (0, 1)
