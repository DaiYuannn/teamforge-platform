<template>
  <div class="project-timeline">
    <!-- 顶部筛选栏 -->
    <div class="timeline-toolbar">
      <el-select
        v-model="selectedTypes"
        multiple
        collapse-tags
        collapse-tags-tooltip
        clearable
        placeholder="筛选事件类型"
        style="width: 280px"
        @change="loadEvents"
      >
        <el-option
          v-for="(meta, key) in EVENT_TYPE_MAP"
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
        style="width: 280px"
        @change="loadEvents"
      />

      <el-button type="primary" :icon="Refresh" @click="loadEvents">刷新</el-button>
      <span class="timeline-total">共 {{ total }} 条事件</span>
    </div>

    <!-- 时间线 -->
    <div v-loading="loading" class="timeline-body">
      <el-empty v-if="!loading && groupedEvents.length === 0" description="暂无事件记录" />

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

/**
 * 项目统一时间线组件
 * 展示项目相关事件，按日期分组，支持事件类型与日期范围筛选
 */

const props = defineProps<{
  /** 项目 ID，不传则查全局 */
  projectId?: number
}>()

// 事件类型映射：颜色 + 标签
const EVENT_TYPE_MAP: Record<string, { label: string; color: string }> = {
  stage_change: { label: '阶段变更', color: '#409EFF' },
  task: { label: '任务', color: '#67C23A' },
  competition: { label: '比赛', color: '#E6A23C' },
  expense: { label: '经费', color: '#F56C6C' },
  file: { label: '文件', color: '#909399' },
  ip: { label: '知识产权', color: '#9B59B6' },
  contribution: { label: '贡献', color: '#36CFC9' },
}

// 状态
const loading = ref(false)
const events = ref<TimelineEvent[]>([])
const total = ref(0)
const selectedTypes = ref<string[]>([])
const dateRange = ref<[string, string] | null>(null)

// 获取事件颜色
function getEventColor(type: string): string {
  return EVENT_TYPE_MAP[type]?.color || '#409EFF'
}

// 获取事件标签
function getEventLabel(type: string): string {
  return EVENT_TYPE_MAP[type]?.label || type
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
  try {
    const params: Record<string, any> = { limit: 200 }
    if (props.projectId) {
      params.project_id = props.projectId
    }
    if (selectedTypes.value.length > 0) {
      params.event_type = selectedTypes.value.join(',')
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await getTimelineEvents(params)
    events.value = res.events || []
    total.value = res.total || 0
  } catch {
    // 错误已由拦截器处理
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
    gap: 12px;
    margin-bottom: 16px;

    .timeline-total {
      margin-left: auto;
      font-size: 13px;
      color: #909399;
    }
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
      background: #f5f7fa;
      border-radius: 6px;
      margin-bottom: 12px;
      position: sticky;
      top: 0;
      z-index: 1;

      .group-date {
        font-size: 14px;
        font-weight: 600;
        color: #303133;
      }

      .group-count {
        font-size: 12px;
        color: #909399;
      }
    }
  }

  .timeline-list {
    padding-left: 8px;
  }

  .event-card {
    padding: 10px 14px;
    background: #fff;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    transition: box-shadow 0.2s ease;

    &:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
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
        color: #303133;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .event-desc {
      font-size: 13px;
      color: #606266;
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
      color: #909399;

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
</style>
