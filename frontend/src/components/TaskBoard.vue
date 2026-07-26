<template>
  <div class="task-board">
    <div v-if="!isMobile" class="desktop-board">
      <div class="board-scroll">
        <div class="board-columns">
          <section
            v-for="column in columns"
            :key="column.value"
            class="board-column"
            :class="{ 'is-drag-over': dragOverStatus === column.value }"
            @dragenter.prevent="onDragOver(column.value)"
            @dragover.prevent="onDragOver(column.value)"
            @dragleave.self="onDragLeave(column.value)"
            @drop.prevent="onDrop(column.value)"
          >
            <header class="column-header">
              <span class="column-heading">
                <span class="column-accent" :style="{ backgroundColor: column.color }"></span>
                <span class="column-title">{{ column.label }}</span>
              </span>
              <span class="column-count">{{ getTasksByStatus(column.value).length }}</span>
            </header>

            <div class="column-body">
              <article
                v-for="task in getTasksByStatus(column.value)"
                :key="task.id"
                class="task-card"
                :class="[priorityClass(task), { 'is-clickable': canOpenTask(task) }]"
                :draggable="canChangeTaskStatus(task)"
                :tabindex="canOpenTask(task) ? 0 : -1"
                @dragstart="onDragStart($event, task)"
                @dragend="onDragEnd"
                @click="openTask(task)"
                @keydown.enter="openTask(task)"
              >
                <div class="task-project">{{ task.project_name || '未关联项目' }}</div>
                <h3 class="task-title">{{ task.title }}</h3>
                <div class="task-card-tags">
                  <el-tag size="small" :type="getTaskPriorityTagType(task.priority || 'medium') as any">
                    {{ getTaskPriorityLabel(task.priority || 'medium') }}优先级
                  </el-tag>
                </div>
                <div class="task-meta-list">
                  <span class="task-meta-row">
                    <el-icon><User /></el-icon>
                    <span class="meta-value">{{ task.assignee_name || '未指定负责人' }}</span>
                  </span>
                  <span class="task-meta-row" :class="deadlineClass(task)">
                    <el-icon><Calendar /></el-icon>
                    <span class="meta-value">{{ formatDate(task.deadline) }}</span>
                  </span>
                </div>
              </article>

              <div v-if="getTasksByStatus(column.value).length === 0" class="empty-column">
                <span>暂无任务</span>
                <small>该流程节点当前为空</small>
              </div>
            </div>
          </section>
        </div>
      </div>

      <section v-if="auxiliaryTasks.length" class="auxiliary-section">
        <header class="auxiliary-header">
          <div>
            <h3>非主流程状态</h3>
            <p>暂停、取消和需要协助的任务</p>
          </div>
          <span class="auxiliary-count">{{ auxiliaryTasks.length }}</span>
        </header>
        <div class="auxiliary-grid">
          <article
            v-for="task in auxiliaryTasks"
            :key="task.id"
            class="auxiliary-task"
            :class="{ 'is-clickable': canOpenTask(task) }"
            :draggable="canChangeTaskStatus(task)"
            :tabindex="canOpenTask(task) ? 0 : -1"
            @dragstart="onDragStart($event, task)"
            @dragend="onDragEnd"
            @click="openTask(task)"
            @keydown.enter="openTask(task)"
          >
            <div class="auxiliary-task-main">
              <el-tag size="small" :type="getTaskStatusTagType(task.status) as any">
                {{ getTaskStatusLabel(task.status) }}
              </el-tag>
              <strong>{{ task.title }}</strong>
              <span>{{ task.project_name || '未关联项目' }}</span>
            </div>
            <div class="auxiliary-task-meta">
              <span>{{ task.assignee_name || '未指定负责人' }}</span>
              <span :class="deadlineClass(task)">{{ formatDate(task.deadline) }}</span>
            </div>
          </article>
        </div>
      </section>
    </div>

    <div v-else class="mobile-task-list">
      <div class="status-segments" role="tablist" aria-label="按任务状态筛选">
        <button
          v-for="segment in mobileSegments"
          :key="segment.value"
          type="button"
          role="tab"
          class="status-segment"
          :class="{ 'is-active': mobileStatus === segment.value }"
          :aria-selected="mobileStatus === segment.value"
          @click="mobileStatus = segment.value"
        >
          <span>{{ segment.label }}</span>
          <span class="segment-count">{{ getSegmentCount(segment.value) }}</span>
        </button>
      </div>

      <div v-if="mobileTasks.length" class="mobile-cards">
        <article
          v-for="task in mobileTasks"
          :key="task.id"
          class="mobile-task-card"
          :class="{ 'is-clickable': canOpenTask(task) }"
          :tabindex="canOpenTask(task) ? 0 : -1"
          @click="openTask(task)"
          @keydown.enter="openTask(task)"
        >
          <div class="mobile-card-heading">
            <span class="mobile-project">{{ task.project_name || '未关联项目' }}</span>
            <el-tag size="small" :type="getTaskStatusTagType(task.status) as any">
              {{ getTaskStatusLabel(task.status) }}
            </el-tag>
          </div>
          <h3>{{ task.title }}</h3>

          <div class="mobile-meta-grid">
            <span class="task-meta-row">
              <el-icon><User /></el-icon>
              <span class="meta-value">{{ task.assignee_name || '未指定负责人' }}</span>
            </span>
            <span class="task-meta-row" :class="deadlineClass(task)">
              <el-icon><Calendar /></el-icon>
              <span class="meta-value">{{ formatDate(task.deadline) }}</span>
            </span>
          </div>

          <footer class="mobile-card-footer" @click.stop @keydown.stop>
            <el-tag size="small" :type="getTaskPriorityTagType(task.priority || 'medium') as any">
              {{ getTaskPriorityLabel(task.priority || 'medium') }}优先级
            </el-tag>
            <label class="mobile-status-control">
              <span>更新状态</span>
              <el-select
                :model-value="task.status"
                size="small"
                aria-label="更新任务状态"
                :disabled="!canChangeTaskStatus(task)"
                @change="changeStatus(task, $event as TaskStatus)"
              >
                <el-option
                  v-for="(item, value) in TASK_STATUS_MAP"
                  :key="value"
                  :label="item.label"
                  :value="value"
                  :disabled="value !== task.status && !canChangeTaskToStatus(task, value as TaskStatus)"
                />
              </el-select>
            </label>
          </footer>
        </article>
      </div>

      <div v-else class="mobile-empty">
        <span>当前状态下暂无任务</span>
        <small>该状态分组当前为空</small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Calendar, User } from '@element-plus/icons-vue'
