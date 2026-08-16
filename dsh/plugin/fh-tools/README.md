# @dsh-external/dsh-fh-tools

Furrhaven 写卡工具箱的 DSH 工具面：把 `fh` CLI 的 9 个命令挂进工具目录。

| 工具 | 命令 | 用途 |
|------|------|------|
| `fh_new` | fh new | 新建卡（模块化 / --full 完整卡） |
| `fh_build` | fh build | IR → FD/FC/FB/酒馆 V2V3 PNG/RisuAI/类脑 |
| `fh_check` | fh check | 门禁聚合（退出码 0=可交付） |
| `fh_audit` | fh audit | 全项目字节余量与资产盘点 |
| `fh_wb_sim` | fh wb sim | 世界书触发模拟器 |
| `fh_comp_check` | fh comp check | 组件五坑 + 拉长四禁检查 |
| `fh_regex_test` | fh regex test | 正则测试台 |
| `fh_vision` | fh vision | 识图模式（立绘/平台截图） |
| `fh_play` | fh play --say | 扮演模式单轮试玩 |

依赖：`fh` CLI（`pip install -e furrhaven-core`）。

## 构建

```bash
# 需要 DSH 源码 checkout（vendor/cordis、packages/core/tools）
DSH_CHECKOUT=<dsh-checkout> bash scripts/build.sh
```

## 热载验证（super-injector）

```
dev_inject_plugin <本目录>
dev_plugin_status          # 看到 @dsh-external/dsh-fh-tools [injected] active
dev_reload_package fh-tools # 改代码后热重载
dev_uninject_plugin fh-tools # 卸载
```

