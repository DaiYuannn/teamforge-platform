<template>
  <div class="page-container project-list-page">
    <PageHeader title="项目管理" subtitle="统一查看项目进度、负责人和交付风险">
      <template #meta>
        <span class="page-meta">当前共 {{ total }} 个项目</span>
      </template>
      <template #actions>
        <el-button
          v-if="!isExternalCollaborator"
          :icon="Download"
          @click="handleExport"
        >
          导出 Excel
        </el-button>
        <el-button
          v-if="canCreateProject"
          type="primary"
          :icon="Plus"
          @click="handleCreate"
        >
          新建项目
        </el-button>
      </template>
    </PageHeader>

    <section class="project-workspace" aria-label="项目列表工作区">
      <div class="filter-toolbar">
        <el-form class="primary-filters" :inline="true" :model="queryParams" @submit.prevent>
          <el-form-item label="关键词">
            <el-input
              v-model="queryParams.search"
              class="keyword-input"
              placeholder="项目名称或编号"
              clearable
              :prefix-icon="Search"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="queryParams.status" class="status-select" placeholder="全部状态" clearable>
              <el-option
                v-for="(item, key) in PROJECT_STATUS_MAP"
                :key="key"
                :label="item.label"
                :value="key"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="数据范围">
            <el-select v-model="queryParams.scope" class="scope-select" aria-label="项目数据范围">
              <el-option label="与我相关" value="mine" />
              <el-option label="团队全部" value="team" />
            </el-select>
          </el-form-item>
          <el-form-item class="filter-actions">
            <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
            <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
            <el-dropdown
              trigger="click"
              :disabled="savingFilterPreference"
              @command="handleFilterPreferenceCommand"
            >
              <el-button :loading="savingFilterPreference">
                {{ hasSavedProjectFilters ? '筛选已记住' : '筛选偏好' }}
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="save">记住当前筛选</el-dropdown-item>
                  <el-dropdown-item command="clear" :disabled="!hasSavedProjectFilters">
                    清除已保存筛选
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button class="advanced-trigger" text type="primary" @click="advancedVisible = !advancedVisible">
              {{ advancedVisible ? '收起筛选' : '更多筛选' }}
              <el-icon class="advanced-arrow" :class="{ 'is-rotate': advancedVisible }">
                <ArrowDown />
              </el-icon>
            </el-button>
          </el-form-item>
        </el-form>

        <el-collapse-transition>
          <div v-show="advancedVisible" class="advanced-search">
            <el-form :inline="true" :model="queryParams" @submit.prevent>
              <el-form-item label="牵头负责人">
                <el-input
                  v-model="queryParams.leader"
                  placeholder="姓名或 ID"
                  clearable
                  @keyup.enter="handleSearch"
                />
              </el-form-item>
              <el-form-item label="开始日期">
                <el-date-picker
                  v-model="queryParams.start_date"
                  type="date"
                  placeholder="选择日期"
                  value-format="YYYY-MM-DD"
                />
              </el-form-item>
              <el-form-item label="结束日期">
                <el-date-picker
                  v-model="queryParams.end_date"
                  type="date"
                  placeholder="选择日期"
                  value-format="YYYY-MM-DD"
                />
              </el-form-item>
              <el-form-item label="排序方式">
                <el-select v-model="queryParams.ordering" placeholder="默认排序" clearable>
                  <el-option label="创建时间倒序" value="-created_at" />
                  <el-option label="创建时间正序" value="created_at" />
                  <el-option label="开始时间倒序" value="-start_date" />
                  <el-option label="开始时间正序" value="start_date" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
        </el-collapse-transition>

        <div v-if="activeFilters.length" class="filter-tags">
          <span class="filter-tags-label">已筛选</span>
          <el-tag
            v-for="filter in activeFilters"
            :key="filter.key"
            closable
            size="small"
            effect="plain"
            @close="removeFilter(filter.key)"
          >
            {{ filter.label }}：{{ filter.value }}
          </el-tag>
          <el-button link type="primary" size="small" @click="handleReset">清除全部</el-button>
        </div>
      </div>

      <div class="list-heading">
        <div>
          <h2>项目清单</h2>
        </div>
        <span class="list-count"><strong>{{ total }}</strong> 个结果</span>
      </div>

      <div v-if="!isCardView" class="table-shell">
        <el-table
          v-loading="loading"
          :data="projectList"
          stripe
          size="small"
          row-class-name="project-row"
          @row-click="handleRowClick"
        >
          <template #empty>
            <EmptyState
              text="暂无项目"
              description="调整筛选条件，或创建第一个项目"
              :illustration="true"
              accent="#176b73"
            >
              <template #action>
                <el-button
                  v-if="canCreateProject"
                  type="primary"
                  :icon="Plus"
                  @click="handleCreate"
                >
                  新建项目
                </el-button>
              </template>
            </EmptyState>
          </template>
          <el-table-column label="项目" min-width="220">
            <template #default="{ row }">
              <div class="project-cell">
                <button class="project-name" type="button" @click.stop="handleDetail(row as Project)">
                  {{ row.name }}
                </button>
                <span class="project-code">{{ row.code || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态 / 优先级" width="154">
            <template #default="{ row }">
              <div class="tag-pair">
                <el-tag :type="getProjectStatusTagType(row.status) as any" size="small" effect="light">
                  {{ getProjectStatusLabel(row.status) }}
                </el-tag>
                <el-tag :type="getPriorityTagType(row.priority) as any" size="small" effect="plain">
                  {{ getPriorityLabel(row as Project) }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="当前阶段" min-width="124">
            <template #default="{ row }">
              <span class="stage-value">
                {{ row.current_stage_display || getStageLabel(row.current_stage || '') || '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="项目负责人" min-width="150">
            <template #default="{ row }">
              {{ row.leader_names?.join('、') || row.leader_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="关联小组 / 可见范围" min-width="170">
            <template #default="{ row }">
              <div class="project-cell">
                <span>{{ row.team_names?.join('、') || '未限定小组' }}</span>
                <span class="project-code">{{ row.visibility_display || '全团队' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="计划结束" width="116">
            <template #default="{ row }">
              <span class="tabular-nums">{{ formatDate(row.planned_end_date) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="进度风险" width="112">
            <template #default="{ row }">
              <el-tooltip :content="getProjectRisk(row as Project).detail" placement="top">
                <el-tag :type="getProjectRisk(row as Project).type as any" size="small" effect="plain">
                  {{ getProjectRisk(row as Project).label }}
                </el-tag>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="项目规模" min-width="176">
            <template #default="{ row }">
              <div class="project-scale">
                <span>成员 {{ row.member_count ?? 0 }}</span>
                <span>任务 {{ row.task_count ?? 0 }}</span>
                <span>比赛 {{ row.competition_count ?? 0 }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            v-if="!isExternalCollaborator"
            label="经费余额"
            width="122"
            align="right"
          >
            <template #default="{ row }">
              <span
                class="finance-balance tabular-nums"
                :class="{ 'is-negative': Number(row.finance_balance || 0) < 0 }"
              >
                {{ formatMoneyWithComma(row.finance_balance || 0) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="最近更新" width="116">
            <template #default="{ row }">
              <el-tooltip
                :content="row.last_leader_update ? '负责人最近一次进度更新' : '尚未打卡，当前以项目创建时间起算'"
                placement="top"
              >
                <span class="tabular-nums">
                  {{ formatDate(row.last_leader_update || row.created_at) }}
                </span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="176" fixed="right" align="right">
            <template #default="{ row }">
              <el-button :icon="View" type="primary" link @click.stop="handleDetail(row as Project)">查看</el-button>
              <el-button
                v-if="row.can_manage"
                :icon="EditPen"
                link
                @click.stop="handleEdit(row as Project)"
              >
                编辑
              </el-button>
              <el-button
                v-if="row.can_manage"
                :icon="Delete"
                type="danger"
                link
                @click.stop="handleDelete(row as Project)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-else v-loading="loading" class="mobile-project-list">
        <article v-for="item in projectList" :key="item.id" class="mobile-project-card">
          <div class="mobile-card-heading">
            <div class="mobile-title-block">
              <button class="mobile-project-title" type="button" @click="handleDetail(item)">
                {{ item.name }}
              </button>
              <span class="project-code">{{ item.code || '-' }}</span>
            </div>
            <el-tag :type="getProjectStatusTagType(item.status) as any" size="small" effect="light">
              {{ getProjectStatusLabel(item.status) }}
            </el-tag>
          </div>

          <p v-if="item.intro" class="mobile-project-intro">{{ item.intro }}</p>

          <dl class="mobile-project-meta">
            <div>
              <dt>项目负责人</dt>
              <dd>{{ item.leader_names?.join('、') || item.leader_name || '-' }}</dd>
            </div>
            <div>
              <dt>关联小组</dt>
              <dd>{{ item.team_names?.join('、') || '未限定小组' }} · {{ item.visibility_display || '全团队' }}</dd>
            </div>
            <div>
              <dt>当前阶段</dt>
              <dd>{{ item.current_stage_display || getStageLabel(item.current_stage || '') || '-' }}</dd>
            </div>
            <div>
              <dt>优先级</dt>
              <dd>
                <el-tag :type="getPriorityTagType(item.priority) as any" size="small" effect="plain">
                  {{ getPriorityLabel(item) }}
                </el-tag>
              </dd>
            </div>
            <div>
              <dt>计划结束</dt>
              <dd class="tabular-nums">{{ formatDate(item.planned_end_date) }}</dd>
            </div>
            <div>
              <dt>进度风险</dt>
              <dd>
                <el-tag :type="getProjectRisk(item).type as any" size="small" effect="plain">
                  {{ getProjectRisk(item).label }}
                </el-tag>
              </dd>
            </div>
            <div>
              <dt>成员</dt>
              <dd>{{ item.member_count ?? 0 }} 人</dd>
            </div>
            <div>
              <dt>任务 / 比赛</dt>
              <dd>{{ item.task_count ?? 0 }} / {{ item.competition_count ?? 0 }}</dd>
            </div>
            <div v-if="!isExternalCollaborator">
              <dt>经费余额</dt>
              <dd
                class="tabular-nums"
                :class="{ 'finance-balance is-negative': Number(item.finance_balance || 0) < 0 }"
              >
                {{ formatMoneyWithComma(item.finance_balance || 0) }}
              </dd>
            </div>
            <div>
              <dt>最近更新</dt>
              <dd class="tabular-nums">{{ formatDate(item.last_leader_update || item.created_at) }}</dd>
            </div>
          </dl>

          <div class="mobile-card-actions">
            <el-button :icon="View" type="primary" link @click="handleDetail(item)">查看</el-button>
            <el-button
              v-if="item.can_manage"
              :icon="EditPen"
              link
              @click="handleEdit(item)"
            >
              编辑
            </el-button>
            <el-button
              v-if="item.can_manage"
              :icon="Delete"
              type="danger"
              link
              @click="handleDelete(item)"
            >
              删除
            </el-button>
          </div>
        </article>

        <EmptyState
          v-if="projectList.length === 0 && !loading"
          text="暂无项目"
          description="调整筛选条件，或创建第一个项目"
          accent="#176b73"
        />
      </div>

      <div v-if="total > 0" class="pagination-wrapper">
        <AccessiblePagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          :layout="isCardView ? 'prev, pager, next' : 'total, sizes, prev, pager, next'"
          background
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </section>

    <ProjectFormDialog
      v-model:visible="formDialogVisible"
      :form-data="editingProject"
      @success="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  Delete,
  Download,
  EditPen,
  Plus,
  RefreshLeft,
  Search,
  View,
} from '@element-plus/icons-vue'
import { getProjects, deleteProject, type ProjectQueryParams } from '@/api/projects'
import { getTeams, type Team } from '@/api/teams'
import { exportData } from '@/api/exports'
import {
  downloadBlob,
  formatDate,
  formatMoneyWithComma,
  getStageLabel,
  getProjectStatusLabel,
  getProjectStatusTagType,
} from '@/utils/format'
import { PROJECT_STATUS_MAP } from '@/utils/constants'
import {
  hasSavedFilterModule,
  mergeSavedFilterModule,
  normalizeProjectSavedFilters,
} from '@/utils/savedFilters'
import { useDevice } from '@/composables/useDevice'
import { useMobileNavigate } from '@/composables/useMobileNavigate'
import type { Project, ProjectFormData } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import ProjectFormDialog from './ProjectFormDialog.vue'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'

const appStore = useAppStore()
const userStore = useUserStore()
const isExternalCollaborator = computed(
  () => userStore.userInfo?.membership_status === 'external',
)

type EditableProjectFormData = ProjectFormData & { id: number }

interface ProjectRisk {
  label: string
  detail: string
  type: 'success' | 'warning' | 'danger' | 'info'
}

const router = useRouter()
const route = useRoute()
const { smartNavigate } = useMobileNavigate()
const { isMobile: isCardView } = useDevice()

const loading = ref(false)
const projectList = ref<Project[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const editingProject = ref<EditableProjectFormData | null>(null)
const teamOptions = ref<Team[]>([])
const advancedVisible = ref(false)
const savingFilterPreference = ref(false)
const accountDefaultScope: 'mine' | 'team' =
  userStore.preferences?.default_scope === 'team' ? 'team' : 'mine'
const canCreateProject = computed(() =>
  userStore.isTeacher
  || userStore.isAdmin
  || Boolean(userStore.userInfo?.permission_codes?.includes('project.create'))
  || teamOptions.value.some((team) => team.can_manage),
)

// 查询参数
const queryParams = reactive<ProjectQueryParams>({
  page: 1,
  page_size: appStore.itemsPerPage,
  search: '',
  status: '',
  leader: '',
  start_date: '',
  end_date: '',
  ordering: '',
  scope: accountDefaultScope,
})

const hasSavedProjectFilters = computed(() =>
  hasSavedFilterModule(userStore.preferences?.saved_filters, 'projects'),
)

const activeFilters = computed(() => {
  const tags: { key: string; label: string; value: string }[] = []
  if (queryParams.search) tags.push({ key: 'search', label: '关键词', value: queryParams.search })
  if (queryParams.status) tags.push({ key: 'status', label: '状态', value: getProjectStatusLabel(queryParams.status) })
  if (queryParams.leader) tags.push({ key: 'leader', label: '负责人', value: String(queryParams.leader) })
  if (queryParams.start_date) tags.push({ key: 'start_date', label: '开始日期', value: queryParams.start_date })
  if (queryParams.end_date) tags.push({ key: 'end_date', label: '结束日期', value: queryParams.end_date })
  if (queryParams.ordering) {
    const orderMap: Record<string, string> = {
      '-created_at': '创建时间倒序',
      created_at: '创建时间正序',
      '-start_date': '开始时间倒序',
      start_date: '开始时间正序',
    }
    tags.push({ key: 'ordering', label: '排序', value: orderMap[queryParams.ordering] || queryParams.ordering })
  }
  return tags
})

function getPriorityLabel(project: Project): string {
  if (project.priority_display) return project.priority_display
  const labels: Record<string, string> = {
    normal: '普通',
    high: '高',
    urgent: '紧急',
  }
  return labels[project.priority || 'normal'] || project.priority || '普通'
}

function getPriorityTagType(priority?: string): 'info' | 'warning' | 'danger' {
  if (priority === 'urgent') return 'danger'
  if (priority === 'high') return 'warning'
  return 'info'
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null
  const normalized = value.length === 10 ? `${value}T00:00:00` : value
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

function getProjectRisk(item: Project): ProjectRisk {
  if (item.status === 'closed') {
    return { label: '已结项', detail: '项目已关闭，不再计算进行中风险', type: 'info' }
  }
  if (item.status === 'paused') {
    return { label: '已暂停', detail: '项目当前处于暂停状态', type: 'warning' }
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const plannedEnd = parseDate(item.planned_end_date)
  const lastUpdate = parseDate(item.last_leader_update) || parseDate(item.created_at)
  const oneDay = 24 * 60 * 60 * 1000

  if (plannedEnd && plannedEnd.getTime() < today.getTime()) {
    const overdueDays = Math.ceil((today.getTime() - plannedEnd.getTime()) / oneDay)
    return { label: '计划逾期', detail: `已超过计划结束日期 ${overdueDays} 天`, type: 'danger' }
  }

  if (lastUpdate) {
    const staleDays = Math.floor((today.getTime() - lastUpdate.getTime()) / oneDay)
    if (staleDays >= 11) {
      return { label: '更新滞后', detail: `负责人已有 ${staleDays} 天未更新项目`, type: 'warning' }
    }
  }

  if (plannedEnd) {
    const remainingDays = Math.ceil((plannedEnd.getTime() - today.getTime()) / oneDay)
    if (remainingDays <= 14) {
      return { label: '临近截止', detail: `距计划结束还有 ${Math.max(remainingDays, 0)} 天`, type: 'warning' }
    }
  }

  return { label: '节奏正常', detail: '当前未发现计划逾期或更新滞后', type: 'success' }
}

function removeFilter(key: string): void {
  switch (key) {
    case 'search':
      queryParams.search = ''
      break
    case 'status':
      queryParams.status = ''
      break
    case 'leader':
      queryParams.leader = ''
      break
    case 'start_date':
      queryParams.start_date = ''
      break
    case 'end_date':
      queryParams.end_date = ''
      break
    case 'ordering':
      queryParams.ordering = ''
      break
  }
  queryParams.page = 1
  loadData()
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const params: Record<string, any> = { page: queryParams.page, page_size: queryParams.page_size }
    if (queryParams.search) params.search = queryParams.search
    if (queryParams.status) params.status = queryParams.status
    if (queryParams.leader) params.leader = queryParams.leader
    if (queryParams.start_date) params.start_date = queryParams.start_date
    if (queryParams.end_date) params.end_date = queryParams.end_date
    if (queryParams.ordering) params.ordering = queryParams.ordering
    if (queryParams.scope) params.scope = queryParams.scope
    const res = await getProjects(params as ProjectQueryParams)
    projectList.value = res.results
    total.value = res.count
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function loadTeamOptions(): Promise<void> {
  try {
    teamOptions.value = (await getTeams()).results
  } catch {
    teamOptions.value = []
  }
}

function handleSearch(): void {
  queryParams.page = 1
  loadData()
}

function handleReset(): void {
  queryParams.search = ''
  queryParams.status = ''
  queryParams.leader = ''
  queryParams.start_date = ''
  queryParams.end_date = ''
  queryParams.ordering = ''
  queryParams.scope = accountDefaultScope
  queryParams.page = 1
  loadData()
}

function restoreProjectSavedFilters(): void {
  const saved = normalizeProjectSavedFilters(
    userStore.preferences?.saved_filters?.projects,
  )
  queryParams.search = saved.search ?? ''
  queryParams.status = saved.status ?? ''
  queryParams.leader = saved.leader ?? ''
  queryParams.start_date = saved.start_date ?? ''
  queryParams.end_date = saved.end_date ?? ''
  queryParams.ordering = saved.ordering ?? ''
  queryParams.scope = saved.scope ?? accountDefaultScope
  advancedVisible.value = Boolean(
    saved.leader
    || saved.start_date
    || saved.end_date
    || saved.ordering,
  )
}

function currentProjectFilterSnapshot() {
  return normalizeProjectSavedFilters({
    search: queryParams.search,
    status: queryParams.status,
    leader: queryParams.leader,
    start_date: queryParams.start_date,
    end_date: queryParams.end_date,
    ordering: queryParams.ordering,
    scope: queryParams.scope,
  })
}

async function saveCurrentProjectFilters(): Promise<void> {
  savingFilterPreference.value = true
  try {
    const savedFilters = mergeSavedFilterModule(
      userStore.preferences?.saved_filters,
      'projects',
      currentProjectFilterSnapshot(),
    )
    await userStore.savePreference({ saved_filters: savedFilters })
    ElMessage.success('已记住当前项目筛选')
  } catch {
    // 请求层统一处理错误。
  } finally {
    savingFilterPreference.value = false
  }
}

async function clearSavedProjectFilters(): Promise<void> {
  savingFilterPreference.value = true
  try {
    const savedFilters = mergeSavedFilterModule(
      userStore.preferences?.saved_filters,
      'projects',
      null,
    )
    await userStore.savePreference({ saved_filters: savedFilters })
    ElMessage.success('已清除项目筛选偏好')
  } catch {
    // 请求层统一处理错误。
  } finally {
    savingFilterPreference.value = false
  }
}

async function handleFilterPreferenceCommand(
  command: string | number | object,
): Promise<void> {
  if (command === 'save') await saveCurrentProjectFilters()
  if (command === 'clear') await clearSavedProjectFilters()
}

function handleCreate(): void {
  editingProject.value = null
  formDialogVisible.value = true
}

function handleEdit(row: Project): void {
  editingProject.value = {
    id: row.id,
    name: row.name,
    code: row.code,
    intro: row.intro,
    leader: row.leader,
    start_date: row.start_date,
    planned_end_date: row.planned_end_date,
    status: row.status,
  }
  formDialogVisible.value = true
}

function handleDetail(row: Project): void {
  smartNavigate(`/projects/${row.id}`)
}

function handleRowClick(row: Project): void {
  handleDetail(row)
}

async function handleDelete(row: Project): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除项目「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProject(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // 取消
  }
}

async function handleExport(): Promise<void> {
  try {
    const blob = await exportData('projects', 'xlsx')
    downloadBlob(blob, `projects_xlsx_${Date.now()}.xlsx`)
    ElMessage.success('导出成功')
  } catch {
    // 错误已由拦截器处理
  }
}

onMounted(async () => {
  restoreProjectSavedFilters()
  await Promise.all([loadData(), loadTeamOptions()])
  if (route.query.action === 'create' && canCreateProject.value) {
    handleCreate()
    router.replace({ path: '/projects' })
  }
})
</script>

<style lang="scss" scoped>
.project-list-page {
  padding-bottom: 32px;
}

.page-meta {
  display: inline-block;
  margin-top: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.project-workspace {
  min-width: 0;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.filter-toolbar {
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border-light);
}

.primary-filters {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-toolbar :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}

.filter-toolbar :deep(.el-form-item__label) {
  color: var(--color-text-regular);
  font-size: 13px;
}

.keyword-input {
  width: 260px;
}

.status-select {
  width: 132px;
}

.scope-select {
  width: 124px;
}

.filter-actions {
  margin-left: auto;
}

.advanced-trigger {
  padding-right: 4px;
  padding-left: 4px;
}

.advanced-arrow {
  margin-left: 4px;
  transition: transform var(--transition-base);

  &.is-rotate {
    transform: rotate(180deg);
  }
}

.advanced-search {
  margin-top: 14px;
  padding: 14px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.advanced-search :deep(.el-form) {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr));
  gap: 12px;
}

.advanced-search :deep(.el-form-item) {
  display: block;
}

.advanced-search :deep(.el-form-item__label) {
  display: block;
  width: 100%;
  height: auto;
  margin-bottom: 6px;
  line-height: 1.4;
}

.advanced-search :deep(.el-input),
.advanced-search :deep(.el-select),
.advanced-search :deep(.el-date-editor) {
  width: 100%;
}

.filter-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.filter-tags-label {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 600;
}

.list-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px 12px;
}

.list-heading h2 {
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.4;
}

.list-count {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
}

.list-count strong {
  color: var(--color-text);
  font-size: 15px;
  font-weight: 600;
}

.table-shell {
  min-width: 0;
  overflow-x: auto;
  border-top: 1px solid var(--color-border-light);
}

.table-shell :deep(.el-table) {
  min-width: 1080px;
}

.table-shell :deep(.project-row) {
  cursor: pointer;
}

.project-cell,
.mobile-title-block {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.project-name,
.mobile-project-title {
  max-width: 100%;
  padding: 0;
  overflow: hidden;
  color: var(--color-text);
  font: inherit;
  font-weight: 600;
  line-height: 1.4;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.project-name:hover,
.mobile-project-title:hover {
  color: var(--color-primary);
}

.project-code {
  color: var(--color-text-muted);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 11px;
  line-height: 1.4;
}

.project-scale {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  color: var(--color-text-regular);
  font-size: 12px;
  white-space: nowrap;
}

.finance-balance {
  color: var(--color-text);
  font-weight: 600;
}

.finance-balance.is-negative {
  color: var(--color-danger);
}

.tag-pair {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.stage-value {
  display: block;
  overflow: hidden;
  color: var(--color-text-regular);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-project-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 14px 14px;
}

.mobile-project-card {
  padding: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.mobile-card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mobile-title-block {
  flex: 1;
}

.mobile-project-title {
  font-size: 15px;
  white-space: normal;
}

.mobile-project-intro {
  display: -webkit-box;
  margin-top: 9px;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.mobile-project-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  margin-top: 14px;
  padding-top: 13px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-project-meta div {
  min-width: 0;
}

.mobile-project-meta dt {
  margin-bottom: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.mobile-project-meta dd {
  min-width: 0;
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-light);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 0 18px 16px;
  border-top: 1px solid var(--color-border-light);
}

@media screen and (max-width: 1100px) {
  .advanced-search :deep(.el-form) {
    grid-template-columns: repeat(2, minmax(170px, 1fr));
  }

  .filter-actions {
    width: 100%;
    margin-left: 0;
  }
}

@media screen and (max-width: 768px) {
  .project-list-page {
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }

  .filter-toolbar {
    padding: 14px;
  }

  .primary-filters {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 112px;
    gap: 12px 10px;
  }

  .primary-filters :deep(.el-form-item) {
    display: block;
    min-width: 0;
  }

  .primary-filters :deep(.el-form-item__label) {
    display: block;
    width: 100%;
    height: auto;
    margin-bottom: 5px;
    line-height: 1.4;
  }

  .keyword-input,
  .status-select,
  .scope-select {
    width: 100%;
  }

  .filter-actions {
    display: flex !important;
    grid-column: 1 / -1;
    align-items: center;
    gap: 6px;
  }

  .filter-actions :deep(.el-form-item__content) {
    flex-wrap: wrap;
    gap: 6px;
  }

  .filter-actions :deep(.el-button + .el-button) {
    margin-left: 0;
  }

  .advanced-search :deep(.el-form) {
    grid-template-columns: 1fr;
  }

  .list-heading {
    align-items: flex-start;
    padding-right: 14px;
    padding-left: 14px;
  }

  .pagination-wrapper {
    justify-content: center;
    padding-right: 8px;
    padding-left: 8px;
  }
}

@media screen and (max-width: 380px) {
  .primary-filters {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    grid-column: 1;
  }

}
</style>
