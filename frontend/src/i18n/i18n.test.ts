import { beforeEach, describe, expect, it } from 'vitest'
import { setLocale, translate } from './index'

describe('runtime internationalization', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('zh-CN')
  })

  it('switches translated UI text and persists the locale', () => {
    setLocale('en')
    expect(translate('登录')).toBe('Sign In')
    expect(translate('项目管理')).toBe('Projects')
    expect(localStorage.getItem('app_locale')).toBe('en')
    expect(document.documentElement.lang).toBe('en')
  })

  it('falls back to the source text for an untranslated key', () => {
    setLocale('en')
    expect(translate('业务专有文本')).toBe('业务专有文本')
  })
})
