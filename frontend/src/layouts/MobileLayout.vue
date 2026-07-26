<template>
  <div class="mobile-layout">
    <!-- 顶部栏 -->
    <div class="mobile-header">
      <div class="header-title">{{ currentSectionTitle }}</div>
      <div class="header-right">
        <!-- 通知铃铛组件 -->
        <NotificationBell />
        <el-button
          text
          circle
          class="menu-btn"
          aria-label="打开菜单"
          @click="showMenu = true"
        >
          <el-icon size="21"><Menu /></el-icon>
        </el-button>
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
    <div class="mobile-tabbar" role="tablist" aria-label="主导航">
      <div
        v-for="tab in mobilePrimaryNavigation"
        :key="tab.path"
        class="tab-item"
        role="tab"
        tabindex="0"
        :class="{ active: isActive(tab.path) }"
        :aria-selected="isActive(tab.path)"
        @click="switchTab(tab.path)"
        @keydown.enter="switchTab(tab.path)"
      >
        <el-icon :size="21"><component :is="tab.icon" /></el-icon>
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </div>

    <!-- 侧滑菜单（更多功能） -->
    <el-drawer v-model="showMenu" direction="rtl" size="82%" :show-close="false" class="mobile-drawer">
      <template #header>
        <div class="drawer-header" role="button" tabindex="0" @click="goProfile" @keydown.enter="goProfile">
          <AvatarWithName
            :name="userInfo?.name || ''"
            :avatar-url="userInfo?.avatar"
            :size="40"
            :show-name="false"
          />
          <div class="drawer-user-info">
            <div class="drawer-user-name">{{ userInfo?.name || '用户' }}</div>
            <div class="drawer-user-role">{{ roleLabel }}</div>
          </div>
          <el-icon class="drawer-arrow"><ArrowRight /></el-icon>
        </div>
      </template>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="drawerDefaultOpeneds"
        :unique-opened="true"
        class="drawer-menu"
        @select="handleMenuSelect"
      >
        <el-sub-menu
          v-for="group in navigationGroups"
          :key="group.key"
          :index="`group:${group.key}`"
        >
          <template #title>
            <el-icon><component :is="group.icon" /></el-icon>
            <span>{{ group.title }}</span>
          </template>
          <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="logout" class="logout-menu-item">
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
import { ArrowRight } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { getRoleLabel } from '@/utils/format'
import NotificationBell from '@/components/NotificationBell.vue'
import AvatarWithName from '@/components/AvatarWithName.vue'
import {
  findNavigationGroup,
  findNavigationItem,
  getMobilePrimaryNavigation,
  getVisibleNavigationGroups,
} from '@/config/navigation'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showMenu = ref(false)

const userInfo = computed(() => userStore.userInfo)
const roleLabel = computed(() => getRoleLabel(userStore.role))
const navigationGroups = computed(() =>
  getVisibleNavigationGroups(userStore.role, userStore.userInfo?.membership_status),
)
const activeNavigationItem = computed(() => findNavigationItem(route.path, navigationGroups.value))
const activeNavigationGroup = computed(() => findNavigationGroup(route.path, navigationGroups.value))
const activeMenu = computed(() => {
  if (route.path.startsWith('/user/')) return '/user/profile'
  return activeNavigationItem.value?.path || route.path
})
const currentSectionTitle = computed(() => {
  if (route.path.startsWith('/user/')) return '个人工作区'
  return activeNavigationGroup.value?.title || '团队工作区'
})
const drawerDefaultOpeneds = computed(() => [
  `group:${activeNavigationGroup.value?.key || 'workspace'}`,
])
const mobilePrimaryNavigation = computed(() =>
  getMobilePrimaryNavigation(userStore.userInfo?.membership_status),
)

// 判断 Tab 是否激活
function isActive(path: string): boolean {
  if (path === '/dashboard') return route.path.startsWith('/dashboard')
  if (path === '/projects') return route.path.startsWith('/projects')
  if (path === '/user/profile') return route.path.startsWith('/user/')
  return route.path === path
}

// 切换 Tab
function switchTab(path: string): void {
  router.push(path)
}

// 跳转个人中心
function goProfile(): void {
  showMenu.value = false
  router.push('/user/profile')
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
  background: var(--bg-color, #f4f6f5);
}

.mobile-header {
  height: calc(52px + env(safe-area-inset-top));
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: env(safe-area-inset-top) 12px 0 16px;
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-color, #dce3e0);
  position: relative;
  z-index: 10;

  .header-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary, #18221f);
    max-width: calc(100vw - 120px);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .menu-btn {
    width: 38px;
    height: 38px;
    color: var(--text-regular, #52605b);
    border-radius: 6px;

    &:active {
      color: var(--primary-color, #176b73);
      background: var(--primary-lighter, #edf7f6);
    }
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
  scroll-padding-bottom: 16px;
}

.mobile-tabbar {
  height: calc(58px + env(safe-area-inset-bottom));
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--bg-card, #fff);
  border-top: 1px solid var(--border-color, #dce3e0);

  .tab-item {
    flex: 1;
    min-width: 0;
    min-height: 52px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    color: var(--text-secondary, #7b8782);
    cursor: pointer;
    padding: 4px 6px;
    position: relative;
    outline: none;

    &.active {
      color: var(--primary-color, #176b73);
      font-weight: 600;

      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 50%;
        width: 24px;
        height: 2px;
        border-radius: 0 0 2px 2px;
        background: var(--primary-color, #176b73);
        transform: translateX(-50%);
      }
    }

    &:focus-visible {
      box-shadow: inset 0 0 0 2px var(--primary-color, #176b73);
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
  width: 100%;
  cursor: pointer;
  transition: opacity 0.2s ease;

  &:active {
    opacity: 0.7;
  }

  .drawer-user-info {
    flex: 1;
    min-width: 0;

    .drawer-user-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary, #18221f);
    }
    .drawer-user-role {
      font-size: 12px;
      color: var(--text-secondary, #7b8782);
      margin-top: 2px;
    }
  }

  .drawer-arrow {
    color: var(--text-secondary, #7b8782);
    flex-shrink: 0;
  }
}

:deep(.drawer-menu) {
  border-right: 0;
  background: transparent;

  .el-sub-menu__title,
  .el-menu-item {
    min-height: 44px;
    color: var(--text-regular, #52605b);
  }

  .el-sub-menu__title {
    font-weight: 600;
  }

  .el-menu-item.is-active {
    color: var(--primary-color, #176b73);
    background: var(--primary-lighter, #edf7f6);
    box-shadow: inset 3px 0 0 var(--primary-color, #176b73);
  }

  .logout-menu-item {
    margin-top: 8px;
    border-top: 1px solid var(--border-color-light, #e7ecea);
    color: var(--text-secondary, #7b8782);
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

@supports (height: 100dvh) {
  .mobile-layout {
    height: 100dvh;
  }
}
</style>

<style lang="scss">
// el-drawer 传送至 body，安全区和尺寸需使用非 scoped 样式
.mobile-drawer.el-drawer {
  max-width: 360px;
}

.mobile-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: calc(16px + env(safe-area-inset-top)) 16px 14px;
  border-bottom: 1px solid var(--border-color, #dce3e0);
}

.mobile-drawer .el-drawer__body {
  padding: 8px 0 calc(12px + env(safe-area-inset-bottom));
  overscroll-behavior: contain;
}

</style>