import { TASK_STATUS_LIST, TASK_STATUS_MAP } from '@/utils/constants'
import {
  formatDate,
  getTaskPriorityLabel,
  getTaskPriorityTagType,
  getTaskStatusLabel,
  getTaskStatusTagType,
} from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import type { Task, TaskStatus } from '@/types'

type MobileStatus = 'all' | TaskStatus

const props = withDefaults(
  defineProps<{
    tasks: Task[]
    interactive?: boolean
    canOpen?: (task: Task) => boolean
    canChangeStatus?: (task: Task) => boolean
    canChangeToStatus?: (task: Task, status: TaskStatus) => boolean
  }>(),
  {
    interactive: true,
  },
)

const emit = defineEmits<{
  (e: 'changeStatus', task: Task, newStatus: TaskStatus): void
  (e: 'taskClick', task: Task): void
}>()

const { isMobile } = useDevice(769)

const columnColors: Partial<Record<TaskStatus, string>> = {
  todo: 'var(--color-info)',
  doing: 'var(--color-primary)',
  pending_review: 'var(--color-warning)',
  done: 'var(--color-success)',
  overdue: 'var(--color-danger)',
}

const columns = TASK_STATUS_LIST.map((column) => ({
  ...column,
  value: column.value as TaskStatus,
  color: columnColors[column.value as TaskStatus] || 'var(--color-info)',
}))

