<template>
  <div class="project-calendar-view page-container">
    <PageHeader title="项目日历" subtitle="全年项目事件密度热力图" />

    <!-- 筛选栏 -->
    <div class="surface-panel calendar-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-label">年份：</span>
        <el-select v-model="selectedYear" class="year-select">
          <el-option v-for="y in yearOptions" :key="y" :label="`${y} 年`" :value="y" />
        </el-select>

        <span class="toolbar-label">项目：</span>
        <el-select
          v-model="selectedProjectId"
          clearable
          filterable
          placeholder="全部项目"
          class="project-select"
          @change="loadCalendar"
        >
          <el-option
            v-for="p in projectOptions"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>
      </div>

      <div class="toolbar-right">
        <span class="legend-label">活跃度：</span>
        <span class="legend-item"><i class="legend-cell lv-1"></i>少</span>
        <span class="legend-item"><i class="legend-cell lv-2"></i></span>
        <span class="legend-item"><i class="legend-cell lv-3"></i></span>
        <span class="legend-item"><i class="legend-cell lv-4"></i>多</span>
      </div>
    </div>

    <!-- 日历热力图 -->
    <section class="surface-panel chart-panel">
      <div class="section-bar">
        <h2>年度事件分布</h2>
        <span>{{ totalEvents }} 条事件</span>
      </div>
      <div v-loading="loading" class="calendar-wrapper">
        <el-empty v-if="!loading && !hasData" description="该年度暂无事件数据" />
        <div v-show="hasData" class="calendar-scroll">
          <div ref="chartRef" class="calendar-chart"></div>
        </div>
      </div>
    </section>

    <!-- 当天事件列表 -->
    <section class="surface-panel day-events-panel">
      <div class="day-events-header">
        <h3 class="section-title">{{ selectedDate || '请点击日历选择日期' }}</h3>
        <span v-if="selectedDate" class="day-events-count">
          共 {{ selectedDayEvents.length }} 条事件
        </span>
      </div>

      <el-empty v-if="selectedDate && selectedDayEvents.length === 0" description="该日期无事件记录" />

      <div v-else-if="selectedDate" class="day-events-list">
        <div v-for="(event, idx) in selectedDayEvents" :key="idx" class="day-event-item">
          <el-tag :color="getLevelColor(event.level)" effect="dark" size="small">
            {{ calendarEventDisplayLabel(event) }}
          </el-tag>
          <span class="day-event-label">{{ event.label }}</span>
        </div>
      </div>

      <el-empty v-else description="点击上方日历的某一天，可查看当日事件详情" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import PageHeader from '@/components/PageHeader.vue'
import { getProjectCalendar, type CalendarDayItem } from '@/api/dashboard'
import { getProjects } from '@/api/projects'
import type { Project } from '@/types'
import { calendarEventDisplayLabel } from '@/utils/calendarEvents'

/**
 * 项目日历热力图页面
 * 使用 ECharts calendar 系列展示全年事件密度
 */

// 状态
const loading = ref(false)
const selectedYear = ref(new Date().getFullYear())
const selectedProjectId = ref<number | undefined>(undefined)
const calendarData = ref<CalendarDayItem[]>([])
const selectedDate = ref<string>('')
const projectOptions = ref<Project[]>([])

// 图表
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

// 年份选项（当前年份及前 4 年）
const yearOptions = computed(() => {
  const current = new Date().getFullYear()
  return [current, current - 1, current - 2, current - 3, current - 4]
})

// 是否有数据
const hasData = computed(() => calendarData.value.some((d) => d.count > 0))

const totalEvents = computed(() => calendarData.value.reduce((sum, day) => sum + day.count, 0))

// 选中日期对应的事件列表
const selectedDayEvents = computed(() => {
  if (!selectedDate.value) return []
  const day = calendarData.value.find((d) => d.date === selectedDate.value)
  return day?.events || []
})

// 获取级别颜色
function getLevelColor(level?: string): string {
  const map: Record<string, string> = {
    national: '#b64242',
    provincial: '#a66116',
    municipal: '#315c86',
    school: '#237a55',
    enterprise: '#76559b',
    high: '#b64242',
    medium: '#a66116',
    low: '#4c6475',
  }
  return map[level || ''] || '#176b73'
}

// 加载项目列表（用于筛选）
async function loadProjectOptions(): Promise<void> {
  try {
    const res = await getProjects({ page: 1, page_size: 200 } as any)
    projectOptions.value = res.results || []
  } catch {
    // 忽略
  }
}

