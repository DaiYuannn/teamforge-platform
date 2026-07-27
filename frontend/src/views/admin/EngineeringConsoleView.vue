<template>
  <div class="engineering-console page-container">
    <PageHeader title="工程控制台" subtitle="运行指标、接口契约与质量门禁">
      <template #actions>
        <el-tooltip content="性能指标自动刷新间隔" placement="bottom">
          <el-select v-model="refreshIntervalMs" aria-label="性能指标自动刷新间隔" class="refresh-select">
            <el-option v-for="option in AUTO_REFRESH_OPTIONS" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-tooltip>
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
        <el-button :icon="Download" type="primary" @click="downloadSchema">下载 OpenAPI</el-button>
      </template>
    </PageHeader>

    <section class="metric-strip" aria-label="实时性能摘要">
      <div class="metric-item"><span>采样请求</span><strong>{{ metrics?.request_count ?? 0 }}</strong></div>
      <div class="metric-item"><span>每分钟请求</span><strong>{{ metrics?.requests_per_minute ?? 0 }}</strong></div>
      <div class="metric-item"><span>平均响应</span><strong>{{ formatMs(metrics?.avg_response_time_ms) }}</strong></div>
      <div class="metric-item"><span>P95 响应</span><strong>{{ formatMs(metrics?.p95_response_time_ms) }}</strong></div>
      <div class="metric-item"><span>错误率</span><strong>{{ formatRate(metrics?.error_rate) }}</strong></div>
    </section>

    <el-tabs v-model="activeTab" class="workspace-tabs">
      <el-tab-pane label="运行性能" name="performance">
        <div v-loading="performanceLoading">
          <section class="workspace-panel">
            <div class="panel-heading">
              <div><h2>进程采样</h2><p>{{ metrics?.note || '等待采样数据' }}</p></div>
              <el-tag
                :type="metrics?.cache_metrics_available ? 'success' : 'info'"
                effect="plain"
                class="cache-status-tag"
              >
                缓存命中率 {{ metrics?.cache_metrics_available ? formatRate(metrics?.cache_hit_rate ?? 0) : '未采集' }}
              </el-tag>
            </div>

            <div class="runtime-facts" aria-label="采样上下文">
              <div class="runtime-fact">
                <span>采样窗口</span>
                <strong>{{ metrics?.request_count ?? 0 }} / {{ metrics?.window_capacity ?? 0 }}</strong>
                <small>当前记录 / 窗口容量</small>
              </div>
              <div class="runtime-fact">
                <span>采集时间</span>
                <strong>{{ formatDateTimeFull(metrics?.collected_at) }}</strong>
                <small>当前服务进程</small>
              </div>
              <div class="runtime-fact">
                <span>慢查询阈值</span>
                <strong>{{ formatThreshold(metrics?.slow_query_threshold_seconds) }}</strong>
                <small>单条数据库查询</small>
              </div>
              <div class="status-distribution">
                <span>HTTP 状态码分布</span>
                <div class="tag-list">
                  <el-tag
                    v-for="([statusCode, count]) in statusCodeEntries"
                    :key="statusCode"
                    :type="statusCodeTone(statusCode)"
                    size="small"
                    effect="plain"
                  >
                    {{ statusCode }} · {{ count }}
                  </el-tag>
                  <span v-if="!statusCodeEntries.length" class="muted">暂无请求样本</span>
                </div>
              </div>
            </div>

            <el-descriptions :column="3" border>
              <el-descriptions-item label="P50">{{ formatMs(metrics?.p50_response_time_ms) }}</el-descriptions-item>
              <el-descriptions-item label="P95">{{ formatMs(metrics?.p95_response_time_ms) }}</el-descriptions-item>
              <el-descriptions-item label="P99">{{ formatMs(metrics?.p99_response_time_ms) }}</el-descriptions-item>
              <el-descriptions-item label="查询总数">{{ metrics?.query_count ?? 0 }}</el-descriptions-item>
              <el-descriptions-item label="每请求查询">{{ metrics?.avg_query_count ?? 0 }}</el-descriptions-item>
              <el-descriptions-item label="平均查询耗时">{{ formatMs(metrics?.avg_query_time_ms) }}</el-descriptions-item>
            </el-descriptions>
          </section>

          <section class="workspace-panel">
            <div class="panel-heading">
              <div><h2>慢查询</h2><p>仅保留 SQL 形状，不记录参数值；阈值 {{ formatThreshold(slowQueryThreshold) }}。</p></div>
              <el-tag effect="plain">{{ slowQueries.length }} 条</el-tag>
            </div>
            <el-table :data="slowQueries" stripe>
              <el-table-column prop="timestamp" label="采集时间" width="168">
                <template #default="{ row }">{{ formatDateTimeFull(row.timestamp) }}</template>
              </el-table-column>
              <el-table-column prop="duration_ms" label="耗时" width="100">
                <template #default="{ row }">{{ formatMs(row.duration_ms) }}</template>
              </el-table-column>
              <el-table-column prop="method" label="方法" width="82" />
              <el-table-column prop="path" label="请求路径" min-width="190" show-overflow-tooltip />
              <el-table-column prop="sql" label="SQL 摘要" min-width="360" show-overflow-tooltip />
              <template #empty><EmptyState text="暂无慢查询" description="采样窗口内没有超过阈值的数据库查询" /></template>
            </el-table>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="OpenAPI 契约" name="openapi">
        <section v-loading="contractLoading" class="workspace-panel">
          <div class="panel-heading">
            <div><h2>版本化接口</h2><p>由标准 schema 生成器提取路径、摘要、标签与操作标识。</p></div>
            <el-tag effect="plain">{{ operationRows.length }} 个操作 · {{ endpoints.length }} 个路径</el-tag>
          </div>
          <el-input
            v-model="endpointSearch"
            :prefix-icon="Search"
            clearable
            placeholder="搜索路径、方法、摘要、标签或操作标识"
            class="endpoint-search"
          />
          <el-table :data="visibleOperations" stripe>
            <el-table-column label="方法" width="90">
              <template #default="{ row }"><el-tag :type="methodTone(row.method)" size="small" effect="plain">{{ row.method }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="path" label="路径" min-width="280" show-overflow-tooltip />
            <el-table-column label="摘要" min-width="230" show-overflow-tooltip>
              <template #default="{ row }"><span :class="{ muted: !row.summary }">{{ row.summary || '未提供摘要' }}</span></template>
            </el-table-column>
            <el-table-column label="标签" min-width="190">
              <template #default="{ row }">
                <div class="tag-list compact-tags">
                  <el-tag v-for="tag in row.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                  <span v-if="!row.tags.length" class="muted">未分类</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="operation_id" label="操作标识" min-width="260" show-overflow-tooltip>
              <template #default="{ row }"><code class="operation-id">{{ row.operation_id || '-' }}</code></template>
            </el-table-column>
            <template #empty><EmptyState text="没有匹配的接口" description="调整搜索条件后重试" /></template>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="质量门禁" name="quality">
        <section v-loading="governanceLoading" class="workspace-panel">
          <div class="panel-heading">
            <div><h2>API 治理</h2><p>按实际路由操作扫描认证、分页与细粒度权限边界。</p></div>
            <el-progress type="circle" :percentage="governance?.score ?? 0" :width="74" />
          </div>

          <div class="quality-summary" aria-label="质量门禁摘要">
            <div><span>扫描操作</span><strong>{{ governance?.endpoints_scanned ?? 0 }}</strong><small>{{ governance?.paths_scanned ?? 0 }} 个路径</small></div>
            <div><span>通过检查</span><strong class="is-pass">{{ governance?.passed ?? 0 }}</strong><small>共 {{ governance?.total ?? 0 }} 项</small></div>
            <div><span>失败检查</span><strong :class="(governance?.failed ?? 0) > 0 ? 'is-fail' : 'is-pass'">{{ governance?.failed ?? 0 }}</strong><small>需治理项</small></div>
          </div>

          <div class="check-list">
            <div v-for="check in governance?.checks || []" :key="check.item" class="check-row">
              <el-icon :class="check.passed ? 'is-pass' : 'is-fail'"><CircleCheck v-if="check.passed" /><CircleClose v-else /></el-icon>
              <div>
                <strong>{{ check.title }}</strong>
                <span>{{ check.detail }}</span>
                <div v-if="!check.passed && check.unrestricted?.length" class="unrestricted-list">
                  <small>未受限端点</small>
                  <code v-for="endpoint in check.unrestricted" :key="endpoint">{{ endpoint }}</code>
                  <small v-if="(check.unrestricted_count || 0) > check.unrestricted.length">
                    另有 {{ (check.unrestricted_count || 0) - check.unrestricted.length }} 个端点
                  </small>
                </div>
              </div>
            </div>
          </div>
          <el-alert
            :title="browserAuditTitle"
            :description="browserAuditDescription"
            type="info"
            show-icon
            :closable="false"
          />
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CircleCheck, CircleClose, Download, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDateTimeFull } from '@/utils/format'
import {
  getAccessibilityGovernance,
  getOpenApiEndpoints,
  getOpenApiSchema,
  getPerformanceMetrics,
  getSlowQueries,
  type EndpointItem,
  type GovernanceReport,
  type PerformanceMetrics,
  type SlowQuery,
} from '@/api/engineering'
import {
  AUTO_REFRESH_OPTIONS,
  DEFAULT_AUTO_REFRESH_MS,
  filterEndpointOperations,
  flattenEndpointOperations,
  methodTone,
  statusCodeTone,
} from './engineeringConsole'

