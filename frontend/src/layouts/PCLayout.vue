<template>
  <div class="pc-layout">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarCollapsed ? '72px' : '248px'" class="pc-sidebar" aria-label="主导航">
      <div class="logo">
        <div class="logo-icon-wrapper">
          <el-icon size="22"><Monitor /></el-icon>
        </div>
        <span v-show="!sidebarCollapsed" class="logo-text">团队管理平台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="defaultOpeneds"
        :collapse="sidebarCollapsed"
        :collapse-transition="false"
        :unique-opened="true"
        router
        class="sidebar-menu"
      >
        <el-sub-menu
          v-for="group in navigationGroups"
          :key="group.key"
          :index="group.key"
          class="navigation-group"
        >
          <template #title>
            <el-icon><component :is="group.icon" /></el-icon>
            <span>{{ group.title }}</span>
          </template>
          <el-menu-item
            v-for="item in group.items"
            :key="item.path"
            :index="item.path"
            class="sidebar-menu-item"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <!-- 右侧主体 -->
    <el-container class="pc-main">
      <!-- 顶部栏 -->
      <el-header class="pc-header">
        <div class="header-left">
          <el-tooltip :content="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'" placement="bottom">
            <el-button
              text
              circle
              class="collapse-btn"
              :aria-label="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
              @click="toggleSidebar"
            >
              <el-icon size="19">
                <Fold v-if="!sidebarCollapsed" />
                <Expand v-else />
              </el-icon>
            </el-button>
          </el-tooltip>
          <el-breadcrumb separator="/" class="header-breadcrumb">
            <el-breadcrumb-item>{{ currentGroupTitle }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 全局搜索 -->
          <el-input
            v-model="searchQuery"
            placeholder="搜索项目/任务/成员..."
            :prefix-icon="Search"
            class="header-search"
            clearable
            @focus="showSearchDialog = true"
            @keyup.enter="handleGlobalSearch"
          />
          <!-- 通知铃铛组件 -->
          <NotificationBell />
          <!-- 用户信息下拉 -->
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <AvatarWithName
                :name="userInfo?.name || ''"
                :avatar-url="userInfo?.avatar"
                :size="32"
                :show-name="false"
              />
              <span class="user-name">{{ userInfo?.name || '用户' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="pc-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 全局搜索结果对话框 -->
    <el-dialog
      v-model="showSearchDialog"
      title="全局搜索"
      width="700px"
      :close-on-click-modal="true"
      append-to-body
    >
      <el-input
        v-model="searchQuery"
        placeholder="输入关键词搜索..."
        :prefix-icon="Search"
        clearable
        @input="debouncedSearch"
        @keyup.enter="handleGlobalSearch"
        style="margin-bottom: 16px"
      />
      <div v-loading="searching" class="search-results">
        <template v-if="searchResults">
          <div v-if="searchResults.total === 0 && searchQuery" class="search-empty">
            <el-empty description="未找到相关结果" />
          </div>
          <template v-else>
            <div v-if="searchResults.projects.length" class="search-group">
              <h4>项目 ({{ searchResults.projects.length }})</h4>
              <div v-for="item in searchResults.projects" :key="'p'+item.id" class="search-item" @click="goTo(item.url)">
                <el-icon><Folder /></el-icon>
                <span>{{ item.name }}</span>
                <el-tag size="small" :type="item.status === 'active' ? 'success' : 'info'">{{ item.status === 'active' ? '进行中' : '已归档' }}</el-tag>
              </div>
            </div>
            <div v-if="searchResults.tasks.length" class="search-group">
              <h4>任务 ({{ searchResults.tasks.length }})</h4>
              <div v-for="item in searchResults.tasks" :key="'t'+item.id" class="search-item" @click="goTo(item.url)">
                <el-icon><Tickets /></el-icon>
                <span>{{ item.title }}</span>
                <el-tag size="small">{{ item.status_display }}</el-tag>
              </div>
            </div>
            <div v-if="searchResults.members.length" class="search-group">
              <h4>成员 ({{ searchResults.members.length }})</h4>
              <div v-for="item in searchResults.members" :key="'m'+item.id" class="search-item" @click="goTo(item.url)">
                <el-icon><User /></el-icon>
                <span>{{ item.name }}</span>
                <el-tag size="small" type="info">{{ item.global_role_display }}</el-tag>
              </div>
            </div>
            <div v-if="searchResults.files.length" class="search-group">
              <h4>文件 ({{ searchResults.files.length }})</h4>
              <div v-for="item in searchResults.files" :key="'f'+item.id" class="search-item" @click="goTo(item.url)">
                <el-icon><Document /></el-icon>
                <span>{{ item.name }}</span>
                <el-tag size="small" :type="item.level === 'sensitive' ? 'danger' : item.level === 'internal' ? 'warning' : 'success'">{{ item.level_display }}</el-tag>
              </div>
            </div>
            <div v-if="searchResults.competitions.length" class="search-group">
              <h4>比赛 ({{ searchResults.competitions.length }})</h4>
              <div v-for="item in searchResults.competitions" :key="'c'+item.id" class="search-item" @click="goTo(item.url)">
                <el-icon><Trophy /></el-icon>
                <span>{{ item.name }}</span>
              </div>
            </div>
          </template>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Search, Folder, Tickets, User, Document, Trophy, Monitor, Fold, Expand, ArrowDown } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import NotificationBell from '@/components/NotificationBell.vue'
import AvatarWithName from '@/components/AvatarWithName.vue'
import { get } from '@/api/request'
import {
  findNavigationGroup,
  findNavigationItem,
  getVisibleNavigationGroups,
} from '@/config/navigation'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

// 侧边栏折叠状态
const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)
const userInfo = computed(() => userStore.userInfo)

// 切换侧边栏
function toggleSidebar(): void {
  appStore.toggleSidebar()
}

const navigationGroups = computed(() => {
  const groups = getVisibleNavigationGroups(
    userStore.role,
    userStore.userInfo?.membership_status,
  )
  const configuredOrder = userStore.preferences?.sidebar_order || []
  const ordered = [...groups].sort((left, right) => {
    const leftIndex = configuredOrder.indexOf(left.key)
    const rightIndex = configuredOrder.indexOf(right.key)
    if (leftIndex < 0 && rightIndex < 0) return 0
    if (leftIndex < 0) return 1
    if (rightIndex < 0) return -1
    return leftIndex - rightIndex
  })
  const favoritePaths = new Set(userStore.preferences?.favorite_routes || [])
  const favoriteItems = ordered.flatMap((group) => group.items)
    .filter((item, index, list) =>
      favoritePaths.has(item.path) && list.findIndex((candidate) => candidate.path === item.path) === index
    )
  return favoriteItems.length
    ? [{ key: 'favorites', title: '常用入口', icon: 'Star', items: favoriteItems }, ...ordered]
    : ordered
})
const activeNavigationItem = computed(() => findNavigationItem(route.path, navigationGroups.value))
const activeNavigationGroup = computed(() => findNavigationGroup(route.path, navigationGroups.value))

// 详情页沿用所属一级入口的激活态，避免菜单高亮丢失
const activeMenu = computed(() => activeNavigationItem.value?.path || route.path)
const defaultOpeneds = computed(() => [activeNavigationGroup.value?.key || 'workspace'])

// 当前页面标题
const currentTitle = computed(() =>
  (route.meta.title as string) || activeNavigationItem.value?.title || '团队管理平台',
)
const currentGroupTitle = computed(() => activeNavigationGroup.value?.title || '团队工作区')

// 下拉菜单命令处理
async function handleCommand(command: string): Promise<void> {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
      await userStore.logout()
      router.push('/login')
    } catch {
      // 用户取消
    }
  } else if (command === 'profile') {
    // 跳转个人中心
    router.push('/user/profile')
  }
}

