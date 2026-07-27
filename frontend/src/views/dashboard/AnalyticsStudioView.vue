<template>
  <div class="page-container analytics-page">
    <PageHeader title="分析工作台" subtitle="配置个人驾驶舱、生成业务报表并沉淀团队周报">
      <template #actions>
        <el-tooltip content="刷新当前视图" placement="bottom">
          <el-button :icon="Refresh" circle aria-label="刷新当前视图" :loading="refreshing" @click="refreshActiveTab" />
        </el-tooltip>
      </template>
    </PageHeader>

    <el-alert
      v-if="!canUseAnalytics"
      title="分析工作台仅对在队或暂离的内部成员开放。"
      type="warning"
      :closable="false"
      show-icon
    />

    <template v-else>
      <div class="metric-strip" aria-label="分析资产概览">
        <div class="metric-item"><span>个人看板</span><strong>{{ dashboards.length }}</strong><small>{{ defaultDashboard?.name || '尚未设置默认' }}</small></div>
        <div class="metric-item"><span>自定义报表</span><strong>{{ reports.length }}</strong><small>{{ reportSourceCount }} 类数据源</small></div>
        <div class="metric-item"><span>本期完成任务</span><strong>{{ weeklyReport?.summary.tasks_completed ?? '-' }}</strong><small>{{ weeklyReport ? `新增 ${weeklyReport.summary.tasks_new} 项` : '等待生成周报' }}</small></div>
        <div class="metric-item" :class="{ 'metric-item--danger': weeklyReport?.summary.tasks_overdue }"><span>逾期任务</span><strong>{{ weeklyReport?.summary.tasks_overdue ?? '-' }}</strong><small>{{ weeklyReport ? `${weeklyReport.summary.tasks_upcoming_deadline} 项即将到期` : '等待生成周报' }}</small></div>
      </div>

      <el-tabs v-model="activeTab" class="studio-tabs" @tab-change="handleTabChange">
        <el-tab-pane label="自定义看板" name="dashboards">
          <section class="section-block">
            <div class="section-toolbar">
              <div><h2>我的看板</h2><p>组合需要长期关注的指标，并设置默认进入视图。</p></div>
              <el-button type="primary" :icon="Plus" @click="openDashboardDialog()">新建看板</el-button>
            </div>
            <el-alert v-if="errors.dashboards" :title="errors.dashboards" type="error" show-icon :closable="false">
              <template #default><el-button link type="primary" @click="loadDashboards">重试</el-button></template>
            </el-alert>
            <div v-loading="loading.dashboards" class="dashboard-grid">
              <article v-for="dashboard in dashboards" :key="dashboard.id" class="dashboard-card">
                <header>
                  <div><h3>{{ dashboard.name }}</h3><p>{{ dateRangeLabel(dashboard.config.date_range) }} · {{ dashboard.config.columns || 2 }} 列布局</p></div>
                  <el-tag v-if="dashboard.is_default" type="success" size="small"><el-icon><StarFilled /></el-icon> 默认</el-tag>
                </header>
                <div class="widget-preview" :style="{ '--preview-columns': Math.min(dashboard.config.columns || 2, 2) }">
                  <div v-for="widget in normalizedWidgets(dashboard)" :key="widget" class="widget-tile">
                    <el-icon><component :is="widgetMeta(widget).icon" /></el-icon>
                    <span>{{ widgetMeta(widget).label }}</span>
                  </div>
                </div>
                <div class="scope-line"><span>{{ dashboard.config.project_id ? projectName(dashboard.config.project_id) : '全部项目' }}</span><time>更新于 {{ formatDateTime(dashboard.updated_at) }}</time></div>
                <div class="record-actions">
                  <el-button text type="primary" :icon="VideoPlay" @click="openDashboard(dashboard)">打开看板</el-button>
                  <el-button v-if="!dashboard.is_default" text type="primary" :icon="Star" @click="makeDefault(dashboard)">设为默认</el-button>
                  <el-button text :icon="Edit" @click="openDashboardDialog(dashboard)">编辑</el-button>
                  <el-button text type="danger" :icon="Delete" @click="removeDashboard(dashboard)">删除</el-button>
                </div>
              </article>
            </div>
            <EmptyState v-if="!loading.dashboards && !errors.dashboards && !dashboards.length" text="暂无个人看板" description="新建看板并选择需要持续关注的指标。" icon="DataAnalysis" :compact="true">
              <template #action><el-button type="primary" :icon="Plus" @click="openDashboardDialog()">新建看板</el-button></template>
            </EmptyState>
          </section>
        </el-tab-pane>

        <el-tab-pane label="自定义报表" name="reports">
          <section class="section-block">
            <div class="section-toolbar">
              <div><h2>报表定义</h2><p>独立维护数据源、筛选和分组，可随时生成结果预览。</p></div>
              <el-button type="primary" :icon="Plus" @click="openReportDialog()">新建报表</el-button>
            </div>
            <el-alert v-if="errors.reports" :title="errors.reports" type="error" show-icon :closable="false">
              <template #default><el-button link type="primary" @click="loadReports">重试</el-button></template>
            </el-alert>
            <div v-loading="loading.reports" class="report-list">
              <article v-for="report in reports" :key="report.id" class="report-row">
                <div class="report-icon"><el-icon><DataAnalysis /></el-icon></div>
                <div class="report-main">
                  <div class="record-heading"><div><h3>{{ report.name }}</h3><p>{{ report.description || '暂无报表说明' }}</p></div><el-tag size="small" effect="plain">{{ reportTypeLabel(report.report_type) }}</el-tag></div>
                  <div class="report-meta">
                    <span>{{ dataSourceLabel(report.config.data_source) }}</span>
                    <span>{{ groupLabel(report.config.data_source, report.config.group_by) }}</span>
                    <span>{{ chartTypeLabel(report.config.chart_type) }}</span>
                    <span>{{ report.created_by_name || '系统' }}创建</span>
                  </div>
                </div>
                <div class="row-actions">
                  <el-button type="primary" plain :icon="VideoPlay" :loading="generatingId === report.id" @click="generateReport(report)">立即生成</el-button>
                  <el-button :icon="Edit" @click="openReportDialog(report)">编辑</el-button>
                  <el-button type="danger" plain :icon="Delete" @click="removeReport(report)">删除</el-button>
                </div>
              </article>
            </div>
            <EmptyState v-if="!loading.reports && !errors.reports && !reports.length" text="暂无自定义报表" description="创建一份报表后可直接生成汇总和分组数据。" icon="DataAnalysis" :compact="true" />
          </section>
        </el-tab-pane>

        <el-tab-pane label="智能周报" name="weekly">
          <section class="weekly-filter" aria-label="周报筛选">
            <el-select v-model="weeklyFilters.project_id" clearable filterable placeholder="全部项目">
              <el-option v-for="project in projects" :key="project.id" :label="`${project.name} · ${project.code}`" :value="project.id" />
            </el-select>
            <el-select v-model="weeklyFilters.weeks">
              <el-option label="最近 1 周" :value="1" /><el-option label="最近 2 周" :value="2" /><el-option label="最近 4 周" :value="4" />
            </el-select>
            <el-button type="primary" :icon="Refresh" :loading="loading.weekly" @click="loadWeeklyReport">生成周报</el-button>
            <el-button :icon="Download" :disabled="!weeklyReport" @click="exportWeeklyReport">导出 Markdown</el-button>
          </section>

          <el-alert v-if="errors.weekly" :title="errors.weekly" type="error" show-icon :closable="false">
            <template #default><el-button link type="primary" @click="loadWeeklyReport">重试</el-button></template>
          </el-alert>
          <div v-loading="loading.weekly" class="weekly-workspace">
            <template v-if="weeklyReport">
              <section class="narrative-band">
                <div><span>智能摘要</span><h2>{{ weeklyPeriod }}</h2></div>
                <p>{{ weeklyReport.narrative }}</p>
              </section>

              <div class="weekly-metrics">
                <div><span>活跃项目</span><strong>{{ weeklyReport.summary.active_projects }}</strong></div>
                <div><span>阶段变更</span><strong>{{ weeklyReport.summary.stage_changes }}</strong></div>
                <div><span>待办任务</span><strong>{{ weeklyReport.summary.tasks_pending }}</strong></div>
                <div><span>本期支出</span><strong>¥{{ formatMoney(weeklyReport.summary.weekly_expense) }}</strong></div>
                <div><span>团队动态</span><strong>{{ weeklyReport.summary.team_activities }}</strong></div>
              </div>

              <div class="weekly-columns">
                <section class="weekly-section">
                  <div class="weekly-heading"><div><h3>项目进展</h3><p>阶段与本期任务变化</p></div><el-tag size="small">{{ weeklyReport.project_progress.length }}</el-tag></div>
                  <div class="progress-list">
                    <article v-for="project in weeklyReport.project_progress" :key="project.project_id">
                      <div><strong>{{ project.project_name }}</strong><span>{{ project.project_code }}</span></div>
                      <el-tag size="small" effect="plain">{{ project.current_stage_display }}</el-tag>
                      <p>完成 {{ project.tasks_completed_this_week }} 项 · 新增 {{ project.tasks_new_this_week }} 项</p>
                    </article>
                    <EmptyState v-if="!weeklyReport.project_progress.length" text="本期暂无活跃项目" :compact="true" />
                  </div>
                </section>

                <section class="weekly-section">
                  <div class="weekly-heading"><div><h3>风险任务</h3><p>逾期与即将到期事项</p></div><el-tag size="small" type="danger">{{ riskTasks.length }}</el-tag></div>
                  <div class="task-list">
                    <article v-for="task in riskTasks.slice(0, 10)" :key="task.task_id">
                      <div><strong>{{ task.title }}</strong><span>{{ task.project_name || '未分配项目' }}</span></div>
                      <el-tag :type="task.status === 'overdue' ? 'danger' : 'warning'" size="small">{{ task.status === 'overdue' ? '已逾期' : '即将到期' }}</el-tag>
                      <time>{{ task.deadline ? formatDateTime(task.deadline) : '-' }}</time>
                    </article>
                    <EmptyState v-if="!riskTasks.length" text="本期暂无风险任务" icon="CircleCheck" :compact="true" />
                  </div>
                </section>
              </div>

              <section class="weekly-section activity-section">
                <div class="weekly-heading"><div><h3>团队动态</h3><p>本期新增贡献记录</p></div><el-tag size="small" type="success">{{ weeklyReport.team_activity.length }}</el-tag></div>
                <div class="activity-list">
                  <article v-for="(activity, index) in weeklyReport.team_activity.slice(0, 12)" :key="String(activity.created_at || index)">
                    <span class="activity-dot" /><div><strong>{{ activity.user_name || '团队成员' }}</strong><p>{{ activity.content || activity.contribution_type || '更新了团队记录' }}</p></div><time>{{ activity.created_at ? formatDateTime(String(activity.created_at)) : '-' }}</time>
                  </article>
                  <EmptyState v-if="!weeklyReport.team_activity.length" text="本期暂无团队动态" :compact="true" />
                </div>
              </section>
            </template>
            <EmptyState v-else-if="!loading.weekly && !errors.weekly" text="尚未生成智能周报" description="选择统计范围后生成本期团队摘要。" icon="Document" :compact="true">
              <template #action><el-button type="primary" :icon="Refresh" @click="loadWeeklyReport">生成周报</el-button></template>
            </EmptyState>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-dialog v-model="dashboardDialog.visible" :title="dashboardDialog.id ? '编辑看板' : '新建看板'" width="640px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top">
        <el-form-item label="看板名称" required><el-input v-model="dashboardDialog.name" maxlength="80" placeholder="例如：项目交付驾驶舱" /></el-form-item>
        <div class="form-grid"><el-form-item label="布局列数"><el-segmented v-model="dashboardDialog.columns" :options="columnOptions" /></el-form-item><el-form-item label="默认周期"><el-select v-model="dashboardDialog.date_range"><el-option label="最近一周" value="week" /><el-option label="最近一月" value="month" /><el-option label="最近一季度" value="quarter" /></el-select></el-form-item></div>
        <el-form-item label="项目范围"><el-select v-model="dashboardDialog.project_id" clearable filterable placeholder="全部项目"><el-option v-for="project in projects" :key="project.id" :label="`${project.name} · ${project.code}`" :value="project.id" /></el-select></el-form-item>
        <el-form-item label="看板组件" required><el-checkbox-group v-model="dashboardDialog.widgets" class="widget-options"><el-checkbox v-for="option in widgetOptions" :key="option.value" :value="option.value"><span class="widget-option"><el-icon><component :is="option.icon" /></el-icon><span><strong>{{ option.label }}</strong><small>{{ option.description }}</small></span></span></el-checkbox></el-checkbox-group></el-form-item>
        <el-form-item label="默认看板"><el-switch v-model="dashboardDialog.is_default" active-text="设为默认" inactive-text="普通看板" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dashboardDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveDashboard">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="dashboardRuntime.visible" :title="dashboardRuntime.item?.name || '看板'" width="900px" :fullscreen="isMobile" append-to-body>
      <div v-loading="dashboardRuntime.loading" class="runtime-dashboard" :style="{ '--runtime-columns': dashboardRuntime.item?.config.columns || 2 }">
        <section v-for="(widget, key) in dashboardRuntime.data?.widgets || {}" :key="key" class="runtime-widget">
          <div class="runtime-heading"><h3>{{ widgetMeta(key as DashboardWidget).label }}</h3><span>{{ dateRangeLabel(dashboardRuntime.item?.config.date_range) }}</span></div>
          <div v-if="widget.metrics?.length" class="runtime-metrics">
            <button v-for="metric in widget.metrics" :key="metric.label" type="button" :disabled="!metric.route" @click="openRuntimeRoute(metric.route)">
              <span>{{ metricLabel(metric.label) }}</span><strong>{{ metric.format === 'currency' ? `¥${formatMoney(Number(metric.value))}` : metric.value }}</strong>
            </button>
          </div>
          <div v-else-if="widget.items?.length" class="runtime-list">
            <button v-for="(item, index) in widget.items" :key="String(item.id || index)" type="button" @click="openRuntimeRoute(String(item.route || ''))">
              <strong>{{ item.title || item.name }}</strong><span>{{ item.project_name || item.stage || item.status }}</span><small>{{ item.deadline ? formatDateTime(String(item.deadline)) : item.task_count !== undefined ? `${item.task_count} 项任务` : '' }}</small>
            </button>
          </div>
          <EmptyState v-else text="当前范围暂无数据" :compact="true" />
        </section>
      </div>
      <template #footer><el-button @click="dashboardRuntime.visible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="reportDialog.visible" :title="reportDialog.id ? '编辑自定义报表' : '新建自定义报表'" width="700px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top">
        <el-form-item label="报表名称" required><el-input v-model="reportDialog.name" maxlength="80" /></el-form-item>
        <el-form-item label="报表说明"><el-input v-model="reportDialog.description" type="textarea" :rows="2" maxlength="300" /></el-form-item>
        <div class="form-grid"><el-form-item label="报表类型" required><el-select v-model="reportDialog.report_type"><el-option label="汇总" value="summary" /><el-option label="对比" value="comparison" /><el-option label="趋势" value="trend" /></el-select></el-form-item><el-form-item label="数据来源" required><el-select v-model="reportDialog.data_source" @change="resetReportGrouping"><el-option label="项目概览" value="project" /><el-option label="任务进度" value="task" /><el-option label="经费汇总" value="finance" /><el-option label="比赛进展" value="competition" /></el-select></el-form-item><el-form-item label="分组方式"><el-select v-model="reportDialog.group_by"><el-option v-for="option in reportGroupOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item><el-form-item label="展示方式"><el-select v-model="reportDialog.chart_type"><el-option label="数据表" value="table" /><el-option label="柱状图" value="bar" /><el-option label="折线图" value="line" /><el-option label="饼图" value="pie" /></el-select></el-form-item></div>
        <el-form-item label="项目筛选"><el-select v-model="reportDialog.project_id" clearable filterable placeholder="全部项目"><el-option v-for="project in projects" :key="project.id" :label="`${project.name} · ${project.code}`" :value="project.id" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="reportDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveReport">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="resultDialog.visible" :title="`${resultDialog.reportName} · 生成结果`" width="760px" :fullscreen="isMobile" append-to-body @closed="disposeReportChart">
      <template v-if="resultDialog.result">
        <div class="result-meta"><span>{{ dataSourceLabel(resultDialog.result.data.data_source) }}</span><time>生成于 {{ formatDateTime(resultDialog.result.generated_at) }}</time></div>
        <div class="result-summary"><div v-for="(value, key) in resultDialog.result.data.summary" :key="key"><span>{{ summaryLabel(String(key)) }}</span><strong>{{ summaryValue(String(key), value) }}</strong></div></div>
        <el-table v-if="resultDialog.result.data.chart_type === 'table'" :data="resultDialog.result.data.groups" max-height="360"><el-table-column v-if="resultDialog.result.data.report_type === 'comparison'" prop="rank" label="排名" width="72" /><el-table-column prop="label" label="分组" min-width="160" /><el-table-column prop="count" label="数量" width="100" align="right" /><el-table-column prop="total" label="金额" width="140" align="right"><template #default="{ row }">{{ row.total === undefined ? '-' : `¥${formatMoney(row.total)}` }}</template></el-table-column><el-table-column v-if="resultDialog.result.data.report_type === 'comparison'" prop="share_percent" label="占比" width="100" align="right"><template #default="{ row }">{{ row.share_percent }}%</template></el-table-column></el-table>
        <div v-else ref="reportChartRef" class="report-chart" role="img" :aria-label="`${chartTypeLabel(resultDialog.result.data.chart_type)}报表图表`" />
        <EmptyState v-if="!resultDialog.result.data.groups.length" text="当前筛选下暂无分组数据" :compact="true" />
      </template>
      <template #footer><el-button @click="resultDialog.visible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Delete, Download, Edit, Plus, Refresh, Star, StarFilled, VideoPlay } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useDevice } from '@/composables/useDevice'
