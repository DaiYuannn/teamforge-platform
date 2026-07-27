import { describe, expect, it } from 'vitest'
import {
  canApproveSensitive,
  normalizeSensitiveWorkspaceTab,
} from './sensitiveWorkspace'

describe('sensitive workspace access', () => {
  it('only exposes the approval queue to sensitive approver roles', () => {
    expect(canApproveSensitive('member')).toBe(false)
    expect(canApproveSensitive('sens_approver')).toBe(true)
    expect(canApproveSensitive('teacher')).toBe(true)
    expect(canApproveSensitive('sys_admin')).toBe(true)
  })

  it('falls back to the catalogue when a member deep-links to approvals', () => {
    expect(normalizeSensitiveWorkspaceTab('pending', 'member')).toBe('my-data')
    expect(normalizeSensitiveWorkspaceTab('pending', 'teacher')).toBe('pending')
    expect(normalizeSensitiveWorkspaceTab('requests', 'member')).toBe('requests')
    expect(normalizeSensitiveWorkspaceTab('unknown', 'sys_admin')).toBe('my-data')
  })
})
