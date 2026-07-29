import { describe, expect, it } from 'vitest'
import {
  TEAM_ROLE_OPTIONS,
  teamRoleTagType,
  teamRoleText,
} from '../memberTeamRole'

describe('member team identity presentation', () => {
  it('keeps the same importance order as the member-directory backend', () => {
    expect(TEAM_ROLE_OPTIONS.map((option) => option.value)).toEqual([
      'teacher',
      'owner',
      'co_lead',
      'admin',
      'advisor',
      'member',
      'external',
    ])
  })

  it('prefers the backend display value and falls back to the role map', () => {
    expect(teamRoleText({
      team_role: 'owner',
      team_role_display: '所选小组主负责人',
    })).toBe('所选小组主负责人')
    expect(teamRoleText({ team_role: 'co_lead' })).toBe('共同负责人')
    expect(teamRoleText({})).toBe('未分组')
  })

  it('gives key leadership identities distinct tones', () => {
    expect(teamRoleTagType('teacher')).toBe('warning')
    expect(teamRoleTagType('owner')).toBe('danger')
    expect(teamRoleTagType('external')).toBe('info')
  })
})
