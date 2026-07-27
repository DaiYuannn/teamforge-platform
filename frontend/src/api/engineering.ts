import { get } from './request'

export interface PerformanceMetrics {
  request_count: number
  window_capacity: number
  requests_per_minute: number
  avg_response_time_ms: number
  p50_response_time_ms: number
  p95_response_time_ms: number
  p99_response_time_ms: number
  query_count: number
  avg_query_count: number
  avg_query_time_ms: number
  error_rate: number
  status_codes: Record<string, number>
  cache_hit_rate: number | null
  cache_metrics_available: boolean
  collected_at: string
  slow_query_threshold_seconds: number
  note: string
}

export interface SlowQuery {
  timestamp: string
  method: string
  path: string
  duration_ms: number
  sql: string
}

export interface SlowQueryResponse {
  slow_queries: SlowQuery[]
  total: number
  threshold_seconds: number
  source: string
}

export interface EndpointOperation {
  operation_id: string
  summary: string
  tags: string[]
}

export interface EndpointItem {
  path: string
  methods: string[]
  operations: Record<string, EndpointOperation>
}

export interface GovernanceCheck {
  item: string
  title: string
  passed: boolean
  detail: string
  unrestricted?: string[]
  unrestricted_count?: number
}

export interface BrowserAuditReference {
  runner: string
  command: string
  standard: string
  note: string
  source: 'ci' | string
  is_realtime: boolean
}

export interface GovernanceReport {
  scope: string
  checks: GovernanceCheck[]
  total: number
  passed: number
  failed: number
  endpoints_scanned: number
  paths_scanned: number
  score: number
  browser_audit: BrowserAuditReference
}

export function getPerformanceMetrics(): Promise<PerformanceMetrics> {
  return get('/common/performance/metrics/')
}

export function getSlowQueries(): Promise<SlowQueryResponse> {
  return get('/common/performance/slow-queries/')
}

export function getOpenApiEndpoints(): Promise<{ endpoints: EndpointItem[]; total: number; schema_url: string }> {
  return get('/common/openapi/endpoints/')
}

export function getOpenApiSchema(): Promise<Record<string, unknown>> {
  return get('/common/openapi/schema/')
}

export function getAccessibilityGovernance(): Promise<GovernanceReport> {
  return get('/common/accessibility/report/')
}
