import { get, post, patch, del } from './request'
import type {
  Member,
  MemberUpdateParams,
  PaginatedResponse,
  PaginationParams,
  TeamRole,
} from '@/types'

/** 成员查询参数 */
export interface MemberQueryParams extends PaginationParams {
  grade?: string
  major?: string
  school?: string
  team?: number
  team_role?: TeamRole
  project?: number
  membership_status?: string
  is_active?: boolean
}

/**
 * 自由文本仅做首尾空白清理，保持用户原始大小写并交由后端进行片段匹配。
 * 空筛选不进入查询字符串，避免被解释成严格的空值条件。
 */
export function normalizeMemberQueryParams(
  params: MemberQueryParams,
): MemberQueryParams {
  const normalized: MemberQueryParams = {}
  const target = normalized as Record<string, unknown>

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (typeof value === 'string') {
      const trimmed = value.trim()
      if (trimmed) {
        target[key] = trimmed
      }
      return
    }
    target[key] = value
  })

  return normalized
}

/** 获取成员列表 */
export function getMembers(params: MemberQueryParams): Promise<PaginatedResponse<Member>> {
  return get<PaginatedResponse<Member>>(
    '/members/',
    normalizeMemberQueryParams(params),
  )
}

/** 获取成员详情 */
export function getMember(id: number): Promise<Member> {
  return get<Member>(`/members/${id}/`)
}

/** 更新成员信息 */
export function updateMember(id: number, data: MemberUpdateParams): Promise<Member> {
  return patch<Member>(`/members/${id}/`, data)
}

// ============================================
// 技能标签 API
// ============================================

/** 获取技能标签列表 */
export const getSkillTags = () => get('/members/skill-tags/')

/** 创建技能标签 */
export const createSkillTag = (data: any) => post('/members/skill-tags/', data)

// ============================================
// 成员技能 API
// ============================================

/** 获取我的技能列表 */
export const getMySkills = () => get('/members/member-skills/')

/** 添加成员技能 */
export const addMemberSkill = (data: any) => post('/members/member-skills/', data)

/** 更新成员技能 */
export const updateMemberSkill = (id: number, data: any) => patch(`/members/member-skills/${id}/`, data)

/** 删除成员技能 */
export const deleteMemberSkill = (id: number) => del(`/members/member-skills/${id}/`)

/** 按用户获取成员技能 */
export const getMemberSkillsByUser = (userId: number) => get('/members/member-skills/by_user/', { user_id: userId })

// ============================================
// 可投入安排 API
// ============================================

/** 获取我的可投入安排列表 */
export const getMySchedules = () => get('/members/flexible-schedules/')

/** 创建可投入安排 */
export const createSchedule = (data: any) => post('/members/flexible-schedules/', data)

/** 修改可投入安排 */
export const updateSchedule = (id: number, data: any) =>
  patch(`/members/flexible-schedules/${id}/`, data)

/** 获取当前半月周期信息 */
export const getCurrentPeriod = () => get('/members/flexible-schedules/current_period/')

/** 获取所有成员最新可投入安排 */
export const getAllLatestSchedules = () => get('/members/flexible-schedules/all_latest/')

/** 按用户获取可投入安排 */
export const getScheduleByUser = (userId: number) => get('/members/flexible-schedules/by_user/', { user_id: userId })

// ============================================
// 成员详情 API
// ============================================

/** 获取成员详情（不传 userId 则获取当前用户） */
export const getMemberDetail = (userId?: number) => get('/members/member-detail/', userId ? { user_id: userId } : {})

// ============================================
// P2: 成员成长时间线
// ============================================

/** 成长时间线事件 */
export interface GrowthEvent {
  id: string
  type: string
  title: string
  description: string
  timestamp: string | null
  date: string | null
  project_name: string
  metadata: Record<string, any>
}

/** 成长时间线数据 */
export interface GrowthTimelineData {
  user_id: number
  user_name: string
  contrib_summary: {
    total: number
    approved: number
    pending: number
    total_weight: number
  }
  events: GrowthEvent[]
  total_events: number
}

/** 获取成员成长时间线 */
export function getGrowthTimeline(userId?: number): Promise<GrowthTimelineData> {
  return get('/members/growth-timeline/', userId ? { user_id: userId } : {})
}