const activeTab = ref('performance')
const endpointSearch = ref('')
const refreshIntervalMs = ref<number>(DEFAULT_AUTO_REFRESH_MS)
const performanceLoading = ref(false)
const contractLoading = ref(false)
const governanceLoading = ref(false)
const metrics = ref<PerformanceMetrics | null>(null)
const slowQueries = ref<SlowQuery[]>([])
const slowQueryThreshold = ref(0)
const endpoints = ref<EndpointItem[]>([])
const governance = ref<GovernanceReport | null>(null)
let autoRefreshTimer: number | null = null

const loading = computed(() => performanceLoading.value || contractLoading.value || governanceLoading.value)
const operationRows = computed(() => flattenEndpointOperations(endpoints.value))
const visibleOperations = computed(() => filterEndpointOperations(operationRows.value, endpointSearch.value))
const statusCodeEntries = computed(() => Object.entries(metrics.value?.status_codes || {})
  .sort(([left], [right]) => Number(left) - Number(right)))
const browserAuditTitle = computed(() => {
  const audit = governance.value?.browser_audit
  return `浏览器 WCAG（CI 执行，非实时） · ${audit?.standard || 'WCAG 2.1 A/AA'} · ${audit?.runner || 'Playwright + axe-core'}`
})
const browserAuditDescription = computed(() => {
  const audit = governance.value?.browser_audit
  if (!audit) return '等待 CI 扫描说明'
  return `${audit.note} 执行命令：${audit.command}`
})

