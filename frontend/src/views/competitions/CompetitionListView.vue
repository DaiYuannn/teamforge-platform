<template>
  <div class="page-container">
    <PageHeader title="比赛管理" subtitle="管理所有竞赛信息">
      <template #actions>
        <el-button
          v-permission="['teacher', 'sys_admin']"
          type="primary"
          :icon="Plus"
          @click="handleCreate"
        >
          新建比赛
        </el-button>
      </template>
    </PageHeader>

    <!-- 视图切换 -->
    <div class="card view-switcher">
      <el-radio-group v-model="currentView">
        <el-radio-button value="list">列表视图</el-radio-button>
        <el-radio-button value="matrix">矩阵视图</el-radio-button>
        <el-radio-button value="funnel">漏斗视图</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 列表视图 -->
    <template v-if="currentView === 'list'">
    <!-- 搜索筛选 -->
    <div class="card search-bar mt-16">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="queryParams.search"
            placeholder="比赛名称"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="queryParams.level" placeholder="全部" clearable style="width: 120px">
            <el-option
              v-for="(item, key) in COMPETITION_LEVEL_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 120px">
            <el-option
              v-for="(item, key) in COMPETITION_STATUS_MAP"
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

    <!-- 比赛列表表格 -->
    <div class="card mt-16">
      <el-table v-loading="loading" :data="competitionList" border stripe>
        <template #empty>
          <EmptyState text="暂无比赛" description="点击「新增比赛」开始创建比赛" accent="#9B59B6" />
        </template>
        <el-table-column prop="name" label="比赛名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="级别" width="90">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getCompetitionStageTagType(row.level) as any"
              effect="light"
              :style="getCompetitionStageTagStyle(row.level)"
              class="stage-tag"
            >
              {{ getCompetitionLevelLabel(row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="organizer" label="主办方" width="150" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getCompetitionStatusTagType(row.status) as any" size="small">
              {{ getCompetitionStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="比赛时间" width="200">
          <template #default="{ row }">
            {{ formatDate(row.start_date) }} ~ {{ formatDate(row.end_date) }}
          </template>
        </el-table-column>
        <el-table-column prop="registration_deadline" label="报名截止" width="120">
          <template #default="{ row }">{{ formatDate(row.registration_deadline) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-permission="['teacher', 'sys_admin']" type="warning" link @click="handleEdit(row as Competition)">编辑</el-button>
            <el-button v-permission="['sys_admin']" type="danger" link @click="handleDelete(row as Competition)">删除</el-button>
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
    </template>

    <!-- 矩阵视图 -->
    <CompetitionMatrixView v-else-if="currentView === 'matrix'" />

    <!-- 漏斗视图 -->
    <CompetitionFunnelView v-else-if="currentView === 'funnel'" />

    <!-- 新建/编辑弹窗 -->
    <CompetitionFormDialog
      v-model:visible="formDialogVisible"
      :form-data="editingCompetition"
      @success="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getCompetitions, deleteCompetition, type CompetitionQueryParams } from '@/api/competitions'
import {
  formatDate,
  getCompetitionLevelLabel,
  getCompetitionStageTagType,
  getCompetitionStageTagStyle,
  getCompetitionStatusTagType,
  getCompetitionStatusLabel,
} from '@/utils/format'
import { COMPETITION_LEVEL_MAP, COMPETITION_STATUS_MAP } from '@/utils/constants'
import type { Competition, CompetitionFormData } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import CompetitionFormDialog from './CompetitionFormDialog.vue'
import CompetitionMatrixView from './CompetitionMatrixView.vue'
import CompetitionFunnelView from './CompetitionFunnelView.vue'

/** 当前视图模式：列表 / 矩阵 / 漏斗 */
type ViewMode = 'list' | 'matrix' | 'funnel'
const currentView = ref<ViewMode>('list')

const loading = ref(false)
const competitionList = ref<Competition[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const editingCompetition = ref<CompetitionFormData | null>(null)

const queryParams = reactive<CompetitionQueryParams>({
  page: 1,
  page_size: 10,
  search: '',
  level: '',
  status: '',
})

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res = await getCompetitions(queryParams)
    competitionList.value = res.results
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
  queryParams.search = ''
  queryParams.level = ''
  queryParams.status = ''
  queryParams.page = 1
  loadData()
}

function handleCreate(): void {
  editingCompetition.value = null
  formDialogVisible.value = true
}

function handleEdit(row: Competition): void {
  editingCompetition.value = { ...row }
  formDialogVisible.value = true
}

async function handleDelete(row: Competition): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除比赛「${row.name}」吗？`, '提示', { type: 'warning' })
    await deleteCompetition(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // 取消
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.mt-16 { margin-top: 16px; }
.view-switcher {
  padding: 12px 16px;
  display: flex;
  align-items: center;
}
.search-bar { padding: 16px; }
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
