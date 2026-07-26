import { beforeEach, describe, expect, it } from 'vitest'
import {
  applyPrimaryColor,
  DEFAULT_PRIMARY_COLOR,
  getPrimaryColorVariables,
  isReadablePrimaryColor,
  normalizePrimaryColor,
  primaryColorContrast,
  resetPrimaryColor,
} from '@/utils/theme'

describe('theme utilities', () => {
  beforeEach(() => {
    document.documentElement.removeAttribute('style')
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

  it('applies and resets theme variables on the document root', () => {
    applyPrimaryColor('#9a6238')

    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe('#9a6238')
    expect(document.documentElement.style.getPropertyValue('--primary-rgb')).toBe('154, 98, 56')

    resetPrimaryColor()
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe(DEFAULT_PRIMARY_COLOR)
  })
})
