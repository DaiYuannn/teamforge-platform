<template>
  <div class="dashboard-view page-container">
    <!-- ==================== 1. 顶部统计卡片区域 ==================== -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :xs="12" :sm="8" :md="6" :lg="4" :xl="4">
        <div class="stat-card stat-blue">
          <div class="stat-icon">
            <el-icon size="30"><Folder /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboardData?.project_overview?.total || 0 }}</div>
            <div class="stat-label">项目总数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6" :lg="4" :xl="4">
        <div class="stat-card stat-green">
          <div class="stat-icon">
            <el-icon size="30"><Promotion /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboardData?.project_overview?.active || 0 }}</div>
            <div class="stat-label">进行中项目</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6" :lg="4" :xl="4">
        <div class="stat-card stat-orange">
          <div class="stat-icon">
            <el-icon size="30"><List /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ pendingTaskCount }}</div>
            <div class="stat-label">待完成任务</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6" :lg="4" :xl="4">
        <div class="stat-card stat-red">
          <div class="stat-icon">
            <el-icon size="30"><WarningFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboardData?.task_overview?.overdue || 0 }}</div>
            <div class="stat-label">已逾期任务</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6" :lg="4" :xl="4">
        <div class="stat-card stat-purple">
          <div class="stat-icon">
            <el-icon size="30"><Money /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ formatMoneyWithComma(dashboardData?.finance_overview?.total_income) }}</div>
            <div class="stat-label">经费总额</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ==================== 2. 项目进度环形图 + 比赛节点日历 ==================== -->
    <el-row :gutter="16" class="mt-16">
      <el-col :xs="24" :lg="10">
        <div class="card">
          <h3 class="card-title">项目进度分布</h3>
          <div ref="projectChartRef" class="chart-container"></div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="14">
        <div class="card">
          <h3 class="card-title">比赛节点日历</h3>
          <el-timeline class="competition-timeline">
            <el-timeline-item
              v-for="(event, idx) in competitionEvents"
              :key="event.id ?? idx"
              :timestamp="formatDate(event.start)"
              placement="top"
              :color="getCompetitionColor(event)"
            >
              <div class="competition-item">
                <span class="competition-title">{{ event.title }}</span>
                <el-tag size="small" :type="getCompetitionStatusType(event)" class="competition-tag">
                  {{ getCompetitionStatusLabel(event) }}
                </el-tag>
              </div>
            </el-timeline-item>
            <EmptyState v-if="competitionEvents.length === 0" text="暂无比赛节点" icon="Calendar" />
          </el-timeline>
        </div>
      </el-col>
    </el-row>

    <!-- ==================== 3. 经费总览表格 + 任务状态柱状图 ==================== -->
    <el-row :gutter="16" class="mt-16">
      <el-col :xs="24" :lg="14">
        <div class="card">
          <h3 class="card-title">经费总览</h3>
          <!-- PC端表格 -->
          <el-table v-if="!isMobile" :data="financeTop5" border stripe size="small">
            <el-table-column prop="project_name" label="项目名称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="budget" label="预算" width="120" align="right">
              <template #default="{ row }">{{ formatMoneyWithComma(row.budget) }}</template>
            </el-table-column>
            <el-table-column prop="expense" label="已使用" width="120" align="right">
              <template #default="{ row }">{{ formatMoneyWithComma(row.expense) }}</template>
            </el-table-column>
            <el-table-column prop="remaining" label="剩余" width="120" align="right">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.remaining < 0 }">
                  {{ formatMoneyWithComma(row.remaining) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="getFinanceStatusType(row)" size="small">
                  {{ getFinanceStatusLabel(row) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <!-- 移动端卡片 -->
          <div v-else class="finance-mobile-list">
            <div v-for="(item, idx) in financeTop5" :key="item.project_name ?? idx" class="finance-mobile-item">
              <div class="finance-mobile-name">{{ item.project_name }}</div>
              <div class="finance-mobile-rows">
                <span><span class="label">预算：</span>{{ formatMoneyWithComma(item.budget) }}</span>
                <span><span class="label">已用：</span>{{ formatMoneyWithComma(item.expense) }}</span>
                <span><span class="label">剩余：</span><span :class="{ 'text-danger': item.remaining < 0 }">{{ formatMoneyWithComma(item.remaining) }}</span></span>
              </div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="10">
        <div class="card">
          <h3 class="card-title">任务状态分布</h3>
          <div ref="taskChartRef" class="chart-container"></div>
        </div>
      </el-col>
    </el-row>

    <!-- ==================== 4. 知识产权申请状态 + 成员灵活工作时间 ==================== -->
    <el-row :gutter="16" class="mt-16">
      <el-col :xs="24" :lg="14">
        <div class="card">
          <h3 class="card-title">知识产权申请状态</h3>
          <div class="ip-status-list">
            <div v-for="(ip, idx) in ipApplications" :key="ip.id ?? idx" class="ip-status-item">
              <div class="ip-status-header">
                <span class="ip-status-title" @click="goToIPDetail(ip.id)">{{ ip.title }}</span>
                <el-tag :type="getIPStatusTagType(ip.status)" size="small" effect="dark">
                  {{ IP_STATUS_MAP[ip.status]?.label || ip.status }}
                </el-tag>
              </div>
              <el-progress
                :percentage="getIPProgress(ip.status)"
                :color="getIPProgressColor(ip.status)"
                :show-text="false"
                :stroke-width="8"
              />
            </div>
            <EmptyState v-if="ipApplications.length === 0" text="暂无知识产权申请" icon="Document" />
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="10">
        <div class="card">
          <h3 class="card-title">成员灵活工作时间</h3>
          <div class="work-status-cards">
            <div class="work-status-item available">
              <el-icon size="28" class="work-icon"><CircleCheckFilled /></el-icon>
              <div class="work-status-value">{{ workStatus.available }}</div>
              <div class="work-status-label">可投入人数</div>
            </div>
            <div class="work-status-item saturated">
              <el-icon size="28" class="work-icon"><WarningFilled /></el-icon>
              <div class="work-status-value">{{ workStatus.saturated }}</div>
              <div class="work-status-label">饱和人数</div>
            </div>
            <div class="work-status-item leave">
              <el-icon size="28" class="work-icon"><RemoveFilled /></el-icon>
              <div class="work-status-value">{{ workStatus.leave }}</div>
              <div class="work-status-label">请假/有事人数</div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ==================== 5. 最近贡献动态 + 风险提醒 + 最近通知 ==================== -->
    <el-row :gutter="16" class="mt-16">
      <!-- 最近贡献动态 -->
      <el-col :xs="24" :lg="8">
        <div class="card">
          <h3 class="card-title">最近贡献动态</h3>
          <el-timeline class="contribution-timeline">
            <el-timeline-item
              v-for="(item, idx) in recentContributions"
              :key="item.id ?? idx"
              :timestamp="formatRelativeTime(item.created_at)"
              placement="top"
              :color="getContributionColor(item.contribution_type)"
            >
              <div class="contribution-content">
                <div class="contribution-header">
                  <span class="contribution-user">{{ item.user_name }}</span>
                  <el-tag :type="CONTRIBUTION_TYPE_MAP[item.contribution_type]?.tagType as any" size="small">
                    {{ CONTRIBUTION_TYPE_MAP[item.contribution_type]?.label || item.contribution_type }}
                  </el-tag>
                </div>
                <p class="contribution-text">{{ item.content }}</p>
                <span class="contribution-project">{{ item.project_name || '-' }}</span>
              </div>
            </el-timeline-item>
            <EmptyState v-if="recentContributions.length === 0" text="暂无贡献动态" icon="Trophy" />
          </el-timeline>
        </div>
      </el-col>
      <!-- 风险提醒 -->
      <el-col :xs="24" :lg="8">
        <div class="card">
          <h3 class="card-title">风险提醒</h3>
          <div class="risk-list">
            <el-alert
              v-for="(alert, idx) in dashboardData?.risk_alerts?.items"
              :key="idx"
              :title="alert.message"
              :type="getRiskAlertType(alert.type) as any"
              :closable="false"
              show-icon
              class="risk-alert-item"
            />
            <EmptyState v-if="!dashboardData?.risk_alerts?.items?.length" text="暂无风险提醒" icon="CircleCheck" />
          </div>
        </div>
      </el-col>
      <!-- 最近通知 -->
      <el-col :xs="24" :lg="8">
        <div class="card">
          <h3 class="card-title">最近通知</h3>
          <div class="notification-list">
            <div v-for="(notice, idx) in recentNotifications" :key="notice.id ?? idx" class="notification-item">
              <div class="notification-header">
                <el-tag :type="getNoticeTagType(notice.category)" size="small">
                  {{ getNoticeLabel(notice.category) }}
                </el-tag>
                <span class="notification-time">{{ formatRelativeTime(notice.created_at) }}</span>
              </div>
              <div class="notification-title">{{ notice.title }}</div>
              <div class="notification-content">{{ notice.content }}</div>
            </div>
            <EmptyState v-if="recentNotifications.length === 0" text="暂无通知" icon="Bell" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ==================== 6. 待我处理事项 ==================== -->
    <el-row :gutter="16" class="mt-16">
      <el-col :span="24">
        <div class="card">
          <h3 class="card-title">待我处理事项</h3>
          <el-row :gutter="12">
            <el-col
              v-for="(todo, idx) in myTodos"
              :key="(todo.application_id ?? idx) + '_' + todo.type"
              :xs="24" :sm="12" :md="8" :lg="6"
            >
              <div
                class="todo-card"
                role="button"
                tabindex="0"
                @click="goToIPDetail(todo.application_id)"
                @keydown.enter="goToIPDetail(todo.application_id)"
              >
                <div class="todo-card-header">
                  <el-tag :type="getTodoTypeTag(todo.type)" size="small">{{ getTodoTypeLabel(todo.type) }}</el-tag>
                  <el-tag v-if="todo.deadline" size="small" :type="getDeadlineColor(todo.deadline) as any">
                    {{ formatDate(todo.deadline) }}
                  </el-tag>
                </div>
                <div class="todo-card-title">{{ todo.title }}</div>
                <div class="todo-card-desc">{{ todo.description }}</div>
                <div class="todo-card-footer">
                  <span class="todo-card-time">{{ formatRelativeTime(todo.created_at) }}</span>
                  <el-button type="primary" link size="small">去处理</el-button>
                </div>
              </div>
            </el-col>
          </el-row>
          <EmptyState v-if="myTodos.length === 0" text="暂无待处理事项" icon="Finished" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getDashboardData } from '@/api/dashboard'
import { getAllLatestSchedules } from '@/api/members'
import { getContributions } from '@/api/contributions'
import { getIPApplications } from '@/api/intellectualProperty'
import { getNotifications } from '@/api/notifications'
import { getMyIPTodo } from '@/api/intellectualProperty'
import {
  formatDate,
  formatRelativeTime,
  formatMoneyWithComma,
} from '@/utils/format'
import {
  CONTRIBUTION_TYPE_MAP,
  IP_STATUS_MAP,
  NOTIFICATION_CATEGORY_MAP,
} from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import type { DashboardData, Contribution } from '@/types'
import type { IPTodoItem } from '@/types/intellectualProperty'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const { isMobile } = useDevice()

// 驾驶舱数据
const dashboardData = ref<DashboardData | null>(null)

// 成员工作状态
const workStatus = reactive({
  available: 0,
  saturated: 0,
  leave: 0,
})

// 最近贡献动态
const recentContributions = ref<Contribution[]>([])

// 知识产权申请列表（前5条）
const ipApplications = ref<any[]>([])

// 最近通知
const recentNotifications = ref<any[]>([])

// 待我处理事项
const myTodos = ref<IPTodoItem[]>([])

// 项目进度环形图
const projectChartRef = ref<HTMLElement>()
let projectChart: echarts.ECharts | null = null

// 任务状态柱状图
const taskChartRef = ref<HTMLElement>()
let taskChart: echarts.ECharts | null = null

// 待完成任务数（待办 + 进行中）
const pendingTaskCount = computed(() => {
  const stats = dashboardData.value?.task_overview
  if (!stats?.status_distribution) return 0
  const todo = stats.status_distribution?.todo?.count || 0
  const doing = stats.status_distribution?.doing?.count || 0
  return todo + doing
})

function toAmount(value: number | string | null | undefined): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

// 经费前5条（从 finance_overview.project_finance 中取）
const financeTop5 = computed(() => {
  const list = dashboardData.value?.finance_overview?.project_finance || []
  return list.slice(0, 5).map((item: any) => ({
    project_name: item.project_name,
    budget: toAmount(item.bonus_amount) + toAmount(item.other_income),
    expense: toAmount(item.used_amount),
    remaining: toAmount(item.remaining_amount),
    status: item.status,
  }))
})

// 比赛节点事件（从日历事件中筛选比赛类型）
const competitionEvents = computed(() => {
  return (dashboardData.value?.calendar_events || []).filter((e: any) => e.type === 'competition')
})

// ==================== 辅助函数 ====================

// 风险提醒 el-alert 类型映射（根据后端 type 字段）
function getRiskAlertType(type: string): string {
  if (type === 'overdue_task') return 'error'
  if (type === 'stale_project') return 'warning'
  if (type === 'upcoming_competition') return 'warning'
  return 'info'
}

// 贡献类型颜色
function getContributionColor(type: string): string {
  const map: Record<string, string> = {
    code: '#409EFF',
    document: '#67C23A',
    design: '#E6A23C',
    test: '#909399',
    research: '#9B59B6',
    management: '#F56C6C',
    presentation: '#36CFC9',
    other: '#909399',
  }
  return map[type] || '#409EFF'
}

// 比赛节点颜色
function getCompetitionColor(event: any): string {
  const now = new Date()
  const eventDate = new Date(event.start)
  if (eventDate < now) return '#909399'
  const diffDays = (eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  if (diffDays <= 7) return '#F56C6C'
  if (diffDays <= 30) return '#E6A23C'
  return '#67C23A'
}

// 比赛节点状态标签类型
function getCompetitionStatusType(event: any): any {
  const now = new Date()
  const eventDate = new Date(event.start)
  if (eventDate < now) return 'info' as any
  const diffDays = (eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  if (diffDays <= 7) return 'danger' as any
  if (diffDays <= 30) return 'warning' as any
  return 'success' as any
}

// 比赛节点状态标签文字
function getCompetitionStatusLabel(event: any): string {
  const now = new Date()
  const eventDate = new Date(event.start)
  if (eventDate < now) return '已结束'
  const diffDays = (eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  if (diffDays <= 7) return '即将开始'
  if (diffDays <= 30) return '准备中'
  return '计划中'
}

// 经费状态标签类型
function getFinanceStatusType(row: any): any {
  if (row.remaining < 0) return 'danger' as any
  if (row.budget > 0 && row.expense / row.budget > 0.8) return 'warning' as any
  return 'success' as any
}

// 经费状态标签文字
function getFinanceStatusLabel(row: any): string {
  if (row.remaining < 0) return '超支'
  if (row.budget > 0 && row.expense / row.budget > 0.8) return '接近预算'
  return '正常'
}

// 知识产权状态Tag类型
function getIPStatusTagType(status: string): any {
  return (IP_STATUS_MAP[status]?.color || 'info') as any
}

// 知识产权进度百分比
function getIPProgress(status: string): number {
  const step = IP_STATUS_MAP[status]?.step ?? 0
  if (step < 0) return 0
  return Math.round((step / 10) * 100)
}

// 知识产权进度颜色
function getIPProgressColor(status: string): string {
  const color = IP_STATUS_MAP[status]?.color
  if (color === 'danger') return '#F56C6C'
  if (color === 'warning') return '#E6A23C'
  if (color === 'success') return '#67C23A'
  if (color === 'info') return '#909399'
  return '#409EFF'
}

// 通知分类标签类型
function getNoticeTagType(category: string): any {
  return (NOTIFICATION_CATEGORY_MAP[category]?.type || 'info') as any
}

// 通知分类标签文字
function getNoticeLabel(category: string): string {
  return NOTIFICATION_CATEGORY_MAP[category]?.label || category
}

// 待办类型标签
function getTodoTypeLabel(type: string): string {
  const map: Record<string, string> = {
    writing: '撰写',
    return_fix: '退回修改',
    submit: '提交',
    review: '审核',
    confirm: '确认',
    objection: '异议处理',
    my_objection: '我的异议',
  }
  return map[type] || type
}

// 待办类型标签颜色
function getTodoTypeTag(type: string): any {
  const map: Record<string, string> = {
    writing: '',
    return_fix: 'danger',
    submit: 'success',
    review: 'warning',
    confirm: 'warning',
    objection: 'info',
    my_objection: 'info',
  }
  return (map[type] || 'info') as any
}

// 截止时间颜色
function getDeadlineColor(deadline: string): any {
  const now = new Date()
  const dl = new Date(deadline)
  if (dl < now) return 'danger' as any
  const diffDays = (dl.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  if (diffDays <= 3) return 'warning' as any
  return 'info' as any
}

// 跳转知识产权详情
function goToIPDetail(id: number): void {
  router.push(`/intellectual-property/${id}`)
}

// ==================== 图表统一配色与样式（P3-3） ====================

/** 统一配色方案：主色 #409EFF，辅色 #67C23A / #E6A23C / #F56C6C / #9B59B6 */
const CHART_COLORS = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#9B59B6', '#36CFC9']

/** 通用 tooltip 样式 */
const CHART_TOOLTIP_STYLE = {
  backgroundColor: 'rgba(255, 255, 255, 0.96)',
  borderColor: '#e4e7ed',
  borderWidth: 1,
  padding: [8, 12],
  textStyle: {
    color: '#303133',
    fontSize: 12,
  },
  extraCssText: 'box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12); border-radius: 6px;',
}

/** 生成线性渐变（用于柱状图填充） */
function makeLinearGradient(color: string, direction: 'vertical' | 'horizontal' = 'vertical'): any {
  const coords = direction === 'vertical' ? { x: 0, y: 0, x2: 0, y2: 1 } : { x: 0, y: 0, x2: 1, y2: 0 }
  return {
    type: 'linear',
    ...coords,
    colorStops: [
      { offset: 0, color: color },
      { offset: 1, color: color + '66' }, // 40% 透明度
    ],
  }
}

// ==================== 图表渲染 ====================

// 渲染项目进度环形图
function renderProjectChart(): void {
  if (!projectChartRef.value || !dashboardData.value) return

  if (!projectChart) {
    projectChart = echarts.init(projectChartRef.value)
  }
  projectChart.showLoading('default', {
    text: '加载中...',
    color: CHART_COLORS[0],
    textColor: '#909399',
    maskColor: 'rgba(255, 255, 255, 0.8)',
    zlevel: 0,
  })

  const stats = dashboardData.value.project_overview || ({} as any)

  const series = [
    { value: stats.active, name: '进行中' },
    { value: stats.closed, name: '已完成' },
    { value: stats.paused, name: '规划中' },
  ].filter((d) => d.value > 0)

  const pieData = series.map((d, i) => ({
    ...d,
    itemStyle: {
      color: makeLinearGradient(CHART_COLORS[i], 'vertical'),
      borderRadius: 6,
      borderColor: '#fff',
      borderWidth: 2,
    },
  }))

  projectChart.setOption({
    color: CHART_COLORS,
    tooltip: {
      trigger: 'item',
      formatter: '{b}: <b>{c}</b> ({d}%)',
      ...CHART_TOOLTIP_STYLE,
    },
    legend: { bottom: '5%', left: 'center', textStyle: { fontSize: 12, color: '#606266' } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#303133' },
          itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0, 0, 0, 0.15)' },
        },
        data: pieData.length > 0 ? pieData : [{ value: 1, name: '暂无数据', itemStyle: { color: '#e0e0e0' } }],
      },
    ],
  } as any)
  projectChart.hideLoading()
}

// 渲染任务状态柱状图
function renderTaskChart(): void {
  if (!taskChartRef.value || !dashboardData.value) return

  if (!taskChart) {
    taskChart = echarts.init(taskChartRef.value)
  }
  taskChart.showLoading('default', {
    text: '加载中...',
    color: CHART_COLORS[0],
    textColor: '#909399',
    maskColor: 'rgba(255, 255, 255, 0.8)',
    zlevel: 0,
  })

  const stats = dashboardData.value.task_overview || ({} as any)
  const dist = stats.status_distribution || {}

  const barColors = ['#909399', '#409EFF', '#67C23A', '#F56C6C']
  const categories = ['待办', '进行中', '已完成', '已逾期']

  taskChart.setOption({
    color: barColors,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(64, 158, 255, 0.08)' } },
      ...CHART_TOOLTIP_STYLE,
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        return `<b>${p.name}</b><br/>数量：<b style="color:${p.color}">${p.value}</b>`
      },
    },
    grid: { left: '8%', right: '8%', bottom: '12%', top: '18%', containLabel: true },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { fontSize: 12, color: '#606266' },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 12, color: '#909399' },
      splitLine: { lineStyle: { color: '#ebeef5', type: 'dashed' } },
    },
    series: [
      {
        type: 'bar',
        data: categories.map((_, i) => {
          const key = ['todo', 'doing', 'done', 'overdue'][i]
          return {
            value: dist?.[key]?.count || 0,
            itemStyle: { color: makeLinearGradient(barColors[i], 'vertical'), borderRadius: [4, 4, 0, 0] },
          }
        }),
        barWidth: '42%',
        label: { show: true, position: 'top', color: '#606266', fontSize: 12, fontWeight: 600 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.15)' } },
      },
    ],
  } as any)
  taskChart.hideLoading()
}

