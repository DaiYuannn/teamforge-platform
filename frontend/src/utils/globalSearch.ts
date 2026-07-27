import type { LocationQueryRaw, RouteLocationRaw } from 'vue-router'

export function parseSearchTarget(url: string): RouteLocationRaw {
  const [path, queryString = ''] = url.split('?', 2)
  const query: LocationQueryRaw = {}
  for (const [key, value] of new URLSearchParams(queryString)) {
    const current = query[key]
    if (current === undefined) query[key] = value
    else query[key] = Array.isArray(current) ? [...current, value] : [current, value]
  }
  return Object.keys(query).length ? { path, query } : path
}

export function positiveQueryId(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
}
