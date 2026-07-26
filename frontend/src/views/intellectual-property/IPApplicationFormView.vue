<template>
  <div class="page-container">
    <PageHeader :title="isEdit ? '编辑申请' : '新建申请'" subtitle="建立从材料撰写、申请执行到负责人审核和老师确认的完整责任链">
      <template #actions>
        <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      </template>
    </PageHeader>

    <section class="form-surface">
      <header class="form-section-header">
        <h2>成果档案</h2>
        <p>这些信息将作为后续材料、审核与授权流程的基础。</p>
      </header>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        :label-width="isMobile ? 'auto' : '112px'"
        :label-position="isMobile ? 'top' : 'right'"
        v-loading="loading"
      >
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="成果名称" prop="title">
              <el-input v-model="form.title" placeholder="请输入成果名称" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="内部编号" prop="application_code">
              <el-input v-model="form.application_code" placeholder="请输入内部编号" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="成果类型" prop="ip_type">
              <el-select v-model="form.ip_type" placeholder="请选择成果类型" style="width: 100%">
                <el-option
                  v-for="(item, key) in IP_TYPE_MAP"
                  :key="key"
                  :label="item.label"
                  :value="key"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="关联项目" prop="related_project">
              <el-select
                v-model="form.related_project"
                :placeholder="relatedProjectRequired ? '请选择关联项目' : '选择关联项目（可选）'"
                :clearable="isPrivileged"
                filterable
                style="width: 100%"
                @change="handleProjectChange"
              >
                <el-option
                  v-for="proj in projectList"
                  :key="proj.id"
                  :label="proj.name"
                  :value="proj.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="开始日期" prop="start_date">
              <el-date-picker
                v-model="form.start_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择申请启动日期"
                clearable
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="form-subsection">
          <h3>责任分工</h3>
          <p>项目内职责仅可分配给有效成员；负责人审核人与老师确认人按流程角色校验。</p>
        </div>

        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="主导撰写人" prop="main_writer">
              <el-select
                v-model="form.main_writer"
                :placeholder="form.related_project || isPrivileged ? '请选择主导撰写人' : '请先选择关联项目'"
                clearable
                filterable
                :loading="participantsLoading"
                :disabled="!canManageRoles || (!form.related_project && !isPrivileged)"
                style="width: 100%"
              >
                <el-option
                  v-for="user in userList"
                  :key="user.id"
                  :label="user.name || user.username || user.email"
                  :value="user.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="申请执行人" prop="applicant_executor">
              <el-select
                v-model="form.applicant_executor"
                placeholder="请选择申请执行人"
                clearable
                filterable
                :loading="participantsLoading"
                :disabled="!canManageRoles || (!form.related_project && !isPrivileged)"
                style="width: 100%"
              >
                <el-option
                  v-for="user in userList"
                  :key="user.id"
                  :label="user.name || user.username || user.email"
                  :value="user.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="材料整理人" prop="material_manager">
              <el-select
                v-model="form.material_manager"
                placeholder="请选择材料整理人"
                clearable
                filterable
                :loading="participantsLoading"
                :disabled="!canManageRoles || (!form.related_project && !isPrivileged)"
                style="width: 100%"
              >
                <el-option
                  v-for="user in userList"
                  :key="user.id"
                  :label="user.name || user.username || user.email"
                  :value="user.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="负责人审核人" prop="project_reviewer">
              <el-select
                v-model="form.project_reviewer"
                placeholder="关联项目负责人"
                :disabled="!canManageRoles || !form.related_project"
                style="width: 100%"
              >
                <el-option
                  v-for="user in projectReviewerOptions"
                  :key="user.id"
                  :label="user.name || user.username || user.email"
                  :value="user.id"
                  :disabled="user.id !== selectedProject?.leader"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="老师确认人" prop="teacher_confirmer">
              <el-select
                v-model="form.teacher_confirmer"
                placeholder="请选择老师确认人"
                clearable
                filterable
                :loading="teachersLoading"
                :disabled="!canManageRoles"
                style="width: 100%"
              >
                <el-option
                  v-for="user in teacherList"
                  :key="user.id"
                  :label="user.name || user.username || user.email"
                  :value="user.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="当前问题" prop="current_problem">
          <el-input
            v-model="form.current_problem"
            type="textarea"
            :rows="3"
            placeholder="记录当前阻塞、退回意见或待确认事项；无问题可留空"
          />
        </el-form-item>

        <el-form-item label="成果简介" prop="intro">
          <el-input
            v-model="form.intro"
            type="textarea"
            :rows="4"
            placeholder="请输入成果简介，描述成果的主要内容和创新点"
          />
        </el-form-item>

        <el-form-item class="form-actions">
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '创建申请' }}
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { createIPApplication, updateIPApplication, getIPApplication } from '@/api/intellectualProperty'
import { getProject, getProjectMembers, getProjects } from '@/api/projects'
import { getUsers } from '@/api/users'
import { IP_TYPE_MAP } from '@/utils/constants'
import type { Project } from '@/types'
import type { IPParticipantOption } from '@/types/intellectualProperty'
import PageHeader from '@/components/PageHeader.vue'
import { useDevice } from '@/composables/useDevice'
import { useUserStore } from '@/stores/user'
import {
  buildInternalParticipantOptions,
  buildProjectParticipantOptions,
  buildTeacherConfirmerOptions,
  normalizeIPProjectFilter,
  resolveIPCreateProjectDeepLink,
} from './ipWorkflow'

