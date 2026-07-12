<template>
  <div class="project-gantt-view page-container">
    <PageHeader title="项目历程" subtitle="项目甘特图 · 阶段与里程碑全景" />

    <!-- 筛选栏 -->
    <div class="card gantt-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-label">项目：</span>
        <el-select
          v-model="selectedProjectId"
          clearable
          filterable
          placeholder="全部项目"
          style="width: 240px"
          @change="loadGantt"
        >
          <el-option
            v-for="p in projectOptions"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>

        <span class="toolbar-label">状态：</span>
        <el-select
          v-model="selectedStatus"
          clearable
          placeholder="全部状态"
          style="width: 140px"
          @change="loadGantt"
        >
          <el-option
            v-for="(meta, key) in PROJECT_STATUS_MAP"
            :key="key"
            :label="meta.label"
            :value="key"
          />
        </el-select>
      </div>

      <div class="toolbar-right">
        <span class="legend-label">图例：</span>
        <span class="legend-item"><i class="legend-bar" style="background: #409EFF"></i>进行中</span>
        <span class="legend-item"><i class="legend-bar" style="background: #E6A23C"></i>已暂停</span>
        <span class="legend-item"><i class="legend-bar" style="background: #909399"></i>已关闭</span>
        <span class="legend-item"><i class="legend-diamond" style="color: #F56C6C">◆</i>里程碑</span>
      </div>
    </div>

    <!-- 甘特图 -->
    <div class="card mt-16">
      <div v-loading="loading" class="gantt-wrapper">
        <el-empty v-if="!loading && ganttProjects.length === 0" description="暂无项目数据" />
        <div
          ref="chartRef"
          class="gantt-chart"
          :style="{ display: ganttProjects.length > 0 ? 'block' : 'none', height: chartHeight + 'px' }"
        ></div>
      </div>
    </div>

    <!-- 项目明细列表 -->
    <div class="card mt-16">
      <h3 class="section-title">项目明细</h3>
      <el-table :data="ganttProjects" border size="small" style="width: 100%">
        <el-table-column prop="project_name" label="项目名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="project_code" label="编号" width="110" />
        <el-table-column prop="leader_name" label="负责人" width="100" />
        <el-table-column prop="current_stage_display" label="当前阶段" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.current_stage_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status_display" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status) as any" size="small">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="110">
          <template #default="{ row }">{{ formatDate(row.start_date) }}</template>
        </el-table-column>
        <el-table-column prop="planned_end_date" label="计划结束" width="110">
          <template #default="{ row }">{{ formatDate(row.planned_end_date) }}</template>
        </el-table-column>
        <el-table-column prop="actual_end_date" label="实际结束" width="110">
          <template #default="{ row }">{{ formatDate(row.actual_end_date) }}</template>
        </el-table-column>
        <el-table-column label="里程碑" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.milestones?.length" type="warning" size="small">
              {{ row.milestones.length }} 个
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import PageHeader from '@/components/PageHeader.vue'
import { getProjectGantt, type GanttProject } from '@/api/dashboard'
import { getProjects } from '@/api/projects'
import type { Project } from '@/types'
import { PROJECT_STATUS_MAP } from '@/utils/constants'
import { formatDate } from '@/utils/format'

/**
 * 项目 Gantt 历程条页面
 * 使用 ECharts 自定义系列（custom series）实现横向甘特图
 */

// 状态
const loading = ref(false)
const selectedProjectId = ref<number | undefined>(undefined)
const selectedStatus = ref<string | undefined>(undefined)
const ganttProjects = ref<GanttProject[]>([])
const projectOptions = ref<Project[]>([])

// 图表
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

// 状态颜色映射
const STATUS_COLOR_MAP: Record<string, string> = {
  active: '#409EFF',
  paused: '#E6A23C',
  closed: '#909399',
}

// 里程碑级别颜色映射
const MILESTONE_COLOR_MAP: Record<string, string> = {
  national: '#F56C6C',
  provincial: '#E6A23C',
  municipal: '#409EFF',
  school: '#67C23A',
  enterprise: '#9B59B6',
}

// 获取状态 Tag 类型
function getStatusTagType(status: string): string {
  return PROJECT_STATUS_MAP[status]?.type || 'info'
}

// 获取状态颜色
function getStatusColor(status: string): string {
  return STATUS_COLOR_MAP[status] || '#409EFF'
}