// ============ 全局搜索 ============

interface SearchResult {
  projects: Array<{ id: number; name: string; status: string; url: string }>
  tasks: Array<{ id: number; title: string; status_display: string; url: string }>
  members: Array<{ id: number; name: string; global_role_display: string; url: string }>
  files: Array<{ id: number; name: string; level_display: string; level: string; url: string }>
  competitions: Array<{ id: number; name: string; url: string }>
  total: number
  query: string
}

const showSearchDialog = ref(false)
const searchQuery = ref('')
const searching = ref(false)
const searchResults = ref<SearchResult | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null

async function handleGlobalSearch(): Promise<void> {
  if (!searchQuery.value.trim()) {
    searchResults.value = null
    return
  }
  showSearchDialog.value = true
  searching.value = true
  try {
    const res = await get<SearchResult>('/dashboard/search/', { q: searchQuery.value, limit: 5 })
    searchResults.value = res
  } catch {
    // 错误已处理
  } finally {
    searching.value = false
  }
}

function debouncedSearch(): void {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    handleGlobalSearch()
  }, 300)
}

function goTo(url: string): void {
  showSearchDialog.value = false
  if (url.includes('?')) {
    const [path, query] = url.split('?')
    router.push({ path, query: { focus: query.split('=')[1] } })
  } else {
    router.push(url)
  }
}
</script>

<style lang="scss" scoped>
.pc-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

