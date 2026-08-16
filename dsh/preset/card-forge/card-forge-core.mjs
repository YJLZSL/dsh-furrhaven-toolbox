/**
 * card-forge-core: 写卡域任务分类与 persona（零依赖，可 node --test）。
 *
 * 对齐 router-standard 的实测行为带：
 *   react [0.5,1] → 动手优先（新建卡/写开场白/写组件/写正则/批量生成）
 *   spec  [0,0.15] → 计划优先（修卡/排查/审计/超限压缩/平台报错）
 *   weak           → 模型自路由（模糊/混合任务）
 */
export const MODE_SPEC = 0
export const MODE_REACT = 1
export const MODE_WEAK = 'weak'

const REACT_RE = /(新建|新卡|创建|写一?[张个]|生成|从零|做一?[张个]|开场白|组件|正则|世界书|批量|扩写|build|create|generate|scaffold|draft)/i
const SPEC_RE = /(修|修复|排查|报错|出错|超限|压缩|审计|检查|审查|优化|门禁|漂移|review|fix|debug|audit|lint|check)/i

const FORGE_PERSONA_REACT =
  'You are a hands-on role-card authoring engineer. Write cards directly: use fh new/fh build/fh check, '
  + 'produce usable card content fast, verify with the gate (exit code 0), and do not build ceremony the user did not ask for.'

const FORGE_PERSONA_SPEC =
  'You are a role-card maintenance engineer. Inspect first, then fix: locate the failing rule with fh check, '
  + 'read the whole section before rewriting (whole-section rewrite discipline), apply one complete replacement, then re-run the gate.'

const FORGE_PERSONA_WEAK_PRO =
  'You are a role-card authoring assistant. Before acting, decide the task type (write or fix) and adopt the matching style: '
  + 'write → hands-on production; fix → inspect-and-plan. Always finish with fh check exit code 0.'

const FORGE_PERSONA_WEAK_FLASH =
  'You are a role-card authoring assistant. Classify the task (write or fix) before acting; write → direct production, '
  + 'fix → inspect-first. Review what you already did and continue; do not repeat completed steps. Think deeply first, then produce.'

export function clamp01(v) {
  return Math.min(1, Math.max(0, Number(v) || 0))
}

export function bandOf(mode) {
  if (mode === MODE_WEAK) return 'weak'
  const m = clamp01(mode)
  if (m < 0.2) return 'spec'
  if (m < 0.5) return 'transition'
  return 'react'
}

export function bandFor(mode) {
  const b = bandOf(mode)
  return b === 'transition' ? 'mixed' : b
}

export function isFlashModel(modelId) {
  return typeof modelId === 'string' && /flash/i.test(modelId)
}

export function personaFor(mode, modelId) {
  switch (bandOf(mode)) {
    case 'spec': return FORGE_PERSONA_SPEC
    case 'weak': return isFlashModel(modelId) ? FORGE_PERSONA_WEAK_FLASH : FORGE_PERSONA_WEAK_PRO
    default: return FORGE_PERSONA_REACT
  }
}

export function coreFor(mode) {
  switch (bandOf(mode)) {
    case 'spec': return ['read', 'edit', 'glob', 'grep']
    case 'weak': return ['str_replace_editor']
    default: return ['read', 'write', 'edit']
  }
}

function countHits(regex, text) {
  const matches = String(text || '').match(new RegExp(regex.source, regex.flags.includes('g') ? regex.flags : regex.flags + 'g'))
  return matches ? matches.length : 0
}

export function classifyTask(text) {
  const react = countHits(REACT_RE, text)
  const spec = countHits(SPEC_RE, text)
  if (react > spec) return MODE_REACT
  if (spec > react) return MODE_SPEC
  return MODE_WEAK
}

export function extractText(data) {
  if (!data) return ''
  const payload = data && typeof data.message === 'object' && data.message !== null ? data.message : data
  const content = Array.isArray(payload.content) ? payload.content : []
  return content.map((c) => (typeof c === 'string' ? c : (c.text ?? ''))).join(' ')
}

export function sessionMode(session) {
  const events = session?.events ?? []
  const userMsg = events.find((e) => e.type === 'user/message')
  return classifyTask(extractText(userMsg?.data))
}

export function applyPersona(sections, personaText) {
  const rest = (sections || []).filter(
    (section) => section.name !== 'persona' && !/persona/i.test(section.name),
  )
  return [...rest, { name: 'card-forge-persona', text: personaText, order: 0 }]
}
