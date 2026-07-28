<template>
  <div class="page-container task-page">
    <PageHeader title="任务管理" subtitle="跨项目跟进分工、状态与截止时间">
      <template #actions>
        <el-radio-group v-if="!isMobile" v-model="viewMode" size="small" class="view-switcher">
          <el-radio-button value="table">
            <el-icon><Grid /></el-icon>
            <span>列表</span>
          </el-radio-button>
          <el-radio-button value="board">
            <el-icon><Operation /></el-icon>
            <span>看板</span>
          </el-radio-button>
        </el-radio-group>
        <el-button
          v-if="canExportTasks"
          :icon="Download"
          :loading="exporting"
          @click="handleExport"
        >
          导出当前结果
        </el-button>
        <el-button
          v-if="canManageTasks"
          type="primary"
          :icon="Plus"
          @click="handleCreate"
        >
          新建任务
        </el-button>
      </template>
    </PageHeader>

    <section class="task-filter-panel" aria-label="任务筛选">
      <el-form
        class="task-filter-form"
        :model="queryParams"
        label-position="top"
        size="small"
        @submit.prevent="handleSearch"
      >
        <el-form-item label="关键词" class="filter-keyword">
          <el-input
            v-model="queryParams.search"
            :prefix-icon="Search"
            placeholder="任务标题、描述或项目"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>

        <el-form-item label="项目" class="filter-project">
          <el-select v-model="queryParams.project" placeholder="全部项目" filterable clearable>
            <el-option
              v-for="project in projectOptions"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部状态" clearable>
            <el-option
              v-for="(item, value) in TASK_STATUS_MAP"
              :key="value"
              :label="item.label"
              :value="value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="优先级">
          <el-select v-model="queryParams.priority" placeholder="全部优先级" clearable>
            <el-option
              v-for="(item, value) in TASK_PRIORITY_MAP"
              :key="value"
              :label="item.label"
              :value="value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="任务负责人" class="filter-assignee">
          <el-select
            v-model="queryParams.assignee"
            placeholder="全部任务负责人"
            filterable
            clearable
          >
            <el-option
              v-for="user in assigneeFilterOptions"
              :key="user.id"
              :label="user.name"
              :value="user.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="数据范围" class="filter-scope">
          <el-select v-model="queryParams.scope" aria-label="任务数据范围">
            <el-option label="与我相关" value="mine" />
            <el-option label="团队全部" value="team" />
          </el-select>
        </el-form-item>

        <el-form-item class="filter-actions">
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" :disabled="!hasFilters" @click="handleReset">重置</el-button>
          <el-dropdown
            class="filter-preference-dropdown"
            trigger="click"
            :disabled="savingFilterPreference"
            @command="handleFilterPreferenceCommand"
          >
            <el-button :loading="savingFilterPreference">
              {{ hasSavedTaskFilters ? '筛选已记住' : '筛选偏好' }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="save">记住当前筛选</el-dropdown-item>
                <el-dropdown-item command="clear" :disabled="!hasSavedTaskFilters">
                  清除已保存筛选
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-form-item>
      </el-form>
    </section>

    <section class="task-workspace" :class="{ 'is-board': activeView === 'board' }">
      <header class="workspace-header">
        <div class="workspace-heading">
          <h2>{{ activeView === 'table' ? '任务清单' : '任务看板' }}</h2>
          <p>{{ activeView === 'table' ? '按项目、任务负责人和期限汇总' : '按主流程状态组织当前任务' }}</p>
        </div>
        <span class="result-count">共 {{ total }} 项</span>
      </header>

      <div v-if="activeView === 'table'" class="table-wrap">
        <el-table
          v-loading="loading"
          class="dense-task-table"
          :data="taskList"
          row-key="id"
          size="small"
          stripe
        >
          <template #empty>
            <EmptyState text="暂无任务" description="调整筛选条件或新建任务" accent="var(--color-primary)" />
          </template>

          <el-table-column prop="title" label="任务" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="task-title-cell">
                <span class="priority-marker" :class="`priority-${row.priority || 'medium'}`"></span>
                <div class="task-title-copy">
                  <strong>{{ row.title }}</strong>
                  <span>#{{ row.id }}</span>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="project_name" label="所属项目" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="project-cell">
                <el-icon><Folder /></el-icon>
                <span>{{ row.project_name || '-' }}</span>
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="assignee_name" label="任务负责人" width="132">
            <template #default="{ row }">
              <span class="assignee-cell">
                <el-avatar :size="24">{{ getInitial(row.assignee_name) }}</el-avatar>
                <span>{{ row.assignee_name || '-' }}</span>
              </span>
            </template>
          </el-table-column>

          <el-table-column label="协作执行 / 验收" min-width="170">
            <template #default="{ row }">
              <div class="milestone-cell">
                <span>{{ row.collaborator_names?.join('、') || '无协作执行人' }}</span>
                <span><small>验收</small>{{ row.reviewer_name || '项目负责人' }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="status" label="状态" width="104">
            <template #default="{ row }">
              <el-tag :type="getTaskStatusTagType(row.status) as any" size="small">
                {{ getTaskStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="priority" label="优先级" width="92">
            <template #default="{ row }">
              <el-tag :type="getTaskPriorityTagType(row.priority || 'medium') as any" size="small">
                {{ row.priority_display || getTaskPriorityLabel(row.priority || 'medium') }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="deadline" label="截止时间" width="158">
            <template #default="{ row }">
              <span class="deadline-cell" :class="deadlineClass(row as Task)">
                <el-icon><Calendar /></el-icon>
                <span>{{ formatDateTime(row.deadline) }}</span>
              </span>
            </template>
          </el-table-column>

          <el-table-column
            label="操作"
            width="132"
            fixed="right"
            align="center"
          >
            <template #default="{ row }">
              <div class="row-actions">
                <el-tooltip content="打开协作详情" placement="top">
                  <el-button
                    circle
                    type="primary"
                    plain
                    :icon="ChatDotRound"
                    aria-label="打开任务协作详情"
                    @click="openTaskCollaboration(row as Task)"
                  />
                </el-tooltip>
                <el-tooltip v-if="canManageTask(row as Task)" content="编辑任务" placement="top">
                  <el-button
                    circle
                    :icon="Edit"
                    :loading="detailLoadingId === row.id"
                    aria-label="编辑任务"
                    @click="handleEdit(row as Task)"
                  />
                </el-tooltip>
                <el-tooltip v-if="canManageTask(row as Task)" content="删除任务" placement="top">
                  <el-button
                    circle
                    type="danger"
                    plain
                    :icon="Delete"
                    aria-label="删除任务"
                    @click="handleDelete(row as Task)"
                  />
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-else v-loading="loading" class="board-wrap">
        <TaskBoard
          :tasks="taskList"
          :interactive="true"
          :can-change-status="canChangeTaskStatus"
          :can-change-to-status="canChangeTaskToStatus"
          @change-status="handleChangeStatus"
          @task-click="handleBoardTaskClick"
        />
      </div>

      <footer v-if="total > 0" class="pagination-wrapper">
        <AccessiblePagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[20, 50, 100]"
          :layout="paginationLayout"
          :pager-count="isMobile ? 5 : 7"
          background
          @size-change="loadData"
          @current-change="loadData"
        />
      </footer>
    </section>

    <TaskFormDialog
      v-model:visible="formDialogVisible"
      :form-data="editingTask"
      :projects="manageableProjects"
      :assignees="assigneeOptions"
      @success="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  Calendar,
  ChatDotRound,
  Delete,
  Download,
  Edit,
  Folder,
  Grid,
  Operation,
  Plus,
  Refresh,
  Search,
} from '@element-plus/icons-vue'
import { changeTaskStatus, deleteTask, getTask, getTasks, type TaskQueryParams } from '@/api/tasks'
import { exportData } from '@/api/exports'
import { getProjectMembers, getProjects } from '@/api/projects'
import { getUsers } from '@/api/users'
import {
  downloadBlob,
  formatDateTime,
  getTaskPriorityLabel,
  getTaskPriorityTagType,
  getTaskStatusLabel,
  getTaskStatusTagType,
} from '@/utils/format'
import { TASK_PRIORITY_MAP, TASK_STATUS_MAP } from '@/utils/constants'
import {
  hasSavedFilterModule,
  mergeSavedFilterModule,
  normalizeTaskSavedFilters,
} from '@/utils/savedFilters'
import { useDevice } from '@/composables/useDevice'
import { useUserStore } from '@/stores/user'
import type { Project, Task, TaskFormData, TaskStatus, User } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import TaskBoard from '@/components/TaskBoard.vue'
import TaskFormDialog from './TaskFormDialog.vue'
import {
  canTransitionTaskStatus,
  getAllowedTaskStatusTargets,
  parsePositiveRouteId,
} from './taskWorkflow'

type ViewMode = 'table' | 'board'
type EditableTask = TaskFormData & { id: number }

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { isMobile } = useDevice(769)

const loading = ref(false)
const detailLoadingId = ref<number | null>(null)
const taskList = ref<Task[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const editingTask = ref<EditableTask | null>(null)
const projectOptions = ref<Project[]>([])
const assigneeOptions = ref<User[]>([])
const viewMode = ref<ViewMode>('table')
const savingFilterPreference = ref(false)
const exporting = ref(false)
const accountDefaultScope: 'mine' | 'team' =
  userStore.preferences?.default_scope === 'team' ? 'team' : 'mine'

const queryParams = reactive<TaskQueryParams>({
  page: 1,
  page_size: userStore.itemsPerPage,
  search: '',
  project: undefined,
  status: undefined,
  priority: undefined,
  assignee: undefined,
  scope: accountDefaultScope,
})

const activeView = computed<ViewMode>(() => (isMobile.value ? 'board' : viewMode.value))
const isGlobalTaskManager = computed(() => ['teacher', 'sys_admin'].includes(userStore.role))
const manageableProjects = computed(() => {
  if (isGlobalTaskManager.value) return projectOptions.value
  const userId = userStore.userInfo?.id
  return projectOptions.value.filter((project) => project.leader === userId)
})
const canManageTasks = computed(() => manageableProjects.value.length > 0)
const canExportTasks = computed(() => !['external', 'exited'].includes(
  userStore.userInfo?.membership_status || 'active',
))
const paginationLayout = computed(() =>
  isMobile.value ? 'total, prev, pager, next' : 'total, sizes, prev, pager, next',
)
const hasFilters = computed(() => Boolean(
  queryParams.search ||
  queryParams.project ||
  queryParams.status ||
  queryParams.priority ||
  queryParams.assignee ||
  queryParams.scope !== accountDefaultScope,
))
const hasSavedTaskFilters = computed(() =>
  hasSavedFilterModule(userStore.preferences?.saved_filters, 'tasks'),
)
const assigneeFilterOptions = computed(() => {
  const options = new Map<number, { id: number; name: string }>()
  assigneeOptions.value.forEach((user) => {
    options.set(user.id, { id: user.id, name: user.name || user.username })
  })
  taskList.value.forEach((task) => {
    if (task.assignee && task.assignee_name) {
      options.set(task.assignee, { id: task.assignee, name: task.assignee_name })
    }
  })
  return Array.from(options.values())
})

async function loadOptions(): Promise<void> {
  const projectsResult = await getProjects({ page: 1, page_size: 100 })
  projectOptions.value = projectsResult.results

  if (isGlobalTaskManager.value) {
    const usersResult = await getUsers({ page: 1, page_size: 100, is_active: true })
    assigneeOptions.value = usersResult.results
    return
  }

  const memberships = await Promise.all(
    manageableProjects.value.map((project) => getProjectMembers(project.id)),
  )
  const members = new Map<number, User>()
  memberships.flat().forEach((membership) => {
    const user = membership.user_detail as User | undefined
    if (user) members.set(user.id, user)
  })
  assigneeOptions.value = Array.from(members.values())
}

function canManageTask(task: Task): boolean {
  if (isGlobalTaskManager.value) return true
  return manageableProjects.value.some((project) => project.id === task.project)
}

function canChangeTaskStatus(task: Task): boolean {
  const userId = userStore.userInfo?.id
  return getAllowedTaskStatusTargets(task, userId, canManageTask(task)).length > 0
}

function canChangeTaskToStatus(task: Task, status: TaskStatus): boolean {
  return canTransitionTaskStatus(
    task,
    status,
    userStore.userInfo?.id,
    canManageTask(task),
  )
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const response = await getTasks(queryParams)
    taskList.value = response.results
    total.value = response.count
  } catch {
    // 请求层统一处理错误。
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
  queryParams.project = undefined
  queryParams.status = undefined
  queryParams.priority = undefined
  queryParams.assignee = undefined
  queryParams.scope = accountDefaultScope
  queryParams.page = 1
  loadData()
}

function restoreTaskSavedFilters(): void {
  const saved = normalizeTaskSavedFilters(
    userStore.preferences?.saved_filters?.tasks,
  )
  queryParams.search = saved.search ?? ''
  queryParams.project = saved.project
  queryParams.status = saved.status
  queryParams.priority = saved.priority
  queryParams.assignee = saved.assignee
  queryParams.scope = saved.scope ?? accountDefaultScope
}

function currentTaskFilterSnapshot() {
  return normalizeTaskSavedFilters({
    search: queryParams.search,
    project: queryParams.project,
    status: queryParams.status,
    priority: queryParams.priority,
    assignee: queryParams.assignee,
    scope: queryParams.scope,
  })
}

async function saveCurrentTaskFilters(): Promise<void> {
  savingFilterPreference.value = true
  try {
    const savedFilters = mergeSavedFilterModule(
      userStore.preferences?.saved_filters,
      'tasks',
      currentTaskFilterSnapshot(),
    )
    await userStore.savePreference({ saved_filters: savedFilters })
    ElMessage.success('已记住当前任务筛选')
  } catch {
    // 请求层统一处理错误。
  } finally {
    savingFilterPreference.value = false
  }
}

async function clearSavedTaskFilters(): Promise<void> {
  savingFilterPreference.value = true
  try {
    const savedFilters = mergeSavedFilterModule(
      userStore.preferences?.saved_filters,
      'tasks',
      null,
    )
    await userStore.savePreference({ saved_filters: savedFilters })
    ElMessage.success('已清除任务筛选偏好')
  } catch {
    // 请求层统一处理错误。
  } finally {
    savingFilterPreference.value = false
  }
}

async function handleFilterPreferenceCommand(
  command: string | number | object,
): Promise<void> {
  if (command === 'save') await saveCurrentTaskFilters()
  if (command === 'clear') await clearSavedTaskFilters()
}

function handleCreate(): void {
  editingTask.value = null
  formDialogVisible.value = true
}

async function handleEdit(row: Task): Promise<void> {
  if (detailLoadingId.value !== null) return
  detailLoadingId.value = row.id
  try {
    const task = await getTask(row.id)
    setEditingTask(task)
    formDialogVisible.value = true
  } catch {
    // 请求层统一处理错误。
  } finally {
    detailLoadingId.value = null
  }
}

function setEditingTask(task: Task): void {
  editingTask.value = {
    id: task.id,
    title: task.title,
    description: task.description || '',
    project: task.project,
    assignee: task.assignee,
    collaborator_ids: task.collaborator_ids || [],
    reviewer: task.reviewer ?? null,
    status: task.status,
    priority: task.priority || 'medium',
    start_date: task.start_date || '',
    deadline: task.deadline || '',
    delay_reason: task.delay_reason || '',
    completion_note: task.completion_note || '',
    attachment_ids: task.attachment_files?.map((file) => file.id) || [],
  }
}

function handleBoardTaskClick(task: Task): void {
  openTaskCollaboration(task)
}

function openTaskCollaboration(task: Task): void {
  router.push({ name: 'TaskCollaboration', params: { id: task.id } })
}

async function handleChangeStatus(task: Task, newStatus: TaskStatus): Promise<void> {
  if (!canChangeTaskToStatus(task, newStatus) || task.status === newStatus) return
  let delayReason: string | undefined
  let completionNote: string | undefined
  if (newStatus === 'overdue') {
    try {
      const result = await ElMessageBox.prompt(
        '进入已逾期状态必须记录延期原因，该说明会保留在任务详情中。',
        '填写延期原因',
        {
          confirmButtonText: '确认延期',
          cancelButtonText: '取消',
          inputPlaceholder: '说明延期原因和新的处理计划',
          inputValidator: (value) => Boolean(value?.trim()) || '请填写延期原因',
        },
      )
      delayReason = result.value.trim()
    } catch {
      return
    }
  }
  if (newStatus === 'pending_review') {
    try {
      const result = await ElMessageBox.prompt(
        '请概述已完成内容、交付物位置和需要审核人关注的事项。',
        '提交任务审核',
        {
          confirmButtonText: '提交审核',
          cancelButtonText: '取消',
          inputPlaceholder: '填写完成说明（可后续补充）',
          inputValue: task.completion_note || '',
        },
      )
      completionNote = result.value.trim()
    } catch {
      return
    }
  }
  const previousStatus = task.status
  task.status = newStatus
  try {
    await changeTaskStatus(task.id, newStatus, delayReason, completionNote)
    ElMessage.success('任务状态已更新')
  } catch {
    task.status = previousStatus
    loadData()
  }
}

async function handleDelete(row: Task): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除任务「${row.title}」吗？`, '删除任务', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteTask(row.id)
    if (taskList.value.length === 1 && (queryParams.page || 1) > 1) {
      queryParams.page = (queryParams.page || 1) - 1
    }
    ElMessage.success('任务已删除')
    loadData()
  } catch {
    // 用户取消或请求层已处理错误。
  }
}

async function handleExport(): Promise<void> {
  if (exporting.value) return
  exporting.value = true
  try {
    const blob = await exportData(
      'tasks',
      'xlsx',
      queryParams.project,
      undefined,
      {
        search: queryParams.search || undefined,
        status: queryParams.status,
        priority: queryParams.priority,
        assignee: queryParams.assignee,
        scope: queryParams.scope,
      },
    )
    downloadBlob(blob, `tasks_filtered_${Date.now()}.xlsx`)
    ElMessage.success('当前任务结果已导出')
  } catch {
    // 请求层统一处理错误。
  } finally {
    exporting.value = false
  }
}

function getInitial(name?: string): string {
  return name?.trim().charAt(0) || '-'
}

function deadlineClass(task: Task): string {
  if (!task.deadline || task.status === 'done' || task.status === 'cancelled') return ''
  const deadline = Date.parse(task.deadline)
  return Number.isFinite(deadline) && deadline < Date.now() ? 'is-overdue' : ''
}

onMounted(async () => {
  restoreTaskSavedFilters()
  const routeProjectId = parsePositiveRouteId(route.query.project_id)
  if (routeProjectId) queryParams.project = routeProjectId

  await Promise.all([loadOptions(), loadData()])
  if (route.query.action === 'create') {
    handleCreate()
    router.replace({ path: '/tasks' })
    return
  }

  const routeTaskId = parsePositiveRouteId(route.query.task_id)
  if (routeTaskId) {
    try {
      const task = await getTask(routeTaskId)
      if (canManageTask(task)) {
        setEditingTask(task)
        formDialogVisible.value = true
      } else {
        openTaskCollaboration(task)
      }
    } catch {
      // 请求层统一处理错误。
    }
  }
})
</script>

<style lang="scss" scoped>
.task-page {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  padding-bottom: max(var(--space-6), env(safe-area-inset-bottom));
}

.task-page :deep(.page-header) {
  margin-bottom: 0;
}

.view-switcher :deep(.el-radio-button__inner) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
}

.task-filter-panel,
.task-workspace {
  min-width: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.task-filter-panel {
  padding: var(--space-3) var(--space-4);
}

.task-filter-form {
  display: grid;
  grid-template-columns:
    minmax(210px, 1.5fr)
    minmax(160px, 1fr)
    minmax(120px, 0.7fr)
    minmax(120px, 0.7fr)
    minmax(150px, 0.9fr)
    minmax(118px, 0.65fr)
    auto;
  align-items: end;
  gap: var(--space-2) var(--space-3);
}

.task-filter-form :deep(.el-form-item) {
  min-width: 0;
  margin-bottom: 0;
}

.task-filter-form :deep(.el-form-item__label) {
  height: 24px;
  padding: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  line-height: 24px;
}

.task-filter-form :deep(.el-select),
.task-filter-form :deep(.el-input) {
  width: 100%;
}

.filter-actions :deep(.el-form-item__content) {
  display: flex;
  flex-wrap: nowrap;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 58px;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.workspace-heading {
  min-width: 0;
}

.workspace-heading h2 {
  color: var(--color-text);
  font-size: var(--font-size-lg);
  font-weight: 600;
  line-height: 1.35;
}

.workspace-heading p {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.result-count {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-variant-numeric: tabular-nums;
}

.table-wrap {
  min-width: 0;
  overflow-x: auto;
}

.dense-task-table {
  width: 100%;
}

.dense-task-table :deep(.el-table__cell) {
  padding-top: 7px;
  padding-bottom: 7px;
}

.dense-task-table :deep(th.el-table__cell) {
  padding-top: 8px;
  padding-bottom: 8px;
  background: var(--bg-table-header);
}

.task-title-cell,
.project-cell,
.assignee-cell,
.deadline-cell,
.row-actions {
  display: flex;
  align-items: center;
  min-width: 0;
}

.task-title-cell {
  gap: var(--space-2);
}

.priority-marker {
  width: 3px;
  height: 30px;
  flex: 0 0 3px;
  background: var(--color-info);
  border-radius: var(--radius-xs);
}

.priority-marker.priority-medium { background: var(--color-primary); }
.priority-marker.priority-high { background: var(--color-warning); }
.priority-marker.priority-urgent { background: var(--color-danger); }

.task-title-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 1px;
}

.task-title-copy strong,
.task-title-copy span,
.project-cell span,
.assignee-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-title-copy strong {
  color: var(--color-text);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.task-title-copy span {
  color: var(--color-text-muted);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.project-cell,
.deadline-cell {
  gap: 6px;
  color: var(--color-text-regular);
  font-size: var(--font-size-xs);
}

.project-cell .el-icon,
.deadline-cell .el-icon {
  flex: 0 0 auto;
  color: var(--color-text-muted);
}

.assignee-cell {
  gap: var(--space-2);
  color: var(--color-text-regular);
  font-size: var(--font-size-xs);
}

.assignee-cell :deep(.el-avatar) {
  flex: 0 0 24px;
  color: var(--color-primary);
  font-size: 11px;
  background: var(--color-primary-soft);
}

.deadline-cell.is-overdue {
  color: var(--color-danger);
  font-weight: 600;
}

.deadline-cell.is-overdue .el-icon {
  color: var(--color-danger);
}

.row-actions {
  justify-content: center;
  gap: 6px;
}

.row-actions :deep(.el-button) {
  width: 28px;
  min-height: 28px;
  height: 28px;
  margin: 0;
}

.board-wrap {
  width: 100%;
  min-width: 0;
  padding: var(--space-3);
  background: var(--color-canvas);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  min-height: 52px;
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--color-border-light);
}

.pagination-wrapper :deep(.el-pagination) {
  padding-top: 0;
}

@media screen and (max-width: 1280px) {
  .task-filter-form {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .filter-keyword {
    grid-column: span 2;
  }
}

@media screen and (max-width: 768px) {
  .task-page {
    gap: var(--space-3);
  }

  .task-filter-panel {
    padding: var(--space-3);
  }

  .task-filter-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-2);
  }

  .filter-keyword,
  .filter-project,
  .filter-assignee,
  .filter-scope,
  .filter-actions {
    grid-column: span 2;
  }

  .filter-actions :deep(.el-form-item__content) {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }

  .filter-preference-dropdown {
    width: 100%;
  }

  .filter-actions :deep(.el-button) {
    width: 100%;
    margin: 0;
  }

  .workspace-header {
    min-height: 54px;
    padding: var(--space-2) var(--space-3);
  }

  .workspace-heading p {
    display: none;
  }

  .board-wrap {
    padding: var(--space-3);
    background: var(--color-surface-subtle);
  }

  .pagination-wrapper {
    justify-content: center;
    min-height: 50px;
    padding-right: var(--space-2);
    padding-left: var(--space-2);
    overflow-x: auto;
  }
}

@media screen and (max-width: 420px) {
  .task-filter-form {
    grid-template-columns: 1fr;
  }

  .filter-keyword,
  .filter-project,
  .filter-assignee,
  .filter-scope,
  .filter-actions {
    grid-column: span 1;
  }
}
</style>
