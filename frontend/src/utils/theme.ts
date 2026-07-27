import type { ThemeMode } from '@/types'

export const PRIMARY_COLOR_OPTIONS = [
  { value: '#176b73', label: '青色' },
  { value: '#2f6f4e', label: '绿色' },
  { value: '#6f5a86', label: '紫色' },
  { value: '#9a6238', label: '棕色' },
] as const

export type PrimaryColor = string
export type ResolvedTheme = 'light' | 'dark'

export interface ThemePreference {
  theme_mode: ThemeMode
  schedule_start: string
  schedule_end: string
}

export const DEFAULT_PRIMARY_COLOR: PrimaryColor = PRIMARY_COLOR_OPTIONS[0].value
export const DEFAULT_THEME_MODE: ThemeMode = 'system'
export const DEFAULT_SCHEDULE_START = '19:00'
export const DEFAULT_SCHEDULE_END = '07:00'
export const THEME_SCHEDULE_REFRESH_MS = 60_000

const legacyPrimaryColorMap: Record<string, string> = {
  blue: '#176b73',
  green: '#2f6f4e',
  purple: '#6f5a86',
  orange: '#9a6238',
}

const HEX_COLOR_PATTERN = /^#[0-9a-f]{6}$/
const TIME_PATTERN = /^([01]\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?$/
const THEME_MODES = new Set<ThemeMode>(['light', 'dark', 'system', 'schedule'])
export const MIN_PRIMARY_COLOR_CONTRAST = 4.5

let activePrimaryColor: PrimaryColor = DEFAULT_PRIMARY_COLOR
let activeThemePreference: ThemePreference = {
  theme_mode: DEFAULT_THEME_MODE,
  schedule_start: DEFAULT_SCHEDULE_START,
  schedule_end: DEFAULT_SCHEDULE_END,
}
let systemMediaQuery: MediaQueryList | null = null
let systemMediaListener: ((event: MediaQueryListEvent) => void) | null = null
let scheduleBoundaryTimer: number | null = null
let scheduleRefreshTimer: number | null = null

function parseHexColor(color: string): [number, number, number] {
  return [
    Number.parseInt(color.slice(1, 3), 16),
    Number.parseInt(color.slice(3, 5), 16),
    Number.parseInt(color.slice(5, 7), 16),
  ]
}

function resolveHexColor(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toLowerCase()
  const compatibleValue = legacyPrimaryColorMap[normalized] || normalized
  return HEX_COLOR_PATTERN.test(compatibleValue) ? compatibleValue : null
}

function relativeLuminance(color: string): number {
  const [red, green, blue] = parseHexColor(color).map((channel) => {
    const normalized = channel / 255
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue
}

export function colorContrastRatio(foreground: unknown, background: unknown): number {
  const foregroundColor = resolveHexColor(foreground)
  const backgroundColor = resolveHexColor(background)
  if (!foregroundColor || !backgroundColor) return 0
  const lighter = Math.max(relativeLuminance(foregroundColor), relativeLuminance(backgroundColor))
  const darker = Math.min(relativeLuminance(foregroundColor), relativeLuminance(backgroundColor))
  return (lighter + 0.05) / (darker + 0.05)
}

/** 主色按钮使用白色文字，需达到 WCAG AA 普通文本对比度。 */
export function primaryColorContrast(value: unknown): number {
  const color = resolveHexColor(value)
  if (!color) return 0
  return colorContrastRatio(color, '#ffffff')
}

export function isReadablePrimaryColor(value: unknown): boolean {
  return primaryColorContrast(value) >= MIN_PRIMARY_COLOR_CONTRAST
}

function toHex(value: number): string {
  return Math.round(value).toString(16).padStart(2, '0')
}

function mixHexColor(color: string, target: string, weight: number): string {
  const sourceRgb = parseHexColor(color)
  const targetRgb = parseHexColor(target)
  return `#${sourceRgb
    .map((channel, index) => toHex(channel * (1 - weight) + targetRgb[index] * weight))
    .join('')}`
}

function ensureContrastOnDarkSurface(color: string): string {
  const background = '#24312c'
  if (colorContrastRatio(color, background) >= MIN_PRIMARY_COLOR_CONTRAST) return color

  let low = 0
  let high = 1
  for (let index = 0; index < 16; index += 1) {
    const weight = (low + high) / 2
    if (colorContrastRatio(mixHexColor(color, '#ffffff', weight), background)
      >= MIN_PRIMARY_COLOR_CONTRAST) {
      high = weight
    } else {
      low = weight
    }
  }
  return mixHexColor(color, '#ffffff', Math.min(1, high + 0.01))
}

export function normalizePrimaryColor(value: unknown): PrimaryColor {
  const color = resolveHexColor(value)
  return color && isReadablePrimaryColor(color) ? color : DEFAULT_PRIMARY_COLOR
}

export function normalizeScheduleTime(value: unknown, fallback: string): string {
  if (typeof value !== 'string') return fallback
  const match = value.trim().match(TIME_PATTERN)
  return match ? `${match[1]}:${match[2]}` : fallback
}

export function normalizeThemePreference(
  value?: Partial<ThemePreference> | null,
): ThemePreference {
  const requestedMode = typeof value?.theme_mode === 'string'
    ? value.theme_mode.toLowerCase() as ThemeMode
    : DEFAULT_THEME_MODE
  const themeMode = THEME_MODES.has(requestedMode) ? requestedMode : DEFAULT_THEME_MODE
  let scheduleStart = normalizeScheduleTime(value?.schedule_start, DEFAULT_SCHEDULE_START)
  let scheduleEnd = normalizeScheduleTime(value?.schedule_end, DEFAULT_SCHEDULE_END)
  if (scheduleStart === scheduleEnd) {
    scheduleStart = DEFAULT_SCHEDULE_START
    scheduleEnd = DEFAULT_SCHEDULE_END
  }
  return {
    theme_mode: themeMode,
    schedule_start: scheduleStart,
    schedule_end: scheduleEnd,
  }
}

function minutesSinceMidnight(date: Date): number {
  return date.getHours() * 60 + date.getMinutes()
}

function scheduleMinutes(value: string): number {
  const [hours, minutes] = value.split(':').map(Number)
  return hours * 60 + minutes
}

/** 支持普通日间区间和例如 19:00-07:00 的跨午夜区间。 */
export function isWithinDarkSchedule(
  now: Date,
  scheduleStart: string,
  scheduleEnd: string,
): boolean {
  const normalized = normalizeThemePreference({
    theme_mode: 'schedule',
    schedule_start: scheduleStart,
    schedule_end: scheduleEnd,
  })
  const current = minutesSinceMidnight(now)
  const start = scheduleMinutes(normalized.schedule_start)
  const end = scheduleMinutes(normalized.schedule_end)
  return start < end
    ? current >= start && current < end
    : current >= start || current < end
}

function systemPrefersDark(): boolean {
  return typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function resolveThemePreference(
  preference?: Partial<ThemePreference> | null,
  now = new Date(),
  prefersDark = systemPrefersDark(),
): ResolvedTheme {
  const normalized = normalizeThemePreference(preference)
  if (normalized.theme_mode === 'dark') return 'dark'
  if (normalized.theme_mode === 'light') return 'light'
  if (normalized.theme_mode === 'system') return prefersDark ? 'dark' : 'light'
  return isWithinDarkSchedule(now, normalized.schedule_start, normalized.schedule_end)
    ? 'dark'
    : 'light'
}

export function millisecondsUntilNextScheduleBoundary(
  now: Date,
  scheduleStart: string,
  scheduleEnd: string,
): number {
  const normalized = normalizeThemePreference({
    theme_mode: 'schedule',
    schedule_start: scheduleStart,
    schedule_end: scheduleEnd,
  })
  const candidates = [normalized.schedule_start, normalized.schedule_end].map((time) => {
    const [hours, minutes] = time.split(':').map(Number)
    const boundary = new Date(now)
    boundary.setHours(hours, minutes, 0, 0)
    if (boundary.getTime() <= now.getTime()) boundary.setDate(boundary.getDate() + 1)
    return boundary.getTime()
  })
  return Math.max(1_000, Math.min(...candidates) - now.getTime() + 50)
}

export function getPrimaryColorVariables(
  value: unknown,
  resolvedTheme: ResolvedTheme = 'light',
): Record<string, string> {
  const fillColor = normalizePrimaryColor(value)
  const color = resolvedTheme === 'dark' ? ensureContrastOnDarkSurface(fillColor) : fillColor
  const rgb = parseHexColor(color).join(', ')
  const fillRgb = parseHexColor(fillColor).join(', ')
  const scaleTarget = resolvedTheme === 'dark' ? '#141c19' : '#ffffff'
  const lightColors = Array.from({ length: 9 }, (_, index) =>
    mixHexColor(fillColor, scaleTarget, (index + 1) / 10)
  )
  const hoverColor = mixHexColor(color, resolvedTheme === 'dark' ? '#ffffff' : '#000000', 0.15)
  const fillHoverColor = mixHexColor(fillColor, '#000000', 0.15)

  const variables: Record<string, string> = {
    '--color-primary': color,
    '--color-primary-hover': hoverColor,
    '--color-primary-fill': fillColor,
    '--color-primary-fill-hover': fillHoverColor,
    '--color-primary-soft': lightColors[8],
    '--primary-color': color,
    '--primary-dark': hoverColor,
    '--primary-light': lightColors[2],
    '--primary-lighter': lightColors[8],
    '--primary-rgb': rgb,
    '--primary-fill-rgb': fillRgb,
    '--sidebar-hover-bg': lightColors[8],
    '--shadow-primary': `0 6px 16px rgba(${fillRgb}, 0.18)`,
    '--focus-ring': `rgba(${rgb}, 0.65)`,
    '--el-color-primary': fillColor,
    '--el-color-primary-rgb': fillRgb,
    '--el-color-primary-dark-2': fillHoverColor,
  }

  lightColors.forEach((lightColor, index) => {
    variables[`--el-color-primary-light-${index + 1}`] = lightColor
  })
  return variables
}

function currentDocumentTheme(): ResolvedTheme {
  if (typeof document === 'undefined') return 'light'
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

export function applyPrimaryColor(value: unknown): PrimaryColor {
  const color = normalizePrimaryColor(value)
  activePrimaryColor = color
  if (typeof document === 'undefined') return color
  const rootStyle = document.documentElement.style
  Object.entries(getPrimaryColorVariables(color, currentDocumentTheme())).forEach(
    ([property, propertyValue]) => rootStyle.setProperty(property, propertyValue)
  )
  return color
}

export function resetPrimaryColor(): PrimaryColor {
  return applyPrimaryColor(DEFAULT_PRIMARY_COLOR)
}

function clearSystemListener(): void {
  if (!systemMediaQuery || !systemMediaListener) return
  if (typeof systemMediaQuery.removeEventListener === 'function') {
    systemMediaQuery.removeEventListener('change', systemMediaListener)
  } else {
    const legacyQuery = systemMediaQuery as MediaQueryList & {
      removeListener?: (listener: (event: MediaQueryListEvent) => void) => void
    }
    legacyQuery.removeListener?.(systemMediaListener)
  }
  systemMediaQuery = null
  systemMediaListener = null
}

function clearScheduleTimers(): void {
  if (scheduleBoundaryTimer !== null) clearTimeout(scheduleBoundaryTimer)
  if (scheduleRefreshTimer !== null) clearInterval(scheduleRefreshTimer)
  scheduleBoundaryTimer = null
  scheduleRefreshTimer = null
}

export function stopThemeRuntime(): void {
  clearSystemListener()
  clearScheduleTimers()
}

function writeResolvedTheme(theme: ResolvedTheme): void {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.dataset.theme = theme
  root.dataset.themeMode = activeThemePreference.theme_mode
  root.classList.toggle('dark', theme === 'dark')
  root.style.colorScheme = theme
  applyPrimaryColor(activePrimaryColor)
}

function refreshActiveTheme(now = new Date()): ResolvedTheme {
  const resolved = resolveThemePreference(activeThemePreference, now)
  writeResolvedTheme(resolved)
  return resolved
}

function armScheduleBoundary(): void {
  if (activeThemePreference.theme_mode !== 'schedule' || typeof window === 'undefined') return
  if (scheduleBoundaryTimer !== null) clearTimeout(scheduleBoundaryTimer)
  scheduleBoundaryTimer = window.setTimeout(() => {
    refreshActiveTheme()
    armScheduleBoundary()
  }, millisecondsUntilNextScheduleBoundary(
    new Date(),
    activeThemePreference.schedule_start,
    activeThemePreference.schedule_end,
  ))
}

function startScheduleRuntime(): void {
  if (typeof window === 'undefined') return
  armScheduleBoundary()
  scheduleRefreshTimer = window.setInterval(
    () => refreshActiveTheme(),
    THEME_SCHEDULE_REFRESH_MS,
  )
}

function startSystemRuntime(): void {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
  systemMediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  systemMediaListener = () => refreshActiveTheme()
  if (typeof systemMediaQuery.addEventListener === 'function') {
    systemMediaQuery.addEventListener('change', systemMediaListener)
  } else {
    const legacyQuery = systemMediaQuery as MediaQueryList & {
      addListener?: (listener: (event: MediaQueryListEvent) => void) => void
    }
    legacyQuery.addListener?.(systemMediaListener)
  }
}

export function applyThemePreference(
  preference?: Partial<ThemePreference> | null,
): ResolvedTheme {
  activeThemePreference = normalizeThemePreference(preference)
  stopThemeRuntime()
  const resolved = refreshActiveTheme()
  if (activeThemePreference.theme_mode === 'system') startSystemRuntime()
  if (activeThemePreference.theme_mode === 'schedule') startScheduleRuntime()
  return resolved
}

export function getActiveThemePreference(): ThemePreference {
  return { ...activeThemePreference }
}

export function resetThemePreference(): ResolvedTheme {
  return applyThemePreference({
    theme_mode: DEFAULT_THEME_MODE,
    schedule_start: DEFAULT_SCHEDULE_START,
    schedule_end: DEFAULT_SCHEDULE_END,
  })
}
