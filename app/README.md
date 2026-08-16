# Furrhaven Studio（桌面端 / Android 尝试）

Tauri 2 + 原生 TypeScript 前端。视觉主题「金箔暖纸工坊」：深褐木案 × 暖金描边 × 米纸面板 × 墨字，动画全部尊重 `prefers-reduced-motion`。

## 功能

- **工作台**：项目开关、卡列表、每卡 × 平台字节余量动画条、全项目审计
- **卡编辑**：模块化 IR 文件树（card.yaml / 分区 md / worldbook）与完整卡 `card.md` 直接编辑保存
- **三工坊**：世界书触发模拟 / 组件五坑检查 / 正则 v2.3 渲染测试
- **构建发布**：FD/FC/FB/酒馆 ST V2V3/RisuAI/类脑 多选构建，产物进 `dist/`
- **扮演试玩 / 识图**：`fh play --say` 与 `fh vision` 的 GUI 面板
- **设置**：直接编辑 `fh.config.yaml`

后端 Rust 命令全部薄封装 `fh` CLI（无 `fh` 时回退 `python -m furrhaven.cli`）。

## 开发

```bash
npm install
npm run tauri dev          # 桌面调试
npm run tauri build        # 发布构建（NSIS 安装包）
```

## Android（可行性实验）

```powershell
rustup target add aarch64-linux-android
$env:ANDROID_HOME="$env:LOCALAPPDATA\Android\Sdk"
$env:ANDROID_SDK_ROOT=$env:ANDROID_HOME
$env:NDK_HOME=(Get-ChildItem "$env:ANDROID_HOME\ndk" -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
npx tauri android init
npx tauri android build --apk --debug
```

APK 产物：`src-tauri/gen/android/app/build/outputs/apk/`。桌面端复用同一套 WebView 前端；Android 侧主要工作是触控布局与文件选择。
