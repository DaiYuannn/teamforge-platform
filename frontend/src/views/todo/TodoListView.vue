<template>
  <div class="page-container unified-todo-page">
    <PageHeader title="待办事项" subtitle="汇总任务、审批与贡献审核，按紧急程度集中处理" />

    <div v-if="loadError" class="status-banner" role="alert">
      <el-icon><WarningFilled /></el-icon>
      <span>待办数据加载失败。</span>
      <el-button link type="primary" @click="loadData">重新加载</el-button>
    </div>

    <section v-loading="loading" class="metric-strip" aria-label="待办概览">
      <button type="button" :class="{ active: filterType === '' }" @click="filterType = ''">
        <span>全部待办</span><strong>{{ stats.total }}</strong>
      </button>
      <button type="button" :class="['danger', { active: filterType === 'overdue_task' }]" @click="filterType = 'overdue_task'">
        <span>已经逾期</span><strong>{{ stats.overdue }}</strong>
      </button>
      <button type="button" :class="{ active: filterType === 'task' }" @click="filterType = 'task'">
        <span>执行任务</span><strong>{{ stats.tasks }}</strong>
      </button>
      <button type="button" :class="['warning', { active: filterType === 'approval' }]" @click="filterType = 'approval'">
        <span>等待审批</span><strong>{{ stats.approvals }}</strong>
      </button>
    </section>

    <section class="todo-workspace">
      <header class="todo-toolbar">
        <div>
          <h2>{{ currentFilterLabel }}</h2>
          <p>{{ visibleTodos.length }} 项需要处理</p>
        </div>
        <el-radio-group v-model="filterType" size="small">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="task">任务</el-radio-button>
          <el-radio-button value="overdue_task">逾期</el-radio-button>
          <el-radio-button value="approval">审批</el-radio-button>
          <el-radio-button value="contribution_review">贡献审核</el-radio-button>
          <el-radio-button value="ip_todo">知识产权</el-radio-button>
        </el-radio-group>
      </header>

      <div v-loading="loading" class="todo-items">
        <button
          v-for="(item, index) in visibleTodos"
          :key="item.id || `${item.type}_${index}`"
          type="button"
          class="todo-row"
          @click="goToUrl(item.url)"
        >
          <span class="todo-icon" :data-tone="typeTone(item.type)">
            <el-icon><component :is="getTypeIcon(item.type)" /></el-icon>
          </span>
          <span class="todo-content">
            <strong>{{ item.title }}</strong>
            <span class="todo-meta">
              <el-tag size="small" :type="getTypeTagType(item.type)">{{ getTypeLabel(item.type) }}</el-tag>
              <span v-if="item.priority">{{ getTaskPriorityLabel(item.priority) }}</span>
              <span v-if="item.due_date" :class="{ overdue: isOverdue(item.due_date) }">
                {{ isOverdue(item.due_date) ? '已逾期' : '截止' }} {{ formatDate(item.due_date) }}
              </span>
            </span>
          </span>
          <el-icon class="todo-arrow"><ArrowRight /></el-icon>
        </button>

        <EmptyState
          v-if="!loading && !visibleTodos.length"
          text="当前筛选下没有待办"
          description="切换类型可以查看其他行动项。"
          icon="CircleCheck"
          accent="#237A55"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, List, Lock, Trophy, Warning, WarningFilled } from '@element-plus/icons-vue'
import { getUnifiedTodos, type UnifiedTodoItem } from '@/api/todo'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { formatDate, getTaskPriorityLabel } from '@/utils/format'

type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

const router = useRouter()
const loading = ref(false)
const loadError = ref(false)
const allTodoItems = ref<UnifiedTodoItem[]>([])
const filterType = ref('')

const visibleTodos = computed(() =>
  filterType.value ? allTodoItems.value.filter((item) => item.type === filterType.value) : allTodoItems.value,
)

const stats = computed(() => ({
  total: allTodoItems.value.length,
  overdue: allTodoItems.value.filter((item) => item.type === 'overdue_task').length,
  tasks: allTodoItems.value.filter((item) => item.type === 'task').length,
  approvals: allTodoItems.value.filter((item) => item.type === 'approval').length,
}))

const currentFilterLabel = computed(() => (filterType.value ? getTypeLabel(filterType.value) : '全部行动项'))

