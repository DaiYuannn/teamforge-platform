import { get } from './request'
import type { DashboardData } from '@/types'

/** 获取首页驾驶舱数据 */
export function getDashboardData(): Promise<DashboardData> {
  return get<DashboardData>('/dashboard/')
}
