<template>
  <div class="page-container schedule-page">
    <PageHeader title="我的灵活工时" subtitle="按半月周期登记可投入时间与工作方式">
      <template #actions>
        <el-button
          type="primary"
          :icon="Plus"
          :disabled="currentPeriod?.is_filled"
          @click="handleOpenForm"
        >
          {{ currentPeriod?.is_filled ? '本期已填写' : '填写本期工时' }}
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="工时数据暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <section v-loading="loading" class="period-surface" aria-labelledby="current-period-title">
      <header class="section-heading">
        <div>
          <h2 id="current-period-title">当前周期</h2>
          <p>{{ periodLabel }}</p>
        </div>
        <el-tag v-if="currentPeriod" :type="currentPeriod.is_filled ? 'success' : 'warning'">
          {{ currentPeriod.is_filled ? '已填写' : '待填写' }}
        </el-tag>
      </header>

      <dl class="period-summary">
        <div class="period-summary__primary">
          <dt>可投入工时</dt>
          <dd>{{ currentSchedule ? scheduleHours(currentSchedule) : '-' }}<small>小时</small></dd>
        </div>
        <div>
          <dt>负载状态</dt>
          <dd>
            <el-tag v-if="currentSchedule" :type="currentSchedule.is_saturated ? 'danger' : 'success'">
              {{ currentSchedule.is_saturated ? '已饱和' : '可投入' }}
            </el-tag>
            <span v-else>-</span>
          </dd>
        </div>
        <div>
          <dt>线下协作</dt>
          <dd>{{ currentSchedule ? (currentSchedule.can_offline ? '可以' : '不可') : '-' }}</dd>
        </div>
        <div>
          <dt>紧急任务</dt>
          <dd>{{ currentSchedule ? (currentSchedule.can_urgent ? '可以' : '不可') : '-' }}</dd>
        </div>
        <div class="period-summary__notes">
          <dt>备注</dt>
          <dd>{{ currentSchedule ? scheduleNotes(currentSchedule) || '-' : '-' }}</dd>
        </div>
      </dl>
    </section>

    <section v-loading="loading" class="history-surface" aria-labelledby="schedule-history-title">
      <header class="section-heading">
        <div>
          <h2 id="schedule-history-title">历史记录</h2>
          <p>{{ scheduleList.length }} 个周期</p>
        </div>
      </header>

      <el-table v-if="!isMobile" :data="scheduleList" table-layout="fixed" size="small">
        <template #empty>
          <EmptyState v-if="!loading" text="暂无工时记录" compact />
        </template>
        <el-table-column label="周期" min-width="190">
          <template #default="{ row }">
            {{ displayDate(row.period_start) }} - {{ displayDate(row.period_end) }}
          </template>
        </el-table-column>
        <el-table-column label="可投入工时" width="110" align="right">
          <template #default="{ row }">{{ scheduleHours(row as ScheduleRecord) }} 小时</template>
        </el-table-column>
        <el-table-column label="线下" width="76" align="center">
          <template #default="{ row }">{{ row.can_offline ? '可以' : '不可' }}</template>
        </el-table-column>
        <el-table-column label="紧急" width="76" align="center">
          <template #default="{ row }">{{ row.can_urgent ? '可以' : '不可' }}</template>
        </el-table-column>
        <el-table-column label="负载" width="88" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_saturated ? 'danger' : 'success'" size="small">
              {{ row.is_saturated ? '饱和' : '可投入' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ scheduleNotes(row as ScheduleRecord) || '-' }}</template>
        </el-table-column>
        <el-table-column label="填写时间" width="118">
          <template #default="{ row }">{{ displayDate(scheduleFilledAt(row as ScheduleRecord)) }}</template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-schedule-list">
        <EmptyState v-if="!loading && scheduleList.length === 0" text="暂无工时记录" compact />
        <article v-for="item in scheduleList" :key="item.id" class="schedule-card">
          <header>
            <div>
              <strong>{{ displayDate(item.period_start) }} - {{ displayDate(item.period_end) }}</strong>
              <span>填写于 {{ displayDate(scheduleFilledAt(item)) }}</span>
            </div>
            <el-tag :type="item.is_saturated ? 'danger' : 'success'" size="small">
              {{ item.is_saturated ? '饱和' : '可投入' }}
            </el-tag>
          </header>
          <dl>
            <div>
              <dt>可投入工时</dt>
              <dd>{{ scheduleHours(item) }} 小时</dd>
            </div>
            <div>
              <dt>线下 / 紧急</dt>
              <dd>{{ item.can_offline ? '可线下' : '不可线下' }} / {{ item.can_urgent ? '可紧急' : '不可紧急' }}</dd>
            </div>
            <div v-if="scheduleNotes(item)" class="schedule-card__notes">
              <dt>备注</dt>
              <dd>{{ scheduleNotes(item) }}</dd>
            </div>
          </dl>
        </article>
      </div>
    </section>

    <el-dialog
      v-model="formVisible"
      title="填写本期工时"
      :width="dialogWidth"
      :close-on-click-modal="false"
      @close="handleClose"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="可投入时间（小时）" prop="work_hours">
          <el-input-number v-model="form.work_hours" :min="0" :max="200" :precision="1" />
        </el-form-item>
        <div class="switch-grid">
          <el-form-item label="可以线下协作" prop="can_offline">
            <el-switch v-model="form.can_offline" />
          </el-form-item>
          <el-form-item label="可以承接紧急任务" prop="can_urgent">
            <el-switch v-model="form.can_urgent" />
          </el-form-item>
          <el-form-item label="当前工作已饱和" prop="is_saturated">
            <el-switch v-model="form.is_saturated" />
          </el-form-item>
        </div>
        <el-form-item label="备注" prop="notes">
          <el-input v-model="form.notes" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="formVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">提交</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { createSchedule, getCurrentPeriod, getMySchedules } from '@/api/members'