// ==================== 数据加载 ====================

// 加载驾驶舱主数据
async function loadData(): Promise<void> {
  try {
    dashboardData.value = await getDashboardData()
    // 渲染图表
    await nextTick()
    renderProjectChart()
    renderTaskChart()
  } catch {
    // 错误已由拦截器处理
  }
  // 并行加载其他数据
  loadWorkStatus()
  loadRecentContributions()
  loadIPApplications()
  loadNotifications()
  loadMyTodos()
}

// 加载成员工作状态
async function loadWorkStatus(): Promise<void> {
  try {
    const res: any = await getAllLatestSchedules()
    const list = Array.isArray(res) ? res : (res.results || [])
    workStatus.available = list.filter((s: any) => !s.is_saturated && (s.work_hours || 0) > 0).length
    workStatus.saturated = list.filter((s: any) => s.is_saturated).length
    workStatus.leave = list.filter((s: any) => !s.work_hours || s.work_hours === 0).length
  } catch {
    // 忽略
  }
}

// 加载最近贡献动态
async function loadRecentContributions(): Promise<void> {
  try {
    const res: any = await getContributions({ page: 1, page_size: 5 })
    recentContributions.value = res.results || []
  } catch {
    // 忽略
  }
}

// 加载知识产权申请列表
async function loadIPApplications(): Promise<void> {
  try {
    const res: any = await getIPApplications({ page: 1, page_size: 5 })
    ipApplications.value = res.results || []
  } catch {
    // 忽略
  }
}

