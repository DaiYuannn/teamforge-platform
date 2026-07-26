import { describe, expect, it } from 'vitest'
import {
  hasSavedFilterModule,
  mergeSavedFilterModule,
  normalizeProjectSavedFilters,
  normalizeTaskSavedFilters,
} from '@/utils/savedFilters'

describe('normalizeProjectSavedFilters', () => {
  it('仅恢复项目页支持的合法字段', () => {
    expect(normalizeProjectSavedFilters({
      search: '  智能车  ',
      status: 'active',
      leader: 42,
      start_date: '2024-02-29',
      end_date: '2024-12-31',
      ordering: '-created_at',
      scope: 'team',
      page: 9,
      unknown: 'drop-me',
    })).toEqual({
      search: '智能车',
      status: 'active',
      leader: '42',
      start_date: '2024-02-29',
      end_date: '2024-12-31',
      ordering: '-created_at',
      scope: 'team',
    })
  })

  it('忽略非法枚举、日期、类型和过长文本', () => {
    expect(normalizeProjectSavedFilters({
      search: 'x'.repeat(201),
      status: 'archived',
      leader: [],
      start_date: '2023-02-29',
      end_date: '2024-13-01',
      ordering: 'name',
      scope: 'all',
    })).toEqual({})
    expect(normalizeProjectSavedFilters([])).toEqual({})
  })
})

describe('normalizeTaskSavedFilters', () => {
  it('恢复合法任务筛选并规范数字 ID', () => {
    expect(normalizeTaskSavedFilters({
      search: '  验收  ',
      project: '12',
      status: 'pending_review',
      priority: 'urgent',
      assignee: 7,
      scope: 'mine',
      page_size: 100,
    })).toEqual({
      search: '验收',
      project: 12,
      status: 'pending_review',
      priority: 'urgent',
      assignee: 7,
      scope: 'mine',
    })
  })

  it('忽略无效 ID、枚举和容器值', () => {
    expect(normalizeTaskSavedFilters({
      project: 0,
      assignee: 1.5,
      status: 'finished',
      priority: 'critical',
      scope: ['mine'],
    })).toEqual({})
    expect(normalizeTaskSavedFilters('bad-data')).toEqual({})
  })
})

describe('mergeSavedFilterModule', () => {
  it('新增模块时保留其他模块且不修改原对象', () => {
    const current = {
      tasks: { status: 'todo' },
      competitions: { level: 'school' },
    }

    const result = mergeSavedFilterModule(
      current,
      'projects',
      { status: 'active', scope: 'team' },
    )

    expect(result).toEqual({
      tasks: { status: 'todo' },
      competitions: { level: 'school' },
      projects: { status: 'active', scope: 'team' },
    })
    expect(current).toEqual({
      tasks: { status: 'todo' },
      competitions: { level: 'school' },
    })
    expect(result.tasks).not.toBe(current.tasks)
  })

  it('清除时只移除目标模块', () => {
    expect(mergeSavedFilterModule({
      projects: { status: 'active' },
      tasks: { priority: 'high' },
    }, 'projects', null)).toEqual({
      tasks: { priority: 'high' },
    })
  })

  it('即使目标模块损坏也可识别并清除', () => {
    expect(hasSavedFilterModule({ projects: 'bad-data' }, 'projects')).toBe(true)
    expect(hasSavedFilterModule({}, 'projects')).toBe(false)
  })
})
