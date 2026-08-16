---
name: furrhaven-card
description: Furrhaven 写卡工具箱流程纪律：多平台角色卡（FD/FC/FB/酒馆 V2V3）从零写作、三工坊（世界书/组件/正则）、完整卡模式、识图与扮演测试。当用户要求写/改/修/审计/导出角色卡时使用。
---

# Furrhaven Card（写卡流程纪律）

> 与 `card-forge` preset 配套；所有门禁以 `fh check` 退出码为准（0 = 可交付）。

## 0. 任务路由（先分类，后动手）

| 任务信号 | 做法 | 首步 |
|---------|------|------|
| 新建卡 / 写开场白 / 写组件 / 写正则 / 批量生成 | 直接生产 | `fh init` 或 `fh new <slug>`（完整卡用 `--full`） |
| 修卡 / 排查 / 审计 / 超限压缩 / 平台报错 | 先定位后动手 | `fh check --card <slug>` → 按规则 ID 定点修；整体重写优先 |
| 模糊 / 混合 | 先问清卡型与平台，再二选一 | 读 `fh.config.yaml` + `fh list` |

## 1. 两种创作模式（用户写法不同，都支持）

- **模块化 IR（默认）**：`cards/<slug>/` 下 `card.yaml` + 分区 md + `worldbook/*.md` + `components.yaml`。适合多人协作、diff 友好。
- **完整卡模式**：`fh new <slug> --full` 生成单文件 `card.md`（卡体 + 世界书 + 组件 + 正则一把梭）。适合整体写作型作者；标题别名宽容（性格设定/人设/personality、开场白/first_mes…），世界书可写 `### 条目名 + front-matter`、fenced YAML 或 JSON。
- 外部导入：`fh import <FD JSON | ST V2V3 JSON | PNG | 任意 md>` → 统一成完整卡 md。

## 2. 五步主流程

1. **定位**：卡型（character/simulator/bigworld）+ 目标平台（fd/fc/fb/st/risu/leinao）。
2. **写作**：先锁权威源（角色总表/立绘），再写 personality（性格内核铁律 + 多面性）、scenario、first_mes、mes_example、response_format。
3. **工坊**：
   - 世界书：`fh wb sim --card X --text "样例消息"` 验证触发；`fh wb keys` 查误触发。
   - 组件：`fh comp new` 起步，`fh comp check` 五坑全查；改库后 `fh build` 自动注入。
   - 正则：`fh regex test --text "样例回复"` 即时渲染；wrapper 必须最后。
4. **门禁**：`fh check --card X` 退出码 0；`fh audit` 看全项目余量。
5. **构建与试玩**：
   - `fh build --card X --platform all`（产物在 dist/，含酒馆 V2/V3 PNG）。
   - `fh play X` 本机扮演试玩（参考游玩）；有立绘/截图时 `fh vision <图> --card X` 先识图对齐外貌。
   - 平台上传：FD 一键导入 JSON；FC 用 8 目录资料包（先删后填五步法）；酒馆导入 `dist/st/*.v3.png`；上传前核对文件大小/时间戳。

## 3. fh 命令域速查

```
fh init [dir] [--genre-furry]          # 项目工作区
fh new <slug> [--full] [--type ...]    # 新卡
fh list / fh check / fh build / fh budget / fh audit
fh wb list|keys|sim|add
fh comp new|list|check|extract|doc
fh regex test|check
fh import <外部卡> ; fh vision <图> [--card X] [--mode ui] ; fh play X [--say "..." ]
fh check --selftest                    # 引擎自检（CI 同款）
```

## 4. 平台硬知识（写作时内化，门禁已规则化）

### FD（Fuderation）
- 自由模式默认：`vn_mode_enabled=false`；character 卡 scenario/world_view 置空并入 personality 分区。
- 组件五坑：`$变量$` 只在 html；id 字符串=name；html 禁 style/script/meta/iframe；单组件 source ≤20,000 字节；占位符 ↔ 消息标签参数名逐字一致。
- 拉长四禁：infinite 动画 / min-height / fixed 全屏层 / setInterval 逐秒改 DOM；安全=伪元素动画 + postMessage 150/500/1200ms 报高。
- 字节口径 v3.0（保守）：personality+scenario+world_view+mes_example+response_format+组件 ai_prompt ≤50,000 UTF-8 字节；世界书独立 30,000；first_mes/quick_replies/组件源码不计。

### FC / FB
- FC ≤15,000（卡+开场白+简介+回复格式），正则 15 条渲染链，全匹配 wrapper 最后。
- FB ≤10,666：跨章节去重→迁共享世界书→零损失删减。
- 单双星号互斥：`(?<!\*)\*(?!\*)`。

### SillyTavern（酒馆本体）与 RisuAI
- `fh build --platform st` 同时出 V2 PNG（`chara` chunk）与 V3 PNG（`ccv3` chunk）+ regex JSON；世界书映射为 character_book（V3 含 use_regex）。
- 导入酒馆用 `dist/st/<slug>.v3.png`；类脑等兼容 V2/V3 的平台同样可导入。

## 5. 错误恢复索引（fh check 规则 ID → 修法）

| 规则 ID | 修法 |
|--------|------|
| `COMP-ID` | `"id": "组件名"`（字符串 = name） |
| `COMP-HTML-TAG` / `COMP-CSS-ROOT` | html 只放纯结构；CSS 用组件根 class 声明变量，禁 `:root` |
| `COMP-VAR-SCRIPT` | `$变量$` 移到 html 或 `.sh-data` span，script 从 DOM 读 |
| `COMP-SOURCE-LIMIT` | 组件拆件/删死代码（source ≤20,000） |
| `BYTE-FD-OVER` | `fh budget` 看字段余量；优先压缩 response_format/personality，深度内容移世界书 |
| `WB-KEYS` | 去掉单字/泛词，补专属词（跨卡雷区查 lexicon） |
| `CONTENT-RESIDUE` | 整分区替换（禁止逐段 patch），跑 `fh check --rule CONTENT-RESIDUE` 复验 |
| `BUILD-DRIFT` | 改完 IR 必须 `fh build` 重建 dist |

## 6. 铁律

1. 平台 JSON 只许 `fh` 脚本读写；严禁文本编辑 dist/。
2. 批量修改前先 git commit；改一张卡先平台实测再批量。
3. 门禁退出码 0 才进下一阶段；先修复再汇报。
4. 题材中立：furry 规则只在 genre-furry 包（`fh init --genre-furry` 显式开启）。
5. 完整卡模式同样走 `fh check`/`fh build`，不因单文件而跳过门禁。
