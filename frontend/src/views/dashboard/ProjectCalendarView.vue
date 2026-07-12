<template>
  <div class="project-calendar-view page-container">
    <PageHeader title="项目日历" subtitle="全年项目事件密度热力图" />

    <!-- 筛选栏 -->
    <div class="card calendar-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-label">年份：</span>
        <el-select v-model="selectedYear" style="width: 120px" @change="loadCalendar">
          <el-option v-for="y in yearOptions" :key="y" :label="`${y} 年`" :value="y" />
        </el-select>

        <span class="toolbar-label">项目：</span>
        <el-select
          v-model="selectedProjectId"
          clearable
          filterable
          placeholder="全部项目"
          style="width: 220px"
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
    <div class="card mt-16">
      <div v-loading="loading" class="calendar-wrapper">
        <el-empty v-if="!loading && !hasData" description="该年度暂无事件数据" />
        <div ref="chartRef" class="calendar-chart" :style="{ display: hasData ? 'block' : 'none' }"></div>
      </div>
    </div>

    <!-- 当天事件列表 -->
    <div class="card mt-16">
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
            {{ event.level_display || event.type }}
          </el-tag>
          <span class="day-event-label">{{ event.label }}</span>
        </div>
      </div>

      <el-empty v-else description="点击上方日历的某一天，可查看当日事件详情" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import PageHeader from '@/components/PageHeader.vue'
import { getProjectCalendar, type CalendarDayItem } from '@/api/dashboard'
import { getProjects } from '@/api/projects'
import type { Project } from '@/types'

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

// 选中日期对应的事件列表
const selectedDayEvents = computed(() => {
  if (!selectedDate.value) return []
  const day = calendarData.value.find((d) => d.date === selectedDate.value)
  return day?.events || []
})

// 获取级别颜色
function getLevelColor(level?: string): string {
  const map: Record<string, string> = {
    national: '#F56C6C',
    provincial: '#E6A23C',
    municipal: '#409EFF',
    school: '#67C23A',
    enterprise: '#9B59B6',
    high: '#F56C6C',
    medium: '#E6A23C',
    low: '#909399',
  }
  return map[level || ''] || '#409EFF'
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
          .map((e) => `· ${e.label}（${e.level_display || e.type}）`)
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
        color: ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
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
        borderColor: '#fff',
        color: '#ebedf0',
      },
      yearLabel: { show: false },
      dayLabel: {
        firstDay: 1,
        nameMap: 'cn',
        fontSize: 12,
        color: '#606266',
      },
      monthLabel: {
        nameMap: 'cn',
        fontSize: 12,
        color: '#606266',
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
            borderColor: '#409EFF',
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
  .mt-16 {
    margin-top: 16px;
  }

  .calendar-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .toolbar-label {
      font-size: 14px;
      color: #606266;
    }

    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #909399;

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
          background: #c6e48b;
        }
        &.lv-2 {
          background: #7bc96f;
        }
        &.lv-3 {
          background: #239a3b;
        }
        &.lv-4 {
          background: #196127;
        }
      }
    }
  }

  .calendar-wrapper {
    min-height: 220px;
    width: 100%;

    .calendar-chart {
      width: 100%;
      height: 240px;
    }
  }

  .day-events-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    .section-title {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
      margin: 0;
      position: relative;
      padding-left: 12px;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 4px;
        height: 16px;
        border-radius: 2px;
        background: #409eff;
      }
    }

    .day-events-count {
      font-size: 13px;
      color: #909399;
    }
  }

  .day-events-list {
    display: flex;
    flex-direction: column;
    gap: 10px;

    .day-event-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      background: #f9fafc;
      border-radius: 6px;

      .day-event-label {
        font-size: 14px;
        color: #303133;
      }
    }
  }
}

@media screen and (max-width: 768px) {
  .project-calendar-view {
    .calendar-toolbar {
      flex-direction: column;
      align-items: flex-start;
    }
  }
}
</style>
