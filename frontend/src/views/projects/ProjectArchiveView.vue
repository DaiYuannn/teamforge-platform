<template>
  <div class="page-container">
    <PageHeader title="项目复盘归档" subtitle="已结项/获奖项目成果检索与展示">
      <template #actions>
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
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
        <el-form-item label="阶段">
          <el-select v-model="queryParams.stage" placeholder="全部" clearable style="width: 140px" @change="handleSearch">
            <el-option label="已获奖" value="awarded" />
            <el-option label="已结项" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="mt-16">
      <el-col :xs="12" :sm="6">
        <div class="stat-card stat-card-blue">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">归档项目总数</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card stat-card-green">
          <div class="stat-value">{{ stats.awarded }}</div>
          <div class="stat-label">获奖项目</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card stat-card-orange">
          <div class="stat-value">{{ stats.closed }}</div>
          <div class="stat-label">已结项项目</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card stat-card-purple">
          <div class="stat-value">{{ stats.totalCompetitions }}</div>
          <div class="stat-label">关联比赛数</div>
        </div>
      </el-col>
    </el-row>

    <!-- 归档项目列表 -->
    <div class="card mt-16">
      <el-table v-loading="loading" :data="archiveList" border stripe>
        <el-table-column prop="code" label="项目编号" width="120" />
        <el-table-column prop="name" label="项目名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="leader_name" label="负责人" width="100" />
        <el-table-column prop="current_stage_display" label="最终阶段" width="100">
          <template #default="{ row }">
            <el-tag :type="row.current_stage === 13 ? 'success' : 'info'" size="small">
              {{ row.current_stage_display || getStageLabel(row.current_stage) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120">
          <template #default="{ row }">{{ formatDate(row.start_date) }}</template>
        </el-table-column>
        <el-table-column prop="actual_end_date" label="结束日期" width="120">
          <template #default="{ row }">{{ formatDate(row.actual_end_date || row.planned_end_date) }}</template>
        </el-table-column>
        <el-table-column prop="intro" label="项目简介" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.intro || row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleViewDetail(row as Project)">查看详情</el-button>
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

    <!-- 项目详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="currentProject?.name || '项目详情'" width="700px">
      <el-descriptions v-if="currentProject" :column="2" border>
        <el-descriptions-item label="项目编号">{{ currentProject.code }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ currentProject.leader_name }}</el-descriptions-item>
        <el-descriptions-item label="最终阶段">{{ currentProject.current_stage_display }}</el-descriptions-item>
        <el-descriptions-item label="开始日期">{{ formatDate(currentProject.start_date) }}</el-descriptions-item>
        <el-descriptions-item label="结束日期">{{ formatDate(currentProject.actual_end_date || currentProject.planned_end_date) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ currentProject.status_display }}</el-descriptions-item>
        <el-descriptions-item label="项目简介" :span="2">{{ currentProject.intro || currentProject.description || '-' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="goToDetail">前往项目详情页</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getProjects, type ProjectQueryParams } from '@/api/projects'
import { formatDate, getStageLabel } from '@/utils/format'
import type { Project } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()
const loading = ref(false)
const archiveList = ref<Project[]>([])
const total = ref(0)
const detailVisible = ref(false)
const currentProject = ref<Project | null>(null)

const queryParams = reactive<ProjectQueryParams & { stage?: string }>({
  page: 1,
  page_size: 10,
  search: '',
  stage: undefined,
})

const stats = computed(() => {
  const awarded = archiveList.value.filter(p => p.current_stage === 13).length
  const closed = archiveList.value.filter(p => p.status === 'closed').length
  return {
    total: total.value,
    awarded,
    closed,
    totalCompetitions: archiveList.value.filter(p => p.competition).length,
  }
})

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const params: any = { ...queryParams, page_size: 999 }
    // 获取已获奖(13)和已结项(14)的项目
    const res = await getProjects(params)
    // 前端过滤归档项目
    let list = res.results
    if (queryParams.stage === 'awarded') {
      list = list.filter(p => p.current_stage === 13)
    } else if (queryParams.stage === 'closed') {
      list = list.filter(p => p.current_stage === 14 || p.status === 'closed')
    } else {
      list = list.filter(p => p.current_stage === 13 || p.current_stage === 14 || p.status === 'closed')
    }
    total.value = list.length
    // 手动分页
    const page = queryParams.page || 1
    const pageSize = queryParams.page_size || 10
    const start = (page - 1) * pageSize
    archiveList.value = list.slice(start, start + pageSize)
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
  if (currentProject.value) {
    detailVisible.value = false
    router.push(`/projects/${currentProject.value.id}`)
  }
}

onMounted(() => {
  loadData()
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
.stat-card {
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  color: #fff;

  .stat-value {
    font-size: 32px;
    font-weight: 700;
  }
  .stat-label {
    font-size: 13px;
    opacity: 0.9;
    margin-top: 4px;
  }
}
.stat-card-blue { background: linear-gradient(135deg, #409EFF, #66b1ff); }
.stat-card-green { background: linear-gradient(135deg, #67C23A, #85ce61); }
.stat-card-orange { background: linear-gradient(135deg, #E6A23C, #ebb563); }
.stat-card-purple { background: linear-gradient(135deg, #9B59B6, #b370cf); }
</style>
