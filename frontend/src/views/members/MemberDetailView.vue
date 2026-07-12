<template>
  <div class="page-container">
    <!-- 返回按钮 -->
    <div class="detail-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      <h2 class="detail-title">成员详情</h2>
    </div>

    <div v-loading="loading">
      <!-- 基本信息 -->
      <div class="card">
        <div class="member-header">
          <AvatarWithName
            :name="member?.name || ''"
            :avatar-url="member?.avatar"
            :size="64"
            :show-name="false"
          />
          <div class="member-info">
            <h3>{{ member?.name }}</h3>
            <p>{{ member?.email }}</p>
          </div>
        </div>
        <el-descriptions :column="2" border class="mt-16">
          <el-descriptions-item label="角色">{{ member?.global_role_display || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="年级">{{ member?.grade || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="专业">{{ member?.major || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="联系方式">{{ member?.phone || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ member?.email || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="加入时间">{{ member?.date_joined ? formatDate(member.date_joined) : '暂无数据' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 参与项目 -->
      <div class="card mt-16">
        <h3 class="section-title">参与项目</h3>
        <el-table :data="member?.projects || []" border size="small">
          <el-table-column prop="project_name" label="项目名称" min-width="200" />
          <el-table-column prop="role_in_project_display" label="项目角色" width="150" />
        </el-table>
        <el-empty v-if="!member?.projects?.length" description="暂无参与项目" :image-size="60" />
      </div>

      <!-- 统计信息 -->
      <div class="card mt-16">
        <h3 class="section-title">统计信息</h3>
        <el-row :gutter="16">
          <el-col :span="8">
            <div class="task-stat-card">
              <div class="stat-value">{{ member?.project_count ?? '暂无数据' }}</div>
              <div class="stat-label">参与项目数</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="task-stat-card">
              <div class="stat-value">{{ member?.is_student ? '是' : '否' }}</div>
              <div class="stat-label">是否学生</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="task-stat-card">
              <div class="stat-value">{{ member?.date_joined ? formatDate(member.date_joined) : '暂无数据' }}</div>
              <div class="stat-label">加入时间</div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 贡献汇总 -->
      <div class="card mt-16">
        <h3 class="section-title">贡献汇总</h3>
        <el-row :gutter="16">
          <el-col :xs="12" :sm="6">
            <div class="task-stat-card">
              <div class="stat-value stat-blue">{{ timelineData?.contrib_summary.total ?? 0 }}</div>
              <div class="stat-label">总贡献数</div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="task-stat-card">
              <div class="stat-value stat-green">{{ timelineData?.contrib_summary.approved ?? 0 }}</div>
              <div class="stat-label">已通过</div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="task-stat-card">
              <div class="stat-value stat-orange">{{ timelineData?.contrib_summary.pending ?? 0 }}</div>
              <div class="stat-label">待审核</div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="task-stat-card">
              <div class="stat-value stat-purple">{{ timelineData?.contrib_summary.total_weight ?? 0 }}</div>
              <div class="stat-label">总权重</div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 成长时间线 -->
      <div class="card mt-16">
        <h3 class="section-title">成长时间线</h3>
        <el-timeline v-if="timelineData?.events?.length" class="growth-timeline">
          <el-timeline-item
            v-for="event in timelineData.events"
            :key="event.id"
            :timestamp="event.date ? formatDate(event.date) : '-'"
            placement="top"
            :color="getEventColor(event.type)"
          >
            <div class="growth-event">
              <div class="growth-event-header">
                <span class="growth-event-title">{{ event.title }}</span>
                <el-tag
                  size="small"
                  effect="light"
                  :style="{ color: getEventColor(event.type), borderColor: getEventColor(event.type) }"
                >
                  {{ getEventTypeLabel(event.type) }}
                </el-tag>
              </div>
              <p v-if="event.description" class="growth-event-desc">{{ event.description }}</p>
              <div v-if="event.project_name" class="growth-event-project">
                <el-icon><Folder /></el-icon>
                <span>{{ event.project_name }}</span>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无成长记录" :image-size="60" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Folder } from '@element-plus/icons-vue'
import { getMember, getGrowthTimeline } from '@/api/members'
import { formatDate } from '@/utils/format'
import type { Member } from '@/types'
import type { GrowthTimelineData } from '@/api/members'
import AvatarWithName from '@/components/AvatarWithName.vue'

const route = useRoute()
const memberId = Number(route.params.id)

const loading = ref(false)
const member = ref<Member | null>(null)
const timelineData = ref<GrowthTimelineData | null>(null)

// 事件类型颜色映射
const EVENT_COLOR_MAP: Record<string, string> = {
  contribution: '#409EFF', // 蓝色
  project_join: '#67C23A', // 绿色
  competition: '#E6A23C', // 橙色
  ip_contribution: '#9B59B6', // 紫色
  task_completed: '#36CFC9', // 青色
}

// 事件类型标签映射
const EVENT_TYPE_LABEL: Record<string, string> = {
  contribution: '贡献',
  project_join: '加入项目',
  competition: '比赛',
  ip_contribution: '知识产权',
  task_completed: '任务完成',
}

/** 获取事件颜色 */
function getEventColor(type: string): string {
  return EVENT_COLOR_MAP[type] || '#909399'
}

/** 获取事件类型标签 */
function getEventTypeLabel(type: string): string {
  return EVENT_TYPE_LABEL[type] || type
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    member.value = await getMember(memberId)
    // 加载成长时间线（需要 user_id）
    const userId = member.value?.user
    if (userId) {
      loadTimeline(userId)
    }
  } catch {
    // 已处理
  } finally {
    loading.value = false
  }
}

async function loadTimeline(userId: number): Promise<void> {
  try {
    timelineData.value = await getGrowthTimeline(userId)
  } catch {
    // 忽略时间线加载错误
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;

  .detail-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.mt-16 { margin-top: 16px; }

.member-header {
  display: flex;
  align-items: center;
  gap: 16px;

  .member-info {
    h3 {
      font-size: 20px;
      color: #303133;
      margin: 0 0 4px 0;
    }
    p {
      font-size: 14px;
      color: #909399;
      margin: 0;
    }
  }
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.task-stat-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 24px;
  text-align: center;

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #409eff;

    &.stat-blue { color: #409eff; }
    &.stat-green { color: #67c23a; }
    &.stat-orange { color: #e6a23c; }
    &.stat-purple { color: #9b59b6; }
  }
  .stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 4px;
  }
}

/* ==================== 成长时间线 ==================== */
.growth-timeline {
  padding: 8px 8px 8px 0;

  .growth-event {
    .growth-event-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 4px;

      .growth-event-title {
        font-size: 14px;
        font-weight: 600;
        color: #303133;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .growth-event-desc {
      font-size: 13px;
      color: #606266;
      margin: 4px 0;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .growth-event-project {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #909399;
      margin-top: 4px;
    }
  }
}
</style>
