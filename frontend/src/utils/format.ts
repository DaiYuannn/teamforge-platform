import dayjs from 'dayjs'
import {
  PROJECT_STAGES,
  PROJECT_STATUS_MAP,
  PROJECT_ROLE_MAP,
  TASK_STATUS_MAP,
  TASK_PRIORITY_MAP,
  ROLE_MAP,
  FINANCE_CATEGORY_MAP,
  COMPETITION_LEVEL_MAP,
  COMPETITION_STATUS_MAP,
  STAGE_COLOR_MAP,
  STAGE_HEX_COLOR_MAP,
} from './constants'

// ============================================
// 日期格式化
// ============================================

/** 格式化日期 YYYY-MM-DD */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD')
}

/** 格式化日期时间 YYYY-MM-DD HH:mm */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

/** 格式化日期时间（带秒）YYYY-MM-DD HH:mm:ss */
export function formatDateTimeFull(date: string | Date | null | undefined): string {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

/** 相对时间（如"3天前"） */
export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return '-'
  const now = dayjs()
  const target = dayjs(date)
  const diffDays = now.diff(target, 'day')
  const diffHours = now.diff(target, 'hour')
  const diffMinutes = now.diff(target, 'minute')

  if (diffMinutes < 1) return '刚刚'
  if (diffMinutes < 60) return `${diffMinutes}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 30) return `${diffDays}天前`
  return formatDate(date)
}

/** 将后端的 0-100 百分比约束到可展示范围。 */
export function normalizePercentage(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null
  return Math.min(100, Math.max(0, numericValue))
}

// ============================================
// 金额格式化
// ============================================

function toFiniteNumber(value: number | string | null | undefined): number {
  if (value === null || value === undefined || value === '') return 0
  const normalized = typeof value === 'string' ? value.replace(/[¥,\s]/g, '') : value
  const numberValue = Number(normalized)
  return Number.isFinite(numberValue) ? numberValue : 0
}

/** 格式化金额（分 -> 元，保留2位小数，带¥符号） */
export function formatMoney(cents: number | string | null | undefined): string {
  const centValue = toFiniteNumber(cents)
  if (!Number.isFinite(centValue)) return '¥0.00'
  const yuan = centValue / 100
  return `¥${yuan.toFixed(2)}`
}

/** 格式化金额（元为单位，保留2位小数，带¥符号） */
export function formatYuan(yuan: number | string | null | undefined): string {
  return `¥${toFiniteNumber(yuan).toFixed(2)}`
}

/** 格式化金额（千分位） */
export function formatMoneyWithComma(yuan: number | string | null | undefined): string {
  return `¥${toFiniteNumber(yuan).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// ============================================
// 文件大小格式化
// ============================================

/** 格式化文件大小 */
export function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`
}

// ============================================
// 状态标签颜色映射
// ============================================

/** 获取项目阶段标签 */
export function getStageLabel(stage: number | string): string {
  return PROJECT_STAGES[Number(stage)] || String(stage)
}

/** 获取项目阶段颜色 */
export function getStageColor(_stage: number | string): string {
  return '#909399'
}

/** 获取项目状态标签 */
export function getProjectStatusLabel(status: string): string {
  return PROJECT_STATUS_MAP[status]?.label || status
}

/** 获取项目状态标签类型 */
export function getProjectStatusTagType(status: string): string {
  return PROJECT_STATUS_MAP[status]?.type || 'info'
}

/** 获取项目成员角色标签 */
export function getProjectRoleLabel(role: string): string {
  return PROJECT_ROLE_MAP[role]?.label || role
}

/** 获取任务状态标签 */
export function getTaskStatusLabel(status: string): string {
  return TASK_STATUS_MAP[status]?.label || status
}

/** 获取任务状态标签类型 */
export function getTaskStatusTagType(status: string): string {
  return TASK_STATUS_MAP[status]?.type || 'info'
}

/** 获取任务状态颜色 */
export function getTaskStatusColor(_status: string): string {
  return '#909399'
}

/** 获取任务优先级标签 */
export function getTaskPriorityLabel(priority: string): string {
  return TASK_PRIORITY_MAP[priority]?.label || priority
}

/** 获取任务优先级标签类型 */
export function getTaskPriorityTagType(priority: string): string {
  return TASK_PRIORITY_MAP[priority]?.tagType || 'info'
}

/** 获取角色标签 */
export function getRoleLabel(role: string): string {
  return ROLE_MAP[role]?.label || role
}

/** 获取角色标签类型 */
export function getRoleTagType(role: string): string {
  return ROLE_MAP[role]?.tagType || 'info'
}

/** 获取经费类别标签 */
export function getFinanceCategoryLabel(category: string): string {
  return FINANCE_CATEGORY_MAP[category]?.label || category
}

/** 获取经费类别颜色 */
export function getFinanceCategoryColor(category: string): string {
  return FINANCE_CATEGORY_MAP[category]?.color || '#909399'
}

/** 获取比赛级别标签 */
export function getCompetitionLevelLabel(level: string): string {
  return COMPETITION_LEVEL_MAP[level]?.label || level
}

/** 获取比赛级别标签类型 */
export function getCompetitionLevelTagType(level: string): string {
  return COMPETITION_LEVEL_MAP[level]?.tagType || 'info'
}

/**
 * 获取比赛级别的 el-tag type（需求C：基于 STAGE_COLOR_MAP）
 * 兼容 school/city/province/national/international 与 national/provincial/municipal/school/enterprise 两套命名
 */
export function getCompetitionStageTagType(level: string): string {
  return STAGE_COLOR_MAP[level] ?? COMPETITION_LEVEL_MAP[level]?.tagType ?? 'info'
}

/**
 * 获取比赛级别的十六进制颜色（需求C：用于时间线节点、矩阵单元格等非 el-tag 场景）
 */
export function getCompetitionStageColor(level: string): string {
  return STAGE_HEX_COLOR_MAP[level] || '#909399'
}

/**
 * 获取比赛级别 el-tag 的自定义样式（需求C：international 为紫色自定义，需深底浅字）
 * 仅在 level 为 international 时返回紫色背景样式，其余返回空对象（交由 el-tag type 控制配色）
 */
export function getCompetitionStageTagStyle(level: string): Record<string, string> {
  if (level === 'international') {
    return {
      backgroundColor: '#9B59B6',
      borderColor: '#9B59B6',
      color: '#ffffff',
    }
  }
  return {}
}

/** 获取比赛状态标签 */
export function getCompetitionStatusLabel(status: string): string {
  return COMPETITION_STATUS_MAP[status]?.label || status
}

/** 获取比赛状态标签类型 */
export function getCompetitionStatusTagType(status: string): string {
  return COMPETITION_STATUS_MAP[status]?.tagType || 'info'
}

// ============================================
// 通用工具函数
// ============================================

/** 生成唯一ID */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/** 防抖函数 */
export function debounce<T extends (...args: unknown[]) => unknown>(fn: T, delay = 300): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}

/** 深拷贝 */
export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

/** 下载Blob文件 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1000)
}

/** 获取文件扩展名 */
export function getFileExtension(filename: string): string {
  return filename.split('.').pop()?.toLowerCase() || ''
}

/** 判断是否为图片文件 */
export function isImageFile(filename: string): boolean {
  const ext = getFileExtension(filename)
  return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext)
}
