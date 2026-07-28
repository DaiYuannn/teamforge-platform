<template>
  <div class="page-container schedule-page">
    <PageHeader title="我的可投入安排" subtitle="登记近期可参与工作的日期范围和大致投入量，不统计实际工时">
      <template #actions>
        <el-button
          type="primary"
          :icon="Plus"
          @click="handleOpenForm"
        >
          {{ currentPeriod?.is_filled ? '修改本期安排' : '填写本期安排' }}
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="可投入安排暂时无法加载"
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
          <dt>预计可投入</dt>
          <dd>{{ currentSchedule ? totalCapacityDays(currentSchedule) : '-' }}<small>天</small></dd>
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
          <dt>可投入日期</dt>
          <dd>{{ currentSchedule ? availabilitySummary(currentSchedule) : '-' }}</dd>
        </div>
      </dl>
    </section>

    <section v-loading="loading" class="history-surface" aria-labelledby="schedule-history-title">
      <header class="section-heading">
        <div>
          <h2 id="schedule-history-title">历史记录</h2>
          <p>{{ scheduleList.length }} 个周期，仅记录计划安排</p>
        </div>
      </header>

      <el-table v-if="!isMobile" :data="scheduleList" table-layout="fixed" size="small">
        <template #empty>
          <EmptyState v-if="!loading" text="暂无可投入安排" compact />
        </template>
        <el-table-column label="周期" min-width="190">
          <template #default="{ row }">
            {{ displayDate(row.period_start) }} - {{ displayDate(row.period_end) }}
          </template>
        </el-table-column>
        <el-table-column label="预计投入" width="100" align="right">
          <template #default="{ row }">{{ totalCapacityDays(row as ScheduleRecord) }} 天</template>
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
        <el-table-column label="可投入日期" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ availabilitySummary(row as ScheduleRecord) }}</template>
        </el-table-column>
        <el-table-column label="填写时间" width="118">
          <template #default="{ row }">{{ displayDate(scheduleFilledAt(row as ScheduleRecord)) }}</template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-schedule-list">
        <EmptyState v-if="!loading && scheduleList.length === 0" text="暂无可投入安排" compact />
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
              <dt>预计可投入</dt>
              <dd>{{ totalCapacityDays(item) }} 天</dd>
            </div>
            <div>
              <dt>线下 / 紧急</dt>
              <dd>{{ item.can_offline ? '可线下' : '不可线下' }} / {{ item.can_urgent ? '可紧急' : '不可紧急' }}</dd>
            </div>
            <div class="schedule-card__notes">
              <dt>日期安排</dt>
              <dd>{{ availabilitySummary(item) }}</dd>
            </div>
          </dl>
        </article>
      </div>
    </section>

    <el-dialog
      v-model="formVisible"
      title="填写本期可投入安排"
      :width="dialogWidth"
      :close-on-click-modal="false"
      @close="handleClose"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-alert
          title="这里填的是未来大致能投入的日期和容量，不要求事后补填实际工作时长。"
          type="info"
          :closable="false"
          show-icon
        />
        <el-form-item label="可投入日期与大致容量" prop="windows">
          <div class="availability-editor">
            <article v-for="(window, index) in form.windows" :key="index" class="availability-window">
              <el-date-picker
                v-model="window.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                :disabled-date="disableOutsideCurrentPeriod"
              />
              <div class="capacity-row">
                <span>这段时间大约能投入</span>
                <el-input-number
                  v-model="window.capacity_days"
                  :min="0.5"
                  :max="periodDayCount"
                  :step="0.5"
                  :precision="1"
                />
                <span>天</span>
                <el-button
                  v-if="form.windows.length > 1"
                  link
                  type="danger"
                  @click="removeWindow(index)"
                >
                  删除
                </el-button>
              </div>
              <el-input
                v-model="window.note"
                maxlength="200"
                placeholder="可选：例如晚间可线上、23 日全天可线下"
              />
            </article>
            <el-button plain @click="addWindow">增加一段日期</el-button>
          </div>
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
        <el-form-item label="其他说明" prop="notes">
          <el-input v-model="form.notes" type="textarea" :rows="2" maxlength="500" show-word-limit />
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
import { createSchedule, getCurrentPeriod, getMySchedules, updateSchedule } from '@/api/members'
import { formatDate } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import type { AvailabilityWindow, FlexibleWorkSchedule } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'

type ScheduleRecord = FlexibleWorkSchedule & {
  notes?: string
  filled_at?: string
}

interface AvailabilityWindowForm {
  dateRange: [string, string] | []
  capacity_days: number
  note: string
}

