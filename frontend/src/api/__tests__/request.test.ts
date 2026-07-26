import { describe, expect, it } from 'vitest'
import service, { isApiResponse, isPublicAuthRequest, unwrapResponseData } from '@/api/request'

describe('API response compatibility', () => {
  it('unwraps the standard API response envelope', () => {
    const project = { id: 1, code: 'P-001', name: '示例项目' }

    expect(unwrapResponseData({ code: 0, message: 'success', data: project })).toEqual(project)
  })

  it('keeps a raw DRF project detail response with a string code field', () => {
    const project = { id: 1, code: 'P-001', name: '示例项目' }

    expect(isApiResponse(project)).toBe(false)
    expect(unwrapResponseData(project)).toBe(project)
  })

  it('keeps a raw DRF intellectual-property detail response', () => {
    const application = { id: 7, application_code: 'IP-007', title: '示例成果' }

    expect(unwrapResponseData(application)).toBe(application)
  })

  it('returns Blob response data instead of the Axios response wrapper', async () => {
    const blob = new Blob(['backup'], { type: 'application/zip' })

    const result = await service.get('/backups/1/download/', {
      responseType: 'blob',
      adapter: async (config) => ({
        data: blob,
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }),
    })

    expect(result).toBe(blob)
  })
})

describe('public authentication requests', () => {
  it('keeps login and refresh requests anonymous even with query strings', () => {
    expect(isPublicAuthRequest('/auth/login/')).toBe(true)
    expect(isPublicAuthRequest('/auth/refresh/?source=retry')).toBe(true)
  })

  it('continues attaching authentication to protected APIs', () => {
    expect(isPublicAuthRequest('/users/me/')).toBe(false)
    expect(isPublicAuthRequest('/finance/overview/')).toBe(false)
  })
})
