#!/usr/bin/env python3
"""生成 docs/04-资产盘点表.md：参考项目 118 脚本逐个标「迁移泛化/教训入 lint/不迁移」。

用法：
  python tools/make_asset_inventory.py "<参考项目>/04-工具" docs/04-资产盘点表.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# 交接文档 §四 已知迁移候选
MIGRATE = {
    "components_lib.py", "rebuild_card.py", "gen_free_mode_card.py",
    "update_simulator_card_v2.py", "export_review_md.py", "apply_review_to_json.py",
    "audit_fd_cards.py", "check_free_mode_counts.py", "fd_json_check.py",
    "fd_reply_format_check.py", "fc_fb_redline_check.py", "sync_to_upload.py",
    "expand_worldbook_lore.py",
}
# 明确的一次性修复脚本：教训入 lint，不迁移
LESSON_PATTERNS = [
    r"^fix_", r"^add_", r"^remove_", r"^revert_", r"^rewrite_", r"^rework_",
    r"^_", r"^p10_", r"^p11_", r"^p21_", r"^p22_", r"^p30_", r"^p31_",
    r"^align_", r"^sync_desc", r"^recalc", r"^rebuild_ruikesi",
]
# 概念/演示/排查类：教训入 lint，产物不迁移
LESSON_EXACT = {
    "check_all.py", "regex_verify_v2.2.py", "regex_verify_v2.3.py",
    "probe_anim_event.py", "shot_firework_demo.py", "scan_encoding.py",
    "scan_prose_all.py", "scan_prose_deep.py", "audit_docs.py", "audit_crosscard.py",
    "audit_optimization.py", "redundancy_check.py", "compress_worldbook.py",
    "exp_weather_impl.py", "build_firework_weather.py", "gen_weather_anim_demo.py",
    "gen_weather_demo.py", "gen_firework_live_demo.py", "gen_vn_showcase.py",
    "gen_components_showcase.py", "gen_component_slim.py", "gen_component_slim_demo.py",
    "gen_component_upgrade_demo.py", "gen_silent_horizon_components.py",
    "gen_fd_design_brief.py", "gen_fd_manual.py", "apply_reply_format.py",
    "p10_split_components.py", "rework_syscards.py", "rework_titles_notes.py",
    "rework_upload_fields.py", "rework_vn_format.py", "rework_fd_fields.py",
    "rework_opening.py", "update_affection_rule.py", "add_affection_pace_rule.py",
    "fix_world_info_keys.py", "fix_yaochen_keys.py", "fix_yaochen_desc.py",
    "fix_yaochen_military_setting.py", "fix_yaochen_quickreplies.py",
    "fix_yaochen_worldinfo.py", "fix_yaochen_childhood_entry.py",
    "fix_yaochen_market_entry.py", "fix_yaochen_personality_entry.py",
    "fix_yaochen_shop_springfest.py", "verify_all_fixes.py", "verify_firework_card.py",
    "verify_settings_final.py", "verify_shared_worldbook.py",
    "pilot_lichang_sys.py", "preupload_final_check.py", "ruikesi_legacy.py",
}
NOT_MIGRATE_EXACT = {
    "草稿转FD上传JSON.py",
}


def classify(name: str) -> str:
    if name in MIGRATE:
        return "迁移泛化"
    if name in NOT_MIGRATE_EXACT:
        return "不迁移"
    if name in LESSON_EXACT:
        return "教训入 lint"
    for pat in LESSON_PATTERNS:
        if re.match(pat, name):
            return "教训入 lint"
    if name.startswith("gen_") or name.startswith("verify_") or name.startswith("scan_"):
        return "教训入 lint"
    return "不迁移（专项残留）"


def note_for(name: str) -> str:
    mapping = {
        "components_lib.py": "组件库单一源注入引擎 → fh.components",
        "rebuild_card.py": "母卡→FD JSON 转换器 → fh.build + fh.export.fd",
        "gen_free_mode_card.py": "自由模式转换器 → fh.export.fd 自由模式口径",
        "update_simulator_card_v2.py": "模拟器卡更新器 → simulator 卡型（M8）",
        "export_review_md.py": "JSON→审阅稿单向导出 → fh review export",
        "apply_review_to_json.py": "审阅稿→JSON 回写 + 状态机锁 → fh review apply",
        "audit_fd_cards.py": "字节口径 v3.0 核算 → fh.budget",
        "check_free_mode_counts.py": "自由模式单卡核算 → fh.budget --card",
        "fd_json_check.py": "FD 结构门禁 C1-C12 → fh.lint FD 规则",
        "fd_reply_format_check.py": "回复格式静态 lint → fh.lint COMP/RESPONSE 规则",
        "fc_fb_redline_check.py": "FC/FB 红线 → fh.lint BYTE-FC/FB",
        "sync_to_upload.py": "FC 主版本→上传包单向同步 → fh.export.fc",
        "expand_worldbook_lore.py": "共享世界观条目写入 → fh.worldbook shared/",
    }
    return mapping.get(name, "")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    scripts = sorted(src.glob("*.py"))
    rows = []
    for p in scripts:
        verdict = classify(p.name)
        rows.append((p.name, verdict, note_for(p.name)))
    n_migrate = sum(1 for _, v, _ in rows if v == "迁移泛化")
    n_lesson = sum(1 for _, v, _ in rows if v == "教训入 lint")
    n_skip = sum(1 for _, v, _ in rows if v.startswith("不迁移"))
    lines = [
        "# Furrhaven · 资产盘点表",
        "",
        "> 版本：1.0 | 2026-08-16 | 权威级别：盘点快照 | 上游来源：参考项目 `个人角色卡（平台参考）\\04-工具\\`",
        "> 结论：118 个脚本 → 13 个迁移泛化（引擎已在 v0.1 落地核心）、教训全部转 lint 规则、一次性修复脚本不迁移。",
        "",
        f"- 迁移泛化：{n_migrate}",
        f"- 教训入 lint：{n_lesson}",
        f"- 不迁移：{n_skip}",
        f"- 合计：{len(rows)}",
        "",
        "| 脚本 | 处置 | 备注 |",
        "|------|------|------|",
    ]
    for name, verdict, note in rows:
        lines.append(f"| {name} | {verdict} | {note} |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"inventory {len(rows)} scripts -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
