import { describe, expect, it } from 'vitest'
import {
  getLeaderUpdateCadence,
  getLegalStageTargets,
  normalizeProjectStage,
} from '@/utils/projectWorkflow'

describe('project workflow stage targets', () => {
  it('normalizes both numeric and serialized stage values', () => {
    expect(normalizeProjectStage(7)).toBe(7)
    expect(normalizeProjectStage('stage_08')).toBe(8)
  })

  it('offers only the next normal stage plus pause and termination', () => {
    expect(getLegalStageTargets(7, 'active')).toEqual([
      { value: 8, label: '推进至 答辩准备', kind: 'next' },
      { value: 15, label: '暂停', kind: 'pause' },
      { value: 16, label: '终止', kind: 'terminate' },
    ])
  })

  it('does not offer workflow writes after closing or termination', () => {
    expect(getLegalStageTargets(14, 'closed')).toEqual([])
    expect(getLegalStageTargets(16, 'active')).toEqual([])
  })

  it('does not expose an invalid backward resume from the paused stage', () => {
    expect(getLegalStageTargets(15, 'paused')).toEqual([
      { value: 16, label: '终止', kind: 'terminate' },
    ])
  })
})

describe('leader update cadence', () => {
  it('starts the 11-day cycle at project creation when no update exists', () => {
    const cadence = getLeaderUpdateCadence(
      null,
      '2026-07-01T16:30:00+08:00',
      new Date('2026-07-12T09:00:00+08:00'),
    )

    expect(cadence.isFirstUpdate).toBe(true)
    expect(cadence.daysSinceUpdate).toBe(11)
    expect(cadence.isOverdue).toBe(true)
  })

  it('uses the latest leader update instead of project creation', () => {
    const cadence = getLeaderUpdateCadence(
      '2026-07-10T11:00:00+08:00',
      '2026-06-01T08:00:00+08:00',
      new Date('2026-07-15T20:00:00+08:00'),
    )

    expect(cadence.isFirstUpdate).toBe(false)
    expect(cadence.daysSinceUpdate).toBe(5)
    expect(cadence.isOverdue).toBe(false)
  })
})
