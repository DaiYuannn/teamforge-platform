<template>
  <el-dialog
    v-model="dialogVisible"
    class="project-form-dialog"
    :title="isEdit ? '编辑项目' : '新建项目'"
    width="760px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      class="project-form"
      :model="form"
      :rules="rules"
      label-position="top"
    >
      <section class="form-section">
        <h3>基本信息</h3>
        <div class="form-grid">
          <el-form-item class="form-field-wide" label="项目名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入项目名称" clearable />
          </el-form-item>
          <el-form-item label="项目编号" prop="code">
            <el-input v-model="form.code" placeholder="例如 XM-2026-001" clearable />
          </el-form-item>
          <el-form-item label="项目牵头负责人 ID" prop="leader">
            <el-input-number
              v-model="form.leader"
              :min="1"
              controls-position="right"
              placeholder="请输入牵头负责人 ID"
            />
          </el-form-item>
          <el-form-item class="form-field-wide" label="关联小组" prop="teams">
            <el-select
              v-model="form.teams"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="可关联一个或多个实际执行小组"
              :loading="teamsLoading"
            >
              <el-option
                v-for="team in teamOptions"
                :key="team.id"
                :label="team.parent_name ? `${team.parent_name} / ${team.name}` : team.name"
                :value="team.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item class="form-field-wide" label="项目可见范围" prop="visibility">
            <el-radio-group v-model="form.visibility">
              <el-radio-button value="project">仅项目成员</el-radio-button>
              <el-radio-button value="teams">关联小组</el-radio-button>
              <el-radio-button value="organization">全团队</el-radio-button>
            </el-radio-group>
            <p class="field-hint">
              “关联小组”只允许所选小组成员查看；“全团队”仍不会向未登录访客公开。
            </p>
          </el-form-item>
          <el-form-item v-if="isEdit" label="项目状态" prop="status">
            <el-select v-model="form.status" placeholder="选择状态">
              <el-option
                v-for="(item, key) in PROJECT_STATUS_MAP"
                :key="key"
                :label="item.label"
                :value="key"
              />
            </el-select>
          </el-form-item>
        </div>
      </section>

      <section class="form-section">
        <h3>计划周期</h3>
        <div class="form-grid">
          <el-form-item label="开始日期" prop="start_date">
            <el-date-picker
              v-model="form.start_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择开始日期"
              @change="handleStartDateChange"
            />
          </el-form-item>
          <el-form-item label="预计结束" prop="planned_end_date">
            <el-date-picker
              v-model="form.planned_end_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择预计结束日期"
              :disabled-date="disableEndDate"
            />
          </el-form-item>
        </div>
      </section>

      <section class="form-section form-section-last">
        <h3>项目说明</h3>
        <el-form-item class="description-field" label="项目描述" prop="intro">
          <el-input
            v-model="form.intro"
            type="textarea"
            :rows="4"
            resize="vertical"
            placeholder="请输入项目背景、目标或关键说明"
          />
        </el-form-item>
      </section>
    </el-form>

    <template #footer>
      <div class="dialog-actions">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '创建项目' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createProject, updateProject } from '@/api/projects'
import { getTeams, type Team } from '@/api/teams'
import { PROJECT_STATUS_MAP } from '@/utils/constants'
import type { ProjectFormData } from '@/types'

type EditableProjectFormData = ProjectFormData & { id?: number }

/**
 * 新建/编辑项目弹窗
 */
const props = defineProps<{
  /** 是否显示 */
  visible: boolean
  /** 编辑时的表单数据（null 表示新建） */
  formData: EditableProjectFormData | null
}>()

