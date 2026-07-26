import type { CompetitionExportParams, CompetitionQueryParams } from '@/api/competitions'

/** 路由参数只能映射为正整数项目 ID，数组取第一个值。 */
export function parseCompetitionProjectQuery(
  value: string | Array<string | null> | null | undefined,
): number | undefined {
  const raw = Array.isArray(value) ? value.find((item): item is string => Boolean(item)) : value
  if (!raw || !/^\d+$/.test(raw)) return undefined
  const parsed = Number(raw)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : undefined
}

/** 导出全部匹配结果，不把当前页码、每页条数和排序等视图参数带入导出。 */
export function toCompetitionExportParams(
  query: CompetitionQueryParams,
): CompetitionExportParams {
  return {
    search: query.search?.trim() || undefined,
    level: query.level || undefined,
    status: query.status || undefined,
    project: query.project,
  }
}
