import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: getMock,
}))

import {
  getSkillRecommendations,
  getTeamSkillMatrix,
} from '@/api/skillMatrix'

beforeEach(() => {
  vi.clearAllMocks()
  getMock.mockResolvedValue({})
})

describe('skill matrix API contract', () => {
  it('keeps all partial-match filters in one matrix request', async () => {
    await getTeamSkillMatrix({
      search: '  LYC ',
      school: ' 示例大学 ',
      major: '计算机',
      team_role: 'member',
      member_status: 'active',
      skill: 'yth',
      min_proficiency: 4,
      competition_event: 5,
      competition_entry: 11,
    })

    expect(getMock).toHaveBeenCalledWith('/skill-matrix/matrix/', {
      search: 'LYC',
      school: '示例大学',
      major: '计算机',
      team_role: 'member',
      member_status: 'active',
      skill: 'yth',
      min_proficiency: 4,
      competition_event: 5,
      competition_entry: 11,
    })
  })

  it('serializes selected skill ids for one exact competition entry', async () => {
    await getSkillRecommendations({
      competition_event: 5,
      competition_entry: 11,
      required_skill_ids: [2, 7],
      min_proficiency: 3,
    })

    expect(getMock).toHaveBeenCalledWith(
      '/skill-matrix/recommendations/',
      {
        competition_event: 5,
        competition_entry: 11,
        required_skill_ids: '2,7',
        min_proficiency: 3,
      },
    )
  })
})
