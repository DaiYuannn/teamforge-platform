<template>
  <div class="page-container">
    <PageHeader title="团队组织" subtitle="维护团队资料、人员角色、离队状态和工作交接">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="openTeamDialog()">新建团队</el-button>
      </template>
    </PageHeader>

    <div class="team-layout">
      <aside class="surface-panel team-list">
        <button
          v-for="team in teams"
          :key="team.id"
          type="button"
          class="team-option"
          :class="{ active: selectedTeam?.id === team.id }"
          @click="selectTeam(team)"
        >
          <strong>{{ team.name }}</strong>
          <span>{{ team.member_count }} 人 · {{ team.owner_name }}</span>
        </button>
        <EmptyState v-if="!loading && teams.length === 0" text="暂无团队" description="创建团队后开始维护组织关系" compact />
      </aside>

      <main v-loading="loading" class="surface-panel team-workspace">
        <template v-if="selectedTeam">
          <header class="team-heading">
            <div>
              <div class="title-line">
                <h2>{{ selectedTeam.name }}</h2>
                <el-tag v-if="selectedTeam.code" size="small" type="info">{{ selectedTeam.code }}</el-tag>
              </div>
              <p>{{ selectedTeam.description || '尚未填写团队介绍' }}</p>
              <span>负责人：{{ selectedTeam.owner_name }} · 联系邮箱：{{ selectedTeam.contact_email || '未设置' }}</span>
            </div>
            <div v-if="selectedTeam.can_manage" class="heading-actions">
              <el-button :icon="Edit" @click="openTeamDialog(selectedTeam)">编辑资料</el-button>
              <el-button type="primary" :icon="UserFilled" @click="openMemberDialog()">添加成员</el-button>
            </div>
          </header>

          <el-alert
            v-if="selectedTeam.join_message"
            :title="selectedTeam.join_message"
            type="info"
            :closable="false"
            show-icon
            class="join-message"
          />

          <el-table :data="members" table-layout="fixed">
            <template #empty><EmptyState text="暂无成员" compact /></template>
            <el-table-column label="成员" min-width="190">
              <template #default="{ row }">
                <div class="member-cell">
                  <strong>{{ row.user_name }}</strong>
                  <span>{{ row.user_email }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="团队角色" width="132">
              <template #default="{ row }">{{ row.role_display || roleLabel(row.role) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="104">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">
                  {{ row.status_display || statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="加入时间" width="120">
              <template #default="{ row }">{{ formatDate(row.joined_at) }}</template>
            </el-table-column>
            <el-table-column v-if="selectedTeam.can_manage" label="操作" width="154" align="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openMemberDialog(row as TeamMember)">管理</el-button>
                <el-button
                  v-if="row.role !== 'owner' && row.status === 'active'"
                  link
                  type="warning"
                  @click="handleTransferOwner(row as TeamMember)"
                >
                  转为负责人
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>
        <EmptyState v-else text="请选择一个团队" description="在左侧选择团队查看组织关系" />
      </main>
    </div>

    <el-dialog
      v-model="teamDialogVisible"
      :title="editingTeamId ? '编辑团队资料' : '新建团队'"
      width="560px"
      append-to-body
    >
      <el-form label-width="90px">
        <el-form-item label="团队名称" required><el-input v-model="teamForm.name" /></el-form-item>
        <el-form-item label="团队编号"><el-input v-model="teamForm.code" placeholder="例如 INNOVATION-LAB" /></el-form-item>
        <el-form-item label="团队介绍"><el-input v-model="teamForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="联系邮箱"><el-input v-model="teamForm.contact_email" /></el-form-item>
        <el-form-item label="加入我们"><el-input v-model="teamForm.join_message" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="teamDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTeam">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="memberDialogVisible"
      :title="editingMember ? '成员角色与交接' : '添加团队成员'"
      width="560px"
      append-to-body
    >
      <el-alert
        v-if="editingMember"
        title="离队会保留该成员在团队中的历史关系，项目负责人还应在对应项目中完成交接。"
        type="info"
        :closable="false"
        show-icon
        class="dialog-alert"
      />
      <el-form label-width="90px">
        <el-form-item v-if="!editingMember" label="成员" required>
          <el-select v-model="memberForm.user" filterable style="width: 100%">
            <el-option
              v-for="item in candidates"
              :key="item.id"
              :label="`${item.name} · ${item.email}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="成员"><strong>{{ editingMember.user_name }}</strong></el-form-item>
        <el-form-item label="团队角色" required>
          <el-select v-model="memberForm.role" style="width: 100%">
            <el-option label="团队管理员" value="admin" />
            <el-option label="指导老师" value="teacher" />
            <el-option label="团队成员" value="member" />
            <el-option label="顾问" value="advisor" />
            <el-option label="外部协作者" value="external" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingMember" label="成员状态" required>
          <el-select v-model="memberForm.status" style="width: 100%">
            <el-option label="在队" value="active" />
            <el-option label="暂离" value="on_leave" />
            <el-option label="已离队" value="exited" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingMember && memberForm.status === 'exited'" label="交接人">
          <el-select v-model="memberForm.handover_to" clearable style="width: 100%">
            <el-option
              v-for="item in activeHandoverMembers"
              :key="item.id"
              :label="`${item.user_name} · ${roleLabel(item.role)}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingMember" label="原因说明">
          <el-input v-model="memberForm.reason" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item v-if="editingMember && memberForm.status === 'exited'" label="交接说明">
          <el-input v-model="memberForm.handover_notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memberDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMember">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Plus, UserFilled } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils/format'
import {
  addTeamMember,
  createTeam,
  getTeamCandidates,
  getTeamMembers,
  getTeams,
  transferTeamOwner,
  transitionTeamMember,
  updateTeam,
  type Team,
  type TeamCandidate,
  type TeamMember,
} from '@/api/teams'

const loading = ref(false)
const saving = ref(false)
const teams = ref<Team[]>([])
const selectedTeam = ref<Team | null>(null)
const members = ref<TeamMember[]>([])
const candidates = ref<TeamCandidate[]>([])
const teamDialogVisible = ref(false)
const memberDialogVisible = ref(false)
const editingTeamId = ref<number | null>(null)
const editingMember = ref<TeamMember | null>(null)

const teamForm = reactive({
  name: '',
  code: '',
  description: '',
  contact_email: '',
  join_message: '',
  is_active: true,
})
const memberForm = reactive({
  user: undefined as number | undefined,
  role: 'member',
  status: 'active',
  reason: '',
  handover_to: undefined as number | undefined,
  handover_notes: '',
})
const activeHandoverMembers = computed(() =>
  members.value.filter((item) =>
    item.id !== editingMember.value?.id && item.status === 'active'
  )
)

function roleLabel(value: string): string {
  return {
    owner: '负责人',
    admin: '团队管理员',
    teacher: '指导老师',
    member: '团队成员',
    advisor: '顾问',
    external: '外部协作者',
  }[value] || value
}

function statusLabel(value: string): string {
  return { active: '在队', on_leave: '暂离', exited: '已离队' }[value] || value
}

function statusType(value: string): 'success' | 'warning' | 'info' {
  if (value === 'on_leave') return 'warning'
  if (value === 'exited') return 'info'
  return 'success'
}

async function loadTeams(): Promise<void> {
  loading.value = true
  try {
    const response = await getTeams()
    teams.value = response.results
    const current = teams.value.find((item) => item.id === selectedTeam.value?.id) || teams.value[0]
    if (current) await selectTeam(current)
  } finally {
    loading.value = false
  }
}

async function selectTeam(team: Team): Promise<void> {
  selectedTeam.value = team
  members.value = await getTeamMembers(team.id)
}

function openTeamDialog(team?: Team): void {
  editingTeamId.value = team?.id || null
  Object.assign(teamForm, {
    name: team?.name || '',
    code: team?.code || '',
    description: team?.description || '',
    contact_email: team?.contact_email || '',
    join_message: team?.join_message || '',
    is_active: team?.is_active ?? true,
  })
  teamDialogVisible.value = true
}

async function saveTeam(): Promise<void> {
  if (!teamForm.name.trim()) {
    ElMessage.warning('请填写团队名称')
    return
  }
  saving.value = true
  try {
    if (editingTeamId.value) await updateTeam(editingTeamId.value, { ...teamForm })
    else await createTeam({ ...teamForm })
    ElMessage.success('团队资料已保存')
    teamDialogVisible.value = false
    await loadTeams()
  } finally {
    saving.value = false
  }
}

async function openMemberDialog(member?: TeamMember): Promise<void> {
  editingMember.value = member || null
  Object.assign(memberForm, {
    user: member?.user,
    role: member?.role === 'owner' ? 'admin' : member?.role || 'member',
    status: member?.status || 'active',
    reason: member?.exit_reason || '',
    handover_to: member?.handover_to || undefined,
    handover_notes: member?.handover_notes || '',
  })
  if (!member && selectedTeam.value) {
    candidates.value = await getTeamCandidates(selectedTeam.value.id)
    const existing = new Set(members.value.filter((item) => item.status !== 'exited').map((item) => item.user))
    candidates.value = candidates.value.filter((item) => !existing.has(item.id))
  }
  memberDialogVisible.value = true
}

async function saveMember(): Promise<void> {
  if (!selectedTeam.value) return
  saving.value = true
  try {
    if (editingMember.value) {
      await transitionTeamMember(selectedTeam.value.id, editingMember.value.id, {
        role: memberForm.role,
        status: memberForm.status,
        reason: memberForm.reason.trim(),
        ...(memberForm.handover_to ? { handover_to: memberForm.handover_to } : {}),
        handover_notes: memberForm.handover_notes.trim(),
      })
    } else if (memberForm.user) {
      await addTeamMember(selectedTeam.value.id, memberForm.user, memberForm.role)
    } else {
      ElMessage.warning('请选择成员')
      return
    }
    ElMessage.success('团队成员已保存')
    memberDialogVisible.value = false
    await loadTeams()
  } finally {
    saving.value = false
  }
}

async function handleTransferOwner(member: TeamMember): Promise<void> {
  if (!selectedTeam.value) return
  try {
    await ElMessageBox.confirm(
      `确定将团队负责人转让给“${member.user_name}”吗？当前负责人将调整为团队管理员。`,
      '转让团队负责人',
      { type: 'warning' },
    )
    await transferTeamOwner(selectedTeam.value.id, member.id, '团队负责人交接')
    ElMessage.success('团队负责人已转让')
    await loadTeams()
  } catch {
    // 用户取消或错误已统一处理
  }
}

onMounted(loadTeams)
</script>

<style lang="scss" scoped>
.team-layout {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: var(--space-4);
}

.team-list {
  align-self: start;
  padding: 8px;
}

.team-option {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 12px;
  color: var(--color-text);
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  &:hover,
  &.active {
    background: var(--color-primary-soft);
  }
}

.team-workspace {
  min-height: 360px;
  padding: 0;
  overflow: hidden;
}

.team-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
  border-bottom: 1px solid var(--color-border-light);

  p,
  span {
    margin-top: 5px;
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.title-line,
.heading-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.member-cell {
  display: grid;

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.join-message {
  margin: 12px 18px 0;
}

.dialog-alert {
  margin-bottom: 18px;
}

@media screen and (max-width: 860px) {
  .team-layout {
    grid-template-columns: 1fr;
  }

  .team-list {
    display: flex;
    overflow-x: auto;
  }

  .team-option {
    min-width: 190px;
  }

  .team-heading {
    flex-direction: column;
  }
}
</style>
