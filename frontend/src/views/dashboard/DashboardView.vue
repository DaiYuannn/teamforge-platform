<template>
  <div class="dashboard-view page-container">
    <header class="workbench-header">
      <div>
        <p class="workbench-date">{{ todayLabel }}</p>
        <div class="title-line">
          <h1>工作台</h1>
          <span v-if="activeDashboard">{{ activeDashboard.name }}</span>
          <span v-if="lastUpdatedLabel">{{ lastUpdatedLabel }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="goTo('/dashboard/calendar')">
          <el-icon><Calendar /></el-icon>日历
        </el-button>
        <el-button @click="goTo('/dashboard/gantt')">
          <el-icon><DataAnalysis /></el-icon>甘特图
        </el-button>
        <el-popover
          v-model:visible="themePopoverVisible"
          placement="bottom-end"
          :width="292"
          trigger="click"
          @before-enter="resetThemeDraft"
          @after-leave="handleThemePopoverHide"
        >
          <template #reference>
            <el-button aria-label="自定义账户主色">
              <el-icon><Brush /></el-icon>主题
            </el-button>
          </template>
          <div class="theme-popover">
            <div class="theme-popover-title">
              <strong>账户主色</strong>
              <span>保存后将在此账户登录时自动恢复</span>
            </div>
            <div class="theme-presets">
              <button
                v-for="option in themeColorOptions"
                :key="option.value"
                type="button"
                :aria-label="option.label"
                :aria-pressed="normalizedThemeDraft === option.value"
                :class="{ active: normalizedThemeDraft === option.value }"
                :style="{ '--swatch-color': option.value }"
                @click="setThemeDraft(option.value)"
              />
            </div>
            <div class="theme-custom-row">
              <el-color-picker
                v-model="themeDraftColor"
                color-format="hex"
                :predefine="predefinedThemeColors"
                aria-label="选择自定义主色"
                @change="previewThemeDraft"
              />
              <el-input
                v-model="themeDraftColor"
                maxlength="7"
                placeholder="#176b73"
                aria-label="主色十六进制值"
                @change="previewThemeDraft"
              />
            </div>
            <div class="theme-popover-actions">
              <el-button size="small" @click="cancelThemeEdit">取消</el-button>
              <el-button
                type="primary"
                size="small"
                :loading="themeSaving"
                @click="saveTheme"
              >
                保存到账户
              </el-button>
            </div>
          </div>
        </el-popover>
        <el-tooltip content="刷新工作台" placement="bottom">
          <el-button
            circle
            aria-label="刷新工作台"
            :loading="initialLoading || isRefreshing"
            @click="loadAll"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </header>

    <div v-if="partialErrorLabel" class="status-banner" role="status">
      <el-icon><WarningFilled /></el-icon>
      <span>部分数据暂未加载：{{ partialErrorLabel }}</span>
      <el-button link type="primary" :loading="isRefreshing" @click="loadAll">重新加载</el-button>
    </div>

    <QuickEntryPanel />

    <section v-if="initialLoading" class="workspace-panel loading-panel" aria-label="工作台加载中">
      <el-skeleton :rows="12" animated />
    </section>

    <el-result
      v-else-if="dashboardUnavailable"
      icon="warning"
      title="工作台暂时无法加载"
      sub-title="请检查网络连接后重试"
      class="dashboard-result"
    >
      <template #extra>
        <el-button type="primary" :loading="isRefreshing" @click="loadAll">重新加载</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="dashboard-sections">
      <section
        v-if="dashboardCardVisible('signals')"
        class="signal-grid"
        aria-label="今日工作摘要"
        :style="{ order: dashboardCardOrder('signals') }"
      >
        <article
          v-for="signal in signalItems"
          :key="signal.label"
          class="signal-card"
          :data-tone="signal.tone"
        >
          <div class="signal-head">
            <span>{{ signal.label }}</span>
            <el-icon><component :is="signal.icon" /></el-icon>
          </div>
          <strong>{{ signal.value }}</strong>
          <p>{{ signal.detail }}</p>
        </article>
      </section>

      <div
        v-if="dashboardCardVisible('priority')"
        class="priority-grid"
        :style="{ order: dashboardCardOrder('priority') }"
      >
        <section class="workspace-panel">
          <div class="panel-header">
            <div><h2>待我处理</h2><p>按优先级与截止时间排列</p></div>
            <el-button link type="primary" @click="goTo('/todo')">
              全部待办<el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>

          <div v-if="todayTodos.length" class="focus-list">
            <button
              v-for="todo in todayTodos"
              :key="`${todo.type}_${todo.id}`"
              type="button"
              class="focus-row todo-row"
              @click="goToTodo(todo)"
            >
              <span class="row-indicator" :data-tone="todoTone(todo.type)"></span>
              <span class="row-copy">
                <strong>{{ todo.title }}</strong>
                <small>{{ todo.project_name || todo.status_display || '需要处理' }}</small>
              </span>
              <span class="row-meta">
                <el-tag size="small" :type="todoTagType(todo.type)">{{ todoTypeLabel(todo.type) }}</el-tag>
                <time>{{ todoDeadlineText(todo.due_date) }}</time>
              </span>
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
          <EmptyState
            v-else
            text="当前没有待办"
            icon="CircleCheck"
            :illustration="false"
            :compact="true"
            accent="#237A55"
          />

          <div class="queue-links">
            <button type="button" @click="goTo('/tasks')">
              <span><small>3 日内到期任务</small><strong>{{ upcomingDeadlineCount }}</strong></span>
              <el-icon><ArrowRight /></el-icon>
            </button>
            <button type="button" @click="goTo('/intellectual-property/todo')">
              <span><small>知识产权待办</small><strong>{{ ipTodoCount }}</strong></span>
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
        </section>

        <section class="workspace-panel">
          <div class="panel-header">
            <div><h2>风险与项目健康</h2><p>{{ activeProjectCount }} 个项目进行中</p></div>
            <el-button link type="primary" @click="goTo('/projects')">
              项目列表<el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>

          <div class="health-line">
            <div><span>近 11 日持续更新</span><strong>{{ healthyActiveProjectCount }} / {{ activeProjectCount }}</strong></div>
            <el-progress :percentage="projectHealthRate" :show-text="false" :stroke-width="7" color="#237A55" />
          </div>

          <div v-if="riskItems.length" class="focus-list">
            <button
              v-for="(risk, index) in riskItems.slice(0, 5)"
              :key="riskKey(risk, index)"
              type="button"
              class="focus-row risk-row"
              @click="goToRisk(risk)"
            >
              <span class="risk-icon" :data-tone="riskTone(risk.type)"><el-icon><Warning /></el-icon></span>
              <span class="row-copy"><strong>{{ risk.message }}</strong><small>{{ riskMeta(risk) }}</small></span>
              <el-tag size="small" :type="riskTagType(risk.type)">{{ riskTypeLabel(risk.type) }}</el-tag>
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
          <EmptyState
            v-else
            text="当前没有风险提醒"
            icon="CircleCheck"
            :illustration="false"
            :compact="true"
            accent="#237A55"
          />
        </section>
      </div>

      <section
        v-if="dashboardCardVisible('delivery')"
        class="workspace-panel delivery-panel"
        :style="{ order: dashboardCardOrder('delivery') }"
      >
        <div class="panel-header">
          <div><h2>交付概览</h2><p>项目与任务状态</p></div>
          <el-radio-group v-model="chartMode" size="small">
            <el-radio-button value="project">项目</el-radio-button>
            <el-radio-button value="task">任务</el-radio-button>
          </el-radio-group>
        </div>
        <div class="delivery-layout">
          <div class="chart-region">
            <div v-if="hasOverviewChartData" ref="overviewChartRef" class="overview-chart"></div>
            <EmptyState
              v-else
              text="暂无状态数据"
              icon="DataAnalysis"
              :illustration="false"
              :compact="true"
              accent="#176B73"
            />
          </div>
          <dl class="delivery-facts">
            <div><dt>项目总数</dt><dd>{{ projectTotal }}</dd></div>
            <div><dt>进行中项目</dt><dd>{{ activeProjectCount }}</dd></div>
            <div><dt>待完成任务</dt><dd>{{ pendingTaskCount }}</dd></div>
            <div><dt>已结项项目</dt><dd>{{ closedProjectCount }}</dd></div>
          </dl>
        </div>
      </section>

      <section
        v-if="dashboardCardVisible('business')"
        class="workspace-panel business-panel"
        :style="{ order: dashboardCardOrder('business') }"
      >
        <div class="panel-header compact-header">
          <div><h2>业务概览</h2><p>经费、成果与团队动态</p></div>
        </div>
        <el-tabs v-model="businessTab" class="business-tabs">
          <el-tab-pane label="经费" name="finance">
            <div class="tab-action"><el-button link type="primary" @click="goTo('/finance')">查看经费明细<el-icon><ArrowRight /></el-icon></el-button></div>
            <dl class="finance-summary">
              <div><dt>总经费</dt><dd>{{ formatMoneyWithComma(dashboardData?.finance_overview?.total_income) }}</dd></div>
              <div><dt>已使用</dt><dd>{{ formatMoneyWithComma(dashboardData?.finance_overview?.total_used) }}</dd></div>
              <div><dt>剩余</dt><dd>{{ formatMoneyWithComma(dashboardData?.finance_overview?.total_remaining) }}</dd></div>
            </dl>
            <template v-if="financeTop5.length">
              <el-table v-if="!isMobile" :data="financeTop5" size="small" class="finance-table">
                <el-table-column prop="project_name" label="项目" min-width="150" show-overflow-tooltip />
                <el-table-column label="预算" min-width="120" align="right"><template #default="{ row }">{{ formatMoneyWithComma(row.budget) }}</template></el-table-column>
                <el-table-column label="已使用" min-width="120" align="right"><template #default="{ row }">{{ formatMoneyWithComma(row.expense) }}</template></el-table-column>
                <el-table-column label="剩余" min-width="120" align="right"><template #default="{ row }"><span :class="{ danger: row.remaining < 0 }">{{ formatMoneyWithComma(row.remaining) }}</span></template></el-table-column>
                <el-table-column label="状态" width="96" align="center"><template #default="{ row }"><el-tag size="small" :type="financeTagType(row)">{{ financeStatus(row) }}</el-tag></template></el-table-column>
              </el-table>
              <div v-else class="mobile-finance-list">
                <div v-for="(item, index) in financeTop5" :key="item.project_name || index">
                  <header><strong>{{ item.project_name || '未命名项目' }}</strong><el-tag size="small" :type="financeTagType(item)">{{ financeStatus(item) }}</el-tag></header>
                  <dl>
                    <div><dt>预算</dt><dd>{{ formatMoneyWithComma(item.budget) }}</dd></div>
                    <div><dt>已使用</dt><dd>{{ formatMoneyWithComma(item.expense) }}</dd></div>
                    <div><dt>剩余</dt><dd :class="{ danger: item.remaining < 0 }">{{ formatMoneyWithComma(item.remaining) }}</dd></div>
                  </dl>
                </div>
              </div>
            </template>
            <EmptyState v-else text="暂无经费数据" icon="Money" :illustration="false" :compact="true" accent="#176B73" />
          </el-tab-pane>

          <el-tab-pane label="知识产权" name="ip">
            <div class="tab-action"><el-button link type="primary" @click="goTo('/intellectual-property')">全部申请<el-icon><ArrowRight /></el-icon></el-button></div>
            <div v-if="ipApplications.length" class="business-list">
              <button v-for="ip in ipApplications" :key="ip.id" type="button" class="business-row ip-row" @click="goToIPDetail(ip.id)">
                <span class="row-copy"><strong>{{ ip.title }}</strong><small>{{ ip.related_project_name || ip.application_code || '未关联项目' }}</small></span>
                <span class="ip-progress"><el-tag size="small" :type="ipTagType(ip.status)">{{ IP_STATUS_MAP[ip.status]?.label || ip.status }}</el-tag><el-progress :percentage="ipProgress(ip.status)" :show-text="false" :stroke-width="6" :color="ipProgressColor(ip.status)" /></span>
                <el-icon><ArrowRight /></el-icon>
              </button>
            </div>
            <EmptyState v-else text="暂无知识产权申请" icon="Document" :illustration="false" :compact="true" accent="#176B73" />
          </el-tab-pane>

          <el-tab-pane label="团队投入" name="team">
            <div class="tab-action"><el-button link type="primary" @click="goTo('/members/team-schedule')">团队工时<el-icon><ArrowRight /></el-icon></el-button></div>
            <dl class="work-status-list">
              <div><span data-tone="success"><el-icon><CircleCheckFilled /></el-icon></span><dt>可投入</dt><dd>{{ workStatus.available }}</dd></div>
              <div><span data-tone="warning"><el-icon><WarningFilled /></el-icon></span><dt>已饱和</dt><dd>{{ workStatus.saturated }}</dd></div>
              <div><span data-tone="neutral"><el-icon><RemoveFilled /></el-icon></span><dt>暂不可投入</dt><dd>{{ workStatus.leave }}</dd></div>
            </dl>
          </el-tab-pane>

          <el-tab-pane label="贡献动态" name="contributions">
            <div v-if="recentContributions.length" class="business-list">
              <div v-for="item in recentContributions" :key="item.id" class="business-row activity-row">
                <span class="activity-dot"></span>
                <span class="row-copy"><strong>{{ item.user_name || '团队成员' }} · {{ item.project_name || '未关联项目' }}</strong><small>{{ item.content }}</small></span>
                <span class="row-meta"><el-tag size="small" :type="CONTRIBUTION_TYPE_MAP[item.contribution_type]?.tagType as any">{{ CONTRIBUTION_TYPE_MAP[item.contribution_type]?.label || item.contribution_type }}</el-tag><time>{{ formatRelativeTime(item.created_at) }}</time></span>
              </div>
            </div>
            <EmptyState v-else text="暂无贡献动态" icon="Trophy" :illustration="false" :compact="true" accent="#176B73" />
          </el-tab-pane>

          <el-tab-pane label="通知" name="notifications">
            <div v-if="recentNotifications.length" class="business-list">
              <div v-for="notice in recentNotifications" :key="notice.id" class="business-row activity-row">
                <span class="activity-dot"></span>
                <span class="row-copy"><strong>{{ notice.title }}</strong><small>{{ notice.content }}</small></span>
                <span class="row-meta"><el-tag size="small" :type="noticeTagType(notice.category || notice.notification_type)">{{ noticeLabel(notice.category || notice.notification_type) }}</el-tag><time>{{ formatRelativeTime(notice.created_at) }}</time></span>
              </div>
            </div>
            <EmptyState v-else text="暂无通知" icon="Bell" :illustration="false" :compact="true" accent="#176B73" />
          </el-tab-pane>

          <el-tab-pane label="比赛节点" name="competitions">
            <div v-if="competitionEvents.length" class="business-list">
              <div v-for="(event, index) in competitionEvents" :key="event.id || index" class="business-row activity-row">
                <span class="activity-dot"></span>
                <span class="row-copy"><strong>{{ event.title }}</strong><small>{{ event.description || '比赛节点' }}</small></span>
                <span class="row-meta"><el-tag size="small" :type="competitionTagType(event)">{{ competitionStatus(event) }}</el-tag><time>{{ formatDate(event.start) }}</time></span>
              </div>
            </div>
            <EmptyState v-else text="暂无比赛节点" icon="Calendar" :illustration="false" :compact="true" accent="#176B73" />
          </el-tab-pane>
        </el-tabs>
      </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Brush, Calendar, Stamp, TrendCharts, WarningFilled } from '@element-plus/icons-vue'
