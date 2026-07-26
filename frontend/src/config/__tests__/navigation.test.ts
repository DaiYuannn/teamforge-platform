import { describe, expect, it } from 'vitest'
import {
  getMobilePrimaryNavigation,
  getVisibleNavigationGroups,
  isExternalRouteAllowed,
} from '@/config/navigation'

describe('account-scoped navigation', () => {
  it('only exposes project collaboration surfaces to external accounts', () => {
    const paths = getVisibleNavigationGroups('member', 'external')
      .flatMap((group) => group.items)
      .map((item) => item.path)

    expect(paths).toContain('/projects')
    expect(paths).toContain('/tasks')
    expect(paths).toContain('/files')
    expect(paths).toContain('/notifications')
    expect(paths).not.toContain('/finance')
    expect(paths).not.toContain('/members')
    expect(paths).not.toContain('/dashboard')
    expect(paths).not.toContain('/audit/logs')
  })

  it('uses an external-safe mobile tab set and route guard policy', () => {
    const paths = getMobilePrimaryNavigation('external').map((item) => item.path)

    expect(paths).toEqual([
      '/projects',
      '/tasks',
      '/files',
      '/notifications',
      '/user/profile',
    ])
    expect(isExternalRouteAllowed('/projects/12')).toBe(true)
    expect(isExternalRouteAllowed('/public-portal')).toBe(true)
    expect(isExternalRouteAllowed('/finance')).toBe(false)
  })
})
