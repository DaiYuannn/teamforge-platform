<template>
  <div class="page-container">
    <PageHeader title="用户管理" subtitle="系统用户与权限管理">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新建用户</el-button>
      </template>
    </PageHeader>

    <!-- 搜索筛选 -->
    <div class="card search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="queryParams.search"
            placeholder="用户名/邮箱/姓名"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="queryParams.global_role" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="(item, key) in ROLE_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 用户列表表格 -->
    <div class="card mt-16">
      <el-table v-loading="loading" :data="userList" border stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="global_role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.global_role) as any" size="small">
              {{ row.global_role_display || getRoleLabel(row.global_role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date_joined" label="注册时间" width="120">
          <template #default="{ row }">{{ formatDate(row.date_joined) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row as User)">编辑</el-button>
            <el-button
              :type="row.is_active ? 'warning' : 'success'"
              link
              @click="handleToggleActive(row as User)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button type="danger" link @click="handleDelete(row as User)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
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
    </div>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="isEdit ? '编辑用户' : '新建用户'"
      width="550px"
      @close="handleClose"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, deleteUser, type UserQueryParams } from '@/api/users'
import { formatDate, getRoleLabel, getRoleTagType } from '@/utils/format'
import { ROLE_MAP } from '@/utils/constants'
import type { User, UserFormData, UserRole } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const loading = ref(false)
const userList = ref<User[]>([])
const total = ref(0)
const formDialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const editingId = ref<number | null>(null)

const isEdit = computed(() => editingId.value !== null)

const queryParams = reactive<UserQueryParams>({
  page: 1,
  page_size: 10,
  search: '',
  global_role: '',
})

// 默认表单
const defaultForm: UserFormData = {
  username: '',
  email: '',
  name: '',
  global_role: 'member' as UserRole,
  phone: '',
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
  queryParams.page = 1
  loadData()
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

async function handleDelete(row: User): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除用户「${row.name || row.username}」吗？`, '提示', { type: 'warning' })
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // 取消
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.mt-16 { margin-top: 16px; }
.search-bar { padding: 16px; }
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
