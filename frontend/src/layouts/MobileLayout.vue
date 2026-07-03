<template>
  <div class="mobile-layout">
    <!-- 顶部栏 -->
    <div class="mobile-header">
      <div class="header-title">{{ currentTitle }}</div>
      <div class="header-right">
        <!-- 通知铃铛组件 -->
        <NotificationBell />
        <el-icon
          class="menu-btn"
          size="22"
          role="button"
          tabindex="0"
          aria-label="打开菜单"
          @click="showMenu = true"
          @keydown.enter="showMenu = true"
        ><Menu /></el-icon>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="mobile-content">
      <router-view v-slot="{ Component }">
        <transition name="slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>

    <!-- 底部 Tab 导航 -->
    <div class="mobile-tabbar">
      <div
        v-for="tab in tabList"
        :key="tab.path"
        class="tab-item"
        role="tab"
        tabindex="0"
        :class="{ active: isActive(tab.path) }"
        :aria-selected="isActive(tab.path)"
        @click="switchTab(tab.path)"
        @keydown.enter="switchTab(tab.path)"
      >
        <el-badge v-if="tab.badge" :value="tab.badge" :max="99">
          <el-icon :size="22"><component :is="tab.icon" /></el-icon>
        </el-badge>
        <el-icon v-else :size="22"><component :is="tab.icon" /></el-icon>
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </div>

    <!-- 侧滑菜单（更多功能） -->
    <el-drawer v-model="showMenu" direction="rtl" size="70%" :show-close="false" class="mobile-drawer">
      <template #header>
        <div class="drawer-header">
          <el-avatar :size="40" :src="userInfo?.avatar" :alt="userInfo?.name || '用户头像'">
            {{ userInfo?.name?.charAt(0) || 'U' }}
          </el-avatar>
          <div class="drawer-user-info">
            <div class="drawer-user-name">{{ userInfo?.name || '用户' }}</div>
            <div class="drawer-user-role">{{ roleLabel }}</div>
          </div>
        </div>
      </template>
      <el-menu :default-active="activeMenu" @select="handleMenuSelect">
        <el-menu-item v-for="item in allMenuList" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
        <el-menu-item index="logout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getRoleLabel } from '@/utils/format'
import NotificationBell from '@/components/NotificationBell.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showMenu = ref(false)

const userInfo = computed(() => userStore.userInfo)
const roleLabel = computed(() => getRoleLabel(userStore.role))
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => (route.meta.title as string) || '团队管理')

// 底部 Tab 列表
const tabList = computed(() => [
  { path: '/dashboard', label: '首页', icon: 'Odometer', badge: 0 },
  { path: '/projects', label: '项目', icon: 'Folder', badge: 0 },
  { path: '/notifications', label: '通知', icon: 'Bell', badge: 0 },
  { path: '/members', label: '我的', icon: 'User', badge: 0 },
])

// 全部菜单列表（侧滑菜单中使用）
const allMenuList = computed(() => {
  const list = [
    { path: '/dashboard', title: '首页驾驶舱', icon: 'Odometer', roles: [] as string[] },
    { path: '/projects', title: '项目管理', icon: 'Folder', roles: [] as string[] },
    { path: '/competitions', title: '比赛管理', icon: 'Trophy', roles: [] as string[] },
    { path: '/tasks', title: '任务管理', icon: 'List', roles: [] as string[] },
    { path: '/members', title: '人员管理', icon: 'User', roles: [] as string[] },
    { path: '/finance', title: '经费管理', icon: 'Money', roles: [] as string[] },
    { path: '/files', title: '文件管理', icon: 'Document', roles: [] as string[] },
    { path: '/imports', title: '导入中心', icon: 'Upload', roles: [] as string[] },
    { path: '/intellectual-property', title: '成果与知识产权', icon: 'Medal', roles: [] as string[] },
    { path: '/intellectual-property/todo', title: '待我处理', icon: 'Bell', roles: [] as string[] },
    { path: '/audit/logs', title: '操作日志', icon: 'Document', roles: ['sys_admin', 'teacher'] as string[] },
    { path: '/contributions', title: '我的贡献', icon: 'Trophy', roles: [] as string[] },
    { path: '/sensitive', title: '敏感资料', icon: 'Lock', roles: [] as string[] },
    { path: '/members/schedule', title: '我的灵活工时', icon: 'Clock', roles: [] as string[] },
    { path: '/members/team-schedule', title: '团队灵活工时', icon: 'DataAnalysis', roles: [] as string[] },
    { path: '/members/skills', title: '技能标签', icon: 'Collection', roles: [] as string[] },
    { path: '/admin/integrations', title: '第三方集成', icon: 'Connection', roles: ['sys_admin'] as string[] },
    { path: '/admin/users', title: '用户管理', icon: 'Setting', roles: ['sys_admin'] as string[] },
  ]
  return list.filter((item) => item.roles.length === 0 || item.roles.includes(userStore.role))
})

// 判断 Tab 是否激活
function isActive(path: string): boolean {
  if (path === '/members' && route.path.startsWith('/members')) return true
  return route.path === path
}

// 切换 Tab
function switchTab(path: string): void {
  router.push(path)
}

// 菜单选择
async function handleMenuSelect(index: string): Promise<void> {
  showMenu.value = false
  if (index === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
      await userStore.logout()
      router.push('/login')
    } catch {
      // 取消
    }
    return
  }
  router.push(index)
}
</script>

<style lang="scss" scoped>
.mobile-layout {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #f5f7fa;
}

.mobile-header {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  position: relative;
  z-index: 10;

  .header-title {
    font-size: 17px;
    font-weight: 600;
    color: #303133;
    max-width: calc(100vw - 120px);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .menu-btn {
    color: #606266;
  }
}

.mobile-content {
  flex: 1;
  width: 100%;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.mobile-tabbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: #fff;
  box-shadow: 0 -1px 4px rgba(0, 0, 0, 0.06);

  .tab-item {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    color: #909399;
    cursor: pointer;
    padding: 4px 6px;

    &.active {
      color: #409eff;
    }

    .tab-label {
      font-size: 11px;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;

  .drawer-user-info {
    .drawer-user-name {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
    .drawer-user-role {
      font-size: 12px;
      color: #909399;
      margin-top: 2px;
    }
  }
}

// 路由切换动画
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.2s ease;
}

.slide-enter-from {
  transform: translateX(100%);
}

.slide-leave-to {
  transform: translateX(-100%);
}

// 无障碍：降低动画
@media (prefers-reduced-motion: reduce) {
  .slide-enter-active,
  .slide-leave-active {
    transition: none;
  }
}
</style>

<style lang="scss">
// 侧滑菜单滚动隔离（el-drawer 传送至 body，需非 scoped 样式）
.mobile-drawer .el-drawer__body {
  overscroll-behavior: contain;
}
</style>