const primaryStatuses = new Set<TaskStatus>(columns.map((column) => column.value))
const draggingTask = ref<Task | null>(null)
const dragOverStatus = ref<TaskStatus | null>(null)
const mobileStatus = ref<MobileStatus>('all')

const mobileSegments = computed<Array<{ value: MobileStatus; label: string }>>(() => [
  { value: 'all', label: '全部' },
  ...Object.entries(TASK_STATUS_MAP).map(([value, item]) => ({
    value: value as TaskStatus,
    label: item.label,
  })),
])

const mobileTasks = computed(() => {
  if (mobileStatus.value === 'all') return props.tasks
  return props.tasks.filter((task) => task.status === mobileStatus.value)
})

const auxiliaryTasks = computed(() =>
  props.tasks.filter((task) => !primaryStatuses.has(task.status)),
)

function getTasksByStatus(status: TaskStatus): Task[] {
  return props.tasks.filter((task) => task.status === status)
}

function getSegmentCount(status: MobileStatus): number {
  if (status === 'all') return props.tasks.length
  return getTasksByStatus(status).length
}

function priorityClass(task: Task): string {
  return `priority-${task.priority || 'medium'}`
}

function isOverdue(task: Task): boolean {
  if (!task.deadline || task.status === 'done' || task.status === 'cancelled') return false
  const deadline = Date.parse(task.deadline)
  return Number.isFinite(deadline) && deadline < Date.now()
}

function deadlineClass(task: Task): string {
  return isOverdue(task) ? 'is-overdue' : ''
}

function openTask(task: Task): void {
  if (canOpenTask(task)) emit('taskClick', task)
}

function canOpenTask(task: Task): boolean {
  return props.interactive && (props.canOpen ? props.canOpen(task) : true)
}

function canChangeTaskStatus(task: Task): boolean {
  return props.interactive && (props.canChangeStatus ? props.canChangeStatus(task) : true)
}

function canChangeTaskToStatus(task: Task, status: TaskStatus): boolean {
  return (
    canChangeTaskStatus(task)
    && (props.canChangeToStatus ? props.canChangeToStatus(task, status) : true)
  )
}

function onDragStart(event: DragEvent, task: Task): void {
  if (!canChangeTaskStatus(task)) {
    event.preventDefault()
    return
  }
  draggingTask.value = task
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(task.id))
  }
}

function onDragOver(status: TaskStatus): void {
  dragOverStatus.value = status
}

function onDragLeave(status: TaskStatus): void {
  if (dragOverStatus.value === status) dragOverStatus.value = null
}

function onDrop(newStatus: TaskStatus): void {
  if (
    draggingTask.value &&
    canChangeTaskToStatus(draggingTask.value, newStatus) &&
    draggingTask.value.status !== newStatus
  ) {
    emit('changeStatus', draggingTask.value, newStatus)
  }
  onDragEnd()
}

function onDragEnd(): void {
  draggingTask.value = null
  dragOverStatus.value = null
}

function changeStatus(task: Task, newStatus: TaskStatus): void {
  if (canChangeTaskToStatus(task, newStatus) && task.status !== newStatus) {
    emit('changeStatus', task, newStatus)
  }
}
</script>

<style lang="scss" scoped>
.task-board {
  width: 100%;
  min-width: 0;
}

.board-scroll {
  width: 100%;
  overflow-x: auto;
  overscroll-behavior-inline: contain;
  padding-bottom: var(--space-1);
}

.board-columns {
  display: grid;
  grid-template-columns: repeat(5, minmax(228px, 1fr));
  gap: var(--space-3);
  min-width: 1164px;
}

.board-column {
  display: flex;
  flex-direction: column;
  height: clamp(420px, 58vh, 680px);
  min-width: 0;
  overflow: hidden;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.board-column.is-drag-over {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 46px;
  min-width: 0;
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-light);
}

.column-heading {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: var(--space-2);
}

.column-accent {
  width: 3px;
  height: 18px;
  flex: 0 0 3px;
  border-radius: var(--radius-xs);
}

.column-title {
  overflow: hidden;
  color: var(--color-text);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.column-count,
.auxiliary-count,
.segment-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 22px;
  padding: 0 6px;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-variant-numeric: tabular-nums;
  background: var(--color-surface-strong);
  border-radius: var(--radius-pill);
}

