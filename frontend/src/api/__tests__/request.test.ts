import { describe, expect, it } from 'vitest'
import service, {
  API_BASE_URL,
  isApiResponse,
  isPublicAuthRequest,
  unwrapResponseData,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from '@/api/request'

describe('API response compatibility', () => {
  it('uses the same-origin API prefix when no build-time base URL is provided', () => {
    expect(API_BASE_URL).toBe('/api/v1')
    expect(service.defaults.baseURL).toBe('/api/v1')
  })

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
    expect(isPublicAuthRequest('/auth/password-reset/request/')).toBe(true)
  })

  it('continues attaching authentication to protected APIs', () => {
    expect(isPublicAuthRequest('/users/me/')).toBe(false)
    expect(isPublicAuthRequest('/finance/overview/')).toBe(false)
  })
})

describe('token persistence', () => {
  it('keeps ordinary sessions in sessionStorage', () => {
    setTokens('session-access', 'session-refresh', false)
    expect(sessionStorage.getItem('access_token')).toBe('session-access')
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(getAccessToken()).toBe('session-access')
    expect(getRefreshToken()).toBe('session-refresh')
    clearTokens()
  })

  it('keeps remembered sessions in localStorage', () => {
    setTokens('local-access', 'local-refresh', true)
    expect(localStorage.getItem('access_token')).toBe('local-access')
    expect(sessionStorage.getItem('access_token')).toBeNull()
    clearTokens()
  })
})