function formatMs(value?: number): string {
  return `${(value || 0).toFixed(1)} ms`
}

function formatRate(value?: number): string {
  return `${((value || 0) * 100).toFixed(1)}%`
}

function formatThreshold(value?: number): string {
  return formatMs((value || 0) * 1000)
}

async function loadPerformance(): Promise<void> {
  if (performanceLoading.value) return
  performanceLoading.value = true
  try {
    // Read a diagnostic endpoint first so the metrics snapshot includes this
    // page's own completed request even in a freshly started worker process.
    const slowData = await getSlowQueries()
    const metricData = await getPerformanceMetrics()
    slowQueries.value = slowData.slow_queries
    slowQueryThreshold.value = slowData.threshold_seconds
    metrics.value = metricData
  } finally {
    performanceLoading.value = false
  }
}

async function loadOpenApi(): Promise<void> {
  if (contractLoading.value) return
  contractLoading.value = true
  try {
    const endpointData = await getOpenApiEndpoints()
    endpoints.value = endpointData.endpoints
  } finally {
    contractLoading.value = false
  }
}

async function loadGovernance(): Promise<void> {
  if (governanceLoading.value) return
  governanceLoading.value = true
  try {
    const governanceData = await getAccessibilityGovernance()
    governance.value = governanceData
  } finally {
    governanceLoading.value = false
  }
}

async function loadAll(): Promise<void> {
  await Promise.allSettled([loadPerformance(), loadOpenApi(), loadGovernance()])
}

function clearAutoRefresh(): void {
  if (autoRefreshTimer === null) return
  window.clearInterval(autoRefreshTimer)
  autoRefreshTimer = null
}

function configureAutoRefresh(): void {
  clearAutoRefresh()
  if (refreshIntervalMs.value <= 0) return
  autoRefreshTimer = window.setInterval(() => {
    void loadPerformance().catch(() => undefined)
  }, refreshIntervalMs.value)
}

