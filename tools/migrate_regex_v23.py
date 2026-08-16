#!/usr/bin/env python3
"""把参考项目《正则脚本_统一渲染_v2.3.md》迁移为 Furrhaven 正则包 YAML。

用法：
  python tools/migrate_regex_v23.py "<参考项目路径>/正则脚本_统一渲染_v2.3.md" [输出.yaml]

这是资产迁移器（一次性批量工具按纪律保留在 tools/，不留在引擎里）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def parse_doc(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"\n### 脚本", text)
    rules: list[dict] = []
    for sec in sections[1:]:
        num_m = re.match(r"\s*(\d+)\s*[：:]\s*([^\n]+)", sec)
        if not num_m:
            continue
        num = int(num_m.group(1))
        name = num_m.group(2).strip()
        # 内联代码：单反引号或双反引号包裹（规则 3 的 find 内含反引号，用双反引号）
        find_m = re.search(r"\*\*查找（正则表达式）\*\*\s*\|\s*(``|`)(.*?)\1", sec, re.S)
        flags_m = re.search(r"\*\*匹配选项\*\*\s*\|\s*`([^`]*)`", sec)
        find = (find_m.group(2) if find_m else "").strip()
        flags_raw = flags_m.group(1).strip() if flags_m else ""
        rep_m = re.search(r"\*\*替换为\*\*\s*\|\s*(.+?)\s*\|", sec, re.S)
        replace = ""
        if rep_m:
            cell = rep_m.group(1).strip()
            if "见下方代码块" in cell:
                code_m = re.search(r"```(?:html)?\s*\n(.*?)```", sec, re.S)
                if code_m:
                    replace = code_m.group(1).strip()
            elif "留空" in cell or "删除匹配内容" in cell:
                replace = ""
            else:
                replace = cell.strip("` ").strip()
        flags: list[str] = []
        if "s" in flags_raw:
            flags.append("DOTALL")
        if "m" in flags_raw:
            flags.append("MULTILINE")
        rules.append({
            "id": f"fc-v23-{num:02d}",
            "name": name,
            "find": find,
            "replace": replace,
            "flags": flags,
            "scope": "ai_reply",
            "order": num,
            "enabled": "禁用" not in name and "已禁用" not in sec[:400],
            "dialect": "fc",
            "notes": "FC 统一渲染 v2.3 模板包（自参考项目迁移）",
        })
    return rules


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / \
        "furrhaven-core" / "furrhaven" / "resources" / "regex_v23.yaml"
    rules = parse_doc(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(rules, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    enabled = sum(1 for r in rules if r["enabled"])
    print(f"migrated {len(rules)} rules ({enabled} enabled) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
