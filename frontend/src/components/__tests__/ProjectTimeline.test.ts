import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'


const componentSource = readFileSync(
  resolve(process.cwd(), 'src/components/ProjectTimeline.vue'),
  'utf8',
)

const expectedEventTypes = {
  stage_change: ['阶段变更', 'stage'],
  task_created: ['任务创建', 'task'],
  task_completed: ['任务完成', 'task'],
  competition_register: ['比赛报名截止', 'competition'],
  competition_material: ['比赛材料截止', 'competition'],
  competition_review: ['比赛网评', 'competition'],
  competition_defense: ['比赛答辩', 'competition'],
  competition_result: ['比赛结果', 'competition'],
  expense: ['经费支出', 'expense'],
  file_upload: ['文件上传', 'file'],
  ip_submit: ['知识产权提交', 'ip'],
  ip_accepted: ['知识产权受理', 'ip'],
  ip_authorized: ['知识产权授权', 'ip'],
  ip_return: ['知识产权退回', 'ip'],
  contribution: ['贡献', 'contribution'],
} as const

describe('ProjectTimeline event contract', () => {
  it('maps every backend event type to a Chinese label and category', () => {
    for (const [type, [label, category]] of Object.entries(expectedEventTypes)) {
      const entryPattern = new RegExp(
        `\\b${type}: \\{ label: '${label}', category: '${category}' \\}`,
      )
      expect(componentSource).toMatch(entryPattern)
    }

    expect(componentSource).toContain(
      "return EVENT_TYPE_MAP[type]?.label || '其他事件'",
    )
    expect(componentSource).toContain(
      'EVENT_CATEGORY_MAP[category].color',
    )
  })

  it('shows coarse categories and expands them into exact API types', () => {
    const categoryMapStart = componentSource.indexOf('const EVENT_CATEGORY_MAP')
    const categoryMapEnd = componentSource.indexOf('// API 返回的 15 种精确事件类型')
    const categoryMapSource = componentSource.slice(categoryMapStart, categoryMapEnd)

    expect(categoryMapStart).toBeGreaterThan(-1)
    expect(categoryMapEnd).toBeGreaterThan(categoryMapStart)
    for (const type of Object.keys(expectedEventTypes)) {
      expect(categoryMapSource).toContain(`'${type}'`)
    }

    expect(componentSource).toContain('v-model="selectedCategories"')
    expect(componentSource).toContain('v-for="(meta, key) in EVENT_CATEGORY_MAP"')
    expect(componentSource).toContain(
      '(category) => EVENT_CATEGORY_MAP[category].types',
    )
    expect(componentSource).toContain("params.event_type = eventTypes.join(',')")
  })
})