import { createEChartsTooltipStyle, readEChartsThemePalette } from '@/composables/useEChartsTheme'
import { useUserStore } from '@/stores/user'
import { downloadBlob, formatDateTime } from '@/utils/format'
import { getProjects } from '@/api/projects'
import type { Project } from '@/types'
import { buildWeeklyReportMarkdown } from './analyticsStudio'
import {
  createCustomDashboard,
  deleteCustomDashboard,
  getCustomDashboardData,
  getCustomDashboards,
  getWeeklyReport,
  setDefaultDashboard,
  updateCustomDashboard,
  type CustomDashboard,
  type CustomDashboardRuntimeData,
  type DashboardWidget,
  type WeeklyReport,
  type WeeklyTask,
} from '@/api/analytics'
import {
  createCustomReport,
  deleteCustomReport,
  generateCustomReport,
  getCustomReports,
  updateCustomReport,
  type CustomReport,
  type GeneratedReport,
  type ReportDataSource,
} from '@/api/reports'

const { isMobile } = useDevice()
const router = useRouter()
const userStore = useUserStore()
const canUseAnalytics = computed(() => Boolean(userStore.userInfo?.is_active) && !['external', 'exited'].includes(userStore.userInfo?.membership_status || 'active'))
const activeTab = ref('dashboards')
const refreshing = ref(false)
const saving = ref(false)
const generatingId = ref<number | null>(null)
const loading = reactive({ dashboards: false, reports: false, weekly: false })
const errors = reactive({ dashboards: '', reports: '', weekly: '' })
const dashboards = ref<CustomDashboard[]>([])
const reports = ref<CustomReport[]>([])
const projects = ref<Project[]>([])
const weeklyReport = ref<WeeklyReport | null>(null)
const weeklyFilters = reactive({ project_id: null as number | null, weeks: 1 })

