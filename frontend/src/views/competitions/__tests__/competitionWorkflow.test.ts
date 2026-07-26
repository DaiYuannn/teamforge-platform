import { describe, expect, it } from 'vitest'
import {
  parseCompetitionProjectQuery,
  toCompetitionExportParams,
} from '../competitionWorkflow'

describe('competition list workflow helpers', () => {
  it('maps a valid project_id deep link to the existing project filter', () => {
    expect(parseCompetitionProjectQuery('42')).toBe(42)
    expect(parseCompetitionProjectQuery([null, '17'])).toBe(17)
    expect(parseCompetitionProjectQuery('0')).toBeUndefined()
    expect(parseCompetitionProjectQuery('-3')).toBeUndefined()
    expect(parseCompetitionProjectQuery('not-an-id')).toBeUndefined()
  })

  it('keeps business filters and drops pagination from an Excel export', () => {
    expect(toCompetitionExportParams({
      page: 7,
      page_size: 10,
      ordering: '-created_at',
      search: '  挑战杯  ',
      project: 12,
      level: 'national',
      status: 'completed',
    })).toEqual({
      search: '挑战杯',
      project: 12,
      level: 'national',
      status: 'completed',
    })
  })
})
