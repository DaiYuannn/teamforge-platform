import { get } from './request'

export interface SkillMatrixTeamMembership {
  team_id: number
  team_name: string
  parent_id: number | null
  parent_name: string
  role: string
  role_display: string
  status: string
  status_display: string
}

export interface SkillMatrixSkill {
  id: number
  skill_id: number
  name: string
  proficiency: number
}

export interface SkillMatrixParticipation {
  participant_id: number
  role: 'leader' | 'member' | 'advisor'
  role_display: string
  participation_status: 'planned' | 'confirmed'
  participation_status_display: string
  responsibility: string
}

export interface SkillMatrixMember {
  user_id: number
  name: string
  username: string
  avatar: string
  school: string
  major: string
  grade: string
  global_role: string
  global_role_display: string
  membership_status: string
  membership_status_display: string
  team_memberships: SkillMatrixTeamMembership[]
  skills: SkillMatrixSkill[]
  entry_participation: SkillMatrixParticipation | null
}

export interface SkillMatrixCompetitionScope {
  event_id: number
  event_name: string
  event_edition: string
  entry_id: number
  entry_name: string
  project_id: number
  project_name: string
}

export interface SkillMatrixResponse {
  scope: {
    type: 'organization' | 'competition_entry' | 'self'
    competition: SkillMatrixCompetitionScope | null
  }
  count: number
  skill_columns: Array<{ id: number; name: string }>
  members: SkillMatrixMember[]
}

export interface SkillMatrixQuery {
  search?: string
  school?: string
  major?: string
  team_role?: string
  member_status?: string
  skill?: string
  skill_id?: number
  min_proficiency?: number
  competition_event?: number
  competition_entry?: number
}

export interface SkillRecommendationMatchedSkill {
  skill_id: number
  name: string
  proficiency: number
  required_proficiency: number
}

export interface SkillRecommendationMissingSkill {
  skill_id: number
  name: string
  current_proficiency: number | null
  required_proficiency: number
  reason: string
}

export interface SkillRecommendation extends SkillMatrixMember {
  rank: number
  score: number
  matched_count: number
  required_count: number
  coverage_ratio: number
  matched_skills: SkillRecommendationMatchedSkill[]
  missing_skills: SkillRecommendationMissingSkill[]
  explanations: string[]
}

export interface SkillRecommendationResponse {
  competition: SkillMatrixCompetitionScope
  minimum_proficiency: number
  required_skills: Array<{
    skill_id: number
    name: string
    required_proficiency: number
  }>
  candidate_count: number
  ranking_formula: string
  recommendations: SkillRecommendation[]
}

export interface SkillRecommendationQuery {
  competition_event: number
  competition_entry: number
  required_skill_ids?: number[]
  required_skills?: string[]
  min_proficiency?: number
}

function compactParams(
  params: Record<string, unknown>,
): Record<string, string | number | boolean> {
  const compacted: Record<string, string | number | boolean> = {}
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      const compact = value.filter(
        (item) => item !== undefined && item !== null && item !== '',
      )
      if (compact.length) compacted[key] = compact.join(',')
      return
    }
    if (typeof value === 'string') {
      const trimmed = value.trim()
      if (trimmed) compacted[key] = trimmed
      return
    }
    compacted[key] = value as number | boolean
  })
  return compacted
}

/** 查询总团队或一条精确参赛条目的只读技能矩阵。 */
export function getTeamSkillMatrix(
  params: SkillMatrixQuery = {},
): Promise<SkillMatrixResponse> {
  return get<SkillMatrixResponse>(
    '/skill-matrix/matrix/',
    compactParams(params as Record<string, unknown>),
  )
}

/** 按比赛届次、参赛条目和必需技能生成可解释的候选人排序。 */
export function getSkillRecommendations(
  params: SkillRecommendationQuery,
): Promise<SkillRecommendationResponse> {
  return get<SkillRecommendationResponse>(
    '/skill-matrix/recommendations/',
    compactParams(params as unknown as Record<string, unknown>),
  )
}
