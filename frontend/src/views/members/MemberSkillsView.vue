<template>
  <div class="page-container skills-page">
    <PageHeader
      title="技能与组队"
      subtitle="维护个人技能，查看团队能力分布，并为具体比赛参赛队推荐协作成员"
    />

    <el-tabs v-model="activeView" class="skills-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="我的技能" name="mine">
        <section class="skills-surface" aria-labelledby="my-skills-title">
          <header class="section-heading">
            <div>
              <h2 id="my-skills-title">我的技能</h2>
              <p>{{ mySkills.length }} 项技能</p>
            </div>
            <el-button type="primary" :icon="Plus" @click="handleAddSkill">
              添加技能
            </el-button>
          </header>

          <div v-loading="loading" class="skill-list">
            <EmptyState
              v-if="!loading && mySkills.length === 0"
              text="暂未添加技能"
              description="添加技能并记录当前熟练度"
              compact
            />
            <article v-for="item in mySkills" :key="item.id" class="skill-row">
              <div class="skill-row__identity">
                <span class="skill-mark" aria-hidden="true">
                  <el-icon><Collection /></el-icon>
                </span>
                <div>
                  <strong>{{ skillName(item) }}</strong>
                  <span>熟练度 {{ item.proficiency }} / 5</span>
                </div>
              </div>
              <el-rate :model-value="item.proficiency" disabled />
              <el-tooltip content="移除技能" placement="top">
                <el-button
                  type="danger"
                  link
                  :icon="Delete"
                  aria-label="移除技能"
                  @click="handleDeleteSkill(item)"
                />
              </el-tooltip>
            </article>
          </div>
        </section>

        <section
          v-permission="['sys_admin']"
          class="skills-surface skill-library-surface"
          aria-labelledby="skill-library-title"
        >
          <header class="section-heading">
            <div>
              <h2 id="skill-library-title">技能词库</h2>
              <p>{{ skillTags.length }} 个可用标签</p>
            </div>
            <el-button :icon="Plus" @click="handleCreateTag">添加标签</el-button>
          </header>

          <div v-loading="tagLoading" class="tag-library">
            <EmptyState
              v-if="!tagLoading && skillTags.length === 0"
              text="暂无技能标签"
              compact
            />
            <el-tag
              v-for="tag in skillTags"
              :key="tag.id"
              type="info"
              closable
              @close="handleDeleteTag(tag)"
            >
              {{ tag.name }}
            </el-tag>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="团队技能矩阵" name="matrix">
        <section class="skills-surface" aria-labelledby="team-matrix-title">
          <header class="section-heading matrix-heading">
            <div>
              <h2 id="team-matrix-title">团队技能矩阵</h2>
              <p>
                {{ matrixData?.count || 0 }} 人
                <template v-if="matrixData?.scope.competition">
                  · {{ matrixData.scope.competition.event_name }}
                  {{ matrixData.scope.competition.event_edition }}
                  · {{ matrixData.scope.competition.entry_name }}
                </template>
              </p>
            </div>
            <el-tag v-if="matrixData?.scope.type === 'self'" type="warning">
              外部协作者仅显示本人
            </el-tag>
            <el-tag v-else-if="matrixData?.scope.type === 'competition_entry'" type="success">
              当前参赛条目
            </el-tag>
            <el-tag v-else type="info">总团队</el-tag>
          </header>

          <div class="filter-panel">
            <div class="filter-grid matrix-scope-grid">
              <el-select
                v-model="matrixFilters.competition_event"
                clearable
                filterable
                placeholder="可选：比赛届次"
                @change="handleMatrixEventChange"
              >
                <el-option
                  v-for="event in competitionEvents"
                  :key="event.id"
                  :label="eventLabel(event)"
                  :value="event.id"
                />
              </el-select>
              <el-select
                v-model="matrixFilters.competition_entry"
                clearable
                filterable
                :disabled="!matrixFilters.competition_event"
                placeholder="可选：参赛项目/队伍"
              >
                <el-option
                  v-for="entry in matrixEntries"
                  :key="entry.id"
                  :label="entryLabel(entry)"
                  :value="entry.id"
                />
              </el-select>
              <el-input
                v-model="matrixFilters.search"
                clearable
                placeholder="姓名、拼音或首字母"
                @keyup.enter="loadMatrix"
              />
              <el-input
                v-model="matrixFilters.school"
                clearable
                placeholder="学校片段"
                @keyup.enter="loadMatrix"
              />
              <el-input
                v-model="matrixFilters.major"
                clearable
                placeholder="专业片段"
                @keyup.enter="loadMatrix"
              />
              <el-select
                v-model="matrixFilters.team_role"
                clearable
                placeholder="团队身份"
              >
                <el-option
                  v-for="option in teamRoleOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              <el-select
                v-model="matrixFilters.member_status"
                clearable
                placeholder="成员状态"
              >
                <el-option label="在队" value="active" />
                <el-option label="暂离" value="on_leave" />
                <el-option label="外部协作者" value="external" />
              </el-select>
              <el-input
                v-model="matrixFilters.skill"
                clearable
                placeholder="技能名称片段"
                @keyup.enter="loadMatrix"
              />
              <el-select
                v-model="matrixFilters.min_proficiency"
                clearable
                placeholder="最低熟练度"
              >
                <el-option
                  v-for="level in 5"
                  :key="level"
                  :label="`${level} 级及以上`"
                  :value="level"
                />
              </el-select>
            </div>
            <div class="filter-actions">
              <el-button type="primary" :loading="matrixLoading" @click="loadMatrix">
                查询矩阵
              </el-button>
              <el-button @click="resetMatrixFilters">重置</el-button>
            </div>
          </div>

          <div v-loading="matrixLoading" class="matrix-table-wrap">
            <EmptyState
              v-if="!matrixLoading && !matrixData?.members.length"
              text="没有符合条件的成员"
              description="可缩短关键词或清除部分筛选条件"
              compact
            />
            <el-table
              v-else
              :data="matrixData?.members || []"
              stripe
              row-key="user_id"
              class="matrix-table"
            >
              <el-table-column label="成员" fixed="left" min-width="164">
                <template #default="{ row }">
                  <div class="member-cell">
                    <el-avatar :size="32" :src="row.avatar || undefined">
                      {{ row.name.slice(0, 1) }}
                    </el-avatar>
                    <div>
                      <strong>{{ row.name }}</strong>
                      <span>{{ row.grade || '年级未填' }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="学校 / 专业" min-width="210">
                <template #default="{ row }">
                  <div class="stacked-copy">
                    <span>{{ row.school || '学校未填' }}</span>
                    <small>{{ row.major || '专业未填' }}</small>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="团队身份" min-width="138">
                <template #default="{ row }">
                  {{ memberRoleLabel(row) }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="96">
                <template #default="{ row }">
                  <el-tag
                    size="small"
                    :type="row.membership_status === 'active' ? 'success' : 'info'"
                  >
                    {{ row.membership_status_display }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                v-if="matrixData?.scope.type === 'competition_entry'"
                label="参赛分工"
                min-width="170"
              >
                <template #default="{ row }">
                  <div class="stacked-copy">
                    <span>{{ row.entry_participation?.role_display || '参赛成员' }}</span>
                    <small>{{ row.entry_participation?.responsibility || '暂未填写分工' }}</small>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="技能名片" min-width="320">
                <template #default="{ row }">
                  <div v-if="row.skills.length" class="skill-chip-list">
                    <el-tag
                      v-for="skill in row.skills"
                      :key="skill.id"
                      size="small"
                      effect="plain"
                    >
                      {{ skill.name }} · {{ skill.proficiency }}/5
                    </el-tag>
                  </div>
                  <span v-else class="muted-copy">尚未登记技能</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="组队 / 任务推荐" name="recommend">
        <section class="skills-surface" aria-labelledby="recommendation-title">
          <header class="section-heading">
            <div>
              <h2 id="recommendation-title">参赛条目内候选人推荐</h2>
              <p>只比较该届比赛、该条参赛记录中尚未退出的成员</p>
            </div>
          </header>

          <div class="filter-panel recommendation-filter">
            <div class="filter-grid recommendation-grid">
              <el-select
                v-model="recommendationForm.competition_event"
                filterable
                placeholder="选择比赛届次"
                @change="handleRecommendationEventChange"
              >
                <el-option
                  v-for="event in competitionEvents"
                  :key="event.id"
                  :label="eventLabel(event)"
                  :value="event.id"
                />
              </el-select>
              <el-select
                v-model="recommendationForm.competition_entry"
                filterable
                :disabled="!recommendationForm.competition_event"
                placeholder="选择参赛项目/队伍"
              >
                <el-option
                  v-for="entry in recommendationEntries"
                  :key="entry.id"
                  :label="entryLabel(entry)"
                  :value="entry.id"
                />
              </el-select>
              <el-select
                v-model="recommendationForm.required_skill_ids"
                multiple
                collapse-tags
                collapse-tags-tooltip
                filterable
                placeholder="选择任务所需技能"
              >
                <el-option
                  v-for="tag in skillTags"
                  :key="tag.id"
                  :label="tag.name"
                  :value="tag.id"
                />
              </el-select>
              <el-select
                v-model="recommendationForm.min_proficiency"
                placeholder="最低熟练度"
              >
                <el-option
                  v-for="level in 5"
                  :key="level"
                  :label="`${level} 级及以上`"
                  :value="level"
                />
              </el-select>
            </div>
            <div class="filter-actions">
              <el-button
                type="primary"
                :loading="recommendationLoading"
                @click="loadRecommendations"
              >
                生成推荐排序
              </el-button>
              <span>技能覆盖 70% + 熟练度 30%，每条结果都显示匹配依据。</span>
            </div>
          </div>

          <div v-loading="recommendationLoading" class="recommendation-results">
            <EmptyState
              v-if="!recommendationLoading && !recommendationData"
              text="请选择比赛、参赛条目和所需技能"
              description="系统不会从总团队中擅自加入不在该参赛条目的人"
              compact
            />
            <template v-else-if="recommendationData">
              <el-alert
                :title="recommendationHeading"
                :description="recommendationData.ranking_formula"
                type="info"
                :closable="false"
                show-icon
              />
              <div
                v-if="recommendationData.recommendations.length"
                class="recommendation-list"
              >
                <article
                  v-for="item in recommendationData.recommendations"
                  :key="item.user_id"
                  class="recommendation-card"
                >
                  <div class="rank-badge">#{{ item.rank }}</div>
                  <div class="recommendation-person">
                    <strong>{{ item.name }}</strong>
                    <span>
                      {{ item.entry_participation?.role_display }}
                      · {{ item.school || '学校未填' }}
                      · {{ item.major || '专业未填' }}
                    </span>
                  </div>
                  <div class="score-block">
                    <strong>{{ item.score }}</strong>
                    <span>综合匹配分</span>
                  </div>
                  <div class="recommendation-evidence">
                    <div>
                      <span class="evidence-label">已匹配</span>
                      <div class="skill-chip-list">
                        <el-tag
                          v-for="skill in item.matched_skills"
                          :key="skill.skill_id"
                          size="small"
                          type="success"
                          effect="plain"
                        >
                          {{ skill.name }} {{ skill.proficiency }}/5
                        </el-tag>
                        <span v-if="!item.matched_skills.length" class="muted-copy">
                          暂无
                        </span>
                      </div>
                    </div>
                    <div>
                      <span class="evidence-label">缺失或未达标</span>
                      <div class="skill-chip-list">
                        <el-tooltip
                          v-for="skill in item.missing_skills"
                          :key="skill.skill_id"
                          :content="skill.reason"
                          placement="top"
                        >
                          <el-tag size="small" type="danger" effect="plain">
                            {{ skill.name }}
                            <template v-if="skill.current_proficiency !== null">
                              {{ skill.current_proficiency }}/5
                            </template>
                          </el-tag>
                        </el-tooltip>
                        <span v-if="!item.missing_skills.length" class="muted-copy">
                          无
                        </span>
                      </div>
                    </div>
                    <p>{{ item.explanations[0] }}</p>
                  </div>
                </article>
              </div>
              <EmptyState
                v-else
                text="当前参赛条目没有可推荐成员"
                description="已退出团队、已撤回参赛或不属于该参赛条目的成员不会进入结果"
                compact
              />
            </template>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="skillDialogVisible"
      title="添加技能"
      :width="dialogWidth"
      :close-on-click-modal="false"
      @close="resetSkillForm"
    >
      <el-form
        ref="skillFormRef"
        :model="skillForm"
        :rules="skillRules"
        label-position="top"
      >
        <el-form-item label="技能标签" prop="skill">
          <el-select
            v-model="skillForm.skill"
            placeholder="选择技能标签"
            filterable
          >
            <el-option
              v-for="tag in skillTags"
              :key="tag.id"
              :label="tag.name"
              :value="tag.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="熟练度" prop="proficiency">
          <div class="proficiency-control">
            <el-rate v-model="skillForm.proficiency" :max="5" />
            <span>{{ skillForm.proficiency }} / 5</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="skillDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="submitting"
            @click="handleSubmitSkill"
          >
            添加技能
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="tagDialogVisible"
      title="添加技能标签"
      :width="dialogWidth"
      :close-on-click-modal="false"
      @close="resetTagForm"
    >
      <el-form
        ref="tagFormRef"
        :model="tagForm"
        :rules="tagRules"
        label-position="top"
      >
        <el-form-item label="标签名称" prop="name">
          <el-input
            v-model="tagForm.name"
            maxlength="100"
            show-word-limit
            placeholder="请输入标签名称"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="tagDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="submitting"
            @click="handleSubmitTag"
          >
            添加标签
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
  type TabPaneName,
} from 'element-plus'
import { Collection, Delete, Plus } from '@element-plus/icons-vue'
import {
  addMemberSkill,
  createSkillTag,
  deleteMemberSkill,
  getMySkills,
  getSkillTags,
} from '@/api/members'
import {
  getCompetitionEvents,
  getCompetitions,
  type CompetitionEvent,
} from '@/api/competitions'
import {
  getSkillRecommendations,
  getTeamSkillMatrix,
  type SkillMatrixQuery,
  type SkillMatrixResponse,
  type SkillRecommendationResponse,
} from '@/api/skillMatrix'
import { del } from '@/api/request'
import { useDevice } from '@/composables/useDevice'
import type { Competition, MemberSkill, SkillTag } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'

type MemberSkillRecord = MemberSkill & { skill?: number; skill_name?: string }
type SkillView = 'mine' | 'matrix' | 'recommend'

const { isMobile } = useDevice()
const activeView = ref<SkillView>('mine')
const loading = ref(false)
const tagLoading = ref(false)
const submitting = ref(false)
const matrixLoading = ref(false)
const recommendationLoading = ref(false)
const mySkills = ref<MemberSkillRecord[]>([])
const skillTags = ref<SkillTag[]>([])
const competitionEvents = ref<CompetitionEvent[]>([])
const matrixEntries = ref<Competition[]>([])
const recommendationEntries = ref<Competition[]>([])
const matrixData = ref<SkillMatrixResponse | null>(null)
const recommendationData = ref<SkillRecommendationResponse | null>(null)
const skillDialogVisible = ref(false)
const tagDialogVisible = ref(false)
const skillFormRef = ref<FormInstance>()
const tagFormRef = ref<FormInstance>()

const dialogWidth = computed(() =>
  isMobile.value ? 'calc(100vw - 24px)' : '440px',
)
const recommendationHeading = computed(() => {
  const data = recommendationData.value
  if (!data) return ''
  return [
    data.competition.event_name,
    data.competition.event_edition,
    '·',
    data.competition.project_name,
    '·',
    data.competition.entry_name,
    `· ${data.candidate_count} 名候选人`,
  ].filter(Boolean).join(' ')
})
const skillForm = reactive({
  skill: '' as number | string,
  proficiency: 3,
})
const tagForm = reactive({ name: '' })
const matrixFilters = reactive<SkillMatrixQuery>({
  search: '',
  school: '',
  major: '',
  team_role: '',
  member_status: '',
  skill: '',
  min_proficiency: undefined,
  competition_event: undefined,
  competition_entry: undefined,
})
const recommendationForm = reactive({
  competition_event: undefined as number | undefined,
  competition_entry: undefined as number | undefined,
  required_skill_ids: [] as number[],
  min_proficiency: 3,
})
const teamRoleOptions = [
  { label: '查看老师（只读）', value: 'teacher' },
  { label: '负责人', value: 'owner' },
  { label: '共同负责人', value: 'co_lead' },
  { label: '团队管理员', value: 'admin' },
  { label: '顾问', value: 'advisor' },
  { label: '团队成员', value: 'member' },
  { label: '外部协作者', value: 'external' },
]
const skillRules: FormRules = {
  skill: [{ required: true, message: '请选择技能标签', trigger: 'change' }],
  proficiency: [
    { required: true, message: '请选择熟练度', trigger: 'change' },
  ],
}
const tagRules: FormRules = {
  name: [{ required: true, message: '请输入标签名称', trigger: 'blur' }],
}

function skillName(item: MemberSkillRecord): string {
  return item.skill_name || item.skill_tag_name || '未命名技能'
}

function eventLabel(event: CompetitionEvent): string {
  return [event.name, event.edition].filter(Boolean).join(' · ')
}

function entryLabel(entry: Competition): string {
  return [
    entry.project_name || `项目 ${entry.project}`,
    entry.entry_name || entry.name,
  ].filter(Boolean).join(' · ')
}

function memberRoleLabel(member: any): string {
  if (member.global_role === 'teacher') return member.global_role_display
  return member.team_memberships[0]?.role_display || member.global_role_display
}

function normalizeCollection<T>(response: T[] | { results?: T[] }): T[] {
  if (Array.isArray(response)) return response
  return response.results || []
}

async function loadMySkills(): Promise<void> {
  loading.value = true
  try {
    const response: any = await getMySkills()
    mySkills.value = normalizeCollection<MemberSkillRecord>(response)
  } catch {
    mySkills.value = []
  } finally {
    loading.value = false
  }
}

async function loadSkillTags(): Promise<void> {
  tagLoading.value = true
  try {
    const response: any = await getSkillTags()
    skillTags.value = normalizeCollection<SkillTag>(response)
  } catch {
    skillTags.value = []
  } finally {
    tagLoading.value = false
  }
}

async function loadCompetitionEvents(): Promise<void> {
  try {
    const response = await getCompetitionEvents({
      page: 1,
      page_size: 100,
    })
    competitionEvents.value = normalizeCollection<CompetitionEvent>(response)
  } catch {
    competitionEvents.value = []
  }
}

async function loadEntries(
  eventId: number | undefined,
  target: 'matrix' | 'recommend',
): Promise<void> {
  const targetRef = target === 'matrix' ? matrixEntries : recommendationEntries
  if (!eventId) {
    targetRef.value = []
    return
  }
  try {
    const response = await getCompetitions({
      event: eventId,
      page: 1,
      page_size: 100,
    })
    targetRef.value = normalizeCollection<Competition>(response)
  } catch {
    targetRef.value = []
  }
}

async function handleMatrixEventChange(value: number | undefined): Promise<void> {
  matrixFilters.competition_entry = undefined
  await loadEntries(value, 'matrix')
}

async function handleRecommendationEventChange(
  value: number | undefined,
): Promise<void> {
  recommendationForm.competition_entry = undefined
  recommendationData.value = null
  await loadEntries(value, 'recommend')
}

async function loadMatrix(): Promise<void> {
  if (
    matrixFilters.competition_event
    && !matrixFilters.competition_entry
  ) {
    ElMessage.warning('选择比赛届次后，还需要选择具体参赛项目/队伍')
    return
  }
  matrixLoading.value = true
  try {
    matrixData.value = await getTeamSkillMatrix({
      ...matrixFilters,
      competition_event: matrixFilters.competition_entry
        ? matrixFilters.competition_event
        : undefined,
    })
  } catch {
    matrixData.value = null
  } finally {
    matrixLoading.value = false
  }
}

async function resetMatrixFilters(): Promise<void> {
  Object.assign(matrixFilters, {
    search: '',
    school: '',
    major: '',
    team_role: '',
    member_status: '',
    skill: '',
    min_proficiency: undefined,
    competition_event: undefined,
    competition_entry: undefined,
  })
  matrixEntries.value = []
  await loadMatrix()
}

async function loadRecommendations(): Promise<void> {
  if (
    !recommendationForm.competition_event
    || !recommendationForm.competition_entry
  ) {
    ElMessage.warning('请先选择比赛届次和具体参赛项目/队伍')
    return
  }
  if (!recommendationForm.required_skill_ids.length) {
    ElMessage.warning('请至少选择一项任务所需技能')
    return
  }
  recommendationLoading.value = true
  try {
    recommendationData.value = await getSkillRecommendations({
      competition_event: recommendationForm.competition_event,
      competition_entry: recommendationForm.competition_entry,
      required_skill_ids: recommendationForm.required_skill_ids,
      min_proficiency: recommendationForm.min_proficiency,
    })
  } catch {
    recommendationData.value = null
  } finally {
    recommendationLoading.value = false
  }
}

function handleTabChange(name: TabPaneName): void {
  if (name === 'matrix' && !matrixData.value && !matrixLoading.value) {
    loadMatrix()
  }
}

function resetSkillForm(): void {
  skillFormRef.value?.clearValidate()
  skillForm.skill = ''
  skillForm.proficiency = 3
}

function resetTagForm(): void {
  tagFormRef.value?.clearValidate()
  tagForm.name = ''
}

function handleAddSkill(): void {
  resetSkillForm()
  skillDialogVisible.value = true
}

function handleCreateTag(): void {
  resetTagForm()
  tagDialogVisible.value = true
}

async function handleSubmitSkill(): Promise<void> {
  if (!formRefValid(skillFormRef.value)) return
  const valid = await skillFormRef.value!.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await addMemberSkill({
      skill: skillForm.skill,
      proficiency: skillForm.proficiency,
    })
    ElMessage.success('技能添加成功')
    skillDialogVisible.value = false
    await loadMySkills()
    if (matrixData.value) await loadMatrix()
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    submitting.value = false
  }
}

async function handleDeleteSkill(item: MemberSkillRecord): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定移除技能「${skillName(item)}」吗？`,
      '移除技能',
      {
        type: 'warning',
        confirmButtonText: '移除',
        cancelButtonText: '取消',
      },
    )
    await deleteMemberSkill(item.id)
    ElMessage.success('技能已移除')
    await loadMySkills()
    if (matrixData.value) await loadMatrix()
  } catch {
    // 用户取消或请求错误已由拦截器处理。
  }
}

async function handleSubmitTag(): Promise<void> {
  if (!formRefValid(tagFormRef.value)) return
  const valid = await tagFormRef.value!.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createSkillTag({ name: tagForm.name.trim() })
    ElMessage.success('标签添加成功')
    tagDialogVisible.value = false
    await loadSkillTags()
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    submitting.value = false
  }
}

async function handleDeleteTag(tag: SkillTag): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除标签「${tag.name}」吗？`,
      '删除技能标签',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
    await del(`/members/skill-tags/${tag.id}/`)
    ElMessage.success('标签已删除')
    await loadSkillTags()
  } catch {
    // 用户取消或请求错误已由拦截器处理。
  }
}

