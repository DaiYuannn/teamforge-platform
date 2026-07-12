<template>
  <div class="todo-list">
    <PageHeader title="待办事项" />

    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" :style="{ color: '#409EFF' }">{{ stats.total || 0 }}</div>
          <div class="stat-label">总待办</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" :style="{ color: '#E6A23C' }">{{ stats.overdue || 0 }}</div>
          <div class="stat-label">逾期</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" :style="{ color: '#67C23A' }">{{ stats.tasks || 0 }}</div>
          <div class="stat-label">任务</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" :style="{ color: '#F56C6C' }">{{ stats.approvals || 0 }}</div>
          <div class="stat-label">审批</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top: 16px">
      <div class="toolbar">
        <el-radio-group v-model="filterType" @change="loadData">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="task">任务</el-radio-button>
          <el-radio-button value="overdue_task">逾期</el-radio-button>
          <el-radio-button value="approval">审批</el-radio-button>
          <el-radio-button value="contribution_review">贡献审核</el-radio-button>
        </el-radio-group>
      </div>

      <div v-loading="loading" class="todo-items">
        <div v-if="todoItems.length === 0 && !loading" class="empty">
          <el-empty description="暂无待办事项" />
        </div>
        <div v-for="(item, idx) in todoItems" :key="idx" class="todo-item" @click="goToUrl(item.url)">
          <div class="todo-icon">
            <el-icon :size="18" :color="getTypeColor(item.type)">
              <component :is="getTypeIcon(item.type)" />
            </el-icon>
          </div>
          <div class="todo-content">
            <div class="todo-title">{{ item.title }}</div>
            <div class="todo-meta">
              <el-tag size="small" :type="getTypeTagType(item.type)">{{ getTypeLabel(item.type) }}</el-tag>
              <span v-if="item.priority" class="priority">优先级: {{ item.priority }}</span>
              <span v-if="item.due_date" class="due-date" :class="{ overdue: isOverdue(item.due_date) }">
                截止: {{ formatDate(item.due_date) }}
              </span>
            </div>
          </div>
          <el-icon class="todo-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { List, Warning, Lock, Trophy, ArrowRight } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { get } from '@/api/request'
import { formatDate } from '@/utils/format'

const router = useRouter()
const loading = ref(false)
const todoItems = ref<any[]>([])
const filterType = ref('')

const stats = computed(() => {
  const result: Record<string, number> = { total: todoItems.value.length }
  todoItems.value.forEach(item => {
    if (item.type === 'overdue_task') result.overdue = (result.overdue || 0) + 1
    if (item.type === 'task') result.tasks = (result.tasks || 0) + 1
    if (item.type === 'approval') result.approvals = (result.approvals || 0) + 1
  })
  return result
})

function getTypeIcon(type: string): any {
  const map: Record<string, any> = {
    task: List,
    overdue_task: Warning,
    approval: Lock,
    contribution_review: Trophy,
  }
  return map[type] || List
}

function getTypeColor(type: string): string {
  const map: Record<string, string> = {
    task: '#409EFF',
    overdue_task: '#F56C6C',
    approval: '#E6A23C',
    contribution_review: '#67C23A',
  }
  return map[type] || '#409EFF'
}

type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

function getTypeTagType(type: string): TagType {
  const map: Record<string, TagType> = {
    task: 'primary',
    overdue_task: 'danger',
    approval: 'warning',
    contribution_review: 'success',
  }
  return map[type] || 'info'
}

function getTypeLabel(type: string): string {
  const map: Record<string, string> = {
    task: '任务',
    overdue_task: '逾期任务',
    approval: '待审批',
    contribution_review: '贡献审核',
  }
  return map[type] || type
}

function isOverdue(dateStr: string): boolean {
  if (!dateStr) return false
  return new Date(dateStr) < new Date()
}

function goToUrl(url: string): void {
  if (!url) return
  if (url.includes('?')) {
    const [path, query] = url.split('?')
    const params = new URLSearchParams(query)
    router.push({ path, query: Object.fromEntries(params) })
  } else {
    router.push(url)
  }
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (filterType.value) params.type = filterType.value
    const res = await get<any>('/todo/', params)
    todoItems.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // handled
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.stat-card {
  text-align: center;
  padding: 8px 0;
}
.stat-value {
  font-size: 32px;
  font-weight: bold;
}
.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.toolbar {
  margin-bottom: 16px;
}
.todo-items {
  min-height: 200px;
}
.empty {
  padding: 40px 0;
}
.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}
.todo-item:hover {
  background: var(--el-fill-color-light);
}
.todo-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--el-fill-color);
  display: flex;
  align-items: center;
  justify-content: center;
}
.todo-content {
  flex: 1;
}
.todo-title {
  font-size: 14px;
  color: var(--el-text-color-primary);
}
.todo-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.due-date.overdue {
  color: var(--el-color-danger);
}
.todo-arrow {
  color: var(--el-text-color-placeholder);
}
</style>
