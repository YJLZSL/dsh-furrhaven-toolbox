import { invoke } from '@tauri-apps/api/core'
import { open } from '@tauri-apps/plugin-dialog'

interface FhOutput {
  code: number
  stdout: string
  stderr: string
  combined: string
}

interface DirEntry {
  name: string
  path: string
  is_dir: boolean
  is_file: boolean
}

interface CardInfo {
  slug: string
  type: string
  mode: string
  name: string
}

interface AuditRow {
  slug: string
  type: string
  name: string
  platforms: { name: string; used: number; limit: number; over: boolean }[]
}

const PLATFORMS: { key: string; label: string; note: string }[] = [
  { key: 'fd', label: 'FD', note: 'JSON 卡 · 单组件 ≤20,000' },
  { key: 'fc', label: 'FC', note: '8 目录包 · 总限 40,000' },
  { key: 'fb', label: 'FB', note: 'md · 10,666' },
  { key: 'st', label: '酒馆 ST', note: 'V2+V3 PNG' },
  { key: 'risu', label: 'RisuAI', note: 'V3 JSON' },
  { key: 'leinao', label: '类脑', note: 'V3 JSON' },
]

const state = {
  project: '',
  cards: [] as CardInfo[],
  currentFile: '',
  dirty: false,
}

function $(sel: string): HTMLElement {
  const el = document.querySelector<HTMLElement>(sel)
  if (!el) throw new Error(`missing element ${sel}`)
  return el
}

function input(sel: string): HTMLInputElement {
  return $(sel) as HTMLInputElement
}

function selectEl(sel: string): HTMLSelectElement {
  return $(sel) as HTMLSelectElement
}

function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function setStatus(text: string, isError = false): void {
  $('statusLeft').textContent = text
  $('statusLeft').classList.toggle('error', isError)
}

function setConsole(sel: string, text: string, code: number | null = null): void {
  const pre = $(sel) as HTMLPreElement
  pre.textContent = text
  pre.classList.toggle('ok', code === 0)
  pre.classList.toggle('fail', code !== null && code !== 0)
}

async function runFh(args: string[]): Promise<FhOutput> {
  if (!state.project) {
    setStatus('请先打开项目', true)
    throw new Error('project not open')
  }
  const out = await invoke<FhOutput>('run_fh', { cwd: state.project, args })
  return out
}

function parseList(text: string): CardInfo[] {
  const cards: CardInfo[] = []
  for (const line of text.split('\n')) {
    const m = line.match(/^\s*(\S+)\s+\[([^\]]+)\]\s+(\S+)\s+(.*)$/)
    if (m) {
      cards.push({ slug: m[1], type: m[2], mode: m[3], name: m[4].trim() || m[1] })
    }
  }
  return cards
}

function parseAudit(text: string): AuditRow[] {
  const rows: AuditRow[] = []
  let current: AuditRow | null = null
  for (const line of text.split('\n')) {
    const head = line.match(/^== (.+?) \[(.+?)\] (.*)==$/)
    if (head) {
      current = { slug: head[1], type: head[2], name: head[3].trim() || head[1], platforms: [] }
      rows.push(current)
      continue
    }
    if (current) {
      const m = line.match(/^\s+([✓⚠])\s+(\w+):\s+(\d+)\/(\d+) B/)
      if (m) {
        current.platforms.push({
          name: m[2],
          used: Number(m[3]),
          limit: Number(m[4]),
          over: m[1] === '⚠',
        })
      }
    }
  }
  return rows
}

