import type { EndpointItem, EndpointOperation } from '@/api/engineering'

export const DEFAULT_AUTO_REFRESH_MS = 30_000

export const AUTO_REFRESH_OPTIONS = [
  { label: '关闭', value: 0 },
  { label: '15 秒', value: 15_000 },
  { label: '30 秒', value: 30_000 },
  { label: '60 秒', value: 60_000 },
] as const

export interface EndpointOperationItem extends EndpointOperation {
  path: string
  method: string
}

const METHOD_ORDER = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

export function flattenEndpointOperations(endpoints: EndpointItem[]): EndpointOperationItem[] {
  return endpoints.flatMap((endpoint) => {
    const operations = Object.entries(endpoint.operations || {})
    const rows = operations.length
      ? operations
      : endpoint.methods.map((method) => [method, {
          operation_id: '',
          summary: '',
          tags: [],
        }] as const)

    return rows.map(([method, operation]) => ({
      path: endpoint.path,
      method: method.toUpperCase(),
      operation_id: operation.operation_id || '',
      summary: operation.summary || '',
      tags: [...new Set(operation.tags || [])],
    }))
  }).sort((left, right) => {
    const pathOrder = left.path.localeCompare(right.path)
    if (pathOrder !== 0) return pathOrder
    return METHOD_ORDER.indexOf(left.method) - METHOD_ORDER.indexOf(right.method)
  })
}

export function filterEndpointOperations(
  operations: EndpointOperationItem[],
  search: string,
): EndpointOperationItem[] {
  const keyword = search.trim().toLowerCase()
  if (!keyword) return operations
  return operations.filter((operation) => [
    operation.path,
    operation.method,
    operation.operation_id,
    operation.summary,
    ...operation.tags,
  ].join(' ').toLowerCase().includes(keyword))
}

export function statusCodeTone(statusCode: string): 'success' | 'warning' | 'danger' | 'info' {
  const code = Number(statusCode)
  if (code >= 500) return 'danger'
  if (code >= 400) return 'warning'
  if (code >= 300) return 'info'
  return 'success'
}

export function methodTone(method: string): 'success' | 'warning' | 'danger' | 'info' {
  if (method === 'GET') return 'success'
  if (method === 'DELETE') return 'danger'
  if (method === 'PUT' || method === 'PATCH') return 'warning'
  return 'info'
}
