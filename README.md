# Furrhaven · 角色卡多平台写卡工具箱

> 版本：v1.1.0（稳定大版本 + 桌面安装器/自动更新） | 2026-08-16
> 定位：**全类型角色卡创作工具箱**（兽人创作出身、不限题材）—— Python 核心引擎 + DeepSeek-Harness 官方框架 fork（dsh-furrhaven），加入 dsh 生态。

## 已实现能力（v1.0.0）

五大能力面 + 用户本次追加的三项：

- **卡体写作**：卡型系统（character / character.activity / simulator / bigworld / custom），题材中立；**两种写法**——模块化 IR（`fh new`）与**完整卡单文件**（`fh new --full`，卡体+世界书+组件+正则一把梭）；宽容解析器兼容 `# name/# personality`、front-matter、中文/英文标题、fenced YAML 等不同作者的写法。
- **世界书工坊**：条目 CRUD、keys 误触发分析、触发模拟器（含递归 depth=1）、预算核算。
- **组件工坊**：`fh comp new` 脚手架、注入引擎、约束检查器（FD 五坑 + 拉长四禁 + 花括号/node --check/:root）、槽位协议文档、extract 入库。
- **正则工坊**：FC 统一渲染 v2.3 模板包（15 条全量迁移）、测试台、wrapper 最后/星号互斥检查。
- **多平台导出**：FD JSON（自由模式 v3.0 字节口径）· FC 8 目录资料包 · FB md · **酒馆本体 SillyTavern V2/V3 PNG**（`chara`+`ccv3` chunk）+ **ST world info JSON / regex JSON** · RisuAI V3 · 类脑 V3。
- **识图模式**：`fh vision <图> [--card X] [--mode ui]` 视觉模型读立绘/参考图/平台截图。
- **扮演模式**：`fh play <slug>` 本机试玩（卡体+常驻世界书组装 prompt，世界书 keys 按轮触发）。
- **审阅双向流**：`fh review export/apply/abort/status`，EDITING 状态机锁拒绝 build/export，apply 回写 IR 且门禁通过才解锁。
- **动画 showcase**：`fh showcase` 生成金箔暖纸主题动效总览（字节条 shimmer/卡牌入场/槽位协议/世界书触发/正则预览）。
- **门禁**：`fh check` 退出码协议（0=可交付），构建指纹锁防漂移，`fh check --selftest` CI 同款。
- **DSH 生态**：主仓 `dsh-furrhaven-toolbox` + 官方框架 fork `dsh-furrhaven`（upstream 同步脚本）；preset `card-forge` + skill `furrhaven-card` + 插件 **`@dsh-external/dsh-fh-tools`**（9 个工具，super-injector 热载已验证）。
- **桌面端 = DSH 官方框架魔改**：fork `deepseek-ai/deepseek-harness`（本地 `dsh-framework/`，私有镜像 `YJLZSL/dsh-furrhaven`），`scripts/sync-dsh.ps1` 同步上游；Furrhaven preset/skill/plugin/主题 以 `furrhaven/` 叠加层合入，不另起桌面栈。

## 快速开始

```powershell
# 1) 安装引擎
pip install -e .\furrhaven-core

# 2) 自检
fh check --selftest

# 3) 建项目 + 写卡（模块化 / 完整卡两种写法任选）
fh init .\my-project
cd .\my-project
fh new 灰野
fh new 穿越卡 --full

# 4) 工坊即时反馈
fh wb sim --card 灰野 --text "我在青澜市下车"
fh comp check --card 灰野
fh regex test --text ">你好，*动作*"

# 5) 门禁 → 构建 → 试玩
fh check
fh build --platform all          # dist/fd fc fb st risu leinao
fh play 灰野                      # 扮演模式（先配 fh.config.yaml play 段或 FH_LLM_*）
fh vision .\assets\立绘.png --card 灰野   # 识图模式
```

## 平台矩阵

