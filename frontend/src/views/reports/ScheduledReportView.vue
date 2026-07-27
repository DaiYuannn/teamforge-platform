<template>
  <div class="page-container report-page">
    <PageHeader title="定时报表" subtitle="按账户创建报表计划，自动生成 Excel、Word 或 PDF 并留存执行记录">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">新建计划</el-button>
      </template>
    </PageHeader>

    <section class="metric-strip" aria-label="定时报表概览">
      <div class="metric-item">
        <span>全部计划</span>
        <strong>{{ schedules.length }}</strong>
        <small>当前可见范围</small>
      </div>
      <div class="metric-item">
        <span>运行中</span>
        <strong>{{ activeCount }}</strong>
        <small>等待下次调度</small>
      </div>
      <div class="metric-item">
        <span>最近成功</span>
        <strong>{{ successCount }}</strong>
        <small>含邮件未配置的文件生成</small>
      </div>
      <div class="metric-item" :class="{ 'metric-item--danger': failedCount > 0 }">
        <span>需要处理</span>
        <strong>{{ failedCount }}</strong>
        <small>最近运行失败</small>
      </div>
    </section>

    <el-tabs v-model="activeTab" class="report-tabs">
      <el-tab-pane label="发送计划" name="schedules">
        <section class="surface-panel table-panel">
          <el-table v-loading="loading" :data="schedules" row-key="id">
            <template #empty>
              <EmptyState
                text="暂无定时报表"
                description="创建计划后，系统会在设定时间自动生成文件。"
                icon="Calendar"
              />
            </template>
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="execution-panel">
                  <h3>最近执行记录</h3>
                  <el-table :data="row.recent_executions" size="small">
                    <el-table-column prop="started_at" label="开始时间" min-width="150">
                      <template #default="{ row: execution }">
                        {{ formatDateTime(execution.started_at) }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="trigger_display" label="触发" width="80" />
                    <el-table-column prop="status_display" label="结果" width="150">
                      <template #default="{ row: execution }">
                        <el-tag :type="statusTone(execution.status)" size="small">
                          {{ execution.status_display }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="delivery_status_display" label="邮件投递" min-width="150" />
                    <el-table-column prop="file_name" label="文件" min-width="220" show-overflow-tooltip />
                    <el-table-column label="操作" width="90" align="right">
                      <template #default="{ row: execution }">
                        <el-button
                          v-if="execution.file_name"
                          link
                          type="primary"
                          @click="downloadExecution(row.id, execution as any)"
                        >
                          下载
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="report_name" label="报表" min-width="190">
              <template #default="{ row }">
                <div class="report-name">
                  <strong>{{ row.report_name }}</strong>
                  <span>{{ row.file_format_display }} · {{ row.frequency_display }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="执行规则" min-width="190">
              <template #default="{ row }">{{ scheduleRule(row as any) }}</template>
            </el-table-column>
            <el-table-column label="接收人" min-width="170" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.recipient_names.length ? row.recipient_names.join('、') : '仅站内留存' }}
              </template>
            </el-table-column>
            <el-table-column prop="next_run" label="下次运行" min-width="160">
              <template #default="{ row }">
                {{ row.is_active && row.next_run ? formatDateTime(row.next_run) : '已停用' }}
              </template>
            </el-table-column>
            <el-table-column prop="last_status_display" label="最近状态" width="150">
              <template #default="{ row }">
                <el-tag :type="statusTone(row.last_status)" size="small">
                  {{ row.last_status_display }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="292" align="right" fixed="right">
              <template #default="{ row }">
                <template v-if="canManageSchedule(row as any)">
                  <el-button link @click="openEditDialog(row as any)">编辑</el-button>
                  <el-button link type="primary" :loading="runningId === row.id" @click="runNow(row as any)">
                    立即运行
                  </el-button>
                  <el-button link @click="toggleSchedule(row as any)">
                    {{ row.is_active ? '停用' : '启用' }}
                  </el-button>
                  <el-button link type="danger" @click="removeSchedule(row as any)">删除</el-button>
                </template>
                <el-tag v-else type="info" size="small">仅接收</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="报表模板" name="templates">
        <section class="template-grid">
          <article v-for="report in reports" :key="report.id" class="surface-panel template-card">
            <div class="template-icon"><el-icon><DataAnalysis /></el-icon></div>
            <div class="template-content">
              <h2>{{ report.name }}</h2>
              <p>{{ report.description || dataSourceLabel(report.config.data_source) }}</p>
              <div>
                <el-tag size="small">{{ dataSourceLabel(report.config.data_source) }}</el-tag>
                <span>{{ report.created_by_name || '系统' }}创建</span>
              </div>
            </div>
          </article>
          <EmptyState
            v-if="!reports.length && !loading"
            text="暂无报表模板"
            description="新建计划时会同时创建一个可复用模板。"
            icon="DataAnalysis"
          />
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="createVisible"
      :title="editingSchedule ? '编辑定时报表' : '新建定时报表'"
      width="660px"
      append-to-body
      destroy-on-close
    >
      <el-form label-position="top" :model="form">
        <div class="form-grid">
          <el-form-item label="报表名称" required class="span-2">
            <el-input
              v-model="form.name"
              maxlength="80"
              placeholder="例如：每周项目进度汇总"
              :disabled="Boolean(editingSchedule)"
            />
          </el-form-item>
          <el-form-item label="数据来源" required>
            <el-select v-model="form.dataSource" :disabled="Boolean(editingSchedule)" @change="handleDataSourceChange">
              <el-option label="项目概览" value="project" />
              <el-option label="任务进度" value="task" />
              <el-option label="经费汇总" value="finance" />
              <el-option label="比赛进展" value="competition" />
            </el-select>
          </el-form-item>
          <el-form-item label="分组方式">
            <el-select v-model="form.groupBy" :disabled="Boolean(editingSchedule)">
              <el-option
                v-for="option in groupOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="文件格式" required>
            <el-select v-model="form.fileFormat">
              <el-option label="Excel 工作簿" value="xlsx" />
              <el-option label="Word 文档" value="docx" />
              <el-option label="PDF 文档" value="pdf" />
            </el-select>
          </el-form-item>
          <el-form-item label="频率" required>
            <el-select v-model="form.frequency">
              <el-option label="每日" value="daily" />
              <el-option label="每周" value="weekly" />
              <el-option label="每月" value="monthly" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.frequency === 'weekly'" label="每周执行日" required>
            <el-select v-model="form.weekday">
              <el-option v-for="(day, index) in WEEKDAYS" :key="day" :label="day" :value="index" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.frequency === 'monthly'" label="每月执行日" required>
            <el-input-number v-model="form.dayOfMonth" :min="1" :max="28" />
          </el-form-item>
          <el-form-item label="执行时间" required>
            <el-time-picker
              v-model="form.executionTime"
              value-format="HH:mm:ss"
              format="HH:mm"
              placeholder="选择时间"
            />
          </el-form-item>
          <el-form-item label="计划状态">
            <el-switch
              v-model="form.isActive"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
            />
          </el-form-item>
          <el-form-item label="邮件接收人" class="span-2">
            <el-select
              v-model="form.recipientIds"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="可不选；不选时仅在站内留存文件"
            >
              <el-option
                v-for="member in members"
                :key="member.id"
                :label="`${member.name || member.email} · ${member.email}`"
                :value="member.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="说明" class="span-2">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="2"
              maxlength="200"
              placeholder="说明该报表的使用场景"
              :disabled="Boolean(editingSchedule)"
            />
          </el-form-item>
        </div>
      </el-form>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="即使邮件服务未配置，报表文件也会正常生成并保存在执行记录中。"
      />
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveSchedule">
          {{ editingSchedule ? '保存修改' : '创建计划' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Plus } from '@element-plus/icons-vue'
import {
  activateScheduledReport,
  createCustomReport,
  createScheduledReport,
  deactivateScheduledReport,
  deleteCustomReport,
  deleteScheduledReport,
  downloadReportExecution,
  getCustomReports,
  getScheduledReports,
  runScheduledReport,
  updateScheduledReport,
  type CustomReport,
  type ReportDataSource,
  type ReportExecution,
  type ReportFileFormat,
  type ReportFrequency,
  type ReportRunStatus,
  type ScheduledReport,
} from '@/api/reports'
import { getMembers } from '@/api/members'
import { downloadBlob, formatDateTime } from '@/utils/format'
import type { Member } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useUserStore } from '@/stores/user'
import { canManageScheduledReport } from './scheduledReportAccess'

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const activeTab = ref('schedules')
const loading = ref(false)
const saving = ref(false)
const runningId = ref<number | null>(null)
const createVisible = ref(false)
const editingSchedule = ref<ScheduledReport | null>(null)
const reports = ref<CustomReport[]>([])
const schedules = ref<ScheduledReport[]>([])
const members = ref<Member[]>([])
const form = reactive({
  name: '',
  description: '',
  dataSource: 'project' as ReportDataSource,
  groupBy: 'status',
  fileFormat: 'xlsx' as ReportFileFormat,
  frequency: 'weekly' as ReportFrequency,
  executionTime: '09:00:00',
  weekday: 0,
  dayOfMonth: 1,
  recipientIds: [] as number[],
  isActive: true,
})
const userStore = useUserStore()

const activeCount = computed(() => schedules.value.filter((item) => item.is_active).length)
const successCount = computed(() =>
  schedules.value.filter((item) => item.last_status === 'success' || item.last_status === 'partial').length,
)
const failedCount = computed(() => schedules.value.filter((item) => item.last_status === 'failed').length)
const groupOptions = computed(() => {
  if (form.dataSource === 'finance') return [
    { label: '按类别', value: 'category' },
    { label: '按项目', value: 'project' },
  ]
  if (form.dataSource === 'competition') return [
    { label: '按状态', value: 'status' },
    { label: '按级别', value: 'level' },
  ]
  if (form.dataSource === 'task') return [
    { label: '按状态', value: 'status' },
    { label: '按项目', value: 'project' },
  ]
  return [
    { label: '按状态', value: 'status' },
    { label: '按阶段', value: 'stage' },
  ]
})

function responseItems<T>(response: { results: T[] } | T[]): T[] {
  return Array.isArray(response) ? response : response.results
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const [reportResponse, scheduleResponse, memberResponse] = await Promise.all([
      getCustomReports(),
      getScheduledReports(),
      getMembers({ page: 1, page_size: 100 }),
    ])
    reports.value = responseItems(reportResponse)
    schedules.value = responseItems(scheduleResponse)
    members.value = responseItems(memberResponse)
  } finally {
    loading.value = false
  }
}

function openCreateDialog(): void {
  editingSchedule.value = null
  Object.assign(form, {
    name: '',
    description: '',
    dataSource: 'project',
    groupBy: 'status',
    fileFormat: 'xlsx',
    frequency: 'weekly',
    executionTime: '09:00:00',
    weekday: 0,
    dayOfMonth: 1,
    recipientIds: [],
    isActive: true,
  })
  createVisible.value = true
}

function canManageSchedule(schedule: ScheduledReport): boolean {
  return canManageScheduledReport(schedule, userStore.userInfo)
}

function openEditDialog(schedule: ScheduledReport): void {
  if (!canManageSchedule(schedule)) return
  const report = reports.value.find((item) => item.id === schedule.report)
  editingSchedule.value = schedule
  Object.assign(form, {
    name: schedule.report_name,
    description: report?.description || '',
    dataSource: report?.config.data_source || 'project',
    groupBy: report?.config.group_by || 'status',
    fileFormat: schedule.file_format,
    frequency: schedule.frequency,
    executionTime: schedule.execution_time,
    weekday: schedule.weekday,
    dayOfMonth: schedule.day_of_month,
    recipientIds: [...schedule.recipient_ids],
    isActive: schedule.is_active,
  })
  createVisible.value = true
}

function handleDataSourceChange(): void {
  form.groupBy = groupOptions.value[0].value
}

async function saveSchedule(): Promise<void> {
  if (!form.name.trim() || !form.executionTime) {
    ElMessage.warning('请填写报表名称和执行时间')
    return
  }
  saving.value = true
  try {
    const schedulePayload = {
      recipient_ids: form.recipientIds,
      frequency: form.frequency,
      execution_time: form.executionTime,
      weekday: form.weekday,
      day_of_month: form.dayOfMonth,
      timezone: 'Asia/Shanghai',
      file_format: form.fileFormat,
      is_active: form.isActive,
    }

    if (editingSchedule.value) {
      await updateScheduledReport(editingSchedule.value.id, schedulePayload)
      ElMessage.success('定时报表计划已更新')
    } else {
      const report = await createCustomReport({
        name: form.name.trim(),
        description: form.description.trim(),
        report_type: 'summary',
        config: {
          data_source: form.dataSource,
          group_by: form.groupBy,
          chart_type: 'table',
        },
      })
      try {
        await createScheduledReport({ report: report.id, ...schedulePayload })
      } catch (error) {
        try {
          await deleteCustomReport(report.id)
        } catch {
          ElMessage.error(`计划创建失败，报表模板 #${report.id} 未能自动清理，请联系管理员处理`)
        }
        throw error
      }
      ElMessage.success('定时报表计划已创建')
    }
    createVisible.value = false
    await loadData()
  } catch {
    // API 拦截器已展示错误；保留弹窗以便修正后重试。
  } finally {
    saving.value = false
  }
}

async function runNow(row: ScheduledReport): Promise<void> {
  runningId.value = row.id
  try {
    const execution = await runScheduledReport(row.id)
    if (execution.status === 'failed') {
      ElMessage.error(execution.error || '报表生成失败')
    } else {
      ElMessage.success(execution.message || '报表已生成')
    }
    await loadData()
  } finally {
    runningId.value = null
  }
}

async function toggleSchedule(row: ScheduledReport): Promise<void> {
  if (row.is_active) await deactivateScheduledReport(row.id)
  else await activateScheduledReport(row.id)
  ElMessage.success(row.is_active ? '计划已停用' : '计划已启用')
  await loadData()
}

async function removeSchedule(row: ScheduledReport): Promise<void> {
  await ElMessageBox.confirm(
    `删除“${row.report_name}”的发送计划？历史生成文件也会一并删除。`,
    '删除定时报表',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  await deleteScheduledReport(row.id)
  ElMessage.success('计划已删除')
  await loadData()
}

async function downloadExecution(scheduleId: number, execution: ReportExecution): Promise<void> {
  const blob = await downloadReportExecution(scheduleId, execution.id)
  downloadBlob(blob, execution.file_name)
}

function statusTone(status: ReportRunStatus): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'success') return 'success'
  if (status === 'partial' || status === 'running') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

function dataSourceLabel(source: ReportDataSource): string {
  return {
    project: '项目概览',
    task: '任务进度',
    finance: '经费汇总',
    competition: '比赛进展',
  }[source]
}

function scheduleRule(schedule: ScheduledReport): string {
  const time = schedule.execution_time.slice(0, 5)
  if (schedule.frequency === 'weekly') return `每${WEEKDAYS[schedule.weekday]} ${time}`
  if (schedule.frequency === 'monthly') return `每月 ${schedule.day_of_month} 日 ${time}`
  return `每日 ${time}`
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: var(--space-5);
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
}

.metric-item {
  display: grid;
  gap: 5px;
  min-height: 104px;
  padding: 16px 18px;
  border-left: 1px solid var(--color-border-light);

  &:first-child { border-left: 0; }
  span, small { color: var(--color-text-muted); }
  span { font-size: 12px; font-weight: 600; }
  strong { color: var(--color-text); font-size: 23px; font-variant-numeric: tabular-nums; }
  small { font-size: 11px; }
}

.metric-item--danger strong { color: var(--color-danger); }

.report-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--space-4);
}

