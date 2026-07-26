<template>
  <div class="page-container">
    <PageHeader title="通知中心" subtitle="查看和管理系统通知">
      <template #actions>
        <el-button type="primary" :icon="Check" @click="handleMarkAllRead">全部已读</el-button>
      </template>
    </PageHeader>

    <!-- 筛选栏 -->
    <div class="surface-panel search-bar">
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
      <span class="filter-result">共 {{ total }} 条通知</span>
    </div>

    <!-- PC端表格 -->
    <section v-if="!isMobile" class="surface-panel content-panel">
      <el-table v-loading="loading" :data="notificationList">
        <template #empty>
          <EmptyState text="暂无通知" description="所有消息都已处理完毕" />
        </template>
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="title-cell" :class="{ 'is-unread': !row.is_read }">
              <span class="unread-dot" aria-hidden="true"></span>
              <span :class="{ 'unread-title': !row.is_read }">{{ row.title }}</span>
            </div>
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
        <el-table-column label="操作" width="92" align="right" fixed="right">
          <template #default="{ row }">
            <el-tooltip content="查看通知" placement="top">
              <el-button text :icon="ViewIcon" aria-label="查看通知" @click="handleView(row as any)" />
            </el-tooltip>
            <el-tooltip v-if="!row.is_read" content="标记已读" placement="top">
              <el-button
                text
                type="success"
                :icon="Check"
                aria-label="标记已读"
                @click="handleMarkRead(row as any)"
              />
            </el-tooltip>
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
    </section>

    <!-- 移动端卡片列表 -->
    <section v-else v-loading="loading" class="surface-panel mobile-list">
      <div class="mobile-list-header">
        <span>通知记录</span>
        <span>{{ total }} 条</span>
      </div>
      <EmptyState v-if="notificationList.length === 0" text="暂无通知" description="所有消息都已处理完毕" :compact="true" />
      <article
        v-for="item in notificationList"
        :key="item.id"
        class="mobile-item"
        :class="{ 'is-unread': !item.is_read }"
      >
        <div class="mobile-item-header">
          <span class="unread-dot" aria-hidden="true"></span>
          <h2 class="mobile-item-title" :class="{ 'unread-title': !item.is_read }">{{ item.title }}</h2>
          <el-tag :type="NOTIFICATION_CATEGORY_MAP[item.notification_type || '']?.type as any" size="small">
            {{ NOTIFICATION_CATEGORY_MAP[item.notification_type || '']?.label || item.notification_type }}
          </el-tag>
        </div>
        <p class="mobile-item-content">{{ item.content }}</p>
        <div class="mobile-item-footer">
          <span class="time">{{ formatDateTime(item.created_at) }}</span>
          <div class="mobile-item-actions">
            <el-button text :icon="ViewIcon" size="small" @click="handleView(item as any)">查看</el-button>
            <el-button v-if="!item.is_read" type="success" text :icon="Check" size="small" @click="handleMarkRead(item as any)">已读</el-button>
          </div>
        </div>
      </article>
      <div class="mobile-pagination">
        <el-pagination
          v-model:current-page="queryParams.page"
          :total="total"
          :page-size="queryParams.page_size"
          layout="prev, pager, next"
          size="small"
          background
          @current-change="loadData"
        />
      </div>
    </section>

    <!-- 通知详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="通知详情"
      width="520px"
      :fullscreen="isMobile"
      append-to-body
    >
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
        <el-button v-if="currentRelatedRoute" type="primary" @click="goToRelatedObject">
          查看关联业务
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, View as ViewIcon } from '@element-plus/icons-vue'
import { getNotifications } from '@/api/notifications'
import { formatDateTime } from '@/utils/format'
import { NOTIFICATION_CATEGORY_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Notification } from '@/types'
import { useAppStore } from '@/stores/app'
import { useNotificationStore } from '@/stores/notification'
import { notificationRelatedRoute } from '@/utils/notificationRoute'