// 加载最近通知
async function loadNotifications(): Promise<void> {
  try {
    const res: any = await getNotifications({ page: 1, page_size: 5 })
    recentNotifications.value = res.results || []
  } catch {
    // 忽略
  }
}

// 加载待我处理事项
async function loadMyTodos(): Promise<void> {
  try {
    const res = await getMyIPTodo() as any
    myTodos.value = Array.isArray(res) ? res : (res?.data || res?.results || [])
  } catch {
    // 忽略
  }
}

// 窗口大小变化时重绘图表
function handleResize(): void {
  projectChart?.resize()
  taskChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  projectChart?.dispose()
  taskChart?.dispose()
})
</script>

<style lang="scss" scoped>
.dashboard-view {
  .mt-16 {
    margin-top: 16px;
  }

  /* ==================== 统计卡片 ==================== */
  .stat-cards {
    display: flex;
    flex-wrap: wrap;

    > .el-col {
      flex: 0 0 20%;
      max-width: 20%;
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
      min-height: 120px;
      height: 120px;
      overflow: hidden;

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

      &.stat-blue .stat-icon { background: linear-gradient(135deg, #409eff, #36cfc9); }
      &.stat-green .stat-icon { background: linear-gradient(135deg, #67c23a, #95de64); }
      &.stat-orange .stat-icon { background: linear-gradient(135deg, #e6a23c, #ffd591); }
      &.stat-red .stat-icon { background: linear-gradient(135deg, #f56c6c, #ff7875); }
      &.stat-purple .stat-icon { background: linear-gradient(135deg, #9b59b6, #c39bd3); }

      .stat-info {
        min-width: 0;

        .stat-value {
          font-size: 28px;
          font-weight: 700;
          color: #303133;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          font-variant-numeric: tabular-nums;
          font-feature-settings: 'tnum';
        }

        .stat-label {
          font-size: 14px;
          color: #909399;
          margin-top: 4px;
        }
      }
    }
  }

  /* ==================== 通用卡片 ==================== */
  .card {
    background: #fff;
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
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

  .chart-container {
    width: 100%;
    height: 300px;
  }

  /* ==================== 比赛节点时间线 ==================== */
  .competition-timeline {
    max-height: 300px;
    overflow-y: auto;
    padding: 8px;

    .competition-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;

      .competition-title {
        font-size: 14px;
        font-weight: 500;
        color: #303133;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  /* ==================== 经费移动端列表 ==================== */
  .finance-mobile-list {
    .finance-mobile-item {
      padding: 12px;
      border-bottom: 1px solid #ebeef5;

      &:last-child {
        border-bottom: none;
      }

      .finance-mobile-name {
        font-size: 14px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 8px;
      }

      .finance-mobile-rows {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 13px;
        color: #606266;

        .label {
          color: #909399;
        }
      }
    }
  }

  .text-danger {
    color: #f56c6c;
    font-weight: 600;
  }

  /* ==================== 知识产权申请状态 ==================== */
  .ip-status-list {
    display: flex;
    flex-direction: column;
    gap: 14px;

    .ip-status-item {
      .ip-status-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;

        .ip-status-title {
          font-size: 14px;
          font-weight: 500;
          color: #303133;
          cursor: pointer;
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          margin-right: 8px;

          &:hover {
            color: #409eff;
          }
        }
      }
    }
  }

  /* ==================== 成员工作状态 ==================== */
  .work-status-cards {
    display: flex;
    gap: 12px;

    .work-status-item {
      flex: 1;
      text-align: center;
      padding: 24px 12px;
      border-radius: 10px;

      &.available {
        background: linear-gradient(135deg, #e8f5e9, #c8e6c9);

        .work-icon {
          color: #67c23a;
        }
      }
      &.saturated {
        background: linear-gradient(135deg, #fff3e0, #ffe0b2);

        .work-icon {
          color: #e6a23c;
        }
      }
      &.leave {
        background: linear-gradient(135deg, #fce4ec, #f8bbd0);

        .work-icon {
          color: #f56c6c;
        }
      }

      .work-status-value {
        font-size: 28px;
        font-weight: 700;
        color: #303133;
        margin-top: 8px;
      }

      .work-status-label {
        font-size: 13px;
        color: #606266;
        margin-top: 4px;
      }
    }
  }

  /* ==================== 贡献动态时间线 ==================== */
  .contribution-timeline {
    max-height: 320px;
    overflow-y: auto;
    padding: 8px;

    .contribution-content {
      .contribution-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;

        .contribution-user {
          font-size: 14px;
          font-weight: 600;
          color: #303133;
        }
      }

      .contribution-text {
        font-size: 13px;
        color: #606266;
        margin: 4px 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .contribution-project {
        font-size: 12px;
        color: #909399;
      }
    }
  }

  /* ==================== 风险提醒 ==================== */
  .risk-list {
    max-height: 320px;
    overflow-y: auto;

    .risk-alert-item {
      margin-bottom: 10px;
    }
  }

  /* ==================== 最近通知 ==================== */
  .notification-list {
    max-height: 320px;
    overflow-y: auto;

    .notification-item {
      padding: 10px 0;
      border-bottom: 1px solid #ebeef5;

      &:last-child {
        border-bottom: none;
      }

      .notification-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
      }

      .notification-title {
        font-size: 14px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 4px;
      }

      .notification-content {
        font-size: 13px;
        color: #606266;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .notification-time {
        font-size: 12px;
        color: #909399;
      }
    }
  }

  /* ==================== 待我处理事项 ==================== */
  .todo-card {
    padding: 16px;
    background: #f9fafc;
    border-radius: 8px;
    border-left: 3px solid #409eff;
    cursor: pointer;
    transition: transform 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
    margin-bottom: 12px;
    height: calc(100% - 12px);

    &:hover {
      background: #ecf5ff;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
    }

    .todo-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 10px;
    }

    .todo-card-title {
      font-size: 14px;
      font-weight: 600;
      color: #303133;
      margin-bottom: 6px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .todo-card-desc {
      font-size: 13px;
      color: #606266;
      margin-bottom: 10px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .todo-card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .todo-card-time {
        font-size: 12px;
        color: #909399;
      }
    }
  }
}

/* ==================== 移动端适配 ==================== */
@media screen and (max-width: 768px) {
  .dashboard-view {
    .stat-cards {
      > .el-col {
        flex: 0 0 50%;
        max-width: 50%;
      }

      .stat-card {
        padding: 14px;
        gap: 10px;
        min-height: 110px;
        height: 110px;

        .stat-icon {
          width: 42px;
          height: 42px;
        }

        .stat-info {
          .stat-value {
            font-size: 18px;
          }

          .stat-label {
            font-size: 12px;
          }
        }
      }
    }

    .work-status-cards {
      flex-direction: column;
    }

    .chart-container {
      height: 250px;
    }
  }
}

/* ==================== 无障碍：降低动画 ==================== */
@media (prefers-reduced-motion: reduce) {
  .dashboard-view {
    .stat-card,
    .todo-card {
      transition: none;
      &:hover {
        transform: none;
      }
    }
  }
}
</style>
