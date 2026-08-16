# Furrhaven · DSH 附属插件（即安即用，即删）

> 版本：v1.3.0 | 2026-08-16 | 定位：**DeepSeek Harness 附属插件**，安装后自动获得角色卡多平台写卡工具面与流程技能；卸载即清理。
> 面向人群：普通 DSH 用户 / 角色卡作者 / 想在 AI 里直接写卡的人。

## 这是什么

Furrhaven 是一套「卡体写作 + 世界书 + 组件 + 正则 + 多平台导出」的角色卡工具箱，现在以 **DSH 插件** 形式分发：

- 安装后自动注册 **9 个 `fh_*` 工具**：`fh_new` / `fh_build` / `fh_check` / `fh_audit` / `fh_wb_sim` / `fh_comp_check` / `fh_regex_test` / `fh_vision` / `fh_play`
- 自动注册 **`furrhaven-card` 技能**：写卡流程纪律 + 官方 `changeMsg`/`getMsgContent` 组件思路 + 防 AI 味提示包
- 卸载即删：工具、技能、bundle 层全部随插件 dispose 清理
- 底层是独立 Python 引擎 `furrhaven-core`（`fh` CLI），DSH 插件只是薄封装

## 小白一键提示词（复制给任意 AI）

前提：你已经安装好 DeepSeek Harness（DSH）。把下面这段直接粘贴给你的 AI 助手，它就能帮你安装并开始使用：

```text
我已经装好了 DeepSeek Harness（DSH），现在想安装 Furrhaven 插件（DSH 附属插件，即安即用即删）：
1. 先确认 Python 已安装；没有就帮我安装 Python 3.11+。
2. 进入 Furrhaven 仓库根目录，运行：pip install -e furrhaven-core
3. 用 DSH 官方方式安装插件：dsh plugin --profile web add .\dsh-external-dsh-fh-tools-1.3.0.tgz
   如果当前环境没有 dsh 命令，就改用 DSH 超级注入器：dev_inject_plugin <仓库>\dsh\plugin\fh-tools
4. 运行 fh check --selftest 验证插件对应的引擎已就绪。
5. 然后帮我创建角色卡项目：fh init ./my-project && cd ./my-project && fh new 测试角色 --full
6. 最后用 fh check 和 fh build --platform all 完成门禁与构建。
如果不知道插件路径，先浏览本仓库根目录，找到 dsh/plugin/fh-tools 或 release 里的 tgz。
```

## 安装（手动）

```powershell
# 引擎
pip install -e .\furrhaven-core
fh check --selftest

# 插件（二选一）
# A. 官方 bundle 安装
dsh plugin --profile web add .\dsh-external-dsh-fh-tools-1.3.0.tgz
# B. super-injector 热载
dev_inject_plugin <本仓库>\dsh\plugin\fh-tools

# 卸载
dsh plugin --profile web remove dsh-fh-tools
# 或 super-injector
dev_uninject_plugin dsh-fh-tools
```

## 能力

- 卡型系统：character / character.activity / simulator / bigworld / custom；模块化 IR 与**完整卡单文件**双写法；宽容解析器兼容多种作者格式
- 世界书工坊：触发模拟、keys 误触发分析、共享世界观、预算
- 组件工坊：FD 五坑 + 拉长四禁 + `changeMsg`/`getMsgContent` 嵌套思路 + 开场切换
- 正则工坊：FC v2.3 模板包、测试台、排序陷阱检查
- 导出：FD / FC（40k 总限）/ FB / 酒馆 V2+V3 PNG / ST world+regex JSON / RisuAI / 类脑
- 识图、扮演、审阅双向流、动画 showcase、构建指纹与门禁

## 平台口径速查

| 平台 | 红线 |
|------|------|
| FD | 卡 50,000；世界书 30,000；**单组件 source ≤20,000** |
| FC | **上传资料包总限 40,000** |
| FB | 10,666 |
| 酒馆/Risu | V2 `chara` + V3 `ccv3` chunk，无硬限 |

## 目录

```
furrhaven-core/      Python 引擎（fh CLI，pytest）
dsh/plugin/fh-tools/ DSH 附属插件（9 工具 + 技能 + bundle）
dsh/skill/           furrhaven-card 技能源文件
dsh/preset/          card-forge 写卡 preset（可选）
tools/               资产迁移/盘点工具
docs/                调研/架构/交接/教程/生态接入
```

## 文档导航

| 文档 | 用途 |
|------|------|
| `docs\01-架构框架设计.md` | 架构规范 |
| `docs\03-交接文档_给下一个AI.md` | 接手开发入口（滚动更新） |
| `docs\04-资产盘点表.md` | 参考项目 118 脚本处置 |
| `docs\06-使用教程.md` | 使用教程 |
| `docs\07-dsh生态接入.md` | DSH 生态接入与 `dsh plugin add` 验证 |
| `dsh\skill\furrhaven-card\SKILL.md` | 写卡流程纪律 |

## 开发与验收

```powershell
python -m pytest furrhaven-core\tests -q    # 引擎单测（21 项）
fh check --selftest                          # 引擎自检
node --test dsh/preset/card-forge/test/      # preset 自测
```

平台口径改动只改 `furrhaven-core/furrhaven/resources/platforms.yaml`。