// 加载日历数据
async function loadCalendar(): Promise<void> {
  loading.value = true
  selectedDate.value = ''
  try {
    const params: { year: number; project_id?: number } = { year: selectedYear.value }
    if (selectedProjectId.value) {
      params.project_id = selectedProjectId.value
    }
    const res = await getProjectCalendar(params)
    calendarData.value = res.calendar || []
    await nextTick()
    renderChart()
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 渲染热力图
function renderChart(): void {
  if (!chartRef.value) return

  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', (params: any) => {
      // 点击日历单元格
      if (params.componentType === 'series' && params.seriesType === 'heatmap') {
        const date = params.data?.[0]
        if (date) {
          selectedDate.value = date
        }
      }
    })
  }

  const data = calendarData.value
    .filter((d) => d.count > 0)
    .map((d) => [d.date, d.count])

  const year = selectedYear.value
  const maxCount = data.length > 0 ? Math.max(...data.map((d) => d[1] as number)) : 0

  chart.setOption({
    tooltip: {
      formatter: (params: any) => {
        const date = params.data?.[0]
        const count = params.data?.[1]
        const day = calendarData.value.find((d) => d.date === date)
        if (!day || count === 0) {
          return `${date}<br/>无事件`
        }
        const eventList = day.events
          .slice(0, 5)
          .map((e) => `· ${e.label}（${calendarEventDisplayLabel(e)}）`)
          .join('<br/>')
        const more = day.events.length > 5 ? `<br/>...共 ${day.events.length} 条` : ''
        return `${date}<br/>事件数：${count}<br/>${eventList}${more}`
      },
    },
    visualMap: {
      min: 0,
      max: maxCount > 0 ? maxCount : 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 10,
      inRange: {
        color: ['#eef2f0', '#d4e5e3', '#8bb5b8', '#3b8187', '#176b73'],
      },
      textStyle: { fontSize: 12 },
    },
    calendar: {
      top: 60,
      left: 50,
      right: 50,
      cellSize: ['auto', 16],
      range: [`${year}-01-01`, `${year}-12-31`],
      itemStyle: {
        borderWidth: 2,
        borderColor: '#ffffff',
        color: '#eef2f0',
      },
      yearLabel: { show: false },
      dayLabel: {
        firstDay: 1,
        nameMap: 'cn',
        fontSize: 12,
        color: '#46524e',
      },
      monthLabel: {
        nameMap: 'cn',
        fontSize: 12,
        color: '#46524e',
        margin: 16,
      },
      splitLine: { show: false },
    },
    series: [
      {
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: data,
        itemStyle: {
          borderRadius: 3,
        },
        emphasis: {
          itemStyle: {
            borderColor: '#176b73',
            borderWidth: 2,
          },
        },
      },
    ],
  } as any)
}

// 窗口大小变化时重绘
function handleResize(): void {
  chart?.resize()
}

watch(selectedYear, () => {
  loadCalendar()
})

onMounted(() => {
  loadProjectOptions()
  loadCalendar()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style lang="scss" scoped>
.project-calendar-view {
  .calendar-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px 20px;
    padding: 10px 14px;

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .toolbar-label {
      font-size: 14px;
      color: var(--color-text-muted);
    }

    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--color-text-muted);

      .legend-label {
        margin-right: 4px;
      }

      .legend-item {
        display: inline-flex;
        align-items: center;
      }

      .legend-cell {
        display: inline-block;
        width: 14px;
        height: 14px;
        border-radius: 3px;
        margin-right: 4px;

        &.lv-1 {
          background: #d4e5e3;
        }
        &.lv-2 {
          background: #8bb5b8;
        }
        &.lv-3 {
          background: #3b8187;
        }
        &.lv-4 {
          background: var(--color-primary);
        }
      }
    }
  }

  .year-select { width: 120px; }
  .project-select { width: 220px; }

  .chart-panel,
  .day-events-panel {
    padding: 0;
    margin-top: var(--space-4);
    overflow: hidden;
  }

  .section-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 52px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--color-border-light);

    h2 {
      margin: 0;
      color: var(--color-text);
      font-size: 14px;
      font-weight: 600;
    }

    span {
      color: var(--color-text-muted);
      font-size: 12px;
    }
  }

  .calendar-wrapper {
    min-height: 220px;
    width: 100%;
    padding: 10px 14px 4px;

    .calendar-scroll {
      width: 100%;
      overflow-x: auto;
      overflow-y: hidden;
    }

    .calendar-chart {
      width: 100%;
      min-width: 780px;
      height: 240px;
    }
  }

  .day-events-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 52px;
    padding: 10px 14px;
    margin-bottom: 0;
    border-bottom: 1px solid var(--color-border-light);

    .section-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--color-text);
      margin: 0;
    }

    .day-events-count {
      font-size: 13px;
      color: var(--color-text-muted);
    }
  }

  .day-events-list {
    display: flex;
    flex-direction: column;
    padding: 2px 14px 10px;

    .day-event-item {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 44px;
      padding: 8px 0;
      border-bottom: 1px solid var(--color-border-light);

      &:last-child { border-bottom: 0; }

      .day-event-label {
        font-size: 14px;
        color: var(--color-text-regular);
      }
    }
  }
}

@media screen and (max-width: 768px) {
  .project-calendar-view {
    .calendar-toolbar {
      flex-direction: column;
      align-items: stretch;
      padding: 10px 12px;

      .toolbar-left {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 8px;
      }

      .year-select,
      .project-select {
        width: 100%;
      }

      .toolbar-right {
        padding-top: 8px;
        border-top: 1px solid var(--color-border-light);
      }
    }

    .calendar-wrapper {
      padding: 8px 8px 2px;

      .calendar-chart {
        width: 820px;
        min-width: 820px;
      }
    }

    .day-events-header {
      align-items: flex-start;
      padding: 10px 12px;
    }

    .day-events-list {
      padding-right: 12px;
      padding-left: 12px;
    }
  }
}
</style>
