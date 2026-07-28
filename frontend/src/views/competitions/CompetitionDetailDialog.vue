<template>
  <el-dialog
    v-model="dialogVisible"
    class="competition-detail-dialog"
    title="比赛全流程详情"
    :width="dialogWidth"
    destroy-on-close
  >
    <template v-if="competition">
      <header class="detail-hero">
        <div>
          <p>{{ competition.project_name || '未命名项目' }}</p>
          <h2>{{ competition.name }}</h2>
          <span>{{ competition.organizer || '主办方待补充' }}</span>
        </div>
        <div class="hero-tags">
          <el-tag
            :type="getCompetitionStageTagType(competition.level) as any"
            :style="getCompetitionStageTagStyle(competition.level)"
          >
            {{ getCompetitionLevelLabel(competition.level) }}
          </el-tag>
          <el-tag :type="getCompetitionStatusTagType(competition.status) as any">
            {{ getCompetitionStatusLabel(competition.status) }}
          </el-tag>
        </div>
      </header>

      <section class="detail-section">
        <h3>流程概况</h3>
        <el-descriptions :column="descriptionColumns" border>
          <el-descriptions-item label="所属小团队">
            {{ projectTeamNames || '未关联小团队' }}
          </el-descriptions-item>
          <el-descriptions-item label="项目牵头负责人">
            {{ projectLeaderNames || '待补充' }}
          </el-descriptions-item>
          <el-descriptions-item label="比赛执行负责人">
            {{ competitionLeaderNames || '待指定' }}
          </el-descriptions-item>
          <el-descriptions-item label="实际参赛人数">
            {{ competition.participant_count || activeParticipants.length }} 人
          </el-descriptions-item>
          <el-descriptions-item label="比赛类型">
            {{ competition.comp_type || '未填写' }}
          </el-descriptions-item>
          <el-descriptions-item label="当前阶段">
            {{ competition.current_stage || '未填写' }}
          </el-descriptions-item>
          <el-descriptions-item label="晋级结果">
            <el-tag :type="competition.is_promoted ? 'success' : 'info'" size="small">
              {{ competition.is_promoted ? '已晋级' : '未晋级 / 待定' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="获奖结果">
            <el-tag :type="competition.is_awarded ? 'warning' : 'info'" size="small">
              {{ competition.is_awarded ? competition.award_level || '已获奖' : '未获奖 / 待定' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </section>

      <section class="detail-section">
        <h3>全流程节点</h3>
        <div class="milestone-grid">
          <div v-for="item in milestones" :key="item.key" class="milestone-item">
            <span>{{ item.label }}</span>
            <strong>{{ displayDate(item.value) }}</strong>
          </div>
        </div>
      </section>

      <section class="detail-section">
        <div class="section-heading">
          <div>
            <h3>比赛执行负责人和实际参赛名单</h3>
            <p>项目牵头负责人负责项目归属，比赛执行负责人负责本场比赛；名单逐人展示实际分工和已登记贡献。</p>
          </div>
        </div>
        <div v-if="participants.length" class="participant-list">
          <div
            v-for="participant in participants"
            :key="participant.id"
            class="participant-item"
            :class="{ 'is-withdrawn': participant.participation_status === 'withdrawn' }"
          >
            <div>
              <strong>{{ participant.user_detail?.name || `成员 ${participant.user}` }}</strong>
              <span>{{ participant.role_display || participantRoleLabel(participant.role) }}</span>
            </div>
            <p>{{ participant.responsibility || '暂未填写具体分工' }}</p>
            <el-tag size="small" effect="plain">
              {{ participant.participation_status_display || '已确认' }}
            </el-tag>
            <div class="participant-contributions">
              <span>本比赛贡献</span>
              <ul v-if="participantContributions(participant.user).length">
                <li
                  v-for="contribution in participantContributions(participant.user)"
                  :key="contribution.id"
                >
                  <div>
                    <strong>{{ contributionCopy(contribution) }}</strong>
                    <small>
                      {{ contribution.contribution_type_display || contribution.contribution_type }}
                      · {{ contribution.status_display || contribution.status }}
                    </small>
                  </div>
                  <el-tag
                    size="small"
                    effect="plain"
                    :type="contribution.reuse_eligible ? 'success' : 'info'"
                  >
                    {{ contribution.reuse_eligible ? '可复用' : '待确认' }}
                  </el-tag>
                </li>
              </ul>
              <p v-else>暂无单独贡献记录；上方分工是当前执行安排，不等同于已审核贡献。</p>
            </div>
          </div>
        </div>
        <el-empty v-else :image-size="64" description="尚未登记实际参赛成员" />
      </section>

      <section class="detail-section">
        <div class="section-heading">
          <div>
            <h3>可复用的已审核贡献证据</h3>
            <p>仅列出当前参赛成员在可见项目内、已经审核通过且来源已核验的记录。</p>
          </div>
        </div>
        <el-alert
          class="reuse-alert"
          :title="competition.contribution_reuse_note || defaultReuseNote"
          type="info"
          :closable="false"
          show-icon
        />
        <div v-if="reusableContributions.length" class="evidence-list">
          <article
            v-for="contribution in reusableContributions"
            :key="contribution.id"
            class="evidence-item"
          >
            <div class="evidence-item__main">
              <div>
                <strong>{{ contributionCopy(contribution) }}</strong>
                <span>
                  {{ contribution.user_name || `成员 ${contribution.user}` }}
                  · {{ contribution.contribution_type_display || contribution.contribution_type }}
                </span>
              </div>
              <el-tag size="small" type="success" effect="plain">
                {{ contribution.reuse_scope_display }}
              </el-tag>
            </div>
            <dl>
              <div>
                <dt>来源项目</dt>
                <dd>{{ contribution.project_name || `项目 ${contribution.project}` }}</dd>
              </div>
              <div>
                <dt>来源记录</dt>
                <dd>{{ contributionOrigin(contribution) }}</dd>
              </div>
              <div v-if="contribution.proof_file_name">
                <dt>证明材料</dt>
                <dd>{{ contribution.proof_file_name }}</dd>
              </div>
            </dl>
          </article>
        </div>
        <el-empty
          v-else
          :image-size="56"
          description="暂无符合“已审核且来源已核验”的可复用贡献"
        />
      </section>

      <section v-if="competition.not_promoted_reason" class="detail-section">
        <h3>未晋级原因</h3>
        <p class="detail-copy">{{ competition.not_promoted_reason }}</p>
      </section>

      <section class="detail-section narrative-grid">
        <article>
          <h3>评审 / 答辩复盘</h3>
          <p class="detail-copy">{{ competition.review_summary || '暂无复盘记录' }}</p>
        </article>
        <article>
          <h3>改进建议</h3>
          <p class="detail-copy">{{ competition.improvement_suggestion || '暂无改进建议' }}</p>
        </article>
      </section>

      <footer class="detail-meta">
        <span>创建于 {{ displayDateTime(competition.created_at) }}</span>
        <span v-if="competition.updated_at">更新于 {{ displayDateTime(competition.updated_at) }}</span>
      </footer>
    </template>

    <template #footer>
      <el-button v-if="canManage && competition" type="primary" @click="emit('edit', competition)">
        编辑比赛与名单
      </el-button>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDevice } from '@/composables/useDevice'
import {
  formatDate,
  formatDateTime,
  getCompetitionLevelLabel,
  getCompetitionStageTagStyle,
  getCompetitionStageTagType,
  getCompetitionStatusLabel,
  getCompetitionStatusTagType,
} from '@/utils/format'
import type {
  Competition,
  CompetitionContributionEvidence,
} from '@/types'

const props = defineProps<{
  visible: boolean
  competition: Competition | null
  canManage?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'edit', value: Competition): void
}>()

const { isMobile } = useDevice()
const dialogWidth = computed(() => (isMobile.value ? 'calc(100vw - 24px)' : '820px'))
const descriptionColumns = computed(() => (isMobile.value ? 1 : 2))
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})

