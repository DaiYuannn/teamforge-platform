<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑贡献' : '填写贡献'"
    :width="dialogWidth"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <div class="form-grid">
        <el-form-item label="项目" prop="project">
          <el-select v-model="form.project" placeholder="选择所属项目" filterable>
            <el-option
              v-for="project in projectOptions"
              :key="project.id"
              :label="`${project.name}（${project.code}）`"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="贡献类型" prop="contribution_type">
          <el-select v-model="form.contribution_type" placeholder="选择贡献类型">
            <el-option
              v-for="(item, key) in CONTRIBUTION_TYPE_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="统计周期" prop="period">
          <el-input v-model="form.period" placeholder="如 2026-07 或 2026春季" />
        </el-form-item>
      </div>

      <el-form-item label="贡献内容" prop="content">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="5"
          maxlength="2000"
          show-word-limit
          placeholder="请具体描述完成的工作与产出"
        />
      </el-form-item>

      <el-form-item label="证明材料">
        <div class="proof-field">
          <el-button
            v-if="isEdit && contribution?.proof_file && !proofFile"
            class="existing-proof"
            type="primary"
            link
            :icon="Document"
            :loading="proofDownloading"
            @click="handleDownloadProof"
          >
            下载现有材料
          </el-button>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :on-exceed="handleFileExceed"
          >
            <el-button :icon="Upload">{{ proofFile ? '更换文件' : '选择文件' }}</el-button>
          </el-upload>
          <span class="proof-name">{{ proofFile?.name || '未选择新文件' }}</span>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-actions">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '提交审核' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  ElMessage,
  type FormInstance,
  type FormRules,
  type UploadFile,
  type UploadInstance,
} from 'element-plus'
import { Document, Upload } from '@element-plus/icons-vue'
import { createContribution, updateContribution } from '@/api/contributions'
import { downloadFile } from '@/api/files'
import { getProjects } from '@/api/projects'
import { CONTRIBUTION_TYPE_MAP } from '@/utils/constants'
import { downloadBlob } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import type { Contribution, Project } from '@/types'

const props = defineProps<{
  visible: boolean
  contribution?: Contribution | null
}>()

const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'success'): void
}>()

const { isMobile } = useDevice()
const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()
const submitting = ref(false)
const proofDownloading = ref(false)
const projectOptions = ref<Project[]>([])
const proofFile = ref<File | null>(null)
const dialogWidth = computed(() => (isMobile.value ? 'calc(100vw - 24px)' : '620px'))
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})
const isEdit = computed(() => Boolean(props.contribution?.id))
const defaultForm = {
  project: '' as number | string,
  contribution_type: '',
  content: '',
  period: new Date().toISOString().slice(0, 7),
}
const form = reactive({ ...defaultForm })
const rules: FormRules = {
  project: [{ required: true, message: '请选择项目', trigger: 'change' }],
  contribution_type: [{ required: true, message: '请选择贡献类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入贡献内容', trigger: 'blur' }],
  period: [{ required: true, message: '请输入统计周期', trigger: 'blur' }],
}

async function loadProjects(): Promise<void> {
  if (projectOptions.value.length) return
  try {
    const response = await getProjects({ page: 1, page_size: 100 })
    projectOptions.value = response.results
  } catch {
    // 请求错误已由拦截器处理。
  }
}

function resetForm(): void {
  formRef.value?.clearValidate()
  Object.assign(form, defaultForm)
  proofFile.value = null
  uploadRef.value?.clearFiles()
}

function syncContribution(): void {
  resetForm()
  if (!props.contribution) return
  Object.assign(form, {
    project: props.contribution.project,
    contribution_type: props.contribution.contribution_type,
    content: props.contribution.content,
    period: props.contribution.period || new Date().toISOString().slice(0, 7),
  })
}

function handleFileChange(file: UploadFile): void {
  proofFile.value = file.raw || null
}

function handleFileRemove(): void {
  proofFile.value = null
}

function handleFileExceed(): void {
  ElMessage.warning('每条贡献仅支持一个证明文件')
}

async function handleDownloadProof(): Promise<void> {
  if (!props.contribution?.proof_file) return
  proofDownloading.value = true
  try {
    const blob = await downloadFile(props.contribution.proof_file)
    downloadBlob(blob, props.contribution.proof_file_name || '贡献证明材料')
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    proofDownloading.value = false
  }
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const payload = new FormData()
  payload.append('project', String(form.project))
  payload.append('contribution_type', form.contribution_type)
  payload.append('content', form.content.trim())
  payload.append('period', form.period.trim())
  if (proofFile.value) payload.append('proof_upload', proofFile.value)

  submitting.value = true
  try {
    if (isEdit.value && props.contribution) {
      await updateContribution(props.contribution.id, payload)
      ElMessage.success('贡献已更新')
    } else {
      await createContribution(payload)
      ElMessage.success('贡献已提交审核')
    }
    emit('success')
    dialogVisible.value = false
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    submitting.value = false
  }
}

function handleClose(): void {
  resetForm()
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      loadProjects()
      syncContribution()
    }
  },
)
</script>

<style lang="scss" scoped>
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

:deep(.el-select) {
  width: 100%;
}

.proof-field {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  width: 100%;
}

.existing-proof {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-primary);
  font-size: 13px;
}

.proof-name {
  min-width: 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media screen and (max-width: 768px) {
  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .proof-field {
    align-items: flex-start;
    flex-direction: column;
  }

  .proof-name {
    max-width: 100%;
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
