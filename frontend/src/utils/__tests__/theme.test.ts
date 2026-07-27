import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  applyThemePreference,
  applyPrimaryColor,
  colorContrastRatio,
  DEFAULT_PRIMARY_COLOR,
  getPrimaryColorVariables,
  isReadablePrimaryColor,
  isWithinDarkSchedule,
  millisecondsUntilNextScheduleBoundary,
  normalizePrimaryColor,
  normalizeThemePreference,
  PRIMARY_COLOR_OPTIONS,
  primaryColorContrast,
  resolveThemePreference,
  resetPrimaryColor,
  stopThemeRuntime,
} from '@/utils/theme'

function createMediaQueryList(matches = false) {
  let changeListener: ((event: MediaQueryListEvent) => void) | null = null
  const mediaQuery = {
    matches,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: vi.fn((_type: string, listener: (event: MediaQueryListEvent) => void) => {
      changeListener = listener
    }),
    removeEventListener: vi.fn((_type: string, listener: (event: MediaQueryListEvent) => void) => {
      if (changeListener === listener) changeListener = null
    }),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(() => true),
  }

  return {
    mediaQuery,
    setMatches(value: boolean) {
      mediaQuery.matches = value
      changeListener?.({ matches: value, media: mediaQuery.media } as MediaQueryListEvent)
    },
  }
}

