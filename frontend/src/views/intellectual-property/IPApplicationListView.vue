<template>
  <div class="page-container ip-list-page">
    <PageHeader title="成果与知识产权" subtitle="跟踪成果申请、责任分工和全流程状态">
      <template #actions>
        <el-button :icon="Download" @click="handleExport">导出</el-button>
        <el-button v-if="canCreateApplication" type="primary" :icon="Plus" @click="handleCreate">
          新建申请
        </el-button>
      </template>
    </PageHeader>

    <div v-if="loadError" class="status-banner" role="alert">
      <el-icon><WarningFilled /></el-icon>
      <span>申请数据加载失败。</span>
      <el-button link type="primary" @click="loadData">重新加载</el-button>
    </div>

    <section class="filter-toolbar" aria-label="知识产权筛选">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleSearch">
        <el-form-item>
          <el-input
            v-model="queryParams.search"
            placeholder="搜索成果名称或编号"
            clearable
            :prefix-icon="Search"
            class="search-input"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-select v-model="queryParams.ip_type" placeholder="全部成果类型" clearable class="type-filter">
            <el-option v-for="(item, key) in IP_TYPE_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="queryParams.status" placeholder="全部流程状态" clearable filterable class="status-filter">
            <el-option v-for="(item, key) in IP_STATUS_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item class="filter-actions">
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <span class="result-count">共 {{ total }} 项成果</span>
    </section>

    <section v-if="!isMobile" class="data-workspace">
      <el-table v-loading="loading" :data="ipList" row-class-name="clickable-row" @row-click="handleDetail">
        <template #empty>
          <EmptyState
            text="暂无知识产权申请"
            description="新建申请后可在这里跟踪材料、审核和授权进度。"
            icon="Medal"
            accent="#76559B"
          />
        </template>
        <el-table-column label="成果" min-width="230">
          <template #default="{ row }">
            <div class="title-cell">
              <strong>{{ row.title }}</strong>
              <span>{{ row.application_code || '暂无内部编号' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="ip_type" label="类型" width="122">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.ip_type)" size="small">
              {{ IP_TYPE_MAP[row.ip_type]?.label || row.ip_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="related_project_name" label="关联项目" min-width="145" show-overflow-tooltip>
          <template #default="{ row }">{{ row.related_project_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="当前状态" width="132">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.status)" size="small">
              {{ IP_STATUS_MAP[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前责任" min-width="156">
          <template #default="{ row }">
            <div class="owner-cell">
              <span>{{ row.main_writer_name || '未分配撰写人' }}</span>
              <small>执行：{{ row.applicant_executor_name || '未分配' }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="return_count" label="退回" width="76" align="center">
          <template #default="{ row }">
            <span :class="['return-count', { 'return-count--danger': row.return_count > 0 }]">
              {{ row.return_count || 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最近更新" width="112">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column width="52" fixed="right" align="center">
          <template #default>
            <el-icon class="row-arrow"><ArrowRight /></el-icon>
          </template>
        </el-table-column>
      </el-table>

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
    </section>

    <section v-else v-loading="loading" class="mobile-workspace">
      <button
        v-for="item in ipList"
        :key="item.id"
        type="button"
        class="application-card"
        @click="handleDetail(item)"
      >
        <span class="application-card__head">
          <span class="application-card__title">{{ item.title }}</span>
          <el-tag :type="getStatusColor(item.status)" size="small">
            {{ IP_STATUS_MAP[item.status]?.label || item.status }}
          </el-tag>
        </span>
        <span class="application-card__meta">
          <span>{{ IP_TYPE_MAP[item.ip_type]?.label || item.ip_type }}</span>
          <span>{{ item.related_project_name || '未关联项目' }}</span>
        </span>
        <span class="application-card__owners">
          <span><small>撰写</small>{{ item.main_writer_name || '未分配' }}</span>
          <span><small>执行</small>{{ item.applicant_executor_name || '未分配' }}</span>
          <span :class="{ danger: item.return_count > 0 }"><small>退回</small>{{ item.return_count || 0 }} 次</span>
        </span>
        <span class="application-card__footer">
          更新于 {{ formatDate(item.updated_at) }}
          <el-icon><ArrowRight /></el-icon>
        </span>
      </button>

      <EmptyState
        v-if="!loading && !ipList.length"
        text="暂无知识产权申请"
        description="新建申请后可在这里跟踪完整流程。"
        icon="Medal"
        accent="#76559B"
      />

      <AccessiblePagination
        v-if="total > queryParams.page_size"
        v-model:current-page="queryParams.page"
        :total="total"
        :page-size="queryParams.page_size"
        layout="prev, pager, next"
        size="small"
        background
        @current-change="loadData"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Download, Plus, Refresh, Search, WarningFilled } from '@element-plus/icons-vue'
import { exportData } from '@/api/exports'
import { getIPApplications } from '@/api/intellectualProperty'
import { getProjects } from '@/api/projects'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDevice } from '@/composables/useDevice'
import { useUserStore } from '@/stores/user'
import type { IPApplicationListItem } from '@/types/intellectualProperty'
import { downloadBlob, formatDate } from '@/utils/format'
import { IP_STATUS_MAP, IP_TYPE_MAP } from '@/utils/constants'
import { normalizeIPProjectFilter } from './ipWorkflow'

const router = useRouter()
const route = useRoute()
const { isMobile } = useDevice()
const userStore = useUserStore()
const loading = ref(false)
const loadError = ref(false)
const leadsProject = ref(false)
const ipList = ref<IPApplicationListItem[]>([])
const total = ref(0)
const canCreateApplication = computed(() =>
  userStore.role === 'sys_admin' || userStore.role === 'teacher' || leadsProject.value,
)

const queryParams = reactive({
  page: 1,
  page_size: userStore.itemsPerPage,
  search: '',
  ip_type: '',
  status: '',
  related_project: normalizeIPProjectFilter(route.query.project_id),
})

async function loadData(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const response = await getIPApplications(queryParams)
    ipList.value = response.results || []
    total.value = response.count || 0
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function loadCreatePermission(): Promise<void> {
  if (userStore.role === 'sys_admin' || userStore.role === 'teacher') return
  try {
    if (!userStore.userInfo) await userStore.fetchProfile()
    const response = await getProjects({ page: 1, page_size: 100 })
    leadsProject.value = response.results.some((project) => project.can_manage)
  } catch {
    leadsProject.value = false
  }
}

function handleSearch(): void {
  queryParams.page = 1
  loadData()
}

function handleReset(): void {
  Object.assign(queryParams, {
    page: 1,
    search: '',
    ip_type: '',
    status: '',
    related_project: undefined,
  })
  if (route.query.project_id !== undefined) {
    const query = { ...route.query }
    delete query.project_id
    router.replace({ query })
    return
  }
  loadData()
}

function handleCreate(): void {
  router.push('/intellectual-property/create')
}

function handleDetail(row: IPApplicationListItem): void {
  router.push(`/intellectual-property/${row.id}`)
}

function getTypeColor(type: string): any {
  return (IP_TYPE_MAP[type]?.color || 'info') as any
}

function getStatusColor(status: string): any {
  return (IP_STATUS_MAP[status]?.color || 'info') as any
}

async function handleExport(): Promise<void> {
  try {
    const blob = await exportData('ip_applications', 'xlsx')
    downloadBlob(blob, `intellectual_property_${Date.now()}.xlsx`)
    ElMessage.success('导出成功')
  } catch {
    // The request interceptor presents the backend error.
  }
}

onMounted(() => {
  loadData()
  loadCreatePermission()
})

watch(
  () => route.query.project_id,
  (projectId) => {
    queryParams.related_project = normalizeIPProjectFilter(projectId)
    queryParams.page = 1
    loadData()
  },
)
</script>

<style lang="scss" scoped>
.ip-list-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ip-list-page :deep(.page-header) { margin-bottom: 0; }

.status-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  color: var(--danger-text);
  background: var(--danger-light);
  border: 1px solid var(--danger-border);
  border-radius: var(--radius-sm);
}

.status-banner span { flex: 1; }

.filter-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.filter-toolbar :deep(.el-form) { display: flex; flex: 1; flex-wrap: wrap; gap: 8px; }
.filter-toolbar :deep(.el-form-item) { margin: 0; }
.search-input { width: 240px; }
.type-filter { width: 160px; }
.status-filter { width: 180px; }

.result-count {
  flex: 0 0 auto;
  padding-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.data-workspace {
  min-width: 0;
  padding: 0 16px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.data-workspace :deep(.clickable-row) { cursor: pointer; }

.title-cell,
.owner-cell {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.title-cell strong {
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.title-cell span,
.owner-cell small {
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.owner-cell span { color: var(--color-text-regular); font-size: 12px; }
.return-count { color: var(--color-text-muted); font-variant-numeric: tabular-nums; }
.return-count--danger { color: var(--color-danger); font-weight: 650; }
.row-arrow { color: var(--color-text-muted); }

.mobile-workspace {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 160px;
}

.application-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 14px;
  color: var(--color-text);
  text-align: left;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.application-card__head,
.application-card__meta,
.application-card__owners,
.application-card__footer {
  display: flex;
  align-items: center;
}

.application-card__head { justify-content: space-between; gap: 10px; }
.application-card__title { min-width: 0; overflow: hidden; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.application-card__meta { gap: 12px; margin-top: 7px; color: var(--color-text-muted); font-size: 12px; }
.application-card__owners { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: 12px; padding: 10px 0; border-top: 1px solid var(--color-border-light); border-bottom: 1px solid var(--color-border-light); }
.application-card__owners > span { display: flex; flex-direction: column; min-width: 0; overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.application-card__owners small { margin-bottom: 2px; color: var(--color-text-muted); font-size: 10px; }
.application-card__owners .danger { color: var(--color-danger); }
.application-card__footer { justify-content: space-between; margin-top: 9px; color: var(--color-text-muted); font-size: 11px; }

@media screen and (max-width: 768px) {
  .filter-toolbar { flex-direction: column; }
  .filter-toolbar :deep(.el-form) { width: 100%; }
  .search-input { width: 100%; }
  .type-filter,
  .status-filter { width: calc(50vw - 24px); }
  .filter-actions { width: 100%; }
  .result-count { padding-top: 0; }
}
</style>
