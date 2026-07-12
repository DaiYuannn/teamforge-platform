<template>
  <div class="funnel-view">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :xs="24" :sm="8">
        <div class="stat-card stat-blue">
          <div class="stat-icon">
            <el-icon size="30"><Trophy /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ summary.totalCompetitions }}</div>
            <div class="stat-label">总比赛数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="stat-card stat-green">
          <div class="stat-icon">
            <el-icon size="30"><Promotion /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ summary.totalPromoted }}</div>
            <div class="stat-label">总晋级数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="stat-card stat-orange">
          <div class="stat-icon">
            <el-icon size="30"><Medal /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ summary.totalAwarded }}</div>
            <div class="stat-label">总获奖数</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 漏斗图 + 明细表格 -->
    <el-row :gutter="16" class="mt-16">
      <!-- 漏斗图 -->
      <el-col :xs="24" :lg="12">
        <div class="card">
          <h3 class="card-title">比赛晋级漏斗</h3>
          <div v-loading="loading" class="funnel-wrapper">
            <div v-if="!loading && funnelData.length > 0" class="funnel-container">
              <template v-for="(item, index) in funnelData" :key="item.level">
                <div
                  class="funnel-bar-wrapper"
                  :style="{ animationDelay: `${index * 0.1}s` }"
                  @mouseenter="hoveredLevel = item.level"
                  @mouseleave="hoveredLevel = null"
                >
                  <div class="funnel-bar" :style="barStyle(item, index)">
                    <div class="funnel-bar-label">
                      <el-tag
                        :type="getCompetitionStageTagType(item.level) as any"
                        size="small"
                        effect="dark"
                        :style="getCompetitionStageTagStyle(item.level)"
                      >
                        {{ item.level_display }}
                      </el-tag>
                    </div>
                    <div class="funnel-bar-count">{{ item.total }}</div>
                    <div class="funnel-bar-rate">{{ getPercentage(item) }}%</div>
                  </div>
                  <transition name="detail-fade">
                    <div v-if="hoveredLevel === item.level" class="funnel-detail">
                      <div class="detail-header">
                        <span class="detail-dot" :style="{ background: getCompetitionStageColor(item.level) }"></span>
                        {{ item.level_display }} 详细数据
                      </div>
                      <div class="detail-grid">
                        <div class="detail-item">
                          <span class="detail-label">参赛数</span>
                          <span class="detail-value">{{ item.total || '-' }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">晋级数</span>
                          <span class="detail-value detail-promoted">{{ item.promoted || '-' }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">晋级率</span>
                          <span class="detail-value">{{ formatRate(item.promotion_rate) }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">获奖数</span>
                          <span class="detail-value detail-awarded">{{ item.awarded || '-' }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">获奖率</span>
                          <span class="detail-value">{{ formatRate(item.award_rate) }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">进行中</span>
                          <span class="detail-value">{{ item.ongoing || '-' }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">已结束</span>
                          <span class="detail-value">{{ item.completed || '-' }}</span>
                        </div>
                      </div>
                    </div>
                  </transition>
                </div>
                <div v-if="index < funnelData.length - 1" class="funnel-connector">
                  <el-icon><ArrowDown /></el-icon>
                </div>
              </template>
            </div>
            <EmptyState v-if="!loading && funnelData.length === 0" text="暂无漏斗数据" icon="DataAnalysis" />
          </div>
        </div>
      </el-col>

      <!-- 明细表格 -->
      <el-col :xs="24" :lg="12">
        <div class="card">
          <h3 class="card-title">各级别晋级明细</h3>
          <el-table v-loading="loading" :data="funnelData" border stripe size="small" show-summary :summary-method="getSummary">
            <el-table-column label="级别" min-width="90">
              <template #default="{ row }">
                <el-tag
                  :type="getCompetitionStageTagType(row.level) as any"
                  size="small"
                  effect="light"
                  :style="getCompetitionStageTagStyle(row.level)"
                >
                  {{ row.level_display }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total" label="参赛数" width="80" align="center">
              <template #default="{ row }">
                <span class="num">{{ row.total || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="promoted" label="晋级数" width="80" align="center">
              <template #default="{ row }">
                <span class="num num-promoted">{{ row.promoted || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="promotion_rate" label="晋级率" width="90" align="center">
              <template #default="{ row }">
                <span :class="['num', rateClass(row.promotion_rate)]">{{ formatRate(row.promotion_rate) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="awarded" label="获奖数" width="80" align="center">
              <template #default="{ row }">
                <span class="num num-awarded">{{ row.awarded || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="award_rate" label="获奖率" width="90" align="center">
              <template #default="{ row }">
                <span :class="['num', rateClass(row.award_rate)]">{{ formatRate(row.award_rate) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="ongoing" label="进行中" width="80" align="center">
              <template #default="{ row }">
                <span class="num">{{ row.ongoing || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="completed" label="已结束" width="80" align="center">
              <template #default="{ row }">
                <span class="num">{{ row.completed || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { TableColumnCtx } from 'element-plus'
import { Trophy, Promotion, Medal, ArrowDown } from '@element-plus/icons-vue'
import { getCompetitionFunnel, type FunnelItem } from '@/api/dashboard'
import {
  getCompetitionStageColor,
  getCompetitionStageTagType,
  getCompetitionStageTagStyle,
} from '@/utils/format'
import EmptyState from '@/components/EmptyState.vue'

const loading = ref(false)
const funnelData = ref<FunnelItem[]>([])
const summary = ref({ totalCompetitions: 0, totalPromoted: 0, totalAwarded: 0 })
const hoveredLevel = ref<string | null>(null)

/** 比率格式化（兼容 0-1 与 0-100 两种返回） */
function formatRate(rate: number | null | undefined): string {
  if (rate === null || rate === undefined || Number.isNaN(rate)) return '-'
  const r = Number(rate)
  if (r === 0) return '0%'
  const percent = r > 1 ? r : r * 100
  return `${percent.toFixed(1)}%`
}

/** 比率高亮类 */
function rateClass(rate: number | null | undefined): string {
  if (rate === null || rate === undefined || Number.isNaN(rate)) return ''
  const r = Number(rate)
  const percent = r > 1 ? r : r * 100
  if (percent >= 50) return 'rate-high'
  if (percent >= 20) return 'rate-mid'
  return 'rate-low'
}

/**
 * 计算漏斗条样式
 * - 宽度基于该级别总数相对最大值的占比
 * - 背景使用级别颜色生成渐变
 * - 阴影使用级别颜色的半透明值营造发光效果
 */
function barStyle(item: FunnelItem, index: number): Record<string, string> {
  const maxTotal = Math.max(...funnelData.value.map((i) => i.total || 0), 1)
  const widthPercent = Math.max(((item.total || 0) / maxTotal) * 100, 20)
  const color = getCompetitionStageColor(item.level)
  const colorDark = darken(color, 0.22)
  const colorLight = lighten(color, 0.1)
  const angle = 120 + index * 5
  return {
    width: `${widthPercent}%`,
    background: `linear-gradient(${angle}deg, ${colorLight} 0%, ${color} 45%, ${colorDark} 100%)`,
    boxShadow: `0 6px 20px ${hexToRgba(color, 0.4)}, inset 0 1px 0 rgba(255, 255, 255, 0.25)`,
  }
}

/** 计算某级别参赛数占所有级别总数的百分比 */
function getPercentage(item: FunnelItem): string {
  const sum = funnelData.value.reduce((s, i) => s + (i.total || 0), 0)
  if (sum === 0) return '0'
  const pct = (item.total / sum) * 100
  return pct.toFixed(1)
}

/** 十六进制颜色变暗 */
function darken(hex: string, amount: number): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim())
  if (!m) return hex
  const r = Math.max(0, Math.round(parseInt(m[1], 16) - 255 * amount))
  const g = Math.max(0, Math.round(parseInt(m[2], 16) - 255 * amount))
  const b = Math.max(0, Math.round(parseInt(m[3], 16) - 255 * amount))
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`
}

/** 十六进制颜色变亮 */
function lighten(hex: string, amount: number): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim())
  if (!m) return hex
  const r = Math.min(255, Math.round(parseInt(m[1], 16) + 255 * amount))
  const g = Math.min(255, Math.round(parseInt(m[2], 16) + 255 * amount))
  const b = Math.min(255, Math.round(parseInt(m[3], 16) + 255 * amount))
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`
}

/** 十六进制转 rgba 字符串 */
function hexToRgba(hex: string, alpha: number): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim())
  if (!m) return `rgba(64, 158, 255, ${alpha})`
  const r = parseInt(m[1], 16)
  const g = parseInt(m[2], 16)
  const b = parseInt(m[3], 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/** 表尾汇总 */
function getSummary({ columns }: { columns: TableColumnCtx<FunnelItem>[]; data: FunnelItem[] }): string[] {
  const totalCompetitions = funnelData.value.reduce((s, i) => s + (i.total || 0), 0)
  const totalPromoted = funnelData.value.reduce((s, i) => s + (i.promoted || 0), 0)
  const totalAwarded = funnelData.value.reduce((s, i) => s + (i.awarded || 0), 0)
  const totalOngoing = funnelData.value.reduce((s, i) => s + (i.ongoing || 0), 0)
  const totalCompleted = funnelData.value.reduce((s, i) => s + (i.completed || 0), 0)
  const overallPromotionRate = totalCompetitions > 0 ? (totalPromoted / totalCompetitions) * 100 : 0
  const overallAwardRate = totalCompetitions > 0 ? (totalAwarded / totalCompetitions) * 100 : 0

  return columns.map((_, index) => {
    switch (index) {
      case 0:
        return '合计'
      case 1:
        return String(totalCompetitions)
      case 2:
        return String(totalPromoted)
      case 3:
        return `${overallPromotionRate.toFixed(1)}%`
      case 4:
        return String(totalAwarded)
      case 5:
        return `${overallAwardRate.toFixed(1)}%`
      case 6:
        return String(totalOngoing)
      case 7:
        return String(totalCompleted)
      default:
        return ''
    }
  })
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res = await getCompetitionFunnel()
    funnelData.value = res.funnel || []
    summary.value = {
      totalCompetitions: res.total_competitions || 0,
      totalPromoted: res.total_promoted || 0,
      totalAwarded: res.total_awarded || 0,
    }
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
    &.stat-green .stat-icon {
      background: linear-gradient(135deg, #67c23a, #95de64);
    }
    &.stat-orange .stat-icon {
      background: linear-gradient(135deg, #e6a23c, #ffd591);
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
  height: 100%;

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

/* ==================== 漏斗可视化 ==================== */
.funnel-wrapper {
  position: relative;
  width: 100%;
  min-height: 360px;
  padding: 8px 0;
  overflow: visible;
}

.funnel-container {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
  overflow: visible;
}

/* ---- 漏斗条容器 ---- */
.funnel-bar-wrapper {
  position: relative;
  width: 100%;
  animation: funnelSlideIn 0.5s cubic-bezier(0.22, 0.61, 0.36, 1) both;

  /* 透明桥接区域：确保鼠标从漏斗条移动到详情卡片时不触发 mouseleave */
  &::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    width: 90%;
    height: 14px;
    z-index: 99;
    display: none;
  }

  &:hover::after {
    display: block;
  }
}

@keyframes funnelSlideIn {
  from {
    opacity: 0;
    transform: translateX(-32px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* ---- 漏斗条 ---- */
.funnel-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 54px;
  margin: 0 auto;
  padding: 0 18px;
  border-radius: 10px;
  color: #fff;
  position: relative;
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  cursor: pointer;

  /* 顶部高光 */
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 50%;
    background: linear-gradient(to bottom, rgba(255, 255, 255, 0.2), transparent);
    pointer-events: none;
  }

  /* 流光动画 */
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 60%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
    animation: funnelShine 3.5s ease-in-out infinite;
    pointer-events: none;
  }
}

/* 悬停时漏斗条放大（通过 wrapper:hover 控制，保证鼠标在详情卡片上时也保持放大） */
.funnel-bar-wrapper:hover .funnel-bar {
  transform: scale(1.03);
  z-index: 10;
}

@keyframes funnelShine {
  0%,
  100% {
    left: -100%;
  }
  50% {
    left: 130%;
  }
}

/* ---- 漏斗条内容 ---- */
.funnel-bar-label {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  z-index: 1;

  :deep(.el-tag) {
    background: rgba(255, 255, 255, 0.22) !important;
    backdrop-filter: blur(6px);
    border: 1px solid rgba(255, 255, 255, 0.35) !important;
    color: #fff !important;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
}

.funnel-bar-count {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  z-index: 1;
}

.funnel-bar-rate {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  font-variant-numeric: tabular-nums;
  z-index: 1;
  background: rgba(255, 255, 255, 0.2);
  padding: 3px 10px;
  border-radius: 12px;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

/* ---- 连接线 ---- */
.funnel-connector {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 32px;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    width: 2px;
    height: 100%;
    background: linear-gradient(to bottom, #dcdfe6, #c0c4cc);
  }

  .el-icon {
    position: relative;
    z-index: 1;
    font-size: 16px;
    color: #909399;
    background: #fff;
    border: 1.5px solid #dcdfe6;
    border-radius: 50%;
    padding: 2px;
    animation: connectorBounce 2s ease-in-out infinite;
  }
}

@keyframes connectorBounce {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(3px);
  }
}

/* ---- 悬停详情卡片 ---- */
.funnel-detail {
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  width: 92%;
  max-width: 440px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.12);
  padding: 14px 16px;
  z-index: 100;

  .detail-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid #f0f0f0;
  }

  .detail-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.05);
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px 12px;
  }

  .detail-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 6px 4px;
    background: #f7f9fc;
    border-radius: 6px;
    transition: background 0.2s ease;

    &:hover {
      background: #ecf5ff;
    }

    .detail-label {
      font-size: 11px;
      color: #909399;
    }

    .detail-value {
      font-size: 16px;
      font-weight: 700;
      color: #303133;
      font-variant-numeric: tabular-nums;

      &.detail-promoted {
        color: #67c23a;
      }

      &.detail-awarded {
        color: #e6a23c;
      }
    }
  }
}

/* 详情卡片淡入淡出动画 */
.detail-fade-enter-active,
.detail-fade-leave-active {
  transition: all 0.25s ease;
}

.detail-fade-enter-from,
.detail-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-6px);
}

/* ==================== 表格数字 ==================== */
.num {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
  color: #303133;

  &.num-promoted {
    color: #67c23a;
    font-weight: 600;
  }

  &.num-awarded {
    color: #e6a23c;
    font-weight: 600;
  }
}

.rate-high {
  color: #67c23a;
  font-weight: 600;
}

.rate-mid {
  color: #e6a23c;
}

.rate-low {
  color: #909399;
}

/* 表尾汇总行 */
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

  .funnel-bar {
    height: 46px;
    padding: 0 12px;
  }

  .funnel-bar-count {
    font-size: 18px;
  }

  .funnel-bar-rate {
    font-size: 12px;
    padding: 2px 8px;
  }

  .funnel-detail {
    width: 100%;
    max-width: none;

    .detail-grid {
      grid-template-columns: repeat(3, 1fr);
    }
  }
}
</style>
