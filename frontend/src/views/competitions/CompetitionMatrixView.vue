<template>
  <div class="matrix-view">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :xs="24" :sm="8">
        <div class="stat-card stat-blue">
          <div class="stat-icon">
            <el-icon size="30"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ grandTotal.total }}</div>
            <div class="stat-label">总参赛数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="stat-card stat-orange">
          <div class="stat-icon">
            <el-icon size="30"><Trophy /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ grandTotal.awarded }}</div>
            <div class="stat-label">总获奖数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="stat-card stat-green">
          <div class="stat-icon">
            <el-icon size="30"><Promotion /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ grandTotal.promoted }}</div>
            <div class="stat-label">总晋级数</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 矩阵表格 -->
    <div class="card mt-16">
      <h3 class="card-title">项目 × 比赛级别 参赛矩阵</h3>
      <el-table
        v-loading="loading"
        :data="matrix"
        border
        stripe
        show-summary
        :summary-method="getSummary"
        :cell-class-name="cellClassName"
        size="small"
      >
        <template #empty>
          <EmptyState text="暂无参赛矩阵数据" description="项目参赛后将在此展示" accent="#9B59B6" />
        </template>
        <el-table-column label="项目名称" fixed min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="project-cell">
              <span class="project-name">{{ row.project_name }}</span>
              <span class="project-code">{{ row.project_code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          v-for="(level, idx) in levels"
          :key="level.key"
          :label="level.name"
          align="center"
          min-width="120"
        >
          <template #header>
            <div class="level-header">
              <span class="level-dot" :style="{ background: getCompetitionStageColor(level.key) }"></span>
              {{ level.name }}
            </div>
          </template>
          <template #default="{ row }">
            <el-tooltip
              v-if="getCell(row, idx) && getCell(row, idx)!.total > 0"
              :content="tooltipContent(getCell(row, idx)!)"
              placement="top"
            >
              <span class="cell-text">{{ formatCell(getCell(row, idx)) }}</span>
            </el-tooltip>
            <span v-else class="cell-text cell-empty">-</span>
          </template>
        </el-table-column>
        <el-table-column label="合计" fixed="right" align="center" min-width="130">
          <template #default="{ row }">
            <el-tooltip
              v-if="getRowTotal(row).total > 0"
              :content="tooltipContent(getRowTotal(row))"
              placement="top"
            >
              <span class="cell-text cell-total">{{ formatTotal(getRowTotal(row)) }}</span>
            </el-tooltip>
            <span v-else class="cell-text cell-empty">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 图例说明 -->
      <div class="legend">
        <span class="legend-item">
          <span class="legend-swatch legend-sw-1"></span>单元格格式：参赛数(获奖数/晋级数)
        </span>
        <span class="legend-item">
          <span class="legend-swatch legend-sw-2"></span>浅色背景表示有参赛记录
        </span>
        <span class="legend-item">0 显示为 "-"</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { TrendCharts, Trophy, Promotion } from '@element-plus/icons-vue'
import type { TableColumnCtx } from 'element-plus'
import { getCompetitionMatrix, type CompetitionMatrixData, type CompetitionMatrixCell, type CompetitionMatrixRow } from '@/api/dashboard'
import { getCompetitionStageColor } from '@/utils/format'
import EmptyState from '@/components/EmptyState.vue'

const loading = ref(false)
const matrixData = ref<CompetitionMatrixData | null>(null)

const levels = computed(() => matrixData.value?.levels || [])
const matrix = computed(() => matrixData.value?.matrix || [])
const levelKeys = computed(() => levels.value.map((l) => l.key))

/** 单元格汇总结构 */
interface CellSummary {
  total: number
  awarded: number
  promoted: number
}

/** 获取某行某级别的单元格（row 来自 el-table 插槽，类型较宽，内部断言为强类型） */
function getCell(row: any, idx: number): CompetitionMatrixCell | undefined {
  const key = levelKeys.value[idx]
  return key ? (row as CompetitionMatrixRow).cells[key] : undefined
}

/** 格式化单元格：参赛数(获奖数/晋级数)，0 显示为 "-" */
function formatCell(cell?: CompetitionMatrixCell): string {
  if (!cell || cell.total === 0) return '-'
  return `${cell.total}(${cell.awarded}/${cell.promoted})`
}

/** 格式化汇总单元格 */
function formatTotal(t: CellSummary): string {
  if (t.total === 0) return '-'
  return `${t.total}(${t.awarded}/${t.promoted})`
}

/** tooltip 内容 */
function tooltipContent(t: CellSummary): string {
  return `参赛数：${t.total}　获奖数：${t.awarded}　晋级数：${t.promoted}`
}

/** 计算某行合计（row 来自 el-table 插槽，类型较宽，内部断言为强类型） */
function getRowTotal(row: any): CellSummary {
  const typedRow = row as CompetitionMatrixRow
  let total = 0
  let awarded = 0
  let promoted = 0
  for (const key of levelKeys.value) {
    const cell = typedRow.cells[key]
    if (cell) {
      total += cell.total
      awarded += cell.awarded
      promoted += cell.promoted
    }
  }
  return { total, awarded, promoted }
}

/** 总计（所有级别汇总） */
const grandTotal = computed<CellSummary>(() => {
  let total = 0
  let awarded = 0
  let promoted = 0
  const totals = matrixData.value?.level_totals || {}
  for (const key of levelKeys.value) {
    const t = totals[key]
    if (t) {
      total += t.total
      awarded += t.awarded
      promoted += t.promoted
    }
  }
  return { total, awarded, promoted }
})

/** 表尾汇总行 */
function getSummary({ columns }: { columns: TableColumnCtx<CompetitionMatrixRow>[]; data: CompetitionMatrixRow[] }): string[] {
  const totals = matrixData.value?.level_totals || {}
  const result: string[] = []
  columns.forEach((_, index) => {
    if (index === 0) {
      result.push('合计')
      return
    }
    // 级别列：index 1 .. levelKeys.length
    if (index >= 1 && index <= levelKeys.value.length) {
      const key = levelKeys.value[index - 1]
      const t = totals[key]
      result.push(t ? formatTotal(t) : '-')
      return
    }
    // 合计列（最后一列）
    result.push(formatTotal(grandTotal.value))
  })
  return result
}

/** 单元格高亮类名 */
function cellClassName({
  row,
  columnIndex,
}: {
  row: CompetitionMatrixRow
  column: TableColumnCtx<CompetitionMatrixRow>
  rowIndex: number
  columnIndex: number
}): string {
  // 级别列
  if (columnIndex >= 1 && columnIndex <= levelKeys.value.length) {
    const cell = getCell(row, columnIndex - 1)
    if (cell && cell.total > 0) return 'cell-has-data'
  }
  // 合计列
  if (columnIndex === levelKeys.value.length + 1) {
    if (getRowTotal(row).total > 0) return 'cell-has-data cell-has-data-total'
  }
  return ''
}

// 加载矩阵数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    matrixData.value = await getCompetitionMatrix()
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.mt-16 {
  margin-top: 16px;
}

/* ==================== 统计卡片 ==================== */
.stat-cards {
  display: flex;
  flex-wrap: wrap;

  > .el-col {
    margin-bottom: 16px;
  }

  .stat-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 18px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    min-height: 100px;

    .stat-icon {
      width: 52px;
      height: 52px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      flex-shrink: 0;
    }

    &.stat-blue .stat-icon {
      background: linear-gradient(135deg, #409eff, #36cfc9);
    }
    &.stat-orange .stat-icon {
      background: linear-gradient(135deg, #e6a23c, #ffd591);
    }
    &.stat-green .stat-icon {
      background: linear-gradient(135deg, #67c23a, #95de64);
    }

    .stat-info {
      .stat-value {
        font-size: 26px;
        font-weight: 700;
        color: #303133;
        font-variant-numeric: tabular-nums;
      }

      .stat-label {
        font-size: 13px;
        color: #909399;
        margin-top: 4px;
      }
    }
  }
}

/* ==================== 卡片 ==================== */
.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);

  .card-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
    display: flex;
    align-items: center;

    &::before {
      content: '';
      width: 4px;
      height: 16px;
      background: #409eff;
      border-radius: 2px;
      margin-right: 8px;
    }
  }
}

/* ==================== 表格单元格 ==================== */
.project-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.4;

  .project-name {
    font-weight: 500;
    color: #303133;
  }

  .project-code {
    font-size: 12px;
    color: #909399;
  }
}

