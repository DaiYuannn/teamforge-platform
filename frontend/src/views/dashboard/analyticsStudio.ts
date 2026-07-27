import type { WeeklyReport, WeeklyTask } from '@/api/analytics'

function money(value: number): string {
  return Number(value || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function buildWeeklyReportMarkdown(report: WeeklyReport, riskTasks: WeeklyTask[]): string {
  const period = `${report.summary.report_period_start.slice(0, 10)} 至 ${report.summary.report_period_end.slice(0, 10)}`
  const lines = [
    `# 团队智能周报（${period}）`,
    '',
    report.narrative,
    '',
    '## 核心指标',
    '',
    `- 完成任务：${report.summary.tasks_completed}`,
    `- 新增任务：${report.summary.tasks_new}`,
    `- 待办任务：${report.summary.tasks_pending}`,
    `- 逾期任务：${report.summary.tasks_overdue}`,
    `- 活跃项目：${report.summary.active_projects}`,
    `- 本期支出：¥${money(report.summary.weekly_expense)}`,
    '',
    '## 项目进展',
    '',
    ...(report.project_progress.length
      ? report.project_progress.map((item) =>
        `- ${item.project_name}（${item.current_stage_display}）：完成 ${item.tasks_completed_this_week} 项，新增 ${item.tasks_new_this_week} 项`
      )
      : ['- 暂无']),
    '',
    '## 风险任务',
    '',
    ...(riskTasks.length
      ? riskTasks.map((item) =>
        `- ${item.title} · ${item.project_name || '未分配项目'} · ${item.deadline ? item.deadline.slice(0, 10) : '无截止时间'}`
      )
      : ['- 暂无']),
    '',
    '## 团队动态',
    '',
    ...(report.team_activity.length
      ? report.team_activity.map((item) =>
        `- ${String(item.user_name || '团队成员')}：${String(item.content || item.contribution_type || '更新了团队记录')}`
      )
      : ['- 暂无']),
    '',
  ]
  return lines.join('\n')
}
