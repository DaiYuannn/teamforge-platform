<template>
  <div class="activity-feed">
    <PageHeader title="动态" />

    <!-- ==================== GitHub 风格贡献热力图 ==================== -->
    <el-card shadow="never" class="calendar-card">
      <div class="calendar-header">
        <span class="calendar-title">{{ totalContributions }} 次动态在过去半年</span>
      </div>

      <div class="calendar-wrapper">
        <!-- 星期标签（左侧，固定不随横向滚动） -->
        <div class="weekday-labels">
          <div class="weekday-label"></div>
          <div class="weekday-label">一</div>
          <div class="weekday-label"></div>
          <div class="weekday-label">三</div>
          <div class="weekday-label"></div>
          <div class="weekday-label">五</div>
          <div class="weekday-label"></div>
        </div>

        <!-- 月份标签 + 网格（可横向滚动） -->
        <div class="calendar-scroll">
          <div class="month-labels">
            <div
              v-for="(label, idx) in monthLabels"
              :key="idx"
              class="month-label"
            >
              {{ label }}
            </div>
          </div>

          <div class="calendar-grid">
            <div
              v-for="day in calendarGrid"
              :key="day.date"
              class="calendar-cell"
              :class="day.future ? 'level-future' : 'level-' + cellLevel(day.count)"
              @mouseenter="onCellHover($event, day)"
              @mouseleave="hoveredDay = null"
            ></div>
          </div>
        </div>
      </div>

      <!-- 图例 -->
      <div class="calendar-footer">
        <div class="calendar-legend">
          <span>少</span>
          <div class="legend-cell level-0"></div>
          <div class="legend-cell level-1"></div>
          <div class="legend-cell level-2"></div>
          <div class="legend-cell level-3"></div>
          <div class="legend-cell level-4"></div>
          <span>多</span>
        </div>
      </div>

      <!-- 悬浮提示 -->
      <div
        v-if="hoveredDay"
        class="calendar-tooltip"
        :style="{ left: tooltipLeft + 'px', top: tooltipTop + 'px' }"
      >
        {{ hoveredDay.count }} 次动态于 {{ hoveredDay.dateLabel }}
      </div>
    </el-card>

    <!-- ==================== 动态列表 ==================== -->
    <el-card shadow="never" class="mt-16">
      <div class="toolbar">
        <el-select
          v-model="filterType"
          placeholder="全部类型"
          clearable
          style="width: 180px"
          @change="onFilterChange"
        >
          <el-option label="创建项目" value="project_created" />
          <el-option label="更新项目" value="project_updated" />
          <el-option label="创建任务" value="task_created" />
          <el-option label="完成任务" value="task_completed" />
          <el-option label="上传文件" value="file_uploaded" />
          <el-option label="发表评论" value="comment_created" />
          <el-option label="成员加入" value="member_joined" />
        </el-select>
      </div>

      <div v-loading="loading" class="timeline">
        <div v-if="activities.length === 0 && !loading" class="empty">
          <el-empty description="暂无动态" />
        </div>

        <template v-for="group in groupedActivities" :key="group.key">
          <div class="date-group-header">{{ group.label }}</div>
          <div
            v-for="item in group.items"
            :key="item.id"
            class="activity-item"
          >
            <div class="activity-icon">
              <el-icon :size="18" :color="getIconColor(item.activity_type)">
                <component :is="getIconName(item.activity_type)" />
              </el-icon>
            </div>
            <div class="activity-content">
              <div class="activity-header">
                <span class="actor-name">{{ item.actor_name || '系统' }}</span>
                <el-tag size="small" type="info">{{ item.type_display }}</el-tag>
                <span class="time">{{ formatRelativeTime(item.created_at) }}</span>
              </div>
              <p class="activity-desc">{{ item.description }}</p>
              <div v-if="item.project_name" class="project-link">
                <el-icon><Folder /></el-icon>
                <span>{{ item.project_name }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Folder, Plus, Edit, Check, Upload, ChatDotRound, User } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { get } from '@/api/request'