function renderDashboard(auditText: string): void {
  state.cards = parseList(auditText.length ? auditText : '')
  const rows = parseAudit(auditText)
  const grid = $('dashboardCards')
  const empty = $('dashboardEmpty')
  if (rows.length === 0) {
    grid.innerHTML = ''
    empty.classList.remove('hidden')
    setConsole('auditReport', auditText || '尚未打开项目')
    return
  }
  empty.classList.add('hidden')
  grid.innerHTML = rows
    .map((row) => {
      const platforms = row.platforms
        .map((p) => {
          const pct = p.limit > 0 ? Math.min(100, Math.round((p.used / p.limit) * 100)) : 0
          const cls = p.over ? 'bar over' : 'bar'
          return `<div class="budget-row">
            <span class="budget-name">${escapeHtml(p.name.toUpperCase())}</span>
            <div class="bar-track"><div class="${cls}" style="width:${pct}%"><i class="bar-shine"></i></div></div>
            <span class="budget-num ${p.over ? 'over-text' : ''}">${p.used.toLocaleString()}/${p.limit.toLocaleString()}</span>
          </div>`
        })
        .join('')
      return `<article class="card-tile">
        <div class="card-tile-head">
          <div class="card-glyph">${escapeHtml(row.type.slice(0, 1).toUpperCase())}</div>
          <div class="card-tile-title">
            <h3>${escapeHtml(row.name)}</h3>
            <p>${escapeHtml(row.slug)} · ${escapeHtml(row.type)}</p>
          </div>
        </div>
        <div class="card-tile-body">${platforms || '<p class="muted">暂无字节数据</p>'}</div>
      </article>`
    })
    .join('')
  setConsole('auditReport', auditText, 0)
}

async function refreshDashboard(): Promise<void> {
  if (!state.project) return
  setStatus('刷新中…')
  try {
    const list = await runFh(['list'])
    state.cards = parseList(list.combined)
    syncCardSelects()
    const audit = await runFh(['audit'])
    renderDashboard(audit.combined)
    setStatus('已刷新')
  } catch (e) {
    setStatus(String(e), true)
  }
}

function syncCardSelects(): void {
  const options = state.cards
    .map((c) => `<option value="${escapeHtml(c.slug)}">${escapeHtml(c.name)}（${escapeHtml(c.slug)}）</option>`)
    .join('')
  for (const sel of ['editorCardSelect', 'wbCard', 'playCard']) {
    const el = selectEl(sel)
    const prev = el.value
    el.innerHTML = options
    if (prev && state.cards.some((c) => c.slug === prev)) el.value = prev
  }
}

// ── 导航 ────────────────────────────────────────────────────────────────────
function switchSection(section: string): void {
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.classList.toggle('active', (btn as HTMLElement).dataset.section === section)
  })
  document.querySelectorAll('.panel').forEach((panel) => {
    panel.classList.remove('active')
  })
  const target = document.getElementById(section)
  if (target) target.classList.add('active')
  if (section === 'editor') void loadEditorTree()
  if (section === 'settings') void loadConfig()
}

// ── 项目 ────────────────────────────────────────────────────────────────────
async function pickProject(): Promise<void> {
  const selected = await open({ directory: true, title: '选择 fh 项目目录' })
  if (typeof selected === 'string') await setProject(selected)
}

async function setProject(path: string): Promise<void> {
  try {
    const ok = await invoke<boolean>('file_exists', { path: `${path}/fh.config.yaml` })
    if (!ok) {
      setStatus('所选目录没有 fh.config.yaml（先 fh init）', true)
      return
    }
    state.project = path
    localStorage.setItem('furrhaven.project', path)
    $('projectPath').textContent = path
    $('projectName').textContent = path.split(/[\\/]/).filter(Boolean).pop() || '—'
    setStatus('项目已打开')
    await refreshDashboard()
  } catch (e) {
    setStatus(String(e), true)
  }
}

// ── 编辑器 ──────────────────────────────────────────────────────────────────
async function listTree(path: string): Promise<DirEntry[]> {
  return await invoke<DirEntry[]>('list_dir', { path })
}

