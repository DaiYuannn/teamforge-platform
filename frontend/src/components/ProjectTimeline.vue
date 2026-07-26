<template>
  <div class="project-timeline">
    <!-- 顶部筛选栏 -->
    <div class="timeline-toolbar">
      <el-select
        v-model="selectedCategories"
        multiple
        collapse-tags
        collapse-tags-tooltip
        clearable
        placeholder="筛选事件类型"
        class="event-type-filter"
        @change="loadEvents"
      >
        <el-option
          v-for="(meta, key) in EVENT_CATEGORY_MAP"
          :key="key"
          :label="meta.label"
          :value="key"
        >
          <span class="type-dot" :style="{ background: meta.color }"></span>
          <span>{{ meta.label }}</span>
        </el-option>
      </el-select>

      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        class="date-filter"
        @change="loadEvents"
      />

      <el-button :icon="Refresh" @click="loadEvents">刷新</el-button>
      <span class="timeline-total">共 {{ total }} 条事件</span>
    </div>

    <div v-if="loadError" class="timeline-error" role="alert">
      <span>事件记录加载失败。</span>
      <el-button link type="primary" @click="loadEvents">重新加载</el-button>
    </div>

    <!-- 时间线 -->
    <div v-loading="loading" class="timeline-body">
      <EmptyState v-if="!loading && groupedEvents.length === 0" text="暂无事件记录" icon="Clock" compact />

      <template v-else>
        <div v-for="group in groupedEvents" :key="group.date" class="timeline-group">
          <div class="group-header">
            <span class="group-date">{{ group.date }}</span>
            <span class="group-count">{{ group.items.length }} 条</span>
          </div>
          <el-timeline class="timeline-list">
            <el-timeline-item
              v-for="event in group.items"
              :key="event.id"
              :timestamp="formatTime(event.timestamp)"
              placement="top"
              :color="getEventColor(event.type)"
              :hollow="false"
            >
              <div class="event-card">
                <div class="event-header">
                  <el-tag
                    :color="getEventColor(event.type)"
                    effect="dark"
                    size="small"
                    class="event-tag"
                  >
                    {{ getEventLabel(event.type) }}
                  </el-tag>
                  <span class="event-title">{{ event.title }}</span>
                </div>
                <p v-if="event.description" class="event-desc">{{ event.description }}</p>
                <div class="event-footer">
                  <span v-if="event.project_name" class="event-project">
                    <el-icon><Folder /></el-icon>
                    {{ event.project_name }}
                    <template v-if="event.project_code">（{{ event.project_code }}）</template>
                  </span>
                  <span v-if="event.operator_name" class="event-operator">
                    <el-icon><User /></el-icon>
                    {{ event.operator_name }}
                  </span>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Refresh, Folder, User } from '@element-plus/icons-vue'
import { getTimelineEvents, type TimelineEvent } from '@/api/dashboard'
import { formatDateTime } from '@/utils/format'
import EmptyState from '@/components/EmptyState.vue'

/**
 * 项目统一时间线组件
 * 展示项目相关事件，按日期分组，支持事件类型与日期范围筛选
 */

const props = defineProps<{
  /** 项目 ID，不传则查全局 */
  projectId?: number
}>()

type EventCategoryKey = 'stage' | 'task' | 'competition' | 'expense' | 'file' | 'ip' | 'contribution'

interface EventCategoryMeta {
  label: string
  color: string
  types: readonly string[]
}

interface EventTypeMeta {
  label: string
  category: EventCategoryKey
}

// 筛选按业务分类呈现，请求时展开成后端的精确事件类型。
const EVENT_CATEGORY_MAP: Record<EventCategoryKey, EventCategoryMeta> = {
  stage: { label: '阶段', color: '#176B73', types: ['stage_change'] },
  task: { label: '任务', color: '#237A55', types: ['task_created', 'task_completed'] },
  competition: {
    label: '比赛',
    color: '#A66116',
    types: [
      'competition_register',
      'competition_material',
      'competition_review',
      'competition_defense',
      'competition_result',
    ],
  },
  expense: { label: '经费', color: '#B64242', types: ['expense'] },
  file: { label: '文件', color: '#6C7874', types: ['file_upload'] },
  ip: {
    label: '知识产权',
    color: '#76559B',
    types: ['ip_submit', 'ip_accepted', 'ip_authorized', 'ip_return'],
  },
  contribution: { label: '贡献', color: '#315C86', types: ['contribution'] },
}