const widgetOptions: Array<{ value: DashboardWidget; label: string; description: string; icon: string }> = [
  { value: 'signals', label: '关键信号', description: '项目、任务与成员总量', icon: 'DataAnalysis' },
  { value: 'priority', label: '优先事项', description: '待办、审批与风险任务', icon: 'List' },
  { value: 'delivery', label: '交付进展', description: '阶段、日历与里程碑', icon: 'TrendCharts' },
  { value: 'business', label: '业务结果', description: '经费、比赛与知识产权', icon: 'PieChart' },
]
const columnOptions = [{ label: '1 列', value: 1 }, { label: '2 列', value: 2 }, { label: '3 列', value: 3 }, { label: '4 列', value: 4 }]
const defaultDashboard = computed(() => dashboards.value.find((item) => item.is_default))
const reportSourceCount = computed(() => new Set(reports.value.map((item) => item.config.data_source)).size)
const riskTasks = computed<WeeklyTask[]>(() => weeklyReport.value ? [...weeklyReport.value.overdue_tasks, ...weeklyReport.value.upcoming_deadline_tasks.filter((item) => !weeklyReport.value?.overdue_tasks.some((overdue) => overdue.task_id === item.task_id))] : [])
const weeklyPeriod = computed(() => weeklyReport.value ? `${weeklyReport.value.summary.report_period_start.slice(0, 10)} 至 ${weeklyReport.value.summary.report_period_end.slice(0, 10)}` : '')