const emit = defineEmits<{
  /** 更新 visible */
  (e: 'update:visible', val: boolean): void
  /** 操作成功 */
  (e: 'success'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const teamsLoading = ref(false)
const teamOptions = ref<Team[]>([])

// 是否编辑模式
const isEdit = computed(() => !!props.formData)

// 弹窗可见性（双向绑定）
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

// 默认表单
const defaultForm: ProjectFormData = {
  name: '',
  code: '',
  intro: '',
  leader: 0,
  teams: [],
  visibility: 'organization',
  start_date: '',
  planned_end_date: '',
  status: 'active',
}

// 表单数据
const form = reactive<ProjectFormData>({ ...defaultForm })

// 验证规则
const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入项目编号', trigger: 'blur' }],
  leader: [
    { required: true, message: '请输入负责人 ID', trigger: 'change' },
    { type: 'number', min: 1, message: '负责人 ID 必须大于 0', trigger: 'change' },
  ],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  planned_end_date: [
    { required: true, message: '请选择预计结束日期', trigger: 'change' },
    {
      validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => {
        if (value && form.start_date && value < form.start_date) {
          callback(new Error('预计结束日期不能早于开始日期'))
          return
        }
        callback()
      },
      trigger: 'change',
    },
  ],
}

function syncForm(data: EditableProjectFormData | null): void {
  Object.assign(form, defaultForm)
  if (!data) return
  Object.assign(form, {
    name: data.name,
    code: data.code,
    intro: data.intro || '',
    leader: data.leader,
    teams: data.teams || [],
    visibility: data.visibility || 'organization',
    start_date: data.start_date,
    planned_end_date: data.planned_end_date,
    status: data.status || 'active',
  })
}

// 监听 props.formData 变化，初始化表单
watch(
  () => props.formData,
  (val) => {
    syncForm(val)
  },
  { immediate: true }
)

function disableEndDate(date: Date): boolean {
  if (!form.start_date) return false
  const startDate = new Date(`${form.start_date}T00:00:00`)
  return date.getTime() < startDate.getTime()
}

function handleStartDateChange(): void {
  if (form.planned_end_date) {
    formRef.value?.validateField('planned_end_date')
  }
}

// 提交表单
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const payload: ProjectFormData = {
    name: form.name.trim(),
    code: form.code.trim(),
    intro: form.intro?.trim() || '',
    leader: form.leader,
    teams: form.teams || [],
    visibility: form.visibility || 'organization',
    start_date: form.start_date,
    planned_end_date: form.planned_end_date,
    status: form.status,
  }

  if (isEdit.value && !props.formData?.id) {
    ElMessage.error('缺少项目 ID，无法保存修改')
    return
  }

  submitting.value = true
  try {
    if (isEdit.value && props.formData?.id) {
      await updateProject(props.formData.id, payload)
      ElMessage.success('项目更新成功')
    } else {
      await createProject(payload)
      ElMessage.success('项目创建成功')
    }
    emit('success')
    dialogVisible.value = false
  } catch {
    // 错误已由拦截器处理
  } finally {
    submitting.value = false
  }
}

// 关闭弹窗
function handleClose(): void {
  formRef.value?.resetFields()
  syncForm(null)
}

async function loadTeams(): Promise<void> {
  if (teamOptions.value.length || teamsLoading.value) return
  teamsLoading.value = true
  try {
    const response = await getTeams()
    teamOptions.value = response.results
  } finally {
    teamsLoading.value = false
  }
}

// 监听弹窗打开时加载比赛列表
watch(
  () => props.visible,
  (val) => {
    if (val) {
      syncForm(props.formData)
      loadTeams()
    }
  }
)
</script>

<style lang="scss" scoped>
.project-form {
  min-width: 0;
}

.form-section {
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border-light);
}

.form-section + .form-section {
  padding-top: 20px;
}

.form-section-last {
  padding-bottom: 0;
  border-bottom: 0;
}

.form-section h3 {
  margin-bottom: 14px;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 18px;
}

.form-field-wide {
  grid-column: 1 / -1;
}

.project-form :deep(.el-form-item) {
  min-width: 0;
  margin-bottom: 0;
}

.project-form :deep(.el-form-item__label) {
  height: auto;
  margin-bottom: 7px;
  color: var(--color-text-regular);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
}

.project-form :deep(.el-input),
.project-form :deep(.el-input-number),
.project-form :deep(.el-select),
.project-form :deep(.el-date-editor) {
  width: 100%;
}

.field-hint {
  margin-top: 6px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.description-field :deep(.el-textarea__inner) {
  min-height: 104px !important;
  line-height: 1.6;
}

.dialog-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.dialog-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

@media screen and (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
    gap: 15px;
  }

  .form-field-wide {
    grid-column: 1;
  }

  .form-section {
    padding-bottom: 18px;
  }

  .form-section + .form-section {
    padding-top: 18px;
  }
}
</style>