// API 返回的 15 种精确事件类型均在此转换为中文标签。
const EVENT_TYPE_MAP: Record<string, EventTypeMeta> = {
  stage_change: { label: '阶段变更', category: 'stage' },
  task_created: { label: '任务创建', category: 'task' },
  task_completed: { label: '任务完成', category: 'task' },
  competition_register: { label: '比赛报名截止', category: 'competition' },
  competition_material: { label: '比赛材料截止', category: 'competition' },
  competition_review: { label: '比赛网评', category: 'competition' },
  competition_defense: { label: '比赛答辩', category: 'competition' },
  competition_result: { label: '比赛结果', category: 'competition' },
  expense: { label: '经费支出', category: 'expense' },
  file_upload: { label: '文件上传', category: 'file' },
  ip_submit: { label: '知识产权提交', category: 'ip' },
  ip_accepted: { label: '知识产权受理', category: 'ip' },
  ip_authorized: { label: '知识产权授权', category: 'ip' },
  ip_return: { label: '知识产权退回', category: 'ip' },
  contribution: { label: '贡献', category: 'contribution' },
}

// 状态
const loading = ref(false)
const loadError = ref(false)
const events = ref<TimelineEvent[]>([])
const total = ref(0)
const selectedCategories = ref<EventCategoryKey[]>([])
const dateRange = ref<[string, string] | null>(null)

// 获取事件颜色
function getEventColor(type: string): string {
  const category = EVENT_TYPE_MAP[type]?.category
  return category ? EVENT_CATEGORY_MAP[category].color : '#176B73'
}

// 获取事件标签
function getEventLabel(type: string): string {
  return EVENT_TYPE_MAP[type]?.label || '其他事件'
}

// 时间格式化
function formatTime(timestamp: string | null): string {
  if (!timestamp) return ''
  return formatDateTime(timestamp)
}

// 按日期分组
const groupedEvents = computed(() => {
  const groups: { date: string; items: TimelineEvent[] }[] = []
  const map = new Map<string, TimelineEvent[]>()

  for (const event of events.value) {
    const date = event.date || '未知日期'
    if (!map.has(date)) {
      map.set(date, [])
    }
    map.get(date)!.push(event)
  }

  // 按日期降序排列
  const sortedDates = Array.from(map.keys()).sort((a, b) => (a < b ? 1 : -1))
  for (const date of sortedDates) {
    const items = map.get(date) || []
    // 同一天内按时间戳倒序
    items.sort((x, y) => {
      const tx = x.timestamp || ''
      const ty = y.timestamp || ''
      return tx < ty ? 1 : -1
    })
    groups.push({ date, items })
  }
  return groups
})

// 加载事件
async function loadEvents(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const params: Record<string, any> = { limit: 200 }
    if (props.projectId) {
      params.project_id = props.projectId
    }
    if (selectedCategories.value.length > 0) {
      const eventTypes = selectedCategories.value.flatMap(
        (category) => EVENT_CATEGORY_MAP[category].types,
      )
      params.event_type = eventTypes.join(',')
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await getTimelineEvents(params)
    events.value = res.events || []
    total.value = res.total || 0
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

// 监听项目 ID 变化
watch(
  () => props.projectId,
  () => {
    loadEvents()
  }
)

onMounted(() => {
  loadEvents()
})
</script>

<style lang="scss" scoped>
.project-timeline {
  .timeline-toolbar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 16px;

    .timeline-total {
      margin-left: auto;
      font-size: 12px;
      color: var(--color-text-muted);
    }
  }

  .event-type-filter,
  .date-filter { width: 260px; }

  .timeline-error {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    padding: 9px 11px;
    color: #7f3030;
    font-size: 12px;
    background: var(--danger-light);
    border: 1px solid #efcfcd;
    border-radius: var(--radius-sm);
  }

  .timeline-body {
    min-height: 200px;
  }

  .timeline-group {
    margin-bottom: 8px;

    .group-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 12px;
      background: var(--color-surface-subtle);
      border: 1px solid var(--color-border-light);
      border-radius: var(--radius-sm);
      margin-bottom: 12px;
      position: sticky;
      top: 0;
      z-index: 1;

      .group-date {
        font-size: 14px;
        font-weight: 600;
        color: var(--color-text);
      }

      .group-count {
        font-size: 12px;
        color: var(--color-text-muted);
      }
    }
  }

  .timeline-list {
    padding-left: 8px;
  }

  .event-card {
    padding: 10px 14px;
    background: var(--color-surface);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-sm);
    transition: border-color var(--transition-fast), background var(--transition-fast);

    &:hover {
      background: var(--color-surface-subtle);
      border-color: var(--color-border);
    }

    .event-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 6px;

      .event-tag {
        border: none;
        color: #fff;
      }

      .event-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--color-text);
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .event-desc {
      font-size: 13px;
      color: var(--color-text-regular);
      margin: 6px 0;
      line-height: 1.5;
    }

    .event-footer {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      margin-top: 8px;
      font-size: 12px;
      color: var(--color-text-muted);

      .event-project,
      .event-operator {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
    }
  }
}

.type-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
}

@media screen and (max-width: 768px) {
  .project-timeline {
    .timeline-toolbar {
      align-items: stretch;
    }

    .event-type-filter,
    .date-filter {
      width: 100%;
    }

    .timeline-total {
      display: flex;
      align-items: center;
      margin-left: 0;
    }

    .timeline-list {
      padding-left: 0;
    }

    .event-card {
      padding: 10px;
    }
  }
}
</style>
