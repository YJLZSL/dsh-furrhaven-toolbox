# Furrhaven Studio（Tauri 原型，已归档）

> 状态：**superseded（2026-08-16）**。用户方向修正：桌面端直接 fork/魔改 DeepSeek Harness 官方框架，不再使用独立 Tauri 栈。
> 本目录保留原因：①「金箔暖纸工坊」主题与动画规范可直接移植到 DSH client UI；② Android/Tauri mobile 可行性实验记录（Gradle 工程、arm64 .so 已打通，见 `docs/05-桌面端与移动端方案.md`）。

正式路线：DSH 官方框架 fork（本地 `dsh-framework/`，upstream 同步脚本见 `scripts/sync-dsh.ps1`）+ Furrhaven preset/skill/plugin 集成。
