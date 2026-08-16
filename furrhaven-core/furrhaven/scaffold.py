"""脚手架：fh init（L3 工作区）+ fh new（新卡，模块化/完整卡双模式）。

模板原则：
- 题材中立：默认模板不含任何兽人/性别假设；
- 好感铁令 12/13 + 性格内核铁律：character 恋爱向默认预填（继承参考项目强制口径），
  非恋爱卡可删；
- 完整卡模式 = 单文件 card.md（卡体+世界书+组件+正则一把梭），给习惯整体写的作者。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config import Project, save_yaml
from .model import WorldBookEntry
from .worldbook import write_entry_file

QUALITY_12 = (
    "好感数值 <level>：普通互动 +1~3%、互动良好 +3~5%、重大事件最多 +8%；"
    "上升后至少 3 轮冷却；严禁一次跳涨 10% 以上或满级/归零。"
)
QUALITY_13 = (
    "关系阶段 <stage> 与 <level> 联动：stage1=0~20 / stage2=21~40 / stage3=41~60 / "
    "stage4=61~80 / stage5=81~100；一次最多升一级且重大事件下一轮才生效；"
    "stage1 禁暧昧、stage2 禁表白、stage3 仍禁直说喜欢、stage4 可表白、stage5 才可日常亲密；"
    "stage1-3 禁自我剖白式袒露内在需求（暗恋只能藏进行为和玩笑）；"
    "玩家套话/直球时角色装傻、打哈哈或岔开话题。"
)

PERSONALITY_TEMPLATE = """【性格内核铁律】本文件 ## 7 是 {name} 性格的唯一基准；任何改写都不得漂移成通用温柔男友，不得与 ## 7 冲突。

## 1. 性别、年龄、种族
（填写）

## 2. 角色经历
（填写：成长史、关键事件、现在的处境）

## 3. 与他的人际关系
- **玩家**：（关系定位、相处方式、只有玩家能看到的反差）
- **重要 NPC**：（每人 2-4 句，含口癖）

## 4. 穿着、身材、外貌
（填写：身高体型、常穿服装、标志物、与立绘逐项对齐）

## 5. 当前身份与生活目标
（填写：明面目标、隐藏目标、日常作息）

## 6. 说话风格与对话内容示例
（填写：口头禅、句式、紧张/说谎/心动时的说话变化）

## 7. 性格、思想、信念
（唯一性格基准：写透多面性、动机、恐惧、信念，不要形容词堆砌）

## 8. 特殊喜好与厌恶
（喜好 / 厌恶）

## 9. 缺点、弱点
（写具体行为，不写抽象标签）

## 10. 特殊持有物与特殊能力
（每件物品/能力：来历 + 使用场景）

## 11. 秘密
（只写玩家能逐步挖出来的）

## 12. 亲密关系偏好（恋爱向卡保留；非恋爱向删除本节）
（含蓄向：靠近时的身体反应、害羞表现，不写直白器官描写）

## 13. 描写侧重点与其他补充项
（微表情/细节物/氛围基调/成长弧线/判定性细节）
"""

SCENARIO_TEMPLATE = """（当前时间、地点、正在发生的事；用第二人称写玩家的处境与入场动作。）
"""

RESPONSE_FORMAT_TEMPLATE = """每次回复固定三段式：场景面板 → 正文（对话 `行内代码`、叙述 *斜体*）→ 心声 → 底部选项面板。

1. 组件调用：成对子标签、闭合完整、标签间不得空行、占位符与消息标签参数名逐字一致。
2. 正文格式：对话用 `行内代码`（不加引号），叙述用 *斜体*，段落间空行。
3. 选项：opt1-3 为玩家第一人称行动（40-80 字，含具体动作，不替玩家编台词），opt4 固定「代入观看」；每轮必输出。
4. {quality12}
5. {quality13}
"""

FIRST_MES_TEMPLATE = """（开场白：当前场景 + 角色第一个动作 + 面板标签 + 选项，结尾用行动选项而不是问题。）
"""

MES_EXAMPLE_TEMPLATE = """<START>

{{{{user}}}}: （玩家第一轮）

{{{{char}}}}:
（角色第一轮：面板 + 正文 + 心声 + 选项）

<END>

<START>

{{{{user}}}}: （玩家第二轮）

{{{{char}}}}:
（角色第二轮）

