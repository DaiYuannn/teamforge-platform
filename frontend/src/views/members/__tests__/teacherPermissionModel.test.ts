import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { ROLE_MAP } from '@/utils/constants'
import { TEAM_ROLE_OPTIONS } from '../memberTeamRole'


describe('small-team teacher permission model', () => {
  it('labels the global teacher as the sole operator and team teachers as read-only', () => {
    expect(ROLE_MAP.teacher.label).toBe('操作老师')
    expect(
      TEAM_ROLE_OPTIONS.find((option) => option.value === 'teacher')?.label,
    ).toBe('查看老师（只读）')
  })

  it('explains how extra teachers must be configured in user management', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/admin/UserManageView.vue'),
      'utf8',
    )
    expect(source).toContain('“操作老师”全局只能有一位')
    expect(source).toContain('查看老师（只读）')
  })
})
