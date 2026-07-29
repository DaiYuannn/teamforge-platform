<template>
  <div class="page-container">
    <PageHeader
      title="团队组织"
      :subtitle="activeView === 'competition'
        ? '按比赛和项目配置参赛队伍，同一成员可以参与多个队伍'
        : '统一维护总团队人员资料、身份、状态和工作交接'"
    >
      <template #actions>
        <el-button
          v-if="activeView === 'directory'"
          type="primary"
          :icon="Plus"
          @click="openTeamDialog()"
        >
          新建总团队
        </el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeView" class="organization-tabs">
      <el-tab-pane label="参赛队伍配置" name="competition">
        <CompetitionRosterPanel />
      </el-tab-pane>
      <el-tab-pane label="总团队人员库" name="directory">
        <div class="team-layout">
          <aside class="surface-panel team-list">
            <button
              v-for="team in rootTeams"
              :key="team.id"
              type="button"
              class="team-option"
              :class="{ active: selectedTeam?.id === team.id }"
              @click="selectTeam(team)"
            >
              <strong>{{ team.name }}</strong>
              <span>{{ team.member_count }} 人 · {{ team.owner_name }}</span>
            </button>
            <EmptyState
              v-if="!loading && rootTeams.length === 0"
              text="暂无总团队"
              description="创建总团队后开始维护统一人员库"
              compact
            />
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

              <section class="member-filter-bar" aria-label="成员筛选">
                <div class="member-filters">
                  <el-select
                    v-model="memberFilters.role"
                    placeholder="全部身份"
                    clearable
                    aria-label="按团队身份筛选"
                    @change="handleMemberFilterChange"
                  >
                    <el-option
                      v-for="option in roleOptions"
                      :key="option.value"
                      :label="option.label"
                      :value="option.value"
                    />
                  </el-select>
                  <el-select
                    v-model="memberFilters.school"
                    placeholder="全部学校"
                    clearable
                    filterable
                    aria-label="按学校筛选"
                    @change="handleMemberFilterChange"
                  >
                    <el-option v-for="school in schoolOptions" :key="school" :label="school" :value="school" />
                  </el-select>
                  <el-select
                    v-model="memberFilters.status"
                    placeholder="全部状态"
                    clearable
                    aria-label="按团队状态筛选"
                    @change="handleMemberFilterChange"
                  >
                    <el-option label="在队" value="active" />
                    <el-option label="暂离" value="on_leave" />
                    <el-option label="已离队" value="exited" />
                  </el-select>
                  <el-button :disabled="!hasActiveMemberFilters" @click="clearMemberFilters">
                    清空筛选
                  </el-button>
                </div>
                <span>显示 {{ members.length }} / {{ allMembers.length }} 人 · 保持团队重要性顺序</span>
              </section>

              <el-table v-loading="memberLoading" :data="members" table-layout="fixed">
                <template #empty>
                  <EmptyState
                    :text="hasActiveMemberFilters ? '没有符合筛选条件的成员' : '暂无成员'"
                    :description="hasActiveMemberFilters ? '可清空筛选查看完整团队名单' : ''"
                    compact
                  />
                </template>
                <el-table-column label="成员" min-width="190">
                  <template #default="{ row }">
                    <div class="member-cell">
                      <el-button link type="primary" @click="openMemberDetail(row.user)">
                        <strong>{{ row.user_name }}</strong>
                      </el-button>
                      <span>{{ row.user_email }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="学校 / 专业" min-width="180">
                  <template #default="{ row }">
                    <div class="member-cell">
                      <span>{{ row.user_school || '未填写学校' }}</span>
                      <span>{{ [row.user_grade, row.user_major].filter(Boolean).join(' · ') || '未填写年级专业' }}</span>
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
                <el-table-column label="操作" width="210" align="right">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="openMemberDetail(row.user)">详情</el-button>
                    <el-button
                      v-if="selectedTeam?.can_manage"
                      link
                      type="primary"
                      @click="openMemberDialog(row as TeamMember)"
                    >
                      管理
                    </el-button>
                    <el-button
                      v-if="selectedTeam?.can_manage && row.role !== 'owner' && row.status === 'active'"
                      link
                      type="warning"
                      @click="handleTransferOwner(row as TeamMember)"
                    >
                      转为主负责人
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </template>
            <EmptyState v-else text="请选择一个总团队" description="在左侧选择总团队查看完整人员库" />
          </main>
        </div>
      </el-tab-pane>
    </el-tabs>

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
        <el-form-item v-if="!editingMember" label="候选筛选">
          <div class="candidate-filter-grid">
            <el-input
              v-model="candidateFilters.school"
              clearable
              placeholder="学校名称片段"
              @keyup.enter="loadCandidates()"
              @clear="loadCandidates()"
            />
            <el-select
              v-model="candidateFilters.team_role"
              clearable
              placeholder="原团队身份"
              @change="loadCandidates()"
            >
              <el-option
                v-for="option in roleOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
            <el-select
              v-model="candidateFilters.membership_status"
              clearable
              placeholder="成员状态"
              @change="loadCandidates()"
            >
              <el-option label="在队" value="active" />
              <el-option label="暂离" value="on_leave" />
              <el-option label="外部协作者" value="external" />
            </el-select>
            <el-button :loading="candidateLoading" @click="loadCandidates()">筛选</el-button>
          </div>
        </el-form-item>
        <el-form-item v-if="!editingMember" label="成员" required>
          <el-select
            v-model="memberForm.user"
            filterable
            remote
            clearable
            reserve-keyword
            :remote-method="handleCandidateSearch"
            :loading="candidateLoading"
            placeholder="姓名、单字、拼音、首字母、邮箱或手机号"
            style="width: 100%"
          >
            <el-option
              v-for="item in candidates"
              :key="item.id"
              :label="candidateLabel(item)"
              :value="item.id"
            >
              <div class="candidate-option">
                <strong>{{ item.name }}</strong>
                <span>{{ [item.school, item.grade, item.major].filter(Boolean).join(' · ') || item.email }}</span>
                <small>{{ item.team_role_display || '未分配团队身份' }} · {{ item.membership_status_display || item.membership_status }}</small>
              </div>
            </el-option>
          </el-select>
          <p class="candidate-search-help">支持任意片段、单字、姓名拼音和首字母，英文字母不区分大小写。</p>
        </el-form-item>
        <el-form-item v-else label="成员"><strong>{{ editingMember.user_name }}</strong></el-form-item>
        <el-form-item label="团队角色" required>
          <el-select v-model="memberForm.role" style="width: 100%">
            <el-option label="主负责人" value="owner" disabled />
            <el-option label="共同负责人" value="co_lead" />
            <el-option label="团队管理员" value="admin" />
            <el-option label="查看老师（只读）" value="teacher" />
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Plus, UserFilled } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import CompetitionRosterPanel from './CompetitionRosterPanel.vue'
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
  type TeamMemberFilters,
  type TeamMemberRole,
} from '@/api/teams'
import {
  filterTeamMembers,
  hasTeamMemberFilters,
  toTeamMemberQueryParams,
} from './teamMemberFilters'

