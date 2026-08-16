# Card Forge（Furrhaven）· DSH Agent Preset

让 DeepSeek Harness 进入「角色卡创作专家」模式的 agent preset。

## 功能

- 写卡域任务路由：新建/生成 → 直接生产；修卡/审计 → 先定位后动手；模糊任务 → 模型自路由
- 首轮窄工具面，首个工具调用后开放完整目录
- 与 `furrhaven-card` 技能、`dsh-fh-tools` 插件配合

## 安装

```powershell
Copy-Item .\dsh\preset\card-forge $env:USERPROFILE\.dsh\.agent-presets\ -Recurse -Force
```

## 使用

在 DSH 新建会话时选择 **Card Forge（Furrhaven）** preset。之后 AI 会按写卡流程工作，并使用 `fh_*` 工具。

## 自测

```bash
node --test test/card-forge-core.test.mjs
```
