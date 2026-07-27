import { describe, expect, it } from 'vitest'
import { parseSearchTarget, positiveQueryId } from '../globalSearch'

describe('global search navigation', () => {
  it('preserves every query parameter in a search result URL', () => {
    expect(parseSearchTarget('/projects/12/operations?tab=knowledge&article_id=34')).toEqual({
      path: '/projects/12/operations',
      query: { tab: 'knowledge', article_id: '34' },
    })
  })

  it('keeps plain paths as strings', () => {
    expect(parseSearchTarget('/projects/12')).toBe('/projects/12')
  })

  it('accepts only positive integer object ids', () => {
    expect(positiveQueryId('7')).toBe(7)
    expect(positiveQueryId(['8'])).toBe(8)
    expect(positiveQueryId('0')).toBeNull()
    expect(positiveQueryId('bad')).toBeNull()
  })
})
