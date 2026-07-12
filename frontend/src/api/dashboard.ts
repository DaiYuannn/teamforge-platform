import { get } from './request'
import type { DashboardData } from '@/types'

/** 获取首页驾驶舱数据 */
export function getDashboardData(): Promise<DashboardData> {
  return get<DashboardData>('/dashboard/')
}

// ============================================
// P1: 时间线/矩阵/漏斗/日历/Gantt 扩展接口
// ============================================

/** 时间线事件 */
export interface TimelineEvent {
  id: string
  type: string
  title: string
  description: string
  timestamp: string | null
  date: string | null
  project_id: number | null
  project_name: string
  project_code: string
  operator_name: string
  metadata: Record<string, any>
}

/** 时间线查询参数 */
export interface TimelineQueryParams {
  project_id?: number
  start_date?: string
  end_date?: string
  event_type?: string
  limit?: number
}

/** 获取统一时间线事件 */
export function getTimelineEvents(params?: TimelineQueryParams): Promise<{ total: number; events: TimelineEvent[] }> {
  return get('/dashboard/timeline/', params)
}

/** 比赛矩阵单元格 */
export interface CompetitionMatrixCell {
  level_display: string
  total: number
  awarded: number
  promoted: number
}

/** 比赛矩阵行 */
export interface CompetitionMatrixRow {
  project_id: number
  project_name: string
  project_code: string
  current_stage: number
  current_stage_display: string
  status: string
  cells: Record<string, CompetitionMatrixCell>
}

/** 比赛矩阵数据 */
export interface CompetitionMatrixData {
  levels: { key: string; name: string }[]
  matrix: CompetitionMatrixRow[]
  level_totals: Record<string, { total: number; awarded: number; promoted: number }>
}

/** 获取比赛矩阵 */
export function getCompetitionMatrix(): Promise<CompetitionMatrixData> {
  return get('/dashboard/competition-matrix/')
}

/** 晋级漏斗项 */
export interface FunnelItem {
  level: string
  level_display: string
  total: number
  promoted: number
  awarded: number
  ongoing: number
  completed: number
  promotion_rate: number
  award_rate: number
}

/** 获取比赛晋级漏斗 */
export function getCompetitionFunnel(): Promise<{ funnel: FunnelItem[]; total_competitions: number; total_promoted: number; total_awarded: number }> {
  return get('/dashboard/competition-funnel/')
}

/** 日历事件项 */
export interface CalendarDayItem {
  date: string
  count: number
  events: { type: string; label: string; level?: string; level_display?: string }[]
}

/** 获取项目日历数据 */
export function getProjectCalendar(params?: { year?: number; project_id?: number }): Promise<{ year: number; calendar: CalendarDayItem[] }> {
  return get('/dashboard/calendar/', params)
}

/** Gantt 阶段项 */
export interface GanttStage {
  stage: number
  stage_display: string
  date: string | null
  operator: string
}

/** Gantt 里程碑项 */
export interface GanttMilestone {
  date: string
  label: string
  level: string
  level_display: string
  is_awarded: boolean
  award_level: string
}

/** Gantt 项目项 */
export interface GanttProject {
  project_id: number
  project_name: string
  project_code: string
  start_date: string | null
  planned_end_date: string | null
  actual_end_date: string | null
  current_stage: number
  current_stage_display: string
  status: string
  status_display: string
  priority: string
  leader_name: string
  stages: GanttStage[]
  milestones: GanttMilestone[]
}

/** 获取 Gantt 历程条数据 */
export function getProjectGantt(params?: { project_id?: number; status?: string }): Promise<{ total: number; projects: GanttProject[] }> {
  return get('/dashboard/gantt/')
}

// ============================================
// P2: 公共展示主页
// ============================================

/** 公共展示统计数据 */
export interface PublicPortalStats {
  total_projects: number
  awarded_projects: number
  closed_projects: number
  total_competitions: number
  awarded_competitions: number
  total_ip: number
}

/** 公共展示获奖项目 */
export interface PublicAwardedProject {
  project_id: number
  project_name: string
  project_code: string
  intro: string
  leader_name: string
  start_date: string
  awards: { competition_name: string; level: string; level_display: string; award_level: string }[]
}

/** 公共展示知识产权成果 */
export interface PublicIPResult {
  ip_id: number
  title: string
  ip_type: string
  ip_type_display: string
  application_code: string
  authorized_date: string
  intro: string
}

/** 公共展示核心成员 */
export interface PublicCoreMember {
  user_id: number
  name: string
  global_role: string
  global_role_display: string
  grade: string
  major: string
  project_count: number
}

/** 公共展示主页数据 */
export interface PublicPortalData {
  stats: PublicPortalStats
  awarded_projects: PublicAwardedProject[]
  ip_results: PublicIPResult[]
  core_members: PublicCoreMember[]
}

/** 获取公共展示主页数据(无需认证) */
export function getPublicPortal(): Promise<PublicPortalData> {
  return get('/dashboard/public-portal/')
}
