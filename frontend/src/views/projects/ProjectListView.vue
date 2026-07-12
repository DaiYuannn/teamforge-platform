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
          <el-button :icon="RefreshLeft" @click="handleReset">重置筛选</el-button>
          <el-button link type="primary" @click="advancedVisible = !advancedVisible">
            {{ advancedVisible ? '收起' : '高级搜索' }}
            <el-icon class="advanced-arrow" :class="{ 'is-rotate': advancedVisible }">
              <ArrowDown />
            </el-icon>
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 高级搜索（展开/收起） -->
      <el-collapse-transition>
        <div v-show="advancedVisible" class="advanced-search">
          <el-form :inline="true" :model="queryParams" @submit.prevent>
            <el-form-item label="负责人">
              <el-input
                v-model="queryParams.leader"
                placeholder="负责人姓名/ID"
                clearable
                style="width: 180px"
                @keyup.enter="handleSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="queryParams.start_date"
                type="date"
                placeholder="开始日期"
                value-format="YYYY-MM-DD"
                style="width: 160px"
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="queryParams.end_date"
                type="date"
                placeholder="结束日期"
                value-format="YYYY-MM-DD"
                style="width: 160px"
              />
            </el-form-item>
            <el-form-item label="排序">
              <el-select v-model="queryParams.ordering" placeholder="默认排序" clearable style="width: 160px">
                <el-option label="创建时间倒序" value="-created_at" />
                <el-option label="创建时间正序" value="created_at" />
                <el-option label="开始时间倒序" value="-start_date" />
                <el-option label="开始时间正序" value="start_date" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
      </el-collapse-transition>

      <!-- 当前筛选条件标签 -->
      <div v-if="activeFilters.length > 0" class="filter-tags">
        <span class="filter-tags-label">当前筛选：</span>
        <el-tag
          v-for="filter in activeFilters"
          :key="filter.key"
          closable
          size="small"
          class="filter-tag"
          @close="removeFilter(filter.key)"
        >
          {{ filter.label }}：{{ filter.value }}
        </el-tag>
        <el-button link type="primary" size="small" @click="handleReset">清除全部</el-button>
      </div>
    </div>

    <!-- 项目列表表格（PC 端）/ 卡片列表（移动端） -->
    <div class="card mt-16">
      <!-- PC 端：表格 -->
      <el-table
        v-if="!isCardView"
        v-loading="loading"
        :data="projectList"
        border
        stripe
        @row-click="handleRowClick"
      >
        <template #empty>
          <EmptyState
            text="暂无项目"
            description="点击右上角「新建项目」开始创建"
            :illustration="true"
            accent="#409EFF"
          >
            <template #action>
              <el-button
                v-permission="['teacher', 'sys_admin']"
                type="primary"
                :icon="Plus"
                @click="handleCreate"
              >
                新建项目
              </el-button>
            </template>
          </EmptyState>
        </template>
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

      <!-- 移动端：卡片列表 -->
      <div v-else v-loading="loading" class="mobile-card-list">
        <div
          v-for="card in cardData"
          :key="card.raw.id"
          class="mobile-card"
          role="button"
          tabindex="0"
          @click="handleDetail(card.raw)"
          @keydown.enter="handleDetail(card.raw)"
        >
          <div class="mobile-card-header">
            <span class="mobile-card-title">{{ card.title }}</span>
            <span class="mobile-card-code">{{ card.raw.code }}</span>
          </div>
          <div v-if="card.subtitle" class="mobile-card-subtitle">{{ card.subtitle }}</div>
          <div class="mobile-card-fields">
            <div v-for="field in card.fields" :key="field.label" class="mobile-card-field">
              <span class="field-label">{{ field.label }}</span>
              <el-tag
                v-if="field.type === 'tag'"
                size="small"
                :type="(field.tagType as any) || 'info'"
                :color="field.color"
                effect="dark"
              >
                {{ field.value }}
              </el-tag>
              <span v-else class="field-value">{{ field.value }}</span>
            </div>
          </div>
        </div>
        <el-empty v-if="cardData.length === 0 && !loading" description="暂无项目" />
      </div>

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
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, RefreshLeft, ArrowDown, Download } from '@element-plus/icons-vue'
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
import { useMobileList } from '@/composables/useMobileList'
import { useMobileNavigate } from '@/composables/useMobileNavigate'
import type { Project, ProjectFormData } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import ProjectFormDialog from './ProjectFormDialog.vue'