.level-header {
  font-weight: 600;
  color: #303133;
  display: inline-flex;
  align-items: center;
  gap: 6px;

  .level-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
}

.cell-text {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
  color: #303133;

  &.cell-empty {
    color: #c0c4cc;
  }

  &.cell-total {
    font-weight: 600;
    color: #409eff;
  }
}

/* 有数据的单元格高亮（el-table 内部 td，需穿透） */
:deep(.cell-has-data) {
  background-color: #ecf5ff !important;

  &.cell-has-data-total {
    background-color: #e1f3d8 !important;
  }
}

/* 表尾汇总行加粗 */
:deep(.el-table__footer-wrapper) {
  .cell {
    font-weight: 600;
    color: #303133;
    font-variant-numeric: tabular-nums;
  }
  td.el-table__cell {
    background-color: #fafafa !important;
  }
}

/* ==================== 图例 ==================== */
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 14px;
  padding: 10px 4px 0;
  font-size: 12px;
  color: #909399;

  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .legend-swatch {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #e4e7ed;
  }

  .legend-sw-1 {
    background: #fff;
    border: 1px solid #dcdfe6;
  }

  .legend-sw-2 {
    background: #ecf5ff;
    border-color: #d9ecff;
  }
}

/* ==================== 移动端适配 ==================== */
@media screen and (max-width: 768px) {
  .stat-cards {
    .stat-card {
      padding: 12px 14px;
      gap: 10px;
      min-height: 86px;

      .stat-icon {
        width: 42px;
        height: 42px;
      }

      .stat-info {
        .stat-value {
          font-size: 20px;
        }
      }
    }
  }

  .legend {
    gap: 12px;
  }
}
</style>
