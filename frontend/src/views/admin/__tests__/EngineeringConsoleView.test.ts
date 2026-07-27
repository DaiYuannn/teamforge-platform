import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import EngineeringConsoleView from '../EngineeringConsoleView.vue'

const apiMocks = vi.hoisted(() => ({
  getAccessibilityGovernance: vi.fn(),
  getOpenApiEndpoints: vi.fn(),
  getOpenApiSchema: vi.fn(),
  getPerformanceMetrics: vi.fn(),
  getSlowQueries: vi.fn(),
}))

vi.mock('@/api/engineering', () => apiMocks)

const metrics = {
  request_count: 12,
  window_capacity: 500,
  requests_per_minute: 4,
  avg_response_time_ms: 18,
  p50_response_time_ms: 12,
  p95_response_time_ms: 34,
  p99_response_time_ms: 51,
  query_count: 24,
  avg_query_count: 2,
  avg_query_time_ms: 3,
  error_rate: 0,
  status_codes: { 200: 11, 404: 1 },
  cache_hit_rate: null,
  cache_metrics_available: false,
  collected_at: '2026-07-27T09:00:00+08:00',
  slow_query_threshold_seconds: 0.2,
  note: '当前进程采样',
}

const governance = {
  scope: 'API',
  checks: [],
  total: 3,
  passed: 3,
  failed: 0,
  endpoints_scanned: 24,
  paths_scanned: 12,
  score: 100,
  browser_audit: {
    runner: 'Playwright + axe-core',
    command: 'npm run test:e2e',
    standard: 'WCAG 2.1 A/AA',
    note: 'CI 质量门禁',
    source: 'ci',
    is_realtime: false,
  },
}

type ConsoleViewModel = {
  refreshIntervalMs: number
}

let intervalHandler: (() => void) | null

function mountView() {
  return shallowMount(EngineeringConsoleView, {
    global: {
      directives: {
        loading: () => undefined,
      },
      stubs: {
        ElAlert: true,
        ElButton: true,
        ElDescriptions: true,
        ElDescriptionsItem: true,
        ElIcon: true,
        ElInput: true,
        ElOption: true,
        ElProgress: true,
        ElSelect: true,
        ElTable: { template: '<div><slot name="empty" /></div>' },
        ElTableColumn: true,
        ElTabPane: { template: '<div><slot /></div>' },
        ElTabs: { template: '<div><slot /></div>' },
        ElTag: true,
        ElTooltip: true,
      },
    },
  })
}

beforeEach(() => {
  Object.values(apiMocks).forEach((mock) => mock.mockReset())
  apiMocks.getPerformanceMetrics.mockResolvedValue(metrics)
  apiMocks.getSlowQueries.mockResolvedValue({
    slow_queries: [],
    total: 0,
    threshold_seconds: 0.2,
    source: 'process_memory',
  })
  apiMocks.getOpenApiEndpoints.mockResolvedValue({
    endpoints: [],
    total: 0,
    schema_url: '/api/common/openapi/schema/',
  })
  apiMocks.getOpenApiSchema.mockResolvedValue({ openapi: '3.0.3' })
  apiMocks.getAccessibilityGovernance.mockResolvedValue(governance)

  intervalHandler = null
  vi.spyOn(window, 'setInterval').mockImplementation((handler) => {
    intervalHandler = () => handler(undefined)
    return 73 as unknown as NodeJS.Timeout
  })
  vi.spyOn(window, 'clearInterval').mockImplementation(() => undefined)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('EngineeringConsoleView auto refresh', () => {
  it('passes visible labels through the shared component contracts', () => {
    const wrapper = mountView()

    expect(wrapper.findComponent(PageHeader).props('subtitle')).toBe('运行指标、接口契约与质量门禁')
    expect(wrapper.findAllComponents(EmptyState).map((component) => component.props('text')))
      .toEqual(['暂无慢查询', '没有匹配的接口'])

    wrapper.unmount()
  })

  it('starts at 30 seconds and can turn automatic refresh off', async () => {
    const wrapper = mountView()

    expect(window.setInterval).toHaveBeenCalledTimes(1)
    expect(window.setInterval).toHaveBeenCalledWith(expect.any(Function), 30_000)

    ;(wrapper.vm as unknown as ConsoleViewModel).refreshIntervalMs = 0
    await nextTick()

    expect(window.clearInterval).toHaveBeenCalledWith(73)
    expect(window.setInterval).toHaveBeenCalledTimes(1)

    wrapper.unmount()
    await flushPromises()
  })

  it('refreshes only performance data and clears the timer on unmount', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(apiMocks.getPerformanceMetrics).toHaveBeenCalledTimes(1)
    expect(apiMocks.getSlowQueries).toHaveBeenCalledTimes(1)
    expect(apiMocks.getOpenApiEndpoints).toHaveBeenCalledTimes(1)
    expect(apiMocks.getAccessibilityGovernance).toHaveBeenCalledTimes(1)
    expect(intervalHandler).not.toBeNull()

    intervalHandler?.()
    await flushPromises()

    expect(apiMocks.getPerformanceMetrics).toHaveBeenCalledTimes(2)
    expect(apiMocks.getSlowQueries).toHaveBeenCalledTimes(2)
    expect(apiMocks.getOpenApiEndpoints).toHaveBeenCalledTimes(1)
    expect(apiMocks.getAccessibilityGovernance).toHaveBeenCalledTimes(1)
    expect(apiMocks.getOpenApiSchema).not.toHaveBeenCalled()

    wrapper.unmount()
    expect(window.clearInterval).toHaveBeenCalledWith(73)
  })
})