const route = useRoute()
const router = useRouter()
const { isMobile } = useDevice()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)
const participantsLoading = ref(false)
const teachersLoading = ref(false)
const projectList = ref<Project[]>([])
const userList = ref<IPParticipantOption[]>([])
const teacherList = ref<IPParticipantOption[]>([])
const loadedReviewerOption = ref<IPParticipantOption | null>(null)
const loadedTeacherOption = ref<IPParticipantOption | null>(null)

// 当前编辑入口使用 create?id=...，同时兼容未来的 params 路由。
const editId = computed(() => Number(route.params.id || route.query.id) || 0)
const isEdit = computed(() => editId.value > 0)
const isPrivileged = computed(() => userStore.role === 'teacher' || userStore.role === 'sys_admin')
const relatedProjectRequired = computed(() => !isEdit.value && !isPrivileged.value)
const selectedProject = computed(() =>
  projectList.value.find((project) => project.id === form.related_project) || null,
)
const canManageRoles = computed(() =>
  isPrivileged.value
  || Boolean(selectedProject.value?.leader === userStore.userInfo?.id),
)
const projectReviewerOptions = computed<IPParticipantOption[]>(() => {
  const options: IPParticipantOption[] = []
  const project = selectedProject.value
  if (project) {
    options.push({
      id: project.leader,
      name: project.leader_name || '项目负责人',
    })
  }
  const loaded = loadedReviewerOption.value
  if (loaded && !options.some((option) => option.id === loaded.id)) {
    options.push({ ...loaded, name: `${loaded.name || loaded.email || '历史审核人'}（历史分配）` })
  }
  return options
})

// 表单数据
const form = reactive({
  title: '',
  application_code: '',
  ip_type: '',
  related_project: null as number | null,
  main_writer: null as number | null,
  applicant_executor: null as number | null,
  material_manager: null as number | null,
  project_reviewer: null as number | null,
  teacher_confirmer: null as number | null,
  start_date: null as string | null,
  current_problem: '',
  intro: '',
})

// 验证规则
const rules = computed<FormRules>(() => ({
  title: [{ required: true, message: '请输入成果名称', trigger: 'blur' }],
  application_code: [{ required: true, message: '请输入内部编号', trigger: 'blur' }],
  ip_type: [{ required: true, message: '请选择成果类型', trigger: 'change' }],
  main_writer: [{ required: true, message: '请选择主导撰写人', trigger: 'change' }],
  related_project: relatedProjectRequired.value
    ? [{ required: true, message: '请选择你负责的关联项目', trigger: 'change' }]
    : [],
  project_reviewer: form.related_project
    ? [{ required: true, message: '请选择项目负责人审核人', trigger: 'change' }]
    : [],
}))

// 加载项目列表（下拉选项）
async function loadProjects(): Promise<void> {
  try {
    const user = userStore.userInfo || await userStore.fetchProfile()
    const response = await getProjects({
      page: 1,
      page_size: 100,
      ...(isPrivileged.value ? {} : { leader: user.id }),
    })
    const projects = [...response.results]
    const relatedProjectId = form.related_project
    if (
      relatedProjectId
      && !projects.some((project) => project.id === relatedProjectId)
      && (isEdit.value || isPrivileged.value)
    ) {
      try {
        projects.push(await getProject(relatedProjectId))
      } catch {
        // Keep the accessible project list when a stale deep link no longer resolves.
      }
    }
    projectList.value = projects
  } catch {
    projectList.value = []
  }
}

function resolveCreateProjectDeepLink(): number | null {
  if (isEdit.value) return null
  const requestedProjectId = resolveIPCreateProjectDeepLink(
    route.query.project_id,
    projectList.value,
  )
  if (!requestedProjectId) {
    if (!normalizeIPProjectFilter(route.query.project_id)) return null
    form.related_project = null
    ElMessage.warning('只能为自己负责的项目新建知识产权申请')
    return null
  }
  form.related_project = requestedProjectId
  return requestedProjectId
}

