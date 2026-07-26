<template>
  <div class="matrix-view">
    <section class="summary-band" aria-label="参赛矩阵汇总">
      <div class="summary-band__intro">
        <span>矩阵概览</span>
        <strong>按项目与赛事级别交叉比较</strong>
      </div>
      <dl class="summary-band__metrics">
        <div>
          <dt>参赛</dt>
          <dd>{{ grandTotal.total }}</dd>
        </div>
        <div>
          <dt>晋级</dt>
          <dd>{{ grandTotal.promoted }}</dd>
        </div>
        <div>
          <dt>获奖</dt>
          <dd>{{ grandTotal.awarded }}</dd>
        </div>
      </dl>
    </section>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="参赛矩阵暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <section class="matrix-surface" aria-labelledby="matrix-title">
      <header class="section-heading">
        <div>
          <h2 id="matrix-title">项目参赛矩阵</h2>
          <p>同一行比较项目在不同级别赛事中的参赛、获奖与晋级数量</p>
        </div>
        <span class="matrix-count">{{ matrix.length }} 个项目</span>
      </header>

      <el-table
        v-loading="loading"
        :data="matrix"
        border
        show-summary
        :summary-method="getSummary"
        :cell-class-name="cellClassName"
        size="small"
        table-layout="fixed"
      >
        <template #empty>
          <EmptyState
            v-if="!loading"
            text="暂无参赛矩阵数据"
            description="项目关联比赛后，比较结果会显示在这里"
          />
        </template>

        <el-table-column label="项目" fixed min-width="210" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="project-cell">
              <strong>{{ row.project_name }}</strong>
              <span>{{ row.project_code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          v-for="(level, index) in levels"
          :key="level.key"
          :label="level.name"
          align="center"
          min-width="116"
        >
          <template #header>
            <div class="level-header">
              <span
                class="level-dot"
                :style="{ backgroundColor: getCompetitionStageColor(level.key) }"
              />
              <span>{{ level.name }}</span>
            </div>
          </template>
          <template #default="{ row }">
            <el-tooltip
              v-if="getCell(row as CompetitionMatrixRow, index)?.total"
              :content="tooltipContent(getCell(row as CompetitionMatrixRow, index)!)"
              placement="top"
            >
              <span class="cell-value">
                {{ formatCell(getCell(row as CompetitionMatrixRow, index)) }}
              </span>
            </el-tooltip>
            <span v-else class="cell-value is-empty">-</span>
          </template>
        </el-table-column>
        <el-table-column label="合计" fixed="right" align="center" min-width="124">
          <template #default="{ row }">
            <el-tooltip
              v-if="getRowTotal(row as CompetitionMatrixRow).total"
              :content="tooltipContent(getRowTotal(row as CompetitionMatrixRow))"
              placement="top"
            >
              <span class="cell-value is-total">
                {{ formatCell(getRowTotal(row as CompetitionMatrixRow)) }}
              </span>
            </el-tooltip>
            <span v-else class="cell-value is-empty">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="matrix-legend" aria-label="矩阵数据说明">
        <span><i class="legend-swatch" />有参赛记录</span>
        <span>数字顺序：参赛 / 获奖 / 晋级</span>
        <span>“-” 表示暂无记录</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { TableColumnCtx } from 'element-plus'
import {
  getCompetitionMatrix,
  type CompetitionMatrixCell,
  type CompetitionMatrixData,
  type CompetitionMatrixRow,
} from '@/api/dashboard'
import { getCompetitionStageColor } from '@/utils/format'
import EmptyState from '@/components/EmptyState.vue'

interface CellSummary {
  total: number
  awarded: number
  promoted: number
}

const loading = ref(false)
const loadFailed = ref(false)
const matrixData = ref<CompetitionMatrixData | null>(null)

const levels = computed(() => matrixData.value?.levels || [])
const matrix = computed(() => matrixData.value?.matrix || [])
const levelKeys = computed(() => levels.value.map((level) => level.key))

const grandTotal = computed<CellSummary>(() => {
  const totals = matrixData.value?.level_totals || {}
  return levelKeys.value.reduce<CellSummary>(
    (result, key) => {
      const item = totals[key]
      if (item) {
        result.total += item.total
        result.awarded += item.awarded
        result.promoted += item.promoted
      }
      return result
    },
    { total: 0, awarded: 0, promoted: 0 },
  )
})

function getCell(row: CompetitionMatrixRow, index: number): CompetitionMatrixCell | undefined {
  const key = levelKeys.value[index]
  return key ? row.cells[key] : undefined
}

function getRowTotal(row: CompetitionMatrixRow): CellSummary {
  return levelKeys.value.reduce<CellSummary>(
    (result, key) => {
      const item = row.cells[key]
      if (item) {
        result.total += item.total
        result.awarded += item.awarded
        result.promoted += item.promoted
      }
      return result
    },
    { total: 0, awarded: 0, promoted: 0 },
  )
}

function formatCell(cell?: CellSummary): string {
  return !cell || cell.total === 0 ? '-' : `${cell.total} / ${cell.awarded} / ${cell.promoted}`
}

function tooltipContent(cell: CellSummary): string {
  return `参赛 ${cell.total}，获奖 ${cell.awarded}，晋级 ${cell.promoted}`
}

function getSummary({
  columns,
}: {
  columns: TableColumnCtx<CompetitionMatrixRow>[]
  data: CompetitionMatrixRow[]
}): string[] {
  const totals = matrixData.value?.level_totals || {}
  return columns.map((_, index) => {
    if (index === 0) return '合计'
    if (index <= levelKeys.value.length) {
      return formatCell(totals[levelKeys.value[index - 1]])
    }
    return formatCell(grandTotal.value)
  })
}

function cellClassName({
  row,
  columnIndex,
}: {
  row: CompetitionMatrixRow
  column: TableColumnCtx<CompetitionMatrixRow>
  rowIndex: number
  columnIndex: number
}): string {
  if (columnIndex >= 1 && columnIndex <= levelKeys.value.length) {
    return getCell(row, columnIndex - 1)?.total ? 'matrix-cell-has-data' : ''
  }
  if (columnIndex === levelKeys.value.length + 1) {
    return getRowTotal(row).total ? 'matrix-cell-has-data matrix-cell-total' : ''
  }
  return ''
}

async function loadData(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    matrixData.value = await getCompetitionMatrix()
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.matrix-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-band {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.summary-band__intro {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  strong {
    margin-top: 2px;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
  }
}

.summary-band__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(82px, 1fr));
  min-width: 294px;

  > div {
    padding: 2px 18px;
    text-align: right;
    border-left: 1px solid var(--color-border-light);
  }

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 2px;
    color: var(--color-text);
    font-size: 22px;
    font-weight: 600;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
  }
}

.matrix-surface {
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border-light);

  h2 {
    color: var(--color-text);
    font-size: 16px;
    font-weight: 600;
    line-height: 1.4;
    letter-spacing: 0;
  }

  p {
    margin-top: 3px;
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.matrix-count {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.project-cell {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;

  strong {
    overflow: hidden;
    color: var(--color-text);
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.level-header {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--color-text-regular);
  font-weight: 600;
}

.level-dot {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
}

.cell-value {
  color: var(--color-text-regular);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;

  &.is-empty {
    color: var(--text-placeholder);
  }

  &.is-total {
    color: var(--color-primary);
    font-weight: 600;
  }
}

:deep(.matrix-cell-has-data) {
  background: var(--color-primary-soft) !important;

  &.matrix-cell-total {
    background: var(--success-light) !important;
  }
}

:deep(.el-table__footer-wrapper) {
  .cell {
    color: var(--color-text);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  td.el-table__cell {
    background: var(--color-surface-subtle) !important;
  }
}

.matrix-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 22px;
  padding: 12px 18px;
  color: var(--color-text-muted);
  font-size: 11px;
  border-top: 1px solid var(--color-border-light);

  span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
}

.legend-swatch {
  width: 12px;
  height: 12px;
  background: var(--color-primary-soft);
  border: 1px solid var(--color-border);
  border-radius: 3px;
}

@media screen and (max-width: 768px) {
  .summary-band {
    flex-direction: column;
    gap: 12px;
    padding: 14px;
  }

  .summary-band__metrics {
    width: 100%;
    min-width: 0;

    > div {
      padding: 2px 12px;

      &:first-child {
        padding-left: 0;
        border-left: 0;
      }
    }

    dd {
      font-size: 19px;
    }
  }

  .section-heading {
    align-items: flex-start;
    padding: 14px;
  }

  .matrix-legend {
    padding: 12px 14px;
  }
}
</style>
