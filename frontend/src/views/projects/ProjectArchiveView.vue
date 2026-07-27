<template>
  <div class="page-container archive-page">
    <PageHeader title="项目归档" subtitle="检索已获奖、已结项或已关闭项目，沉淀可复用成果">
      <template #actions>
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
      </template>
    </PageHeader>

    <div v-if="loadError" class="status-banner" role="alert">
      <el-icon><WarningFilled /></el-icon>
      <span>归档项目加载失败。</span>
      <el-button link type="primary" @click="loadData">重新加载</el-button>
    </div>

    <section class="filter-toolbar" aria-label="归档项目筛选">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleSearch">
        <el-form-item>
          <el-input
            v-model="queryParams.search"
            placeholder="搜索项目名称或编号"
            clearable
            :prefix-icon="Search"
            class="search-input"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-select v-model="queryParams.stage" placeholder="全部归档状态" clearable class="stage-filter" @change="handleSearch">
            <el-option label="已获奖" value="awarded" />
            <el-option label="已结项或关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <span class="result-count">共 {{ total }} 个归档项目</span>
    </section>

    <section v-loading="loading" class="metric-strip" aria-label="归档概览">
      <div>
        <span>归档项目</span>
        <strong class="tabular-nums">{{ stats.total }}</strong>
        <small>当前筛选范围</small>
      </div>
      <div>
        <span>获奖项目</span>
        <strong class="tabular-nums metric-success">{{ stats.awarded }}</strong>
        <small>最终阶段为已获奖</small>
      </div>
      <div>
        <span>结项项目</span>
        <strong class="tabular-nums">{{ stats.closed }}</strong>
        <small>已结项或已关闭</small>
      </div>
    </section>

    <section class="archive-workspace">
      <el-table v-if="!isMobile" v-loading="loading" :data="archiveList" @row-click="handleViewDetail">
        <template #empty>
          <EmptyState text="暂无归档项目" description="项目获奖、结项或关闭后会显示在这里。" icon="FolderOpened" compact />
        </template>
        <el-table-column label="项目" min-width="220">
          <template #default="{ row }">
            <div class="project-cell">
              <strong>{{ row.name }}</strong>
              <span>{{ row.code || '暂无项目编号' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="leader_name" label="负责人" width="110">
          <template #default="{ row }">{{ row.leader_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="最终阶段" width="118">
          <template #default="{ row }">
            <el-tag :type="row.current_stage === 13 ? 'success' : 'info'" size="small">
              {{ row.current_stage_display || getStageLabel(row.current_stage || 1) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行周期" min-width="190">
          <template #default="{ row }">
            <span class="date-range">{{ formatDate(row.start_date) }} 至 {{ formatDate(row.actual_end_date || row.planned_end_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="项目简介" min-width="210" show-overflow-tooltip>
          <template #default="{ row }">{{ row.intro || '-' }}</template>
        </el-table-column>
        <el-table-column width="52" fixed="right" align="center">
          <template #default><el-icon class="row-arrow"><ArrowRight /></el-icon></template>
        </el-table-column>
      </el-table>

      <div v-else-if="archiveList.length" class="archive-mobile-list">
        <article
          v-for="project in archiveList"
          :key="project.id"
          class="archive-mobile-row"
          role="button"
          tabindex="0"
          @click="handleViewDetail(project)"
          @keydown.enter="handleViewDetail(project)"
          @keydown.space.prevent="handleViewDetail(project)"
        >
          <div class="mobile-row-head">
            <div>
              <strong>{{ project.name }}</strong>
              <span>{{ project.code || '暂无项目编号' }}</span>
            </div>
            <el-tag :type="project.current_stage === 13 ? 'success' : 'info'" size="small">
              {{ project.current_stage_display || getStageLabel(project.current_stage || 1) }}
            </el-tag>
          </div>
          <p>{{ project.intro || '暂无项目简介' }}</p>
          <dl>
            <div><dt>负责人</dt><dd>{{ project.leader_name || '-' }}</dd></div>
            <div><dt>结束日期</dt><dd>{{ formatDate(project.actual_end_date || project.planned_end_date) }}</dd></div>
          </dl>
          <el-icon class="row-arrow"><ArrowRight /></el-icon>
        </article>
      </div>
      <EmptyState v-else-if="!loading" text="暂无归档项目" description="项目获奖、结项或关闭后会显示在这里。" icon="FolderOpened" compact />

      <AccessiblePagination
        v-if="total > 0"
        v-model:current-page="queryParams.page"
        v-model:page-size="queryParams.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next'"
        background
        @size-change="paginateArchive"
        @current-change="paginateArchive"
      />
    </section>

    <el-dialog v-model="detailVisible" :title="currentProject?.name || '项目详情'" width="700px">
      <el-descriptions v-if="currentProject" :column="isMobile ? 1 : 2" border>
        <el-descriptions-item label="项目编号">{{ currentProject.code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ currentProject.leader_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最终阶段">{{ currentProject.current_stage_display || getStageLabel(currentProject.current_stage || 1) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ currentProject.status_display || '-' }}</el-descriptions-item>
        <el-descriptions-item label="开始日期">{{ formatDate(currentProject.start_date) }}</el-descriptions-item>
        <el-descriptions-item label="结束日期">{{ formatDate(currentProject.actual_end_date || currentProject.planned_end_date) }}</el-descriptions-item>
        <el-descriptions-item label="项目简介" :span="isMobile ? 1 : 2">{{ currentProject.intro || '-' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="goToDetail">查看完整项目</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Refresh, Search, WarningFilled } from '@element-plus/icons-vue'
import { getProjects, type ProjectQueryParams } from '@/api/projects'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDevice } from '@/composables/useDevice'
import type { Project } from '@/types'
import { formatDate, getStageLabel } from '@/utils/format'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const router = useRouter()
const { isMobile } = useDevice()
const loading = ref(false)
const loadError = ref(false)
const allArchiveProjects = ref<Project[]>([])
const archiveList = ref<Project[]>([])
const total = ref(0)
const detailVisible = ref(false)
const currentProject = ref<Project | null>(null)

const queryParams = reactive<ProjectQueryParams & { stage?: string }>({
  page: 1,
  page_size: appStore.itemsPerPage,
  search: '',
  stage: undefined,
})

const stats = computed(() => ({
  total: allArchiveProjects.value.length,
  awarded: allArchiveProjects.value.filter((project) => project.current_stage === 13).length,
  closed: allArchiveProjects.value.filter((project) => project.current_stage === 14 || project.status === 'closed').length,
}))

function paginateArchive(): void {
  const page = queryParams.page || 1
  const pageSize = queryParams.page_size || 10
  const start = (page - 1) * pageSize
  archiveList.value = allArchiveProjects.value.slice(start, start + pageSize)
}

async function loadData(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const projectsFromAllPages: Project[] = []
    let page = 1
    while (true) {
      const response = await getProjects({
        page,
        page_size: 100,
        search: queryParams.search,
      })
      projectsFromAllPages.push(...response.results)
      if (!response.next || response.results.length === 0) break
      page += 1
    }

    let projects = projectsFromAllPages.filter((project) =>
      project.current_stage === 13 || project.current_stage === 14 || project.status === 'closed',
    )
    if (queryParams.stage === 'awarded') {
      projects = projects.filter((project) => project.current_stage === 13)
    } else if (queryParams.stage === 'closed') {
      projects = projects.filter((project) => project.current_stage === 14 || project.status === 'closed')
    }
    allArchiveProjects.value = projects
    total.value = projects.length
    const maxPage = Math.max(1, Math.ceil(total.value / (queryParams.page_size || 10)))
    if ((queryParams.page || 1) > maxPage) queryParams.page = maxPage
    paginateArchive()
  } catch {
    loadError.value = true
    allArchiveProjects.value = []
    archiveList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  queryParams.page = 1
  loadData()
}

function handleReset(): void {
  queryParams.search = ''
  queryParams.stage = undefined
  queryParams.page = 1
  loadData()
}

function handleViewDetail(project: Project): void {
  currentProject.value = project
  detailVisible.value = true
}

function goToDetail(): void {
  if (!currentProject.value) return
  detailVisible.value = false
  router.push(`/projects/${currentProject.value.id}`)
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.archive-page { display: flex; flex-direction: column; gap: 16px; }
.archive-page :deep(.page-header) { margin-bottom: 0; }

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
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.filter-toolbar :deep(.el-form-item) { margin-bottom: 14px; }
.search-input { width: 250px; }
.stage-filter { width: 170px; }
.result-count { margin-bottom: 14px; color: var(--color-text-muted); font-size: 12px; white-space: nowrap; }

.metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.metric-strip > div { display: flex; flex-direction: column; min-width: 0; padding: 15px 18px; }
.metric-strip > div + div { border-left: 1px solid var(--color-border-light); }
.metric-strip span { color: var(--color-text-muted); font-size: 11px; }
.metric-strip strong { margin-top: 4px; color: var(--color-text); font-size: 22px; font-weight: 650; }
.metric-strip small { margin-top: 2px; color: var(--color-text-muted); font-size: 10px; }
.metric-strip .metric-success { color: var(--color-success); }

.archive-workspace { padding: 0 16px 16px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.project-cell { display: flex; flex-direction: column; min-width: 0; }
.project-cell strong { overflow: hidden; color: var(--color-text); font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.project-cell span,
.date-range { margin-top: 2px; color: var(--color-text-muted); font-size: 11px; }
.row-arrow { color: var(--color-text-muted); }

.archive-mobile-row { position: relative; padding: 14px 28px 14px 0; border-bottom: 1px solid var(--color-border-light); }
.archive-mobile-row:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.mobile-row-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.mobile-row-head > div { display: flex; flex-direction: column; min-width: 0; }
.mobile-row-head strong { color: var(--color-text); font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.mobile-row-head span { margin-top: 3px; color: var(--color-text-muted); font-size: 11px; }
.archive-mobile-row > p { display: -webkit-box; margin-top: 8px; overflow: hidden; color: var(--color-text-regular); font-size: 12px; line-height: 1.5; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.archive-mobile-row dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 12px; margin-top: 10px; }
.archive-mobile-row dt { color: var(--color-text-muted); font-size: 10px; }
.archive-mobile-row dd { margin-top: 2px; overflow: hidden; color: var(--color-text-regular); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.archive-mobile-row > .row-arrow { position: absolute; top: 50%; right: 2px; transform: translateY(-50%); }

@media screen and (max-width: 768px) {
  .archive-page { gap: 12px; }
  .filter-toolbar { align-items: stretch; flex-direction: column; gap: 0; padding: 12px 12px 0; }
  .filter-toolbar :deep(.el-form) { display: grid; grid-template-columns: 1fr; }
  .search-input,
  .stage-filter { width: 100%; }
  .result-count { margin-top: -4px; }
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-strip > div + div { border-left: 0; }
  .metric-strip > div:nth-child(even) { border-left: 1px solid var(--color-border-light); }
  .metric-strip > div:nth-child(n + 3) { border-top: 1px solid var(--color-border-light); }
  .metric-strip > div:last-child:nth-child(odd) { grid-column: 1 / -1; }
  .metric-strip > div { padding: 12px; }
  .metric-strip strong { font-size: 18px; }
  .archive-workspace { padding: 0 14px 14px; }
}
</style>