interface AvailabilityForm {
  windows: AvailabilityWindowForm[]
  can_offline: boolean
  can_urgent: boolean
  is_saturated: boolean
  notes: string
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
const periodDayCount = computed(() => {
  if (!currentPeriod.value) return 31
  const start = new Date(`${currentPeriod.value.period_start}T00:00:00`)
  const end = new Date(`${currentPeriod.value.period_end}T00:00:00`)
  return Math.max(1, Math.floor((end.getTime() - start.getTime()) / 86_400_000) + 1)
})

function emptyWindow(): AvailabilityWindowForm {
  return {
    dateRange: currentPeriod.value
      ? [currentPeriod.value.period_start, currentPeriod.value.period_end]
      : [],
    capacity_days: 0.5,
    note: '',
  }
}

function createDefaultForm(): AvailabilityForm {
  return {
    windows: [emptyWindow()],
    can_offline: true,
    can_urgent: false,
    is_saturated: false,
    notes: '',
  }
}

const form = reactive<AvailabilityForm>(createDefaultForm())
const rules: FormRules = {
  windows: [{
    validator: (_rule: unknown, value: AvailabilityWindowForm[], callback: (error?: Error) => void) => {
      const invalid = !value.length || value.some(
        (item) => item.dateRange.length !== 2 || !item.capacity_days || item.capacity_days <= 0,
      )
      callback(invalid ? new Error('请完整填写至少一段可投入日期和大致容量') : undefined)
    },
    trigger: 'change',
  }],
}

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '-'
}

function availabilityWindows(item: ScheduleRecord): AvailabilityWindow[] {
  const windows = item.detail?.availability_windows
  return Array.isArray(windows) ? windows : []
}

function totalCapacityDays(item: ScheduleRecord): number | string {
  const windows = availabilityWindows(item)
  if (windows.length) {
    return windows.reduce((sum, window) => sum + Number(window.capacity_days || 0), 0)
  }
  const legacyHours = Number(item.work_hours ?? item.available_hours)
  return Number.isFinite(legacyHours) ? Number((legacyHours / 8).toFixed(1)) : '-'
}

function availabilitySummary(item: ScheduleRecord): string {
  const windows = availabilityWindows(item)
  if (!windows.length) return '旧记录未填写具体日期'
  return windows.map((window) => {
    const range = window.start_date === window.end_date
      ? displayDate(window.start_date)
      : `${displayDate(window.start_date)} 至 ${displayDate(window.end_date)}`
    return `${range}（约 ${window.capacity_days} 天）${window.note ? `：${window.note}` : ''}`
  }).join('；')
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
  const existing = currentSchedule.value
  if (existing) {
    const windows = availabilityWindows(existing)
    Object.assign(form, {
      windows: windows.length
        ? windows.map((window) => ({
            dateRange: [window.start_date, window.end_date] as [string, string],
            capacity_days: Number(window.capacity_days),
            note: window.note || '',
          }))
        : [emptyWindow()],
      can_offline: existing.can_offline,
      can_urgent: existing.can_urgent,
      is_saturated: existing.is_saturated,
      notes: scheduleNotes(existing),
    })
  } else {
    Object.assign(form, createDefaultForm())
  }
  formVisible.value = true
}

function addWindow(): void {
  form.windows.push(emptyWindow())
}

function removeWindow(index: number): void {
  form.windows.splice(index, 1)
}

function disableOutsideCurrentPeriod(date: Date): boolean {
  if (!currentPeriod.value) return false
  const value = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0'),
  ].join('-')
  return value < currentPeriod.value.period_start || value > currentPeriod.value.period_end
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value || !currentPeriod.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
      period_start: currentPeriod.value.period_start,
      period_end: currentPeriod.value.period_end,
      detail: {
        availability_windows: form.windows.map((window) => ({
          start_date: window.dateRange[0],
          end_date: window.dateRange[1],
          capacity_days: window.capacity_days,
          note: window.note.trim(),
        })),
      },
      can_offline: form.can_offline,
      can_urgent: form.can_urgent,
      is_saturated: form.is_saturated,
      notes: form.notes.trim(),
    }
    if (currentSchedule.value) {
      await updateSchedule(currentSchedule.value.id, payload)
    } else {
      await createSchedule(payload)
    }
    ElMessage.success('本期可投入安排已保存')
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
  Object.assign(form, createDefaultForm())
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

.availability-editor {
  display: grid;
  width: 100%;
  gap: 10px;
}

.availability-window {
  display: grid;
  gap: 10px;
  padding: 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
}

.capacity-row {
  display: grid;
  grid-template-columns: auto 120px auto 1fr;
  align-items: center;
  gap: 8px;

  :deep(.el-button) {
    justify-self: end;
  }
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

  .capacity-row {
    grid-template-columns: minmax(0, 1fr) 104px auto;

    :deep(.el-button) {
      grid-column: 1 / -1;
      justify-self: start;
    }
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
