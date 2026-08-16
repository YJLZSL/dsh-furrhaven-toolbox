"""fh CLI：Furrhaven 写卡工具箱入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from . import __version__, SUPPORTED_PLATFORMS, SUPPORTED_CARD_TYPES
from .config import Project, load_bundled_platforms


def _exit_parser(parser: argparse.ArgumentParser, message: str) -> None:
    parser.print_help(sys.stderr)
    print(f"\n错误：{message}", file=sys.stderr)
    raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except SystemExit:
        raise
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"fh: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fh",
        description="Furrhaven Toolbox：全类型角色卡创作工具箱（卡体/世界书/组件/正则/多平台导出/识图/扮演）",
    )
    p.add_argument("--version", action="version", version=f"fh {__version__} (furrhaven-core)")
    sub = p.add_subparsers(dest="command")

    def add(name, help_text):
        return sub.add_parser(name, help=help_text)

    # init
    pi = add("init", "生成 L3 项目工作区")
    pi.add_argument("dir", nargs="?", default=".")
    pi.add_argument("--name", default=None, help="项目名")
    pi.add_argument("--platforms", default="fd,st,fc,fb", help="逗号分隔平台")
    pi.add_argument("--genre-furry", action="store_true", help="开启 genre-furry 规则包（题材 opt-in）")

    # new
    pn = add("new", "新建卡（模块化目录或 --full 完整卡单文件）")
    pn.add_argument("slug")
    pn.add_argument("--type", default="character", choices=SUPPORTED_CARD_TYPES)
    pn.add_argument("--full", action="store_true", help="完整卡模式：单文件 card.md（卡体+世界书+组件+正则）")
    pn.add_argument("--component-set", default=None)

    # list
    add("list", "列出项目中的卡")

    # build
    pb = add("build", "IR → 平台产物（fd/fc/fb/st/risu/leinao/all）")
    pb.add_argument("--card", default=None, help="只构建指定 slug")
    pb.add_argument("--platform", default=None, help="逗号分隔；缺省用 fh.config.yaml")
    pb.add_argument("--dist", default=None, help="产物目录（缺省 dist/）")

    # check
    pc = add("check", "门禁聚合（退出码 0=可交付，1=有 error）")
    pc.add_argument("--card", default=None)
    pc.add_argument("--platform", default=None, help="只跑指定平台检查（逗号分隔）")
    pc.add_argument("--rule", default=None, help="只看指定规则 ID（子串）")
    pc.add_argument("--selftest", action="store_true", help="引擎自检")

    # budget
    pbud = add("budget", "字节余量表（口径表驱动）")
    pbud.add_argument("--card", default=None)
    pbud.add_argument("--platform", default=None)

    # audit
    add("audit", "全项目审计：余量表 + 跨卡扫描 + 世界书概览")

    # wb
    pw = add("wb", "世界书工坊")
    wsub = pw.add_subparsers(dest="wb_command")
    wsub.add_parser("list", help="列出卡的世界书条目")
    pwk = wsub.add_parser("keys", help="keys 误触发分析")
    pwk.add_argument("--card", default=None)
    pws = wsub.add_parser("sim", help="触发模拟器：样例消息 → 命中条目 + 注入顺序 + token")
    pws.add_argument("--card", required=True)
    pws.add_argument("--text", required=True, help="样例玩家消息")
    pwa = wsub.add_parser("add", help="新增条目")
    pwa.add_argument("--card", required=True)
    pwa.add_argument("--keys", required=True)
    pwa.add_argument("--content", required=True)
    pwa.add_argument("--name", default="")
    pwa.add_argument("--constant", action="store_true")
    pwa.add_argument("--priority", type=int, default=500)
    pwa.add_argument("--depth", type=int, default=3)

    # comp
    pco = add("comp", "组件工坊")
    csub = pco.add_subparsers(dest="comp_command")
    cnew = csub.add_parser("new", help="组件脚手架（四件套合规起点）")
    cnew.add_argument("name")
    cnew.add_argument("--color", default="#D2B46A")
    clist = csub.add_parser("list", help="列出组件库")
    clist.add_argument("--set", default=None)
    ccheck = csub.add_parser("check", help="约束检查器（五坑+拉长四禁）")
    ccheck.add_argument("--card", default=None)
    ccheck.add_argument("--name", default=None)
    cext = csub.add_parser("extract", help="从现有 FD 卡提取组件入库")
    cext.add_argument("json", help="FD 卡 JSON 路径")
    cext.add_argument("--names", default=None, help="逗号分隔；缺省全部")
    cinj = csub.add_parser("inject", help="把组件集注入卡（构建时也会自动注入）")
    cinj.add_argument("--card", default=None)
    cdoc = csub.add_parser("doc", help="由 meta.json 生成槽位协议文档")
    cdoc.add_argument("name")

    # regex
    pr = add("regex", "正则工坊")
    rsub = pr.add_subparsers(dest="regex_command")
    rt = rsub.add_parser("test", help="测试台：样例回复 → 按序应用 → 预览")
    rt.add_argument("--card", default=None)
    rt.add_argument("--file", default=None, help="规则 YAML 路径")
    rt.add_argument("--text", required=True, help="样例 AI 回复")
    rt.add_argument("--html-out", default=None, help="同时写 HTML 预览")
    rsub.add_parser("check", help="排序陷阱检查（wrapper 最后/星号互斥）")

    # import
    pi2 = add("import", "导入外部卡（FD JSON / ST V2V3 JSON·PNG / 任意 md 多写法）→ 完整卡 md")
    pi2.add_argument("source")
    pi2.add_argument("--out", default=None, help="输出路径（缺省 stdout）")
    pi2.add_argument("--slug", default=None)

    # vision
    pv = add("vision", "识图模式：读立绘/参考图/平台截图")
    pv.add_argument("image")
    pv.add_argument("--card", default=None)
    pv.add_argument("--mode", default="character", choices=["character", "ui"],
                    help="character=外貌描述；ui=平台截图排查")
    pv.add_argument("--prompt", default=None)

    # play
    pp = add("play", "扮演模式：构建后本机试玩（参考游玩）")
    pp.add_argument("slug")
    pp.add_argument("--say", default=None, help="单轮测试消息")
    pp.add_argument("--once", action="store_true", help="配合 --say 用：输出一轮后退出")

    # calibrate
    pcal = add("calibrate", "口径重测：生成探针卡，实测后回填 platforms.local.yaml")
    pcal.add_argument("platform", choices=["fd"])

    # review
    prv = add("review", "审阅双向流：export 加锁 → apply 回写 IR + 门禁 → IDLE")
    rsub = prv.add_subparsers(dest="review_command")
    rexp = rsub.add_parser("export", help="导出文字审阅稿并加 EDITING 锁")
    rexp.add_argument("--card", default=None)
    rapp = rsub.add_parser("apply", help="审阅稿回写 IR（门禁过才解锁）")
    rapp.add_argument("--card", required=True)
    rab = rsub.add_parser("abort", help="放弃本次审阅，解锁")
    rab.add_argument("--card", required=True)
    rsub.add_parser("status", help="查看审阅状态机")

    # showcase
    psh = add("showcase", "动画 showcase：项目卡总览（字节条/槽位协议/世界书/正则）")
    psh.add_argument("--out", default=None, help="输出路径（缺省 dist/showcase.html）")

    return p


def _load_project_or_die(args) -> Project:
    project = Project.discover(Path.cwd())
    if project is None:
        print("fh: 当前目录不是 fh 项目（缺 fh.config.yaml），先 `fh init`", file=sys.stderr)
        raise SystemExit(2)
    return project


def _parse_platforms(args, project: Project | None) -> list[str] | None:
    if getattr(args, "platform", None):
        raw = args.platform
        if raw == "all":
            return list(SUPPORTED_PLATFORMS)
        return [x.strip() for x in raw.split(",") if x.strip() in SUPPORTED_PLATFORMS]
    return None


def _load_cards(project: Project, only: str | None):
    from .build import load_project_cards, resolve_components
    cards = load_project_cards(project, only)
    return [(c, resolve_components(c, project)) for c in cards]


def _dispatch(args: argparse.Namespace) -> int:
    cmd = args.command
    if cmd == "init":
        from .scaffold import scaffold_workspace
        platforms = [x.strip() for x in args.platforms.split(",") if x.strip() in SUPPORTED_PLATFORMS]
        name = args.name or Path(args.dir).resolve().name
        project = scaffold_workspace(args.dir, name, platforms,
                                     rulepacks={"genre-furry": args.genre_furry})
        print(f"✓ 工作区已生成：{project.root}")
        print(f"  平台开关：{platforms}")
        print("  下一步：fh new <slug>（或 --full 完整卡）")
        return 0

    if cmd == "check" and args.selftest:
        return selftest()

    project = _load_project_or_die(args)

    if cmd == "new":
        from .scaffold import scaffold_card
        component_set = args.component_set or ("sim3" if args.type == "simulator" else
                                               "world4" if args.type == "bigworld" else "vn4")
        out = scaffold_card(project, args.slug, args.type, full=args.full, component_set=component_set)
        print(f"✓ 新卡已创建：{out}")
        print("  下一步：写内容 → fh check --card {} → fh build".format(args.slug))
        return 0

    if cmd == "list":
        from .build import load_project_cards
        cards = load_project_cards(project)
        if not cards:
            print("（暂无卡）fh new <slug>")
            return 0
        for c in cards:
            print(f"  {c.slug:20s} [{c.type:18s}] {c.authoring_mode:8s} {c.name}")
        return 0

    if cmd == "build":
        from .build import build_all
        from .review import assert_not_editing
        assert_not_editing(project, args.card, "build")
        platforms = _parse_platforms(args, project)
        dist = Path(args.dist) if args.dist else None
        results = build_all(project, only=args.card, platforms=platforms, dist_root=dist)
        for slug, r in results.items():
            arts = r["artifacts"]
            print(f"✓ {slug} ({r['card'].type})")
            for platform, paths in arts.items():
                if isinstance(paths, dict):
                    for k, path in paths.items():
                        print(f"    [{platform}/{k}] {path}")
                else:
                    print(f"    [{platform}] {paths}")
        print(f"锁文件已更新：{project.root / '.fh-lock.yaml'}")
        return 0

    if cmd == "check":
        return _cmd_check(args, project)

    if cmd == "budget":
        return _cmd_budget(args, project)

    if cmd == "audit":
        return _cmd_audit(project)

    if cmd == "wb":
        return _cmd_wb(args, project)

    if cmd == "comp":
        return _cmd_comp(args, project)

    if cmd == "regex":
        return _cmd_regex(args, project)

    if cmd == "import":
        return _cmd_import(args)

    if cmd == "vision":
        return _cmd_vision(args, project)

    if cmd == "play":
        return _cmd_play(args, project)

    if cmd == "calibrate":
        return _cmd_calibrate(args, project)

    if cmd == "review":
        return _cmd_review(args, project)

    if cmd == "showcase":
        from .showcase import generate_showcase
        out = generate_showcase(project, Path(args.out) if args.out else None)
        print(f"✓ showcase 已生成：{out}")
        return 0

    print("fh: 缺少子命令（fh --help）", file=sys.stderr)
    return 2


# ── check / budget / audit ───────────────────────────────────────────────────
def _cmd_check(args, project: Project) -> int:
    from .lint import EXIT_OK, EXIT_USAGE, LintReport, run_lints
    from .build import check_drift, load_project_cards, resolve_components

    if args.selftest:
        return selftest()

    platforms = _parse_platforms(args, project)
    cards = load_project_cards(project, args.card)
    if not cards:
        print("fh: 没有可检查的卡", file=sys.stderr)
        return EXIT_USAGE
    report = LintReport()
    packs = {
        "quality-core": project.rulepack_on("quality-core"),
        "genre-furry": project.rulepack_on("genre-furry"),
        "type-simulator": project.rulepack_on("type-simulator"),
        "type-bigworld": project.rulepack_on("type-bigworld"),
    }
    for card in cards:
        comps = resolve_components(card, project)
        card_packs = {
            "quality-core": packs["quality-core"],
            "genre-furry": packs["genre-furry"],
            "type-simulator": packs["type-simulator"] if card.type == "simulator" else False,
            "type-bigworld": packs["type-bigworld"] if card.type == "bigworld" else False,
        }
        run_lints(card, comps, project.platforms, project,
                  platforms=platforms, enabled_packs=card_packs)
    for msg in check_drift(project, args.card):
        report.problems.append(__import__("furrhaven.lint", fromlist=["Problem"]).Problem(
            "BUILD-DRIFT", "error", msg))
    problems = report.problems
    if args.rule:
        problems = [p for p in problems if args.rule.upper() in p.rule_id.upper()]
    filtered = LintReport(problems)
    print(filtered.render())
    return filtered.exit_code


def _cmd_budget(args, project: Project) -> int:
    from .build import load_project_cards, resolve_components
    from .budget import compute_budget
    platforms = _parse_platforms(args, project) or ["fd", "fc", "fb"]
    for card in load_project_cards(project, args.card):
        comps = resolve_components(card, project)
        for p in platforms:
            print(compute_budget(card, p, project.platforms, comps).table())
    return 0


def _cmd_audit(project: Project) -> int:
    from .build import load_project_cards, resolve_components
    from .budget import compute_budget
    cards = load_project_cards(project)
    if not cards:
        print("（暂无卡）")
        return 0
    print(f"项目：{project.config['project']['name']} | 卡数：{len(cards)}")
    for card in cards:
        comps = resolve_components(card, project)
        wb_bytes = sum(len(e.content.encode('utf-8')) for e in card.worldbook)
        print(f"\n== {card.slug} [{card.type}] {card.name} ==")
        print(f"  世界书条目 {len(card.worldbook)}（content {wb_bytes} B） | 组件 {len(comps)} | "
              f"快捷回复 {len(card.quick_replies)} | 正则 {len(card.regex_rules)}")
        for p in ("fd", "fc", "fb"):
            b = compute_budget(card, p, project.platforms, comps)
            mark = "⚠" if b.over else "✓"
            print(f"  {mark} {p}: {b.used}/{b.limit} B（余 {b.remaining}）")
    return 0


# ── 工坊命令 ─────────────────────────────────────────────────────────────────
def _cmd_wb(args, project: Project) -> int:
    from .build import load_project_cards
    from .worldbook import analyze_keys, next_entry_id, simulate_triggers
    cards = load_project_cards(project, getattr(args, "card", None))
    if args.wb_command == "list":
        for c in cards:
            print(f"== {c.slug} ==")
            for e in c.worldbook:
                mark = "★" if e.constant else " "
                print(f"  {mark} [{e.id}] {e.trigger_keys_text():24s} {e.name or '(无名)'}  {len(e.content)}字")
        return 0
    if args.wb_command == "keys":
        for c in cards:
            print(f"== {c.slug} keys 分析 ==")
            for w in analyze_keys(c.worldbook):
                print(f"  ⚠ {w.entry.name or w.entry.trigger_keys_text()}：{w.reason}")
        return 0
    if args.wb_command == "sim":
        card = cards[0] if cards else None
        if card is None:
            print("fh: 找不到卡", file=sys.stderr)
            return 2
        hits, token_bytes = simulate_triggers(card.worldbook, args.text)
        print(f"样例消息：{args.text}")
        print(f"命中 {len(hits)} 条，注入 {token_bytes} 字节：")
        for h in sorted(hits, key=lambda x: (x.entry.priority, str(x.entry.id))):
            print(f"  [{h.via}] {h.entry.name or h.entry.trigger_keys_text()}（{h.matched_key}）")
        return 0
    if args.wb_command == "add":
        from .worldbook import write_entry_file
        card = cards[0] if cards else None
        if card is None:
            print("fh: 找不到卡", file=sys.stderr)
            return 2
        card_dir = project.cards_dir / card.slug
        if not (card_dir / "worldbook").exists():
            print("fh: 完整卡模式请直接编辑 card.md 的世界书区块", file=sys.stderr)
            return 2
        entry = next_entry_id(card)
        eid = entry
        from .model import WorldBookEntry
        e = WorldBookEntry(id=eid, keys=[k.strip() for k in args.keys.split(",") if k.strip()],
                           content=args.content, name=args.name or args.keys.split(",")[0],
                           depth=args.depth, priority=args.priority, constant=args.constant)
        idx = len(list((card_dir / "worldbook").glob("*.md"))) + 1
        write_entry_file(card_dir / "worldbook" / f"{idx:02d}-{e.name}.md", e)
        print(f"✓ 条目已写入（id={eid}）")
        return 0
    print("fh wb: 缺少子命令（list/keys/sim/add）", file=sys.stderr)
    return 2


def _cmd_comp(args, project: Project) -> int:
    from .components import (check_component, extract_from_fd, load_component_dir,
                             load_component_set, protocol_doc, scaffold_component)
    if args.comp_command == "new":
        out = project.components_dir / args.name
        if out.exists():
            print(f"fh: 组件已存在：{out}", file=sys.stderr)
            return 2
        c = scaffold_component(out, args.name, color=args.color)
        print(f"✓ 组件四件套已生成：{out}（{c.label}）")
        print("  下一步：fh comp check --name " + args.name)
        return 0
    if args.comp_command == "list":
        if not project.components_dir.exists():
            print("（无组件库）")
            return 0
        for d in sorted(project.components_dir.iterdir()):
            if d.is_dir() and (d / "meta.json").exists():
                c = load_component_dir(d)
                print(f"  {c.name:16s} {c.label}  source={c.source_bytes}B")
        return 0
    if args.comp_command == "check":
        targets: list[Any] = []
        if args.name:
            d = project.components_dir / args.name
            if d.exists():
                targets.append(load_component_dir(d))
            else:
                print(f"fh: 组件不存在：{d}", file=sys.stderr)
                return 2
        else:
            from .build import load_project_cards, resolve_components
            for card in load_project_cards(project, args.card):
                targets.extend(resolve_components(card, project))
        n = 0
        for c in targets:
            probs = check_component(c, project.platforms)
            for p in probs:
                print(f"  [{'ERROR' if p.fatal else 'WARN'}] {p.rule} {c.name}: {p.message}")
                n += 1
        print(f"{len(targets)} 组件，{n} 问题")
        return 1 if any(True for c in targets for p in check_component(c, project.platforms) if p.fatal) else 0
    if args.comp_command == "extract":
        written = extract_from_fd(Path(args.json), project.components_dir,
                                  [x.strip() for x in args.names.split(",")] if args.names else None)
        for d in written:
            print(f"  ✓ 提取 {d.name}")
        return 0
    if args.comp_command == "doc":
        d = project.components_dir / args.name
        if not d.exists():
            print(f"fh: 组件不存在：{d}", file=sys.stderr)
            return 2
        print(protocol_doc(load_component_dir(d)))
        return 0
    print("fh comp: 缺少子命令（new/list/check/extract/doc）", file=sys.stderr)
    return 2


def _cmd_regex(args, project: Project) -> int:
    from .regexlab import apply_rules, check_rules, load_rules, render_html_preview
    if args.regex_command == "test":
        rules = []
        if args.file:
            rules = load_rules(args.file)
        elif args.card:
            from .build import load_project_cards
            cards = load_project_cards(project, args.card)
            rules = cards[0].regex_rules if cards else []
        else:
            p = project.regex_dir / "regex.yaml"
            if p.exists():
                rules = load_rules(p)
        if not rules:
            print("fh: 没有正则规则（--file / --card / regex/regex.yaml）", file=sys.stderr)
            return 2
        result = apply_rules(rules, args.text)
        print("── 渲染输出 ──")
        print(result.output)
        print("── 命中 ──")
        for rule, n in result.hits:
            print(f"  {rule.order}. {rule.name or rule.id}: {n} 次" if n >= 0 else f"  {rule.id}: 正则错误")
        if args.html_out:
            Path(args.html_out).write_text(render_html_preview(result), encoding="utf-8")
            print(f"HTML 预览：{args.html_out}")
        return 0
    if args.regex_command == "check":
        p = project.regex_dir / "regex.yaml"
        rules = load_rules(p) if p.exists() else []
        for card in __import__("furrhaven.build", fromlist=["load_project_cards"]).load_project_cards(project):
            rules += card.regex_rules
        for w in check_rules(rules):
            print(f"  ⚠ {w.rule_id} {w.rule.id}: {w.message}")
        return 0
    print("fh regex: 缺少子命令（test/check）", file=sys.stderr)
    return 2


def _cmd_import(args) -> int:
    from .parsers import export_full_card_md, load_card
    result = load_card(args.source)
    if args.slug:
        result.card.slug = args.slug
    for w in result.warnings:
        print(f"⚠ {w}", file=sys.stderr)
    md = export_full_card_md(result.card)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8", newline="\n")
        print(f"✓ 已导出完整卡 md：{out}")
    else:
        print(md)
    return 0


def _cmd_vision(args, project: Project) -> int:
    from .vision import UI_PROMPT, describe_image, vision_to_card
    prompt = args.prompt or (UI_PROMPT if args.mode == "ui" else None)
    if args.card:
        text, out = vision_to_card(args.image, project, prompt)
        print(text)
        print(f"\n✓ 识图笔记已写入：{out}")
    else:
        print(describe_image(args.image, prompt, project))
    return 0


def _cmd_play(args, project: Project) -> int:
    from .build import load_project_cards
    from .play import interactive_play, play_turn
    cards = load_project_cards(project, args.slug)
    if not cards:
        print(f"fh: 找不到卡 {args.slug}", file=sys.stderr)
        return 2
    card = cards[0]
    if args.say:
        print(play_turn(card, args.say, project=project))
        return 0
    return interactive_play(card, project)


def _cmd_calibrate(args, project: Project) -> int:
    from .exporters import _json_dump, fd_card
    from .model import Card
    # 探针卡：每个计数字段填 500 个「字」，平台显示值即可反推口径
    probe = Card(slug="probe-fd", name="口径探针")
    probe.personality = "字" * 500
    probe.scenario = "字" * 500
    probe.world_view = "字" * 500
    probe.mes_example = "字" * 500
    probe.response_format = "字" * 500
    probe.first_mes = "字" * 500
    probe.creator_notes = "口径探针卡：请平台显示「已使用」数值后回填 platforms.local.yaml"
    out = project.dist_dir / "calibrate" / "角色卡_口径探针_V3.json"
    _json_dump(fd_card(probe, []), out)
    print(f"✓ 探针卡已生成：{out}")
    print("  上传平台 → 记录「已使用」字节数 → `fh calibrate` 流程回填 platforms.local.yaml")
    print("  期望：各字段 1500 字节（UTF-8）时，显示值可反推计入字段口径。")
    return 0


def _cmd_review(args, project: Project) -> int:
    from .review import read_state, review_abort, review_apply, review_export
    if args.review_command == "export":
        written = review_export(project, args.card)
        for p in written:
            print(f"✓ 审阅稿已导出（EDITING 锁已加）：{p}")
        return 0
    if args.review_command == "apply":
        review_apply(project, args.card)
        print(f"✓ {args.card} 已回写 IR，门禁通过，状态解锁")
        return 0
    if args.review_command == "abort":
        review_abort(project, args.card)
        print(f"✓ {args.card} 审阅已放弃并解锁")
        return 0
    if args.review_command == "status":
        state = read_state(project)
        if not state:
            print("（无审阅记录）")
        for slug, st in state.items():
            print(f"  {slug}: {st.get('status')}")
        return 0
    print("fh review: 缺少子命令（export/apply/abort/status）", file=sys.stderr)
    return 2


# ── 引擎自检 ─────────────────────────────────────────────────────────────────
def selftest() -> int:
    """无外部依赖的引擎自检（CI 与 DSH 插件共用）。"""
    import io
    import json
    import tempfile

    checks: list[tuple[str, bool, str]] = []

    def ok(name: str, cond: bool, note: str = "") -> None:
        checks.append((name, bool(cond), note))

    # 1. 解析器：完整卡 md（多写法）
    from .parsers import parse_card_text
    sample = """---
