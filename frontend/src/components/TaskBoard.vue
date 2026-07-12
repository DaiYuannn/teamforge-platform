<template>
  <div class="task-board">
    <!-- ===================== PC 端：多列看板 ===================== -->
    <div v-if="!isMobile" class="board-columns">
      <div
        v-for="col in columns"
        :key="col.value"
        class="board-column"
        @dragover.prevent="onDragOver(col.value)"
        @dragleave="onDragLeave"
        @drop="onDrop(col.value)"
      >
        <!-- 列头 -->
        <div class="column-header" :style="{ borderTopColor: col.color }">
          <span class="column-title">{{ col.label }}</span>
          <el-badge :value="getTasksByStatus(col.value).length" type="info" />
        </div>

        <!-- 任务卡片列表 -->
        <div class="column-body">
          <div
            v-for="task in getTasksByStatus(col.value)"
            :key="task.id"
            class="task-card"
            draggable="true"
            @dragstart="onDragStart(task)"
            @click="$emit('taskClick', task)"
          >
            <div class="task-title">{{ task.title }}</div>
            <div class="task-meta">
              <el-tag size="small" :type="getTaskPriorityTagType(task.priority || '') as any">
                {{ getTaskPriorityLabel(task.priority || '') }}
              </el-tag>
              <span class="task-assignee">
                <el-avatar :size="20" :src="task.assignee_avatar">
                  {{ task.assignee_name?.charAt(0) }}
                </el-avatar>
                {{ task.assignee_name }}
              </span>
            </div>
            <div class="task-date">
              <el-icon><Calendar /></el-icon>
              {{ formatDate(task.deadline) }}
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="getTasksByStatus(col.value).length === 0" class="empty-column">
            暂无任务
          </div>
        </div>
      </div>
    </div>

    <!-- ===================== 移动端：横向滑动卡片视图 ===================== -->
    <div v-else class="mobile-board">
      <div v-if="tasks.length === 0" class="mobile-empty">暂无任务</div>
      <div v-else class="mobile-card-list">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="mobile-task-wrapper"
        >
          <!-- 状态切换提示（左/右） -->
          <div class="swipe-hint swipe-hint-left">
            <el-icon><ArrowLeft /></el-icon>
            <span>{{ prevStatusLabel(task.status) }}</span>
          </div>
          <div class="swipe-hint swipe-hint-right">
            <span>{{ nextStatusLabel(task.status) }}</span>
            <el-icon><ArrowRight /></el-icon>
          </div>

          <!-- 可滑动卡片 -->
          <div
            class="mobile-task-card"
            :class="{
              'is-swiping': swipe.taskId === task.id,
              'swipe-right': swipe.taskId === task.id && swipe.offsetX > 0,
              'swipe-left': swipe.taskId === task.id && swipe.offsetX < 0,
            }"
            :style="cardStyle(task.id)"
            @touchstart.passive="onTouchStart($event, task)"
            @touchmove.passive="onTouchMove($event, task)"
            @touchend.passive="onTouchEnd($event, task)"
            @click="onCardClick(task)"
          >
            <div class="mobile-card-header">
              <span class="mobile-task-title">{{ task.title }}</span>
              <el-tag
                size="small"
                :type="getTaskStatusTagType(task.status) as any"
              >
                {{ getTaskStatusLabel(task.status) }}
              </el-tag>
            </div>
            <div class="mobile-card-meta">
              <el-tag size="small" :type="getTaskPriorityTagType(task.priority || '') as any">
                {{ getTaskPriorityLabel(task.priority || '') }}
              </el-tag>
              <span class="mobile-task-assignee">
                <el-avatar :size="22" :src="task.assignee_avatar">
                  {{ task.assignee_name?.charAt(0) }}
                </el-avatar>
                {{ task.assignee_name }}
              </span>
            </div>
            <div class="mobile-card-footer">
              <span class="mobile-task-project">{{ task.project_name || '-' }}</span>
              <span class="mobile-task-date">
                <el-icon><Calendar /></el-icon>
                {{ formatDate(task.deadline) }}
              </span>
            </div>

            <!-- 移动端专用状态切换按钮组 -->
            <div class="status-switch-group" @click.stop>
              <el-button
                v-for="s in MOBILE_STATUS_CYCLE"
                :key="s"
                size="small"
                :type="task.status === s ? 'primary' : 'default'"
                :plain="task.status !== s"
                @click.stop="changeStatus(task, s)"
              >
                {{ getTaskStatusLabel(s) }}
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 移动端滑动操作提示 -->
      <div class="swipe-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>左右滑动卡片可切换状态</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 任务看板组件
 * - PC 端：四列看板（待办/进行中/待审核/已完成/延期），支持拖拽
 * - 移动端：横向滑动卡片视图，每张卡片可左右滑动切换状态（todo→doing→done）
 *           并提供移动端专用状态切换按钮组
 */