import { formatDate } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import type { FlexibleWorkSchedule } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'

type ScheduleRecord = FlexibleWorkSchedule & {
  notes?: string
  filled_at?: string
  detail?: Record<string, unknown>
}

interface CurrentPeriod {
  period_start: string
  period_end: string
  is_filled: boolean
  schedule?: ScheduleRecord
}

const { isMobile } = useDevice()
const loading = ref(false)
const loadFailed = ref(false)
const scheduleList = ref<ScheduleRecord[]>([])
const currentPeriod = ref<CurrentPeriod | null>(null)
const formVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const dialogWidth = computed(() => (isMobile.value ? 'calc(100vw - 24px)' : '520px'))
const currentSchedule = computed<ScheduleRecord | null>(() => {
  if (currentPeriod.value?.schedule) return currentPeriod.value.schedule
  return (
    scheduleList.value.find(
      (item) => item.period_start === currentPeriod.value?.period_start,
    ) || null
  )
})
const periodLabel = computed(() =>
  currentPeriod.value
    ? `${displayDate(currentPeriod.value.period_start)} - ${displayDate(currentPeriod.value.period_end)}`
    : '周期信息加载中',
)

const defaultForm = {
  work_hours: 40,
  can_offline: true,
  can_urgent: false,
  is_saturated: false,
  notes: '',
}
const form = reactive({ ...defaultForm })
const rules: FormRules = {
  work_hours: [{ required: true, message: '请输入可投入时间', trigger: 'blur' }],
}

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
    const [periodResponse, schedulesResponse]: [any, any] = await Promise.all([
      getCurrentPeriod(),
      getMySchedules(),
    ])
    currentPeriod.value = periodResponse
    scheduleList.value = Array.isArray(schedulesResponse)
      ? schedulesResponse
      : schedulesResponse.results || []
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

function handleOpenForm(): void {
  if (!currentPeriod.value) {
    ElMessage.warning('当前周期尚未加载完成')
    return
  }
  formVisible.value = true
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value || !currentPeriod.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createSchedule({
      period_start: currentPeriod.value.period_start,
      period_end: currentPeriod.value.period_end,
      ...form,
    })
    ElMessage.success('本期工时已提交')
    formVisible.value = false
    await loadData()
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    submitting.value = false
  }
}

function handleClose(): void {
  formRef.value?.clearValidate()
  Object.assign(form, defaultForm)
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.schedule-page {
  display: flex;
  flex-direction: column;
  gap: 12px;

  :deep(.page-header) {
    margin-bottom: 6px;
  }
}

.load-alert {
  margin-bottom: 0;
}

.period-surface,
.history-surface {
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
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border-light);

  h2 {
    color: var(--color-text);
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0;
  }

  p {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.period-summary {
  display: grid;
  grid-template-columns: 1.2fr repeat(3, minmax(110px, 0.7fr)) 1.5fr;

  > div {
    min-width: 0;
    padding: 16px 18px;
    border-left: 1px solid var(--color-border-light);

    &:first-child {
      border-left: 0;
    }
  }

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 4px;
    overflow-wrap: anywhere;
    color: var(--color-text-regular);
    font-size: 13px;
  }
}

.period-summary__primary dd {
  color: var(--color-text);
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;

  small {
    margin-left: 4px;
    color: var(--color-text-muted);
    font-size: 11px;
    font-weight: 400;
  }
}

.history-surface :deep(.el-table::before) {
  display: none;
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
    }

    strong {
      color: var(--color-text);
      font-size: 14px;
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
}

.schedule-card__notes {
  grid-column: 1 / -1;
}

.switch-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

:deep(.el-input-number) {
  width: 100%;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media screen and (max-width: 1000px) {
  .period-summary {
    grid-template-columns: repeat(4, minmax(0, 1fr));

    .period-summary__primary {
      grid-column: span 1;
    }

    .period-summary__notes {
      grid-column: 1 / -1;
      border-top: 1px solid var(--color-border-light);
      border-left: 0;
    }
  }
}

@media screen and (max-width: 768px) {
  .section-heading {
    padding: 13px 14px;
  }

  .period-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));

    > div {
      padding: 13px 14px;

      &:nth-child(odd) {
        border-left: 0;
      }

      &:nth-child(n + 3) {
        border-top: 1px solid var(--color-border-light);
      }
    }

    .period-summary__notes {
      grid-column: 1 / -1;
    }
  }

  .history-surface {
    overflow: visible;
    background: transparent;
    border: 0;

    .section-heading {
      padding: 0 0 10px;
      border-bottom: 0;
    }
  }

  .switch-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }

  .dialog-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));

    :deep(.el-button) {
      width: 100%;
      margin-left: 0;
    }
  }
}
</style>