.column-body {
  flex: 1;
  min-height: 0;
  padding: var(--space-2);
  overflow-y: auto;
}

.task-card {
  margin-bottom: var(--space-2);
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-left: 3px solid var(--color-info);
  border-radius: var(--radius-sm);
  cursor: grab;
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.task-card:hover,
.task-card:focus-visible,
.auxiliary-task:hover,
.auxiliary-task:focus-visible,
.mobile-task-card:hover,
.mobile-task-card:focus-visible {
  background: var(--color-surface-subtle);
  border-color: var(--color-border);
}

.task-card:active {
  cursor: grabbing;
}

.task-card[draggable='false'],
.auxiliary-task[draggable='false'] {
  cursor: default;
}

.task-card.priority-low { border-left-color: var(--color-info); }
.task-card.priority-medium { border-left-color: var(--color-primary); }
.task-card.priority-high { border-left-color: var(--color-warning); }
.task-card.priority-urgent { border-left-color: var(--color-danger); }

.task-project,
.mobile-project {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-title {
  min-height: 40px;
  margin: 5px 0 var(--space-2);
  overflow: hidden;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.45;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.task-card-tags {
  min-height: 24px;
  margin-bottom: var(--space-2);
}

.task-meta-list {
  display: grid;
  gap: 5px;
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border-light);
}

.task-meta-row {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 6px;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.task-meta-row .el-icon {
  flex: 0 0 auto;
}

.meta-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.is-overdue {
  color: var(--color-danger) !important;
  font-weight: 600;
}

.empty-column {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  min-height: 132px;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
}

.empty-column small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.auxiliary-section {
  margin-top: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.auxiliary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.auxiliary-header h3 {
  color: var(--color-text);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.auxiliary-header p {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.auxiliary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-2);
  padding: var(--space-3);
}

.auxiliary-task {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: grab;
}

.auxiliary-task-main,
.auxiliary-task-meta {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-1);
}

.auxiliary-task-main strong,
.auxiliary-task-main span,
.auxiliary-task-meta span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.auxiliary-task-main strong {
  color: var(--color-text);
  font-size: var(--font-size-sm);
}

.auxiliary-task-main > span,
.auxiliary-task-meta {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.auxiliary-task-meta {
  flex: 0 0 auto;
  text-align: right;
}

.is-clickable {
  cursor: pointer;
}

.status-segments {
  display: flex;
  width: 100%;
  gap: var(--space-1);
  padding: var(--space-1);
  overflow-x: auto;
  background: var(--color-surface-strong);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  scrollbar-width: none;
}

.status-segments::-webkit-scrollbar {
  display: none;
}

.status-segment {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  min-width: 82px;
  height: 34px;
  gap: 6px;
  padding: 0 var(--space-2);
  color: var(--color-text-regular);
  font-size: var(--font-size-xs);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.status-segment.is-active {
  color: var(--color-primary);
  font-weight: 600;
  background: var(--color-surface);
  border-color: var(--color-border);
}

.status-segment.is-active .segment-count {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.mobile-cards {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.mobile-task-card {
  min-width: 0;
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.mobile-card-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  gap: var(--space-2);
}

.mobile-project {
  flex: 1;
  min-width: 0;
}

.mobile-task-card h3 {
  margin: var(--space-2) 0 var(--space-3);
  color: var(--color-text);
  font-size: 15px;
  font-weight: 600;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.mobile-meta-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-2);
}

.mobile-card-footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
}

.mobile-status-control {
  display: grid;
  flex: 0 0 136px;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.mobile-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  min-height: 180px;
  margin-top: var(--space-3);
  gap: var(--space-1);
  color: var(--color-text-regular);
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
}

.mobile-empty small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

@media screen and (max-width: 420px) {
  .mobile-meta-grid {
    grid-template-columns: 1fr;
  }

  .mobile-card-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .mobile-status-control {
    width: 100%;
    flex-basis: auto;
  }
}
</style>