| 平台 | 产物 | 红线（UTF-8 字节） | 状态 |
|------|------|-------------------|------|
| FD | `dist/fd/角色卡_{名}_V3.json` | 卡 50,000；世界书 30,000；组件 source 20,000 | ✅ 可导出（口径 v3.0） |
| FC | `dist/fc/{slug}-fc-pack/`（8 目录） | 40,000（资料包总限，2026-08-16 口径修订） | ✅ 可导出 |
| FB | `dist/fb/{名}.md` | 10,666 | ✅ 可导出 |
| **SillyTavern 酒馆本体** | `dist/st/{slug}.v2.png` + `.v3.png` + `.regex.json` | 无硬限 | ✅ V2/V3 PNG |
| RisuAI / 类脑 | `dist/{risu,leinao}/{slug}.v3.json` | 无硬限 | ✅ V3 |

## 桌面端（DSH 官方框架魔改）

```powershell
# 同步官方上游 + 自测（fork 默认分支 furrhaven）
.\scripts\sync-dsh.ps1 -SkipSslVerify

# fork 内的 Furrhaven 叠加层
dsh-framework\furrhaven\presets\card-forge     # 写卡 preset
dsh-framework\furrhaven\plugins\fh-tools       # 9 个 fh_* 工具
dsh-framework\furrhaven\skills\furrhaven-card  # 写卡技能
dsh-framework\furrhaven\theme                  # 金箔暖纸主题覆盖层

# 桌面安装器（Electron 壳 + 自动更新）
cd desktop
npm install
npx electron-builder --win nsis
# 产物：desktop/dist/Furrhaven-Studio-Setup-1.1.0.exe（自动更新指向 dsh-furrhaven-toolbox Releases）
```

独立 Tauri 原型已归档 `prototypes/tauri-studio/`（主题/动画规范与 Android 实验记录保留）。

## 目录

```
furrhaven-core/      L1 纯 Python 引擎（fh CLI，pytest）
dsh-framework/       DSH 官方框架 fork（独立仓库；furrhaven/ 叠加层 + upstream 同步）
prototypes/          Tauri 桌面原型（已归档，主题规范保留）
dsh/
  preset/card-forge/ L2 preset（写卡域任务路由 + persona）
  skill/furrhaven-card/SKILL.md
  plugin/fh-tools/   L2 插件（@dsh-external/dsh-fh-tools，9 个 fh 工具，已注入 DSH 验证）
tools/               迁移器/盘点器（参考项目资产 → 引擎）
docs/                调研/架构/计划/交接/盘点（权威分级）
```

## 文档导航

| 文档 | 用途 |
|------|------|
| `docs\03-交接文档_给下一个AI.md` | 接手开发入口（滚动更新） |
| `docs\01-架构框架设计.md` | 架构规范 v2.0 |
| `docs\02-开发更新计划.md` | 五阶段十一里程碑 v2.0 |
| `docs\04-资产盘点表.md` | 参考项目 118 脚本处置 |
| `docs\05-桌面端与移动端方案.md` | DSH fork 魔改路线 / 同步机制 / 主题动画 / Android 结论 |
| `docs\06-使用教程.md` | v1.0.0 使用教程（安装/双模式/三工坊/门禁/DSH 生态） |
| `docs\07-dsh生态接入.md` | DSH 官方生态接入验证与 `dsh plugin add` 安装方式 |
| `dsh\skill\furrhaven-card\SKILL.md` | 写卡流程纪律 |

## 开发与验收

```powershell
python -m pytest furrhaven-core\tests -q    # 引擎单测（21 项）
fh check --selftest                          # 引擎自检（CI 同款）
node --test dsh/preset/card-forge/test/      # preset 自测（Node 24 用通配路径）
.\scripts\sync-dsh.ps1                       # DSH 官方框架上游同步 + fork 自检
```

平台口径改动只改 `furrhaven-core/furrhaven/resources/platforms.yaml`；平台改版用 `fh calibrate fd` 探针实测回填 `platforms.local.yaml`。
