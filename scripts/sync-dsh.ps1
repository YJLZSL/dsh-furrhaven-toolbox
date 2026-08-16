# Furrhaven DSH fork 同步脚本
#
# 用法：
#   .\scripts\sync-dsh.ps1                 # 从 upstream（官方 DSH）fetch + rebase furrhaven 分支
#   .\scripts\sync-dsh.ps1 -Publish        # 把本仓 dsh/ 资产发布进 fork 的 furrhaven/ 层并提交
#   .\scripts\sync-dsh.ps1 -SkipSslVerify  # 本机 git 证书链不完整时启用（一次命令）
#
# 前提：fork 位于 <本仓>\dsh-framework，remote:
#   origin   = https://github.com/YJLZSL/dsh-furrhaven.git
#   upstream = https://github.com/deepseek-ai/deepseek-harness.git
[CmdletBinding()]
param(
    [string]$ForkPath = '',
    [switch]$Publish,
    [switch]$SkipSslVerify
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $ForkPath) { $ForkPath = Join-Path $repoRoot 'dsh-framework' }
if (-not (Test-Path (Join-Path $ForkPath '.git'))) {
    throw "DSH fork 不存在：$ForkPath（先 clone official repo，remote origin 指向私有镜像）"
}

$gitArgs = @('-C', $ForkPath)
if ($SkipSslVerify) { $gitArgs += '-c', 'http.sslVerify=false' }

Write-Host "== fork: $ForkPath"

# 1. 上游同步
git @gitArgs fetch upstream --prune
if ($LASTEXITCODE -ne 0) { throw 'fetch upstream 失败' }

$current = git @gitArgs rev-parse --abbrev-ref HEAD
if ($current -ne 'furrhaven') {
    Write-Host "当前分支 $current，切换到 furrhaven"
    git @gitArgs checkout furrhaven
}

git @gitArgs rebase upstream/master
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'rebase 冲突：先 git rebase --abort 或解决冲突后继续；本脚本不再自动提交。'
    exit 1
}

# 2. 可选：把本仓 dsh/ 资产发布进 fork 层
if ($Publish) {
    $dest = Join-Path $ForkPath 'furrhaven'
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item (Join-Path $repoRoot 'dsh\preset\card-forge\*') (Join-Path $dest 'presets\card-forge') -Recurse -Force
    Copy-Item (Join-Path $repoRoot 'dsh\skill\furrhaven-card\*') (Join-Path $dest 'skills\furrhaven-card') -Recurse -Force
    Copy-Item (Join-Path $repoRoot 'dsh\plugin\fh-tools\src\*') (Join-Path $dest 'plugins\fh-tools\src') -Recurse -Force
    Copy-Item (Join-Path $repoRoot 'dsh\plugin\fh-tools\package.json') (Join-Path $dest 'plugins\fh-tools\package.json') -Force
    git @gitArgs add furrhaven
    $diff = git @gitArgs diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git @gitArgs commit -m 'furrhaven: publish write-card assets from toolbox repo'
    } else {
        Write-Host '资产无变化，跳过提交'
    }
}

# 3. 自检：preset 零依赖测试
node --test (Join-Path $ForkPath 'furrhaven\presets\card-forge\test\card-forge-core.test.mjs')
if ($LASTEXITCODE -ne 0) { throw 'preset 自测失败' }

Write-Host '== 同步完成 =='
git @gitArgs log --oneline -3
git @gitArgs status --short
