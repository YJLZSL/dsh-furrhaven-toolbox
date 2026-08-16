"""动画 showcase 生成器：把项目卡渲染成金箔暖纸主题的动效总览页。

用途：稳定版交付的可视化验收面（字节条 shimmer / 卡牌入场 / 组件槽位协议 /
正则渲染 / 世界书触发）。纯静态 HTML，可在任何浏览器打开。
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .model import Card

BASE_CSS = """
:root{--bg0:#14100c;--bg1:#1d1610;--paper:#f5eee0;--paper2:#fdfaf3;--ink:#2b2118;
--inkf:#9b8a74;--gold:#b8860b;--gold2:#d8b25a;--bright:#f0d491;--brown:#8b7355;
--deep:#4a3728;--line:rgba(139,115,85,.35);--ok:#4d7a52;--danger:#a2452f}
*{box-sizing:border-box}body{margin:0;background:
radial-gradient(1100px 620px at 78% -12%,rgba(184,134,11,.16),transparent 60%),
radial-gradient(900px 700px at -8% 112%,rgba(139,115,85,.14),transparent 55%),
linear-gradient(160deg,var(--bg1),var(--bg0) 55%,#100c08);color:var(--ink);
font-family:'Noto Serif SC','Source Han Serif SC',STSong,SimSun,Georgia,serif}
.wrap{max-width:1200px;margin:0 auto;padding:36px 26px 60px}
.hero{color:var(--paper);text-align:center;padding:26px 0 34px}
.hero h1{font-size:30px;letter-spacing:.12em;margin:0}
.hero p{color:var(--inkf);letter-spacing:.3em;font-size:12px}
.hero h1 b{background:linear-gradient(100deg,var(--bright),var(--gold));-webkit-background-clip:text;background-clip:text;color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px}
.card{background:linear-gradient(170deg,var(--paper2),var(--paper));border:1px solid var(--line);
border-radius:16px;padding:18px;box-shadow:0 10px 30px rgba(20,14,8,.45);position:relative;overflow:hidden;
animation:rise .5s cubic-bezier(.2,1,.3,1) both}
.card:nth-child(2){animation-delay:.06s}.card:nth-child(3){animation-delay:.12s}
.card:nth-child(4){animation-delay:.18s}.card:nth-child(5){animation-delay:.24s}
.card::after{content:'';position:absolute;top:0;left:10%;right:10%;height:2px;
background:linear-gradient(90deg,transparent,var(--gold),transparent)}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.card h2{margin:0 0 4px;font-size:19px}.card .sub{color:var(--inkf);font-size:12px;margin:0 0 14px}
.bar{display:grid;grid-template-columns:52px 1fr 116px;gap:8px;align-items:center;margin:7px 0}
.bar b{font-family:Consolas,monospace;font-size:11px;color:var(--deep)}
.bar span{font-family:Consolas,monospace;font-size:11px;color:var(--brown);text-align:right}
.track{height:7px;border-radius:4px;background:rgba(74,55,40,.14);overflow:hidden}
.fill{height:100%;border-radius:4px;background:linear-gradient(90deg,#7d9a5f,var(--ok));
animation:grow 1s cubic-bezier(.2,1,.3,1) both;position:relative;overflow:hidden}
.fill.over{background:linear-gradient(90deg,#c26b4e,var(--danger))}
.fill::after{content:'';position:absolute;inset:0;background:linear-gradient(100deg,transparent 20%,
rgba(255,255,255,.4) 50%,transparent 80%);transform:translateX(-100%);animation:shine 2.8s ease-in-out infinite}
@keyframes grow{from{width:0}}
@keyframes shine{0%,55%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
.panel{background:var(--paper2);border:1px solid var(--line);border-radius:16px;padding:18px;margin-top:20px;
box-shadow:0 10px 30px rgba(20,14,8,.4);animation:rise .6s cubic-bezier(.2,1,.3,1) both}
.panel h3{margin:0 0 12px;color:var(--deep);letter-spacing:.08em}
.console{background:#211a12;color:#e6d9be;font-family:Consolas,monospace;font-size:12px;line-height:1.7;
white-space:pre-wrap;padding:14px;border-radius:10px;border:1px solid rgba(216,178,90,.14)}
.proto{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.proto article{border:1px dashed var(--line);border-radius:10px;padding:12px}
.proto h4{margin:0 0 6px;color:var(--gold)}
.slot{font-size:12px;color:var(--brown)}
.seal{display:inline-block;border:1px solid var(--gold);border-radius:7px;color:var(--gold);
padding:4px 10px;margin-right:8px;font-size:12px}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation-duration:.01ms!important;transition:none!important}}
"""


def _escape(text: str) -> str:
    return html.escape(str(text))


def budget_bars(card: Card, platforms_cfg: dict[str, Any], components: list[Any]) -> str:
    from .budget import compute_budget
    rows = []
    for platform in ("fd", "fc", "fb"):
        b = compute_budget(card, platform, platforms_cfg, components)
        pct = min(100, round(b.used / b.limit * 100)) if b.limit else 0
        rows.append(
            f'<div class="bar"><b>{platform.upper()}</b><div class="track">'
            f'<div class="fill{" over" if b.over else ""}" style="animation-delay:.2s">{""}</div></div>'
            f'<span class="{"over" if b.over else ""}" style="color:{"var(--danger)" if b.over else "var(--brown)"}">'
            f'{b.used:,}/{b.limit:,}</span></div>'
        )
    return "".join(rows)


def showcase_html(project, cards: list[tuple[Card, list[Any]]]) -> str:
    body: list[str] = ['<div class="wrap">',
                       '<header class="hero"><h1>Furrhaven <b>Showcase</b></h1>'
                       '<p>金箔暖纸 · 多平台写卡验收</p></header>', '<div class="grid">']
    for i, (card, comps) in enumerate(cards):
        body.append(
            f'<article class="card" style="animation-delay:{i * 0.07:.2f}s">'
            f'<h2>{_escape(card.name)}</h2><p class="sub">{_escape(card.slug)} · {_escape(card.type)}'
            f' · {len(card.worldbook)} 世界书 · {len(comps)} 组件</p>'
            f'{budget_bars(card, project.platforms, comps)}</article>'
        )
    body.append('</div>')

    # 组件槽位协议
    proto: list[str] = []
    for card, comps in cards:
        for c in comps:
            slots = c.meta.get("slots") or []
            slot_html = "、".join(
                f'{s.get("name")}' + ("*" if s.get("required") else "") for s in slots if isinstance(s, dict)
            ) or "—"
            proto.append(
                f'<article><h4>{_escape(c.name)}</h4><p class="sub">{_escape(c.label)}</p>'
                f'<p class="slot">槽位：{_escape(slot_html)}（* 必填）</p>'
                f'<p class="slot">source {c.source_bytes:,} B / 20,000</p></article>'
            )
    body.append('<section class="panel"><h3>组件槽位协议（来自 meta.json）</h3>'
                f'<div class="proto">{"".join(proto) or "<p class=slot>无组件</p>"}</div></section>')

    # 世界书触发演示
    sim: list[str] = []
    from .worldbook import simulate_triggers
    for card, _comps in cards:
        hits, tokens = simulate_triggers(card.worldbook, "我在青澜市下车，夜雨刚停")
        sim.append(f"[{_escape(card.slug)}] 命中 {len(hits)} 条 / {tokens:,} B\n" +
                   "\n".join(f"  · {_escape(h.entry.name or h.entry.trigger_keys_text())}（{h.via}）"
                             for h in sorted(hits, key=lambda x: (x.entry.priority, str(x.entry.id)))))
    body.append('<section class="panel"><h3>世界书触发模拟</h3>'
                f'<pre class="console">{_escape(chr(10).join(sim))}</pre></section>')

    # 正则渲染演示
    from .regexlab import apply_rules
    for card, _comps in cards:
        if card.regex_rules:
            res = apply_rules(card.regex_rules, ">你好\n\n*他推开门，动作轻得像是怕惊动风。*")
            body.append('<section class="panel"><h3>正则测试台预览</h3>'
                        f'<pre class="console">{_escape(res.output)}</pre></section>')
            break
    body.append("</div>")
    return (
        "<!doctype html><html lang=zh-CN><head><meta charset=utf-8>"
        f"<title>Furrhaven Showcase</title><style>{BASE_CSS}</style></head><body>{''.join(body)}</body></html>"
    )


def generate_showcase(project, out: Path | None = None) -> Path:
    from .build import load_project_cards, resolve_components
    cards = [(c, resolve_components(c, project)) for c in load_project_cards(project)]
    if not cards:
        raise RuntimeError("没有卡，先 fh new")
    out = out or project.dist_dir / "showcase.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(showcase_html(project, cards), encoding="utf-8", newline="\n")
    return out
