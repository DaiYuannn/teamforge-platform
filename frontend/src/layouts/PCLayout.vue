<template>
  <div class="pc-layout">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="pc-sidebar">
      <div class="logo">
        <el-icon size="28" color="#409EFF"><Monitor /></el-icon>
        <span v-show="!sidebarCollapsed" class="logo-text">团队管理系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="sidebarCollapsed"
        :collapse-transition="false"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        router
      >
        <template v-for="item in menuList" :key="item.path">
          <!-- 仅管理员可见的用户管理 -->
          <el-menu-item v-if="!item.roles || hasPermission(item.roles)" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
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
          <!-- 通知铃铛组件 -->
          <NotificationBell />
          <!-- 用户信息下拉 -->
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :src="userInfo?.avatar" :alt="userInfo?.name || '用户头像'">
                {{ userInfo?.name?.charAt(0) || 'U' }}
              </el-avatar>
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
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import type { UserRole } from '@/types'
import NotificationBell from '@/components/NotificationBell.vue'

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
  { path: '/members', title: '人员', icon: 'User' },
  { path: '/finance', title: '经费', icon: 'Money' },
  { path: '/files', title: '文件', icon: 'Document' },
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
    // 跳转个人中心（预留）
    router.push('/members')
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

.pc-sidebar {
  background-color: #304156;
  transition: width 0.3s;
  overflow: hidden;
  flex-shrink: 0;

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background-color: #2b3a4d;

    .logo-text {
      color: #fff;
      font-size: 16px;
      font-weight: 600;
      white-space: nowrap;
    }
  }

  :deep(.el-menu) {
    border-right: none;
    font-size: 14px;
  }
}

.pc-main {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
}

.pc-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
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
      &:hover {
        color: #409eff;
      }
    }

    .page-title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      max-width: 28em;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-shrink: 0;

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

      .user-name {
        font-size: 14px;
        color: #303133;
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}

.pc-content {
  background: #f5f7fa;
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
</style>
