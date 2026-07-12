<template>
  <el-popover placement="bottom-end" :width="360" trigger="click" @show="handlePopoverShow">
    <template #reference>
      <el-badge :value="unreadCount" :max="99" :hidden="unreadCount === 0" class="bell-badge">
        <el-icon size="20" class="bell-icon"><Bell /></el-icon>
      </el-badge>
    </template>

    <!-- 下拉面板 -->
    <div class="bell-panel">
      <div class="bell-panel-header">
        <span class="bell-panel-title">通知</span>
        <el-button v-if="unreadCount > 0" type="primary" link size="small" @click="handleMarkAllRead">全部已读</el-button>
      </div>
      <div v-loading="loading" class="bell-panel-list">
        <div v-if="recentList.length === 0" class="bell-empty">暂无通知</div>
        <div
          v-for="item in recentList"
          :key="item.id"
          class="bell-item"
          :class="{ unread: !item.is_read }"
          @click="handleClickItem(item)"
        >
          <div class="bell-item-header">
            <span class="bell-item-title">{{ item.title }}</span>
            <el-tag v-if="!item.is_read" type="danger" size="small">未读</el-tag>
          </div>
          <p class="bell-item-content">{{ item.content }}</p>
          <span class="bell-item-time">{{ formatRelativeTime(item.created_at) }}</span>
        </div>
      </div>
      <div class="bell-panel-footer">
        <el-button type="primary" link @click="goToCenter">查看全部</el-button>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { getUnreadCount, getNotifications, markAsRead, markAllAsRead } from '@/api/notifications'
import { formatRelativeTime } from '@/utils/format'
import type { Notification } from '@/types'

const router = useRouter()

const unreadCount = ref(0)
const loading = ref(false)
const recentList = ref<Notification[]>([])
let timer: ReturnType<typeof setInterval> | null = null

// 获取未读数量
async function loadUnreadCount(): Promise<void> {
  try {
    const res: any = await getUnreadCount()
    unreadCount.value = res.count ?? 0
  } catch {
    // 静默失败
  }
}

// 加载最近5条通知
async function loadRecent(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getNotifications({ page: 1, page_size: 5 })
    recentList.value = res.results || []
  } catch {
    // 静默失败
  } finally {
    loading.value = false
  }
}

// 弹出面板展开时：刷新最近通知并同步未读数（需求H：保证实时性）
function handlePopoverShow(): void {
  loadRecent()
  loadUnreadCount()
}

// 点击单条通知
async function handleClickItem(item: Notification): Promise<void> {
  if (!item.is_read) {
    try {
      await markAsRead(item.id)
      item.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch {
      // 静默
    }
  }
  goToCenter()
}

// 全部标记已读
async function handleMarkAllRead(): Promise<void> {
  try {
    await markAllAsRead()
    unreadCount.value = 0
    recentList.value.forEach((n) => (n.is_read = true))
  } catch {
    // 静默
  }
}

// 跳转通知中心
function goToCenter(): void {
  router.push('/notifications')
}

onMounted(() => {
  loadUnreadCount()
  // 每30秒轮询一次未读数量
  timer = setInterval(loadUnreadCount, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
.bell-badge {
  display: inline-flex;
  align-items: center;
}

.bell-icon {
  cursor: pointer;
  color: #606266;
  &:hover {
    color: #409eff;
  }
}

.bell-panel {
  .bell-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 8px;
    border-bottom: 1px solid #ebeef5;

    .bell-panel-title {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
    }
  }

  .bell-panel-list {
    max-height: 360px;
    overflow-y: auto;

    .bell-empty {
      text-align: center;
      color: #909399;
      font-size: 13px;
      padding: 32px 0;
    }
  }

  .bell-item {
    padding: 10px 4px;
    border-bottom: 1px solid #f0f2f5;
    cursor: pointer;

    &:hover {
      background: #f5f7fa;
    }

    &.unread {
      .bell-item-title {
        font-weight: 600;
        color: #303133;
      }
    }

    .bell-item-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;

      .bell-item-title {
        font-size: 13px;
        color: #606266;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin-right: 8px;
      }
    }

    .bell-item-content {
      font-size: 12px;
      color: #909399;
      margin: 0 0 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .bell-item-time {
      font-size: 11px;
      color: #c0c4cc;
    }
  }

  .bell-panel-footer {
    text-align: center;
    padding-top: 8px;
    border-top: 1px solid #ebeef5;
  }
}
</style>
