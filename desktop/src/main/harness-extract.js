const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { app } = require('electron');

function looseHarnessRoot() {
  return path.join(process.resourcesPath, 'vendor', 'deepseek-harness');
}

function harnessArchivePath() {
  return path.join(process.resourcesPath, 'vendor', 'deepseek-harness.tar');
}

function extractedHarnessRoot() {
  return path.join(app.getPath('userData'), 'runtime', app.getVersion());
}

/** 兼容已安装的官方 DSH 桌面端运行时（方便迁移，无需重新下载运行时）。 */
function legacyHarnessRoot() {
  if (process.platform !== 'win32' || !process.env.APPDATA) return null;
  return path.join(process.env.APPDATA, 'Deepseek-Harness-Desktop', 'runtime', '0.1.3');
}

function hasBuiltHarness(root) {
  return fs.existsSync(path.join(root, 'apps', 'cli', 'lib', 'bin.js'))
    && fs.existsSync(path.join(root, 'apps', 'web', 'dist', 'index.html'));
}

function packagedHarnessRoot() {
  const extracted = extractedHarnessRoot();
  if (hasBuiltHarness(extracted)) {
    return extracted;
  }
  const legacy = legacyHarnessRoot();
  if (legacy && hasBuiltHarness(legacy)) {
    return legacy;
  }
  const loose = looseHarnessRoot();
  if (hasBuiltHarness(loose)) {
    return loose;
  }
  return extracted;
}

function runTar(args) {
  return new Promise((resolve, reject) => {
    const child = spawn('tar', args, {
      windowsHide: true,
      stdio: ['ignore', 'ignore', 'pipe'],
    });
    let stderr = '';
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString('utf8');
    });
    child.on('error', reject);
    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(stderr.trim() || `tar 退出码 ${code}`));
    });
  });
}

async function ensurePackagedHarness(log = () => {}) {
  if (!app.isPackaged) {
    return null;
  }
  const dest = extractedHarnessRoot();
  if (hasBuiltHarness(dest)) {
    return dest;
  }
  const loose = looseHarnessRoot();
  if (hasBuiltHarness(loose)) {
    return loose;
  }
  const legacy = legacyHarnessRoot();
  if (legacy && hasBuiltHarness(legacy)) {
    log(`复用官方 DSH 运行时：${legacy}`);
    return legacy;
  }
  const archive = harnessArchivePath();
  if (!fs.existsSync(archive)) {
    throw new Error('缺少运行时归档 deepseek-harness.tar（可从 dsh-furrhaven-toolbox Release 获取，或先安装官方 Deepseek-Harness-Desktop 以复用运行时）');
  }
  log('正在解压运行时（仅首次，之后会变快）…');
  fs.rmSync(dest, { recursive: true, force: true });
  fs.mkdirSync(dest, { recursive: true });
  await runTar(['-xf', archive, '-C', dest]);
  if (!hasBuiltHarness(dest)) {
    throw new Error('运行时解压不完整，请重新安装');
  }
  log(`运行时已解压到 ${dest}`);
  return dest;
}

module.exports = {
  harnessArchivePath,
  extractedHarnessRoot,
  packagedHarnessRoot,
  ensurePackagedHarness,
  hasBuiltHarness,
};
