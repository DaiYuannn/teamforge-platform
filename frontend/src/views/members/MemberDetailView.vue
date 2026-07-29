<template>
  <div class="page-container member-detail-page">
    <PageHeader title="成员详情" subtitle="团队成员资料、项目参与和成长记录">
      <template #actions>
        <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
        <el-button
          v-if="member"
          type="primary"
          plain
          :icon="Lock"
          @click="openSensitiveCenter"
        >
          敏感资料
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="成员详情暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <div v-loading="loading" class="detail-content">
      <section class="profile-surface" aria-labelledby="profile-name">
        <header class="profile-header">
          <AvatarWithName
            :name="memberName"
            :avatar-url="member?.avatar"
            :size="58"
            :show-name="false"
          />
          <div class="profile-identity">
            <div class="profile-name-row">
              <h2 id="profile-name">{{ memberName }}</h2>
              <el-tag :type="roleTagType(member?.global_role) as any" size="small">
                {{ member?.global_role_display || '未设置角色' }}
              </el-tag>
              <el-tag :type="membershipStatusType(member?.membership_status) as any" size="small" effect="plain">
                {{ membershipStatusLabel(member?.membership_status) }}
              </el-tag>
            </div>
            <p>{{ member?.email || '未填写邮箱' }}</p>
          </div>
        </header>

        <dl class="profile-details">
          <div>
            <dt>学校</dt>
            <dd>{{ member?.school || '-' }}</dd>
          </div>
          <div>
            <dt>年级</dt>
            <dd>{{ member?.grade || '-' }}</dd>
          </div>
          <div>
            <dt>专业</dt>
            <dd>{{ member?.major || '-' }}</dd>
          </div>
          <div>
            <dt>联系电话</dt>
            <dd>{{ member?.phone || '-' }}</dd>
          </div>
          <div>
            <dt>加入时间</dt>
            <dd>{{ displayDate(member?.team_joined_at || member?.date_joined) }}</dd>
          </div>
          <div>
            <dt>所属小组</dt>
            <dd>{{ teamMembershipText }}</dd>
          </div>
          <div v-if="member?.team_left_at">
            <dt>离队时间</dt>
            <dd>{{ displayDate(member.team_left_at) }}</dd>
          </div>
        </dl>

        <dl class="summary-strip" aria-label="成员统计摘要">
          <div>
            <dt>参与项目</dt>
            <dd>{{ member?.project_count ?? 0 }}</dd>
          </div>
          <div>
            <dt>成员类型</dt>
            <dd class="summary-text">{{ member?.is_student ? '学生' : '非学生' }}</dd>
          </div>
          <div>
            <dt>贡献总数</dt>
            <dd>{{ timelineData?.contrib_summary.total ?? 0 }}</dd>
          </div>
          <div>
            <dt>待审核</dt>
            <dd :class="{ 'is-warning': (timelineData?.contrib_summary.pending || 0) > 0 }">
              {{ timelineData?.contrib_summary.pending ?? 0 }}
            </dd>
          </div>
          <div>
            <dt>已通过</dt>
            <dd class="is-success">{{ timelineData?.contrib_summary.approved ?? 0 }}</dd>
          </div>
          <div>
            <dt>总权重</dt>
            <dd>{{ timelineData?.contrib_summary.total_weight ?? 0 }}</dd>
          </div>
        </dl>
      </section>

      <section class="detail-surface" aria-labelledby="member-projects-title">
        <header class="section-heading">
          <div>
            <h2 id="member-projects-title">参与项目</h2>
            <p>{{ member?.projects?.length || 0 }} 个项目</p>
          </div>
        </header>

        <el-table v-if="!isMobile" :data="member?.projects || []" table-layout="fixed" size="small">
          <template #empty>
            <EmptyState text="暂无参与项目" compact />
          </template>
          <el-table-column label="项目" min-width="220">
            <template #default="{ row }">
              <div class="project-name-cell">
                <strong>{{ row.project_name }}</strong>
                <span>{{ row.project_code || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="role_in_project_display" label="项目角色" width="140" />
          <el-table-column label="参与状态" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="projectMembershipStatusType(row.membership_status)">
                {{ row.membership_status_display || projectMembershipStatusLabel(row.membership_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="项目状态" width="110">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.project_status || '-' }}</el-tag>
            </template>
          </el-table-column>
        </el-table>

        <div v-else class="mobile-project-list">
          <EmptyState v-if="!member?.projects?.length" text="暂无参与项目" compact />
          <article v-for="project in member?.projects || []" :key="project.project_id">
            <div>
              <strong>{{ project.project_name }}</strong>
              <span>{{ project.project_code || '-' }}</span>
            </div>
            <div class="mobile-project-meta">
              <span>{{ project.role_in_project_display || '-' }}</span>
              <el-tag size="small" :type="projectMembershipStatusType(project.membership_status)">
                {{ project.membership_status_display || projectMembershipStatusLabel(project.membership_status) }}
              </el-tag>
              <el-tag size="small" type="info">{{ project.project_status || '-' }}</el-tag>
            </div>
          </article>
        </div>
      </section>

      <section class="detail-surface" aria-labelledby="member-competitions-title">
        <header class="section-heading">
          <div>
            <h2 id="member-competitions-title">精确参赛记录</h2>
            <p>{{ member?.competition_participations?.length || 0 }} 条报名队记录</p>
          </div>
        </header>

        <el-table
          v-if="!isMobile"
          :data="member?.competition_participations || []"
          table-layout="fixed"
          size="small"
        >
          <template #empty>
            <EmptyState text="暂无精确参赛记录" compact />
          </template>
          <el-table-column label="比赛届次" min-width="180">
            <template #default="{ row }">
              <div class="project-name-cell">
                <strong>{{ row.event_name || row.competition_name }}</strong>
                <span>{{ [row.event_edition, row.event_organizer].filter(Boolean).join(' · ') || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="项目 / 参赛条目" min-width="190">
            <template #default="{ row }">
              <div class="project-name-cell">
                <strong>{{ row.project_name }}</strong>
                <span>{{ row.entry_name || row.project_code || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="role_display" label="参赛身份" width="112" />
          <el-table-column label="参与状态" width="108">
            <template #default="{ row }">
              <el-tag size="small" :type="competitionStatusType(row.participation_status)">
                {{ row.participation_status_display }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="具体分工" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.responsibility || '尚未填写具体分工' }}</template>
          </el-table-column>
        </el-table>

        <div v-else class="mobile-project-list">
          <EmptyState
            v-if="!member?.competition_participations?.length"
            text="暂无精确参赛记录"
            compact
          />
          <article
            v-for="record in member?.competition_participations || []"
            :key="record.participant_id"
          >
            <div>
              <strong>{{ record.event_name || record.competition_name }}</strong>
              <span>{{ [record.event_edition, record.project_name, record.entry_name].filter(Boolean).join(' · ') }}</span>
            </div>
            <p>{{ record.responsibility || '尚未填写具体分工' }}</p>
            <div class="mobile-project-meta">
              <span>{{ record.role_display }}</span>
              <el-tag size="small" :type="competitionStatusType(record.participation_status)">
                {{ record.participation_status_display }}
              </el-tag>
            </div>
          </article>
        </div>
      </section>

      <section class="detail-surface" aria-labelledby="growth-title">
        <header class="section-heading">
          <div>
            <h2 id="growth-title">成长时间线</h2>
            <p>{{ timelineData?.total_events || 0 }} 条记录</p>
          </div>
        </header>

        <div v-loading="timelineLoading" class="timeline-content">
          <el-timeline v-if="timelineData?.events?.length" class="growth-timeline">
            <el-timeline-item
              v-for="event in timelineData.events"
              :key="event.id"
              :timestamp="displayDate(event.date)"
              placement="top"
              :color="eventColor(event.type)"
            >
              <article class="growth-event">
                <header>
                  <strong>{{ event.title }}</strong>
                  <el-tag size="small" effect="light" :type="eventTagType(event.type) as any">
                    {{ eventTypeLabel(event.type) }}
                  </el-tag>
                </header>
                <p v-if="event.description">{{ event.description }}</p>
                <span v-if="event.project_name" class="growth-project">
                  <el-icon><Folder /></el-icon>
                  {{ event.project_name }}
                </span>
              </article>
            </el-timeline-item>
          </el-timeline>
          <EmptyState v-else-if="!timelineLoading" text="暂无成长记录" compact />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Folder, Lock } from '@element-plus/icons-vue'
import { getGrowthTimeline, getMember, type GrowthTimelineData } from '@/api/members'
import { formatDate } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import type { Member } from '@/types'
import AvatarWithName from '@/components/AvatarWithName.vue'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const { isMobile } = useDevice()
const memberId = Number(route.params.id)
const loading = ref(false)
const timelineLoading = ref(false)
const loadFailed = ref(false)
const member = ref<Member | null>(null)
const timelineData = ref<GrowthTimelineData | null>(null)

const memberName = computed(
  () => member.value?.name || member.value?.user_name || member.value?.username || '成员',
)
const teamMembershipText = computed(() => {
  const memberships = member.value?.team_memberships || []
  return memberships.length
    ? memberships.map((item) => `${item.team_name}（${item.role_display}）`).join('、')
    : '未分组'
})

function openSensitiveCenter(): void {
  if (!member.value) return
  const firstActiveTeam = member.value.team_memberships?.find(
    (item) => item.status === 'active',
  )
  void router.push({
    name: 'SensitiveCenter',
    query: {
      tab: 'my-data',
      subject_user: String(member.value.id),
      subject_name: memberName.value,
      ...(firstActiveTeam ? { team: String(firstActiveTeam.team_id) } : {}),
    },
  })
}

const EVENT_TYPE_LABEL: Record<string, string> = {
  contribution: '贡献',
  project_join: '加入项目',
  competition: '比赛',
  ip_contribution: '知识产权',
  task_completed: '任务完成',
  member_status: '成员状态',
  project_membership: '项目成员变动',
}

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '-'
}

function roleTagType(role?: string): string {
  if (role === 'sys_admin') return 'danger'
  if (role === 'teacher') return 'warning'
  return 'info'
}

function membershipStatusLabel(value?: string): string {
  return {
    active: '在队',
    on_leave: '暂离',
    exited: '已离队',
    external: '外部协作者',
  }[value || 'active'] || '在队'
}

function membershipStatusType(value?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (value === 'exited') return 'danger'
  if (value === 'on_leave') return 'warning'
  if (value === 'external') return 'info'
  return 'success'
}

function projectMembershipStatusLabel(value?: string): string {
  return { active: '参与中', on_leave: '暂离', exited: '已退出' }[value || 'active'] || '参与中'
}

function projectMembershipStatusType(value?: string): 'success' | 'warning' | 'info' {
  if (value === 'on_leave') return 'warning'
  if (value === 'exited') return 'info'
  return 'success'
}

function competitionStatusType(value?: string): 'success' | 'warning' | 'info' {
  if (value === 'planned') return 'warning'
  if (value === 'withdrawn') return 'info'
  return 'success'
}

function eventTypeLabel(type: string): string {
  return EVENT_TYPE_LABEL[type] || type
}

function eventTagType(type: string): string {
  if (type === 'project_join' || type === 'task_completed') return 'success'
  if (type === 'member_status' || type === 'project_membership') return 'warning'
  if (type === 'competition') return 'warning'
  if (type === 'ip_contribution') return 'info'
  return ''
}

function eventColor(type: string): string {
  if (type === 'project_join' || type === 'task_completed') return 'var(--color-success)'
  if (type === 'member_status' || type === 'project_membership') return 'var(--color-warning)'
  if (type === 'competition') return 'var(--color-warning)'
  if (type === 'ip_contribution') return 'var(--ip-color)'
  return 'var(--color-primary)'
}

async function loadTimeline(userId: number): Promise<void> {
  timelineLoading.value = true
  try {
    timelineData.value = await getGrowthTimeline(userId)
  } catch {
    timelineData.value = null
  } finally {
    timelineLoading.value = false
  }
}

async function loadData(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    member.value = await getMember(memberId)
    await loadTimeline(member.value.id)
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.load-alert {
  margin-bottom: 12px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 240px;
}

.profile-surface,
.detail-surface {
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px;
}

.profile-identity {
  min-width: 0;

  > p {
    margin-top: 4px;
    overflow: hidden;
    color: var(--color-text-muted);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.profile-name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;

  h2 {
    overflow-wrap: anywhere;
    color: var(--color-text);
    font-size: 20px;
    font-weight: 600;
    line-height: 1.35;
    letter-spacing: 0;
  }
}

.profile-details {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  padding: 16px 18px;
  background: var(--color-surface-subtle);
  border-top: 1px solid var(--color-border-light);

  dt,
  .summary-strip dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 3px;
    overflow-wrap: anywhere;
    color: var(--color-text-regular);
    font-size: 13px;
  }
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  border-top: 1px solid var(--color-border-light);

  > div {
    min-width: 0;
    padding: 14px 18px;
    border-left: 1px solid var(--color-border-light);

    &:first-child {
      border-left: 0;
    }
  }

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 3px;
    color: var(--color-text);
    font-size: 20px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;

    &.summary-text {
      font-size: 14px;
    }

    &.is-warning {
      color: var(--color-warning);
    }

    &.is-success {
      color: var(--color-success);
    }
  }
}

.section-heading {
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border-light);

  h2 {
    color: var(--color-text);
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0;
  }

  p {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
}

.project-name-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;

  strong {
    color: var(--color-text);
    font-weight: 600;
  }

  span {
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.mobile-project-list {
  padding: 0 14px;

  article {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 0;
    border-bottom: 1px solid var(--color-border-light);

    &:last-child {
      border-bottom: 0;
    }

    > div:first-child {
      display: flex;
      flex-direction: column;
      min-width: 0;

      strong {
        overflow-wrap: anywhere;
        color: var(--color-text);
        font-size: 13px;
      }

      span {
        margin-top: 2px;
        color: var(--color-text-muted);
        font-size: 11px;
      }
    }
  }
}

.mobile-project-meta {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  flex: 0 0 auto;
  gap: 5px;
  color: var(--color-text-regular);
  font-size: 12px;
}

.timeline-content {
  min-height: 132px;
  padding: 18px 18px 4px;
}

.growth-timeline {
  padding: 2px 0 0 4px;
}

.growth-event {
  padding-bottom: 8px;

  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;

    strong {
      min-width: 0;
      overflow-wrap: anywhere;
      color: var(--color-text);
      font-size: 14px;
      font-weight: 600;
    }
  }

  > p {
    margin-top: 6px;
    color: var(--color-text-regular);
    font-size: 13px;
    line-height: 1.55;
  }
}

.growth-project {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

@media screen and (max-width: 900px) {
  .summary-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));

    > div:nth-child(4) {
      border-left: 0;
    }

    > div:nth-child(n + 4) {
      border-top: 1px solid var(--color-border-light);
    }
  }
}

@media screen and (max-width: 768px) {
  .profile-header {
    padding: 16px 14px;
  }

  .profile-details {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 14px;
  }

  .summary-strip > div {
    padding: 12px;
  }

  .summary-strip dd {
    font-size: 18px;
  }

  .section-heading {
    padding: 13px 14px;
  }

  .timeline-content {
    padding: 16px 14px 2px;
  }
}

@media screen and (max-width: 420px) {
  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));

    > div:nth-child(odd) {
      border-left: 0;
    }

    > div:nth-child(n + 3) {
      border-top: 1px solid var(--color-border-light);
    }
  }
}
</style>