const loading = ref(false)
const memberLoading = ref(false)
const router = useRouter()
const activeView = ref<'competition' | 'directory'>('competition')
const saving = ref(false)
const teams = ref<Team[]>([])
const selectedTeam = ref<Team | null>(null)
const members = ref<TeamMember[]>([])
const allMembers = ref<TeamMember[]>([])
const candidates = ref<TeamCandidate[]>([])
const candidateLoading = ref(false)
const teamDialogVisible = ref(false)
const memberDialogVisible = ref(false)
const editingTeamId = ref<number | null>(null)
const editingMember = ref<TeamMember | null>(null)
let memberRequestId = 0
let candidateRequestId = 0
let candidateSearchTimer: ReturnType<typeof setTimeout> | undefined

const memberFilters = reactive<TeamMemberFilters>({
  role: undefined,
  school: '',
  status: undefined,
})
const candidateFilters = reactive<{
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
const roleOptions: Array<{ label: string; value: TeamMemberRole }> = [
  { label: '查看老师（只读）', value: 'teacher' },
  { label: '主负责人', value: 'owner' },
  { label: '共同负责人', value: 'co_lead' },
  { label: '团队管理员', value: 'admin' },
  { label: '顾问', value: 'advisor' },
  { label: '团队成员', value: 'member' },
  { label: '外部协作者', value: 'external' },
]

const teamForm = reactive({
  name: '',
  code: '',
  description: '',
  contact_email: '',
  join_message: '',
  is_active: true,
  parent: undefined as number | undefined,
})
const memberForm = reactive({
  user: undefined as number | undefined,
  role: 'member' as TeamMemberRole,
  status: 'active' as TeamMember['status'],
  reason: '',
  handover_to: undefined as number | undefined,
  handover_notes: '',
})
const activeHandoverMembers = computed(() =>
  allMembers.value.filter((item) =>
    item.id !== editingMember.value?.id && item.status === 'active'
  )
)
const schoolOptions = computed(() =>
  Array.from(new Set(
    allMembers.value
      .map((item) => item.user_school?.trim())
      .filter((school): school is string => Boolean(school)),
  )).sort((left, right) => left.localeCompare(right, 'zh-CN')),
)
const hasActiveMemberFilters = computed(() => hasTeamMemberFilters(memberFilters))
const rootTeams = computed(() => teams.value.filter((team) => !team.parent))

function roleLabel(value: string): string {
  return {
    owner: '主负责人',
    co_lead: '共同负责人',
    admin: '团队管理员',
    teacher: '查看老师（只读）',
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

function candidateLabel(candidate: TeamCandidate): string {
  return [candidate.name, candidate.email, candidate.school].filter(Boolean).join(' · ')
}

async function loadCandidates(search = candidateFilters.search): Promise<void> {
  const teamId = selectedTeam.value?.id
  if (!teamId || editingMember.value) return
  candidateFilters.search = search
  const requestId = ++candidateRequestId
  candidateLoading.value = true
  try {
    const result = await getTeamCandidates(teamId, {
      ...(search.trim() ? { search: search.trim() } : {}),
      ...(candidateFilters.school.trim() ? { school: candidateFilters.school.trim() } : {}),
      ...(candidateFilters.team_role ? { team_role: candidateFilters.team_role } : {}),
      ...(candidateFilters.membership_status
        ? { membership_status: candidateFilters.membership_status }
        : {}),
    })
    if (requestId !== candidateRequestId || selectedTeam.value?.id !== teamId) return
    const existing = new Set(
      allMembers.value
        .filter((item) => item.status !== 'exited')
        .map((item) => item.user),
    )
    candidates.value = result.filter((item) => !existing.has(item.id))
  } finally {
    if (requestId === candidateRequestId) candidateLoading.value = false
  }
}

function handleCandidateSearch(query: string): void {
  candidateFilters.search = query
  if (candidateSearchTimer) clearTimeout(candidateSearchTimer)
  candidateSearchTimer = setTimeout(() => {
    loadCandidates(query)
  }, 220)
}

async function loadTeams(): Promise<void> {
  loading.value = true
  try {
    const response = await getTeams({ page_size: 100 })
    teams.value = response.results
    const current = rootTeams.value.find(
      (item) => item.id === selectedTeam.value?.id,
    ) || rootTeams.value[0]
    if (current) await selectTeam(current)
    else selectedTeam.value = null
  } finally {
    loading.value = false
  }
}

async function selectTeam(team: Team): Promise<void> {
  selectedTeam.value = team
  allMembers.value = []
  members.value = []
  await loadSelectedTeamMembers(true)
}

async function loadSelectedTeamMembers(refreshFullList = false): Promise<void> {
  const teamId = selectedTeam.value?.id
  if (!teamId) return

  const requestId = ++memberRequestId
  memberLoading.value = true
  try {
    const params = toTeamMemberQueryParams(memberFilters)
    const filteredRequest = getTeamMembers(
      teamId,
      hasActiveMemberFilters.value ? params : undefined,
    )
    const fullRequest = refreshFullList && hasActiveMemberFilters.value
      ? getTeamMembers(teamId)
      : null
    const [filtered, full] = await Promise.all([
      filteredRequest,
      fullRequest || Promise.resolve(null),
    ])
    if (requestId !== memberRequestId || selectedTeam.value?.id !== teamId) return

    if (full) allMembers.value = full
    else if (!hasActiveMemberFilters.value) allMembers.value = filtered

    // 后端优先筛选；本地再做一次兜底，兼容只支持 status 的旧部署。
    members.value = filterTeamMembers(filtered, memberFilters)
  } finally {
    if (requestId === memberRequestId) memberLoading.value = false
  }
}

async function handleMemberFilterChange(): Promise<void> {
  await loadSelectedTeamMembers(false)
}

async function clearMemberFilters(): Promise<void> {
  memberRequestId += 1
  memberLoading.value = false
  memberFilters.role = undefined
  memberFilters.school = ''
  memberFilters.status = undefined
  if (allMembers.value.length > 0) {
    // 初次进入团队时已经保留完整名单，清空后立即恢复后端原始顺序。
    members.value = [...allMembers.value]
    return
  }
  // 若在完整名单尚未返回时清空筛选，重新请求一次，避免旧请求被取消后留下空表。
  await loadSelectedTeamMembers(true)
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
    parent: undefined,
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
    role: member?.role || 'member',
    status: member?.status || 'active',
    reason: member?.exit_reason || '',
    handover_to: member?.handover_to || undefined,
    handover_notes: member?.handover_notes || '',
  })
  if (!member && selectedTeam.value) {
    Object.assign(candidateFilters, {
      search: '',
      school: '',
      team_role: undefined,
      membership_status: '',
    })
    candidates.value = []
    await loadCandidates('')
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
      `确定将主负责人转让给“${member.user_name}”吗？当前主负责人将调整为共同负责人。`,
      '转让主负责人',
      { type: 'warning' },
    )
    await transferTeamOwner(selectedTeam.value.id, member.id, '团队负责人交接')
    ElMessage.success('团队负责人已转让')
    await loadTeams()
  } catch {
    // 用户取消或错误已统一处理
  }
}

function openMemberDetail(userId: number): void {
  router.push(`/members/${userId}`)
}

onMounted(loadTeams)
</script>

<style lang="scss" scoped>
.organization-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 14px;
  }

  :deep(.el-tabs__item) {
    height: 42px;
    font-weight: 600;
  }
}

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

.member-filter-bar {
  display: flex;
  min-width: 0;
  padding: 12px 18px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--color-surface-subtle);
  border-bottom: 1px solid var(--color-border-light);
}

.member-filters {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.member-filters :deep(.el-select) {
  width: 150px;
}

.member-filter-bar > span {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
}

.dialog-alert {
  margin-bottom: 18px;
}

.candidate-filter-grid {
  display: grid;
  width: 100%;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: 8px;
}

.candidate-option {
  display: grid;
  padding: 4px 0;
  line-height: 1.3;

  span,
  small {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.candidate-search-help {
  margin: 5px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.4;
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

  .member-filter-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .member-filters {
    display: grid;
    width: 100%;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .member-filters :deep(.el-select),
  .member-filters :deep(.el-button) {
    width: 100%;
  }

  .candidate-filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media screen and (max-width: 480px) {
  .member-filters {
    grid-template-columns: 1fr;
  }


  .candidate-filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
