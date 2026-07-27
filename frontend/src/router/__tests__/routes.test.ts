import { describe, expect, it } from 'vitest'
import router from '@/router'

describe('v2.1 workspace routes', () => {
  it('registers collaboration, analytics and administration workspaces', () => {
    const routes = new Map(router.getRoutes().map((route) => [route.name, route]))

    expect(routes.get('TaskCollaboration')?.path).toBe('/tasks/:id/collaboration')
    expect(routes.get('TaskCollaboration')?.meta.hidden).toBe(true)
    expect(routes.get('ProjectOperations')?.path).toBe('/projects/:id/operations')
    expect(routes.get('ProjectOperations')?.meta.hidden).toBe(true)
    expect(routes.get('AnalyticsStudio')?.path).toBe('/analytics-studio')
    expect(routes.get('PlatformCapabilities')?.path).toBe('/admin/platform-capabilities')
    expect(routes.get('EngineeringConsole')?.path).toBe('/admin/engineering')
    expect(routes.get('EngineeringConsole')?.meta.roles).toEqual(['sys_admin'])
    expect(routes.get('IPTodo')?.meta.title).toBe('知识产权待办')
  })

  it('keeps legacy sensitive links as hidden workspace redirects', () => {
    const routes = new Map(router.getRoutes().map((route) => [route.name, route]))
    const requestRoute = routes.get('SensitiveRequests')
    const pendingRoute = routes.get('SensitivePending')

    expect(requestRoute?.meta.hidden).toBe(true)
    expect(pendingRoute?.meta.hidden).toBe(true)
    expect(typeof requestRoute?.redirect).toBe('function')
    expect(typeof pendingRoute?.redirect).toBe('function')

    const requestTarget = typeof requestRoute?.redirect === 'function'
      ? requestRoute.redirect({ query: { source: 'notification' } } as never, {} as never)
      : requestRoute?.redirect
    const pendingTarget = typeof pendingRoute?.redirect === 'function'
      ? pendingRoute.redirect({ query: { request_id: '17' } } as never, {} as never)
      : pendingRoute?.redirect

    expect(requestTarget).toEqual({
      name: 'SensitiveCenter',
      query: { source: 'notification', tab: 'requests' },
    })
    expect(pendingTarget).toEqual({
      name: 'SensitiveCenter',
      query: { request_id: '17', tab: 'pending' },
    })
  })
})
