# Changelog

所有值得注意的变更记录于此。版本号遵循 semver；平台口径 / IR schema 破坏性变更会 bump minor 并提供迁移说明。

## [0.2.0-dev] - 2026-08-16

### Changed

- **FC 口径修订（用户拍板）**：FC 上传资料包总限制由 15,000 改为 **40,000 UTF-8 字节**；`fh budget`/`fh check` 现在按 卡+开场白+简介+世界书+回复格式+正则+故事线 全量核算。
- FD 单组件 source ≤20,000 硬限保持不变。

### Added

- **桌面端改为 DSH 官方框架魔改（用户方向修正）**：
  - fork `deepseek-ai/deepseek-harness` → `dsh-framework/`（私有镜像 `YJLZSL/furrhaven-dsh`，默认分支 `furrhaven`，upstream=官方）
  - `scripts/sync-dsh.ps1`：fetch upstream → rebase furrhaven → preset node --test 自测（已实测通过）
  - fork 内 `furrhaven/` 叠加层：card-forge preset / fh-tools plugin / furrhaven-card skill / 金箔暖纸主题 CSS
  - 独立 Tauri 原型归档到 `prototypes/tauri-studio/`（NSIS 安装包已产出，仅作记录）
- **Android 可行性实验（Tauri 路线，已归档）**：`tauri android init` 成功、arm64-v8a Rust 库编译入 jniLibs；APK 出包受本机 Gradle 证书/代理拦截未完成。正式移动路线待 DSH Web UI 主题接入后立项。
- `docs/05-桌面端与移动端方案.md`：技术选型 / 美术规范 / 动画规范 / Android 结论。

## [0.1.0] - 2026-08-16

### Added（M0 + M1/M2 核心链路 + 三工坊核心 + 用户追加能力）

- **L1 引擎 `furrhaven-core`**（`fh` CLI，Python 3.11+，PyYAML 唯一外部依赖）
  - `fh init`：L3 项目工作区脚手架（cards/shared/components/regex/assets/dist/reviews）
  - `fh new`：模块化 IR（card.yaml + 分区 md + worldbook/*.md）与 **完整卡单文件模式**（`--full`，卡体+世界书+组件+正则一把梭）
  - 宽容解析器：中英标题别名、front-matter、`# name/# personality` 自由模式写法、fenced YAML/JSON、外部卡导入（`fh import` FD JSON / ST V2V3 JSON / PNG / 任意 md）
  - 卡型系统：character / character.activity / simulator / bigworld / custom（模板继承与规则包开关预留）
  - `fh build`：IR → **FD JSON（自由模式 v3.0 字节口径）/ FC 8 目录资料包 / FB md / SillyTavern V2+V3 PNG（`chara`+`ccv3` tEXt chunk）/ RisuAI V3 / 类脑 V3**
  - 构建指纹锁 `.fh-lock.yaml` + `fh check` 漂移检测
  - `fh budget`：口径表驱动 UTF-8 字节核算（FD 字段级余量表）
  - `fh check`：lint 规则引擎（IR/FD/WB/COMP/REGEX/BYTE/CONTENT/PROSE/FURRY），退出码 0/1/2
  - `fh check --selftest`：无外部依赖引擎自检（10 项）
- **三工坊核心**
  - 世界书：`fh wb list/keys/sim/add`（keys 误触发分析、触发模拟器含递归 depth=1、预算）
  - 组件：`fh comp new/list/check/extract/doc`（FD 五坑 + 拉长四禁 + 花括号/node --check/:root + 槽位协议文档）
  - 正则：`fh regex test/check` + **FC 统一渲染 v2.3 模板包 15 条全量迁移**（`tools/migrate_regex_v23.py`）
- **识图模式 `fh vision`**：OpenAI 兼容视觉接口读立绘/参考图/平台截图（character/ui 两档 prompt），`--card` 写入 assets/
- **扮演模式 `fh play`**：卡体+常驻世界书组装系统提示，世界书 keys 按轮触发注入；`--say` 单轮测试（CI 可用）
- **DSH 三件套骨架**
  - preset `dsh/preset/card-forge`：写卡域 react/spec/weak 路由 + persona（node --test 7 项全绿；已装入 `~/.dsh/.agent-presets/card-forge`）
  - skill `dsh/skill/furrhaven-card/SKILL.md`：任务路由/双模式/五步流程/fh 命令域/错误恢复表
  - plugin `dsh/plugin/fh-tools`：fh_new/build/check/audit/wb_sim/comp_check/regex_test/vision/play 九工具（tsc 编译，super-injector 注入 DSH 验证 active）
- **资产盘点**：`tools/make_asset_inventory.py` → `docs/04-资产盘点表.md`（118 脚本：13 迁移泛化 / 101 教训入 lint / 4 不迁移）

### 已知限制（下一阶段）

- 审阅双向流完整版（`fh review export/apply` + 状态机锁）未实现
- simulator/bigworld 卡型模板已预留，组件集与专属规则包待 M8/M9
- 平台导入实测（FD/FC/FB/ST 各传一张）待做；`fh calibrate` 只有 FD 探针生成
- 公开仓脱敏审查未做（参考项目角色名/立绘/专属词不得入公开仓）