const dashboardDialog = reactive({ visible: false, id: null as number | null, name: '', widgets: ['signals', 'priority', 'delivery', 'business'] as DashboardWidget[], columns: 2 as 1 | 2 | 3 | 4, date_range: 'month' as 'week' | 'month' | 'quarter', project_id: null as number | null, is_default: false })
const dashboardRuntime = reactive({ visible: false, loading: false, item: null as CustomDashboard | null, data: null as CustomDashboardRuntimeData | null })
const reportDialog = reactive({ visible: false, id: null as number | null, name: '', description: '', report_type: 'summary', data_source: 'project' as ReportDataSource, group_by: 'status', chart_type: 'table', project_id: null as number | null })
const resultDialog = reactive({ visible: false, reportName: '', result: null as GeneratedReport | null })
const reportChartRef = ref<HTMLElement>()
let reportChart: echarts.ECharts | null = null

const responseItems = <T,>(response: { results: T[] } | T[]): T[] => Array.isArray(response) ? response : response.results
const reportGroupOptions = computed(() => {
  if (reportDialog.data_source === 'finance') return [{ label: '按经费类别', value: 'category' }, { label: '按项目', value: 'project' }]
  if (reportDialog.data_source === 'competition') return [{ label: '按比赛状态', value: 'status' }, { label: '按比赛级别', value: 'level' }]
  if (reportDialog.data_source === 'task') return [{ label: '按任务状态', value: 'status' }, { label: '按项目', value: 'project' }]
  return [{ label: '按项目状态', value: 'status' }, { label: '按项目阶段', value: 'stage' }]
})

