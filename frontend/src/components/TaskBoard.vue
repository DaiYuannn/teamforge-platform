<template>
  <div class="task-board">
    <!-- 四列看板 -->
    <div class="board-columns">
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
              {{ formatDate(task.due_date) }}
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="getTasksByStatus(col.value).length === 0" class="empty-column">
            暂无任务
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { TASK_STATUS_LIST } from '@/utils/constants'
import { formatDate, getTaskPriorityLabel, getTaskPriorityTagType } from '@/utils/format'
import type { Task, TaskStatus } from '@/types'

/**
 * 任务看板组件
 * 四列（待办/进行中/已完成/延期），支持拖拽
 */
const props = defineProps<{
  /** 任务列表 */
  tasks: Task[]
}>()

const emit = defineEmits<{
  /** 拖拽改变任务状态 */
  (e: 'changeStatus', task: Task, newStatus: TaskStatus): void
  /** 点击任务卡片 */
  (e: 'taskClick', task: Task): void
}>()

// 看板列定义
const columns = TASK_STATUS_LIST

// 正在拖拽的任务
const draggingTask = ref<Task | null>(null)

// 按状态分组获取任务
function getTasksByStatus(status: string): Task[] {
  return props.tasks.filter((t) => t.status === status)
}

// 拖拽开始
function onDragStart(task: Task): void {
  draggingTask.value = task
}

// 拖拽悬停
function onDragOver(_status: string): void {
  // 可添加视觉反馈
}

// 拖拽离开
function onDragLeave(): void {
  // 可添加视觉反馈
}

// 放下任务
function onDrop(newStatus: string): void {
  if (draggingTask.value && draggingTask.value.status !== newStatus) {
    emit('changeStatus', draggingTask.value, newStatus as TaskStatus)
  }
  draggingTask.value = null
}
</script>

<style lang="scss" scoped>
.task-board {
  width: 100%;
  overflow-x: auto;
  padding: 8px;
}

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
</style>