// ============================================
// 动态列表状态
// ============================================
const loading = ref(false)
const activities = ref<any[]>([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filterType = ref('')

// ============================================
// 贡献日历状态
// ============================================
const WEEKS = 26 // 26 周 ≈ 182 天
const calendarData = ref<Map<string, number>>(new Map())
const hoveredDay = ref<CalendarCell | null>(null)
const tooltipLeft = ref(0)
const tooltipTop = ref(0)

interface CalendarCell {
  date: string
  dateLabel: string
  count: number
  future: boolean
}

// ============================================
// 图标与颜色映射
// ============================================
function getIconName(type: string): any {
  const map: Record<string, any> = {
    project_created: Plus,
    project_updated: Edit,
    project_closed: Check,
    task_created: Plus,
    task_completed: Check,
    task_updated: Edit,
    file_uploaded: Upload,
    comment_created: ChatDotRound,
    member_joined: User,
    member_left: User,
  }
  return map[type] || Edit
}

function getIconColor(type: string): string {
  if (type.includes('created')) return '#67C23A'
  if (type.includes('completed')) return '#409EFF'
  if (type.includes('uploaded')) return '#E6A23C'
  if (type.includes('comment')) return '#909399'
  return '#409EFF'
}

// ============================================
// 日期工具
// ============================================
function todayMidnight(): Date {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
}

/** 将日期/ISO 字符串转换为本地日期键 YYYY-MM-DD */
function toDateKey(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** 中文日期标签：2026年7月5日 */
function formatDateLabel(date: Date): string {
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

// ============================================
// 日历网格计算
// ============================================

/**
 * 构建 26 周 × 7 天的网格。
 * 最后一列为本周（包含今天），未来日期标记为透明不可交互。
 */
const calendarGrid = computed<CalendarCell[]>(() => {
  const today = todayMidnight()
  const dayOfWeek = today.getDay() // 0=周日
  // 本周周日
  const thisSunday = new Date(today)
  thisSunday.setDate(today.getDate() - dayOfWeek)
  // 网格起始日 = 本周周日往前推 25 周
  const startDate = new Date(thisSunday)
  startDate.setDate(thisSunday.getDate() - (WEEKS - 1) * 7)

  const cells: CalendarCell[] = []
  for (let w = 0; w < WEEKS; w++) {
    for (let d = 0; d < 7; d++) {
      const date = new Date(startDate)
      date.setDate(startDate.getDate() + w * 7 + d)
      const dateKey = toDateKey(date)
      const future = date.getTime() > today.getTime()
      const count = future ? 0 : (calendarData.value.get(dateKey) || 0)
      cells.push({
        date: dateKey,
        dateLabel: formatDateLabel(date),
        count,
        future,
      })
    }
  }
  return cells
})

/** 月份标签：按周列对齐，每周列取该周周日的月份，月份变化时显示 */
const monthLabels = computed<string[]>(() => {
  const today = todayMidnight()
  const dayOfWeek = today.getDay()
  const thisSunday = new Date(today)
  thisSunday.setDate(today.getDate() - dayOfWeek)
  const startDate = new Date(thisSunday)
  startDate.setDate(thisSunday.getDate() - (WEEKS - 1) * 7)

  const labels: string[] = []
  let lastMonth = -1
  for (let w = 0; w < WEEKS; w++) {
    const weekStart = new Date(startDate)
    weekStart.setDate(startDate.getDate() + w * 7)
    const m = weekStart.getMonth()
    if (m !== lastMonth) {
      labels.push(`${m + 1}月`)
      lastMonth = m
    } else {
      labels.push('')
    }
  }
  return labels
})

/** 半年内的动态总数 */
const totalContributions = computed<number>(() => {
  let sum = 0
  calendarData.value.forEach((v) => (sum += v))
  return sum
})

/** 根据当日动态数量返回颜色等级 0-4 */
function cellLevel(count: number): number {
  if (count === 0) return 0
  if (count <= 2) return 1
  if (count <= 5) return 2
  if (count <= 9) return 3
  return 4
}

/** 单元格悬浮：记录提示位置（相对日历卡片） */
function onCellHover(e: MouseEvent, day: CalendarCell): void {
  hoveredDay.value = day
  const card = (e.currentTarget as HTMLElement).closest('.calendar-card') as HTMLElement | null
  if (!card) return
  const rect = card.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  // 估算提示宽度，靠近右边缘时向左偏移避免溢出
  const estWidth = 200
  tooltipLeft.value = x + 14 + estWidth > rect.width ? x - 14 - estWidth : x + 14
  tooltipTop.value = y + 14
}

// ============================================
// 动态列表按日期分组
// ============================================
const groupedActivities = computed<{ key: string; label: string; items: any[] }[]>(() => {
  const groups: { key: string; label: string; items: any[] }[] = []
  const today = todayMidnight()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)

  let currentKey = ''
  for (const item of activities.value) {
    const d = new Date(item.created_at)
    d.setHours(0, 0, 0, 0)
    const key = toDateKey(d)
    if (key !== currentKey) {
      let label: string
      if (d.getTime() === today.getTime()) {
        label = '今天'
      } else if (d.getTime() === yesterday.getTime()) {
        label = '昨天'
      } else {
        label = formatDateLabel(d)
      }
      groups.push({ key, label, items: [] })
      currentKey = key
    }
    groups[groups.length - 1].items.push(item)
  }
  return groups
})

// ============================================
// 数据加载
// ============================================

/** 加载动态列表（分页，page_size=20） */
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize }
    if (filterType.value) params.type = filterType.value
    const res = await get<any>('/activities/', params)
    activities.value = res.results || res
    total.value = res.count || activities.value.length
  } catch {
    // 已由拦截器统一提示
  } finally {
    loading.value = false
  }
}