const router = useRouter()
const appStore = useAppStore()
const notificationStore = useNotificationStore()

const { isMobile } = useDevice()

const loading = ref(false)
const notificationList = ref<Notification[]>([])
const total = ref(0)
const detailVisible = ref(false)
const currentNotification = ref<Notification | null>(null)
const currentRelatedRoute = computed(() => currentNotification.value
  ? notificationRelatedRoute(currentNotification.value)
  : null)
const readFilter = ref('')

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: appStore.itemsPerPage,
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
    await notificationStore.markAsRead(row.id)
    row.is_read = true
  } catch {
    // 错误已由拦截器处理
  }
}

async function goToRelatedObject(): Promise<void> {
  if (!currentRelatedRoute.value) return
  detailVisible.value = false
  await router.push(currentRelatedRoute.value)
}

// 全部标记已读
async function handleMarkAllRead(): Promise<void> {
  try {
    await notificationStore.markAllAsRead()
    ElMessage.success('已全部标记为已读')
    loadData()
  } catch {
    // 错误已由拦截器处理
  }
}

onMounted(() => {
  loadData()
})

watch(
  () => notificationStore.notifications[0]?.id,
  (latestId, previousId) => {
    if (latestId && latestId !== previousId && queryParams.page === 1) {
      void loadData()
    }
  },
)
</script>

<style lang="scss" scoped>
.search-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 10px 14px;

  :deep(.el-form) {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px 16px;
  }

  :deep(.el-form-item) {
    margin: 0;
  }
}

.filter-result {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--color-text-muted);
}

.content-panel {
  padding: 0;
  margin-top: var(--space-4);
  overflow: hidden;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 0 14px 14px;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.unread-dot {
  display: block;
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  background: transparent;
  border-radius: 50%;
}

.is-unread .unread-dot {
  background: var(--color-danger);
}

.unread-title {
  font-weight: 600;
  color: var(--color-text);
}

.mobile-list {
  padding: 0;
  margin-top: var(--space-4);
  overflow: hidden;

  .mobile-list-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 48px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text);
    border-bottom: 1px solid var(--color-border-light);

    span:last-child {
      font-size: 12px;
      font-weight: 400;
      color: var(--color-text-muted);
    }
  }

  .mobile-item {
    position: relative;
    padding: 13px 12px;
    border-bottom: 1px solid var(--color-border-light);

    &.is-unread {
      background: var(--color-surface-subtle);
    }

    &:last-of-type {
      border-bottom: 0;
    }
  }

  .mobile-item-header {
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .mobile-item-title {
    flex: 1;
    min-width: 0;
    margin: 0;
    overflow: hidden;
    color: var(--color-text-regular);
    font-size: 14px;
    font-weight: 500;
    line-height: 1.45;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-item-content {
    display: -webkit-box;
    margin: 7px 0 8px 14px;
    overflow: hidden;
    color: var(--color-text-regular);
    font-size: 13px;
    line-height: 1.55;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .mobile-item-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding-left: 14px;
  }

  .time {
    font-size: 12px;
    color: var(--color-text-muted);
  }

  .mobile-item-actions {
    display: flex;
    align-items: center;
  }

  .mobile-pagination {
    display: flex;
    justify-content: center;
    padding: 0 6px 12px;
  }
}

@media screen and (max-width: 768px) {
  .search-bar {
    align-items: flex-start;
    flex-direction: column;
    padding: 10px 12px;

    :deep(.el-form) {
      width: 100%;
      align-items: flex-start;
      flex-direction: column;
      gap: 10px;
    }

    :deep(.el-form-item) {
      width: 100%;
      align-items: flex-start;
      flex-direction: column;
    }

    :deep(.el-form-item__content) {
      width: 100%;
    }

    :deep(.el-radio-group) {
      width: 100%;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    :deep(.el-radio-button__inner) {
      width: 100%;
    }

    :deep(.el-select) {
      width: 100% !important;
    }
  }
}
</style>