// 获取里程碑颜色
function getMilestoneColor(level: string): string {
  return MILESTONE_COLOR_MAP[level] || '#F56C6C'
}

// 图表高度（根据项目数量动态计算）
const chartHeight = computed(() => {
  return Math.max(300, ganttProjects.value.length * 56 + 100)
})

// 加载项目列表（用于筛选）
async function loadProjectOptions(): Promise<void> {
  try {
    const res = await getProjects({ page: 1, page_size: 200 } as any)
    projectOptions.value = res.results || []
  } catch {
    // 忽略
  }
}

// 加载 Gantt 数据
async function loadGantt(): Promise<void> {
  loading.value = true
  try {
    const params: { project_id?: number; status?: string } = {}
    if (selectedProjectId.value) {
      params.project_id = selectedProjectId.value
    }
    if (selectedStatus.value) {
      params.status = selectedStatus.value
    }
    const res = await getProjectGantt(params)
    ganttProjects.value = res.projects || []
    await nextTick()
    renderChart()
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 渲染甘特图
function renderChart(): void {
  if (!chartRef.value || ganttProjects.value.length === 0) return

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const projects = ganttProjects.value

  // y 轴类别（项目名称）
  const categories = projects.map((p) => p.project_name)

  // 计算时间范围
  let minTime = Infinity
  let maxTime = -Infinity
  const now = Date.now()
  for (const p of projects) {
    if (p.start_date) {
      const t = dayjs(p.start_date).valueOf()
      if (t < minTime) minTime = t
    }
    const end = p.actual_end_date || p.planned_end_date
    if (end) {
      const t = dayjs(end).valueOf()
      if (t > maxTime) maxTime = t
    } else {
      // 未结束的项目，延伸到今天
      if (now > maxTime) maxTime = now
    }
  }
  // 留出边距
  if (minTime !== Infinity) {
    minTime = minTime - 7 * 24 * 60 * 60 * 1000
  }
  if (maxTime !== -Infinity) {
    maxTime = maxTime + 7 * 24 * 60 * 60 * 1000
  }

  // 自定义系列数据（甘特条）
  const ganttData = projects.map((p, idx) => {
    const startTs = p.start_date ? dayjs(p.start_date).valueOf() : minTime
    const endTs = p.actual_end_date
      ? dayjs(p.actual_end_date).valueOf()
      : p.planned_end_date
        ? dayjs(p.planned_end_date).valueOf()
        : now
    return {
      value: [idx, startTs, endTs, p.current_stage_display || ''],
      itemStyle: {
        color: getStatusColor(p.status),
        borderRadius: 4,
      },
      project: p,
    }
  })

  // 里程碑散点数据
  const milestoneData: any[] = []
  for (const p of projects) {
    const idx = projects.indexOf(p)
    for (const m of p.milestones || []) {
      if (m.date) {
        milestoneData.push({
          value: [dayjs(m.date).valueOf(), idx],
          itemStyle: {
            color: m.is_awarded ? getMilestoneColor(m.award_level || m.level) : '#fff',
            borderColor: getMilestoneColor(m.level),
            borderWidth: 2,
          },
          milestone: m,
          project: p,
        })
      }
    }
  }

  // renderItem：绘制甘特条 + 阶段标签
  function renderItem(params: any, api: any): any {
    const categoryIndex = api.value(0)
    const start = api.coord([api.value(1), categoryIndex])
    const end = api.coord([api.value(2), categoryIndex])
    const stageText = api.value(3)
    const height = api.size([0, 1])[1] * 0.6

    const rectShape = echarts.graphic.clipRectByRect(
      {
        x: start[0],
        y: start[1] - height / 2,
        width: Math.max(end[0] - start[0], 2),
        height: height,
      },
      {
        x: params.coordSys.x,
        y: params.coordSys.y,
        width: params.coordSys.width,
        height: params.coordSys.height,
      }
    )

    if (!rectShape) {
      return undefined
    }

    const children: any[] = [
      {
        type: 'rect',
        transition: ['shape'],
        shape: rectShape,
        style: api.style(),
      },
    ]

    // 阶段文字标注（条够宽时才显示）
    const barWidth = end[0] - start[0]
    if (stageText && barWidth > 60) {
      children.push({
        type: 'text',
        style: {
          text: stageText,
          x: start[0] + 6,
          y: start[1],
          textAlign: 'left',
          textVerticalAlign: 'middle',
          fontSize: 11,
          fill: '#fff',
          fontWeight: 'bold',
        },
        silent: true,
      })
    }

    return {
      type: 'group',
      children: children,
    }
  }

  chart.setOption({
    tooltip: {
      formatter: (params: any) => {
        // 甘特条 tooltip
        if (params.seriesType === 'custom') {
          const p = params.data?.project as GanttProject | undefined
          if (!p) return ''
          const lines = [
            `<b>${p.project_name}</b>（${p.project_code}）`,
            `负责人：${p.leader_name || '-'}`,
            `当前阶段：${p.current_stage_display || '-'}`,
            `状态：${p.status_display || '-'}`,
            `开始：${formatDate(p.start_date)}`,
            `计划结束：${formatDate(p.planned_end_date)}`,
          ]
          if (p.actual_end_date) {
            lines.push(`实际结束：${formatDate(p.actual_end_date)}`)
          }
          if (p.milestones?.length) {
            lines.push(`里程碑：${p.milestones.length} 个`)
          }
          return lines.join('<br/>')
        }
        // 里程碑 tooltip
        if (params.seriesType === 'scatter') {
          const m = params.data?.milestone
          const p = params.data?.project
          if (!m) return ''
          const lines = [
            `<b>${m.label}</b>`,
            `所属项目：${p?.project_name || '-'}`,
            `日期：${formatDate(m.date)}`,
            `级别：${m.level_display || m.level}`,
          ]
          if (m.is_awarded) {
            lines.push(`已获奖：${m.award_level || '-'}`)
          }
          return lines.join('<br/>')
        }
        return ''
      },
    },
    grid: {
      left: 180,
      right: 40,
      top: 20,
      bottom: 60,
    },
    xAxis: {
      type: 'time',
      min: minTime === Infinity ? undefined : minTime,
      max: maxTime === -Infinity ? undefined : maxTime,
      axisLabel: {
        fontSize: 12,
        color: '#606266',
        formatter: (val: number) => {
          return dayjs(val).format('YYYY-MM-DD')
        },
      },
      splitLine: { show: true, lineStyle: { type: 'dashed', color: '#ebeef5' } },
    },
    yAxis: {
      type: 'category',
      data: categories,
      inverse: true,
      axisLabel: {
        fontSize: 12,
        color: '#303133',
        width: 160,
        overflow: 'truncate',
      },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [
      {
        name: '项目历程',
        type: 'custom',
        renderItem: renderItem,
        encode: {
          x: [1, 2],
          y: 0,
        },
        data: ganttData,
        clip: true,
      },
      {
        name: '里程碑',
        type: 'scatter',
        symbol: 'diamond',
        symbolSize: 14,
        data: milestoneData,
        z: 10,
      },
      {
        // 今日参考线
        name: '今日',
        type: 'line',
        data: [],
        markLine: {
          symbol: 'none',
          silent: true,
          label: {
            formatter: '今日',
            position: 'insideEndTop',
            fontSize: 11,
            color: '#F56C6C',
          },
          lineStyle: {
            color: '#F56C6C',
            type: 'dashed',
            width: 1.5,
          },
          data: [
            {
              xAxis: now,
            },
          ],
        },
      },
    ],
  } as any)

  // 容器高度可能随项目数量变化，重新渲染后需 resize
  chart.resize()
}

// 窗口大小变化时重绘
function handleResize(): void {
  chart?.resize()
}

onMounted(() => {
  loadProjectOptions()
  loadGantt()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style lang="scss" scoped>
.project-gantt-view {
  .mt-16 {
    margin-top: 16px;
  }

  .gantt-toolbar {
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
      gap: 12px;
      font-size: 13px;
      color: #909399;
      flex-wrap: wrap;

      .legend-label {
        margin-right: 4px;
      }

      .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }

      .legend-bar {
        display: inline-block;
        width: 18px;
        height: 10px;
        border-radius: 2px;
      }

      .legend-diamond {
        font-size: 14px;
        line-height: 1;
      }
    }
  }

  .gantt-wrapper {
    min-height: 300px;
    width: 100%;

    .gantt-chart {
      width: 100%;
      min-height: 300px;
    }
  }

  .section-title {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 16px;
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
}

@media screen and (max-width: 768px) {
  .project-gantt-view {
    .gantt-toolbar {
      flex-direction: column;
      align-items: flex-start;
    }
  }
}
</style>