import { reactive, ref } from 'vue'
import { Calendar, ArrowLeft, ArrowRight, InfoFilled } from '@element-plus/icons-vue'
import { TASK_STATUS_LIST } from '@/utils/constants'
import {
  formatDate,
  getTaskPriorityLabel,
  getTaskPriorityTagType,
  getTaskStatusLabel,
  getTaskStatusTagType,
} from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import type { Task, TaskStatus } from '@/types'

const props = defineProps<{
  /** 任务列表 */
  tasks: Task[]
}>()

const emit = defineEmits<{
  /** 拖拽/滑动改变任务状态 */
  (e: 'changeStatus', task: Task, newStatus: TaskStatus): void
  /** 点击任务卡片 */
  (e: 'taskClick', task: Task): void
}>()

const { isMobile } = useDevice()

// 看板列定义
const columns = TASK_STATUS_LIST

// 正在拖拽的任务（PC 端）
const draggingTask = ref<Task | null>(null)

// 移动端状态切换循环（todo → doing → done → todo）
const MOBILE_STATUS_CYCLE: TaskStatus[] = ['todo', 'doing', 'done']

/** 触发阈值（px） */
const SWIPE_THRESHOLD = 60

// 滑动状态
const swipe = reactive<{
  taskId: number | null
  startX: number
  startY: number
  offsetX: number
  scrolling: boolean
}>({
  taskId: null,
  startX: 0,
  startY: 0,
  offsetX: 0,
  scrolling: false,
})

// 标记刚刚发生过滑动，用于抑制随之而来的 click 事件
const justSwiped = ref(false)

// 按状态分组获取任务
function getTasksByStatus(status: string): Task[] {
  return props.tasks.filter((t) => t.status === status)
}

// ============ PC 端拖拽 ============
function onDragStart(task: Task): void {
  draggingTask.value = task
}

function onDragOver(_status: string): void {
  // 可添加视觉反馈
}

function onDragLeave(): void {
  // 可添加视觉反馈
}

function onDrop(newStatus: string): void {
  if (draggingTask.value && draggingTask.value.status !== newStatus) {
    emit('changeStatus', draggingTask.value, newStatus as TaskStatus)
  }
  draggingTask.value = null
}

// ============ 移动端滑动 ============
/** 获取状态在循环中的索引（不在循环中则取最近的前一个） */
function statusIndex(status: TaskStatus): number {
  const idx = MOBILE_STATUS_CYCLE.indexOf(status)
  return idx >= 0 ? idx : 0
}

/** 下一个状态标签 */
function nextStatusLabel(status: TaskStatus): string {
  const idx = statusIndex(status)
  const next = MOBILE_STATUS_CYCLE[(idx + 1) % MOBILE_STATUS_CYCLE.length]
  return getTaskStatusLabel(next)
}

/** 上一个状态标签 */
function prevStatusLabel(status: TaskStatus): string {
  const idx = statusIndex(status)
  const prev =
    MOBILE_STATUS_CYCLE[(idx - 1 + MOBILE_STATUS_CYCLE.length) % MOBILE_STATUS_CYCLE.length]
  return getTaskStatusLabel(prev)
}

/** 卡片位移样式 */
function cardStyle(taskId: number): Record<string, string> {
  if (swipe.taskId !== taskId) return {}
  return {
    transform: `translateX(${swipe.offsetX}px)`,
    transition: swipe.scrolling ? 'none' : 'transform 0.25s ease',
  }
}

function onTouchStart(e: TouchEvent, task: Task): void {
  const touch = e.touches[0]
  if (!touch) return
  swipe.taskId = task.id
  swipe.startX = touch.clientX
  swipe.startY = touch.clientY
  swipe.offsetX = 0
  swipe.scrolling = false
}

function onTouchMove(e: TouchEvent, task: Task): void {
  if (swipe.taskId !== task.id) return
  const touch = e.touches[0]
  if (!touch) return
  const deltaX = touch.clientX - swipe.startX
  const deltaY = touch.clientY - swipe.startY

  // 判断方向：首次移动决定是水平滑动还是垂直滚动
  if (!swipe.scrolling && Math.abs(deltaX) + Math.abs(deltaY) > 8) {
    swipe.scrolling = true
  }

  // 垂直滚动时不干扰，让页面正常滚动
  if (Math.abs(deltaY) > Math.abs(deltaX)) {
    swipe.offsetX = 0
    return
  }

  // 水平滑动：通过 CSS touch-action: pan-y 由浏览器保证不触发页面滚动，
  // 此处仅记录位移用于卡片平移
  swipe.offsetX = deltaX
}

