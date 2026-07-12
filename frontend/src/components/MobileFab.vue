<template>
  <!-- 仅在移动端显示 -->
  <div v-if="isMobile" class="mobile-fab">
    <!-- 展开后的快捷操作列表 -->
    <transition name="fab-list">
      <ul v-show="expanded" class="fab-actions">
        <li
          v-for="action in actions"
          :key="action.key"
          class="fab-action-item"
          role="button"
          tabindex="0"
          :aria-label="action.label"
          @click="handleAction(action)"
          @keydown.enter="handleAction(action)"
        >
          <span class="fab-action-label">{{ action.label }}</span>
          <el-button circle :type="action.type" :icon="action.icon" class="fab-action-btn" />
        </li>
      </ul>
    </transition>

    <!-- 遮罩层（展开时点击空白收起） -->
    <transition name="fab-mask">
      <div v-show="expanded" class="fab-mask" @click="expanded = false" />
    </transition>

    <!-- 主 FAB 按钮 -->
    <el-button
      circle
      type="primary"
      :icon="expanded ? Close : Plus"
      class="fab-main"
      :class="{ 'is-expanded': expanded }"
      aria-label="快捷操作"
      @click="toggleExpand"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 移动端快捷操作 FAB 按钮
 *
 * - 仅在移动端显示（通过 useDevice 判断）
 * - 固定在右下角浮动操作按钮
 * - 点击展开 4 个快捷操作：新建任务、新建项目、扫一扫（预留）、返回顶部
 * - 使用 transition 动画展开/收起
 */
import { ref, onUnmounted, onMounted, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Plus,
  Close,
  EditPen,
  FolderAdd,
  Aim,
  Top,
} from '@element-plus/icons-vue'
import { useDevice } from '@/composables/useDevice'

const { isMobile } = useDevice()
const router = useRouter()

/** 快捷操作项类型 */
interface FabAction {
  key: string
  label: string
  icon: Component
  type: '' | 'primary' | 'success' | 'warning' | 'danger' | 'info'
}

/** 快捷操作列表 */
const actions: FabAction[] = [
  { key: 'newTask', label: '新建任务', icon: EditPen, type: 'primary' },
  { key: 'newProject', label: '新建项目', icon: FolderAdd, type: 'success' },
  { key: 'scan', label: '扫一扫', icon: Aim, type: 'warning' },
  { key: 'backTop', label: '返回顶部', icon: Top, type: 'info' },
]

/** 是否展开 */
const expanded = ref(false)

/** 切换展开/收起 */
function toggleExpand(): void {
  expanded.value = !expanded.value
}

/** 处理快捷操作点击 */
function handleAction(action: FabAction): void {
  expanded.value = false
  switch (action.key) {
    case 'newTask':
      // 跳转任务页并携带创建意图（query 标记）
      router.push({ path: '/tasks', query: { action: 'create' } })
      break
    case 'newProject':
      // 跳转项目页并携带创建意图（query 标记）
      router.push({ path: '/projects', query: { action: 'create' } })
      break
    case 'scan':
      // 扫一扫功能预留
      ElMessage.info('扫一扫功能即将上线')
      break
    case 'backTop':
      scrollToTop()
      break
  }
}

/** 滚动内容区返回顶部 */
function scrollToTop(): void {
  // 优先查找移动端布局的内容滚动容器
  const container =
    document.querySelector('.mobile-content') ||
    document.querySelector('.page-container') ||
    document.querySelector('main')
  if (container) {
    container.scrollTo({ top: 0, behavior: 'smooth' })
  } else {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

/** 点击外部收起 */
function handleOutsideClick(e: MouseEvent): void {
  if (!expanded.value) return
  const target = e.target as Node
  const fabRoot = document.querySelector('.mobile-fab')
  if (fabRoot && !fabRoot.contains(target)) {
    expanded.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick, { capture: true })
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick)
})
</script>

<style lang="scss" scoped>
.mobile-fab {
  position: fixed;
  right: 16px;
  // 留出底部 tabbar 的高度（56px）+ 安全间距
  bottom: 72px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.fab-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  position: relative;
  z-index: 2;
}

.fab-action-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;

  .fab-action-label {
    background: rgba(48, 49, 51, 0.85);
    color: #fff;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 12px;
    white-space: nowrap;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  }

  .fab-action-btn {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
  }
}

.fab-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0);
  z-index: 1;
  pointer-events: auto;
}

.fab-main {
  width: 52px;
  height: 52px;
  font-size: 22px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.45);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  position: relative;
  z-index: 2;

  &.is-expanded {
    transform: rotate(45deg);
  }
}

// 展开列表动画
.fab-list-enter-active,
.fab-list-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.fab-list-enter-from,
.fab-list-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.9);
}

// 遮罩动画
.fab-mask-enter-active,
.fab-mask-leave-active {
  transition: opacity 0.25s ease;
}

.fab-mask-enter-from,
.fab-mask-leave-to {
  opacity: 0;
}

// 无障碍：降低动画
@media (prefers-reduced-motion: reduce) {
  .fab-main,
  .fab-list-enter-active,
  .fab-list-leave-active,
  .fab-mask-enter-active,
  .fab-mask-leave-active {
    transition: none;
  }
}
</style>
