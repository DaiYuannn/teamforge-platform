<template>
  <div class="pc-layout">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="pc-sidebar">
      <div class="logo">
        <div class="logo-icon-wrapper">
          <el-icon size="24" color="#60e8ff"><Monitor /></el-icon>
        </div>
        <span v-show="!sidebarCollapsed" class="logo-text">团队管理系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="sidebarCollapsed"
        :collapse-transition="false"
        background-color="transparent"
        text-color="#8a9bb4"
        active-text-color="#60e8ff"
        router
        class="sidebar-menu"
      >
        <template v-for="item in menuList" :key="item.path">
          <el-menu-item v-if="!item.roles || hasPermission(item.roles)" :index="item.path" class="sidebar-menu-item">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
      <div v-show="!sidebarCollapsed" class="sidebar-footer">
        <div class="sidebar-version">v1.0.0</div>
      </div>
    </el-aside>

    <!-- 右侧主体 -->
    <el-container class="pc-main">
      <!-- 顶部栏 -->
      <el-header class="pc-header">
        <div class="header-left">
          <el-icon
            class="collapse-btn"
            @click="toggleSidebar"
            size="20"
            role="button"
            tabindex="0"
            :aria-label="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
            @keydown.enter="toggleSidebar"
          >
            <Fold v-if="!sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
          <span class="page-title">{{ currentTitle }}</span>
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
import type { UserRole } from '@/types'
import NotificationBell from '@/components/NotificationBell.vue'
import AvatarWithName from '@/components/AvatarWithName.vue'
import { get } from '@/api/request'

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

// 当前激活的菜单
const activeMenu = computed(() => route.path)

// 当前页面标题
const currentTitle = computed(() => (route.meta.title as string) || '团队管理系统')

// 侧边栏菜单列表
const menuList = computed(() => [
  { path: '/dashboard', title: '首页', icon: 'Odometer' },
  { path: '/projects', title: '项目', icon: 'Folder' },
  { path: '/competitions', title: '比赛', icon: 'Trophy' },
  { path: '/tasks', title: '任务', icon: 'List' },
  { path: '/todo', title: '待办事项', icon: 'Checked' },
  { path: '/members', title: '人员', icon: 'User' },
  { path: '/finance', title: '经费', icon: 'Money' },
  { path: '/files', title: '文件', icon: 'Document' },
  { path: '/announcements', title: '公告', icon: 'Notification' },
  { path: '/activities', title: '动态', icon: 'ChatLineSquare' },
  { path: '/imports', title: '导入中心', icon: 'Upload' },
  { path: '/intellectual-property', title: '成果与知识产权', icon: 'Medal' },
  { path: '/intellectual-property/todo', title: '待我处理', icon: 'Bell' },
  { path: '/audit/logs', title: '操作日志', icon: 'Document', roles: ['sys_admin', 'teacher'] as UserRole[] },
  { path: '/notifications', title: '通知中心', icon: 'Bell' },
  { path: '/contributions', title: '我的贡献', icon: 'Trophy' },
  { path: '/sensitive', title: '敏感资料', icon: 'Lock' },
  { path: '/members/schedule', title: '我的灵活工时', icon: 'Clock' },
  { path: '/members/team-schedule', title: '团队灵活工时', icon: 'DataAnalysis' },
  { path: '/members/skills', title: '技能标签', icon: 'Collection' },
  { path: '/admin/integrations', title: '第三方集成', icon: 'Connection', roles: ['sys_admin'] as UserRole[] },
  { path: '/admin/users', title: '用户管理', icon: 'Setting', roles: ['sys_admin'] as UserRole[] },
])

// 检查权限
function hasPermission(roles: string[]): boolean {
  return roles.includes(userStore.role)
}

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
  background: linear-gradient(180deg, #1a2332 0%, #0f1925 100%);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background:
      radial-gradient(ellipse at top, rgba(96, 232, 255, 0.04) 0%, transparent 50%),
      linear-gradient(180deg, transparent 0%, rgba(96, 232, 255, 0.02) 100%);
    pointer-events: none;
  }

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: rgba(0, 0, 0, 0.3);
    border-bottom: 1px solid rgba(96, 232, 255, 0.08);
    position: relative;
    z-index: 1;

    .logo-icon-wrapper {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: linear-gradient(135deg, rgba(96, 232, 255, 0.15), rgba(64, 158, 255, 0.1));
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 12px rgba(96, 232, 255, 0.2);
    }

    .logo-text {
      color: #e8f4ff;
      font-size: 15px;
      font-weight: 600;
      white-space: nowrap;
      letter-spacing: 0.5px;
    }
  }

  :deep(.el-menu) {
    border-right: none;
    font-size: 14px;
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 8px 0;
    position: relative;
    z-index: 1;

    &::-webkit-scrollbar {
      width: 4px;
    }
    &::-webkit-scrollbar-track {
      background: transparent;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(96, 232, 255, 0.15);
      border-radius: 2px;
      &:hover {
        background: rgba(96, 232, 255, 0.3);
      }
    }
    * {
      scrollbar-width: thin;
      scrollbar-color: rgba(96, 232, 255, 0.15) transparent;
    }
  }

  :deep(.el-menu-item) {
    height: 44px;
    line-height: 44px;
    margin: 2px 8px;
    border-radius: 8px;
    transition: all 0.2s ease;
    position: relative;

    &:hover {
      background: rgba(96, 232, 255, 0.08) !important;
      color: #b0d4f1 !important;
    }

    &.is-active {
      background: linear-gradient(90deg, rgba(96, 232, 255, 0.15), rgba(96, 232, 255, 0.05)) !important;
      color: #60e8ff !important;
      box-shadow: inset 3px 0 0 #60e8ff;

      .el-icon {
        color: #60e8ff;
        filter: drop-shadow(0 0 4px rgba(96, 232, 255, 0.4));
      }
    }
  }

  .sidebar-footer {
    padding: 8px 16px;
    border-top: 1px solid rgba(96, 232, 255, 0.06);
    position: relative;
    z-index: 1;

    .sidebar-version {
      font-size: 11px;
      color: rgba(138, 155, 180, 0.5);
      text-align: center;
      letter-spacing: 0.5px;
    }
  }
}

/* ==================== 主区域 ==================== */
.pc-main {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  background: #f0f2f5;
}

.pc-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06), 0 0 0 1px rgba(0, 0, 0, 0.02);
  padding: 0 20px;
  z-index: 10;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;

    .collapse-btn {
      cursor: pointer;
      color: #606266;
      padding: 6px;
      border-radius: 6px;
      transition: all 0.2s;
      &:hover {
        color: #409eff;
        background: rgba(64, 158, 255, 0.08);
      }
    }

    .page-title {
      font-size: 16px;
      font-weight: 600;
      color: #1d2129;
      max-width: 28em;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;

    .header-search {
      width: 240px;
      :deep(.el-input__wrapper) {
        border-radius: 8px;
        transition: all 0.2s;
        &:hover {
          box-shadow: 0 0 0 1px #c0c4cc inset;
        }
        &.is-focus {
          box-shadow: 0 0 0 1px #409eff inset, 0 0 8px rgba(64, 158, 255, 0.15);
        }
      }
    }

    .header-icon {
      cursor: pointer;
      color: #606266;
      &:hover {
        color: #409eff;
      }
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 8px;
      transition: background 0.2s;
      &:hover {
        background: rgba(64, 158, 255, 0.06);
      }

      .user-name {
        font-size: 14px;
        color: #1d2129;
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}

.pc-content {
  background: #f0f2f5;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
  width: 100%;
  min-width: 0;
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