name: 测试角色
type: character
---
# 人设
性格内核。

## 1. 基础
测试设定。

# 开场白
你好。

# 回复格式
1. 面板。
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
content: 青澜市是一座沿海城市。
---
"""
    r = parse_card_text(sample, "test")
    ok("parse.full-card", r.card.name == "测试角色" and r.card.personality and
       len(r.card.worldbook) == 2, f"entries={len(r.card.worldbook)}")

    # 2. 触发模拟器（含递归）
    from .worldbook import simulate_triggers
    e2 = r.card.worldbook[1]
    hits, _ = simulate_triggers(r.card.worldbook, "我来到青澜")
    ok("wb.sim.direct", any(h.entry is e2 and h.via == "direct" for h in hits))
    hits2, _ = simulate_triggers(r.card.worldbook, "系统-角色")
    ok("wb.sim.constant", any(h.entry.constant for h in hits2))

    # 3. 字节口径
    from .budget import compute_budget
    from .config import load_bundled_platforms
    r.card.personality = "字" * 1000
    r.card.response_format = ""
    b = compute_budget(r.card, "fd", load_bundled_platforms(), [])
    ok("budget.fd.utf8", b.used == 3000, f"used={b.used}")

    # 4. 组件检查器命中历史事故
    from .components import check_component
    from .model import Component
    bad = Component(name="bad", id="notbad", html="<style>x</style>", css=":root{}",
                    script="clean('$scene$')")
    probs = check_component(bad, load_bundled_platforms(), node_check=False)
    ids = {p.rule for p in probs}
    ok("comp.pitfalls", {"COMP-ID", "COMP-HTML-TAG", "COMP-CSS-ROOT", "COMP-VAR-SCRIPT"} <= ids,
       f"rules={sorted(ids)}")

    # 5. PNG V2/V3 往返
    from .exporters import st_v2, st_v3
    from .png import read_card_png, write_card_png
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p1 = write_card_png(st_v2(r.card), td / "v2.png", include_v2=True, include_v3=False)
        p2 = write_card_png(st_v3(r.card), td / "v3.png", include_v2=False, include_v3=True)
        v2 = read_card_png(p1)
        v3 = read_card_png(p2)
        ok("png.v2.roundtrip", v2.get("spec") == "chara_card_v2" and v2["data"]["name"] == "测试角色")
        ok("png.v3.roundtrip", v3.get("spec") == "chara_card_v3" and v3["data"]["nickname"] == "测试角色")

    # 6. 正则测试台
    from .regexlab import apply_rules
    from .model import RegexRule
    rules = [RegexRule(id="bold", name="加粗", find=r"^>(.+)$", replace=r"**$1**",
                       flags=["MULTILINE"], order=1)]
    res = apply_rules(rules, ">你好\n正文", "ai_reply")
    ok("regex.apply", res.output == "**你好**\n正文", res.output)

    # 7. lint 聚合退出码协议
    from .lint import EXIT_OK, LintReport, run_lints
    rep = run_lints(r.card, [], load_bundled_platforms(), None, platforms=["fd"],
                    enabled_packs={"quality-core": False, "genre-furry": False,
                                   "type-simulator": False, "type-bigworld": False})
    ok("lint.gate", rep.exit_code in (EXIT_OK, 1) and isinstance(rep.render(), str))

    # 8. FD 导出结构
    from .exporters import fd_card
    fd = fd_card(r.card, [])
    ok("export.fd.structure", all(k in fd for k in ("name", "world_info", "components",
                                                    "quick_replies", "vn_mode_enabled", "lorebook_config")))

    failed = [c for c in checks if not c[1]]
    for name, passed, note in checks:
        print(f"  {'✓' if passed else '✗'} {name} {note}")
    if failed:
        print(f"\nSELFTEST FAIL：{len(failed)} 项失败")
        return 1
    print(f"\nSELFTEST PASS：{len(checks)} 项全绿")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
