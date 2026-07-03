<template>
  <div class="page-container">
    <PageHeader title="成果与知识产权" subtitle="管理软件著作权、专利、论文等知识产权成果">
      <template #actions>
        <el-button :icon="Download" @click="handleExport">导出Excel</el-button>
        <el-button
          v-permission="['sys_admin', 'teacher']"
          type="primary"
          :icon="Plus"
          @click="handleCreate"
        >
          新建申请
        </el-button>
      </template>
    </PageHeader>

    <!-- 筛选栏 -->
    <div class="card search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="成果类型">
          <el-select v-model="queryParams.ip_type" placeholder="全部" clearable style="width: 160px">
            <el-option
              v-for="(item, key) in IP_TYPE_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 160px">
            <el-option
              v-for="(item, key) in IP_STATUS_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input
            v-model="queryParams.search"
            placeholder="成果名称/编号"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- PC端表格 -->
    <div v-if="!isMobile" class="card mt-16">
      <el-table
        v-loading="loading"
        :data="ipList"
        border
        stripe
        @row-click="handleDetail"
      >
        <el-table-column prop="title" label="成果名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="ip_type" label="类型" width="130">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.ip_type)" size="small">
              {{ IP_TYPE_MAP[row.ip_type]?.label || row.ip_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="related_project_name" label="关联项目" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.related_project_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="当前状态" width="130">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.status)" size="small">
              {{ IP_STATUS_MAP[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="main_writer_name" label="主导撰写人" width="110">
          <template #default="{ row }">{{ row.main_writer_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="applicant_executor_name" label="申请执行人" width="110">
          <template #default="{ row }">{{ row.applicant_executor_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="return_count" label="退回次数" width="90" align="center">
          <template #default="{ row }">
            <el-badge v-if="row.return_count > 0" :value="row.return_count" type="danger" />
            <span v-else>0</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="120">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="handleDetail(row as IPApplicationListItem)">查看详情</el-button>
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

    <!-- 移动端卡片列表 -->
    <div v-else v-loading="loading" class="mobile-list">
      <el-empty v-if="ipList.length === 0" description="暂无数据" />
      <el-card
        v-for="item in ipList"
        :key="item.id"
        class="mobile-card"
        shadow="hover"
        @click="handleDetail(item)"
      >
        <div class="mobile-card-header">
          <span class="mobile-card-title">{{ item.title }}</span>
          <el-tag :type="getStatusColor(item.status)" size="small">
            {{ IP_STATUS_MAP[item.status]?.label || item.status }}
          </el-tag>
        </div>
        <div class="mobile-card-body">
          <div class="mobile-card-row">
            <el-tag :type="getTypeColor(item.ip_type)" size="small">
              {{ IP_TYPE_MAP[item.ip_type]?.label || item.ip_type }}
            </el-tag>
            <span v-if="item.return_count > 0" class="return-badge">
              退回 {{ item.return_count }} 次
            </span>
          </div>
          <div class="mobile-card-row">
            <span class="label">撰写人：</span>
            <span>{{ item.main_writer_name || '-' }}</span>
          </div>
          <div class="mobile-card-row">
            <span class="label">执行人：</span>
            <span>{{ item.applicant_executor_name || '-' }}</span>
          </div>
          <div class="mobile-card-row">
            <span class="label">更新：</span>
            <span>{{ formatDate(item.updated_at) }}</span>
          </div>
        </div>
      </el-card>

      <!-- 移动端分页 -->
      <div class="mobile-pagination">
        <el-pagination
          v-model:current-page="queryParams.page"
          :total="total"
          :page-size="queryParams.page_size"
          layout="prev, pager, next"
          small
          background
          @current-change="loadData"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search, Refresh, Download } from '@element-plus/icons-vue'
import { getIPApplications } from '@/api/intellectualProperty'
import { exportData } from '@/api/exports'
import { formatDate } from '@/utils/format'
import { IP_TYPE_MAP, IP_STATUS_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import type { IPApplicationListItem } from '@/types/intellectualProperty'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()
const { isMobile } = useDevice()

const loading = ref(false)
const ipList = ref<IPApplicationListItem[]>([])
const total = ref(0)

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: 10,
  search: '',
  ip_type: '',
  status: '',
})

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res = await getIPApplications(queryParams) as any
    ipList.value = res.results || []
    total.value = res.count || 0
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
  queryParams.ip_type = ''
  queryParams.status = ''
  queryParams.page = 1
  loadData()
}

// 新建申请
function handleCreate(): void {
  router.push('/intellectual-property/create')
}

// 查看详情
function handleDetail(row: IPApplicationListItem): void {
  router.push(`/intellectual-property/${row.id}`)
}

// 获取类型Tag颜色
function getTypeColor(type: string): any {
  return (IP_TYPE_MAP[type]?.color || '') as any
}

// 获取状态Tag颜色
function getStatusColor(status: string): any {
  return (IP_STATUS_MAP[status]?.color || '') as any
}

// 导出知识产权列表
async function handleExport(): Promise<void> {
  try {
    const res: any = await exportData('intellectual_property', 'xlsx')
    const blobData = res.data ? res.data : res
    const url = window.URL.createObjectURL(new Blob([blobData]))
    const link = document.createElement('a')
    link.href = url
    link.download = `intellectual_property_xlsx_${Date.now()}.xlsx`
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

/* 移动端样式 */
.mobile-list {
  .mobile-card {
    margin-bottom: 12px;
    cursor: pointer;

    .mobile-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;

      .mobile-card-title {
        font-size: 15px;
        font-weight: 600;
        color: #303133;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin-right: 8px;
      }
    }

    .mobile-card-body {
      .mobile-card-row {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        color: #606266;
        margin-bottom: 4px;

        .label {
          color: #909399;
        }

        .return-badge {
          color: #f56c6c;
          font-size: 12px;
          margin-left: 8px;
        }
      }
    }
  }

  .mobile-pagination {
    display: flex;
    justify-content: center;
    margin-top: 16px;
  }
}
</style>
