import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  bandFor, classifyTask, coreFor, extractText, personaFor, sessionMode, clamp01, MODE_REACT, MODE_SPEC, MODE_WEAK,
} from '../card-forge-core.mjs'

test('写卡任务分类：新建/生成 → react', () => {
  assert.equal(classifyTask('新建一张现代题材角色卡，写开场白'), MODE_REACT)
  assert.equal(classifyTask('批量生成世界书条目和组件'), MODE_REACT)
})

test('写卡任务分类：修卡/审计 → spec', () => {
  assert.equal(classifyTask('修复 FD 组件导入报错'), MODE_SPEC)
  assert.equal(classifyTask('审计字节超限并压缩'), MODE_SPEC)
})

test('模糊任务 → weak（模型自路由）', () => {
  assert.equal(classifyTask('帮我看看这张卡'), MODE_WEAK)
})

test('band 映射与核心工具面', () => {
  assert.equal(bandFor(0), 'spec')
  assert.equal(bandFor(1), 'react')
  assert.equal(bandFor(MODE_WEAK), 'weak')
  assert.deepEqual(coreFor(0), ['read', 'edit', 'glob', 'grep'])
  assert.deepEqual(coreFor(1), ['read', 'write', 'edit'])
  assert.deepEqual(coreFor(MODE_WEAK), ['str_replace_editor'])
})

test('sessionMode 从持久会话事件推导（resume 安全）', () => {
  const session = { events: [{ type: 'user/message', data: { source: { kind: 'user' }, content: [{ type: 'text', text: '修复平台报错' }] } }] }
  assert.equal(sessionMode(session), MODE_SPEC)
})

test('extractText 防御性解包', () => {
  assert.equal(extractText({ content: [{ type: 'text', text: 'hello' }] }), 'hello')
  assert.equal(extractText({ message: { content: ['hi'] } }), 'hi')
  assert.equal(extractText(undefined), '')
})

test('persona 分型', () => {
  assert.match(personaFor(MODE_REACT, 'v4-pro'), /hands-on role-card/i)
  assert.match(personaFor(MODE_WEAK, 'v4-flash'), /classify/i)
  assert.equal(clamp01(5), 1)
  assert.equal(clamp01(-1), 0)
})
