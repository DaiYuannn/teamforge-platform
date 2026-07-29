import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'


describe('competition award ledger', () => {
  it('shows multiple awards with date, recipients and CRUD actions in competition detail', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/competitions/CompetitionDetailDialog.vue'),
      'utf8',
    )

    expect(source).toContain('比赛成果与获奖记录')
    expect(source).toContain('award.award_date')
    expect(source).toContain('awardRecipientNames(award)')
    expect(source).toContain('createCompetitionAward')
    expect(source).toContain('updateCompetitionAward')
    expect(source).toContain('deleteCompetitionAward')
    expect(source).toContain('从本场比赛实际参赛名单选择')
  })
})