async function downloadSchema(): Promise<void> {
  const schema = await getOpenApiSchema()
  const blob = new Blob([JSON.stringify(schema, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'teamforge-openapi.json'
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('OpenAPI 契约已下载')
}

watch(refreshIntervalMs, configureAutoRefresh)
onMounted(() => {
  configureAutoRefresh()
  void loadAll()
})
onBeforeUnmount(clearAutoRefresh)
</script>

<style scoped lang="scss">
.refresh-select { width: 112px; }
.metric-strip { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); margin-bottom: 16px; border: 1px solid var(--color-border-light); background: var(--color-surface); }
.metric-item { min-width: 0; padding: 16px; border-right: 1px solid var(--color-border-light); }
.metric-item:last-child { border-right: 0; }
.metric-item span { display: block; color: var(--color-text-secondary); font-size: 13px; }
.metric-item strong { display: block; margin-top: 7px; color: var(--color-text-primary); font-size: 23px; }
.workspace-panel { margin-bottom: 16px; padding: 18px; border: 1px solid var(--color-border-light); background: var(--color-surface); }
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.panel-heading h2 { margin: 0; font-size: 17px; }
.panel-heading p { margin: 5px 0 0; color: var(--color-text-secondary); font-size: 13px; }
.runtime-facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 16px; border: 1px solid var(--color-border-light); }
.runtime-fact { min-width: 0; padding: 13px 14px; border-right: 1px solid var(--color-border-light); }
.runtime-fact:nth-child(3) { border-right: 0; }
.runtime-fact span, .status-distribution > span, .quality-summary span { display: block; color: var(--color-text-secondary); font-size: 12px; }
.runtime-fact strong { display: block; margin-top: 5px; color: var(--color-text-primary); font-size: 15px; overflow-wrap: anywhere; }
.runtime-fact small, .quality-summary small { display: block; margin-top: 3px; color: var(--color-text-secondary); font-size: 11px; }
.status-distribution { grid-column: 1 / -1; padding: 12px 14px; border-top: 1px solid var(--color-border-light); }
.tag-list { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.compact-tags { margin-top: 0; }
.cache-status-tag.el-tag--info {
  --el-tag-text-color: #405b6b;
  color: #405b6b;
  opacity: 1 !important;
  transition: none !important;
  animation: none !important;
}
.cache-status-tag :deep(.el-tag__content) { color: inherit; }
:global(html.dark) .cache-status-tag.el-tag--info { --el-tag-text-color: var(--color-text-secondary); color: var(--color-text-secondary); }
.endpoint-search { max-width: 460px; margin-bottom: 14px; }
.operation-id { color: var(--color-text-primary); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }
.quality-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 16px; border: 1px solid var(--color-border-light); }
.quality-summary > div { min-width: 0; padding: 13px 14px; border-right: 1px solid var(--color-border-light); }
.quality-summary > div:last-child { border-right: 0; }
.quality-summary strong { display: block; margin-top: 4px; color: var(--color-text-primary); font-size: 22px; }
.quality-summary strong.is-pass { color: var(--color-success); }
.quality-summary strong.is-fail { color: var(--color-danger); }
.check-list { display: grid; gap: 10px; margin-bottom: 16px; }
.check-row { display: flex; align-items: flex-start; gap: 10px; padding: 12px; border: 1px solid var(--color-border-light); }
.check-row div { min-width: 0; }
.check-row strong, .check-row span { display: block; }
.check-row span { margin-top: 3px; color: var(--color-text-secondary); font-size: 13px; overflow-wrap: anywhere; }
.unrestricted-list { display: grid; gap: 5px; margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--color-border-light); }
.unrestricted-list small { color: var(--color-text-secondary); font-size: 12px; }
.unrestricted-list code { display: block; color: var(--color-danger); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; overflow-wrap: anywhere; }
.muted { color: var(--color-text-secondary); }
.is-pass { color: var(--color-success); }
.is-fail { color: var(--color-danger); }
@media (max-width: 900px) { .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } .metric-item { border-bottom: 1px solid var(--color-border-light); } .runtime-facts { grid-template-columns: 1fr; } .runtime-fact { border-right: 0; border-bottom: 1px solid var(--color-border-light); } .runtime-fact:nth-child(3) { border-bottom: 0; } }
@media (max-width: 600px) { .metric-strip, .quality-summary { grid-template-columns: 1fr; } .metric-item, .quality-summary > div { border-right: 0; border-bottom: 1px solid var(--color-border-light); } .quality-summary > div:last-child { border-bottom: 0; } .panel-heading { align-items: flex-start; flex-direction: column; } .workspace-panel { padding: 12px; } .refresh-select { width: 104px; } }
</style>
