import { get, post, patch, del } from './request'
import type { PaginatedResponse, PaginationParams } from '@/types'

export type TeamMemberRole =
  | 'owner'
  | 'co_lead'
  | 'admin'
  | 'teacher'
  | 'member'
  | 'advisor'
  | 'external'

export type TeamMemberStatus = 'active' | 'on_leave' | 'exited'

export interface TeamMemberFilters {
  role?: TeamMemberRole
  school: string
  status?: TeamMemberStatus
}

export interface TeamMemberQueryParams {
  role?: TeamMemberRole
  school?: string
  status?: TeamMemberStatus
}

export interface Team {
  id: number
  name: string
  code?: string
  description: string
  contact_email?: string
  join_message?: string
  is_active: boolean
  owner: number
  owner_name: string
  member_count: number
  parent?: number | null
  parent_name?: string
  team_type: 'organization' | 'squad'
  team_type_display?: string
  child_count?: number
  current_user_role?: string
  can_manage?: boolean
  created_at: string
}

export interface TeamMember {
  id: number
  team: number
  user: number
  user_name: string
  user_email: string
  user_avatar?: string
  user_school?: string
  user_grade?: string
  user_major?: string
  role: TeamMemberRole
  role_display?: string
  status: TeamMemberStatus
  status_display?: string
  joined_at: string
  left_at?: string | null
  exit_reason?: string
  handover_to?: number | null
  handover_to_name?: string
  handover_notes?: string
}

export interface TeamCandidate {
  id: number
  name: string
  email: string
  membership_status: string
}

export function getTeams(params?: PaginationParams): Promise<PaginatedResponse<Team>> {
  return get<PaginatedResponse<Team>>('/teams/', params)
}

export function createTeam(data: Partial<Team>): Promise<Team> {
  return post<Team>('/teams/', data)
}

export function updateTeam(id: number, data: Partial<Team>): Promise<Team> {
  return patch<Team>(`/teams/${id}/`, data)
}

export function getTeamMembers(
  id: number,
  params?: TeamMemberQueryParams,
): Promise<TeamMember[]> {
  return get<TeamMember[]>(`/teams/${id}/members/`, params)
}

export function addTeamMember(id: number, user: number, role: string): Promise<TeamMember> {
  return post<TeamMember>(`/teams/${id}/members/`, { user, role })
}

export function transitionTeamMember(
  teamId: number,
  memberId: number,
  data: {
    role?: string
    status?: string
    reason?: string
    handover_to?: number
    handover_notes?: string
  },
): Promise<TeamMember> {
  return post<TeamMember>(`/teams/${teamId}/members/${memberId}/transition/`, data)
}

export function removeTeamMember(teamId: number, memberId: number): Promise<void> {
  return del<void>(`/teams/${teamId}/members/${memberId}/`)
}

export function getTeamCandidates(id: number, search?: string): Promise<TeamCandidate[]> {
  return get<TeamCandidate[]>(`/teams/${id}/candidates/`, search ? { search } : undefined)
}

export function transferTeamOwner(
  teamId: number,
  memberId: number,
  reason: string,
): Promise<Team> {
  return post<Team>(`/teams/${teamId}/transfer-owner/`, { member_id: memberId, reason })
}
