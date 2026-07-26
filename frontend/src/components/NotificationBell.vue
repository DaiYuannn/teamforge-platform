<template>
  <el-popover placement="bottom-end" :width="360" trigger="click" @after-enter="handlePopoverShow">
    <template #reference>
      <el-button text circle class="bell-button" :aria-label="unreadLabel">
        <el-badge :value="unreadCount" :max="99" :hidden="unreadCount === 0" class="bell-badge">
          <el-icon size="19"><Bell /></el-icon>
        </el-badge>
      </el-button>
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
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { formatRelativeTime } from '@/utils/format'
import type { Notification } from '@/types'
import { useNotificationStore } from '@/stores/notification'
import { notificationRelatedRoute } from '@/utils/notificationRoute'

const router = useRouter()
const notificationStore = useNotificationStore()
const { unreadCount, recentNotifications: recentList } = storeToRefs(notificationStore)

const loading = ref(false)
const unreadLabel = computed(() => unreadCount.value ? `通知，${unreadCount.value} 条未读` : '通知')

async function refreshNotifications(): Promise<void> {
  loading.value = true
  try {
    await notificationStore.hydrate()
  } catch {
    // 静默失败
  } finally {
    loading.value = false
  }
}

function handlePopoverShow(): void {
  void refreshNotifications()
}

// 点击单条通知
async function handleClickItem(item: Notification): Promise<void> {
  if (!item.is_read) {
    try {
      await notificationStore.markAsRead(item.id)
    } catch {
      // 静默
    }
  }
  await router.push(notificationRelatedRoute(item) || '/notifications')
}

// 全部标记已读
async function handleMarkAllRead(): Promise<void> {
  try {
    await notificationStore.markAllAsRead()
  } catch {
    // 静默
  }
}

// 跳转通知中心
function goToCenter(): void {
  router.push('/notifications')
}

onMounted(() => {
  void refreshNotifications().finally(() => notificationStore.startStream())
})

onUnmounted(() => {
  notificationStore.stopStream()
})
</script>

<style lang="scss" scoped>
.bell-badge {
  display: inline-flex;
  align-items: center;
}

.bell-button {
  width: 36px;
  height: 36px;
  color: var(--color-text-regular);

  &:hover,
  &:focus-visible {
    color: var(--color-primary);
    background: var(--color-primary-soft);
  }
}

.bell-panel {
  .bell-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--color-border-light);

    .bell-panel-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--color-text);
    }
  }

  .bell-panel-list {
    max-height: 360px;
    overflow-y: auto;

    .bell-empty {
      text-align: center;
      color: var(--color-text-muted);
      font-size: 13px;
      padding: 32px 0;
    }
  }

  .bell-item {
    padding: 10px 4px;
    border-bottom: 1px solid var(--color-border-light);
    cursor: pointer;

    &:hover {
      background: var(--color-surface-subtle);
    }

    &.unread {
      .bell-item-title {
        font-weight: 600;
        color: var(--color-text);
      }
    }

    .bell-item-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;

      .bell-item-title {
        font-size: 13px;
        color: var(--color-text-regular);
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin-right: 8px;
      }
    }

    .bell-item-content {
      font-size: 12px;
      color: var(--color-text-muted);
      margin: 0 0 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .bell-item-time {
      font-size: 11px;
      color: var(--color-text-muted);
    }
  }

  .bell-panel-footer {
    text-align: center;
    padding-top: 8px;
    border-top: 1px solid var(--color-border-light);
  }
}
</style>
