/**
 * @dsh-external/dsh-fh-tools — Furrhaven 写卡工具箱工具面。
 *
 * 每个工具都是 `fh` CLI 的薄封装：L1 引擎纯 Python、零 DSH 依赖；
 * 本插件只负责把 fh 命令挂进 DSH 工具目录（ctx.effect 规范：热卸载自动清理）。
 *
 * 首轮工具面由 card-forge preset 控制（首轮 shell+editor，晋升后全目录），
 * 因此本插件不做二次锚定，避免与 preset 的 system-prompt/assemble 打架。
 */
import { execFile } from 'node:child_process'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = '@dsh-external/dsh-fh-tools'
export const inject = ['tools']

const MAX_BUFFER = 16 * 1024 * 1024
const TIMEOUT_MS = 180_000

interface ExecResult {
  code: number
  text: string
}

function exec(cmd: string, args: string[], cwd: string, timeoutMs: number): Promise<ExecResult> {
  return new Promise((resolve) => {
    execFile(
      cmd,
      args,
      { cwd: cwd || process.cwd(), timeout: timeoutMs, windowsHide: true, maxBuffer: MAX_BUFFER },
      (error, stdout, stderr) => {
        if (error) {
          const code = (error as unknown as { code?: number }).code ?? -1
          resolve({ code, text: `${String(stdout || '')}${String(stderr || '')}${String(error.message || '')}` })
          return
        }
        resolve({ code: 0, text: `${String(stdout || '')}${String(stderr || '')}` })
      },
    )
  })
}

/** 优先 `fh`；未安装时回退 `python -m furrhaven.cli`（同语义）。 */
async function runFh(args: string[], cwd: string): Promise<string> {
  let result = await exec('fh', args, cwd, TIMEOUT_MS)
  if (result.code === -2 || /ENOENT/i.test(result.text)) { // fh 不在 PATH
    result = await exec('python', ['-m', 'furrhaven.cli', ...args], cwd, TIMEOUT_MS)
  }
  const head = result.text.trim()
  const marker = result.code === 0 ? 'OK' : `EXIT ${result.code}`
  return `[fh ${marker}]\n${head.slice(0, 12000)}`
}

/** 把可选参数统一收成 argv 片段。 */
function argvOf(args: Record<string, unknown>, key: string, flag: string): string[] {
  const v = args[key]
  if (v === undefined || v === null || v === '') return []
  return [flag, String(v)]
}

