import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(
  resolve(process.cwd(), 'src/views/members/MemberSkillsView.vue'),
  'utf8',
)
const navigationSource = readFileSync(
  resolve(process.cwd(), 'src/config/navigation.ts'),
  'utf8',
)
const routerSource = readFileSync(
  resolve(process.cwd(), 'src/router/index.ts'),
  'utf8',
)

describe('member skills workspace contract', () => {
  it('keeps personal skill maintenance and adds matrix plus recommendation tabs', () => {
    expect(source).toContain('label="我的技能"')
    expect(source).toContain('label="团队技能矩阵"')
    expect(source).toContain('label="组队 / 任务推荐"')
    expect(source).toContain('姓名、拼音或首字母')
    expect(source).toContain('学校片段')
    expect(source).toContain('专业片段')
    expect(source).toContain('技能名称片段')
  })

  it('requires event-entry context and explains recommendation evidence', () => {
    expect(source).toContain('选择比赛届次')
    expect(source).toContain('选择参赛项目/队伍')
    expect(source).toContain('选择任务所需技能')
    expect(source).toContain('技能覆盖 70% + 熟练度 30%')
    expect(source).toContain('已匹配')
    expect(source).toContain('缺失或未达标')
    expect(source).toContain('系统不会从总团队中擅自加入不在该参赛条目的人')
  })

  it('names the route and navigation entry after the expanded workspace', () => {
    expect(navigationSource).toContain(
      "{ path: '/members/skills', title: '技能与组队'",
    )
    expect(routerSource).toContain(
      "meta: { title: '技能与组队', requiresAuth: true }",
    )
  })
})
