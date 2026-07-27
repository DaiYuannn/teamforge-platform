import { describe, expect, it } from 'vitest'
import {
  FAVORITE_ROUTE_PATHS,
  getFavoriteNavigationItems,
  getFavoriteNavigationOptions,
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
    expect(paths).not.toContain('/analytics-studio')
    expect(paths).not.toContain('/admin/platform-capabilities')
    expect(paths).not.toContain('/admin/engineering')
  })

  it('exposes new workspaces according to internal roles', () => {
    const memberPaths = getVisibleNavigationGroups('member', 'active')
      .flatMap((group) => group.items)
      .map((item) => item.path)
    const adminPaths = getVisibleNavigationGroups('sys_admin', 'active')
      .flatMap((group) => group.items)
      .map((item) => item.path)

    expect(memberPaths).toContain('/analytics-studio')
    expect(memberPaths).toContain('/admin/platform-capabilities')
    expect(memberPaths).not.toContain('/admin/engineering')
    expect(adminPaths).toContain('/admin/engineering')
    expect(memberPaths.filter((path) => path.startsWith('/sensitive'))).toEqual(['/sensitive'])

    const outcomeItems = getVisibleNavigationGroups('member', 'active')
      .find((group) => group.key === 'outcomes')?.items || []
    expect(outcomeItems.find((item) => item.path === '/intellectual-property/todo')?.title)
      .toBe('知识产权待办')
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

  it('keeps each account favorite order while removing unavailable and duplicate routes', () => {
    const favorites = getFavoriteNavigationItems(
      ['/tasks', '/finance', '/tasks', '/projects', '/admin/users'],
      'member',
      'external',
    )

    expect(favorites.map((item) => item.path)).toEqual(['/tasks', '/projects'])
    expect(favorites.map((item) => item.groupTitle)).toEqual(['项目执行', '项目执行'])
  })

  it('only offers supported routes visible to the current account', () => {
    const memberOptions = getFavoriteNavigationOptions('member', 'active')
    const adminOptions = getFavoriteNavigationOptions('sys_admin', 'active')
    const externalOptions = getFavoriteNavigationOptions('member', 'external')

    expect(memberOptions.some((item) => item.path === '/admin/users')).toBe(false)
    expect(memberOptions.map((item) => item.path)).toEqual(expect.arrayContaining([
      '/notifications',
      '/analytics-studio',
    ]))
    expect(adminOptions.map((item) => item.path)).toEqual(expect.arrayContaining([
      '/admin/engineering',
      '/admin/users',
    ]))
    expect(externalOptions.map((item) => item.path)).toEqual([
      '/notifications',
      '/projects',
      '/projects/archive',
      '/competitions',
      '/tasks',
      '/files',
      '/contributions',
      '/contributions/pending',
    ])
    expect(adminOptions.every((item) => FAVORITE_ROUTE_PATHS.includes(item.path))).toBe(true)
  })
})
