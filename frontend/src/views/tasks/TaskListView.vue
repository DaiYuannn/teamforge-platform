<template>
  <div class="page-container">
    <PageHeader title="任务管理" subtitle="管理所有项目任务">
      <template #actions>
        <!-- 视图切换：表格 / 看板 -->
        <el-button-group class="view-toggle">
          <el-button :type="viewMode === 'table' ? 'primary' : 'default'" @click="viewMode = 'table'">
            <el-icon><Grid /></el-icon>
            <span>表格</span>
          </el-button>
          <el-button :type="viewMode === 'board' ? 'primary' : 'default'" @click="viewMode = 'board'">
            <el-icon><Operation /></el-icon>
            <span>看板</span>
          </el-button>
        </el-button-group>
        <el-button
          v-permission="['teacher', 'sys_admin']"
          type="primary"
          :icon="Plus"
          @click="handleCreate"
        >
          新建任务
        </el-button>
      </template>
    </PageHeader>

    <!-- 搜索筛选 -->
    <div class="card search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="项目">
          <el-select v-model="queryParams.project" placeholder="全部项目" clearable style="width: 180px">
            <el-option
              v-for="p in projectOptions"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 120px">
            <el-option
              v-for="(item, key) in TASK_STATUS_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="queryParams.priority" placeholder="全部" clearable style="width: 120px">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="queryParams.assignee" placeholder="负责人ID" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 任务列表：表格（PC 默认）/ 看板（移动端默认，支持横向滑动） -->
    <div class="card mt-16">
      <!-- 表格视图 -->
      <el-table v-if="viewMode === 'table'" v-loading="loading" :data="taskList" border stripe>
        <template #empty>
          <EmptyState text="暂无任务" description="点击「新建任务」开始创建" accent="#67C23A" />
        </template>
        <el-table-column prop="title" label="任务标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="project_name" label="所属项目" width="150" show-overflow-tooltip />
        <el-table-column prop="assignee_name" label="负责人" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getTaskStatusTagType(row.status) as any" size="small">
              {{ getTaskStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="90">
          <template #default="{ row }">
            <el-tag
              :type="row.priority === 'urgent' ? 'danger' : row.priority === 'high' ? 'warning' : row.priority === 'low' ? 'info' : 'primary'"
              size="small"
            >
              {{ row.priority_display || ({ low: '低', medium: '中', high: '高', urgent: '紧急' } as Record<string, string>)[row.priority] || '中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止日期" width="120">
          <template #default="{ row }">{{ formatDate(row.deadline) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-permission="['teacher', 'sys_admin']" type="warning" link @click="handleEdit(row as Task)">编辑</el-button>
            <el-button v-permission="['teacher', 'sys_admin']" type="danger" link @click="handleDelete(row as Task)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 看板视图（移动端为横向滑动卡片） -->
      <TaskBoard
        v-else
        :tasks="taskList"
        @change-status="handleChangeStatus"
        @task-click="handleEdit"
      />

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

    <!-- 新建/编辑弹窗 -->
    <TaskFormDialog
      v-model:visible="formDialogVisible"
      :form-data="editingTask"
      :projects="projectOptions"
      @success="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Grid, Operation } from '@element-plus/icons-vue'
import { getTasks, deleteTask, changeTaskStatus, type TaskQueryParams } from '@/api/tasks'
import { getProjects } from '@/api/projects'
import {
  formatDate,
  getTaskStatusLabel,
  getTaskStatusTagType,
} from '@/utils/format'
import { TASK_STATUS_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import type { Task, TaskStatus, TaskFormData, Project } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import TaskBoard from '@/components/TaskBoard.vue'
import TaskFormDialog from './TaskFormDialog.vue'

const route = useRoute()
const router = useRouter()
const { isMobile } = useDevice()

const loading = ref(false)
const taskList = ref<Task[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const editingTask = ref<TaskFormData | null>(null)
const projectOptions = ref<Project[]>([])

// 视图模式：移动端默认看板（横向滑动卡片），PC 端默认表格
const viewMode = ref<'table' | 'board'>(isMobile.value ? 'board' : 'table')

const queryParams = reactive<TaskQueryParams>({
  page: 1,
  page_size: 10,
  project: undefined,
  status: undefined,
  priority: undefined,
  assignee: undefined,
})

// 加载项目选项
async function loadProjects(): Promise<void> {
  try {
    const res = await getProjects({ page: 1, page_size: 999 })
    projectOptions.value = res.results
  } catch {
    // 忽略
  }
}

// 加载任务
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res = await getTasks(queryParams)
    taskList.value = res.results
    total.value = res.count
  } catch {
    // 已处理
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  queryParams.page = 1
  loadData()
}

function handleReset(): void {
  queryParams.project = undefined
  queryParams.status = undefined
  queryParams.priority = undefined
  queryParams.assignee = undefined
  queryParams.page = 1
  loadData()
}

function handleCreate(): void {
  editingTask.value = null
  formDialogVisible.value = true
}

function handleEdit(row: Task): void {
  editingTask.value = {
    title: row.title,
    description: row.description,
    project: row.project,
    assignee: row.assignee,
    status: row.status,
    deadline: row.deadline,
  }
  formDialogVisible.value = true
}

/**
 * 处理任务状态切换（看板拖拽 / 移动端滑动 / 按钮组触发）
 */
async function handleChangeStatus(task: Task, newStatus: TaskStatus): Promise<void> {
  if (task.status === newStatus) return
  try {
    await changeTaskStatus(task.id, newStatus)
    // 本地更新状态
    task.status = newStatus
    ElMessage.success('状态已更新')
  } catch {
    // 失败时重新加载以保证数据一致
    loadData()
  }
}

async function handleDelete(row: Task): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除任务「${row.title}」吗？`, '提示', { type: 'warning' })
    await deleteTask(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // 取消
  }
}

onMounted(() => {
  loadProjects()
  loadData()
  // 处理 FAB / 外部携带的创建意图
  if (route.query.action === 'create') {
    handleCreate()
    // 清理 query，避免刷新重复触发
    router.replace({ path: '/tasks' })
  }
})
</script>

<style lang="scss" scoped>
.mt-16 { margin-top: 16px; }
.search-bar { padding: 16px; }
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