.table-panel {
  padding: 0;
  overflow: hidden;
}

.report-name {
  display: grid;
  gap: 3px;
  strong { color: var(--color-text); font-size: 13px; }
  span { color: var(--color-text-muted); font-size: 11px; }
}

.execution-panel {
  padding: 10px 40px 18px;
  h3 { margin: 0 0 10px; color: var(--color-text); font-size: 13px; }
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.template-card {
  display: flex;
  gap: 14px;
  padding: 18px;
}

.template-icon {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  color: var(--color-primary);
  background: var(--color-primary-light-9);
  border-radius: var(--radius-md);
}

.template-content {
  min-width: 0;
  h2 { margin: 0; color: var(--color-text); font-size: 14px; }
  p { min-height: 38px; margin: 6px 0 12px; color: var(--color-text-regular); font-size: 12px; line-height: 1.55; }
  div { display: flex; align-items: center; gap: 8px; }
  div span { color: var(--color-text-muted); font-size: 11px; }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
  .span-2 { grid-column: 1 / -1; }
  :deep(.el-select),
  :deep(.el-date-editor),
  :deep(.el-input-number) { width: 100%; }
}

@media screen and (max-width: 900px) {
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-item:nth-child(3) { border-left: 0; border-top: 1px solid var(--color-border-light); }
  .metric-item:nth-child(4) { border-top: 1px solid var(--color-border-light); }
  .template-grid { grid-template-columns: 1fr; }
}

@media screen and (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
  .form-grid .span-2 { grid-column: auto; }
}
</style>