function onTouchEnd(_e: TouchEvent, task: Task): void {
  if (swipe.taskId !== task.id) return
  const offset = swipe.offsetX
  const wasScrolling = swipe.scrolling

  // 重置位移
  swipe.offsetX = 0
  swipe.scrolling = false
  swipe.taskId = null

  if (!wasScrolling) return

  // 标记发生过滑动，抑制后续 click
  justSwiped.value = true

  // 右滑：前进（todo → doing → done）
  if (offset > SWIPE_THRESHOLD) {
    const idx = statusIndex(task.status)
    const next = MOBILE_STATUS_CYCLE[(idx + 1) % MOBILE_STATUS_CYCLE.length]
    if (task.status !== next) {
      emit('changeStatus', task, next)
    }
  }
  // 左滑：后退
  else if (offset < -SWIPE_THRESHOLD) {
    const idx = statusIndex(task.status)
    const prev =
      MOBILE_STATUS_CYCLE[(idx - 1 + MOBILE_STATUS_CYCLE.length) % MOBILE_STATUS_CYCLE.length]
    if (task.status !== prev) {
      emit('changeStatus', task, prev)
    }
  }
}

/** 按钮组切换状态 */
function changeStatus(task: Task, newStatus: TaskStatus): void {
  if (task.status !== newStatus) {
    emit('changeStatus', task, newStatus)
  }
}

/** 卡片点击（排除滑动） */
function onCardClick(task: Task): void {
  // 若刚刚发生滑动，则不触发点击
  if (justSwiped.value) {
    justSwiped.value = false
    return
  }
  emit('taskClick', task)
}
</script>

<style lang="scss" scoped>
.task-board {
  width: 100%;
  overflow-x: auto;
  padding: 8px;
}

/* ===================== PC 端看板 ===================== */
.board-columns {
  display: flex;
  gap: 16px;
  min-height: 400px;
}

.board-column {
  flex: 1;
  min-width: 260px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  flex-direction: column;

  .column-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-top: 3px solid #909399;
    border-radius: 8px 8px 0 0;
    background: #fff;

    .column-title {
      font-size: 14px;
      font-weight: 600;
      color: #303133;
    }
  }

  .column-body {
    flex: 1;
    padding: 8px;
    overflow-y: auto;
  }

  .empty-column {
    text-align: center;
    color: #c0c4cc;
    font-size: 13px;
    padding: 40px 0;
  }
}

.task-card {
  background: #fff;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  &:active {
    cursor: grabbing;
  }

  .task-title {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .task-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;

    .task-assignee {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #606266;
    }
  }

  .task-date {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #909399;
  }
}

@media screen and (max-width: 768px) {
  .board-columns {
    flex-direction: column;
  }
}

/* ===================== 移动端滑动卡片视图 ===================== */
.mobile-board {
  width: 100%;
  padding: 4px 0 8px;
}

.mobile-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-task-wrapper {
  position: relative;
  overflow: hidden;
  border-radius: 10px;
}

.mobile-task-card {
  position: relative;
  z-index: 2;
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  will-change: transform;
  touch-action: pan-y;

  &.swipe-right {
    box-shadow: 0 2px 12px rgba(103, 194, 58, 0.25);
  }
  &.swipe-left {
    box-shadow: 0 2px 12px rgba(64, 158, 255, 0.25);
  }

  .mobile-card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 10px;

    .mobile-task-title {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
      flex: 1;
      line-height: 1.4;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
  }

  .mobile-card-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;

    .mobile-task-assignee {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #606266;
    }
  }

  .mobile-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    color: #909399;
    padding-bottom: 10px;
    border-bottom: 1px dashed #ebeef5;
    margin-bottom: 10px;

    .mobile-task-date {
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }

  .status-switch-group {
    display: flex;
    gap: 6px;

    :deep(.el-button) {
      flex: 1;
    }
  }
}

/* 滑动提示背景 */
.swipe-hint {
  position: absolute;
  top: 0;
  bottom: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;

  &.swipe-hint-left {
    left: 0;
    background: linear-gradient(90deg, rgba(64, 158, 255, 0.85), rgba(64, 158, 255, 0.4));
  }

  &.swipe-hint-right {
    right: 0;
    background: linear-gradient(270deg, rgba(103, 194, 58, 0.85), rgba(103, 194, 58, 0.4));
  }
}

.mobile-empty {
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
  padding: 40px 0;
}

.swipe-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 12px;
  font-size: 12px;
  color: #c0c4cc;
}

/* 无障碍：降低动画 */
@media (prefers-reduced-motion: reduce) {
  .mobile-task-card {
    transition: none !important;
  }
  .task-card {
    transition: none;
  }
}
</style>

