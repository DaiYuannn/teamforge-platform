import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(
  resolve(process.cwd(), 'src/views/projects/ProjectListView.vue'),
  'utf8',
)

describe('project team perspective', () => {
  it('offers four explicit views with the small-team view first', () => {
    const labels = ['我的小团队', '我管理的', '我参与的', '全部可见']
    for (const label of labels) expect(source).toContain(`label: '${label}'`)
    expect(source.indexOf("value: 'my_teams'")).toBeLessThan(
      source.indexOf("value: 'visible'"),
    )
    expect(source).toContain("accountDefaultScope: ProjectViewScope")
    expect(source).toContain(": userStore.preferences?.default_scope === 'team'")
    expect(source).toContain(": 'my_teams'")
  })

  it('names every responsibility level instead of using one generic leader', () => {
    for (const label of [
      '项目牵头 / 共同负责人',
      '所属小团队 / 团队负责人',
      '比赛 / 实际负责人',
      '这个项目里，每个人正在做什么',
    ]) {
      expect(source).toContain(label)
    }
    for (const field of [
      'co_leader_names',
      'team_details',
      'competition_summaries',
      'member_work_summary',
      'active_task_titles',
      'competition_responsibilities',
    ]) {
      expect(source).toContain(field)
    }
  })

  it('shows an explicit compatibility message for teachers without team links', () => {
    expect(source).toContain('applyUnavailableTeamScopeFallback')
    expect(source).toContain('当前教师账号尚未关联指导团队')
    expect(source).toContain("queryParams.scope = 'visible'")
  })

  it('puts recorded spending before the calculated available amount', () => {
    expect(source).toContain('支出 / 计算可用')
    expect(source.indexOf('row.finance_spending')).toBeLessThan(
      source.indexOf('row.finance_available'),
    )
    expect(source).toContain('支出为全部已记录金额')
    expect(source).toContain('计算可用＝预算控制基准－已完成及流程中支出')
  })
})