import { getDashboardData } from '@/api/dashboard'
import { getCustomDashboards, type CustomDashboard } from '@/api/analytics'
import { getAllLatestSchedules } from '@/api/members'
import { getContributions } from '@/api/contributions'
import { getIPApplications } from '@/api/intellectualProperty'
import { getNotifications } from '@/api/notifications'
import { getUnifiedTodos, type UnifiedTodoItem } from '@/api/todo'
import { formatDate, formatMoneyWithComma, formatRelativeTime } from '@/utils/format'
import { CONTRIBUTION_TYPE_MAP, IP_STATUS_MAP, NOTIFICATION_CATEGORY_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import {
  createEChartsTooltipStyle,
  readEChartsThemePalette,
  useEChartsTheme,
} from '@/composables/useEChartsTheme'
import type { Contribution, DashboardData } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import QuickEntryPanel from '@/components/QuickEntryPanel.vue'
import { useUserStore } from '@/stores/user'
import {
  PRIMARY_COLOR_OPTIONS,
  applyPrimaryColor,
  isReadablePrimaryColor,
  normalizePrimaryColor,
} from '@/utils/theme'

type SectionKey = 'dashboard' | 'workStatus' | 'contributions' | 'ip' | 'notifications' | 'todos'
type ChartMode = 'project' | 'task'
type BusinessTab = 'finance' | 'ip' | 'team' | 'contributions' | 'notifications' | 'competitions'
interface RiskItem { type: string; message: string; project_id?: number; task_id?: number; competition_id?: number; last_update?: string; deadline?: string | null; defense_date?: string | null }
interface CompetitionEvent { id?: string | number; title: string; description?: string; start: string }

const router = useRouter()
const userStore = useUserStore()
const activeDashboard = ref<CustomDashboard | null>(null)
const effectiveDashboardCards = computed(() => (
  activeDashboard.value?.config.widgets?.length
    ? activeDashboard.value.config.widgets
    : userStore.dashboardCards
))
function dashboardCardVisible(card: string): boolean {
  return effectiveDashboardCards.value.includes(card as any)
}
function dashboardCardOrder(card: string): number {
  const index = effectiveDashboardCards.value.indexOf(card as any)
  return index < 0 ? 99 : index
}
const { isMobile } = useDevice()
const dashboardData = ref<DashboardData | null>(null)
const recentContributions = ref<Contribution[]>([])
const ipApplications = ref<any[]>([])
const recentNotifications = ref<any[]>([])
const myTodos = ref<UnifiedTodoItem[]>([])
const initialLoading = ref(true)
const isRefreshing = ref(false)
const loadErrors = ref<Set<SectionKey>>(new Set())
const chartMode = ref<ChartMode>('project')
const businessTab = ref<BusinessTab>('finance')
const themePopoverVisible = ref(false)
const themeSaving = ref(false)
const themeDraftCommitted = ref(false)
const themeDraftColor = ref(userStore.primaryColor)
const themeColorOptions = PRIMARY_COLOR_OPTIONS
const predefinedThemeColors = PRIMARY_COLOR_OPTIONS.map((option) => option.value)
const normalizedThemeDraft = computed(() => normalizePrimaryColor(themeDraftColor.value))
const workStatus = reactive({ available: 0, saturated: 0, leave: 0 })
const overviewChartRef = ref<HTMLElement>()
let overviewChart: echarts.ECharts | null = null
let chartResizeObserver: ResizeObserver | null = null

const sectionLabels: Record<SectionKey, string> = {
  dashboard: '项目与任务概览', workStatus: '团队投入状态', contributions: '贡献动态',
  ip: '知识产权进展', notifications: '近期通知', todos: '待办事项',
}
const todoLabels: Record<string, string> = {
  task: '任务',
  overdue_task: '逾期任务',
  approval: '敏感审批',
  contribution_review: '贡献审核',
  ip_todo: '知识产权',
}
const riskLabels: Record<string, string> = { stale_project: '项目停滞', overdue_task: '任务逾期', upcoming_competition: '比赛临近' }
const chartPrimaryColor = computed(() => userStore.primaryColor)
const todayLabel = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())