async function loadDashboards(): Promise<void> { loading.dashboards = true; errors.dashboards = ''; try { dashboards.value = responseItems(await getCustomDashboards()) } catch { errors.dashboards = '个人看板加载失败，请检查网络后重试。' } finally { loading.dashboards = false } }
async function loadReports(): Promise<void> { loading.reports = true; errors.reports = ''; try { reports.value = responseItems(await getCustomReports()) } catch { errors.reports = '自定义报表加载失败，请检查网络后重试。' } finally { loading.reports = false } }
async function loadProjects(): Promise<void> { try { projects.value = responseItems(await getProjects({ page: 1, page_size: 100 })) } catch { ElMessage.warning('项目筛选项加载失败') } }
async function loadWeeklyReport(): Promise<void> { loading.weekly = true; errors.weekly = ''; try { weeklyReport.value = await getWeeklyReport({ ...(weeklyFilters.project_id ? { project_id: weeklyFilters.project_id } : {}), weeks: weeklyFilters.weeks }) } catch { errors.weekly = '智能周报生成失败，请稍后重试。' } finally { loading.weekly = false } }
async function refreshActiveTab(): Promise<void> { refreshing.value = true; try { if (activeTab.value === 'dashboards') await loadDashboards(); if (activeTab.value === 'reports') await loadReports(); if (activeTab.value === 'weekly') await loadWeeklyReport() } finally { refreshing.value = false } }
function handleTabChange(): void { if (activeTab.value === 'dashboards' && !dashboards.value.length) void loadDashboards(); if (activeTab.value === 'reports' && !reports.value.length) void loadReports(); if (activeTab.value === 'weekly' && !weeklyReport.value) void loadWeeklyReport() }

