<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`从总团队添加成员 · ${competitionName}`"
    width="860px"
    append-to-body
    destroy-on-close
  >
    <el-alert
      title="这里只新增项目与比赛中的参赛配置，不会改变成员在总团队中的身份和状态。"
      type="info"
      :closable="false"
      show-icon
      class="picker-alert"
    />

    <section class="candidate-filters" aria-label="候选成员筛选">
      <el-input
        v-model="filters.search"
        clearable
        placeholder="姓名、单字、拼音、首字母或邮箱（输入 1 个字符即可搜索）"
        aria-label="搜索候选成员"
      />
      <el-select
        v-model="filters.school"
        clearable
        filterable
        allow-create
        default-first-option
        placeholder="全部学校"
        aria-label="按学校筛选候选成员"
      >
        <el-option
          v-for="school in schoolOptions"
          :key="school"
          :label="school"
          :value="school"
        />
      </el-select>
      <el-select
        v-model="filters.team_role"
        clearable
        placeholder="全部总团队身份"
        aria-label="按总团队身份筛选候选成员"
      >
        <el-option
          v-for="option in teamRoleOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
      <el-select
        v-model="filters.membership_status"
        clearable
        placeholder="全部总团队状态"
        aria-label="按总团队状态筛选候选成员"
      >
        <el-option label="在队" value="active" />
        <el-option label="暂离" value="on_leave" />
      </el-select>
    </section>

    <div class="picker-toolbar">
      <span>搜索结果 {{ candidates.length }} 人</span>
      <el-form-item label="加入后的参赛身份">
        <el-select v-model="participantRole">
          <el-option label="参赛成员" value="member" />
          <el-option label="比赛负责人" value="leader" />
          <el-option label="指导成员" value="advisor" />
        </el-select>
      </el-form-item>
    </div>

    <el-table
      v-loading="loading"
      :data="candidates"
      row-key="id"
      table-layout="fixed"
      max-height="420"
    >
      <template #empty>
        <el-empty
          :image-size="64"
          description="没有符合当前关键词和筛选条件的总团队成员"
        />
      </template>
      <el-table-column label="选择" width="68" align="center">
        <template #default="{ row }">
          <el-checkbox
            :model-value="selectedIds.includes(row.id)"
            :disabled="!candidateSelectable(row as TeamCandidate)"
            :aria-label="`选择 ${row.name}`"
            @change="toggleCandidate(row.id, $event)"
          />
        </template>
      </el-table-column>
      <el-table-column label="成员" min-width="190">
        <template #default="{ row }">
          <div class="candidate-main">
            <strong>{{ row.name }}</strong>
            <span>{{ row.email }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="学校 / 专业" min-width="180">
        <template #default="{ row }">
          <div class="candidate-main">
            <span>{{ row.school || '未填写学校' }}</span>
            <span>{{ [row.grade, row.major].filter(Boolean).join(' · ') || '未填写年级专业' }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="总团队身份" min-width="126">
        <template #default="{ row }">
          {{ row.team_role_display || teamRoleLabel(row.team_role) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="112">
        <template #default="{ row }">
          <el-tag :type="candidateStatusType(row as TeamCandidate)" size="small">
            {{ candidateStatusLabel(row as TeamCandidate) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="说明" min-width="120">
        <template #default="{ row }">
          <span v-if="existingUserIdSet.has(row.id)" class="muted">已在当前条目</span>
          <span v-else-if="!candidateSelectable(row as TeamCandidate)" class="muted">当前不可加入</span>
          <span v-else class="available">可以加入</span>
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <div class="picker-footer">
        <span>已选择 {{ selectedIds.length }} 人</span>
        <div>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="saving"
            :disabled="selectedIds.length === 0"
            @click="saveSelected"
          >
            加入当前参赛条目
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  addCompetitionParticipant,
  getCompetitionParticipantCandidates,
} from '@/api/competitions'
import type { CompetitionParticipant } from '@/types'
import type {
  TeamCandidate,
  TeamMemberRole,
} from '@/api/teams'

const props = defineProps<{
  visible: boolean
  competitionId: number | null
  competitionName: string
  existingUserIds: number[]
}>()

const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'saved'): void
}>()

const candidates = ref<TeamCandidate[]>([])
const selectedIds = ref<number[]>([])
const knownSchools = ref<string[]>([])
const loading = ref(false)
const saving = ref(false)
const participantRole = ref<CompetitionParticipant['role']>('member')
let searchTimer: number | undefined
let candidateRequestId = 0

const filters = reactive<{
  search: string
  school: string
  team_role?: TeamMemberRole
  membership_status: string
}>({
  search: '',
  school: '',
  team_role: undefined,
  membership_status: '',
})

const teamRoleOptions: Array<{ label: string; value: TeamMemberRole }> = [
  { label: '查看老师（只读）', value: 'teacher' },
  { label: '主负责人', value: 'owner' },
  { label: '共同负责人', value: 'co_lead' },
  { label: '团队管理员', value: 'admin' },
  { label: '顾问', value: 'advisor' },
  { label: '团队成员', value: 'member' },
]

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})
const existingUserIdSet = computed(() => new Set(props.existingUserIds))
const schoolOptions = computed(() =>
  [...knownSchools.value].sort((left, right) => left.localeCompare(right, 'zh-CN')),
)

function teamRoleLabel(role?: TeamMemberRole): string {
  return teamRoleOptions.find((option) => option.value === role)?.label || '未设置'
}

function candidateStatusLabel(candidate: TeamCandidate): string {
  if (candidate.is_active === false) return '账号停用'
  return candidate.membership_status_display || {
    active: '在队',
    on_leave: '暂离',
    exited: '已离队',
    external: '外部协作者',
  }[candidate.membership_status] || candidate.membership_status || '未知'
}

function candidateStatusType(
  candidate: TeamCandidate,
): 'success' | 'warning' | 'info' | 'danger' {
  if (candidate.is_active === false || candidate.membership_status === 'exited') return 'danger'
  if (candidate.membership_status === 'on_leave') return 'warning'
  if (candidate.membership_status === 'external') return 'info'
  return 'success'
}

function candidateSelectable(candidate: TeamCandidate): boolean {
  return (
    !existingUserIdSet.value.has(candidate.id)
    && candidate.is_active !== false
    && ['active', 'on_leave'].includes(candidate.membership_status)
  )
}

function toggleCandidate(
  candidateId: number,
  checked: string | number | boolean,
): void {
  if (checked) {
    if (!selectedIds.value.includes(candidateId)) {
      selectedIds.value = [...selectedIds.value, candidateId]
    }
    return
  }
  selectedIds.value = selectedIds.value.filter((id) => id !== candidateId)
}

function scheduleCandidateLoad(delay = 220): void {
  if (!props.visible || !props.competitionId) return
  if (searchTimer !== undefined) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadCandidates, delay)
}

