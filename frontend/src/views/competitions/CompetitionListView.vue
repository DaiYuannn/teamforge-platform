<template>
  <div class="page-container competition-page">
    <PageHeader title="比赛管理" subtitle="集中维护赛事节点，比较项目参赛情况与晋级结果">
      <template #actions>
        <el-button
          :icon="Download"
          :loading="exporting"
          @click="handleExport"
        >
          导出当前筛选 Excel
        </el-button>
        <el-button
          v-if="canCreateCompetition"
          type="primary"
          :icon="Plus"
          @click="handleCreate"
        >
          新建比赛
        </el-button>
      </template>
    </PageHeader>

    <section class="view-toolbar" aria-label="比赛数据视图">
      <div class="view-segment" role="group" aria-label="切换比赛视图">
        <button
          v-for="view in viewOptions"
          :key="view.value"
          type="button"
          class="view-segment__item"
          :class="{ 'is-active': currentView === view.value }"
          :aria-pressed="currentView === view.value"
          @click="currentView = view.value"
        >
          <el-icon aria-hidden="true"><component :is="view.icon" /></el-icon>
          <span>{{ view.label }}</span>
        </button>
      </div>
      <span v-if="currentView === 'list'" class="view-total">
        共 <strong>{{ total }}</strong> 场比赛
      </span>
    </section>

    <template v-if="currentView === 'list'">
      <section class="filter-panel" aria-label="比赛筛选">
        <el-form
          class="filter-form"
          :inline="!isMobile"
          :label-position="isMobile ? 'top' : 'left'"
          :model="queryParams"
          @submit.prevent="handleSearch"
        >
          <el-form-item label="关键词">
            <el-input
              v-model="queryParams.search"
              :prefix-icon="Search"
              placeholder="搜索比赛名称"
              clearable
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="项目">
            <el-select
              v-model="queryParams.project"
              placeholder="全部项目"
              clearable
              filterable
              :loading="projectsLoading"
            >
              <el-option
                v-for="project in projectOptions"
                :key="project.id"
                :label="project.name"
                :value="project.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="级别">
            <el-select v-model="queryParams.level" placeholder="全部级别" clearable>
              <el-option
                v-for="(item, key) in COMPETITION_LEVEL_MAP"
                :key="key"
                :label="item.label"
                :value="key"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="queryParams.status" placeholder="全部状态" clearable>
              <el-option
                v-for="(item, key) in COMPETITION_STATUS_MAP"
                :key="key"
                :label="item.label"
                :value="key"
              />
            </el-select>
          </el-form-item>
          <el-form-item class="filter-actions">
            <el-button type="primary" :icon="Search" native-type="submit">查询</el-button>
            <el-button :icon="Refresh" :disabled="!hasActiveFilters" @click="handleReset">
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </section>

      <el-alert
        v-if="loadFailed"
        class="load-alert"
        title="比赛数据暂时无法加载"
        type="error"
        :closable="false"
        show-icon
      >
        <template #default>
          <el-button link type="primary" @click="loadData">重新加载</el-button>
        </template>
      </el-alert>

      <section v-loading="loading" class="list-surface" aria-label="比赛列表">
        <div v-if="!isMobile" class="desktop-table">
          <el-table :data="competitionList" table-layout="fixed">
            <template #empty>
              <EmptyState
                v-if="!loading"
                text="暂无比赛"
                description="创建比赛后，赛事节点会集中显示在这里"
              >
                <template #action>
                  <el-button
                    v-if="canCreateCompetition"
                    type="primary"
                    :icon="Plus"
                    @click="handleCreate"
                  >
                    新建比赛
                  </el-button>
                </template>
              </EmptyState>
            </template>

            <el-table-column label="比赛" min-width="220">
              <template #default="{ row }">
                <button
                  type="button"
                  class="competition-name-cell competition-name-button"
                  @click="handleView(row as CompetitionRow)"
                >
                  <strong>{{ row.name }}</strong>
                  <span>{{ row.project_name || row.organizer || '未关联项目' }}</span>
                </button>
              </template>
            </el-table-column>
            <el-table-column label="级别" width="88">
              <template #default="{ row }">
                <el-tag
                  size="small"
                  :type="getCompetitionStageTagType(row.level) as any"
                  effect="light"
                  :style="getCompetitionStageTagStyle(row.level)"
                >
                  {{ getCompetitionLevelLabel(row.level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="organizer" label="主办方" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">{{ row.organizer || '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="96">
              <template #default="{ row }">
                <el-tag :type="getCompetitionStatusTagType(row.status) as any" size="small">
                  {{ getCompetitionStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="比赛负责人 / 参赛人数" min-width="160">
              <template #default="{ row }">
                <div class="milestone-cell">
                  <span>{{ row.leader_names?.join('、') || '待指定负责人' }}</span>
                  <span><small>成员</small>{{ row.participant_count || 0 }} 人</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="当前阶段" min-width="124" show-overflow-tooltip>
              <template #default="{ row }">{{ row.current_stage || '-' }}</template>
            </el-table-column>
            <el-table-column label="报名 / 答辩" min-width="174">
              <template #default="{ row }">
                <div class="milestone-cell">
                  <span><small>报名</small>{{ displayDate(row.register_date) }}</span>
                  <span><small>答辩</small>{{ displayDate(row.defense_date) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="结果公布" width="116">
              <template #default="{ row }">{{ displayDate(row.result_date) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="184" fixed="right" align="right">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  :icon="View"
                  :loading="detailLoadingId === row.id"
                  @click="handleView(row as CompetitionRow)"
                >
                  查看
                </el-button>
                <el-button
                  v-if="canEditCompetition(row as CompetitionRow)"
                  type="primary"
                  link
                  :icon="Edit"
                  :loading="editingId === row.id"
                  @click="handleEdit(row as CompetitionRow)"
                >
                  编辑
                </el-button>
                <el-button
                  v-if="canEditCompetition(row as CompetitionRow)"
                  type="danger"
                  link
                  :icon="Delete"
                  @click="handleDelete(row as CompetitionRow)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-else class="mobile-list">
          <EmptyState
            v-if="!loading && competitionList.length === 0"
            text="暂无比赛"
            description="创建比赛后，赛事节点会集中显示在这里"
          >
            <template #action>
              <el-button
                v-if="canCreateCompetition"
                type="primary"
                :icon="Plus"
                @click="handleCreate"
              >
                新建比赛
              </el-button>
            </template>
          </EmptyState>

          <article v-for="item in competitionList" :key="item.id" class="competition-row">
            <header class="competition-row__header">
              <div>
                <h2>{{ item.name }}</h2>
                <p>{{ item.project_name || item.organizer || '未关联项目' }}</p>
              </div>
              <el-tag :type="getCompetitionStatusTagType(item.status) as any" size="small">
                {{ getCompetitionStatusLabel(item.status) }}
              </el-tag>
            </header>

            <dl class="competition-row__details">
              <div>
                <dt>级别</dt>
                <dd>{{ getCompetitionLevelLabel(item.level) }}</dd>
              </div>
              <div>
                <dt>报名</dt>
                <dd>{{ displayDate(item.register_date) }}</dd>
              </div>
              <div>
                <dt>答辩</dt>
                <dd>{{ displayDate(item.defense_date) }}</dd>
              </div>
              <div>
                <dt>结果</dt>
                <dd>{{ displayDate(item.result_date) }}</dd>
              </div>
              <div>
                <dt>比赛负责人</dt>
                <dd>{{ item.leader_names?.join('、') || '待指定' }}</dd>
              </div>
              <div>
                <dt>参赛人数</dt>
                <dd>{{ item.participant_count || 0 }} 人</dd>
              </div>
            </dl>

            <footer class="competition-row__actions">
              <el-button
                type="primary"
                link
                :icon="View"
                :loading="detailLoadingId === item.id"
                @click="handleView(item)"
              >
                查看
              </el-button>
              <el-button
                v-if="canEditCompetition(item)"
                type="primary"
                link
                :icon="Edit"
                :loading="editingId === item.id"
                @click="handleEdit(item)"
              >
                编辑
              </el-button>
              <el-button
                v-if="canEditCompetition(item)"
                type="danger"
                link
                :icon="Delete"
                @click="handleDelete(item)"
              >
                删除
              </el-button>
            </footer>
          </article>
        </div>

        <div v-if="total > 0" class="pagination-wrapper">
          <AccessiblePagination
            v-model:current-page="queryParams.page"
            v-model:page-size="queryParams.page_size"
            :total="total"
            :page-sizes="[10, 20, 50]"
            :layout="paginationLayout"
            :size="isMobile ? 'small' : 'default'"
            background
            @size-change="loadData"
            @current-change="loadData"
          />
        </div>
      </section>
    </template>

    <CompetitionMatrixView v-else-if="currentView === 'matrix'" />
    <CompetitionFunnelView v-else />

    <CompetitionFormDialog
      v-model:visible="formDialogVisible"
      :form-data="editingCompetition"
      @success="loadData"
    />
    <CompetitionDetailDialog
      v-model:visible="detailDialogVisible"
      :competition="selectedCompetition"
      :can-manage="Boolean(selectedCompetition?.can_manage)"
      @edit="handleDetailEdit"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataAnalysis,
  Delete,
  Download,
  Edit,
  Grid,
  List,
  Plus,
  Refresh,
  Search,
  View,
} from '@element-plus/icons-vue'
import {
  deleteCompetition,
  exportCompetitions,
  getCompetition,
  getCompetitions,
  type CompetitionQueryParams,
} from '@/api/competitions'
import { getProjects } from '@/api/projects'
import {
  downloadBlob,
  formatDate,
  getCompetitionLevelLabel,
  getCompetitionStageTagStyle,
  getCompetitionStageTagType,
  getCompetitionStatusLabel,
  getCompetitionStatusTagType,
} from '@/utils/format'
import { COMPETITION_LEVEL_MAP, COMPETITION_STATUS_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import { positiveQueryId } from '@/utils/globalSearch'
import type { Competition, Project } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import CompetitionFormDialog from './CompetitionFormDialog.vue'
import CompetitionDetailDialog from './CompetitionDetailDialog.vue'
import CompetitionMatrixView from './CompetitionMatrixView.vue'
import CompetitionFunnelView from './CompetitionFunnelView.vue'
import {
  parseCompetitionProjectQuery,
  toCompetitionExportParams,
} from './competitionWorkflow'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const appStore = useAppStore()

type ViewMode = 'list' | 'matrix' | 'funnel'
type CompetitionRow = Competition

const viewOptions = [
  { value: 'list', label: '赛事列表', icon: List },
  { value: 'matrix', label: '参赛矩阵', icon: Grid },
  { value: 'funnel', label: '晋级漏斗', icon: DataAnalysis },
] as const

const { isMobile } = useDevice()
const currentView = ref<ViewMode>('list')
const loading = ref(false)
const loadFailed = ref(false)
const competitionList = ref<CompetitionRow[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const editingCompetition = ref<Competition | null>(null)
const selectedCompetition = ref<Competition | null>(null)
const detailLoadingId = ref<number | null>(null)
const editingId = ref<number | null>(null)
const exporting = ref(false)
const projectsLoading = ref(false)
const projectOptions = ref<Project[]>([])

const queryParams = reactive<CompetitionQueryParams>({
  page: 1,
  page_size: appStore.itemsPerPage,
  search: '',
  level: '',
  status: '',
  project: parseCompetitionProjectQuery(route.query.project_id),
})

const hasActiveFilters = computed(
  () => Boolean(queryParams.search || queryParams.project || queryParams.level || queryParams.status),
)
const canCreateCompetition = computed(
  () => projectOptions.value.some((project) => project.can_manage),
)
const paginationLayout = computed(() =>
  isMobile.value ? 'prev, pager, next' : 'total, sizes, prev, pager, next',
)

async function loadData(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    const res = await getCompetitions(queryParams)
    competitionList.value = res.results
    total.value = res.count
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '-'
}

function handleSearch(): void {
  queryParams.page = 1
  loadData()
}

function handleReset(): void {
  queryParams.search = ''
  queryParams.project = undefined
  queryParams.level = ''
  queryParams.status = ''
  queryParams.page = 1
  loadData()
}

function handleCreate(): void {
  editingCompetition.value = null
  formDialogVisible.value = true
}

function canEditCompetition(row: CompetitionRow): boolean {
  return Boolean(row.can_manage)
}

async function handleView(row: CompetitionRow): Promise<void> {
  if (detailLoadingId.value !== null) return
  detailLoadingId.value = row.id
  try {
    selectedCompetition.value = await getCompetition(row.id)
    detailDialogVisible.value = true
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    detailLoadingId.value = null
  }
}

async function handleEdit(row: CompetitionRow): Promise<void> {
  if (editingId.value !== null) return
  editingId.value = row.id
  try {
    // 列表接口是摘要数据，编辑前必须读取完整详情，避免隐藏节点被空值覆盖。
    editingCompetition.value = await getCompetition(row.id)
    formDialogVisible.value = true
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    editingId.value = null
  }
}

function handleDetailEdit(competition: Competition): void {
  detailDialogVisible.value = false
  editingCompetition.value = competition
  formDialogVisible.value = true
}

async function handleExport(): Promise<void> {
  if (exporting.value) return
  exporting.value = true
  try {
    const blob = await exportCompetitions(toCompetitionExportParams(queryParams))
    downloadBlob(blob, `比赛列表_${new Date().toISOString().slice(0, 10)}.xlsx`)
    ElMessage.success('比赛筛选结果已导出')
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    exporting.value = false
  }
}

async function loadProjectOptions(): Promise<void> {
  projectsLoading.value = true
  try {
    const response = await getProjects({ page: 1, page_size: 100 })
    projectOptions.value = response.results
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    projectsLoading.value = false
  }
}

async function handleDelete(row: CompetitionRow): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除比赛「${row.name}」吗？`, '删除比赛', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
    await deleteCompetition(row.id)
    ElMessage.success('删除成功')
    const currentPage = queryParams.page || 1
    if (competitionList.value.length === 1 && currentPage > 1) {
      queryParams.page = currentPage - 1
    }
    loadData()
  } catch {
    // 用户取消删除或请求错误已由拦截器处理。
  }
}

onMounted(async () => {
  await Promise.all([loadProjectOptions(), loadData()])
  const competitionId = positiveQueryId(route.query.competition_id)
  if (!competitionId) return
  detailLoadingId.value = competitionId
  try {
    selectedCompetition.value = await getCompetition(competitionId)
    detailDialogVisible.value = true
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    detailLoadingId.value = null
  }
})
</script>

<style lang="scss" scoped>
.competition-page {
  --competition-row-padding: 16px 18px;
}

.view-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.view-segment {
  display: inline-grid;
  grid-template-columns: repeat(3, minmax(104px, 1fr));
  gap: 2px;
  padding: 3px;
  background: var(--color-surface-strong);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.view-segment__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 34px;
  padding: 0 13px;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0;
  background: transparent;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  transition: color var(--transition-fast), background var(--transition-fast);

  &:hover {
    color: var(--color-text);
  }

  &.is-active {
    color: var(--color-primary);
    background: var(--color-surface);
    box-shadow: inset 0 0 0 1px var(--color-border-light);
  }
}

.view-total {
  color: var(--color-text-muted);
  font-size: 13px;

  strong {
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }
}

.filter-panel,
.list-surface {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.filter-panel {
  padding: 14px 16px 0;
  margin-bottom: 12px;
}

.filter-form {
  :deep(.el-form-item) {
    margin-right: 12px;
    margin-bottom: 14px;
  }

  :deep(.el-input) {
    width: 220px;
  }

  :deep(.el-select) {
    width: 132px;
  }
}

.filter-actions {
  margin-left: auto;
  margin-right: 0 !important;
}

.load-alert {
  margin-bottom: 12px;
}

.list-surface {
  min-height: 220px;
  overflow: hidden;
}

.desktop-table {
  :deep(.el-table) {
    --el-table-border-color: var(--color-border-light);
  }

  :deep(.el-table::before) {
    display: none;
  }

  :deep(.el-table th.el-table__cell) {
    height: 42px;
    background: var(--color-surface-subtle);
  }

  :deep(.el-table td.el-table__cell) {
    height: 58px;
  }
}

.competition-name-cell,
.milestone-cell {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.competition-name-cell {
  gap: 3px;

  strong {
    overflow: hidden;
    color: var(--color-text);
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    overflow: hidden;
    color: var(--color-text-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.competition-name-button {
  width: 100%;
  padding: 0;
  text-align: left;
  background: transparent;
  border: 0;
  cursor: pointer;

  &:hover strong,
  &:focus-visible strong {
    color: var(--color-primary);
  }

  &:focus-visible {
    outline: 2px solid color-mix(in srgb, var(--color-primary) 38%, transparent);
    outline-offset: 3px;
    border-radius: 2px;
  }
}

.milestone-cell {
  gap: 3px;
  color: var(--color-text-regular);
  font-size: 12px;
  font-variant-numeric: tabular-nums;

  span {
    display: flex;
    gap: 7px;
  }

  small {
    width: 26px;
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.mobile-list {
  padding: 0 14px;
}

.competition-row {
  padding: 16px 0;
  border-bottom: 1px solid var(--color-border-light);

  &:last-child {
    border-bottom: 0;
  }
}

.competition-row__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;

  > div {
    min-width: 0;
  }

  h2 {
    overflow-wrap: anywhere;
    color: var(--color-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 1.45;
    letter-spacing: 0;
  }

  p {
    margin-top: 3px;
    overflow: hidden;
    color: var(--color-text-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.competition-row__details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
  margin-top: 16px;

  div {
    min-width: 0;
  }

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 2px;
    color: var(--color-text-regular);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
  }
}

.competition-row__actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  padding-top: 12px;
  margin-top: 14px;
  border-top: 1px solid var(--color-border-light);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 0 16px 16px;
  border-top: 1px solid var(--color-border-light);
}

@media screen and (max-width: 768px) {
  .view-toolbar {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
  }

  .view-segment {
    width: 100%;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .view-segment__item {
    min-width: 0;
    padding: 0 6px;
  }

  .view-total {
    align-self: flex-end;
  }

  .filter-panel {
    padding: 14px;
  }

  .filter-form {
    :deep(.el-form-item) {
      margin-right: 0;
      margin-bottom: 12px;
    }

    :deep(.el-form-item__label) {
      margin-bottom: 5px;
      line-height: 1.2;
    }

    :deep(.el-input),
    :deep(.el-select) {
      width: 100%;
    }
  }

  .filter-actions {
    margin-bottom: 0 !important;

    :deep(.el-form-item__content) {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    :deep(.el-button) {
      width: 100%;
      margin-left: 0;
    }
  }

  .list-surface {
    overflow: visible;
    background: transparent;
    border: 0;
  }

  .mobile-list {
    display: grid;
    gap: 10px;
    padding: 0;
  }

  .competition-row {
    padding: 14px;
    background: var(--color-surface);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-md);

    &:last-child {
      border-bottom: 1px solid var(--color-border-light);
    }
  }

  .pagination-wrapper {
    justify-content: center;
    padding: 14px 8px 0;
    border-top: 0;
  }
}

@media screen and (max-width: 380px) {
  .view-segment__item {
    gap: 4px;
    font-size: 12px;
  }
}
</style>