/* ==================== 侧边栏 ==================== */
.pc-sidebar {
  background: var(--bg-card, #fff);
  border-right: 1px solid var(--border-color, #dce3e0);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;

  .logo {
    height: 64px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 10px;
    padding: 0 14px;
    border-bottom: 1px solid var(--border-color-light, #e7ecea);

    .logo-icon-wrapper {
      width: 36px;
      height: 36px;
      flex: 0 0 36px;
      border-radius: 8px;
      color: var(--primary-color, #176b73);
      background: var(--primary-lighter, #edf7f6);
      border: 1px solid rgba(var(--primary-rgb, 23, 107, 115), 0.12);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .logo-text {
      color: var(--text-primary, #18221f);
      font-size: 15px;
      font-weight: 600;
      white-space: nowrap;
    }
  }

  :deep(.sidebar-menu) {
    border-right: none;
    background: transparent;
    font-size: 14px;
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 8px 0;

    &::-webkit-scrollbar {
      width: 4px;
    }
    &::-webkit-scrollbar-track {
      background: transparent;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(24, 34, 31, 0.14);
      border-radius: 2px;
      &:hover {
        background: rgba(24, 34, 31, 0.24);
      }
    }
    scrollbar-width: thin;
    scrollbar-color: rgba(24, 34, 31, 0.14) transparent;
  }

  :deep(.el-sub-menu__title) {
    height: 44px;
    line-height: 44px;
    margin: 2px 8px;
    border-radius: 6px;
    color: var(--text-regular, #52605b);
    font-weight: 600;
    transition: color 0.16s ease, background-color 0.16s ease;

    &:hover {
      color: var(--text-primary, #18221f);
      background: var(--el-fill-color-light, #f2f5f4);
    }
  }

  :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
    color: var(--primary-color, #176b73);
  }

  :deep(.el-menu--inline) {
    background: transparent;
  }

  :deep(.el-menu-item) {
    height: 40px;
    line-height: 40px;
    margin: 1px 8px 1px 18px;
    border-radius: 6px;
    color: var(--text-regular, #52605b);
    transition: color 0.16s ease, background-color 0.16s ease;

    &:hover {
      color: var(--text-primary, #18221f);
      background: var(--el-fill-color-light, #f2f5f4);
    }

    &.is-active {
      color: var(--primary-color, #176b73);
      background: var(--primary-lighter, #edf7f6);
      box-shadow: inset 3px 0 0 var(--primary-color, #176b73);
      font-weight: 600;
    }
  }

  :deep(.el-menu--collapse .el-sub-menu__title) {
    margin-inline: 8px;
    padding: 0 12px !important;
  }
}

/* ==================== 主区域 ==================== */
.pc-main {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  background: var(--bg-color, #f4f6f5);
}

.pc-header {
  height: 64px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-color, #dce3e0);
  padding: 0 20px;
  z-index: 10;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;

    .collapse-btn {
      width: 36px;
      height: 36px;
      color: var(--text-regular, #52605b);
      border-radius: 6px;
      &:hover {
        color: var(--primary-color, #176b73);
        background: var(--primary-lighter, #edf7f6);
      }
    }

    .header-breadcrumb {
      max-width: 34em;
      overflow: hidden;
      white-space: nowrap;

      :deep(.el-breadcrumb__inner) {
        color: var(--text-secondary, #7b8782);
        font-size: 13px;
        font-weight: 400;
      }

      :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
        color: var(--text-primary, #18221f);
        font-weight: 600;
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;

    .header-search {
      width: 252px;
      :deep(.el-input__wrapper) {
        border-radius: 6px;
        background: var(--el-fill-color-extra-light, #f6f8f7);
        box-shadow: 0 0 0 1px transparent inset;
        &:hover {
          box-shadow: 0 0 0 1px var(--border-color, #dce3e0) inset;
        }
        &.is-focus {
          background: #fff;
          box-shadow: 0 0 0 1px var(--primary-color, #176b73) inset;
        }
      }
    }

    .header-icon {
      cursor: pointer;
      color: #606266;
      &:hover {
        color: var(--primary-color, #176b73);
      }
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      transition: background 0.2s;
      &:hover {
        background: var(--el-fill-color-light, #f2f5f4);
      }

      .user-name {
        font-size: 14px;
        color: var(--text-primary, #18221f);
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}

.pc-content {
  background: var(--bg-color, #f4f6f5);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
  width: 100%;
  min-width: 0;
}

@supports (height: 100dvh) {
  .pc-layout {
    height: 100dvh;
  }
}

@media screen and (max-width: 1100px) {
  .pc-header {
    .header-left .header-breadcrumb {
      max-width: 22em;
    }

    .header-right {
      gap: 10px;

      .header-search {
        width: 190px;
      }

      .user-info .user-name {
        display: none;
      }
    }
  }
}

@media screen and (max-width: 920px) {
  .pc-header {
    .header-left .header-breadcrumb {
      max-width: 150px;
    }

    .header-right .header-search {
      display: none;
    }
  }
}

// 路由切换动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// 无障碍：降低动画
@media (prefers-reduced-motion: reduce) {
  .pc-sidebar {
    transition: none;
  }
  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }
}

// 搜索结果样式
.search-results {
  max-height: 500px;
  overflow-y: auto;

  .search-empty {
    padding: 20px 0;
  }

  .search-group {
    margin-bottom: 16px;

    h4 {
      margin: 0 0 8px 0;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }

  .search-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
    font-size: 14px;

    &:hover {
      background: var(--el-fill-color-light);
    }

    .el-icon {
      color: var(--el-color-primary);
    }
  }
}
</style>