function getTypeIcon(type: string): any {
  return { task: List, overdue_task: Warning, approval: Lock, contribution_review: Trophy, ip_todo: Trophy }[type] || List
}

function typeTone(type: string): string {
  return { task: 'primary', overdue_task: 'danger', approval: 'warning', contribution_review: 'success', ip_todo: 'warning' }[type] || 'neutral'
}

function getTypeTagType(type: string): TagType {
  return ({ task: 'primary', overdue_task: 'danger', approval: 'warning', contribution_review: 'success', ip_todo: 'warning' }[type] || 'info') as TagType
}

function getTypeLabel(type: string): string {
  return { task: '任务', overdue_task: '逾期任务', approval: '待审批', contribution_review: '贡献审核', ip_todo: '知识产权' }[type] || type
}

function isOverdue(date: string): boolean {
  return new Date(date).getTime() < Date.now()
}

function goToUrl(url: string): void {
  if (!url) return
  const [path, queryString] = url.split('?')
  if (!queryString) {
    router.push(path)
    return
  }
  router.push({ path, query: Object.fromEntries(new URLSearchParams(queryString)) })
}

async function loadData(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const response = await getUnifiedTodos()
    allTodoItems.value = response.results || []
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.unified-todo-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.unified-todo-page :deep(.page-header) { margin-bottom: 0; }

.status-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  color: #7f3030;
  background: var(--danger-light);
  border: 1px solid #efcfcd;
  border-radius: var(--radius-sm);
}

.status-banner span { flex: 1; }

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.metric-strip button {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 16px 18px;
  color: var(--color-text);
  text-align: left;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.metric-strip button + button { border-left: 1px solid var(--color-border-light); }
.metric-strip button.active { background: var(--color-primary-soft); }
.metric-strip span { color: var(--color-text-muted); font-size: 12px; }
.metric-strip strong { font-size: 24px; font-weight: 650; font-variant-numeric: tabular-nums; }
.metric-strip .danger strong { color: var(--color-danger); }
.metric-strip .warning strong { color: var(--color-warning); }

.todo-workspace {
  padding: 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.todo-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--color-border-light);
}

.todo-toolbar h2 { font-size: 16px; font-weight: 600; }
.todo-toolbar p { margin-top: 3px; color: var(--color-text-muted); font-size: 11px; }

.todo-items { min-height: 180px; }

.todo-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 13px 4px;
  color: var(--color-text);
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--color-border-light);
  cursor: pointer;
}

.todo-row:hover { background: var(--color-surface-subtle); }

.todo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--color-info);
  background: var(--info-light);
  border-radius: var(--radius-sm);
}

.todo-icon[data-tone='primary'] { color: var(--color-primary); background: var(--color-primary-soft); }
.todo-icon[data-tone='danger'] { color: var(--color-danger); background: var(--danger-light); }
.todo-icon[data-tone='warning'] { color: var(--color-warning); background: var(--warning-light); }
.todo-icon[data-tone='success'] { color: var(--color-success); background: var(--success-light); }

.todo-content { display: flex; flex-direction: column; min-width: 0; }
.todo-content > strong { overflow: hidden; font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.todo-meta { display: flex; align-items: center; gap: 10px; margin-top: 5px; color: var(--color-text-muted); font-size: 11px; }
.todo-meta .overdue { color: var(--color-danger); font-weight: 600; }
.todo-arrow { color: var(--color-text-muted); }

@media screen and (max-width: 768px) {
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-strip button { padding: 12px; }
  .metric-strip button + button { border-left: 0; }
  .metric-strip button:nth-child(even) { border-left: 1px solid var(--color-border-light); }
  .metric-strip button:nth-child(n + 3) { border-top: 1px solid var(--color-border-light); }
  .metric-strip strong { font-size: 20px; }
  .todo-workspace { padding: 14px; }
  .todo-toolbar { align-items: flex-start; flex-direction: column; }
  .todo-toolbar :deep(.el-radio-group) { width: 100%; overflow-x: auto; flex-wrap: nowrap; }
  .todo-toolbar :deep(.el-radio-button) { flex: 0 0 auto; }
  .todo-meta { flex-wrap: wrap; }
}
</style>
