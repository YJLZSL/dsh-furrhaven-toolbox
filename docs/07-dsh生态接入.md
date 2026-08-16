# DSH 生态接入（v1.1 验证记录）

> 版本：1.0 | 2026-08-16 | 权威级别：规范 | 上游来源：官方 `docs/user/develop/basic/publish.md`

## 结论

已经按 DSH 官方插件生态的要求接入，不是“自造框架”：

1. 官方框架：fork `deepseek-ai/deepseek-harness`（`dsh-furrhaven`），直接使用 DSH 官方 Web UI / Electron 壳。
2. 插件可安装：`dsh-fh-tools` 现在是 **bundle** 包，带 `dsh.bundle` 清单 + `cordis.patch.yml`，可用 `dsh plugin --profile web add <repo-or-tgz>` 安装。
3. preset 进入官方 shipped preset root：`apps/cli/config/agent-presets/card-forge`。
4. 生态命名与 topic：仓库名 `dsh-*`，GitHub topics 含 `dsh-plugin`、`deepseek-harness`。
5. 上游同步：`scripts/sync-dsh.ps1` 已实测（fetch upstream → rebase furrhaven → preset 自测）。

## 官方验证方法

```powershell
# 1) 官方仓库 publish 文档确认 bundle 结构
#    dsh-framework/docs/user/develop/basic/publish.md

# 2) 本地安装验证（用打包后的 tgz）
dsh plugin --profile web add .\dsh-external-dsh-fh-tools-1.0.0.tgz
dsh plugin --profile web list

# 3) 源码 fork 同步
.\scripts\sync-dsh.ps1 -SkipSslVerify
```

## 注意事项

- bundle 的 `dsh.bundle.patch` 引用的包名必须与 `package.json.name` 一致（本插件为 `@dsh-external/dsh-fh-tools`）。
- 官方还支持 npm 发布后 `dsh plugin add your-package`；当前仓库 private，先走 tarball / git 安装。
- 主题接入 `packages/client/ui-theme` 属于 DSH client 插件规范（slot/store 纪律），作为 v1.1 后续项，暂以桌面壳主题 + `furrhaven-theme.css` 覆盖层交付。