async function loadParticipantOptions(projectId: number | null): Promise<void> {
  participantsLoading.value = true
  try {
    if (!projectId) {
      if (!isPrivileged.value) {
        userList.value = []
        return
      }
      const response = await getUsers({ page: 1, page_size: 100, is_active: true })
      userList.value = buildInternalParticipantOptions(response.results)
      return
    }

    const project = projectList.value.find((item) => item.id === projectId) || await getProject(projectId)
    const members = await getProjectMembers(projectId)
    userList.value = buildProjectParticipantOptions(project, members)

  } catch {
    userList.value = []
  } finally {
    participantsLoading.value = false
  }
}

async function loadTeacherOptions(): Promise<void> {
  teachersLoading.value = true
  try {
    const [teachers, administrators] = await Promise.all([
      getUsers({ page: 1, page_size: 100, global_role: 'teacher', is_active: true }),
      getUsers({ page: 1, page_size: 100, global_role: 'sys_admin', is_active: true }),
    ])
    const options = buildTeacherConfirmerOptions([
      ...teachers.results,
      ...administrators.results,
    ])
    const loaded = loadedTeacherOption.value
    if (loaded && !options.some((option) => option.id === loaded.id)) {
      options.push(loaded)
    }
    teacherList.value = options
  } catch {
    teacherList.value = loadedTeacherOption.value ? [loadedTeacherOption.value] : []
  } finally {
    teachersLoading.value = false
  }
}

async function handleProjectChange(projectId: number | null): Promise<void> {
  form.main_writer = null
  form.applicant_executor = null
  form.material_manager = null
  const project = projectList.value.find((item) => item.id === projectId)
  form.project_reviewer = project?.leader || null
  await loadParticipantOptions(projectId)
}

// 编辑模式下加载已有数据
async function loadData(): Promise<void> {
  if (!isEdit.value) return
  const res = await getIPApplication(editId.value)
  Object.assign(form, {
    title: res.title || '',
    application_code: res.application_code || '',
    ip_type: res.ip_type || '',
    related_project: res.related_project || null,
    main_writer: res.main_writer || null,
    applicant_executor: res.applicant_executor || null,
    material_manager: res.material_manager || null,
    project_reviewer: res.project_reviewer || null,
    teacher_confirmer: res.teacher_confirmer || null,
    start_date: res.start_date || null,
    current_problem: res.current_problem || '',
    intro: res.intro || '',
  })
  loadedReviewerOption.value = res.project_reviewer_detail
    ? {
        id: res.project_reviewer_detail.id,
        name: res.project_reviewer_detail.name,
        email: res.project_reviewer_detail.email,
      }
    : null
  loadedTeacherOption.value = res.teacher_confirmer_detail
    ? {
        id: res.teacher_confirmer_detail.id,
        name: res.teacher_confirmer_detail.name,
        email: res.teacher_confirmer_detail.email,
        global_role: res.teacher_confirmer_detail.global_role,
        membership_status: res.teacher_confirmer_detail.membership_status,
        is_active: res.teacher_confirmer_detail.is_active,
      }
    : null
}

// 提交表单
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const payload: Record<string, unknown> = { ...form }
      if (isEdit.value && !canManageRoles.value) {
        for (const field of [
          'related_project',
          'main_writer',
          'applicant_executor',
          'material_manager',
          'project_reviewer',
          'teacher_confirmer',
        ]) {
          delete payload[field]
        }
      }
      if (isEdit.value) {
        await updateIPApplication(editId.value, payload)
        ElMessage.success('申请更新成功')
      } else {
        await createIPApplication(payload)
        ElMessage.success('申请创建成功')
      }
      router.push('/intellectual-property')
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

async function initialize(): Promise<void> {
  loading.value = true
  try {
    if (!userStore.userInfo) await userStore.fetchProfile()
    await loadData()
    if (!isEdit.value) {
      form.related_project = normalizeIPProjectFilter(route.query.project_id) || null
    }
    await loadProjects()
    const deepLinkedProjectId = resolveCreateProjectDeepLink()
    await Promise.all([
      deepLinkedProjectId
        ? handleProjectChange(deepLinkedProjectId)
        : loadParticipantOptions(form.related_project),
      loadTeacherOptions(),
    ])
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    loading.value = false
  }
}

onMounted(initialize)
</script>

<style lang="scss" scoped>
.form-surface {
  max-width: 960px;
  padding: 22px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.form-section-header {
  margin-bottom: 22px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.form-section-header h2 {
  font-size: 16px;
  font-weight: 600;
}

.form-section-header p {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.form-subsection {
  margin: 6px 0 18px;
  padding: 14px 16px;
  background: var(--color-surface-subtle);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-sm);
}

.form-subsection h3 {
  font-size: 14px;
  font-weight: 600;
}

.form-subsection p {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.form-actions {
  margin-top: 8px;
  margin-bottom: 0;
}

@media screen and (max-width: 768px) {
  .form-surface {
    padding: 14px;
  }
}
</style>
