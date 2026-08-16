# dsh-furrhaven-desktop

Furrhaven Studio 桌面壳：基于 DeepSeek-Harness-Desktop（Electron）魔改，直接运行 DSH 官方 Web UI。

- 主题：新增「金箔暖纸」（furrhaven）家族，支持深/浅两套 + 衬线字体/等宽字体变量。
- 自动更新：`src/main/update.js` 指向 `YJLZSL/dsh-furrhaven-toolbox` Releases（每次发布 `Furrhaven-Studio-Setup-*.exe` 即可自动提示更新）。
- 安装：`electron-builder` 产出 NSIS `Furrhaven-Studio-Setup-<version>.exe`（非压缩包）。
- 运行时：优先复用官方 `Deepseek-Harness-Desktop` 已解压运行时；没有时需 `resources/vendor/deepseek-harness.tar`。

## 构建

```powershell
npm install
npx electron-builder --win nsis
# 产物：desktop/dist/Furrhaven-Studio-Setup-1.0.0.exe
```

## 开发

```powershell
npm install electron
npx electron .
```