const milestones = computed(() => {
  const value = props.competition
  if (!value) return []
  return [
    { key: 'register_date', label: '报名日期', value: value.register_date },
    { key: 'material_deadline', label: '材料提交截止', value: value.material_deadline },
    { key: 'review_date', label: '网评日期', value: value.review_date },
    { key: 'defense_date', label: '答辩日期', value: value.defense_date },
    { key: 'school_date', label: '校赛日期', value: value.school_date },
    { key: 'city_date', label: '市赛日期', value: value.city_date },
    { key: 'province_date', label: '省赛日期', value: value.province_date },
    { key: 'national_date', label: '国赛日期', value: value.national_date },
    { key: 'result_date', label: '结果公布', value: value.result_date },
  ]
})

const participants = computed(() => props.competition?.participants || [])
const activeParticipants = computed(() =>
  participants.value.filter((item) => item.participation_status !== 'withdrawn'),
)
const projectLeaderNames = computed(() =>
  props.competition?.project_leader_names?.join('、') || '',
)
const projectTeamNames = computed(() =>
  props.competition?.project_team_names?.join('、') || '',
)
const competitionLeaderNames = computed(() =>
  props.competition?.leader_names?.join('、') || '',
)
const competitionContributions = computed(() =>
  props.competition?.competition_contributions || [],
)
const reusableContributions = computed(() =>
  props.competition?.reusable_contributions || [],
)
const defaultReuseNote = '复用只引用内容和证明材料；原贡献仍归属来源项目，不会自动复制或重复计分。'