const router = useRouter()
const route = useRoute()
// 移动端智能跳转：列表跳详情（移动端 push，PC 端可新窗口打开）
const { smartNavigate } = useMobileNavigate()

const loading = ref(false)
const projectList = ref<Project[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const editingProject = ref<ProjectFormData | null>(null)

// 移动端列表优化：PC 端表格 / 移动端卡片
const { isCardView, cardData } = useMobileList<Project>(projectList, {
  title: (item) => item.name,
  subtitle: (item) => item.intro || '',
  fields: (item) => [
    {
      label: '负责人',
      value: item.leader_name || '-',
      type: 'text',
    },
    {
      label: '阶段',
      value: item.current_stage_display || getStageLabel(item.current_stage || ''),
      type: 'tag',
      tagType: 'info',
      color: getStageColor(item.current_stage || ''),
    },
    {
      label: '状态',
      value: getProjectStatusLabel(item.status),
      type: 'tag',
      tagType: getProjectStatusTagType(item.status),
    },
    {
      label: '开始日期',
      value: formatDate(item.start_date),
      type: 'date',
    },
    {
      label: '成员数',
      value: item.member_count ?? 0,
      type: 'text',
    },
  ],
})
const advancedVisible = ref(false)

// 查询参数
const queryParams = reactive<ProjectQueryParams>({
  page: 1,
  page_size: 10,
  search: '',
  status: '',
  leader: '',
  start_date: '',
  end_date: '',
  ordering: '',
})

// 当前激活的筛选条件（用于展示 el-tag）
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

// 移除单个筛选条件
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

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    // 仅传递非空参数
    const params: Record<string, any> = { page: queryParams.page, page_size: queryParams.page_size }
    if (queryParams.search) params.search = queryParams.search
    if (queryParams.status) params.status = queryParams.status
    if (queryParams.leader) params.leader = queryParams.leader
    if (queryParams.start_date) params.start_date = queryParams.start_date
    if (queryParams.end_date) params.end_date = queryParams.end_date
    if (queryParams.ordering) params.ordering = queryParams.ordering
    const res = await getProjects(params as ProjectQueryParams)
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
  queryParams.leader = ''
  queryParams.start_date = ''
  queryParams.end_date = ''
  queryParams.ordering = ''
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
  // 移动端 push 跳转详情；PC 端亦 push（如需新窗口可传 openNew=true）
  smartNavigate(`/projects/${row.id}`)
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
  // 处理 FAB / 外部携带的创建意图
  if (route.query.action === 'create') {
    handleCreate()
    // 清理 query，避免刷新重复触发
    router.replace({ path: '/projects' })
  }
})
</script>

<style lang="scss" scoped>
.mt-16 {
  margin-top: 16px;
}

.search-bar {
  padding: 16px;

  .advanced-search {
    margin-top: 12px;
    padding: 12px 16px;
    background: #f5f7fa;
    border-radius: 6px;
    border-left: 3px solid #409eff;
  }

  .advanced-arrow {
    margin-left: 4px;
    transition: transform 0.25s ease;

    &.is-rotate {
      transform: rotate(180deg);
    }
  }

  .filter-tags {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px dashed #ebeef5;

    .filter-tags-label {
      font-size: 13px;
      color: #909399;
    }

    .filter-tag {
      border-radius: 4px;
    }
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ===================== 移动端卡片列表 ===================== */
.mobile-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;

  &:active {
    transform: scale(0.99);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .mobile-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;

    .mobile-card-title {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }

    .mobile-card-code {
      font-size: 12px;
      color: #909399;
      flex-shrink: 0;
    }
  }

  .mobile-card-subtitle {
    font-size: 12px;
    color: #909399;
    margin-bottom: 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .mobile-card-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;

    .mobile-card-field {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;

      .field-label {
        color: #909399;
      }

      .field-value {
        color: #303133;
        font-weight: 500;
      }
    }
  }
}

/* PC 端隐藏移动端卡片样式（仅卡片容器由 v-if 控制，此处无需额外处理） */
@media screen and (min-width: 769px) {
  .mobile-card-list {
    display: none;
  }
}
</style>
