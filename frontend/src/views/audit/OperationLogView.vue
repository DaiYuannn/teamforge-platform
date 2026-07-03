<template>
  <div class="page-container" v-permission="['sys_admin', 'teacher']">
    <PageHeader title="操作日志" subtitle="查看系统操作记录与审计信息" />

    <!-- 筛选栏 -->
    <div class="card search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="模块">
          <el-select v-model="queryParams.module" placeholder="全部模块" clearable style="width: 160px">
            <el-option
              v-for="(item, key) in AUDIT_MODULE_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="操作人">
          <el-input
            v-model="queryParams.operator"
            placeholder="操作人ID"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="queryParams.operation_type" placeholder="全部" clearable style="width: 120px">
            <el-option
              v-for="(item, key) in AUDIT_ACTION_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 360px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 日志表格 -->
    <div class="card mt-16">
      <el-table v-loading="loading" :data="logList" border stripe>
        <el-table-column prop="operator_name" label="操作人" width="110" />
        <el-table-column prop="created_at" label="操作时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="120">
          <template #default="{ row }">
            <el-tag :type="AUDIT_MODULE_MAP[row.module]?.tagType as any" size="small">
              {{ AUDIT_MODULE_MAP[row.module]?.label || row.module }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operation_type" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="AUDIT_ACTION_MAP[row.operation_type]?.tagType as any" size="small">
              {{ AUDIT_ACTION_MAP[row.operation_type]?.label || row.operation_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="object_type" label="对象类型" width="120" show-overflow-tooltip />
        <el-table-column prop="request_method" label="请求方法" width="90" />
        <el-table-column prop="response_status" label="响应状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.response_status) as any" size="small">
              {{ row.response_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleDetail(row as any)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="日志详情" width="700px">
      <el-descriptions v-if="currentLog" v-loading="detailLoading" :column="2" border>
        <el-descriptions-item label="操作人">{{ currentLog.operator_name }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">{{ formatDateTime(currentLog.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="模块">{{ AUDIT_MODULE_MAP[currentLog.module || '']?.label || currentLog.module }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ AUDIT_ACTION_MAP[currentLog.operation_type || '']?.label || currentLog.operation_type }}</el-descriptions-item>
        <el-descriptions-item label="对象类型">{{ currentLog.object_type }}</el-descriptions-item>
        <el-descriptions-item label="对象ID">{{ currentLog.object_id ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ currentLog.request_method }}</el-descriptions-item>
        <el-descriptions-item label="响应状态">{{ currentLog.response_status }}</el-descriptions-item>
        <el-descriptions-item label="请求路径" :span="2">{{ currentLog.request_path }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog.request_ip || '暂无记录' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getOperationLogs, getOperationLog } from '@/api/audit'
import { formatDateTime } from '@/utils/format'
import { AUDIT_MODULE_MAP, AUDIT_ACTION_MAP } from '@/utils/constants'
import PageHeader from '@/components/PageHeader.vue'
import type { OperationLog } from '@/types'

const loading = ref(false)
const logList = ref<OperationLog[]>([])
const total = ref(0)
const detailVisible = ref(false)
const detailLoading = ref(false)
const currentLog = ref<OperationLog | null>(null)

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: 10,
  operator: '',
  module: '',
  operation_type: '',
  start_date: '',
  end_date: '',
})

// 时间范围
const dateRange = ref<[string, string] | null>(null)

// 监听时间范围变化
watch(dateRange, (val) => {
  if (val && val.length === 2) {
    queryParams.start_date = val[0]
    queryParams.end_date = val[1]
  } else {
    queryParams.start_date = ''
    queryParams.end_date = ''
  }
})

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const params: any = { ...queryParams }
    if (!params.operator) delete params.operator
    if (!params.module) delete params.module
    if (!params.operation_type) delete params.operation_type
    if (!params.start_date) delete params.start_date
    if (!params.end_date) delete params.end_date
    const res: any = await getOperationLogs(params)
    logList.value = res.results || []
    total.value = res.count || 0
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 搜索
function handleSearch(): void {
  queryParams.page = 1
  loadData()
}

// 重置
function handleReset(): void {
  queryParams.operator = ''
  queryParams.module = ''
  queryParams.operation_type = ''
  queryParams.start_date = ''
  queryParams.end_date = ''
  dateRange.value = null
  queryParams.page = 1
  loadData()
}

// 查看详情
async function handleDetail(row: any): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  currentLog.value = row as OperationLog
  try {
    const detail: any = await getOperationLog(row.id)
    currentLog.value = detail as OperationLog
  } catch {
    // 保留列表行数据作为兜底
  } finally {
    detailLoading.value = false
  }
}

// 响应状态标签类型
function getStatusTagType(status: number): string {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'warning'
  if (status >= 500) return 'danger'
  return 'info'
}

// 格式化JSON
function formatJson(data: any): string {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.mt-16 {
  margin-top: 16px;
}

.search-bar {
  padding: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.json-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