async function loadEditorTree(): Promise<void> {
  const slug = selectEl('editorCardSelect').value
  if (!slug) return
  const cardDir = `${state.project}/cards/${slug}`
  const files: { path: string; label: string; depth: number }[] = []
  async function walk(dir: string, depth: number): Promise<void> {
    if (depth > 3) return
    for (const entry of await listTree(dir)) {
      if (entry.is_dir && entry.name !== 'dist') {
        await walk(entry.path, depth + 1)
      } else if (entry.is_file && /\.(md|yaml|yml|json)$/.test(entry.name)) {
        files.push({ path: entry.path, label: `${'  '.repeat(depth)}${entry.name}`, depth })
      }
    }
  }
  try {
    await walk(cardDir, 0)
  } catch (e) {
    setStatus(String(e), true)
    return
  }
  const tree = $('fileTree')
  tree.innerHTML = files
    .map((f) => `<li class="file-node" data-path="${escapeHtml(f.path)}">${escapeHtml(f.label)}</li>`)
    .join('')
  tree.querySelectorAll('.file-node').forEach((node) => {
    node.addEventListener('click', () => void openFile((node as HTMLElement).dataset.path || ''))
  })
  if (files.length > 0) await openFile(files[0].path)
}

async function openFile(path: string): Promise<void> {
  try {
    const content = await invoke<string>('read_text_file', { path })
    state.currentFile = path
    $('editingPath').textContent = path
    ;($('editorText') as HTMLTextAreaElement).value = content
    markDirty(false)
    $('editorStatus').textContent = '已载入'
  } catch (e) {
    setStatus(String(e), true)
  }
}

function markDirty(dirty: boolean): void {
  state.dirty = dirty
  $('dirtyDot').classList.toggle('hidden', !dirty)
  $('editorStatus').textContent = dirty ? '未保存' : '已载入'
}

async function saveFile(): Promise<void> {
  if (!state.currentFile) return
  const content = ($('editorText') as HTMLTextAreaElement).value
  try {
    await invoke('write_text_file', { path: state.currentFile, content })
    markDirty(false)
    setStatus('已保存')
  } catch (e) {
    setStatus(String(e), true)
  }
}

// ── 构建 ────────────────────────────────────────────────────────────────────
function renderPlatformGrid(): void {
  $('platformGrid').innerHTML = PLATFORMS.map(
    (p) => `<label class="platform-tile"><input type="checkbox" data-platform="${p.key}" checked />
      <span class="platform-key">${p.key}</span><span class="platform-label">${p.label}</span>
      <span class="platform-note">${p.note}</span></label>`,
  ).join('')
}

async function runBuild(): Promise<void> {
  const selected = [...document.querySelectorAll<HTMLInputElement>('input[data-platform]:checked')]
    .map((el) => el.dataset.platform || '')
  if (selected.length === 0) {
    setStatus('至少勾选一个平台', true)
    return
  }
  $('buildStage').classList.remove('hidden')
  setConsole('buildOutput', '')
  try {
    const args = ['build', '--platform', selected.join(',')]
    const card = input('buildCard').value.trim()
    if (card) args.push('--card', card)
    const out = await runFh(args)
    setConsole('buildOutput', out.combined, out.code)
    setStatus(out.code === 0 ? '构建完成' : '构建有错误', out.code !== 0)
    if (out.code === 0) await refreshDashboard()
  } catch (e) {
    setConsole('buildOutput', String(e), -1)
    setStatus('构建失败', true)
  } finally {
    $('buildStage').classList.add('hidden')
  }
}

// ── 工坊 / 试玩 / 识图 ──────────────────────────────────────────────────────
async function runWorkshop(which: 'wb' | 'comp' | 'regex'): Promise<void> {
  try {
    if (which === 'wb') {
      const card = selectEl('wbCard').value
      const text = input('wbText').value.trim()
      if (!card || !text) return
      const out = await runFh(['wb', 'sim', '--card', card, '--text', text])
      setConsole('wbOutput', out.combined, out.code)
    } else if (which === 'comp') {
      const args = ['comp', 'check']
      const card = input('compCard').value.trim()
      const name = input('compName').value.trim()
      if (card) args.push('--card', card)
      if (name) args.push('--name', name)
      const out = await runFh(args)
      setConsole('compOutput', out.combined, out.code)
    } else {
      const text = input('regexText').value.trim()
      if (!text) return
      const out = await runFh(['regex', 'test', '--text', text])
      setConsole('regexOutput', out.combined, out.code)
    }
  } catch (e) {
    setStatus(String(e), true)
  }
}

