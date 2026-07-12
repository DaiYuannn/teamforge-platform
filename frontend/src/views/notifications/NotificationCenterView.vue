<template>
  <div class="page-container">
    <PageHeader title="通知中心" subtitle="查看和管理系统通知">
      <template #actions>
        <el-button type="primary" :icon="Check" @click="handleMarkAllRead">全部标记已读</el-button>
      </template>
    </PageHeader>

    <!-- 筛选栏 -->
    <div class="card search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="状态">
          <el-radio-group v-model="readFilter" @change="handleSearch">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="false">未读</el-radio-button>
            <el-radio-button value="true">已读</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="queryParams.category" placeholder="全部分类" clearable style="width: 150px" @change="handleSearch">
            <el-option
              v-for="(item, key) in NOTIFICATION_CATEGORY_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <!-- PC端表格 -->
    <div v-if="!isMobile" class="card mt-16">
      <el-table v-loading="loading" :data="notificationList" border stripe>
        <template #empty>
          <EmptyState text="暂无通知" description="所有消息都已处理完毕" accent="#E6A23C" />
        </template>
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span :class="{ 'unread-title': !row.is_read }">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="内容摘要" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ row.content }}</template>
        </el-table-column>
        <el-table-column prop="notification_type" label="分类" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="NOTIFICATION_CATEGORY_MAP[row.notification_type]?.type as any">
              {{ NOTIFICATION_CATEGORY_MAP[row.notification_type]?.label || row.notification_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="is_read" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_read ? 'info' : 'danger' as any" size="small">
              {{ row.is_read ? '已读' : '未读' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleView(row as any)">查看</el-button>
            <el-button v-if="!row.is_read" type="success" link @click="handleMarkRead(row as any)">标记已读</el-button>
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
      <EmptyState v-if="notificationList.length === 0" text="暂无通知" description="所有消息都已处理完毕" accent="#E6A23C" :compact="true" />
      <el-card v-for="item in notificationList" :key="item.id" class="mobile-card" shadow="hover">
        <div class="mobile-card-header">
          <span class="mobile-card-title" :class="{ 'unread-title': !item.is_read }">{{ item.title }}</span>
          <el-tag :type="NOTIFICATION_CATEGORY_MAP[item.notification_type || '']?.type as any" size="small">
            {{ NOTIFICATION_CATEGORY_MAP[item.notification_type || '']?.label || item.notification_type }}
          </el-tag>
        </div>
        <p class="mobile-card-content">{{ item.content }}</p>
        <div class="mobile-card-footer">
          <span class="time">{{ formatDateTime(item.created_at) }}</span>
          <div>
            <el-button v-if="!item.is_read" type="success" link size="small" @click="handleMarkRead(item as any)">标记已读</el-button>
          </div>
        </div>
      </el-card>
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

    <!-- 通知详情弹窗 -->
    <el-dialog v-model="detailVisible" title="通知详情" width="500px">
      <el-descriptions v-if="currentNotification" :column="1" border>
        <el-descriptions-item label="标题">{{ currentNotification.title }}</el-descriptions-item>
        <el-descriptions-item label="分类">
          <el-tag :type="NOTIFICATION_CATEGORY_MAP[currentNotification.notification_type || '']?.type as any" size="small">
            {{ NOTIFICATION_CATEGORY_MAP[currentNotification.notification_type || '']?.label || currentNotification.notification_type }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatDateTime(currentNotification.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="内容">{{ currentNotification.content }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { getNotifications, markAsRead, markAllAsRead } from '@/api/notifications'
import { formatDateTime } from '@/utils/format'
import { NOTIFICATION_CATEGORY_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Notification } from '@/types'

const { isMobile } = useDevice()

const loading = ref(false)
const notificationList = ref<Notification[]>([])
const total = ref(0)
const detailVisible = ref(false)
const currentNotification = ref<Notification | null>(null)
const readFilter = ref('')

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: 10,
  category: '',
  is_read: '' as string,
})

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const params: any = { ...queryParams }
    if (readFilter.value !== '') {
      params.is_read = readFilter.value === 'true'
    } else {
      delete params.is_read
    }
    if (!params.category) {
      delete params.category
    }
    const res: any = await getNotifications(params)
    notificationList.value = res.results || []
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

// 查看通知
function handleView(row: any): void {
  currentNotification.value = row as Notification
  detailVisible.value = true
  // 如果未读，标记为已读
  if (!row.is_read) {
    handleMarkRead(row)
  }
}

// 标记单条已读
async function handleMarkRead(row: any): Promise<void> {
  try {
    await markAsRead(row.id)
    row.is_read = true
  } catch {
    // 错误已由拦截器处理
  }
}

// 全部标记已读
async function handleMarkAllRead(): Promise<void> {
  try {
    await markAllAsRead()
    ElMessage.success('已全部标记为已读')
    loadData()
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

.unread-title {
  font-weight: 600;
  color: #303133;
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
        color: #606266;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin-right: 8px;
      }
    }

    .mobile-card-content {
      font-size: 13px;
      color: #606266;
      margin: 0 0 8px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .mobile-card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .time {
        font-size: 12px;
        color: #909399;
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
