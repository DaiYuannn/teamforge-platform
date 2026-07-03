<template>
  <div class="page-container">
    <PageHeader title="待我处理" subtitle="我负责的知识产权相关待办事项" />

    <div v-loading="loading" class="todo-container">
      <!-- 按类型分组展示 -->
      <div v-for="group in todoGroups" :key="group.type" class="todo-group">
        <div class="group-header">
          <el-icon :size="18"><component :is="group.icon" /></el-icon>
          <span class="group-title">{{ group.title }}</span>
          <el-badge :value="group.items.length" type="primary" />
        </div>

        <div class="group-items">
          <el-card
            v-for="item in group.items"
            :key="item.application_id + item.type"
            class="todo-item"
            shadow="hover"
            @click="goToDetail(item.application_id)"
          >
            <div class="todo-item-header">
              <span class="todo-item-title">{{ item.title }}</span>
              <el-tag v-if="item.deadline" size="small" :type="getDeadlineColor(item.deadline)">
                截止：{{ formatDate(item.deadline) }}
              </el-tag>
            </div>
            <div class="todo-item-desc">{{ item.description }}</div>
            <div class="todo-item-footer">
              <span class="todo-item-time">{{ formatRelativeTime(item.created_at) }}</span>
              <el-button type="primary" link size="small">去处理</el-button>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 空状态 -->
      <el-empty v-if="!loading && allTodos.length === 0" description="暂无待办事项" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMyIPTodo } from '@/api/intellectualProperty'
import { formatDate, formatRelativeTime } from '@/utils/format'
import type { IPTodoItem } from '@/types/intellectualProperty'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()

const loading = ref(false)
const allTodos = ref<IPTodoItem[]>([])

// 待办类型分组配置
const groupConfig: Record<string, { title: string; icon: string }> = {
  writing: { title: '我负责撰写的材料', icon: 'Edit' },
  return_fix: { title: '我需要修改的退回', icon: 'WarningFilled' },
  submit: { title: '我需要提交的申请', icon: 'Upload' },
  review: { title: '我需要审核的', icon: 'View' },
  confirm: { title: '我需要确认的', icon: 'CircleCheck' },
  objection: { title: '我需要处理的异议', icon: 'ChatDotRound' },
  my_objection: { title: '我提出的异议', icon: 'Bell' },
}

// 按类型分组的待办列表
const todoGroups = computed(() => {
  const groups: { type: string; title: string; icon: string; items: IPTodoItem[] }[] = []
  for (const [type, config] of Object.entries(groupConfig)) {
    const items = allTodos.value.filter((t) => t.type === type)
    if (items.length > 0) {
      groups.push({
        type,
        title: config.title,
        icon: config.icon,
        items,
      })
    }
  }
  return groups
})

// 加载待办数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res = await getMyIPTodo() as any
    allTodos.value = Array.isArray(res) ? res : (res?.data || res?.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 跳转到申请详情
function goToDetail(applicationId: number): void {
  router.push(`/intellectual-property/${applicationId}`)
}

// 获取截止时间标签颜色
function getDeadlineColor(deadline: string): any {
  const now = new Date()
  const dl = new Date(deadline)
  if (dl < now) return 'danger'
  const diffDays = (dl.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  if (diffDays <= 3) return 'warning'
  return 'info'
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.todo-container {
  .todo-group {
    margin-bottom: 24px;

    .group-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      padding: 0 4px;

      .group-title {
        font-size: 16px;
        font-weight: 600;
        color: #303133;
      }
    }

    .group-items {
      .todo-item {
        margin-bottom: 12px;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          transform: translateY(-2px);
        }

        .todo-item-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;

          .todo-item-title {
            font-size: 15px;
            font-weight: 600;
            color: #303133;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-right: 8px;
          }
        }

        .todo-item-desc {
          font-size: 13px;
          color: #606266;
          margin-bottom: 8px;
          line-height: 1.5;
        }

        .todo-item-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;

          .todo-item-time {
            font-size: 12px;
            color: #909399;
          }
        }
      }
    }
  }
}

@media screen and (max-width: 768px) {
  .todo-container {
    .todo-group {
      .group-header {
        .group-title {
          font-size: 14px;
        }
      }
    }
  }
}
</style>
