<template>
  <div class="page-container">
    <PageHeader title="待我审核" subtitle="审核项目成员提交的贡献记录" />

    <!-- PC端表格 -->
    <div v-if="!isMobile" class="card mt-16">
      <el-table v-loading="loading" :data="pendingList" border stripe>
        <el-table-column prop="project_name" label="项目" min-width="150" show-overflow-tooltip />
        <el-table-column prop="user_name" label="成员" width="100" />
        <el-table-column prop="contribution_type" label="贡献类型" width="120">
          <template #default="{ row }">
            <el-tag :type="CONTRIBUTION_TYPE_MAP[row.contribution_type]?.tagType as any" size="small">
              {{ CONTRIBUTION_TYPE_MAP[row.contribution_type]?.label || row.contribution_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="贡献内容" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="填写时间" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleReview(row as any)">审核</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 移动端卡片列表 -->
    <div v-else v-loading="loading" class="mobile-list">
      <el-empty v-if="pendingList.length === 0" description="暂无待审核贡献" />
      <el-card v-for="item in pendingList" :key="item.id" class="mobile-card" shadow="hover">
        <div class="mobile-card-header">
          <span class="mobile-card-title">{{ item.project_name }}</span>
          <el-tag :type="CONTRIBUTION_TYPE_MAP[item.contribution_type]?.tagType as any" size="small">
            {{ CONTRIBUTION_TYPE_MAP[item.contribution_type]?.label || item.contribution_type }}
          </el-tag>
        </div>
        <div class="mobile-card-body">
          <div class="mobile-card-row"><span class="label">成员：</span><span>{{ item.user_name }}</span></div>
          <div class="mobile-card-row"><span>{{ item.content }}</span></div>
          <div class="mobile-card-row"><span class="label">填写时间：</span><span>{{ formatDate(item.created_at) }}</span></div>
        </div>
        <div class="mobile-card-actions">
          <el-button type="primary" link size="small" @click="handleReview(item as any)">审核</el-button>
        </div>
      </el-card>
    </div>

    <!-- 审核弹窗 -->
    <ContributionReviewDialog
      v-model:visible="reviewDialogVisible"
      :contribution="reviewingContribution"
      @success="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getPendingReview } from '@/api/contributions'
import { formatDate } from '@/utils/format'
import { CONTRIBUTION_TYPE_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import ContributionReviewDialog from './ContributionReviewDialog.vue'
import type { Contribution } from '@/types'

const { isMobile } = useDevice()

const loading = ref(false)
const pendingList = ref<Contribution[]>([])
const reviewDialogVisible = ref(false)
const reviewingContribution = ref<Contribution | null>(null)

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getPendingReview()
    pendingList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 审核
function handleReview(row: any): void {
  reviewingContribution.value = row as Contribution
  reviewDialogVisible.value = true
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
