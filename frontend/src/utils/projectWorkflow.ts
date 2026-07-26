import type { ProjectStage, ProjectStatus } from '@/types'
import { getStageLabel } from '@/utils/format'

export interface StageTargetOption {
  value: number
  label: string
  kind: 'next' | 'pause' | 'terminate'
}

export interface LeaderUpdateCadence {
  baseline: Date | null
  daysSinceUpdate: number
  isFirstUpdate: boolean
  isOverdue: boolean
}

const NORMAL_FINAL_STAGE = 14
const PAUSED_STAGE = 15
const TERMINATED_STAGE = 16
const LEADER_UPDATE_INTERVAL_DAYS = 11
const ONE_DAY = 24 * 60 * 60 * 1000

export function normalizeProjectStage(stage: ProjectStage | null | undefined): number {
  if (typeof stage === 'number') return stage
  const match = String(stage || '').match(/(\d+)$/)
  return match ? Number(match[1]) : 1
}

/**
 * 前端只开放不会跳过正常业务节点的阶段操作：
 * - 常规执行阶段可进入下一阶段，也可暂停或终止；
 * - 暂停项目只能按当前后端契约终止；
 * - 已结项、已终止或状态已关闭的项目不再提供推进操作。
 */
export function getLegalStageTargets(
  currentStage: ProjectStage,
  projectStatus: ProjectStatus = 'active',
): StageTargetOption[] {
  const current = normalizeProjectStage(currentStage)
  if (
    projectStatus === 'closed'
    || current === NORMAL_FINAL_STAGE
    || current >= TERMINATED_STAGE
  ) {
    return []
  }

  if (current === PAUSED_STAGE) {
    return [{
      value: TERMINATED_STAGE,
      label: getStageLabel(TERMINATED_STAGE),
      kind: 'terminate',
    }]
  }

  if (current < 1 || current > NORMAL_FINAL_STAGE) return []

  const targets: StageTargetOption[] = [
    {
      value: current + 1,
      label: `推进至 ${getStageLabel(current + 1)}`,
      kind: 'next',
    },
    {
      value: PAUSED_STAGE,
      label: getStageLabel(PAUSED_STAGE),
      kind: 'pause',
    },
    {
      value: TERMINATED_STAGE,
      label: getStageLabel(TERMINATED_STAGE),
      kind: 'terminate',
    },
  ]

  return targets.filter(
    (option, index, options) =>
      option.value !== current
      && options.findIndex((candidate) => candidate.value === option.value) === index,
  )
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null
  const normalized = value.length === 10 ? `${value}T00:00:00` : value
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return null
  date.setHours(0, 0, 0, 0)
  return date
}

/**
 * 首次负责人更新尚未发生时，从项目创建时间起算 11 天周期。
 */
export function getLeaderUpdateCadence(
  lastLeaderUpdate?: string | null,
  createdAt?: string | null,
  now = new Date(),
): LeaderUpdateCadence {
  const lastUpdateDate = parseDate(lastLeaderUpdate)
  const baseline = lastUpdateDate || parseDate(createdAt)
  if (!baseline) {
    return {
      baseline: null,
      daysSinceUpdate: 0,
      isFirstUpdate: !lastUpdateDate,
      isOverdue: false,
    }
  }

  const today = new Date(now)
  today.setHours(0, 0, 0, 0)
  const daysSinceUpdate = Math.max(
    0,
    Math.floor((today.getTime() - baseline.getTime()) / ONE_DAY),
  )

  return {
    baseline,
    daysSinceUpdate,
    isFirstUpdate: !lastUpdateDate,
    isOverdue: daysSinceUpdate >= LEADER_UPDATE_INTERVAL_DAYS,
  }
}
