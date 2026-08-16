# Furrhaven 安装脚本：L1 引擎 + L2 preset/skill 落地（plugin 构建用 dev_build_plugin 或手工 tsc）
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host '[1/3] pip install -e furrhaven-core'
python -m pip install -e (Join-Path $root 'furrhaven-core')

Write-Host '[2/3] install card-forge preset'
$dst = Join-Path $env:USERPROFILE '.dsh\.agent-presets\card-forge'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item (Join-Path $root 'dsh\preset\card-forge\*') -Destination $dst -Recurse -Force

Write-Host '[3/3] selftest'
fh check --selftest

Write-Host @'

完成。plugin fh-tools 已编译则运行：
  dsh plugin --profile web add <repo>/dsh/plugin/fh-tools
或用 super-injector：dev_inject_plugin <repo>/dsh/plugin/fh-tools
skill：把 dsh/skill/furrhaven-card 复制到项目 .agents/skills/ 即可被发现。
'@