<END>
"""

SYS_ENTRY_CONTENT = {
    "角色": "当前出场角色为「{name}」：{简短的当前状态}。行为签名：{2-3 个标志性动作}。语言风格：{口头禅与句式}。外貌：{与立绘一致的关键特征}。",
    "场景": "当前场景：{地点}。氛围：{天气/光线/声音}。设施：{可交互物}。在场 NPC：{名字+状态+情绪}。",
    "目标": "当前主线目标：{目标}。当前阶段：{子目标}。推进提示：{下一步可做的事}。",
    "好感": "当前好感度 {数值}，关系阶段 {stage}。互动模式：{当前相处模式}。升级阈值：{下一阶段需要的关键事件}。",
    "关系": "当前关系阶段：{定位}。互动指南：{可做/不可做}。下一阶段：{解锁条件}。",
}


def scaffold_workspace(root: str | Path, name: str, platforms: list[str] | None = None,
                       rulepacks: dict[str, bool] | None = None) -> Project:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "cards").mkdir(exist_ok=True)
    (root / "shared").mkdir(exist_ok=True)
    (root / "components" / "sets").mkdir(parents=True, exist_ok=True)
    (root / "regex").mkdir(exist_ok=True)
    (root / "assets").mkdir(exist_ok=True)
    (root / "dist").mkdir(exist_ok=True)
    (root / "reviews").mkdir(exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    (root / "archive").mkdir(exist_ok=True)

    cfg: dict[str, Any] = {
        "project": {
            "name": name,
            "platforms": platforms or ["fd", "st", "fc", "fb"],
            "card_types": ["character", "simulator", "bigworld"],
            "authoring_modes": ["modular", "full"],
        },
        "rulepacks": {
            "quality-core": True,
            "genre-furry": bool((rulepacks or {}).get("genre-furry", False)),
            "type-simulator": "auto",
            "type-bigworld": "auto",
        },
        "lexicon": {
            "forbidden_words": [],
            "exclusive_word_map": {},
            "dead_metaphors": ["金属板", "蓝宝石", "山峦", "星海", "星辰大海"],
        },
        "play": {"api_base": "", "api_key": "", "model": "", "user_name": "我",
                 "temperature": 1.0, "max_tokens": 2048},
        "vision": {"api_base": "", "api_key": "", "model": ""},
        "model_roles": {"lint": "flash", "draft": "flash", "rewrite": "v4-pro max"},
    }
    save_yaml(root / "fh.config.yaml", cfg)

    # 组件集默认清单
    save_yaml(root / "components" / "sets" / "vn4.yaml",
              {"components": ["vnHeader", "vnMap", "vnThought", "vnFooter"]})
    # 起步组件四件套（合规起点：槽位协议 + sh-data + 主动报高；AI 写回复格式可直接引用）
    from .components import scaffold_component
    starter = {
        "vnHeader": (["scene", "time", "date", "atmosphere", "climate", "location", "chars", "temp"], "#D2B46A"),
        "vnMap": (["loc_prev", "loc_curr", "loc_next", "move1", "move2"], "#8A7DB8"),
        "vnThought": (["thought"], "#B8A27A"),
        "vnFooter": (["opt1", "opt2", "opt3", "opt4", "level", "stage", "items"], "#C08A4E"),
    }
    for cname, (slots, color) in starter.items():
        if not (root / "components" / cname).exists():
            scaffold_component(root / "components" / cname, cname,
                               slots=[{"name": s, "required": s in ("scene", "loc_curr", "thought", "opt1", "level", "stage"),
                                       "desc": f"槽位 {s}"} for s in slots],
                               color=color)
    # 正则模板包（bundled v2.3）
    bundled = Path(__file__).resolve().parent / "resources" / "regex_v23.yaml"
    if bundled.exists():
        (root / "regex" / "regex.yaml").write_text(bundled.read_text(encoding="utf-8"),
                                                   encoding="utf-8", newline="\n")
    (root / "shared" / "角色总表.md").write_text(
        "# 角色总表\n\n> 单一事实源：物种/年龄/职业/外貌/内核设定冲突时以此为准。\n\n| 角色 | 卡型 | 内核一句话 | 字节状态 |\n|------|------|-----------|---------|\n",
        encoding="utf-8", newline="\n")
    (root / "README.md").write_text(
        f"# {name}\n\n由 `fh init` 生成。目录结构见 docs 文档地图；常用命令：\n\n"
        "```\nfh new <slug>            # 模块化新卡\nfh new <slug> --full     # 完整卡单文件\nfh check                 # 门禁\nfh build --platform all  # 全平台导出\nfh play <slug>           # 扮演试玩\n```\n",
        encoding="utf-8", newline="\n")
    for d in ("dist", "reviews", "archive", "assets"):
        (root / d / ".gitkeep").write_text("", encoding="utf-8")
    return Project(root)


def _system_entries(card_type: str, name: str, slug: str) -> list[WorldBookEntry]:
    if card_type == "simulator":
        keys_map = {"时间": "系统-时间", "阶段": "系统-阶段", "资源": "系统-资源", "事件": "系统-事件"}
    elif card_type == "bigworld":
        keys_map = {"地点": "系统-地点", "在场NPC": "系统-在场NPC", "世界时间": "系统-世界时间",
                    "主线进度": "系统-主线进度", "玩家状态": "系统-玩家状态", "已知情报": "系统-已知情报"}
    else:
        keys_map = {"角色": "系统-角色", "场景": "系统-场景", "目标": "系统-目标",
                    "好感": "系统-好感", "关系": "系统-关系"}
    out = []
    for idx, (label, key) in enumerate(keys_map.items(), start=1):
        content = SYS_ENTRY_CONTENT.get(label, "当前{label}：{状态}。").replace("{name}", name)
        out.append(WorldBookEntry(
            id=int(f"1750{idx:02d}0000"), keys=[key], name=f"{label}（系统条目）",
            content=content, depth=0, priority=idx, constant=True, probability=100))
    return out


def scaffold_card(project: Project, slug: str, card_type: str = "character",
                  full: bool = False, component_set: str = "vn4") -> Path:
    card_dir = project.cards_dir / slug
    card_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "slug": slug,
        "type": card_type,
        "name": slug,
        "title": "",
        "description": "（列表钩子：第二人称场景式 + 悬念）",
        "tags": [],
        "component_set": component_set,
        "component_theme": {"COLOR": "#D2B46A"},
    }
    personality = PERSONALITY_TEMPLATE.format(name=meta["name"])
    response_format = RESPONSE_FORMAT_TEMPLATE.format(quality12=QUALITY_12, quality13=QUALITY_13)
    entries = _system_entries(card_type, meta["name"], slug)

    if full:
        text = _full_card_markdown(meta, personality, response_format, entries, card_type)
        (card_dir / "card.md").write_text(text, encoding="utf-8", newline="\n")
        return card_dir / "card.md"

    save_yaml(card_dir / "card.yaml", meta)
    (card_dir / "personality.md").write_text(personality, encoding="utf-8", newline="\n")
    (card_dir / "scenario.md").write_text(SCENARIO_TEMPLATE, encoding="utf-8", newline="\n")
    (card_dir / "world_view.md").write_text("（世界观：地点、时代、运行规则；角色卡自由模式可并入 personality，模拟器/大世界卡必填。）\n",
                                            encoding="utf-8", newline="\n")
    (card_dir / "first_mes.md").write_text(FIRST_MES_TEMPLATE, encoding="utf-8", newline="\n")
    (card_dir / "mes_example.md").write_text(MES_EXAMPLE_TEMPLATE, encoding="utf-8", newline="\n")
    (card_dir / "response_format.md").write_text(response_format, encoding="utf-8", newline="\n")
    (card_dir / "creator_notes.md").write_text("（直白笔记体：维护说明、口径记录，与简介同步。）\n",
                                               encoding="utf-8", newline="\n")
    save_yaml(card_dir / "components.yaml",
              {"set": component_set,
               "components": ["vnHeader", "vnMap", "vnThought", "vnFooter"] if component_set == "vn4" else [],
               "theme": meta["component_theme"]})
    wb = card_dir / "worldbook"
    wb.mkdir(exist_ok=True)
    for e in entries:
        fname = f"{e.priority:02d}-{e.name.split('（')[0]}.md"
        write_entry_file(wb / fname, e)
    return card_dir


def _full_card_markdown(meta: dict[str, Any], personality: str, response_format: str,
                        entries: list[WorldBookEntry], card_type: str) -> str:
    clean_meta = {k: v for k, v in meta.items() if v not in ("", None, [])}
    out = ["---", yaml.safe_dump(clean_meta, allow_unicode=True, sort_keys=False).rstrip(), "---", "",
           "# 人设 / 性格（personality）", "", personality, "",
           "# 场景（scenario）", "", SCENARIO_TEMPLATE, "",
           "# 世界观（world_view）", "", "（世界观：地点、时代、运行规则。）", "",
           "# 开场白（first_mes）", "", FIRST_MES_TEMPLATE, "",
           "# 对话示例（mes_example）", "", MES_EXAMPLE_TEMPLATE, "",
           "# 回复格式（response_format）", "", response_format, "",
           "# 创作者备注（creator_notes）", "", "（直白笔记体。）", "",
           "# 世界书（worldbook）", ""]
    for e in entries:
        fm = {"id": e.id, "keys": e.keys, "name": e.name, "depth": e.depth,
              "priority": e.priority, "constant": e.constant}
        out += [f"### {e.name}", "---", yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).rstrip(),
                "---", "", e.content, ""]
    out += ["# 组件（components）", "", "```yaml",
            yaml.safe_dump({"set": meta.get("component_set", "vn4"),
                            "components": ["vnHeader", "vnMap", "vnThought", "vnFooter"],
                            "theme": meta.get("component_theme", {})},
                           allow_unicode=True, sort_keys=False).rstrip(), "```", ""]
    return "\n".join(out)