export function apply(ctx: { effect: (fn: () => void, label?: string) => void; tools: { register: (tool: ReturnType<typeof defineTool>, label?: string) => void } }): void {
  const reg = (tool: ReturnType<typeof defineTool>, label: string) => {
    ctx.effect(() => ctx.tools.register(tool), label)
  }

  reg(defineTool({
    name: 'fh_new',
    description: '新建角色卡：模块化目录（默认）或 --full 完整卡单文件（卡体+世界书+组件+正则）。返回生成路径。',
    parameters: {
      slug: { type: 'string', required: true, description: '卡目录名（slug，如 huiye）' },
      type: { type: 'string', description: '卡型 character / character.activity / simulator / bigworld / custom（默认 character）' },
      full: { type: 'boolean', description: 'true=完整卡单文件模式（一把梭写法）' },
      cwd: { type: 'string', description: '项目根目录（fh.config.yaml 所在；默认进程 cwd）' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { slug: string; type?: string; full?: boolean; cwd?: string }) {
      const argv = ['new', args.slug, ...(args.type ? ['--type', args.type] : []), ...(args.full ? ['--full'] : [])]
      return runFh(argv, args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_new')

  reg(defineTool({
    name: 'fh_build',
    description: '构建导出：IR → FD JSON / FC 8目录包 / FB md / 酒馆 V2+V3 PNG / RisuAI / 类脑。写后必须跑。',
    parameters: {
      card: { type: 'string', description: '只构建指定 slug（缺省全部）' },
      platform: { type: 'string', description: '逗号分隔 fd/fc/fb/st/risu/leinao，或 all（缺省 fh.config.yaml）' },
      cwd: { type: 'string', description: '项目根目录' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { card?: string; platform?: string; cwd?: string }) {
      return runFh(['build', ...argvOf(args, 'card', '--card'), ...argvOf(args, 'platform', '--platform')], args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_build')

  reg(defineTool({
    name: 'fh_check',
    description: '门禁聚合：IR/组件五坑/世界书/正则/字节/残留/漂移检查。退出码 0=可交付，先修复再汇报。',
    parameters: {
      card: { type: 'string', description: '只检查指定 slug' },
      platform: { type: 'string', description: '只跑指定平台检查（fd/fc/fb，逗号分隔）' },
      rule: { type: 'string', description: '只看指定规则 ID（如 COMP-ID / CONTENT-RESIDUE）' },
      selftest: { type: 'boolean', description: '引擎自检' },
      cwd: { type: 'string', description: '项目根目录' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { card?: string; platform?: string; rule?: string; selftest?: boolean; cwd?: string }) {
      const argv = ['check',
        ...argvOf(args, 'card', '--card'), ...argvOf(args, 'platform', '--platform'),
        ...argvOf(args, 'rule', '--rule'), ...(args.selftest ? ['--selftest'] : [])]
      return runFh(argv, args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_check')

  reg(defineTool({
    name: 'fh_audit',
    description: '全项目审计：每卡字节余量、世界书/组件/正则/快捷回复盘点。',
    parameters: {
      cwd: { type: 'string', description: '项目根目录' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { cwd?: string }) {
      return runFh(['audit'], args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_audit')

  reg(defineTool({
    name: 'fh_wb_sim',
    description: '世界书触发模拟器：样例玩家消息 → 命中条目/注入顺序/token 占用（写作时即时反馈）。',
    parameters: {
      card: { type: 'string', required: true, description: '卡 slug' },
      text: { type: 'string', required: true, description: '样例玩家消息' },
      cwd: { type: 'string', description: '项目根目录' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { card: string; text: string; cwd?: string }) {
      return runFh(['wb', 'sim', '--card', args.card, '--text', args.text], args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_wb_sim')

  reg(defineTool({
    name: 'fh_comp_check',
    description: '组件约束检查器：FD 五坑（$变量$位置/id=name/html禁标签/source 20k/槽位对齐）+ 拉长四禁 + node --check。',
    parameters: {
      name: { type: 'string', description: '只查组件库中指定组件名（缺省查卡引用的全部）' },
      card: { type: 'string', description: '只查指定卡引用的组件' },
      cwd: { type: 'string', description: '项目根目录' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { name?: string; card?: string; cwd?: string }) {
      return runFh(['comp', 'check', ...argvOf(args, 'name', '--name'), ...argvOf(args, 'card', '--card')], args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_comp_check')

  reg(defineTool({
    name: 'fh_regex_test',
    description: '正则测试台：样例 AI 回复按序应用规则 → 渲染预览 + 每条命中（改正则立即验收）。',
    parameters: {
      text: { type: 'string', required: true, description: '样例 AI 回复文本' },
      card: { type: 'string', description: '用指定卡的正则规则（缺省 regex/regex.yaml）' },
      file: { type: 'string', description: '规则 YAML 路径' },
      cwd: { type: 'string', description: '项目根目录' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { text: string; card?: string; file?: string; cwd?: string }) {
      return runFh(['regex', 'test', '--text', args.text,
        ...argvOf(args, 'card', '--card'), ...argvOf(args, 'file', '--file')], args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_regex_test')

  reg(defineTool({
    name: 'fh_vision',
    description: '识图模式：视觉模型读立绘/参考图/平台截图 → 外貌描述或 UI 排查线索（--card 写入 assets/）。',
    parameters: {
      image: { type: 'string', required: true, description: '图片路径（png/jpg/webp）' },
      card: { type: 'string', description: '卡 slug：结果写入 assets/<图>_appearance.md' },
      mode: { type: 'string', description: 'character=外貌描述（默认）；ui=平台截图组件排查' },
      cwd: { type: 'string', description: '项目根目录' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { image: string; card?: string; mode?: string; cwd?: string }) {
      return runFh(['vision', args.image,
        ...argvOf(args, 'card', '--card'), ...argvOf(args, 'mode', '--mode')], args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_vision')

  reg(defineTool({
    name: 'fh_play',
    description: '扮演模式试玩：构建后按卡体+世界书扮演一轮（--say 单轮；交互式请直接用终端 fh play）。',
    parameters: {
      slug: { type: 'string', required: true, description: '卡 slug' },
      say: { type: 'string', description: '单轮测试消息' },
      cwd: { type: 'string', description: '项目根目录' },
    },
    output: { schema: { type: 'string' }, render: (_a: unknown, v: unknown) => [{ type: 'text', text: String(v) }] },
    async execute(args: { slug: string; say?: string; cwd?: string }) {
      if (!args.say) return '[fh_play] 交互式扮演请在终端运行 `fh play <slug>`；本工具用 --say 做单轮测试'
      return runFh(['play', args.slug, '--say', args.say], args.cwd || '')
    },
  }), '@dsh-external/dsh-fh-tools: fh_play')
}