function participantContributions(userId: number): CompetitionContributionEvidence[] {
  return competitionContributions.value.filter((item) => item.user === userId)
}

function contributionCopy(contribution: CompetitionContributionEvidence): string {
  return contribution.content
    || contribution.description
    || contribution.contribution_type_display
    || '未填写贡献说明'
}

function contributionOrigin(contribution: CompetitionContributionEvidence): string {
  if (contribution.origin_competition_name) {
    return `比赛：${contribution.origin_competition_name}`
  }
  return contribution.source_type_display || contribution.source_type || '手工登记'
}

function participantRoleLabel(role: string): string {
  return {
    leader: '比赛负责人',
    member: '参赛成员',
    advisor: '指导老师',
  }[role] || role
}

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '待确定'
}

function displayDateTime(value?: string | null): string {
  return value ? formatDateTime(value) : '-'
}
</script>

<style lang="scss" scoped>
.detail-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 18px;
  background:
    linear-gradient(120deg, color-mix(in srgb, var(--color-primary) 9%, transparent), transparent 65%),
    var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  > div:first-child {
    min-width: 0;
  }

  p,
  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  h2 {
    margin: 4px 0;
    color: var(--color-text);
    font-size: 20px;
    font-weight: 650;
    line-height: 1.4;
    overflow-wrap: anywhere;
  }
}

.hero-tags {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
}

.detail-section {
  margin-top: 22px;

  > h3,
  .section-heading h3,
  article > h3 {
    margin-bottom: 10px;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
  }
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;

  h3 {
    margin-bottom: 3px !important;
  }

  p {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 12px;
    line-height: 1.6;
  }
}

.milestone-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.milestone-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 66px;
  padding: 11px 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);

  span {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  strong {
    color: var(--color-text-regular);
    font-size: 13px;
    font-weight: 550;
    font-variant-numeric: tabular-nums;
  }
}

.participant-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.participant-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 12px;
  padding: 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);

  > div {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  strong {
    color: var(--color-text);
    font-size: 13px;
  }

  span,
  p {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  p {
    grid-column: 1 / -1;
    margin: 0;
  }
}

.participant-contributions {
  grid-column: 1 / -1;
  padding-top: 9px;
  border-top: 1px solid var(--color-border-light);

  > span {
    color: var(--color-text-muted);
    font-size: 11px;
    font-weight: 600;
  }

  > p {
    margin-top: 5px;
    color: var(--color-text-muted);
    font-size: 11px;
  }

  ul {
    display: grid;
    gap: 5px;
    padding: 0;
    margin: 6px 0 0;
    list-style: none;
  }

  li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 7px 8px;
    background: var(--color-surface);
    border-radius: 4px;

    > div {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    strong {
      overflow: hidden;
      font-size: 12px;
      font-weight: 550;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      color: var(--color-text-muted);
      font-size: 10px;
    }
  }
}

.participant-item.is-withdrawn {
  opacity: 0.68;
}

.reuse-alert {
  margin-bottom: 10px;
}

.evidence-list {
  display: grid;
  gap: 8px;
}

.evidence-item {
  padding: 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.evidence-item__main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;

  > div {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  strong {
    color: var(--color-text);
    font-size: 13px;
    overflow-wrap: anywhere;
  }

  span {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.evidence-item dl {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  margin: 9px 0 0;

  div {
    display: flex;
    gap: 5px;
    min-width: 0;
  }

  dt,
  dd {
    margin: 0;
    font-size: 11px;
  }

  dt {
    color: var(--color-text-muted);
  }

  dd {
    color: var(--color-text-regular);
    overflow-wrap: anywhere;
  }
}

.narrative-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;

  article {
    min-width: 0;
    padding: 14px;
    background: var(--color-surface-subtle);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-sm);
  }
}

.detail-copy {
  color: var(--color-text-regular);
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.detail-meta {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  padding-top: 14px;
  margin-top: 20px;
  color: var(--color-text-muted);
  font-size: 11px;
  border-top: 1px solid var(--color-border-light);
}

:deep(.el-dialog__body) {
  max-height: min(72vh, 760px);
  overflow-y: auto;
}

@media screen and (max-width: 768px) {
  .detail-hero {
    flex-direction: column;
    padding: 14px;
  }

  .hero-tags {
    width: 100%;
  }

  .milestone-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .narrative-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .participant-list {
    grid-template-columns: minmax(0, 1fr);
  }

  .detail-meta {
    align-items: flex-end;
    flex-direction: column;
    gap: 4px;
  }
}
</style>
