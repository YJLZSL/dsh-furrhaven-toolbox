/**
 * card-forge-bootstrap: 写卡域任务路由（react/spec/weak）。
 *
 * 机制对齐 router-standard：
 * - 读取会话首条真实用户消息分类任务；
 * - 首个请求注入对应 persona + 首轮核心工具面（shell 动态补）；
 * - 首次持久 tool/call 后开放完整目录、不再干预；
 * - 模式从持久会话事件推导，resume/reload 安全。
 *
 * 风神兼容四守则：独立 preset 不改 router-standard 本体；service 行 isolate
 * realm 不碰 host-plane；不注册 dev_router_* 冲突名；持久会话事件推导 + 零外部 import。
 */
import {
  applyPersona, bandOf, coreFor, extractText, personaFor, sessionMode, clamp01,
} from './card-forge-core.mjs'

export const name = 'card-forge-bootstrap'

export const inject = ['systemPrompt', 'tools', 'llm']

export function apply(ctx, config) {
  const agents = new Map()
  const firstUserText = new Map()
  const routerMode = config.routerMode === 'spec' ? 'spec' : 'standard'
  const RL_PERSONA = 'You are a role-card authoring expert. Work step by step: produce, verify with fh check, fix until exit code 0.'

  ctx.on('system-prompt/assemble', async (_assembly, context, next) => {
    const assembled = await next()
    const agent = context.agent
    if (agent === undefined) return assembled
    const session = agent.session
    agents.set(session.id, agent)

    const mode = firstUserText.get(session.id) ?? sessionMode(session)
    const modelId = agent.options?.model
    const planSection = (assembled.sections || []).find((s) => /plan/i.test(s.name))

    let sections
    let core
    if (routerMode === 'standard') {
      // RL 接口还原：首轮只有一句话 persona + shell/editor
      sections = planSection
        ? [planSection, { name: 'card-forge-persona', text: RL_PERSONA, order: 0 }]
        : [{ name: 'card-forge-persona', text: RL_PERSONA, order: 0 }]
      core = new Set(['str_replace_editor'])
    } else {
      sections = applyPersona(assembled.sections, personaFor(mode, modelId))
      core = new Set(coreFor(mode))
    }

    if (session.events.some((event) => event.type === 'tool/call')) {
      return { ...assembled, sections, contexts: [] } // 晋升：完整目录
    }

    const available = new Set(assembled.tools.map((tool) => tool.name))
    const shell = available.has('pwsh') ? 'pwsh' : available.has('bash') ? 'bash' : null
    if (shell === null) {
      throw new Error(`${name}: no platform shell in catalog`)
    }
    core.add(shell)
    return {
      ...assembled,
      sections,
      contexts: [],
      tools: assembled.tools.filter((tool) => core.has(tool.name)),
    }
  })

  const GUIDE_WEAK =
    '\nCard-Forge: classify this card task (write or fix) now — write: direct production with fh new/build; fix: inspect-first with fh check. Finish with the gate at exit code 0.'
  ctx.on('session/event', (session, event) => {
    if (event.type !== 'user/message') return
    const data = event.data ?? {}
    if (data.source?.kind !== 'user') return
    const text = extractText(data)
    if (!firstUserText.has(session.id) && text.trim()) {
      firstUserText.set(session.id, text.trim())
    }
    const agent = ctx.get('agent')
    const target = agent !== undefined && agent.session === session
      ? agent
      : [...agents.values()].find((a) => a.session === session)
    if (target === undefined || target.inbox === undefined) return
    if (bandOf(firstUserText.get(session.id) ?? sessionMode(session)) !== 'weak') return
    if (!text.trim()) return
    try {
      target.inbox.append('next-step', {
        id: `card-forge-guide-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role: 'user',
        source: { kind: 'plugin', plugin: 'card-forge-bootstrap' },
        content: [{ type: 'text', text: GUIDE_WEAK }],
      })
    } catch { /* duplicate/ordering races: skip */ }
  })

  ctx.effect(() => {})
  void clamp01
}