describe('theme utilities', () => {
  beforeEach(() => {
    stopThemeRuntime()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    document.documentElement.removeAttribute('style')
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.removeAttribute('data-theme-mode')
    document.documentElement.classList.remove('dark')
  })

  afterEach(() => {
    stopThemeRuntime()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('normalizes preset, custom, uppercase, and legacy primary colors', () => {
    expect(normalizePrimaryColor('#2F6F4E')).toBe('#2f6f4e')
    expect(normalizePrimaryColor('#245C8A')).toBe('#245c8a')
    expect(normalizePrimaryColor(' purple ')).toBe('#6f5a86')
    expect(normalizePrimaryColor('unsupported')).toBe(DEFAULT_PRIMARY_COLOR)
    expect(normalizePrimaryColor(undefined)).toBe(DEFAULT_PRIMARY_COLOR)
  })

  it('rejects colors that cannot support readable white button text', () => {
    expect(isReadablePrimaryColor('#ffffff')).toBe(false)
    expect(isReadablePrimaryColor('#ffff00')).toBe(false)
    expect(normalizePrimaryColor('#ffffff')).toBe(DEFAULT_PRIMARY_COLOR)
    expect(primaryColorContrast('#176b73')).toBeGreaterThanOrEqual(4.5)
    expect(isReadablePrimaryColor('#245c8a')).toBe(true)
  })

  it('derives a complete Element Plus color scale', () => {
    const variables = getPrimaryColorVariables('#2f6f4e')

    expect(variables['--color-primary']).toBe('#2f6f4e')
    expect(variables['--primary-rgb']).toBe('47, 111, 78')
    expect(variables['--el-color-primary-light-1']).toMatch(/^#[0-9a-f]{6}$/)
    expect(variables['--el-color-primary-light-9']).toMatch(/^#[0-9a-f]{6}$/)
    expect(variables['--el-color-primary-dark-2']).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('keeps every preset readable for both dark-surface text and white-text fills', () => {
    PRIMARY_COLOR_OPTIONS.forEach(({ value }) => {
      const variables = getPrimaryColorVariables(value, 'dark')

      expect(colorContrastRatio(variables['--color-primary'], '#24312c')).toBeGreaterThanOrEqual(4.5)
      expect(colorContrastRatio(variables['--color-primary-fill'], '#ffffff')).toBeGreaterThanOrEqual(4.5)
      expect(variables['--el-color-primary']).toBe(value)
    })
  })

  it('applies and resets theme variables on the document root', () => {
    applyPrimaryColor('#9a6238')

    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe('#9a6238')
    expect(document.documentElement.style.getPropertyValue('--primary-rgb')).toBe('154, 98, 56')

    resetPrimaryColor()
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe(DEFAULT_PRIMARY_COLOR)
  })

  it('normalizes theme modes and API time values', () => {
    expect(normalizeThemePreference({
      theme_mode: 'dark',
      schedule_start: '20:30:00',
      schedule_end: '06:15:00',
    })).toEqual({
      theme_mode: 'dark',
      schedule_start: '20:30',
      schedule_end: '06:15',
    })

    expect(normalizeThemePreference({
      theme_mode: 'schedule',
      schedule_start: '08:00',
      schedule_end: '08:00',
    })).toMatchObject({ schedule_start: '19:00', schedule_end: '07:00' })
  })

  it('resolves both daytime and overnight dark schedules', () => {
    expect(isWithinDarkSchedule(new Date(2026, 0, 1, 22, 0), '19:00', '07:00')).toBe(true)
    expect(isWithinDarkSchedule(new Date(2026, 0, 2, 6, 59), '19:00', '07:00')).toBe(true)
    expect(isWithinDarkSchedule(new Date(2026, 0, 2, 7, 0), '19:00', '07:00')).toBe(false)
    expect(isWithinDarkSchedule(new Date(2026, 0, 2, 12, 0), '09:00', '17:00')).toBe(true)
    expect(isWithinDarkSchedule(new Date(2026, 0, 2, 18, 0), '09:00', '17:00')).toBe(false)
  })

  it('resolves explicit and system theme preferences', () => {
    expect(resolveThemePreference({ theme_mode: 'light' }, new Date(), true)).toBe('light')
    expect(resolveThemePreference({ theme_mode: 'dark' }, new Date(), false)).toBe('dark')
    expect(resolveThemePreference({ theme_mode: 'system' }, new Date(), true)).toBe('dark')
    expect(resolveThemePreference({ theme_mode: 'system' }, new Date(), false)).toBe('light')
  })

  it('writes the resolved theme to the document and rebuilds the primary scale', () => {
    applyThemePreference({ theme_mode: 'light' })
    applyPrimaryColor('#2f6f4e')
    const lightScale = document.documentElement.style.getPropertyValue('--el-color-primary-light-9')

    applyThemePreference({ theme_mode: 'dark' })

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(document.documentElement.dataset.themeMode).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.style.colorScheme).toBe('dark')
    expect(document.documentElement.style.getPropertyValue('--color-primary-fill')).toBe('#2f6f4e')
    expect(document.documentElement.style.getPropertyValue('--el-color-primary')).toBe('#2f6f4e')
    expect(colorContrastRatio(
      document.documentElement.style.getPropertyValue('--color-primary'),
      '#24312c',
    )).toBeGreaterThanOrEqual(4.5)
    expect(document.documentElement.style.getPropertyValue('--el-color-primary-light-9')).not.toBe(lightScale)
  })

  it('reacts to system color-scheme changes and removes the listener when switching modes', () => {
    const { mediaQuery, setMatches } = createMediaQueryList(false)
    vi.stubGlobal('matchMedia', vi.fn(() => mediaQuery))

    applyThemePreference({ theme_mode: 'system' })
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(mediaQuery.addEventListener).toHaveBeenCalledWith('change', expect.any(Function))

    setMatches(true)
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    applyThemePreference({ theme_mode: 'light' })
    expect(mediaQuery.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
  })

  it('refreshes a scheduled theme at the exact next boundary', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 0, 1, 18, 59, 59, 0))

    expect(millisecondsUntilNextScheduleBoundary(
      new Date(),
      '19:00',
      '07:00',
    )).toBe(1_050)

    applyThemePreference({
      theme_mode: 'schedule',
      schedule_start: '19:00',
      schedule_end: '07:00',
    })
    expect(document.documentElement.dataset.theme).toBe('light')

    vi.advanceTimersByTime(1_049)
    expect(document.documentElement.dataset.theme).toBe('light')
    vi.advanceTimersByTime(1)
    expect(document.documentElement.dataset.theme).toBe('dark')
  })
})
