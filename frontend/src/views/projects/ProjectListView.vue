<template>
  <div class="page-container">
    <PageHeader title="项目管理" subtitle="管理所有竞赛项目">
      <template #actions>
        <el-button :icon="Download" @click="handleExport">导出Excel</el-button>
        <el-button
          v-permission="['teacher', 'sys_admin']"
          type="primary"
          :icon="Plus"
          @click="handleCreate"
        >
          新建项目
        </el-button>
      </template>
    </PageHeader>

    <!-- 搜索筛选 -->
    <div class="card search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="queryParams.search"
            placeholder="项目名称/编号"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 120px">
            <el-option
              v-for="(item, key) in PROJECT_STATUS_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 项目列表表格 -->
    <div class="card mt-16">
      <el-table
        v-loading="loading"
        :data="projectList"
        border
        stripe
        @row-click="handleRowClick"
      >
        <el-table-column prop="code" label="项目编号" width="120" />
        <el-table-column prop="name" label="项目名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="leader_name" label="负责人" width="100" />
        <el-table-column prop="current_stage" label="当前阶段" width="120">
          <template #default="{ row }">
            <el-tag size="small" :color="getStageColor(row.current_stage)" effect="dark">
              {{ row.current_stage_display || getStageLabel(row.current_stage) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getProjectStatusTagType(row.status) as any" size="small">
              {{ getProjectStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120">
          <template #default="{ row }">{{ formatDate(row.start_date) }}</template>
        </el-table-column>
        <el-table-column prop="member_count" label="成员数" width="80" align="center" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="handleDetail(row as Project)">详情</el-button>
            <el-button
              v-permission="['teacher', 'sys_admin']"
              type="warning"
              link
              @click.stop="handleEdit(row as Project)"
            >
              编辑
            </el-button>
            <el-button
              v-permission="['sys_admin']"
              type="danger"
              link
              @click.stop="handleDelete(row as Project)"
            >
              删除
            </el-button>
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

    <!-- 新建/编辑弹窗 -->
    <ProjectFormDialog
      v-model:visible="formDialogVisible"
      :form-data="editingProject"
      @success="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Download } from '@element-plus/icons-vue'
import { getProjects, deleteProject, type ProjectQueryParams } from '@/api/projects'
import { exportData } from '@/api/exports'
import {
  formatDate,
  getStageLabel,
  getStageColor,
  getProjectStatusLabel,
  getProjectStatusTagType,
} from '@/utils/format'
import { PROJECT_STATUS_MAP } from '@/utils/constants'
import type { Project, ProjectFormData } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import ProjectFormDialog from './ProjectFormDialog.vue'

const router = useRouter()

const loading = ref(false)
const projectList = ref<Project[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const editingProject = ref<ProjectFormData | null>(null)

// 查询参数
const queryParams = reactive<ProjectQueryParams>({
  page: 1,
  page_size: 10,
  search: '',
  status: '',
})

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res = await getProjects(queryParams)
    projectList.value = res.results
    total.value = res.count
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
  queryParams.search = ''
  queryParams.status = ''
  queryParams.page = 1
  loadData()
}

// 新建
function handleCreate(): void {
  editingProject.value = null
  formDialogVisible.value = true
}

// 编辑
function handleEdit(row: Project): void {
  editingProject.value = {
    name: row.name,
    code: row.code,
    description: row.intro,
    competition: row.competition,
    leader: row.leader,
    start_date: row.start_date,
    expected_end_date: row.planned_end_date,
    status: row.status,
  }
  formDialogVisible.value = true
}

// 详情
function handleDetail(row: Project): void {
  router.push(`/projects/${row.id}`)
}

// 行点击
function handleRowClick(row: Project): void {
  handleDetail(row)
}

// 删除
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

// 导出项目列表
async function handleExport(): Promise<void> {
  try {
    const res: any = await exportData('projects', 'xlsx')
    const blobData = res.data ? res.data : res
    const url = window.URL.createObjectURL(new Blob([blobData]))
    const link = document.createElement('a')
    link.href = url
    link.download = `projects_xlsx_${Date.now()}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    // 错误已由拦截器处理
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
</style>