function normalizedWidgets(item: CustomDashboard): DashboardWidget[] { return Array.isArray(item.config.widgets) && item.config.widgets.length ? item.config.widgets : ['signals', 'priority'] }
function widgetMeta(widget: DashboardWidget) { return widgetOptions.find((item) => item.value === widget) || widgetOptions[0] }
function metricLabel(value: string): string { return ({ Projects: '项目总数', 'Active projects': '进行中项目', 'Pending tasks': '待处理任务', 'Active members': '活跃成员', 'Period expense': '周期支出', Competitions: '比赛总数', Awarded: '获奖比赛', 'IP applications': '知识产权申请' } as Record<string, string>)[value] || value }
function dateRangeLabel(value?: string): string { return ({ week: '最近一周', month: '最近一月', quarter: '最近一季度' } as Record<string, string>)[value || 'month'] || '自定义周期' }
function projectName(id: number): string { return projects.value.find((item) => item.id === id)?.name || `项目 #${id}` }
function formatMoney(value: number | string): string { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function dataSourceLabel(value: ReportDataSource): string { return ({ project: '项目概览', task: '任务进度', finance: '经费汇总', competition: '比赛进展' })[value] }
function reportTypeLabel(value: string): string { return ({ summary: '汇总报表', comparison: '对比报表', trend: '趋势报表' } as Record<string, string>)[value] || value }
function chartTypeLabel(value?: string): string { return ({ table: '数据表', bar: '柱状图', line: '折线图', pie: '饼图' } as Record<string, string>)[value || 'table'] || '数据表' }
function groupLabel(source: ReportDataSource, value?: string): string { const labels: Record<string, string> = { status: '按状态', stage: '按阶段', project: '按项目', category: '按类别', level: '按级别' }; return labels[value || ''] || `${dataSourceLabel(source)}默认分组` }
function summaryLabel(key: string): string { return ({ total: '总数', active: '进行中', closed: '已结项', paused: '已暂停', done: '已完成', overdue: '已逾期', doing: '进行中', todo: '待开始', awarded: '已获奖', promoted: '已晋级', total_amount: '总金额', count: '记录数', message: '提示' } as Record<string, string>)[key] || key }
function summaryValue(key: string, value: string | number): string { return key === 'total_amount' ? `¥${formatMoney(value)}` : String(value) }
async function confirmAction(message: string, title: string): Promise<boolean> {
  try {
    await ElMessageBox.confirm(message, title, { type: 'warning' })
    return true
  } catch {
    return false
  }
}

function openDashboardDialog(item?: CustomDashboard): void { Object.assign(dashboardDialog, { visible: true, id: item?.id || null, name: item?.name || '', widgets: [...(item ? normalizedWidgets(item) : ['signals', 'priority', 'delivery', 'business'])] as DashboardWidget[], columns: item?.config.columns || 2, date_range: item?.config.date_range || 'month', project_id: item?.config.project_id || null, is_default: item?.is_default ?? !dashboards.value.length }) }
async function saveDashboard(): Promise<void> { if (!dashboardDialog.name.trim() || !dashboardDialog.widgets.length) return void ElMessage.warning('请填写看板名称并选择至少一个组件'); const payload = { name: dashboardDialog.name.trim(), config: { widgets: dashboardDialog.widgets, columns: dashboardDialog.columns, date_range: dashboardDialog.date_range, project_id: dashboardDialog.project_id }, is_default: dashboardDialog.is_default }; saving.value = true; try { if (dashboardDialog.id) await updateCustomDashboard(dashboardDialog.id, payload); else await createCustomDashboard(payload); dashboardDialog.visible = false; ElMessage.success('看板已保存'); await loadDashboards() } finally { saving.value = false } }
async function makeDefault(item: CustomDashboard): Promise<void> { await setDefaultDashboard(item.id); ElMessage.success(`“${item.name}”已设为默认看板`); await loadDashboards() }
async function removeDashboard(item: CustomDashboard): Promise<void> { if (!await confirmAction(`删除看板“${item.name}”？`, '删除看板')) return; await deleteCustomDashboard(item.id); ElMessage.success('看板已删除'); await loadDashboards() }
async function openDashboard(item: CustomDashboard): Promise<void> {
  Object.assign(dashboardRuntime, { visible: true, loading: true, item, data: null })
  try { dashboardRuntime.data = await getCustomDashboardData(item.id) }
  finally { dashboardRuntime.loading = false }
}
function openRuntimeRoute(route?: string): void { if (route) { dashboardRuntime.visible = false; void router.push(route) } }

function resetReportGrouping(): void { reportDialog.group_by = reportGroupOptions.value[0].value }
function openReportDialog(item?: CustomReport): void { Object.assign(reportDialog, { visible: true, id: item?.id || null, name: item?.name || '', description: item?.description || '', report_type: item?.report_type || 'summary', data_source: item?.config.data_source || 'project', group_by: item?.config.group_by || 'status', chart_type: item?.config.chart_type || 'table', project_id: Number(item?.config.filters?.project_id) || null }) }
async function saveReport(): Promise<void> { if (!reportDialog.name.trim()) return void ElMessage.warning('请填写报表名称'); const payload = { name: reportDialog.name.trim(), description: reportDialog.description.trim(), report_type: reportDialog.report_type, config: { data_source: reportDialog.data_source, group_by: reportDialog.group_by, chart_type: reportDialog.chart_type, filters: reportDialog.project_id ? { project_id: reportDialog.project_id } : {} } }; saving.value = true; try { if (reportDialog.id) await updateCustomReport(reportDialog.id, payload); else await createCustomReport(payload); reportDialog.visible = false; ElMessage.success('自定义报表已保存'); await loadReports() } finally { saving.value = false } }
async function removeReport(item: CustomReport): Promise<void> { if (!await confirmAction(`删除报表“${item.name}”？关联的定时计划可能受影响。`, '删除自定义报表')) return; await deleteCustomReport(item.id); ElMessage.success('报表已删除'); await loadReports() }
async function generateReport(item: CustomReport): Promise<void> { generatingId.value = item.id; try { resultDialog.result = await generateCustomReport(item.id); resultDialog.reportName = item.name; resultDialog.visible = true; await nextTick(); renderReportChart() } finally { generatingId.value = null } }
function disposeReportChart(): void { reportChart?.dispose(); reportChart = null }
function renderReportChart(): void {
  disposeReportChart()
  const result = resultDialog.result?.data
  if (!result || result.chart_type === 'table' || !reportChartRef.value || !result.groups.length) return
  reportChart = echarts.init(reportChartRef.value)
  const palette = readEChartsThemePalette()
  const values = result.groups.map((group) => Number(result.value_key === 'total' ? group.total || 0 : group.count || 0))
  const labels = result.groups.map((group) => group.label)
  const tooltip = { trigger: 'item' as const, confine: true, ...createEChartsTooltipStyle(palette) }
  if (result.chart_type === 'pie') {
    reportChart.setOption({
      color: [palette.primary, palette.success, palette.warning, palette.danger, palette.info],
      tooltip,
      legend: { bottom: 0, textStyle: { color: palette.textMuted } },
      series: [{ type: 'pie', radius: ['38%', '66%'], center: ['50%', '44%'], data: labels.map((name, index) => ({ name, value: values[index] })), itemStyle: { borderColor: palette.surface, borderWidth: 2 } }],
    })
    return
  }
  reportChart.setOption({
    color: [palette.primary], tooltip: { ...tooltip, trigger: 'axis' },
    grid: { left: 20, right: 20, top: 24, bottom: 36, containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { color: palette.textMuted, interval: 0, rotate: labels.length > 6 ? 28 : 0 }, axisLine: { lineStyle: { color: palette.border } } },
    yAxis: { type: 'value', minInterval: result.value_key === 'count' ? 1 : undefined, axisLabel: { color: palette.textMuted }, splitLine: { lineStyle: { color: palette.borderLight, type: 'dashed' } } },
    series: [{ type: result.chart_type, data: values, smooth: result.chart_type === 'line', barMaxWidth: 44, symbolSize: 8, itemStyle: result.chart_type === 'bar' ? { borderRadius: [3, 3, 0, 0] } : undefined }],
  })
}

function exportWeeklyReport(): void {
  const report = weeklyReport.value
  if (!report) return
  const filename = `团队智能周报_${report.summary.report_period_end.slice(0, 10)}.md`
  downloadBlob(new Blob([buildWeeklyReportMarkdown(report, riskTasks.value)], { type: 'text/markdown;charset=utf-8' }), filename)
  ElMessage.success('周报已导出')
}

onMounted(async () => {
  if (!canUseAnalytics.value) return
  await Promise.all([loadDashboards(), loadReports(), loadProjects(), loadWeeklyReport()])
})
onBeforeUnmount(disposeReportChart)
</script>

<style scoped lang="scss">
.analytics-page { padding-bottom: 48px; }
.metric-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 18px; overflow: hidden; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.metric-item { display: grid; gap: 4px; min-height: 96px; padding: 15px 18px; border-left: 1px solid var(--color-border-light); &:first-child { border-left: 0; } span, small { min-width: 0; overflow: hidden; color: var(--color-text-muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; } strong { color: var(--color-text); font-size: 24px; font-variant-numeric: tabular-nums; } }
.metric-item--danger strong { color: var(--color-danger); }
.studio-tabs :deep(.el-tabs__header) { margin-bottom: 18px; }
.section-block { margin-bottom: 28px; }
.section-toolbar { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 14px; h2 { margin: 0; font-size: 17px; } p { margin-top: 3px; color: var(--color-text-muted); font-size: 12px; } }
.dashboard-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; min-height: 80px; }
.dashboard-card { display: grid; gap: 14px; min-width: 0; padding: 16px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); header { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; h3 { margin: 0; font-size: 15px; } p { margin-top: 3px; color: var(--color-text-muted); font-size: 11px; } } }
.widget-preview { display: grid; grid-template-columns: repeat(var(--preview-columns), minmax(0, 1fr)); gap: 7px; min-height: 92px; padding: 8px; background: var(--color-surface-subtle); border-radius: var(--radius-sm); }
.widget-tile { display: flex; align-items: center; gap: 7px; min-height: 36px; padding: 8px; color: var(--color-text-regular); background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-xs); font-size: 11px; .el-icon { color: var(--color-primary); } }
.scope-line { display: flex; justify-content: space-between; gap: 10px; color: var(--color-text-muted); font-size: 11px; }
.record-actions { display: flex; justify-content: flex-end; gap: 4px; padding-top: 9px; border-top: 1px solid var(--color-border-light); }
.report-list { display: grid; gap: 9px; min-height: 80px; }
.report-row { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; align-items: center; gap: 14px; padding: 14px 16px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.report-icon { display: grid; place-items: center; width: 40px; height: 40px; color: var(--color-primary); background: var(--color-primary-soft); border-radius: var(--radius-sm); font-size: 19px; }
.record-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; min-width: 0; h3 { margin: 0; color: var(--color-text); font-size: 14px; overflow-wrap: anywhere; } p { margin-top: 3px; color: var(--color-text-muted); font-size: 12px; line-height: 1.45; } }
.report-meta { display: flex; flex-wrap: wrap; gap: 5px 14px; margin-top: 8px; color: var(--color-text-muted); font-size: 11px; }
.row-actions { display: flex; gap: 7px; }
.weekly-filter { display: grid; grid-template-columns: minmax(220px, .8fr) 150px auto auto 1fr; gap: 10px; margin-bottom: 16px; }
.weekly-workspace { min-height: 180px; }
.narrative-band { display: grid; grid-template-columns: minmax(180px, .35fr) minmax(0, 1fr); gap: 28px; padding: 20px; color: #fff; background: #263f3b; border-radius: var(--radius-md); span { color: #bcd2cd; font-size: 11px; } h2 { margin: 4px 0 0; font-size: 17px; } p { align-self: center; color: #edf5f3; line-height: 1.8; } }
.weekly-metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); margin: 14px 0; overflow: hidden; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); div { display: grid; gap: 5px; padding: 14px 16px; border-left: 1px solid var(--color-border-light); &:first-child { border-left: 0; } } span { color: var(--color-text-muted); font-size: 11px; } strong { font-size: 18px; font-variant-numeric: tabular-nums; } }
.weekly-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.weekly-section { padding: 16px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.weekly-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 12px; h3 { margin: 0; font-size: 15px; } p { margin-top: 2px; color: var(--color-text-muted); font-size: 11px; } }
.progress-list, .task-list, .activity-list { display: grid; gap: 0; }
.progress-list article { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 5px 10px; padding: 11px 0; border-bottom: 1px solid var(--color-border-light); &:last-child { border-bottom: 0; } div { display: grid; } strong { font-size: 12px; } span, p { color: var(--color-text-muted); font-size: 11px; } p { grid-column: 1 / -1; } }
.task-list article { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 10px; padding: 10px 0; border-bottom: 1px solid var(--color-border-light); &:last-child { border-bottom: 0; } div { display: grid; } strong { font-size: 12px; } span, time { color: var(--color-text-muted); font-size: 11px; } time { grid-column: 2; text-align: right; } }
.activity-section { margin-top: 14px; }
.activity-list article { display: grid; grid-template-columns: 8px minmax(0, 1fr) auto; align-items: start; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--color-border-light); &:last-child { border-bottom: 0; } strong { font-size: 12px; } p, time { color: var(--color-text-muted); font-size: 11px; } }
.activity-dot { width: 7px; height: 7px; margin-top: 5px; background: var(--color-success); border-radius: 50%; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.widget-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); width: 100%; gap: 8px; :deep(.el-checkbox) { height: auto; margin: 0; padding: 10px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); } }
.widget-option { display: flex; align-items: center; gap: 8px; span { display: grid; } strong { color: var(--color-text); font-size: 12px; } small { color: var(--color-text-muted); font-size: 10px; } }
.runtime-dashboard { display: grid; grid-template-columns: repeat(var(--runtime-columns), minmax(0, 1fr)); gap: 12px; min-height: 220px; }
.runtime-widget { min-width: 0; padding: 14px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.runtime-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; h3 { margin: 0; font-size: 15px; } span { color: var(--color-text-muted); font-size: 12px; } }
.runtime-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; button { min-height: 74px; padding: 10px; text-align: left; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: var(--radius-xs); cursor: pointer; &:disabled { cursor: default; } span, strong { display: block; } span { color: var(--color-text-muted); font-size: 12px; } strong { margin-top: 8px; font-size: 21px; } } }
.runtime-list { display: grid; button { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 3px 10px; padding: 9px 4px; text-align: left; background: transparent; border: 0; border-bottom: 1px solid var(--color-border-light); cursor: pointer; strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } span, small { color: var(--color-text-muted); font-size: 12px; } small { grid-column: 1 / -1; } } }
.result-meta { display: flex; justify-content: space-between; margin-bottom: 14px; color: var(--color-text-muted); font-size: 12px; }
.report-chart { width: 100%; height: 380px; }
.result-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; margin-bottom: 14px; div { display: grid; gap: 4px; padding: 12px; background: var(--color-surface-subtle); border-radius: var(--radius-sm); } span { color: var(--color-text-muted); font-size: 11px; } strong { font-size: 17px; overflow-wrap: anywhere; } }
:deep(.el-select), :deep(.el-date-editor) { width: 100%; }
@media (max-width: 1050px) { .metric-strip { grid-template-columns: repeat(2, 1fr); } .metric-item:nth-child(3) { border-left: 0; border-top: 1px solid var(--color-border-light); } .metric-item:nth-child(4) { border-top: 1px solid var(--color-border-light); } .report-row { grid-template-columns: 42px minmax(0, 1fr); .row-actions { grid-column: 1 / -1; justify-content: flex-end; } } .weekly-filter { grid-template-columns: 1fr 150px auto auto; } .weekly-metrics { grid-template-columns: repeat(3, 1fr); div:nth-child(4) { border-left: 0; border-top: 1px solid var(--color-border-light); } div:nth-child(5) { border-top: 1px solid var(--color-border-light); } } }
@media (max-width: 720px) { .section-toolbar { align-items: stretch; flex-direction: column; } .dashboard-grid { grid-template-columns: minmax(0, 1fr); } .report-row { grid-template-columns: 36px minmax(0, 1fr); padding: 12px; .row-actions { justify-content: flex-start; flex-wrap: wrap; } } .report-icon { width: 34px; height: 34px; } .weekly-filter { grid-template-columns: 1fr 1fr; > :nth-child(n + 3) { width: 100%; } } .narrative-band { grid-template-columns: 1fr; gap: 10px; padding: 16px; } .weekly-columns { grid-template-columns: 1fr; } .weekly-metrics { grid-template-columns: repeat(2, 1fr); div:nth-child(3), div:nth-child(5) { border-left: 0; } div:nth-child(n + 3) { border-top: 1px solid var(--color-border-light); } } .form-grid, .widget-options { grid-template-columns: 1fr; } }
@media (max-width: 420px) { .metric-item { min-height: 82px; padding: 12px; strong { font-size: 20px; } } .scope-line, .result-meta { flex-direction: column; } .weekly-filter { grid-template-columns: 1fr; } .weekly-metrics { grid-template-columns: 1fr; div { border-left: 0; border-top: 1px solid var(--color-border-light); &:first-child { border-top: 0; } } } .activity-list article { grid-template-columns: 8px minmax(0, 1fr); time { grid-column: 2; } } }
@media (max-width: 720px) { .runtime-dashboard { grid-template-columns: 1fr; } }
</style>