function formRefValid(instance?: FormInstance): boolean {
  return Boolean(instance)
}

onMounted(() => {
  loadMySkills()
  loadSkillTags()
  loadCompetitionEvents()
})
</script>

<style lang="scss" scoped>
.skills-page {
  display: flex;
  flex-direction: column;
  gap: 12px;

  :deep(.page-header) {
    margin-bottom: 6px;
  }
}

.skills-tabs {
  :deep(.el-tabs__header) {
    margin: 0 0 12px;
  }

  :deep(.el-tabs__nav-wrap::after) {
    height: 1px;
    background: var(--color-border-light);
  }
}

.skills-surface {
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.skill-library-surface {
  margin-top: 12px;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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

.matrix-heading {
  align-items: flex-start;
}

.skill-list {
  min-height: 120px;
  padding: 0 18px;
}

.skill-row {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 150px 32px;
  align-items: center;
  gap: 18px;
  min-height: 66px;
  border-bottom: 1px solid var(--color-border-light);

  &:last-child {
    border-bottom: 0;
  }
}

.skill-row__identity,
.member-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;

  > div {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  strong {
    overflow: hidden;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span:last-child {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.skill-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);
}

.tag-library {
  display: flex;
  align-content: flex-start;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 104px;
  padding: 18px;
}

.filter-panel {
  padding: 16px 18px;
  background: var(--color-bg-soft);
  border-bottom: 1px solid var(--color-border-light);
}

.filter-grid {
  display: grid;
  gap: 10px;
}

.matrix-scope-grid {
  grid-template-columns: repeat(3, minmax(180px, 1fr));
}

.recommendation-grid {
  grid-template-columns: repeat(4, minmax(180px, 1fr));
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;

  > span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.matrix-table-wrap {
  min-height: 240px;
}

.matrix-table {
  width: 100%;
}

.stacked-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;

  small {
    color: var(--color-text-muted);
  }
}

.skill-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.muted-copy {
  color: var(--color-text-muted);
  font-size: 12px;
}

.recommendation-results {
  min-height: 220px;
  padding: 16px 18px 18px;
}

.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.recommendation-card {
  display: grid;
  grid-template-columns: 44px minmax(190px, 0.7fr) 108px minmax(280px, 1.6fr);
  align-items: start;
  gap: 14px;
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
  background: var(--color-primary-soft);
  border-radius: 50%;
}

.recommendation-person {
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    color: var(--color-text);
    font-size: 15px;
  }

  span {
    margin-top: 4px;
    color: var(--color-text-muted);
    font-size: 12px;
    line-height: 1.5;
  }
}

.score-block {
  display: flex;
  flex-direction: column;

  strong {
    color: var(--color-primary);
    font-size: 24px;
    font-variant-numeric: tabular-nums;
    line-height: 1;
  }

  span {
    margin-top: 5px;
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.recommendation-evidence {
  display: grid;
  gap: 8px;

  > div {
    display: grid;
    grid-template-columns: 88px minmax(0, 1fr);
    align-items: start;
    gap: 8px;
  }

  p {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.evidence-label {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 24px;
}

.proficiency-control {
  display: flex;
  align-items: center;
  gap: 12px;

  span {
    color: var(--color-text-muted);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
}

:deep(.el-select) {
  width: 100%;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media screen and (max-width: 1180px) {
  .matrix-scope-grid,
  .recommendation-grid {
    grid-template-columns: repeat(2, minmax(180px, 1fr));
  }

  .recommendation-card {
    grid-template-columns: 44px minmax(180px, 1fr) 90px;
  }

  .recommendation-evidence {
    grid-column: 2 / -1;
  }
}

@media screen and (max-width: 768px) {
  .section-heading {
    align-items: flex-start;
    padding: 13px 14px;
  }

  .skill-list {
    padding: 0 14px;
  }

  .skill-row {
    grid-template-columns: minmax(0, 1fr) 32px;
    gap: 10px;
    padding: 12px 0;

    :deep(.el-rate) {
      grid-column: 1 / -1;
      grid-row: 2;
      padding-left: 42px;
    }
  }

  .tag-library,
  .filter-panel,
  .recommendation-results {
    padding: 14px;
  }

  .matrix-scope-grid,
  .recommendation-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .filter-actions {
    align-items: stretch;
    flex-direction: column;

    :deep(.el-button) {
      width: 100%;
      margin-left: 0;
    }
  }

  .recommendation-card {
    grid-template-columns: 42px minmax(0, 1fr) 76px;
    gap: 10px;
  }

  .recommendation-evidence {
    grid-column: 1 / -1;

    > div {
      grid-template-columns: minmax(0, 1fr);
      gap: 3px;
    }
  }

  .dialog-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));

    :deep(.el-button) {
      width: 100%;
      margin-left: 0;
    }
  }
}
</style>
