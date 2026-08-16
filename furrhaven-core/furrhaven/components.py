"""组件工坊：FD 式 VN 组件创作-管理-注入-验收全链路。

平台硬知识全部规则化（参考项目全流程文档 §5 + FD JSON 规范 §5 + AGENTS.md）：
五坑：$变量$ 只许在 html / id 字符串=name / html 禁 style·script·meta /
source ≤20,000（JSON 转义后）/ 占位符 ↔ 消息标签参数名对齐。
拉长四禁：infinite 真实动画 / min-height 撑高 / fixed 全屏层 / setInterval 改 DOM。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import Project
from .model import Card, Component

HTML_TEMPLATE = """<div class="{name}">
  <span class="sh-data" data-scene="$scene$"></span>
  <div class="d-scene">$scene$</div>
</div>"""

CSS_TEMPLATE = """.{name} {{
  font-family: "Noto Serif SC", "Source Han Serif SC", serif;
  color: %COLOR%;
  line-height: 1.4;
}}
.sh-data {{ display: none !important; }}
"""

JS_TEMPLATE = """(() => {{
  const root = document.getElementById('{name}');
  if (!root) return;
  const read = (sel) => {{
    const el = root.querySelector(sel);
    return el ? el.textContent.trim() : '';
  }};
  const clean = (v) => (!v || v.indexOf('$') !== -1) ? '' : v;
  const scene = clean(read('.d-scene'));
  if (!scene) root.style.display = 'none';
  const report = () => {{
    try {{
      const frame = window.frameElement;
      parent.postMessage({{
        type: 'story-component-resize',
        id: frame ? frame.id : '{name}',
        height: document.body.scrollHeight,
      }}, '*');
    }} catch (_) {{ /* 非 iframe 环境忽略 */ }}
  }};
  [150, 500, 1200].forEach((ms) => setTimeout(report, ms));
}})();
"""

META_TEMPLATE = {
    "id": "{name}",
    "name": "{name}",
    "label": "自定义组件 {name}",
    "render": "iframe",
    "slots": [{"name": "scene", "required": True, "desc": "场景名"}],
    "theme": {"color": "%COLOR%"},
}


@dataclass
class ComponentProblem:
    component: str
    rule: str
    message: str
    fatal: bool = True


def load_component_dir(d: Path) -> Component:
    """从四件套单一源（html.html/style.css/script.js/meta.json）读取组件。"""
    html = (d / "html.html").read_text(encoding="utf-8") if (d / "html.html").exists() else ""
    css = (d / "style.css").read_text(encoding="utf-8") if (d / "style.css").exists() else ""
    script = (d / "script.js").read_text(encoding="utf-8") if (d / "script.js").exists() else ""
    meta: dict[str, Any] = {}
    if (d / "meta.json").exists():
        try:
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    return Component(
        name=str(meta.get("name", d.name)),
        label=str(meta.get("label", d.name)),
        html=html, css=css, script=script,
        ai_prompt=str(meta.get("ai_prompt", "")),
        description=str(meta.get("description", "")),
        id=str(meta.get("id", meta.get("name", d.name))),
        meta=meta,
        render=str(meta.get("render", "iframe")),
    )


def save_component_dir(d: Path, c: Component) -> None:
    d.mkdir(parents=True, exist_ok=True)
    meta = dict(c.meta or {})
    meta.update({"id": c.id, "name": c.name, "label": c.label, "render": c.render,
                 "ai_prompt": c.ai_prompt, "description": c.description})
    (d / "html.html").write_text(c.html, encoding="utf-8", newline="\n")
    (d / "style.css").write_text(c.css, encoding="utf-8", newline="\n")
    (d / "script.js").write_text(c.script, encoding="utf-8", newline="\n")
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def scaffold_component(d: Path, name: str, slots: list[dict[str, Any]] | None = None,
                       color: str = "#D2B46A") -> Component:
    meta = json.loads(json.dumps(META_TEMPLATE))
    meta["id"] = name
    meta["name"] = name
    meta["label"] = f"组件 {name}"
    meta["theme"] = {"color": color}
    if slots:
        meta["slots"] = slots
    slot_list = slots or [{"name": "scene", "required": True, "desc": "场景名"}]
    html_parts = [f'<div class="{name}">']
    for s in slot_list:
        html_parts.append(f'  <span class="sh-data" data-{s["name"]}>${s["name"]}$</span>')
    first = slot_list[0]["name"]
    html_parts += [
        f'  <div class="d-{first}">${first}$</div>',
        "</div>",
    ]
    script = f"""(function () {{
  const root = document.getElementById('{name}');
  if (!root) return;
  const read = (sel) => {{
    const el = root.querySelector(sel);
    return el ? el.textContent.trim() : '';
  }};
  const clean = (v) => (!v || v.indexOf('$') !== -1) ? '' : v;
  const visible = clean(read('.d-{first}'));
  if (!visible) root.style.display = 'none';
  const report = () => {{
    try {{
      const frame = window.frameElement;
      parent.postMessage({{
        type: 'story-component-resize',
        id: frame ? frame.id : '{name}',
        height: document.body.scrollHeight,
      }}, '*');
    }} catch (_) {{ /* 非 iframe 环境忽略 */ }}
  }};
  [150, 500, 1200].forEach(function (ms) {{ setTimeout(report, ms); }});
}})();
"""
    c = Component(
        name=name, id=name, label=str(meta["label"]),
        html="\n".join(html_parts),
        css=CSS_TEMPLATE.format(name=name).replace("%COLOR%", color),
        script=script,
        ai_prompt="每次回复输出 " + "".join(
            f"<{s['name']}>值</{s['name']}>" for s in slot_list
        ) + f"，包在 <${name}$>…</${name}$> 内",
        description="由 fh comp new 生成的合规起点组件",
        meta=meta,
    )
    d.mkdir(parents=True, exist_ok=True)
    save_component_dir(d, c)
    return c


def load_component_set(project: Project, set_name: str | None = None) -> list[Component]:
    name = set_name or "vn4"
    from .config import load_bundled_platforms
    sets = load_bundled_platforms().get("components", {})
    names = sets.get(name, [])
    out: list[Component] = []
    for n in names:
        c = project.find_component(n)
        if c is None:
            # 允许项目内组件集同名目录直接作为组件
            d = project.components_dir / n
            if d.exists() and (d / "meta.json").exists():
                c = load_component_dir(d)
        if c is not None:
            out.append(c)
    # 项目 components/sets/<name>.yaml 覆盖
    set_yaml = project.components_dir / "sets" / f"{name}.yaml"
    if set_yaml.exists():
        data = yaml.safe_load(set_yaml.read_text(encoding="utf-8")) or {}
        names = data.get("components", names)
        out = []
        for n in names:
            c = project.find_component(n)
            if c is not None:
                out.append(c)
    return out


def check_component(c: Component, platforms_cfg: dict[str, Any] | None = None,
                    node_check: bool = True) -> list[ComponentProblem]:
    """组件约束检查器：平台五坑 + 拉长四禁 + 语法配对。"""
    problems: list[ComponentProblem] = []
    limit = 20000
    if platforms_cfg:
        limit = int(platforms_cfg.get("platforms", {}).get("fd", {}).get("component_source_limit_bytes", 20000))

    if not c.name or not str(c.id) == c.name:
        problems.append(ComponentProblem(c.name, "COMP-ID", "组件 id 必须是字符串且 = name（否则 css/script 全部失效）"))
    if not c.html.strip():
        problems.append(ComponentProblem(c.name, "COMP-HTML-EMPTY", "html 字段不能为空（平台会报错）"))
    for tag in ("style", "script", "meta", "iframe", "object", "embed", "link"):
        if re.search(rf"<\s*/?{tag}\b", c.html, re.I):
            problems.append(ComponentProblem(c.name, "COMP-HTML-TAG", f"html 字段含禁止标签 <{tag}>（平台清洗器剥离，导入会失败）"))
    if re.search(r"\son\w+\s*=", c.html, re.I):
        problems.append(ComponentProblem(c.name, "COMP-HTML-ONHANDLER", "html 含 inline on* 事件处理器，平台会剥离"))
    if ":root" in c.css:
        problems.append(ComponentProblem(c.name, "COMP-CSS-ROOT", "CSS 禁用 :root 选择器（平台会误判为 HTML 标签导致导入失败）"))
    # $变量$ 只许在 html
    for var in re.findall(r"\$(?!\{)([^$\n]{1,64})\$", c.script):
        problems.append(ComponentProblem(c.name, "COMP-VAR-SCRIPT", f"$变量$ 出现在 script（平台只替换 html）：${var}$ 永远拿不到值"))
    if re.search(r"infinite\b", c.css, re.I):
        problems.append(ComponentProblem(c.name, "COMP-STRETCH-INFINITE", "禁 infinite 真实元素动画（动画事件冒泡导致反复测高→消息拉长），用伪元素动画"))
    if re.search(r"min-height\s*:", c.css, re.I):
        problems.append(ComponentProblem(c.name, "COMP-STRETCH-MINHEIGHT", "禁 min-height 撑高（内容少时面板内大片空白）"))
    if re.search(r"position\s*:\s*fixed", c.css, re.I) and "fixed 覆盖自身 iframe" not in c.description:
        problems.append(ComponentProblem(c.name, "COMP-STRETCH-FIXED", "禁 fixed 全屏层（空 iframe 被最小高度撑开=顶部空一大排）"))
    if re.search(r"setInterval\s*\(", c.script):
        problems.append(ComponentProblem(c.name, "COMP-STRETCH-INTERVAL", "禁 setInterval 逐秒改 DOM（持续变化→反复测高）"))
    # 花括号配对
    if c.css.count("{") != c.css.count("}"):
        problems.append(ComponentProblem(c.name, "COMP-CSS-BRACES", f"css 花括号不配对：{{={c.css.count('{')} }}={c.css.count('}')}（缺 }} 会吞掉后续组件 css）"))
    if c.script.count("{") != c.script.count("}"):
        problems.append(ComponentProblem(c.name, "COMP-JS-BRACES", f"script 花括号不配对：{{={c.script.count('{')} }}={c.script.count('}')}"))
    if re.search(r"animation[^;{]*delay|animation[^;{]*both", c.css):
        problems.append(ComponentProblem(c.name, "COMP-ANIM-SAFE", "动画不得用 delay / both fill mode（动画失败时元素永久不可见）", fatal=False))
    src_bytes = c.source_bytes
    if src_bytes > limit:
        problems.append(ComponentProblem(c.name, "COMP-SOURCE-LIMIT", f"组件 source {src_bytes} > {limit} 字节（JSON 转义后硬限）"))
    # 槽位参数名对齐：html 占位符 必须出现在 meta.slots 或已知协议中
    slots = {s.get("name") for s in (c.meta.get("slots") or []) if isinstance(s, dict)}
    html_vars = set(re.findall(r"\$(?!\{)([^$\n]{1,64})\$", c.html))
    if slots:
        unknown = html_vars - slots
        if unknown:
            problems.append(ComponentProblem(c.name, "COMP-SLOT-ALIGN", f"html 占位符未在 meta.slots 声明：{sorted(unknown)}（与消息标签参数名必须逐字一致）", fatal=False))
    if node_check and c.script.strip():
        problems.extend(_node_check(c))
    return problems


def _node_check(c: Component) -> list[ComponentProblem]:
    node = shutil.which("node")
    if not node:
        return []
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
        f.write(c.script)
        path = f.name
    try:
        proc = subprocess.run([node, "--check", path], capture_output=True, text=True, timeout=30)
    except Exception:
        return []
    finally:
        Path(path).unlink(missing_ok=True)
    if proc.returncode != 0:
        return [ComponentProblem(c.name, "COMP-JS-SYNTAX", f"node --check 失败：{proc.stderr.strip()[:300]}")]
    return []


def protocol_doc(c: Component) -> str:
    slots = c.meta.get("slots") or []
    lines = [f"# 组件 {c.name} 调用协议（{c.label}）", ""]
    if c.ai_prompt:
        lines += ["## AI 提示词", "", c.ai_prompt, ""]
    lines += ["## 调用格式", "", f"<${c.name}$><槽位>值</槽位>…</${c.name}$>", "", "## 槽位表", "",
              "| 槽位 | 必填 | 说明 |", "|------|------|------|"]
    for s in slots:
        if isinstance(s, dict):
            lines.append(f"| {s.get('name','')} | {'是' if s.get('required') else '否'} | {s.get('desc','')} |")
    lines += ["", "> 占位符 `$槽位$` 只能写在 html；script 从 DOM 读取。"]
    return "\n".join(lines) + "\n"


def extract_from_fd(json_path: Path, out_dir: Path, names: list[str] | None = None) -> list[Path]:
    """从现有 FD 卡提取组件入库（extract）。"""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    written: list[Path] = []
    for comp in data.get("components", []):
        name = comp.get("name", "")
        if names and name not in names:
            continue
        d = out_dir / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "html.html").write_text(comp.get("html", ""), encoding="utf-8", newline="\n")
        (d / "style.css").write_text(comp.get("css", ""), encoding="utf-8", newline="\n")
        (d / "script.js").write_text(comp.get("script", ""), encoding="utf-8", newline="\n")
        meta = {"id": comp.get("id", name), "name": name, "label": comp.get("label", name),
                "ai_prompt": comp.get("ai_prompt", ""), "description": comp.get("description", ""),
                "render": "iframe"}
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        written.append(d)
    return written


def inject_components(card: Card, components: list[Component]) -> Card:
    """构建时注入：把组件集写入卡（不复写 ai_prompt，允许 per-card 覆盖）。"""
    named = {c.name: c for c in components}
    out: list[Component] = []
    for ref in card.components:
        if isinstance(ref, Component):
            out.append(ref)
        elif ref in named:
            comp = named[ref]
            # per-card ai_prompt 覆盖优先
            custom = next((x for x in card.components if isinstance(x, Component) and x.name == ref), None)
            if custom is not None and custom.ai_prompt:
                import copy
                comp = copy.deepcopy(comp)
                comp.ai_prompt = custom.ai_prompt
            out.append(comp)
    return out