async function loadCandidates(): Promise<void> {
  const competitionId = props.competitionId
  if (!competitionId) return
  const requestId = ++candidateRequestId
  loading.value = true
  try {
    const result = await getCompetitionParticipantCandidates(competitionId, {
      ...(filters.search.trim() ? { search: filters.search.trim() } : {}),
      ...(filters.school.trim() ? { school: filters.school.trim() } : {}),
      ...(filters.team_role ? { team_role: filters.team_role } : {}),
      ...(filters.membership_status
        ? { membership_status: filters.membership_status }
        : {}),
    })
    if (requestId !== candidateRequestId) return
    candidates.value = result
    const schools = new Set(knownSchools.value)
    result.forEach((candidate) => {
      if (candidate.school?.trim()) schools.add(candidate.school.trim())
    })
    knownSchools.value = [...schools]
  } finally {
    if (requestId === candidateRequestId) loading.value = false
  }
}

async function saveSelected(): Promise<void> {
  const competitionId = props.competitionId
  if (!competitionId || selectedIds.value.length === 0) return
  saving.value = true
  const requestedIds = [...selectedIds.value]
  try {
    const results = await Promise.allSettled(
      requestedIds.map((user) =>
        addCompetitionParticipant(competitionId, {
          user,
          role: participantRole.value,
          participation_status: 'planned',
          responsibility: '',
        }),
      ),
    )
    const successfulIds = requestedIds.filter(
      (_, index) => results[index]?.status === 'fulfilled',
    )
    const failedCount = requestedIds.length - successfulIds.length
    if (successfulIds.length > 0) {
      selectedIds.value = selectedIds.value.filter(
        (id) => !successfulIds.includes(id),
      )
      emit('saved')
    }
    if (failedCount > 0) {
      ElMessage.warning(`已加入 ${successfulIds.length} 人，另有 ${failedCount} 人未能加入`)
      await loadCandidates()
      return
    }
    ElMessage.success(`已加入 ${successfulIds.length} 名参赛成员`)
    dialogVisible.value = false
  } finally {
    saving.value = false
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      candidateRequestId += 1
      return
    }
    selectedIds.value = []
    participantRole.value = 'member'
    Object.assign(filters, {
      search: '',
      school: '',
      team_role: undefined,
      membership_status: '',
    })
    scheduleCandidateLoad(0)
  },
)

watch(
  () => [
    filters.search,
    filters.school,
    filters.team_role,
    filters.membership_status,
  ],
  () => scheduleCandidateLoad(),
)

onBeforeUnmount(() => {
  if (searchTimer !== undefined) window.clearTimeout(searchTimer)
  candidateRequestId += 1
})
</script>

<style lang="scss" scoped>
.picker-alert {
  margin-bottom: 16px;
}

.candidate-filters {
  display: grid;
  grid-template-columns: minmax(260px, 1.7fr) repeat(3, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.candidate-filters :deep(.el-select) {
  width: 100%;
}

.picker-toolbar {
  display: flex;
  min-height: 38px;
  margin-bottom: 8px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.picker-toolbar :deep(.el-form-item) {
  margin-bottom: 0;
}

.candidate-main {
  display: grid;
  min-width: 0;
  gap: 2px;

  strong,
  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}

.available {
  color: var(--color-success);
  font-size: 12px;
}

.picker-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  > span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

@media screen and (max-width: 900px) {
  .candidate-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media screen and (max-width: 560px) {
  .candidate-filters {
    grid-template-columns: 1fr;
  }

  .picker-toolbar,
  .picker-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
