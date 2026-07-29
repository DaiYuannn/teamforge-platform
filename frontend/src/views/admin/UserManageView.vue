<template>
  <div class="page-container">
    <PageHeader title="用户管理" subtitle="一位操作老师负责业务操作，其余老师按团队配置为只读查看者">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新建用户</el-button>
      </template>
    </PageHeader>

    <!-- 搜索筛选 -->
    <div class="surface-panel search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="queryParams.search"
            placeholder="用户名/邮箱/姓名"
            clearable
            class="keyword-input"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="queryParams.global_role"
            placeholder="全部角色"
            clearable
            class="role-select"
            @change="handleSearch"
          >
            <el-option
              v-for="(item, key) in ROLE_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="成员状态">
          <el-select
            v-model="queryParams.membership_status"
            placeholder="全部状态"
            clearable
            class="role-select"
            @change="handleSearch"
          >
            <el-option label="在队" value="active" />
            <el-option label="暂离" value="on_leave" />
            <el-option label="已离队" value="exited" />
            <el-option label="外部协作者" value="external" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <span class="result-count">共 {{ total }} 位用户</span>
    </div>

    <!-- 用户列表表格 -->
    <section class="surface-panel user-workspace">
      <el-table v-if="!isMobile" v-loading="loading" :data="userList">
        <template #empty>
          <EmptyState text="暂无用户" description="调整筛选条件后重试" :compact="true" />
        </template>
        <el-table-column label="用户" min-width="180">
          <template #default="{ row }">
            <div class="user-identity">
              <AvatarWithName :name="row.name || row.username" :avatar-url="row.avatar" :size="32" :show-name="false" />
              <div class="identity-text">
                <strong>{{ row.name || row.username }}</strong>
                <span>@{{ row.username }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="global_role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.global_role) as any" size="small">
              {{ row.global_role_display || getRoleLabel(row.global_role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="membership_status" label="成员状态" width="100">
          <template #default="{ row }">
            <el-tag :type="membershipStatusType(row.membership_status)" size="small">
              {{ membershipStatusLabel(row.membership_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="账号" width="72">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date_joined" label="注册时间" width="120">
          <template #default="{ row }">{{ formatDate(row.date_joined) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="168" align="right" fixed="right">
          <template #default="{ row }">
            <el-tooltip content="编辑用户" placement="top">
              <el-button text :icon="Edit" aria-label="编辑用户" @click="handleEdit(row as User)" />
            </el-tooltip>
            <el-tooltip :content="row.is_active ? '禁用用户' : '启用用户'" placement="top">
              <el-button
                text
                :type="row.is_active ? 'warning' : 'success'"
                :icon="row.is_active ? CircleClose : CircleCheck"
                :aria-label="row.is_active ? '禁用用户' : '启用用户'"
                @click="handleToggleActive(row as User)"
              />
            </el-tooltip>
            <el-tooltip content="成员状态与离队交接" placement="top">
              <el-button text type="primary" :icon="RefreshRight" aria-label="成员状态与离队交接" @click="handleLifecycle(row as User)" />
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <div v-else v-loading="loading" class="mobile-users">
        <EmptyState v-if="userList.length === 0 && !loading" text="暂无用户" :compact="true" />
        <article v-for="row in userList" :key="row.id" class="mobile-user">
          <div class="mobile-user-heading">
            <div class="user-identity">
              <AvatarWithName :name="row.name || row.username" :avatar-url="row.avatar" :size="36" :show-name="false" />
              <div class="identity-text">
                <strong>{{ row.name || row.username }}</strong>
                <span>@{{ row.username }}</span>
              </div>
            </div>
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </div>
          <div class="mobile-user-meta">
            <el-tag :type="getRoleTagType(row.global_role) as any" size="small" effect="plain">
              {{ row.global_role_display || getRoleLabel(row.global_role) }}
            </el-tag>
            <el-tag :type="membershipStatusType(row.membership_status)" size="small" effect="plain">
              {{ membershipStatusLabel(row.membership_status) }}
            </el-tag>
            <span>{{ row.email }}</span>
            <span v-if="row.phone">{{ row.phone }}</span>
            <span>注册于 {{ formatDate(row.date_joined) }}</span>
          </div>
          <div class="mobile-user-actions">
            <el-button text :icon="Edit" @click="handleEdit(row as User)">编辑</el-button>
            <el-button
              text
              :type="row.is_active ? 'warning' : 'success'"
              :icon="row.is_active ? CircleClose : CircleCheck"
              @click="handleToggleActive(row as User)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button text type="primary" :icon="RefreshRight" @click="handleLifecycle(row as User)">状态与交接</el-button>
          </div>
        </article>
      </div>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <AccessiblePagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </section>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="isEdit ? '编辑用户' : '新建用户'"
      width="620px"
      :fullscreen="isMobile"
      append-to-body
      @close="handleClose"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        :label-width="isMobile ? 'auto' : '80px'"
        :label-position="isMobile ? 'top' : 'right'"
        class="user-form"
      >
        <el-alert
          title="“操作老师”全局只能有一位；其他老师请使用“普通成员”，再到团队组织中设置为“查看老师（只读）”。"
          type="info"
          :closable="false"
          show-icon
          class="teacher-mode-alert"
        />
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="学校">
          <el-input v-model="form.school" placeholder="请输入学校" />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="form.grade" placeholder="例如 2024级" />
        </el-form-item>
        <el-form-item label="专业">
          <el-input v-model="form.major" placeholder="请输入专业" />
        </el-form-item>
        <el-form-item label="角色" prop="global_role">
          <el-select v-model="form.global_role" placeholder="选择角色" style="width: 100%">
            <el-option
              v-for="(item, key) in ROLE_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="确认密码" prop="password_confirm">
          <el-input v-model="form.password_confirm" type="password" placeholder="请再次输入密码" show-password />
        </el-form-item>
        <el-form-item v-if="isEdit" label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="lifecycleDialogVisible"
      title="成员状态与离队交接"
      width="560px"
      :fullscreen="isMobile"
      append-to-body
    >
      <el-alert
        title="离队不会删除账户、贡献、项目或文件历史；若该成员是项目负责人，必须选择能够接手其项目的在队成员。"
        type="info"
        :closable="false"
        show-icon
        class="lifecycle-alert"
      />
      <el-form label-width="92px" :label-position="isMobile ? 'top' : 'right'">
        <el-form-item label="成员">
          <strong>{{ lifecycleForm.name }}</strong>
        </el-form-item>
        <el-form-item label="新状态" required>
          <el-select v-model="lifecycleForm.status" style="width: 100%">
            <el-option label="在队" value="active" />
            <el-option label="暂离" value="on_leave" />
            <el-option label="已离队" value="exited" />
            <el-option label="外部协作者" value="external" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="lifecycleForm.status === 'exited'" label="工作交接">
          <el-select
            v-model="lifecycleForm.handover_to"
            clearable
            filterable
            placeholder="如负责项目，请选择接手人"
            style="width: 100%"
          >
            <el-option
              v-for="candidate in handoverCandidates"
              :key="candidate.id"
              :label="`${candidate.name} · ${candidate.email}`"
              :value="candidate.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="原因说明" :required="lifecycleForm.status === 'exited'">
          <el-input
            v-model="lifecycleForm.reason"
            type="textarea"
            :rows="3"
            placeholder="记录暂离、离队或重新加入的原因"
          />
        </el-form-item>
        <el-form-item v-if="lifecycleForm.status === 'exited'" label="交接说明">
          <el-input
            v-model="lifecycleForm.handover_notes"
            type="textarea"
            :rows="3"
            placeholder="记录资料、任务、经费及知识产权交接情况"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="lifecycleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="transitioning" @click="submitLifecycle">确认变更</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { CircleCheck, CircleClose, Edit, Plus, Search, Refresh, RefreshRight } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, transitionUser, type UserQueryParams } from '@/api/users'
import { formatDate, getRoleLabel, getRoleTagType } from '@/utils/format'
import { ROLE_MAP } from '@/utils/constants'
import type { User, UserFormData, UserRole } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import AvatarWithName from '@/components/AvatarWithName.vue'
import { useDevice } from '@/composables/useDevice'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const { isMobile } = useDevice()

const loading = ref(false)
const userList = ref<User[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const submitting = ref(false)
const transitioning = ref(false)
const formRef = ref<FormInstance>()
const editingId = ref<number | null>(null)

const isEdit = computed(() => editingId.value !== null)
const lifecycleDialogVisible = ref(false)
const lifecycleForm = reactive({
  user_id: 0,
  name: '',
  status: 'active' as 'active' | 'on_leave' | 'exited' | 'external',
  reason: '',
  handover_to: undefined as number | undefined,
  handover_notes: '',
})
const handoverCandidates = computed(() =>
  userList.value.filter((user) =>
    user.id !== lifecycleForm.user_id
    && user.is_active
    && user.membership_status !== 'exited'
  )
)

const queryParams = reactive<UserQueryParams>({
  page: 1,
  page_size: appStore.itemsPerPage,
  search: '',
  global_role: '',
  membership_status: '',
})

// 默认表单
const defaultForm: UserFormData = {
  username: '',
  email: '',
  name: '',
  global_role: 'member' as UserRole,
  phone: '',
  school: '',
  grade: '',
  major: '',
  password: '',
  password_confirm: '',
  is_active: true,
}

const form = reactive<UserFormData>({ ...defaultForm })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  global_role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  password_confirm: [
    {
      required: true,
      validator: (_rule: any, value: string, callback: any) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const params: any = { ...queryParams }
    if (!params.global_role) delete params.global_role
    if (!params.search) delete params.search
    const res = await getUsers(params)
    userList.value = res.results
    total.value = res.count
  } catch {
    // 已处理
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  queryParams.page = 1
  loadData()
}

function handleReset(): void {
  queryParams.search = ''
  queryParams.global_role = ''
  queryParams.membership_status = ''
  queryParams.page = 1
  loadData()
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

function handleCreate(): void {
  editingId.value = null
  Object.assign(form, defaultForm)
  formDialogVisible.value = true
}

function handleEdit(row: User): void {
  editingId.value = row.id
  Object.assign(form, {
    username: row.username,
    email: row.email,
    name: row.name,
    global_role: row.global_role,
    phone: row.phone || '',
    school: row.school || '',
    grade: row.grade || '',
    major: row.major || '',
    password: '',
    password_confirm: '',
    is_active: row.is_active,
  })
  formDialogVisible.value = true
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value && editingId.value) {
        const updateData: Partial<UserFormData> = { ...form }
        delete (updateData as any).password
        delete (updateData as any).password_confirm
        await updateUser(editingId.value, updateData)
        ElMessage.success('用户更新成功')
      } else {
        const createData: UserFormData = { ...form }
        await createUser(createData)
        ElMessage.success('用户创建成功')
      }
      formDialogVisible.value = false
      loadData()
    } catch {
      // 已处理
    } finally {
      submitting.value = false
    }
  })
}

function handleClose(): void {
  formRef.value?.resetFields()
  Object.assign(form, defaultForm)
  editingId.value = null
}

async function handleToggleActive(row: User): Promise<void> {
  try {
    await updateUser(row.id, { is_active: !row.is_active })
    ElMessage.success(row.is_active ? '已禁用' : '已启用')
    loadData()
  } catch {
    // 已处理
  }
}

function handleLifecycle(row: User): void {
  lifecycleForm.user_id = row.id
  lifecycleForm.name = row.name || row.username
  lifecycleForm.status = row.membership_status || 'active'
  lifecycleForm.reason = row.exit_reason || ''
  lifecycleForm.handover_to = row.handover_to || undefined
  lifecycleForm.handover_notes = row.handover_notes || ''
  lifecycleDialogVisible.value = true
}

async function submitLifecycle(): Promise<void> {
  if (lifecycleForm.status === 'exited' && !lifecycleForm.reason.trim()) {
    ElMessage.warning('请填写离队原因')
    return
  }
  transitioning.value = true
  try {
    await transitionUser(lifecycleForm.user_id, {
      status: lifecycleForm.status,
      reason: lifecycleForm.reason.trim(),
      ...(lifecycleForm.handover_to ? { handover_to: lifecycleForm.handover_to } : {}),
      handover_notes: lifecycleForm.handover_notes.trim(),
    })
    ElMessage.success('成员状态与交接记录已保存')
    lifecycleDialogVisible.value = false
    loadData()
  } catch {
    // 错误已统一处理
  } finally {
    transitioning.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.search-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 10px 14px;

  :deep(.el-form) {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px 16px;
  }

  :deep(.el-form-item) {
    margin: 0;
  }
}

.keyword-input { width: 220px; }
.role-select { width: 150px; }

.lifecycle-alert {
  margin-bottom: 18px;
}

.teacher-mode-alert {
  grid-column: 1 / -1;
  margin-bottom: 4px;
}

.result-count {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
}

.user-workspace {
  padding: 0;
  margin-top: var(--space-4);
  overflow: hidden;
}

.user-identity {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.identity-text {
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    overflow: hidden;
    color: var(--color-text);
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    overflow: hidden;
    color: var(--color-text-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 0 14px 14px;
}

.mobile-users {
  min-height: 160px;
  padding: 0 12px;
}

.mobile-user {
  padding: 13px 0 8px;
  border-bottom: 1px solid var(--color-border-light);

  &:last-child { border-bottom: 0; }
}

.mobile-user-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.mobile-user-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin: 8px 0 3px 45px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.mobile-user-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
}

@media screen and (min-width: 769px) {
  .user-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 16px;

    :deep(.el-form-item:nth-last-child(-n + 3)) {
      grid-column: 1 / -1;
    }
  }
}

@media screen and (max-width: 768px) {
  .search-bar {
    align-items: flex-start;
    flex-direction: column;
    padding: 10px 12px;

    :deep(.el-form),
    :deep(.el-form-item),
    :deep(.el-form-item__content) {
      width: 100%;
    }

    :deep(.el-form) {
      align-items: stretch;
      flex-direction: column;
      gap: 10px;
    }

    :deep(.el-form-item) {
      align-items: flex-start;
      flex-direction: column;
    }

    .keyword-input,
    .role-select {
      width: 100%;
    }
  }

  .pagination-wrapper {
    justify-content: center;
    padding: 0 6px 12px;
  }
}
</style>
