<template>
  <div class="page-container team-schedule-page">
    <PageHeader title="团队灵活工时" subtitle="查看团队成员最近一次可投入时间与负载状态" />

    <section class="schedule-summary" aria-label="团队工时摘要">
      <div class="schedule-summary__intro">
        <span>当前团队</span>
        <strong>{{ scheduleList.length }} 人已填写</strong>
      </div>
      <dl>
        <div>
          <dt>可投入</dt>
          <dd class="is-success">{{ availableCount }}</dd>
        </div>
        <div>
          <dt>可紧急</dt>
          <dd>{{ urgentCount }}</dd>
        </div>
        <div>
          <dt>已饱和</dt>
          <dd :class="{ 'is-danger': saturatedCount > 0 }">{{ saturatedCount }}</dd>
        </div>
      </dl>
    </section>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="团队工时暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <section v-loading="loading" class="schedule-surface" aria-label="团队工时列表">
      <el-table v-if="!isMobile" :data="scheduleList" table-layout="fixed">
        <template #empty>
          <EmptyState v-if="!loading" text="暂无团队工时" compact />
        </template>
        <el-table-column prop="user_name" label="成员" min-width="140">
          <template #default="{ row }"><strong class="member-name">{{ row.user_name || '-' }}</strong></template>
        </el-table-column>
        <el-table-column label="周期" min-width="190">
          <template #default="{ row }">
            {{ displayDate(row.period_start) }} - {{ displayDate(row.period_end) }}
          </template>
        </el-table-column>
        <el-table-column label="可投入工时" width="112" align="right">
          <template #default="{ row }">{{ scheduleHours(row as ScheduleRecord) }} 小时</template>
        </el-table-column>
        <el-table-column label="负载" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_saturated ? 'danger' : 'success'" size="small">
              {{ row.is_saturated ? '饱和' : '可投入' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="线下" width="72" align="center">
          <template #default="{ row }">{{ row.can_offline ? '可以' : '不可' }}</template>
        </el-table-column>
        <el-table-column label="紧急" width="72" align="center">
          <template #default="{ row }">{{ row.can_urgent ? '可以' : '不可' }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ scheduleNotes(row as ScheduleRecord) || '-' }}</template>
        </el-table-column>
        <el-table-column label="填写时间" width="118">
          <template #default="{ row }">{{ displayDate(scheduleFilledAt(row as ScheduleRecord)) }}</template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-schedule-list">
        <EmptyState v-if="!loading && scheduleList.length === 0" text="暂无团队工时" compact />
        <article v-for="item in scheduleList" :key="item.id" class="schedule-card">
          <header>
            <div>
              <strong>{{ item.user_name || '-' }}</strong>
              <span>{{ displayDate(item.period_start) }} - {{ displayDate(item.period_end) }}</span>
            </div>
            <el-tag :type="item.is_saturated ? 'danger' : 'success'" size="small">
              {{ item.is_saturated ? '饱和' : '可投入' }}
            </el-tag>
          </header>
          <div class="hours-row">
            <span>可投入工时</span>
            <strong>{{ scheduleHours(item) }} 小时</strong>
          </div>
          <dl>
            <div>
              <dt>线下协作</dt>
              <dd>{{ item.can_offline ? '可以' : '不可' }}</dd>
            </div>
            <div>
              <dt>紧急任务</dt>
              <dd>{{ item.can_urgent ? '可以' : '不可' }}</dd>
            </div>
            <div v-if="scheduleNotes(item)" class="schedule-card__notes">
              <dt>备注</dt>
              <dd>{{ scheduleNotes(item) }}</dd>
            </div>
          </dl>
          <footer>填写于 {{ displayDate(scheduleFilledAt(item)) }}</footer>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getAllLatestSchedules } from '@/api/members'
import { formatDate } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import type { FlexibleWorkSchedule } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'

type ScheduleRecord = FlexibleWorkSchedule & { notes?: string; filled_at?: string }

const { isMobile } = useDevice()
const loading = ref(false)
const loadFailed = ref(false)
const scheduleList = ref<ScheduleRecord[]>([])
const saturatedCount = computed(() => scheduleList.value.filter((item) => item.is_saturated).length)
const urgentCount = computed(() => scheduleList.value.filter((item) => item.can_urgent).length)
const availableCount = computed(
  () => scheduleList.value.filter((item) => !item.is_saturated && Number(scheduleHours(item)) > 0).length,
)

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '-'
}

function scheduleHours(item: ScheduleRecord): number | string {
  return item.work_hours ?? item.available_hours ?? '-'
}

function scheduleNotes(item: ScheduleRecord): string {
  return item.notes ?? item.remark ?? ''
}

function scheduleFilledAt(item: ScheduleRecord): string | undefined {
  return item.filled_at ?? item.created_at
}

async function loadData(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    const response: any = await getAllLatestSchedules()
    scheduleList.value = Array.isArray(response) ? response : response.results || []
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.team-schedule-page {
  display: flex;
  flex-direction: column;
  gap: 12px;

  :deep(.page-header) {
    margin-bottom: 6px;
  }
}

.schedule-summary {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.schedule-summary__intro {
  display: flex;
  flex-direction: column;
  justify-content: center;

  span {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  strong {
    margin-top: 2px;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
  }
}

.schedule-summary dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(78px, 1fr));
  min-width: 280px;

  > div {
    padding: 1px 18px;
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
    font-size: 20px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;

    &.is-success {
      color: var(--color-success);
    }

    &.is-danger {
      color: var(--color-danger);
    }
  }
}

.load-alert {
  margin-bottom: 0;
}

.schedule-surface {
  min-height: 220px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  :deep(.el-table::before) {
    display: none;
  }
}

.member-name {
  color: var(--color-text);
  font-weight: 600;
}

.mobile-schedule-list {
  display: grid;
  gap: 10px;
}

.schedule-card {
  padding: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  > header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;

    > div {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    strong {
      color: var(--color-text);
      font-size: 15px;
      font-weight: 600;
    }

    span {
      margin-top: 2px;
      color: var(--color-text-muted);
      font-size: 11px;
    }
  }

  dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
    margin-top: 14px;
  }

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 2px;
    overflow-wrap: anywhere;
    color: var(--color-text-regular);
    font-size: 13px;
  }

  > footer {
    padding-top: 10px;
    margin-top: 12px;
    color: var(--color-text-muted);
    font-size: 11px;
    border-top: 1px solid var(--color-border-light);
  }
}

.hours-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  margin-top: 12px;
  border-top: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  strong {
    color: var(--color-text);
    font-size: 16px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
}

.schedule-card__notes {
  grid-column: 1 / -1;
}

@media screen and (max-width: 768px) {
  .schedule-summary {
    flex-direction: column;
    gap: 12px;
    padding: 14px;
  }

  .schedule-summary dl {
    width: 100%;
    min-width: 0;

    > div {
      padding: 1px 12px;

      &:first-child {
        padding-left: 0;
        border-left: 0;
      }
    }
  }

  .schedule-surface {
    overflow: visible;
    background: transparent;
    border: 0;
  }
}
</style>
