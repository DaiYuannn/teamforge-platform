<template>
  <div class="page-container">
    <PageHeader title="我的贡献" subtitle="填写和管理项目贡献记录">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="handleCreate">填写贡献</el-button>
        <el-button :icon="Download" @click="handleExport">导出Excel</el-button>
      </template>
    </PageHeader>

    <!-- PC端表格 -->
    <div v-if="!isMobile" class="card mt-16">
      <el-table v-loading="loading" :data="contributionList" border stripe>
        <el-table-column prop="project_name" label="项目" min-width="150" show-overflow-tooltip />
        <el-table-column prop="contribution_type" label="贡献类型" width="120">
          <template #default="{ row }">
            <el-tag :type="CONTRIBUTION_TYPE_MAP[row.contribution_type]?.tagType as any" size="small">
              {{ CONTRIBUTION_TYPE_MAP[row.contribution_type]?.label || row.contribution_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="贡献内容" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="CONTRIBUTION_STATUS_MAP[row.status]?.tagType as any" size="small">
              {{ CONTRIBUTION_STATUS_MAP[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reviewer_name" label="审核人" width="100">
          <template #default="{ row }">{{ row.reviewer_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="reviewed_at" label="审核时间" width="120">
          <template #default="{ row }">{{ formatDate(row.reviewed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" type="warning" link @click="handleEdit(row as any)">编辑</el-button>
            <el-button v-if="row.status === 'pending'" type="danger" link @click="handleDelete(row as any)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 移动端卡片列表 -->
    <div v-else v-loading="loading" class="mobile-list">
      <el-empty v-if="contributionList.length === 0" description="暂无贡献记录" />
      <el-card v-for="item in contributionList" :key="item.id" class="mobile-card" shadow="hover">
        <div class="mobile-card-header">
          <span class="mobile-card-title">{{ item.project_name }}</span>
          <el-tag :type="CONTRIBUTION_STATUS_MAP[item.status]?.tagType as any" size="small">
            {{ CONTRIBUTION_STATUS_MAP[item.status]?.label || item.status }}
          </el-tag>
        </div>
        <div class="mobile-card-body">
          <div class="mobile-card-row">
            <el-tag :type="CONTRIBUTION_TYPE_MAP[item.contribution_type]?.tagType as any" size="small">
              {{ CONTRIBUTION_TYPE_MAP[item.contribution_type]?.label || item.contribution_type }}
            </el-tag>
          </div>
          <div class="mobile-card-row"><span>{{ item.content }}</span></div>
          <div class="mobile-card-row" v-if="item.reviewer_name">
            <span class="label">审核人：</span><span>{{ item.reviewer_name }}</span>
          </div>
        </div>
        <div v-if="item.status === 'pending'" class="mobile-card-actions">
          <el-button type="warning" link size="small" @click="handleEdit(item as any)">编辑</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(item as any)">删除</el-button>
        </div>
      </el-card>
    </div>

    <!-- 填写贡献弹窗 -->
    <ContributionFormDialog
      v-model:visible="formDialogVisible"
      :contribution="editingContribution"
      @success="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download } from '@element-plus/icons-vue'
import { getMyContributions, deleteContribution } from '@/api/contributions'
import { exportData } from '@/api/exports'
import { formatDate } from '@/utils/format'
import { CONTRIBUTION_TYPE_MAP, CONTRIBUTION_STATUS_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import ContributionFormDialog from './ContributionFormDialog.vue'
import type { Contribution } from '@/types'

const { isMobile } = useDevice()

const loading = ref(false)
const contributionList = ref<Contribution[]>([])
const formDialogVisible = ref(false)
const editingContribution = ref<Contribution | null>(null)

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getMyContributions()
    contributionList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 填写贡献
function handleCreate(): void {
  editingContribution.value = null
  formDialogVisible.value = true
}

// 编辑
function handleEdit(row: any): void {
  editingContribution.value = row as Contribution
  formDialogVisible.value = true
}

// 删除
async function handleDelete(row: any): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要删除该贡献记录吗？', '提示', { type: 'warning' })
    await deleteContribution(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // 取消
  }
}

// 导出Excel
async function handleExport(): Promise<void> {
  try {
    const res: any = await exportData('contributions', 'xlsx')
    const blobData = res.data ? res.data : res
    const url = window.URL.createObjectURL(new Blob([blobData]))
    const link = document.createElement('a')
    link.href = url
    link.download = `contributions_xlsx_${Date.now()}.xlsx`
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

/* 移动端样式 */
.mobile-list {
  .mobile-card {
    margin-bottom: 12px;

    .mobile-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;

      .mobile-card-title {
        font-size: 15px;
        font-weight: 600;
        color: #303133;
      }
    }

    .mobile-card-body {
      .mobile-card-row {
        font-size: 13px;
        color: #606266;
        margin-bottom: 4px;

        .label {
          color: #909399;
        }
      }
    }

    .mobile-card-actions {
      margin-top: 8px;
      text-align: right;
    }
  }
}
</style>
