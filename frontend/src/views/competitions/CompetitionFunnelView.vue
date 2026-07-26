<template>
  <div class="funnel-view">
    <section class="summary-band" aria-label="比赛晋级汇总">
      <div class="summary-band__intro">
        <span>晋级概览</span>
        <strong>从参赛规模到晋级与获奖结果</strong>
      </div>
      <dl class="summary-band__metrics">
        <div>
          <dt>比赛</dt>
          <dd>{{ summary.totalCompetitions }}</dd>
        </div>
        <div>
          <dt>晋级</dt>
          <dd>{{ summary.totalPromoted }}</dd>
        </div>
        <div>
          <dt>获奖</dt>
          <dd>{{ summary.totalAwarded }}</dd>
        </div>
      </dl>
    </section>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="晋级数据暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <section v-loading="loading" class="funnel-surface" aria-labelledby="funnel-title">
      <header class="section-heading">
        <div>
          <h2 id="funnel-title">各级别转化情况</h2>
          <p>按比赛级别汇总参赛、晋级、获奖与进度状态</p>
        </div>
        <span class="level-count">{{ funnelData.length }} 个级别</span>
      </header>

      <div v-if="!loading && funnelData.length" class="stage-list" role="list">
        <article
          v-for="(item, index) in funnelData"
          :key="item.level"
          class="stage-row"
          role="listitem"
        >
          <div class="stage-identity">
            <span class="stage-index">{{ formatStageIndex(index) }}</span>
            <span
              class="stage-dot"
              :style="{ backgroundColor: getCompetitionStageColor(item.level) }"
              aria-hidden="true"
            />
            <div>
              <strong>{{ item.level_display }}</strong>
              <span>{{ getPercentage(item) }}% 的参赛量</span>
            </div>
          </div>

          <div class="stage-volume">
            <div class="stage-volume__label">
              <span>参赛规模</span>
              <strong>{{ item.total }}</strong>
            </div>
            <div
              class="stage-track"
              role="img"
              :aria-label="`${item.level_display}参赛 ${item.total} 项`"
            >
              <span :style="stageBarStyle(item)" />
            </div>
          </div>

          <dl class="stage-metrics">
            <div>
              <dt>晋级</dt>
              <dd>
                <strong>{{ item.promoted }}</strong>
                <span :class="rateTone(item.promotion_rate)">
                  {{ formatRate(item.promotion_rate) }}
                </span>
              </dd>
            </div>
            <div>
              <dt>获奖</dt>
              <dd>
                <strong>{{ item.awarded }}</strong>
                <span :class="rateTone(item.award_rate)">{{ formatRate(item.award_rate) }}</span>
              </dd>
            </div>
            <div>
              <dt>进行中</dt>
              <dd><strong>{{ item.ongoing }}</strong></dd>
            </div>
            <div>
              <dt>已结束</dt>
              <dd><strong>{{ item.completed }}</strong></dd>
            </div>
          </dl>
        </article>
      </div>

      <EmptyState
        v-if="!loading && funnelData.length === 0"
        text="暂无晋级数据"
        description="比赛产生晋级或获奖结果后，阶段数据会显示在这里"
        icon="DataAnalysis"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getCompetitionFunnel, type FunnelItem } from '@/api/dashboard'
import { getCompetitionStageColor, normalizePercentage } from '@/utils/format'
import EmptyState from '@/components/EmptyState.vue'

interface FunnelSummary {
  totalCompetitions: number
  totalPromoted: number
  totalAwarded: number
}

const loading = ref(false)
const loadFailed = ref(false)
const funnelData = ref<FunnelItem[]>([])
const summary = ref<FunnelSummary>({
  totalCompetitions: 0,
  totalPromoted: 0,
  totalAwarded: 0,
})

function formatRate(rate: number | null | undefined): string {
  const percent = normalizePercentage(rate)
  return percent === null ? '-' : `${percent.toFixed(1)}%`
}

function rateTone(rate: number | null | undefined): string {
  const percent = normalizePercentage(rate)
  if (percent === null) return 'rate-muted'
  if (percent >= 50) return 'rate-positive'
  if (percent >= 20) return 'rate-caution'
  return 'rate-muted'
}

function getPercentage(item: FunnelItem): string {
  const total = funnelData.value.reduce((sum, current) => sum + (current.total || 0), 0)
  return total === 0 ? '0.0' : ((item.total / total) * 100).toFixed(1)
}

function stageBarStyle(item: FunnelItem): Record<string, string> {
  const maximum = Math.max(...funnelData.value.map((current) => current.total || 0), 1)
  const width = item.total > 0 ? Math.max((item.total / maximum) * 100, 6) : 0
  return { width: `${width}%` }
}

function formatStageIndex(index: number): string {
  return String(index + 1).padStart(2, '0')
}

async function loadData(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    const response = await getCompetitionFunnel()
    funnelData.value = response.funnel || []
    summary.value = {
      totalCompetitions: response.total_competitions || 0,
      totalPromoted: response.total_promoted || 0,
      totalAwarded: response.total_awarded || 0,
    }
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.funnel-view {
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

.funnel-surface {
  min-height: 280px;
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

.level-count {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.stage-list {
  padding: 0 18px;
}

.stage-row {
  display: grid;
  grid-template-columns: minmax(150px, 0.75fr) minmax(190px, 1fr) minmax(390px, 1.55fr);
  align-items: center;
  gap: 20px;
  padding: 20px 0;
  border-bottom: 1px solid var(--color-border-light);

  &:last-child {
    border-bottom: 0;
  }
}

.stage-identity {
  display: grid;
  grid-template-columns: 28px 8px minmax(0, 1fr);
  align-items: center;
  gap: 9px;

  > div {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  strong {
    overflow: hidden;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  > div span {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }
}

.stage-index {
  color: var(--color-text-muted);
  font-family: $font-family-mono;
  font-size: 11px;
}

.stage-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.stage-volume {
  min-width: 0;
}

.stage-volume__label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: var(--color-text-muted);
  font-size: 11px;

  strong {
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
}

.stage-track {
  width: 100%;
  height: 8px;
  overflow: hidden;
  background: var(--color-surface-strong);
  border-radius: var(--radius-xs);

  span {
    display: block;
    height: 100%;
    background: var(--color-primary);
    border-radius: inherit;
  }
}

.stage-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(72px, 1fr));
  min-width: 0;

  > div {
    min-width: 0;
    padding: 0 14px;
    border-left: 1px solid var(--color-border-light);
  }

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    display: flex;
    align-items: baseline;
    gap: 6px;
    margin-top: 3px;
    white-space: nowrap;

    strong {
      color: var(--color-text);
      font-size: 16px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }

    span {
      font-size: 11px;
      font-variant-numeric: tabular-nums;
    }
  }
}

.rate-positive {
  color: var(--color-success);
}

.rate-caution {
  color: var(--color-warning);
}

.rate-muted {
  color: var(--color-text-muted);
}

@media screen and (max-width: 1180px) {
  .stage-row {
    grid-template-columns: minmax(150px, 0.75fr) minmax(220px, 1.25fr);
  }

  .stage-metrics {
    grid-column: 1 / -1;

    > div:first-child {
      padding-left: 0;
      border-left: 0;
    }
  }
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

    p {
      max-width: 34ch;
    }
  }

  .stage-list {
    padding: 0 14px;
  }

  .stage-row {
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
    padding: 18px 0;
  }

  .stage-metrics {
    grid-column: auto;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 0;

    > div {
      padding: 0 12px;

      &:nth-child(odd) {
        padding-left: 0;
        border-left: 0;
      }
    }
  }
}
</style>
