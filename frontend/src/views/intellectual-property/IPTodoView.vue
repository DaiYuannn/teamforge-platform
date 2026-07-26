<template>
  <div class="page-container ip-todo-page">
    <PageHeader title="待我处理" subtitle="集中处理知识产权流程中与你有关的行动项" />

    <div v-if="loadError" class="status-banner" role="alert">
      <el-icon><WarningFilled /></el-icon>
      <span>待办数据加载失败。</span>
      <el-button link type="primary" @click="loadData">重新加载</el-button>
    </div>

    <section v-loading="loading" class="todo-summary" aria-label="待办摘要">
      <div><span>全部待办</span><strong>{{ allTodos.length }}</strong></div>
      <div :class="{ danger: overdueCount > 0 }"><span>已经逾期</span><strong>{{ overdueCount }}</strong></div>
      <div :class="{ warning: dueSoonCount > 0 }"><span>三日内到期</span><strong>{{ dueSoonCount }}</strong></div>
    </section>

    <section v-if="todoGroups.length" class="todo-workspace">
      <section v-for="group in todoGroups" :key="group.type" class="todo-group">
        <header class="group-header">
          <span class="group-icon"><el-icon><component :is="group.icon" /></el-icon></span>
          <div>
            <h2>{{ group.title }}</h2>
            <p>{{ group.items.length }} 项待处理</p>
          </div>
        </header>

        <div class="todo-list">
          <button
            v-for="item in group.items"
            :key="`${item.application_id}_${item.type}`"
            type="button"
            class="todo-row"
            @click="goToDetail(item.application_id)"
          >
            <span class="todo-main">
              <strong>{{ item.title }}</strong>
              <span>{{ item.description }}</span>
            </span>
            <span class="todo-meta">
              <span v-if="item.deadline" :data-tone="getDeadlineTone(item.deadline)">
                {{ deadlineLabel(item.deadline) }}
              </span>
              <time>{{ formatRelativeTime(item.created_at) }}</time>
            </span>
            <el-icon class="row-arrow"><ArrowRight /></el-icon>
          </button>
        </div>
      </section>
    </section>

    <EmptyState
      v-else-if="!loading"
      text="当前没有待办事项"
      description="新的撰写、审核、确认或异议任务会出现在这里。"
      icon="CircleCheck"
      accent="#237A55"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, WarningFilled } from '@element-plus/icons-vue'
import { getMyIPTodo } from '@/api/intellectualProperty'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import type { IPTodoItem } from '@/types/intellectualProperty'
import { formatDate, formatRelativeTime } from '@/utils/format'
import { mapIPApplicationsToTodos } from './ipWorkflow'

const router = useRouter()
const loading = ref(false)
const loadError = ref(false)
const allTodos = ref<IPTodoItem[]>([])

const groupConfig: Record<IPTodoItem['type'], { title: string; icon: string; order: number }> = {
  return_fix: { title: '退回修改', icon: 'WarningFilled', order: 1 },
  review: { title: '审核申请', icon: 'View', order: 2 },
  confirm: { title: '确认申请', icon: 'CircleCheck', order: 3 },
  submit: { title: '提交申请', icon: 'Upload', order: 4 },
  writing: { title: '材料撰写', icon: 'Edit', order: 5 },
  objection: { title: '异议处理', icon: 'ChatDotRound', order: 6 },
  my_objection: { title: '我提出的异议', icon: 'Bell', order: 7 },
}

const todoGroups = computed(() =>
  Object.entries(groupConfig)
    .map(([type, config]) => ({
      type: type as IPTodoItem['type'],
      ...config,
      items: allTodos.value
        .filter((item) => item.type === type)
        .sort((left, right) => dateValue(left.deadline) - dateValue(right.deadline)),
    }))
    .filter((group) => group.items.length)
    .sort((left, right) => left.order - right.order),
)

