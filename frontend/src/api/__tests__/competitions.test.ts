import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  getMock,
  postMock,
  patchMock,
  deleteMock,
  downloadMock,
} = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  patchMock: vi.fn(),
  deleteMock: vi.fn(),
  downloadMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: getMock,
  post: postMock,
  patch: patchMock,
  del: deleteMock,
  download: downloadMock,
}))

import {
  addCompetitionParticipant,
  createCompetitionAward,
  deleteCompetitionAward,
  deleteCompetitionParticipant,
  exportCompetitions,
  getCompetitionAwards,
  getCompetitionEvents,
  getCompetitionParticipantCandidates,
  getCompetitions,
  updateCompetitionParticipant,
  updateCompetitionAward,
} from '@/api/competitions'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('competition export API contract', () => {
  it('exports the complete current list filter without pagination', async () => {
    const blob = new Blob(['competition'])
    downloadMock.mockResolvedValueOnce(blob)

    await expect(exportCompetitions({
      search: '挑战杯',
      project: 23,
      level: 'province',
      status: 'ongoing',
    })).resolves.toBe(blob)

    expect(downloadMock).toHaveBeenCalledWith('/exports/', {
      params: {
        type: 'competitions',
        file_format: 'xlsx',
        search: '挑战杯',
        project_id: 23,
        level: 'province',
        status: 'ongoing',
      },
    })
  })
})

describe('competition organization API contract', () => {
  it('loads competition editions and their project entries', async () => {
    getMock.mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })

    await getCompetitionEvents({ page: 1, page_size: 100 })
    await getCompetitions({ event: 12, page: 1, page_size: 100 })

    expect(getMock).toHaveBeenNthCalledWith(
      1,
      '/competitions/events/',
      { page: 1, page_size: 100 },
    )
    expect(getMock).toHaveBeenNthCalledWith(
      2,
      '/competitions/',
      { event: 12, page: 1, page_size: 100 },
    )
  })

  it('passes one-character search and all related member filters together', async () => {
    getMock.mockResolvedValue([])

    await getCompetitionParticipantCandidates(31, {
      search: '刘',
      school: '示范大学',
      team_role: 'co_lead',
      membership_status: 'active',
    })

    expect(getMock).toHaveBeenCalledWith(
      '/competitions/31/participant-candidates/',
      {
        search: '刘',
        school: '示范大学',
        team_role: 'co_lead',
        membership_status: 'active',
      },
    )
  })

  it('reuses the existing participant write endpoints', async () => {
    postMock.mockResolvedValue({})
    patchMock.mockResolvedValue({})
    deleteMock.mockResolvedValue(undefined)

    await addCompetitionParticipant(31, {
      user: 8,
      role: 'member',
      participation_status: 'planned',
    })
    await updateCompetitionParticipant(31, 44, {
      role: 'leader',
      participation_status: 'confirmed',
      responsibility: '答辩主讲',
    })
    await deleteCompetitionParticipant(31, 44)

    expect(postMock).toHaveBeenCalledWith(
      '/competitions/31/participants/',
      {
        user: 8,
        role: 'member',
        participation_status: 'planned',
      },
    )
    expect(patchMock).toHaveBeenCalledWith(
      '/competitions/31/participants/',
      {
        participant_id: 44,
        role: 'leader',
        participation_status: 'confirmed',
        responsibility: '答辩主讲',
      },
    )
    expect(deleteMock).toHaveBeenCalledWith(
      '/competitions/31/participants/?participant_id=44',
    )
  })
})

describe('competition award ledger API contract', () => {
  it('supports listing, creating, editing and deleting individual awards', async () => {
    getMock.mockResolvedValue([])
    postMock.mockResolvedValue({})
    patchMock.mockResolvedValue({})
    deleteMock.mockResolvedValue(undefined)
    const payload = {
      award_name: '全国一等奖',
      award_level: '一等奖',
      award_date: '2026-07-20',
      recipients: [8, 9],
      notes: '现场总决赛',
    }

    await getCompetitionAwards(31)
    await createCompetitionAward(31, payload)
    await updateCompetitionAward(31, 7, { award_level: '金奖' })
    await deleteCompetitionAward(31, 7)

    expect(getMock).toHaveBeenCalledWith('/competitions/31/award_tracking/')
    expect(postMock).toHaveBeenCalledWith('/competitions/31/award_tracking/', payload)
    expect(patchMock).toHaveBeenCalledWith(
      '/competitions/31/awards/7/',
      { award_level: '金奖' },
    )
    expect(deleteMock).toHaveBeenCalledWith('/competitions/31/awards/7/')
  })
})
