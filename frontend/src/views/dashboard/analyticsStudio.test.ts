import { describe, expect, it } from 'vitest'
import type { WeeklyReport, WeeklyTask } from '@/api/analytics'
import { buildWeeklyReportMarkdown } from './analyticsStudio'

const report: WeeklyReport = {
  summary: {
    report_period_start: '2026-07-20T09:00:00+08:00',
    report_period_end: '2026-07-26T18:00:00+08:00',
    weeks: 1,
    tasks_completed: 4,
    tasks_new: 3,
    tasks_pending: 2,
    tasks_overdue: 1,
    tasks_upcoming_deadline: 1,
    active_projects: 1,
    stage_changes: 2,
    weekly_expense: 1200,
    team_activities: 1,
  },
  narrative: '本周完成核心交付。',
  completed_tasks: [],
  new_tasks: [],
  pending_tasks: [],
  overdue_tasks: [],
  upcoming_deadline_tasks: [],
  project_progress: [{
    project_id: 7,
    project_name: '星火计划',
    project_code: 'P-007',
    current_stage: 8,
    current_stage_display: '答辩准备',
    tasks_completed_this_week: 4,
    tasks_new_this_week: 3,
  }],
  stage_changes: [],
  upcoming_competitions: [],
  team_activity: [{ user_name: '陈同学', content: '完成材料复核' }],
}

const riskTask: WeeklyTask = {
  task_id: 9,
  title: '提交答辩材料',
  status: 'overdue',
  status_display: '已逾期',
  project_name: '星火计划',
  deadline: '2026-07-25T18:00:00+08:00',
}

describe('weekly report export', () => {
  it('includes the period, key metrics, project progress, risks, and activity', () => {
    const markdown = buildWeeklyReportMarkdown(report, [riskTask])

    expect(markdown).toContain('# 团队智能周报（2026-07-20 至 2026-07-26）')
    expect(markdown).toContain('- 本期支出：¥1,200.00')
    expect(markdown).toContain('星火计划（答辩准备）：完成 4 项，新增 3 项')
    expect(markdown).toContain('提交答辩材料 · 星火计划 · 2026-07-25')
    expect(markdown).toContain('陈同学：完成材料复核')
  })
})
