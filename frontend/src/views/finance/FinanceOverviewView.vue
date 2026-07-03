<template>
  <div class="page-container">
    <PageHeader title="经费管理" subtitle="所有项目经费汇总与支出管理">
      <template #actions>
        <el-button :icon="Download" @click="handleExport('xlsx')">导出Excel</el-button>
        <el-button :icon="Download" @click="handleExport('pdf')">导出PDF</el-button>
      </template>
    </PageHeader>

    <!-- 经费统计卡片 -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-label">总预算</div>
          <div class="stat-value">{{ formatMoneyWithComma(totalBudget) }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-label">总支出</div>
          <div class="stat-value danger">{{ formatMoneyWithComma(totalExpense) }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-label">剩余</div>
          <div class="stat-value" :class="{ danger: totalRemaining < 0 }">
            {{ formatMoneyWithComma(totalRemaining) }}
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-label">支出笔数</div>
          <div class="stat-value">{{ expenseList.length }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 经费支出图表 -->
    <div class="card mt-16">
      <h3 class="card-title">支出类别分布</h3>
      <div ref="chartRef" class="chart-container"></div>
    </div>

    <!-- 经费支出汇总表格 -->
    <div class="card mt-16">
      <div class="table-header">
        <h3 class="card-title">经费支出明细</h3>
        <el-select v-model="filterProject" placeholder="筛选项目" clearable style="width: 200px" @change="loadData">
          <el-option
            v-for="p in projectOptions"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>
      </div>
      <FinanceTable
        :expenses="expenseList"
        :show-budget="false"
        :show-actions="false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { getFinanceExpenses, getFinanceBudgets, type ExpenseQueryParams } from '@/api/finance'
import { getProjects } from '@/api/projects'
import { exportData } from '@/api/exports'
import { formatMoneyWithComma, getFinanceCategoryLabel } from '@/utils/format'
import { FINANCE_CATEGORY_MAP } from '@/utils/constants'
import type { FinanceExpense, FinanceBudget, Project } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import FinanceTable from '@/components/FinanceTable.vue'

const expenseList = ref<FinanceExpense[]>([])
const budgetList = ref<FinanceBudget[]>([])
const projectOptions = ref<Project[]>([])
const filterProject = ref<number | undefined>(undefined)
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function toAmount(value: number | string | null | undefined): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

// 统计计算
const totalExpense = computed(() => expenseList.value.reduce((sum, e) => sum + toAmount(e.amount), 0))
const totalBudget = computed(() => budgetList.value.reduce((sum, b) => sum + toAmount(b.bonus_amount) + toAmount(b.other_income), 0))
const totalRemaining = computed(() => totalBudget.value - totalExpense.value)

// 加载数据
async function loadData(): Promise<void> {
  try {
    const params: ExpenseQueryParams = { page: 1, page_size: 999 }
    if (filterProject.value) params.project = filterProject.value
    const res = await getFinanceExpenses(params)
    expenseList.value = res.results
    // 加载预算数据
    const budgetParams: any = { page: 1, page_size: 999 }
    if (filterProject.value) budgetParams.project = filterProject.value
    const budgetRes: any = await getFinanceBudgets(budgetParams)
    budgetList.value = budgetRes.results || []
    await nextTick()
    renderChart()
  } catch {
    // 已处理
  }
}

// 加载项目选项
async function loadProjects(): Promise<void> {
  try {
    const res = await getProjects({ page: 1, page_size: 999 })
    projectOptions.value = res.results
  } catch {
    // 忽略
  }
}

// 渲染图表
function renderChart(): void {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)

  // 按类别统计支出
  const categoryData: Record<string, number> = {}
  expenseList.value.forEach((e) => {
    categoryData[e.category || ''] = (categoryData[e.category || ''] || 0) + toAmount(e.amount)
  })

  const categories = Object.keys(FINANCE_CATEGORY_MAP)
  const data = categories.map((cat) => ({
    name: FINANCE_CATEGORY_MAP[cat].label,
    value: categoryData[cat] || 0,
    itemStyle: { color: FINANCE_CATEGORY_MAP[cat].color },
  }))

  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, left: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data,
        label: { show: true, formatter: '{b}\n{c}' },
      },
    ],
  })
}

function handleResize(): void {
  chart?.resize()
}

// 导出经费数据
async function handleExport(format: string): Promise<void> {
  try {
    const res: any = await exportData('finance', format)
    const blobData = res.data ? res.data : res
    const url = window.URL.createObjectURL(new Blob([blobData]))
    const link = document.createElement('a')
    link.href = url
    link.download = `finance_${format}_${Date.now()}.${format === 'excel' ? 'xlsx' : format}`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    // 错误已由拦截器处理
  }
}

onMounted(() => {
  loadProjects()
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style lang="scss" scoped>
.stat-cards {
  .stat-card {
    background: #fff;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

    .stat-label {
      font-size: 13px;
      color: #909399;
      margin-bottom: 8px;
    }
    .stat-value {
      font-size: 22px;
      font-weight: 600;
      color: #303133;
      &.danger { color: #f56c6c; }
    }
  }
}

.mt-16 { margin-top: 16px; }

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .card-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
  height: 300px;
}
</style>
