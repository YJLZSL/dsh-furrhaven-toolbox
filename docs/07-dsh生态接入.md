# DSH 生态接入（v1.2.0）

> 版本：2.0 | 2026-08-16 | 权威级别：规范 | 上游来源：官方 `docs/user/develop/basic/publish.md`

## 结论

Furrhaven 现在是 **DSH 附属插件**（`@dsh-external/dsh-fh-tools`），即安即用、即删：

1. 插件是官方 **bundle**：`package.json` 带 `dsh.bundle.patch` + `cordis.patch.yml`。
2. `dsh plugin --profile web add <tgz|repo>` 可安装；`remove` 即删。
3. 安装后自动注册 9 个 `fh_*` 工具 + `furrhaven-card` 技能（`ctx.skills.register`）。
4. 仓库使用 `dsh-` 命名与 `dsh-plugin` topic，已公开开放。
5. 官方 fork / 桌面安装器已从主仓删除，不再作为主路线。

## 安装验证

```powershell
# 引擎
pip install -e furrhaven-core

# 插件（二选一）
dsh plugin --profile web add .\dsh-external-dsh-fh-tools-1.2.0.tgz
# 或 super-injector
dev_inject_plugin <repo>\dsh\plugin\fh-tools

# 卸载
dsh plugin --profile web remove dsh-fh-tools
dev_uninject_plugin dsh-fh-tools
```

## 注意事项

- `dsh.bundle.patch` 引用的包名必须与 `package.json.name` 一致（`@dsh-external/dsh-fh-tools`）。
- 技能内容随插件内置（`skills/furrhaven-card/SKILL.md`），插件加载时注册、dispose 时注销。
- 官方还支持 npm 发布后 `dsh plugin add <npm-package>`；当前以 GitHub Release tgz 与 git 安装为主。
