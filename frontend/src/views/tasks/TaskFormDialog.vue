<template>
  <el-dialog
    v-model="dialogVisible"
    class="task-form-dialog"
    :title="isEdit ? '编辑任务' : '新建任务'"
    width="min(720px, calc(100vw - 32px))"
    :fullscreen="isMobile"
    :close-on-click-modal="false"
    append-to-body
    destroy-on-close
    @closed="handleClosed"
  >
    <el-form
      ref="formRef"
      class="task-form"
      :model="form"
      :rules="rules"
      label-position="top"
      status-icon
    >
      <div class="form-grid">
        <el-form-item label="任务标题" prop="title" class="field-wide">
          <el-input
            v-model="form.title"
            maxlength="200"
            show-word-limit
            placeholder="输入清晰、可执行的任务标题"
          />
        </el-form-item>

        <el-form-item label="所属项目" prop="project">
          <el-select v-model="form.project" placeholder="选择所属项目" filterable @change="handleProjectChange">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="任务负责人" prop="assignee">
          <el-select v-model="form.assignee" placeholder="选择任务负责人" filterable>
            <el-option
              v-for="user in assignees"
              :key="user.id"
              :label="user.name || user.username"
              :value="user.id"
            >
              <span class="user-option-name">{{ user.name || user.username }}</span>
              <span class="user-option-email">{{ user.email }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="协作执行人" prop="collaborator_ids" class="field-wide">
          <el-select
            v-model="form.collaborator_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择共同执行任务的成员"
          >
            <el-option
              v-for="user in assignees"
              :key="user.id"
              :label="user.name || user.username"
              :value="user.id"
            >
              <span class="user-option-name">{{ user.name || user.username }}</span>
              <span class="user-option-email">{{ user.email }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="任务验收人" prop="reviewer">
          <el-select
            v-model="form.reviewer"
            placeholder="可选；未指定时由项目负责人审核"
            filterable
            clearable
          >
            <el-option
              v-for="user in assignees"
              :key="user.id"
              :label="user.name || user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" placeholder="选择优先级">
            <el-option
              v-for="(item, value) in TASK_PRIORITY_MAP"
              :key="value"
              :label="item.label"
              :value="value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="任务状态" prop="status">
          <el-select v-model="form.status" placeholder="选择状态" :disabled="!isEdit">
            <el-option
              v-for="(item, value) in TASK_STATUS_MAP"
              :key="value"
              :label="item.label"
              :value="value"
              :disabled="isStatusOptionDisabled(value)"
            />
          </el-select>
          <span v-if="!isEdit" class="field-tip">新任务从“待办”开始，再按执行与审核流程推进。</span>
        </el-form-item>

        <el-form-item label="开始时间" prop="start_date">
          <el-date-picker
            v-model="form.start_date"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            format="YYYY-MM-DD HH:mm"
            placeholder="选择开始时间"
          />
        </el-form-item>

        <el-form-item label="截止时间" prop="deadline">
          <el-date-picker
            v-model="form.deadline"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            format="YYYY-MM-DD HH:mm"
            placeholder="选择截止时间"
          />
        </el-form-item>

        <el-form-item label="任务描述" prop="description" class="field-wide">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="5"
            maxlength="2000"
            show-word-limit
            resize="vertical"
            placeholder="补充验收标准、交付物或协作说明"
          />
        </el-form-item>

        <el-form-item label="延期原因" prop="delay_reason" class="field-wide">
          <el-input
            v-model="form.delay_reason"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            resize="vertical"
            :placeholder="form.status === 'overdue' ? '必填：说明延期原因和后续计划' : '如发生延期，可提前记录原因和调整计划'"
          />
        </el-form-item>

        <el-form-item label="完成说明" prop="completion_note" class="field-wide">
          <el-input
            v-model="form.completion_note"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            resize="vertical"
            placeholder="记录已完成内容、交付物位置和需要审核人关注的事项"
          />
        </el-form-item>

        <el-form-item label="任务附件" class="field-wide">
          <div class="attachment-field">
            <el-select
              v-model="form.attachment_ids"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择文件中心已有文件"
              :disabled="!form.project"
            >
              <el-option
                v-for="file in projectFiles"
                :key="file.id"
                :label="`${file.name} · v${file.version || 1}`"
                :value="file.id"
              />
            </el-select>
            <el-upload
              :auto-upload="false"
              multiple
              :on-change="handlePendingFile"
              :on-remove="handlePendingFileRemove"
            >
              <el-button :icon="Paperclip" :disabled="!form.project">添加新文件</el-button>
              <template #tip>
                <span class="attachment-tip">新文件会以“内部”级别保存到所选项目，并关联到任务。</span>
              </template>
            </el-upload>
          </div>
        </el-form-item>
      </div>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button :icon="Close" @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :icon="Check" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '创建任务' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { Check, Close, Paperclip } from '@element-plus/icons-vue'
import { createTask, updateTask } from '@/api/tasks'
import { getFilesByProject, uploadFile } from '@/api/files'
import { TASK_PRIORITY_MAP, TASK_STATUS_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import type { FileAsset, Project, TaskFormData, User } from '@/types'
import { getManagerTaskStatusTargets } from './taskWorkflow'

type EditableTaskForm = TaskFormData & { id: number }

const props = defineProps<{
  visible: boolean
  formData: EditableTaskForm | null
  projects: Project[]
  assignees: User[]
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}>()

const { isMobile } = useDevice(769)
const formRef = ref<FormInstance>()
const submitting = ref(false)
const projectFiles = ref<FileAsset[]>([])
const pendingFiles = ref<File[]>([])

const isEdit = computed(() => props.formData !== null)
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})

const defaultForm: TaskFormData = {
  title: '',
  description: '',
  project: 0,
  assignee: 0,
  collaborator_ids: [],
  reviewer: null,
  status: 'todo',
  priority: 'medium',
  start_date: '',
  deadline: '',
  delay_reason: '',
  completion_note: '',
  attachment_ids: [],
}

const form = reactive<TaskFormData>({ ...defaultForm })

function requiredSelection(label: string) {
  return (_rule: unknown, value: number, callback: (error?: Error) => void) => {
    if (!value || value < 1) callback(new Error(`请选择${label}`))
    else callback()
  }
}

function validateDeadline(_rule: unknown, value: string, callback: (error?: Error) => void): void {
  if (!value) {
    callback(new Error('请选择截止时间'))
    return
  }
  if (form.start_date && dayjs(value).isBefore(dayjs(form.start_date))) {
    callback(new Error('截止时间不能早于开始时间'))
    return
  }
  callback()
}

function validateDelayReason(
  _rule: unknown,
  value: string,
  callback: (error?: Error) => void,
): void {
  if (form.status === 'overdue' && !value?.trim()) {
    callback(new Error('进入已逾期状态必须填写延期原因'))
    return
  }
  callback()
}

const rules: FormRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  project: [{ validator: requiredSelection('所属项目'), trigger: 'change' }],
  assignee: [{ validator: requiredSelection('任务负责人'), trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  status: [{ required: true, message: '请选择任务状态', trigger: 'change' }],
  start_date: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  deadline: [{ validator: validateDeadline, trigger: 'change' }],
  delay_reason: [{ validator: validateDelayReason, trigger: 'blur' }],
}

function normalizeDateTime(value?: string): string {
  if (!value) return ''
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('YYYY-MM-DDTHH:mm:ss') : ''
}

function syncForm(data: EditableTaskForm | null): void {
  Object.assign(form, {
    ...defaultForm,
    collaborator_ids: [],
    attachment_ids: [],
  })
  if (!data) return
  Object.assign(form, {
    title: data.title,
    description: data.description || '',
    project: data.project,
    assignee: data.assignee,
    collaborator_ids: [...(data.collaborator_ids || [])],
    reviewer: data.reviewer ?? null,
    status: data.status || 'todo',
    priority: data.priority || 'medium',
    start_date: normalizeDateTime(data.start_date),
    deadline: normalizeDateTime(data.deadline),
    delay_reason: data.delay_reason || '',
    completion_note: data.completion_note || '',
    attachment_ids: data.attachment_ids || [],
  })
  loadProjectFiles(data.project)
}

function isStatusOptionDisabled(value: string): boolean {
  if (!props.formData) return value !== 'todo'
  const currentStatus = props.formData.status || 'todo'
  return (
    value !== currentStatus
    && !getManagerTaskStatusTargets(currentStatus).includes(value as typeof currentStatus)
  )
}

watch(
  () => props.formData,
  (data) => syncForm(data),
  { immediate: true },
)

async function handleSubmit(): Promise<void> {
  if (!formRef.value || submitting.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload: TaskFormData = { ...form }
    const task = props.formData
      ? await updateTask(props.formData.id, payload)
      : await createTask(payload)
    if (props.formData) {
      ElMessage.success('任务已更新')
    } else {
      ElMessage.success('任务已创建')
    }
    if (pendingFiles.value.length) {
      const uploaded = await Promise.all(
        pendingFiles.value.map((file) =>
          uploadFile(form.project, file, {
            project: form.project,
            level: 'internal',
          }),
        ),
      )
      const attachmentIds = [
        ...(form.attachment_ids || []),
        ...uploaded.map((file) => file.id),
      ]
      await updateTask(task.id, { attachment_ids: attachmentIds })
    }
    emit('success')
    dialogVisible.value = false
  } catch {
    // 请求层统一处理错误。
  } finally {
    submitting.value = false
  }
}

function handleClosed(): void {
  formRef.value?.resetFields()
  syncForm(null)
  projectFiles.value = []
  pendingFiles.value = []
}

async function loadProjectFiles(projectId: number): Promise<void> {
  if (!projectId) {
    projectFiles.value = []
    return
  }
  try {
    projectFiles.value = (await getFilesByProject(projectId))
      .filter((file) => file.level !== 'sensitive')
  } catch {
    projectFiles.value = []
  }
}

function handleProjectChange(projectId: number): void {
  form.collaborator_ids = []
  form.reviewer = null
  form.attachment_ids = []
  pendingFiles.value = []
  loadProjectFiles(projectId)
}

function handlePendingFile(uploadFileItem: UploadFile): void {
  if (!uploadFileItem.raw) return
  if (!pendingFiles.value.some((file) => file === uploadFileItem.raw)) {
    pendingFiles.value.push(uploadFileItem.raw)
  }
}

function handlePendingFileRemove(uploadFileItem: UploadFile): void {
  if (!uploadFileItem.raw) return
  pendingFiles.value = pendingFiles.value.filter((file) => file !== uploadFileItem.raw)
}
</script>

<style lang="scss" scoped>
.task-form {
  width: 100%;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 var(--space-4);
}

.field-wide {
  grid-column: 1 / -1;
}

.task-form :deep(.el-form-item) {
  min-width: 0;
  margin-bottom: var(--space-4);
}

.task-form :deep(.el-form-item__label) {
  padding-bottom: 6px;
  color: var(--color-text-regular);
  font-size: var(--font-size-sm);
  font-weight: 500;
  line-height: 1.35;
}

.task-form :deep(.el-select),
.task-form :deep(.el-date-editor),
.task-form :deep(.el-input) {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.attachment-field {
  display: grid;
  width: 100%;
  gap: 10px;
}

.attachment-tip {
  display: block;
  margin-top: 5px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.field-tip {
  display: block;
  margin-top: 5px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.dialog-footer :deep(.el-button) {
  min-width: 104px;
  margin: 0;
}

.user-option-name {
  color: var(--color-text);
}

.user-option-email {
  float: right;
  max-width: 52%;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media screen and (max-width: 768px) {
  :global(.task-form-dialog.el-dialog.is-fullscreen) {
    display: flex;
    width: 100% !important;
    max-width: none;
    height: 100dvh;
    margin: 0;
    flex-direction: column;
    border-radius: 0;
    box-shadow: none;
  }

  :global(.task-form-dialog.el-dialog.is-fullscreen .el-dialog__header) {
    flex: 0 0 auto;
    padding: var(--space-4);
  }

  :global(.task-form-dialog.el-dialog.is-fullscreen .el-dialog__body) {
    flex: 1;
    min-height: 0;
    max-height: none;
    padding: var(--space-4);
    overflow-y: auto;
  }

  :global(.task-form-dialog.el-dialog.is-fullscreen .el-dialog__footer) {
    flex: 0 0 auto;
    padding: var(--space-3) var(--space-4) max(var(--space-4), env(safe-area-inset-bottom));
    background: var(--color-surface);
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .field-wide {
    grid-column: auto;
  }

  .dialog-footer {
    display: grid;
    grid-template-columns: 1fr 1fr;
    width: 100%;
  }

  .dialog-footer :deep(.el-button) {
    width: 100%;
    min-width: 0;
  }
}
</style>
