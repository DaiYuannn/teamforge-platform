<template>
  <article class="entry-card">
    <header class="entry-card__header">
      <div>
        <div class="entry-title">
          <h4>{{ entry.project_name || `项目 ${entry.project}` }}</h4>
          <el-tag size="small" type="info">
            {{ entry.entry_name || `参赛条目 #${entry.id}` }}
          </el-tag>
        </div>
        <p>
          {{ entry.event_name || entry.name }}
          <template v-if="entry.current_stage"> · {{ entry.current_stage }}</template>
        </p>
      </div>
      <div class="entry-actions">
        <span>{{ activeParticipantCount }} 名当前成员</span>
        <el-button
          v-if="entry.can_manage"
          type="primary"
          size="small"
          :icon="UserFilled"
          @click="pickerVisible = true"
        >
          从总团队添加
        </el-button>
      </div>
    </header>

    <section class="entry-filter-bar" aria-label="参赛成员筛选">
      <el-select v-model="participantFilters.role" clearable placeholder="全部身份">
        <el-option label="指导成员" value="advisor" />
        <el-option label="比赛负责人" value="leader" />
        <el-option label="参赛成员" value="member" />
      </el-select>
      <el-select v-model="participantFilters.school" clearable filterable placeholder="全部学校">
        <el-option v-for="school in participantSchools" :key="school" :label="school" :value="school" />
      </el-select>
      <el-select v-model="participantFilters.status" clearable placeholder="全部状态">
        <el-option label="拟参赛" value="planned" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="已退出" value="withdrawn" />
      </el-select>
      <el-button :disabled="!hasParticipantFilters" @click="clearParticipantFilters">清空</el-button>
      <span>显示 {{ filteredParticipants.length }} / {{ participants.length }} 人</span>
    </section>

    <el-table
      v-loading="loading"
      :data="filteredParticipants"
      row-key="id"
      table-layout="fixed"
      size="small"
    >
      <template #empty>
        <el-empty
          :image-size="54"
          description="该项目在本次比赛中尚未配置参赛成员"
        />
      </template>
      <el-table-column label="成员" min-width="160">
        <template #default="{ row }">
          <div class="participant-main">
            <strong>{{ participantName(row as CompetitionParticipant) }}</strong>
            <span>{{ row.user_detail?.email || '未填写邮箱' }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="学校 / 专业" min-width="170">
        <template #default="{ row }">
          <div class="participant-main">
            <span>{{ row.user_detail?.school || '未填写学校' }}</span>
            <span>
              {{
                [row.user_detail?.grade, row.user_detail?.major]
                  .filter(Boolean)
                  .join(' · ') || '未填写年级专业'
              }}
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="参赛身份" width="112">
        <template #default="{ row }">
          <el-tag :type="participantRoleType(row.role)" size="small">
            {{ row.role_display || participantRoleLabel(row.role) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="参与状态" width="108">
        <template #default="{ row }">
          <el-tag :type="participantStatusType(row.participation_status)" size="small">
            {{
              row.participation_status_display
              || participantStatusLabel(row.participation_status)
            }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="具体分工" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.responsibility || '尚未填写具体分工' }}
        </template>
      </el-table-column>
      <el-table-column
        v-if="entry.can_manage"
        label="操作"
        width="118"
        align="right"
      >
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEdit(row as CompetitionParticipant)">
            管理
          </el-button>
          <el-button link type="danger" :icon="Delete" @click="removeParticipant(row as CompetitionParticipant)">
            移除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <CompetitionMemberPicker
      v-model:visible="pickerVisible"
      :competition-id="entry.id"
      :competition-name="[entry.project_name, entry.entry_name].filter(Boolean).join(' · ') || entry.name"
      :existing-user-ids="existingUserIds"
      @saved="emit('refresh')"
    />

    <el-dialog
      v-model="editVisible"
      title="管理参赛成员"
      width="520px"
      append-to-body
    >
      <el-form label-width="90px">
        <el-form-item label="成员">
          <strong>{{ editingParticipant ? participantName(editingParticipant) : '' }}</strong>
        </el-form-item>
        <el-form-item label="参赛身份">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="指导成员" value="advisor" />
            <el-option label="比赛负责人" value="leader" />
            <el-option label="参赛成员" value="member" />
          </el-select>
        </el-form-item>
        <el-form-item label="参与状态">
          <el-select v-model="editForm.participation_status" style="width: 100%">
            <el-option label="拟参赛" value="planned" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已退出" value="withdrawn" />
          </el-select>
        </el-form-item>
        <el-form-item label="具体分工">
          <el-input
            v-model="editForm.responsibility"
            type="textarea"
            :rows="4"
            placeholder="例如：答辩主讲、技术开发、材料整理"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveParticipant">
          保存
        </el-button>
      </template>
    </el-dialog>
  </article>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, UserFilled } from '@element-plus/icons-vue'
import {
  deleteCompetitionParticipant,
  updateCompetitionParticipant,
} from '@/api/competitions'
import type { Competition, CompetitionParticipant } from '@/types'
import CompetitionMemberPicker from './CompetitionMemberPicker.vue'

const props = defineProps<{
  entry: Competition
  participants: CompetitionParticipant[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (event: 'refresh'): void
}>()

const pickerVisible = ref(false)
const editVisible = ref(false)
const saving = ref(false)
const editingParticipant = ref<CompetitionParticipant | null>(null)
const participantFilters = reactive<{
  role?: CompetitionParticipant['role']
  school: string
  status?: CompetitionParticipant['participation_status']
}>({
  role: undefined,
  school: '',
  status: undefined,
})
const editForm = reactive<{
  role: CompetitionParticipant['role']
  participation_status: CompetitionParticipant['participation_status']
  responsibility: string
}>({
  role: 'member',
  participation_status: 'planned',
  responsibility: '',
})

const rolePriority: Record<CompetitionParticipant['role'], number> = {
  advisor: 0,
  leader: 1,
  member: 2,
}
const statusPriority: Record<CompetitionParticipant['participation_status'], number> = {
  confirmed: 0,
  planned: 1,
  withdrawn: 2,
}

const sortedParticipants = computed(() =>
  [...props.participants].sort((left, right) => (
    rolePriority[left.role] - rolePriority[right.role]
    || statusPriority[left.participation_status] - statusPriority[right.participation_status]
    || participantName(left).localeCompare(participantName(right), 'zh-CN')
  )),
)
const participantSchools = computed(() => Array.from(new Set(
  props.participants
    .map((participant) => participant.user_detail?.school?.trim())
    .filter((school): school is string => Boolean(school)),
)).sort((left, right) => left.localeCompare(right, 'zh-CN')))
const hasParticipantFilters = computed(() => Boolean(
  participantFilters.role || participantFilters.school || participantFilters.status,
))
const filteredParticipants = computed(() => sortedParticipants.value.filter((participant) => (
  (!participantFilters.role || participant.role === participantFilters.role)
  && (!participantFilters.school || participant.user_detail?.school === participantFilters.school)
  && (!participantFilters.status || participant.participation_status === participantFilters.status)
)))

function clearParticipantFilters(): void {
  participantFilters.role = undefined
  participantFilters.school = ''
  participantFilters.status = undefined
}
const activeParticipantCount = computed(() =>
  props.participants.filter(
    (participant) => participant.participation_status !== 'withdrawn',
  ).length,
)
const existingUserIds = computed(() =>
  props.participants.map((participant) => participant.user),
)

function participantName(participant: CompetitionParticipant): string {
  return participant.user_detail?.name || `成员 ${participant.user}`
}

function participantRoleLabel(role: CompetitionParticipant['role']): string {
  return {
    advisor: '指导成员',
    leader: '比赛负责人',
    member: '参赛成员',
  }[role]
}

function participantRoleType(
  role: CompetitionParticipant['role'],
): 'warning' | 'success' | 'info' {
  if (role === 'advisor') return 'warning'
  if (role === 'leader') return 'success'
  return 'info'
}

function participantStatusLabel(
  status: CompetitionParticipant['participation_status'],
): string {
  return {
    planned: '拟参赛',
    confirmed: '已确认',
    withdrawn: '已退出',
  }[status]
}

function participantStatusType(
  status: CompetitionParticipant['participation_status'],
): 'success' | 'warning' | 'info' {
  if (status === 'confirmed') return 'success'
  if (status === 'planned') return 'warning'
  return 'info'
}

function openEdit(participant: CompetitionParticipant): void {
  editingParticipant.value = participant
  Object.assign(editForm, {
    role: participant.role,
    participation_status: participant.participation_status,
    responsibility: participant.responsibility || '',
  })
  editVisible.value = true
}

async function saveParticipant(): Promise<void> {
  if (!editingParticipant.value) return
  saving.value = true
  try {
    await updateCompetitionParticipant(
      props.entry.id,
      editingParticipant.value.id,
      {
        role: editForm.role,
        participation_status: editForm.participation_status,
        responsibility: editForm.responsibility.trim(),
      },
    )
    ElMessage.success('参赛成员配置已更新')
    editVisible.value = false
    emit('refresh')
  } finally {
    saving.value = false
  }
}

async function removeParticipant(participant: CompetitionParticipant): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定从当前参赛条目中移除“${participantName(participant)}”吗？总团队人员信息不会被删除。`,
      '移除参赛成员',
      { type: 'warning' },
    )
    await deleteCompetitionParticipant(props.entry.id, participant.id)
    ElMessage.success('已从当前参赛条目移除')
    emit('refresh')
  } catch {
    // 用户取消或请求错误已由统一拦截器处理。
  }
}
</script>

<style lang="scss" scoped>
.entry-card {
  min-width: 0;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.entry-card__header {
  display: flex;
  padding: 15px 16px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  background: var(--color-surface-subtle);
  border-bottom: 1px solid var(--color-border-light);

  p {
    margin-top: 4px;
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.entry-title,
.entry-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.entry-filter-bar {
  display: flex;
  padding: 10px 16px;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--color-border-light);

  :deep(.el-select) {
    width: 142px;
  }

  > span {
    margin-left: auto;
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.entry-title h4 {
  color: var(--color-text);
  font-size: 15px;
  font-weight: 600;
}

.entry-actions {
  justify-content: flex-end;

  > span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.participant-main {
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

@media screen and (max-width: 700px) {
  .entry-card__header {
    flex-direction: column;
  }

  .entry-actions {
    justify-content: flex-start;
  }

  .entry-filter-bar :deep(.el-select) {
    width: calc(50% - 4px);
  }

  .entry-filter-bar > span {
    width: 100%;
    margin-left: 0;
  }
}
</style>