async function runPlay(): Promise<void> {
  const slug = selectEl('playCard').value
  const say = input('playSay').value.trim()
  if (!slug || !say) return
  setConsole('playOutput', '思考中…')
  $('playBubble').classList.add('hidden')
  try {
    const out = await runFh(['play', slug, '--say', say])
    const text = out.combined.replace(/^\[fh OK\]\s*/m, '').trim()
    setConsole('playOutput', out.combined, out.code)
    const bubble = $('playBubble')
    bubble.textContent = text
    bubble.classList.remove('hidden')
    setStatus(out.code === 0 ? '回复已生成' : '扮演模式错误', out.code !== 0)
  } catch (e) {
    setConsole('playOutput', String(e), -1)
  }
}

async function runVision(): Promise<void> {
  const image = input('visionImage').value.trim()
  if (!image) return
  const mode = selectEl('visionMode').value
  const card = input('visionCard').value.trim()
  try {
    const args = ['vision', image, '--mode', mode]
    if (card) args.push('--card', card)
    const out = await runFh(args)
    setConsole('visionOutput', out.combined, out.code)
    setStatus(out.code === 0 ? '识图完成' : '识图失败', out.code !== 0)
  } catch (e) {
    setConsole('visionOutput', String(e), -1)
  }
}

async function loadConfig(): Promise<void> {
  if (!state.project) return
  try {
    const content = await invoke<string>('read_text_file', { path: `${state.project}/fh.config.yaml` })
    ;($('configEditor') as HTMLTextAreaElement).value = content
    $('configStatus').textContent = '已载入 fh.config.yaml'
  } catch (e) {
    $('configStatus').textContent = String(e)
  }
}

async function saveConfig(): Promise<void> {
  if (!state.project) return
  try {
    await invoke('write_text_file', {
      path: `${state.project}/fh.config.yaml`,
      content: ($('configEditor') as HTMLTextAreaElement).value,
    })
    $('configStatus').textContent = '已保存；重新打开项目/刷新后生效'
    setStatus('配置已保存')
  } catch (e) {
    $('configStatus').textContent = String(e)
  }
}

// ── 启动 ────────────────────────────────────────────────────────────────────
async function boot(): Promise<void> {
  renderPlatformGrid()

  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchSection((btn as HTMLElement).dataset.section || 'dashboard'))
  })
  document.querySelectorAll('.ws-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const which = (tab as HTMLElement).dataset.ws
      document.querySelectorAll('.ws-tab').forEach((t) => t.classList.toggle('active', t === tab))
      document.querySelectorAll('.ws-pane').forEach((p) => {
        p.classList.toggle('active', p.id === `ws-${which}`)
      })
    })
  })

  $('btnPickProject').addEventListener('click', () => void pickProject())
  $('btnRefresh').addEventListener('click', () => void refreshDashboard())
  selectEl('editorCardSelect').addEventListener('change', () => void loadEditorTree())
  ;($('editorText') as HTMLTextAreaElement).addEventListener('input', () => markDirty(true))
  $('btnSaveFile').addEventListener('click', () => void saveFile())
  $('btnBuild').addEventListener('click', () => void runBuild())
  $('btnWbSim').addEventListener('click', () => void runWorkshop('wb'))
  $('btnCompCheck').addEventListener('click', () => void runWorkshop('comp'))
  $('btnRegexTest').addEventListener('click', () => void runWorkshop('regex'))
  $('btnPlay').addEventListener('click', () => void runPlay())
  $('btnVision').addEventListener('click', () => void runVision())
  $('btnSaveConfig').addEventListener('click', () => void saveConfig())

  try {
    const version = await invoke<FhOutput>('fh_version')
    const v = version.combined.trim().split(/\s+/)[1]
    $('engineBadge').textContent = v ? `fh ${v}` : 'fh —'
  } catch {
    $('engineBadge').textContent = 'fh 未安装'
  }

  const saved = localStorage.getItem('furrhaven.project')
  if (saved) await setProject(saved)
}

void boot()