const dashboardUnavailable = computed(() => !dashboardData.value && loadErrors.value.has('dashboard'))
const partialErrorLabel = computed(() => dashboardUnavailable.value ? '' : Array.from(loadErrors.value).map((key) => sectionLabels[key]).join('、'))
const lastUpdatedLabel = computed(() => {
  const value = dashboardData.value?.generated_at
  if (!value) return ''
  const parsed = new Date(String(value).replace(' ', 'T'))
  return Number.isNaN(parsed.getTime()) ? `数据更新于 ${value}` : `数据更新于 ${parsed.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
})
const riskItems = computed<RiskItem[]>(() => dashboardData.value?.risk_alerts?.items || [])
const riskCount = computed(() => dashboardData.value?.risk_alerts?.total || riskItems.value.length)
const overdueTaskCount = computed(() => dashboardData.value?.task_overview?.overdue || 0)
const upcomingDeadlineCount = computed(() => dashboardData.value?.task_overview?.upcoming_deadline || 0)
const projectTotal = computed(() => dashboardData.value?.project_overview?.total || 0)
const activeProjectCount = computed(() => dashboardData.value?.project_overview?.active || 0)
const closedProjectCount = computed(() => dashboardData.value?.project_overview?.closed || 0)
const pendingTaskCount = computed(() => {
  const distribution = dashboardData.value?.task_overview?.status_distribution
  return (distribution?.todo?.count || 0) + (distribution?.doing?.count || 0)
})
const staleProjectCount = computed(() => new Set(riskItems.value.filter((item) => item.type === 'stale_project' && item.project_id).map((item) => item.project_id)).size)
const healthyActiveProjectCount = computed(() => Math.max(0, activeProjectCount.value - staleProjectCount.value))
const projectHealthRate = computed(() => activeProjectCount.value ? Math.round(healthyActiveProjectCount.value / activeProjectCount.value * 100) : 0)
const projectHealthText = computed(() => activeProjectCount.value ? `${healthyActiveProjectCount.value} / ${activeProjectCount.value} 个项目近 11 日有更新` : '暂无进行中项目')
const pendingApprovalCount = computed(() => myTodos.value.filter((todo) => ['approval', 'contribution_review', 'ip_todo'].includes(todo.type)).length)
const todayTodos = computed(() => [...myTodos.value].sort((a, b) => dateValue(a.due_date) - dateValue(b.due_date)).slice(0, 5))
const todayTodoCount = computed(() => myTodos.value.length)
const ipTodoCount = computed(() => myTodos.value.filter((todo) => todo.type === 'ip_todo').length)
const signalItems = computed(() => [
  { label: '今日待办', value: todayTodoCount.value, detail: `${upcomingDeadlineCount.value} 个任务将在 3 日内到期`, tone: 'primary', icon: Calendar },
  { label: '逾期 / 风险', value: riskCount.value, detail: `其中 ${overdueTaskCount.value} 个任务已逾期`, tone: 'danger', icon: WarningFilled },
  { label: '待审批', value: pendingApprovalCount.value, detail: '贡献、敏感资料与知识产权事项', tone: 'warning', icon: Stamp },
  { label: '项目健康', value: `${projectHealthRate.value}%`, detail: projectHealthText.value, tone: 'success', icon: TrendCharts },
])

function toAmount(value: number | string | null | undefined): number { const numberValue = Number(value); return Number.isFinite(numberValue) ? numberValue : 0 }
const financeTop5 = computed(() => (dashboardData.value?.finance_overview?.project_finance || []).slice(0, 5).map((item: any) => ({
  project_name: item.project_name, budget: toAmount(item.bonus_amount) + toAmount(item.other_income),
  expense: toAmount(item.used_amount), remaining: toAmount(item.remaining_amount),
})))
const competitionEvents = computed<CompetitionEvent[]>(() => {
  const direct = (dashboardData.value?.calendar_events || []).filter((event: any) => event.type === 'competition').map((event: any) => ({ id: event.id, title: event.title, description: event.description, start: event.start }))
  return direct.length ? direct : riskItems.value.filter((item) => item.type === 'upcoming_competition' && item.defense_date).map((item) => ({ id: item.competition_id, title: item.message, description: '答辩节点临近', start: item.defense_date as string }))
})
const projectChartData = computed(() => {
  const stats = dashboardData.value?.project_overview
  return [{ value: stats?.active || 0, name: '进行中' }, { value: stats?.closed || 0, name: '已结项' }, { value: stats?.paused || 0, name: '暂停' }].filter((item) => item.value > 0)
})
const taskChartData = computed(() => {
  const distribution = dashboardData.value?.task_overview?.status_distribution || {}
  return [{ key: 'todo', name: '待办', value: distribution.todo?.count || 0 }, { key: 'doing', name: '进行中', value: distribution.doing?.count || 0 }, { key: 'done', name: '已完成', value: distribution.done?.count || 0 }, { key: 'overdue', name: '已逾期', value: distribution.overdue?.count || 0 }]
})
const hasOverviewChartData = computed(() => chartMode.value === 'project' ? projectChartData.value.length > 0 : taskChartData.value.some((item) => item.value > 0))

function dateKey(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
function isToday(value: string | null | undefined): boolean { return dateKey(value) === dateKey(new Date().toISOString()) }
function dateValue(value: string | null | undefined): number { const parsed = value ? new Date(value).getTime() : NaN; return Number.isNaN(parsed) ? Number.MAX_SAFE_INTEGER : parsed }
function todoDeadlineText(value: string | null | undefined): string { if (!value) return '无截止时间'; if (isToday(value)) return '今天'; return dateValue(value) < Date.now() ? `已逾期 · ${formatDate(value)}` : formatDate(value) }
function todoTypeLabel(type: string): string { return todoLabels[type] || type }
function todoTagType(type: string): any { return ({ overdue_task: 'danger', approval: 'warning', contribution_review: 'success', ip_todo: 'warning', task: 'primary' } as Record<string, string>)[type] || 'info' }
function todoTone(type: string): string { if (type === 'overdue_task') return 'danger'; if (['approval', 'ip_todo'].includes(type)) return 'warning'; if (type === 'contribution_review') return 'success'; return 'primary' }
function riskTypeLabel(type: string): string { return riskLabels[type] || '提醒' }
function riskTagType(type: string): any { return type === 'overdue_task' ? 'danger' : ['stale_project', 'upcoming_competition'].includes(type) ? 'warning' : 'info' }
function riskTone(type: string): string { return type === 'overdue_task' ? 'danger' : ['stale_project', 'upcoming_competition'].includes(type) ? 'warning' : 'neutral' }
function riskKey(item: RiskItem, index: number): string { return `${item.type}_${item.project_id || item.task_id || item.competition_id || index}` }
function riskMeta(item: RiskItem): string { if (item.deadline) return `截止 ${formatDate(item.deadline)}`; if (item.defense_date) return `答辩 ${formatDate(item.defense_date)}`; return item.last_update ? `最近更新 ${item.last_update}` : '请及时处理' }
function financeTagType(row: any): any { if (row.remaining < 0) return 'danger'; return row.budget > 0 && row.expense / row.budget > 0.8 ? 'warning' : 'success' }
function financeStatus(row: any): string { if (row.remaining < 0) return '超支'; return row.budget > 0 && row.expense / row.budget > 0.8 ? '接近预算' : '正常' }
function ipTagType(status: string): any { return IP_STATUS_MAP[status]?.color || 'info' }
function ipProgress(status: string): number { const step = IP_STATUS_MAP[status]?.step ?? 0; return step < 0 ? 0 : Math.round(step / 10 * 100) }
function ipProgressColor(status: string): string { const colors: Record<string, string> = { danger: '#B64242', warning: '#A66116', success: '#237A55', info: '#93A09B' }; return colors[IP_STATUS_MAP[status]?.color] || '#176B73' }
function noticeTagType(category: string): any { return NOTIFICATION_CATEGORY_MAP[category]?.type || 'info' }
function noticeLabel(category: string): string { return NOTIFICATION_CATEGORY_MAP[category]?.label || category || '通知' }
function competitionTagType(event: CompetitionEvent): any { const days = (dateValue(event.start) - Date.now()) / 86_400_000; return days < 0 ? 'info' : days <= 7 ? 'danger' : days <= 30 ? 'warning' : 'success' }
function competitionStatus(event: CompetitionEvent): string { const days = (dateValue(event.start) - Date.now()) / 86_400_000; return days < 0 ? '已结束' : days <= 7 ? '即将开始' : days <= 30 ? '准备中' : '计划中' }
function goTo(path: string): void { router.push(path) }
function goToIPDetail(id: number): void { router.push(`/intellectual-property/${id}`) }
function goToTodo(todo: UnifiedTodoItem): void {
  if (todo.route_name) {
    router.push({
      name: todo.route_name,
      params: todo.route_params || {},
      query: Object.fromEntries(
        Object.entries(todo.route_query || {}).map(([key, value]) => [key, String(value)]),
      ),
    })
    return
  }
  if (todo.url) router.push(todo.url)
}
function goToRisk(item: RiskItem): void { if (item.type === 'stale_project' && item.project_id) router.push(`/projects/${item.project_id}`); else router.push(item.type === 'upcoming_competition' ? '/competitions' : '/tasks') }
function extractList(payload: any): any[] { if (Array.isArray(payload)) return payload; if (Array.isArray(payload?.results)) return payload.results; if (Array.isArray(payload?.data)) return payload.data; if (Array.isArray(payload?.data?.results)) return payload.data.results; return [] }
function resetThemeDraft(): void {
  themeDraftColor.value = userStore.primaryColor
  themeDraftCommitted.value = false
}
function setThemeDraft(color: string): void {
  if (!isReadablePrimaryColor(color)) return
  themeDraftColor.value = color
  applyPrimaryColor(color)
}
function previewThemeDraft(color: string | null): void {
  if (color && /^#[0-9a-fA-F]{6}$/.test(color) && isReadablePrimaryColor(color)) {
    themeDraftColor.value = color.toLowerCase()
    applyPrimaryColor(themeDraftColor.value)
  }
}
function handleThemePopoverHide(): void {
  if (!themeDraftCommitted.value) {
    userStore.syncPrimaryColor(userStore.userInfo?.preferences?.primary_color)
  }
  themeDraftColor.value = userStore.primaryColor
  themeDraftCommitted.value = false
}
function cancelThemeEdit(): void {
  userStore.syncPrimaryColor(userStore.userInfo?.preferences?.primary_color)
  resetThemeDraft()
  themePopoverVisible.value = false
}
async function saveTheme(): Promise<void> {
  if (!/^#[0-9a-fA-F]{6}$/.test(themeDraftColor.value)) {
    ElMessage.warning('请输入完整的六位十六进制颜色')
    return
  }
  if (!isReadablePrimaryColor(themeDraftColor.value)) {
    ElMessage.warning('主色过浅，请选择能清晰显示白色文字的较深颜色')
    return
  }
  themeSaving.value = true
  try {
    const preference = await userStore.savePreference({
      primary_color: themeDraftColor.value.toLowerCase(),
    })
    themeDraftColor.value = preference.primary_color
    themeDraftCommitted.value = true
    themePopoverVisible.value = false
    ElMessage.success('账户主色已保存')
  } catch {
    themeDraftColor.value = userStore.primaryColor
  } finally {
    themeSaving.value = false
  }
}

async function loadDashboard(): Promise<void> {
  try {
    const response = await getCustomDashboards()
    const dashboards = Array.isArray(response) ? response : response.results
    activeDashboard.value = dashboards.find((item) => item.is_default) || null
  } catch {
    activeDashboard.value = null
  }
  dashboardData.value = await getDashboardData(
    activeDashboard.value?.config.project_id
      ? { project_id: activeDashboard.value.config.project_id }
      : undefined,
  )
}
async function loadWorkStatus(): Promise<void> {
  const list = extractList(await getAllLatestSchedules())
  workStatus.available = list.filter((item: any) => !item.is_saturated && toAmount(item.available_hours ?? item.work_hours) > 0).length
  workStatus.saturated = list.filter((item: any) => item.is_saturated).length
  workStatus.leave = list.filter((item: any) => !item.is_saturated && toAmount(item.available_hours ?? item.work_hours) <= 0).length
}
async function loadRecentContributions(): Promise<void> { recentContributions.value = extractList(await getContributions({ page: 1, page_size: 5 })) as Contribution[] }
async function loadIPApplications(): Promise<void> { ipApplications.value = extractList(await getIPApplications({ page: 1, page_size: 5 })) }
async function loadNotifications(): Promise<void> { recentNotifications.value = extractList(await getNotifications({ page: 1, page_size: 5 })) }
async function loadMyTodos(): Promise<void> { myTodos.value = (await getUnifiedTodos()).results || [] }
async function loadAll(): Promise<void> {
  if (!initialLoading.value) isRefreshing.value = true
  const operations: Array<[SectionKey, () => Promise<void>]> = [['dashboard', loadDashboard], ['workStatus', loadWorkStatus], ['contributions', loadRecentContributions], ['ip', loadIPApplications], ['notifications', loadNotifications], ['todos', loadMyTodos]]
  const results = await Promise.allSettled(operations.map(([, loader]) => loader()))
  loadErrors.value = new Set(results.flatMap((result, index) => result.status === 'rejected' ? [operations[index][0]] : []))
  initialLoading.value = false
  isRefreshing.value = false
  await nextTick()
  renderChart()
}

function ensureChart(): echarts.ECharts | null {
  const element = overviewChartRef.value
  if (!element) { overviewChart?.dispose(); overviewChart = null; return null }
  if (!overviewChart || overviewChart.getDom() !== element) { overviewChart?.dispose(); overviewChart = echarts.init(element) }
  chartResizeObserver?.disconnect()
  if (typeof ResizeObserver !== 'undefined') { chartResizeObserver = new ResizeObserver(() => overviewChart?.resize()); chartResizeObserver.observe(element) }
  return overviewChart
}
function renderChart(): void {
  if (!hasOverviewChartData.value) { overviewChart?.dispose(); overviewChart = null; chartResizeObserver?.disconnect(); return }
  const chart = ensureChart()
  if (!chart) return
  const palette = readEChartsThemePalette()
  const tooltipStyle = { ...createEChartsTooltipStyle(palette), padding: [8, 10] }
  chart.clear()
  if (chartMode.value === 'project') {
    chart.setOption({
      animationDuration: 280, color: [palette.primary, palette.success, palette.info],
      tooltip: { trigger: 'item', formatter: '{b}: <b>{c}</b> ({d}%)', ...tooltipStyle },
      legend: { bottom: 0, left: 'center', itemWidth: 10, itemHeight: 10, textStyle: { color: palette.textMuted, fontSize: 12 } },
      series: [{ type: 'pie', radius: ['46%', '70%'], center: ['50%', '44%'], label: { show: false }, emphasis: { scaleSize: 4 }, itemStyle: { borderColor: palette.surface, borderWidth: 2 }, data: projectChartData.value }],
    })
    return
  }
  const colors: Record<string, string> = { todo: palette.info, doing: palette.primary, done: palette.success, overdue: palette.danger }
  chart.setOption({
    animationDuration: 280, tooltip: { trigger: 'item', formatter: '{b}: <b>{c}</b>', confine: true, ...tooltipStyle },
    grid: { left: 12, right: 12, top: 20, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: taskChartData.value.map((item) => item.name), axisTick: { show: false }, axisLine: { lineStyle: { color: palette.border } }, axisLabel: { color: palette.textRegular, fontSize: 12, interval: 0 } },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { color: palette.textMuted, fontSize: 12 }, splitLine: { lineStyle: { color: palette.borderLight, type: 'dashed' } } },
    series: [{ type: 'bar', barMaxWidth: 38, emphasis: { disabled: true }, label: { show: true, position: 'top', color: palette.textRegular, fontSize: 12 }, data: taskChartData.value.map((item) => ({ value: item.value, itemStyle: { color: colors[item.key], borderRadius: [3, 3, 0, 0] } })) }],
  })
}

useEChartsTheme(renderChart)
watch([chartMode, isMobile, chartPrimaryColor], async () => { await nextTick(); renderChart() })
onMounted(() => { loadAll(); window.addEventListener('resize', renderChart) })
onUnmounted(() => { window.removeEventListener('resize', renderChart); chartResizeObserver?.disconnect(); overviewChart?.dispose() })
</script>

<style lang="scss" scoped>
.dashboard-sections {
  display: flex;
  flex-direction: column;
}

.dashboard-view {
  color: var(--color-text-primary, #18221f);
  letter-spacing: 0;
  padding-bottom: 32px;
  button { letter-spacing: 0; }
}

.workbench-header {
  display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 18px;
  h1 { margin: 0; color: var(--color-text-primary, #18221f); font-size: 24px; line-height: 1.25; font-weight: 650; }
}
.workbench-date { margin: 0 0 4px; color: var(--color-text-secondary, #5f6c67); font-size: 13px; }
.title-line { display: flex; align-items: baseline; flex-wrap: wrap; gap: 10px; span { color: var(--color-text-tertiary, #7c8984); font-size: 12px; } }
.header-actions { display: flex; align-items: center; flex-shrink: 0; gap: 8px; :deep(.el-button + .el-button) { margin-left: 0; } }

.theme-popover-title {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 14px;

  strong { color: var(--color-text-primary, #18221f); font-size: 14px; }
  span { color: var(--color-text-tertiary, #7c8984); font-size: 12px; line-height: 1.45; }
}
.theme-presets {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;

  button {
    width: 31px;
    height: 31px;
    padding: 0;
    background: var(--swatch-color);
    border: 3px solid var(--color-surface, #fff);
    border-radius: 50%;
    box-shadow: 0 0 0 1px var(--color-border, #dce3e0);
    cursor: pointer;

    &.active { box-shadow: 0 0 0 2px var(--swatch-color); }
  }
}
.theme-custom-row {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}
.theme-popover-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
}

.status-banner {
  display: flex; align-items: center; gap: 8px; min-height: 42px; margin-bottom: 16px; padding: 8px 12px;
  color: var(--color-warning, #a66116); background: rgba(166, 97, 22, 0.08); border: 1px solid rgba(166, 97, 22, 0.22); border-radius: 6px; font-size: 13px;
  span { flex: 1; min-width: 0; }
}
.dashboard-result, .workspace-panel { background: var(--color-surface, #fff); border: 1px solid var(--color-border, #dce3e0); border-radius: 8px; }
.dashboard-result { min-height: 440px; }
.workspace-panel { min-width: 0; padding: 20px; }
.loading-panel { min-height: 520px; }

.signal-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; }
.signal-card {
  min-width: 0; min-height: 126px; padding: 16px 18px; background: var(--color-surface, #fff); border: 1px solid var(--color-border, #dce3e0); border-top: 3px solid var(--color-border-strong, #c6d0cc); border-radius: 8px;
  &[data-tone='primary'] { border-top-color: var(--primary-color, #176b73); .signal-head .el-icon { color: var(--primary-color, #176b73); background: rgba(23, 107, 115, 0.1); } }
  &[data-tone='danger'] { border-top-color: var(--color-danger, #b64242); .signal-head .el-icon { color: var(--color-danger, #b64242); background: rgba(182, 66, 66, 0.1); } }
  &[data-tone='warning'] { border-top-color: var(--color-warning, #a66116); .signal-head .el-icon { color: var(--color-warning, #a66116); background: rgba(166, 97, 22, 0.1); } }
  &[data-tone='success'] { border-top-color: var(--color-success, #237a55); .signal-head .el-icon { color: var(--color-success, #237a55); background: rgba(35, 122, 85, 0.1); } }
  > strong { display: block; margin-top: 10px; font-size: 27px; line-height: 1; font-weight: 700; font-variant-numeric: tabular-nums; }
  p { margin: 6px 0 0; color: var(--color-text-secondary, #5f6c67); font-size: 12px; line-height: 1.5; }
}
.signal-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--color-text-secondary, #5f6c67); font-size: 13px; font-weight: 500; .el-icon { display: inline-flex; width: 30px; height: 30px; border-radius: 6px; font-size: 16px; } }

.priority-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(340px, 0.85fr); gap: 16px; margin-bottom: 16px; }
.panel-header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px;
  h2 { margin: 0; font-size: 16px; line-height: 1.4; font-weight: 650; }
  p { margin: 3px 0 0; color: var(--color-text-tertiary, #7c8984); font-size: 12px; }
  :deep(.el-button) { flex-shrink: 0; }
}
.compact-header { margin-bottom: 0; }
.focus-list, .business-list { display: flex; flex-direction: column; }
.focus-row, .business-row, .queue-links button {
  appearance: none; width: 100%; color: inherit; background: transparent; border: 0; font: inherit; text-align: left;
  &:focus-visible { outline: 2px solid var(--primary-color, #176b73); outline-offset: -2px; }
}
.focus-row {
  display: grid; align-items: center; gap: 11px; min-height: 62px; padding: 8px 6px; border-bottom: 1px solid var(--color-border-light, #e8edeb); cursor: pointer;
  &:hover { background: var(--color-surface-subtle, #f7f9f8); }
  > .el-icon { color: var(--color-text-tertiary, #7c8984); font-size: 14px; }
}
.todo-row { grid-template-columns: 4px minmax(0, 1fr) auto 16px; }
.risk-row { grid-template-columns: 32px minmax(0, 1fr) auto 16px; }
.row-copy { display: flex; flex-direction: column; min-width: 0; gap: 3px; strong, small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } strong { font-size: 14px; font-weight: 600; } small { color: var(--color-text-secondary, #5f6c67); font-size: 12px; line-height: 1.45; } }
.row-meta { display: flex; align-items: flex-end; flex-direction: column; flex-shrink: 0; gap: 5px; color: var(--color-text-tertiary, #7c8984); font-size: 11px; font-variant-numeric: tabular-nums; }
.row-indicator { align-self: stretch; min-height: 38px; background: var(--primary-color, #176b73); border-radius: 3px; &[data-tone='danger'] { background: var(--color-danger, #b64242); } &[data-tone='warning'] { background: var(--color-warning, #a66116); } &[data-tone='success'] { background: var(--color-success, #237a55); } }
.risk-icon { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; color: var(--color-text-tertiary, #7c8984); background: rgba(124, 137, 132, 0.1); border-radius: 6px; &[data-tone='danger'] { color: var(--color-danger, #b64242); background: rgba(182, 66, 66, 0.1); } &[data-tone='warning'] { color: var(--color-warning, #a66116); background: rgba(166, 97, 22, 0.1); } }

.queue-links { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 14px; border: 1px solid var(--color-border, #dce3e0); border-radius: 6px; overflow: hidden; }
.queue-links button {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 64px; padding: 10px 14px; cursor: pointer;
  & + button { border-left: 1px solid var(--color-border, #dce3e0); }
  &:hover { background: var(--color-surface-subtle, #f7f9f8); }
  span { display: flex; align-items: baseline; min-width: 0; gap: 8px; } small { color: var(--color-text-secondary, #5f6c67); font-size: 12px; } strong { font-size: 20px; font-variant-numeric: tabular-nums; } > .el-icon { flex-shrink: 0; color: var(--primary-color, #176b73); }
}
.health-line { margin-bottom: 12px; padding: 12px 14px; background: var(--color-surface-subtle, #f7f9f8); border: 1px solid var(--color-border-light, #e8edeb); border-radius: 6px; > div { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 9px; color: var(--color-text-secondary, #5f6c67); font-size: 12px; } strong { color: var(--color-text-primary, #18221f); font-size: 15px; font-variant-numeric: tabular-nums; } }

.delivery-panel { margin-bottom: 16px; }
.delivery-layout { display: grid; grid-template-columns: minmax(0, 1fr) 260px; gap: 20px; min-height: 280px; }
.chart-region { min-width: 0; }
.overview-chart { width: 100%; height: 270px; }
.delivery-facts, .finance-summary, .work-status-list, .mobile-finance-list dl { margin: 0; }
.delivery-facts {
  display: grid; align-content: center; grid-template-columns: repeat(2, minmax(0, 1fr)); border-left: 1px solid var(--color-border, #dce3e0);
  div { min-width: 0; padding: 16px; } dt { color: var(--color-text-secondary, #5f6c67); font-size: 12px; } dd { margin: 6px 0 0; font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }
}

.business-tabs { :deep(.el-tabs__header) { margin-bottom: 12px; } :deep(.el-tabs__item) { height: 38px; font-size: 13px; } }
.tab-action { display: flex; justify-content: flex-end; min-height: 32px; margin-top: -6px; }
.finance-summary {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 14px; padding: 12px 0; background: var(--color-surface-subtle, #f7f9f8); border: 1px solid var(--color-border-light, #e8edeb); border-radius: 6px;
  div { min-width: 0; padding: 0 14px; & + div { border-left: 1px solid var(--color-border, #dce3e0); } } dt { color: var(--color-text-secondary, #5f6c67); font-size: 12px; } dd { margin: 5px 0 0; overflow-wrap: anywhere; font-size: 16px; font-weight: 650; font-variant-numeric: tabular-nums; }
}
.finance-table { width: 100%; :deep(.el-table__inner-wrapper::before) { display: none; } :deep(th.el-table__cell) { color: var(--color-text-secondary, #5f6c67); background: var(--color-surface-subtle, #f7f9f8); font-weight: 600; } }
.danger { color: var(--color-danger, #b64242) !important; }
.mobile-finance-list > div { padding: 13px 0; border-bottom: 1px solid var(--color-border-light, #e8edeb); header { display: flex; align-items: center; justify-content: space-between; gap: 12px; strong { min-width: 0; overflow: hidden; font-size: 14px; text-overflow: ellipsis; white-space: nowrap; } } dl { display: flex; flex-direction: column; gap: 7px; margin-top: 10px; div { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; min-width: 0; } } dt { flex-shrink: 0; color: var(--color-text-secondary, #5f6c67); font-size: 12px; } dd { min-width: 0; max-width: 68%; margin: 0; overflow-wrap: anywhere; font-size: 13px; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; } }

.business-row { min-height: 60px; padding: 9px 6px; border-bottom: 1px solid var(--color-border-light, #e8edeb); }
button.business-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(160px, 0.45fr) 16px; align-items: center; gap: 14px; cursor: pointer; &:hover { background: var(--color-surface-subtle, #f7f9f8); } > .el-icon { color: var(--color-text-tertiary, #7c8984); } }
.ip-progress { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.activity-row { display: grid; grid-template-columns: 8px minmax(0, 1fr) auto; align-items: center; gap: 10px; }
.activity-dot { width: 7px; height: 7px; background: var(--primary-color, #176b73); border-radius: 50%; }
.work-status-list {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--color-border, #dce3e0); border-radius: 6px; overflow: hidden;
  > div { display: grid; justify-items: center; min-width: 0; padding: 22px 8px; & + div { border-left: 1px solid var(--color-border, #dce3e0); } }
  span { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; color: var(--color-text-tertiary, #7c8984); background: rgba(124, 137, 132, 0.1); border-radius: 6px; &[data-tone='success'] { color: var(--color-success, #237a55); background: rgba(35, 122, 85, 0.1); } &[data-tone='warning'] { color: var(--color-warning, #a66116); background: rgba(166, 97, 22, 0.1); } }
  dt { margin-top: 8px; color: var(--color-text-secondary, #5f6c67); font-size: 12px; } dd { margin: 4px 0 0; font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }
}

@media screen and (max-width: 1180px) {
  .signal-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .priority-grid { grid-template-columns: minmax(0, 1fr); }
}
@media screen and (max-width: 768px) {
  .dashboard-view { padding-bottom: 20px; }
  .workbench-header { align-items: flex-start; flex-direction: column; margin-bottom: 14px; }
  .header-actions { width: 100%; :deep(.el-button:not(.is-circle)) { flex: 1; } }
  .signal-grid { gap: 10px; }
  .signal-card { min-height: 116px; padding: 14px; > strong { font-size: 24px; } }
  .workspace-panel { padding: 16px; }
  .delivery-layout { grid-template-columns: minmax(0, 1fr); min-height: 0; }
  .delivery-facts { border-top: 1px solid var(--color-border, #dce3e0); border-left: 0; }
  .overview-chart { height: 250px; }
  .todo-row { grid-template-columns: 4px minmax(0, 1fr) 16px; .row-meta { display: none; } }
  .risk-row { grid-template-columns: 32px minmax(0, 1fr) 16px; .el-tag { display: none; } }
  button.business-row { grid-template-columns: minmax(0, 1fr) 16px; .ip-progress { grid-column: 1; } }
  .activity-row { grid-template-columns: 8px minmax(0, 1fr); .row-meta { grid-column: 2; align-items: center; flex-direction: row; } }
}
@media screen and (max-width: 520px) {
  .signal-grid, .queue-links, .finance-summary, .work-status-list { grid-template-columns: minmax(0, 1fr); }
  .signal-card { min-height: 106px; }
  .queue-links button + button, .finance-summary div + div, .work-status-list > div + div { border-top: 1px solid var(--color-border, #dce3e0); border-left: 0; }
  .finance-summary div { padding: 9px 14px; }
  .delivery-facts { grid-template-columns: minmax(0, 1fr); div { display: flex; align-items: center; justify-content: space-between; padding: 10px 6px; border-bottom: 1px solid var(--color-border-light, #e8edeb); } dd { margin: 0; font-size: 18px; } }
  .work-status-list > div { grid-template-columns: 32px minmax(0, 1fr) auto; align-items: center; justify-items: start; gap: 10px; padding: 10px 12px; } .work-status-list dt, .work-status-list dd { margin: 0; } .work-status-list dd { font-size: 18px; }
}
</style>
