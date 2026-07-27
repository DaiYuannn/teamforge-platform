<template>
  <div class="page-container" v-permission="['sys_admin', 'teacher']">
    <PageHeader title="操作日志" subtitle="查看系统操作记录与审计信息">
      <template #actions>
        <el-button :icon="Download" :loading="exporting" @click="handleExport">
          导出当前结果
        </el-button>
      </template>
    </PageHeader>

    <!-- 筛选栏 -->
    <div class="surface-panel search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="路径 / 对象">
          <el-input
            v-model="queryParams.search"
            placeholder="接口路径或对象类型"
            clearable
            class="search-input"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="queryParams.module" placeholder="全部模块" clearable class="module-select">
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
            class="operator-input"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="queryParams.operation_type" placeholder="全部类型" clearable class="action-select">
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
            class="date-range"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <span class="result-count">共 {{ total }} 条记录</span>
    </div>

    <!-- 日志表格 -->
    <section class="surface-panel log-workspace">
      <el-table v-if="!isMobile" v-loading="loading" :data="logList">
        <template #empty>
          <EmptyState text="暂无操作日志" description="调整筛选条件后重试" :compact="true" />
        </template>
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
        <el-table-column label="操作" width="64" align="right" fixed="right">
          <template #default="{ row }">
            <el-tooltip content="查看详情" placement="top">
              <el-button text :icon="ViewIcon" aria-label="查看详情" @click="handleDetail(row as any)" />
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <div v-else v-loading="loading" class="mobile-logs">
        <EmptyState v-if="logList.length === 0 && !loading" text="暂无操作日志" :compact="true" />
        <article v-for="row in logList" :key="row.id" class="mobile-log">
          <div class="mobile-log-heading">
            <strong>{{ row.operator_name || '系统' }}</strong>
            <el-tag :type="getStatusTagType(row.response_status || 0) as any" size="small">
              {{ row.response_status || '-' }}
            </el-tag>
          </div>
          <div class="mobile-log-tags">
            <el-tag :type="AUDIT_MODULE_MAP[row.module || '']?.tagType as any" size="small" effect="plain">
              {{ AUDIT_MODULE_MAP[row.module || '']?.label || row.module }}
            </el-tag>
            <el-tag :type="AUDIT_ACTION_MAP[row.operation_type || '']?.tagType as any" size="small" effect="plain">
              {{ AUDIT_ACTION_MAP[row.operation_type || '']?.label || row.operation_type }}
            </el-tag>
            <span>{{ row.request_method || '-' }}</span>
          </div>
          <p class="mobile-log-path">{{ row.request_path || row.object_type || '-' }}</p>
          <div class="mobile-log-footer">
            <time>{{ formatDateTime(row.created_at) }}</time>
            <el-button text :icon="ViewIcon" @click="handleDetail(row as any)">详情</el-button>
          </div>
        </article>
      </div>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <AccessiblePagination
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
    </section>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="日志详情"
      width="720px"
      :fullscreen="isMobile"
      append-to-body
    >
      <el-descriptions v-if="currentLog" v-loading="detailLoading" :column="isMobile ? 1 : 2" border>
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
        <el-descriptions-item v-if="currentLog.user_agent" label="客户端" :span="2">
          {{ currentLog.user_agent }}
        </el-descriptions-item>
        <el-descriptions-item v-if="currentLog.request_data" label="请求数据" :span="2">
          <pre class="json-block">{{ formatJson(currentLog.request_data) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Download, Search, Refresh, View as ViewIcon } from '@element-plus/icons-vue'
import { exportOperationLogs, getOperationLogs, getOperationLog } from '@/api/audit'
import { downloadBlob, formatDateTime } from '@/utils/format'
import { AUDIT_MODULE_MAP, AUDIT_ACTION_MAP } from '@/utils/constants'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useDevice } from '@/composables/useDevice'
import type { OperationLog } from '@/types'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const route = useRoute()

const { isMobile } = useDevice()

const loading = ref(false)
const logList = ref<OperationLog[]>([])
const total = ref(0)
const detailVisible = ref(false)
const detailLoading = ref(false)
const exporting = ref(false)
const currentLog = ref<OperationLog | null>(null)

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: appStore.itemsPerPage,
  search: String(route.query.search || ''),
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
    if (!params.search) delete params.search
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
  queryParams.search = ''
  queryParams.module = ''
  queryParams.operation_type = ''
  queryParams.start_date = ''
  queryParams.end_date = ''
  dateRange.value = null
  queryParams.page = 1
  loadData()
}

function activeFilterParams(): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries({
      operator: queryParams.operator,
      search: queryParams.search,
      module: queryParams.module,
      operation_type: queryParams.operation_type,
      start_date: queryParams.start_date,
      end_date: queryParams.end_date,
    }).filter(([, value]) => Boolean(value)),
  )
}

async function handleExport(): Promise<void> {
  exporting.value = true
  try {
    const blob = await exportOperationLogs(activeFilterParams())
    downloadBlob(blob, `操作日志_${new Date().toISOString().slice(0, 10)}.xlsx`)
  } finally {
    exporting.value = false
  }
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
.search-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 10px 14px;

  :deep(.el-form) {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px 14px;
  }

  :deep(.el-form-item) {
    margin: 0;
  }
}

.search-input {
  width: 220px;
}

.module-select { width: 150px; }
.operator-input { width: 150px; }
.action-select { width: 132px; }
.date-range { width: 260px !important; }

.result-count {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
}

.log-workspace {
  padding: 0;
  margin-top: var(--space-4);
  overflow: hidden;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 0 14px 14px;
}

.json-block {
  max-height: 300px;
  padding: 10px;
  margin: 0;
  overflow: auto;
  color: var(--color-text-regular);
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xs);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.mobile-logs {
  min-height: 160px;
  padding: 0 12px;
}

.mobile-log {
  padding: 13px 0 7px;
  border-bottom: 1px solid var(--color-border-light);

  &:last-child { border-bottom: 0; }
}

.mobile-log-heading,
.mobile-log-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.mobile-log-heading strong {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
}

.mobile-log-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.mobile-log-path {
  margin: 8px 0 3px;
  overflow: hidden;
  color: var(--color-text-regular);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-log-footer time {
  color: var(--color-text-muted);
  font-size: 12px;
}

@media screen and (max-width: 768px) {
  .search-bar {
    align-items: flex-start;
    flex-direction: column;
    padding: 10px 12px;

    :deep(.el-form),
    :deep(.el-form-item),
    :deep(.el-form-item__content) {
      width: 100%;
    }

    :deep(.el-form) {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    :deep(.el-form-item) {
      align-items: flex-start;
      flex-direction: column;
    }

    :deep(.el-form-item:nth-last-child(-n + 2)) {
      grid-column: 1 / -1;
    }

    .module-select,
    .operator-input,
    .action-select,
    .date-range {
      width: 100% !important;
    }
  }

  .pagination-wrapper {
    justify-content: center;
    padding: 0 6px 12px;
  }
}

@media screen and (max-width: 420px) {
  .search-bar :deep(.el-form) {
    grid-template-columns: 1fr;
  }

  .search-bar :deep(.el-form-item:nth-last-child(-n + 2)) {
    grid-column: auto;
  }
}
</style>