const overdueCount = computed(() => allTodos.value.filter((item) => getDeadlineTone(item.deadline) === 'danger').length)
const dueSoonCount = computed(() => allTodos.value.filter((item) => getDeadlineTone(item.deadline) === 'warning').length)

function dateValue(value: string | null | undefined): number {
  if (!value) return Number.MAX_SAFE_INTEGER
  const timestamp = new Date(value).getTime()
  return Number.isNaN(timestamp) ? Number.MAX_SAFE_INTEGER : timestamp
}

function getDeadlineTone(deadline: string | null | undefined): 'danger' | 'warning' | 'neutral' {
  if (!deadline) return 'neutral'
  const difference = dateValue(deadline) - Date.now()
  if (difference < 0) return 'danger'
  if (difference <= 3 * 86_400_000) return 'warning'
  return 'neutral'
}

function deadlineLabel(deadline: string): string {
  const tone = getDeadlineTone(deadline)
  if (tone === 'danger') return `已逾期 · ${formatDate(deadline)}`
  if (tone === 'warning') return `即将到期 · ${formatDate(deadline)}`
  return `截止 ${formatDate(deadline)}`
}

async function loadData(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const response = await getMyIPTodo()
    allTodos.value = mapIPApplicationsToTodos(response)
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function goToDetail(applicationId: number): void {
  router.push(`/intellectual-property/${applicationId}`)
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.ip-todo-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ip-todo-page :deep(.page-header) { margin-bottom: 0; }

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

.todo-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.todo-summary > div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 16px 18px;
}

.todo-summary > div + div { border-left: 1px solid var(--color-border-light); }
.todo-summary span { color: var(--color-text-muted); font-size: 12px; }
.todo-summary strong { font-size: 24px; font-weight: 650; font-variant-numeric: tabular-nums; }
.todo-summary .danger strong { color: var(--color-danger); }
.todo-summary .warning strong { color: var(--color-warning); }

.todo-workspace {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.todo-group {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 20px;
  padding: 18px;
}

.todo-group + .todo-group { border-top: 1px solid var(--color-border-light); }

.group-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.group-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  color: var(--ip-color);
  background: var(--ip-light);
  border-radius: var(--radius-sm);
}

.group-header h2 { font-size: 14px; font-weight: 600; }
.group-header p { margin-top: 3px; color: var(--color-text-muted); font-size: 11px; }

.todo-list { border-top: 1px solid var(--color-border-light); }

.todo-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 20px;
  align-items: center;
  gap: 16px;
  width: 100%;
  padding: 12px 4px;
  color: var(--color-text);
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--color-border-light);
  cursor: pointer;
}

.todo-row:last-child { border-bottom: 0; }
.todo-row:hover { background: var(--color-surface-subtle); }
.todo-main { display: flex; flex-direction: column; min-width: 0; }
.todo-main strong { overflow: hidden; font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.todo-main > span { display: -webkit-box; margin-top: 4px; overflow: hidden; color: var(--color-text-muted); font-size: 12px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.todo-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; color: var(--color-text-muted); font-size: 11px; }
.todo-meta > span[data-tone='danger'] { color: var(--color-danger); font-weight: 600; }
.todo-meta > span[data-tone='warning'] { color: var(--color-warning); font-weight: 600; }
.row-arrow { color: var(--color-text-muted); }

@media screen and (max-width: 768px) {
  .todo-summary > div { flex-direction: column; align-items: flex-start; padding: 12px; }
  .todo-summary strong { font-size: 20px; }
  .todo-group { grid-template-columns: 1fr; gap: 12px; padding: 14px; }
  .todo-row { grid-template-columns: minmax(0, 1fr) 18px; gap: 10px; }
  .todo-meta { grid-column: 1 / -1; grid-row: 2; flex-direction: row; align-items: center; justify-content: space-between; }
  .row-arrow { grid-column: 2; grid-row: 1; }
}
</style>