/**
 * 加载日历数据：以 page_size=500 拉取动态并按日期聚合。
 * 若存在更多分页则继续拉取（最多 20 页兜底），保证热力图数据完整。
 */
async function loadCalendarData(): Promise<void> {
  try {
    const counts = new Map<string, number>()
    const pageSizeCal = 500
    let currentPage = 1
    let hasMore = true
    let safety = 0

    while (hasMore && safety < 20) {
      const res = await get<any>('/activities/', {
        page: currentPage,
        page_size: pageSizeCal,
      })
      const list: any[] = res.results || (Array.isArray(res) ? res : [])
      list.forEach((item: any) => {
        if (!item?.created_at) return
        const key = toDateKey(item.created_at)
        counts.set(key, (counts.get(key) || 0) + 1)
      })
      const totalCount: number = res.count ?? list.length
      hasMore =
        res.next != null &&
        list.length === pageSizeCal &&
        currentPage * pageSizeCal < totalCount
      currentPage++
      safety++
    }
    calendarData.value = counts
  } catch {
    // 已由拦截器统一提示
  }
}

/** 筛选变更：重置页码后重新加载列表 */
function onFilterChange(): void {
  page.value = 1
  loadData()
}

onMounted(() => {
  loadData()
  loadCalendarData()
})
</script>

<style scoped>
/* ============================================
   贡献日历
   ============================================ */
.calendar-card {
  position: relative;
  margin-bottom: 16px;
}
.calendar-header {
  margin-bottom: 16px;
}
.calendar-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.calendar-wrapper {
  display: flex;
  align-items: flex-start;
}
/* 左侧星期标签：与网格行对齐 */
.weekday-labels {
  display: grid;
  grid-template-rows: repeat(7, 13px);
  row-gap: 3px;
  width: 22px;
  flex-shrink: 0;
  /* 顶部偏移 = 月份标签行高(16px) + 下边距(4px) */
  padding-top: 20px;
  margin-right: 4px;
}
.weekday-label {
  font-size: 10px;
  line-height: 13px;
  color: var(--el-text-color-secondary);
  text-align: right;
}
/* 可横向滚动的日历主体 */
.calendar-scroll {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
}
.month-labels {
  display: grid;
  grid-template-columns: repeat(26, 13px);
  column-gap: 3px;
  height: 16px;
  margin-bottom: 4px;
}
.month-label {
  font-size: 10px;
  line-height: 16px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
/* 网格：7 行，按列自动流动 */
.calendar-grid {
  display: grid;
  grid-template-rows: repeat(7, 13px);
  grid-auto-flow: column;
  grid-auto-columns: 13px;
  gap: 3px;
}
.calendar-cell {
  width: 13px;
  height: 13px;
  border-radius: 2px;
  cursor: pointer;
  transition: outline 0.1s ease;
}
.calendar-cell:hover {
  outline: 1px solid rgba(0, 0, 0, 0.25);
  outline-offset: -1px;
}
/* GitHub 配色 */
.level-0 {
  background-color: #ebedf0;
}
.level-1 {
  background-color: #9be9a8;
}
.level-2 {
  background-color: #40c463;
}
.level-3 {
  background-color: #30a14e;
}
.level-4 {
  background-color: #216e39;
}
.level-future {
  background-color: transparent;
  cursor: default;
  pointer-events: none;
}
.calendar-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.calendar-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
.legend-cell {
  width: 11px;
  height: 11px;
  border-radius: 2px;
}
.calendar-tooltip {
  position: absolute;
  z-index: 20;
  padding: 6px 10px;
  font-size: 12px;
  color: #fff;
  white-space: nowrap;
  background: rgba(0, 0, 0, 0.82);
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  pointer-events: none;
}

/* ============================================
   动态列表
   ============================================ */
.mt-16 {
  margin-top: 16px;
}
.toolbar {
  margin-bottom: 16px;
}
.timeline {
  min-height: 200px;
}
.empty {
  padding: 40px 0;
}
.date-group-header {
  padding: 12px 0 6px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: var(--el-text-color-secondary);
}
.date-group-header:first-child {
  padding-top: 0;
}
.activity-item {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.activity-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--el-fill-color-light);
}
.activity-content {
  flex: 1;
  min-width: 0;
}
.activity-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.actor-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.time {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.activity-desc {
  margin: 2px 0;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.project-link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-color-primary);
}
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ============================================
   响应式：小屏日历可横向滚动
   ============================================ */
@media screen and (max-width: 768px) {
  .calendar-scroll {
    overflow-x: auto;
  }
  .calendar-tooltip {
    display: none;
  }
}
</style>
