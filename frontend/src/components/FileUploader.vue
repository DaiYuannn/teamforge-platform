<template>
  <section class="file-uploader">
    <el-upload
      ref="uploadRef"
      class="upload-dropzone"
      :action="''"
      :auto-upload="false"
      :on-change="handleFileChange"
      :on-remove="handleFileRemove"
      :file-list="fileList"
      :limit="limit"
      :accept="accept"
      :disabled="uploading"
      drag
      multiple
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">
        将文件拖到此处，或<em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">{{ tip || uploadTipText }}</div>
      </template>
    </el-upload>

    <div class="upload-settings">
      <div class="level-selector">
        <span class="setting-label">文件级别</span>
        <el-radio-group v-model="permission" :disabled="uploading">
          <el-radio-button value="public"><el-icon><Share /></el-icon><span>公开</span></el-radio-button>
          <el-radio-button value="internal"><el-icon><User /></el-icon><span>内部</span></el-radio-button>
          <el-radio-button value="sensitive"><el-icon><Lock /></el-icon><span>敏感</span></el-radio-button>
        </el-radio-group>
      </div>

      <div class="level-notice" :class="`is-${permission}`">
        <el-icon><component :is="levelPresentation.icon" /></el-icon>
        <div>
          <strong>{{ levelPresentation.label }}</strong>
          <span>{{ levelPresentation.detail }}</span>
        </div>
      </div>

      <label class="description-field">
        <span class="setting-label">文件描述</span>
        <el-input
          v-model="description"
          type="textarea"
          :rows="2"
          :disabled="uploading"
          resize="vertical"
          placeholder="补充文件内容或版本说明（可选）"
        />
      </label>
    </div>

    <div class="upload-actions">
      <span>{{ fileList.length ? `已选择 ${fileList.length} 个文件` : '尚未选择文件' }}</span>
      <el-button
        type="primary"
        :icon="Upload"
        :loading="uploading"
        :disabled="fileList.length === 0"
        @click="handleUpload"
      >
        上传文件
      </el-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, Share, Upload, UploadFilled, User } from '@element-plus/icons-vue'
import type { UploadFile, UploadInstance } from 'element-plus'
import { uploadFile } from '@/api/files'
import type { FileLevel } from '@/types'

/**
 * 文件上传组件
 * 支持三级权限选择（公开/项目成员/仅负责人）
 */
const props = withDefaults(
  defineProps<{
    /** 项目 ID */
    projectId: number
    /** 允许的文件类型 */
    accept?: string
    /** 最大文件大小（MB） */
    maxSize?: number
    /** 文件数量限制 */
    limit?: number
    /** 提示文字 */
    tip?: string
  }>(),
  {
    accept: '',
    maxSize: 50,
    limit: 10,
    tip: '',
  }
)

const emit = defineEmits<{
  /** 上传成功 */
  (e: 'success'): void
}>()

// 上传提示文本
const uploadTipText = computed(() => {
  const typeText = props.accept || '所有类型'
  return `支持上传 ${typeText} 文件，单文件不超过 ${props.maxSize}MB`
})

const levelPresentation = computed(() => {
  const presentations = {
    public: { label: '公开文件', detail: '适用于可公开共享的项目材料', icon: Share },
    internal: { label: '内部文件', detail: '仅供项目相关成员协作使用', icon: User },
    sensitive: { label: '敏感文件', detail: '仅授权人员可访问，请确认内容级别', icon: Lock },
  }
  return presentations[permission.value]
})

const uploadRef = ref<UploadInstance>()
const fileList = ref<UploadFile[]>([])
const permission = ref<FileLevel>('internal')
const description = ref('')
const uploading = ref(false)

// 文件选择变化
function handleFileChange(file: UploadFile, files: UploadFile[]): void {
  // 检查文件大小
  const maxBytes = props.maxSize * 1024 * 1024
  if (file.size && file.size > maxBytes) {
    ElMessage.error(`文件 ${file.name} 超过 ${props.maxSize}MB 限制`)
    fileList.value = files.filter((f) => f.uid !== file.uid)
    return
  }
  fileList.value = files
}

// 文件移除
function handleFileRemove(file: UploadFile, files: UploadFile[]): void {
  fileList.value = files
}

// 执行上传
async function handleUpload(): Promise<void> {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  try {
    for (const file of fileList.value) {
      const rawFile = file.raw
      if (!rawFile) continue
      await uploadFile(props.projectId, rawFile, {
        project: props.projectId,
        level: permission.value,
        description: description.value,
      })
    }
    ElMessage.success('文件上传成功')
    fileList.value = []
    description.value = ''
    uploadRef.value?.clearFiles()
    emit('success')
  } catch {
    ElMessage.error('文件上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style lang="scss" scoped>
.file-uploader {
  min-width: 0;
}

.upload-dropzone :deep(.el-upload) {
  width: 100%;
}

.upload-dropzone :deep(.el-upload-dragger) {
  width: 100%;
  min-height: 154px;
  padding: 30px 18px 20px;
  background: var(--color-surface-subtle);
  border-color: var(--color-border);
  border-radius: var(--radius-sm);
}

.upload-dropzone :deep(.el-upload-dragger:hover) {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
}

.upload-dropzone :deep(.el-icon--upload) {
  margin-bottom: 8px;
  color: var(--color-primary);
  font-size: 34px;
}

.upload-dropzone :deep(.el-upload__text) {
  color: var(--color-text-regular);
  font-size: 13px;
}

.upload-dropzone :deep(.el-upload__text em) {
  color: var(--color-primary);
  font-style: normal;
  font-weight: 600;
}

.upload-dropzone :deep(.el-upload__tip) {
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.upload-settings {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(280px, 1.2fr);
  gap: 14px 18px;
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid var(--color-border-light);
}

.level-selector,
.description-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 8px;
}

.setting-label {
  color: var(--color-text-regular);
  font-size: 12px;
  font-weight: 600;
}

.level-selector :deep(.el-radio-group) {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: 100%;
}

.level-selector :deep(.el-radio-button) {
  min-width: 0;
}

.level-selector :deep(.el-radio-button__inner) {
  display: flex;
  width: 100%;
  min-height: 34px;
  padding: 7px 10px;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border-radius: 0;
}

.level-selector :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}

.level-selector :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.level-notice {
  display: flex;
  min-width: 0;
  padding: 10px 12px;
  align-items: center;
  gap: 10px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.level-notice > .el-icon {
  flex: 0 0 auto;
  color: var(--color-info);
  font-size: 18px;
}

.level-notice > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 1px;
}

.level-notice strong {
  color: var(--color-text);
  font-size: 12px;
  font-weight: 600;
}

.level-notice span {
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.45;
}

.level-notice.is-public > .el-icon {
  color: var(--color-success);
}

.level-notice.is-internal > .el-icon {
  color: var(--color-warning);
}

.level-notice.is-sensitive {
  background: var(--danger-light);
  border-color: rgba(182, 66, 66, 0.3);
}

.level-notice.is-sensitive > .el-icon {
  color: var(--color-danger);
}

.description-field {
  grid-column: 1 / -1;
}

.description-field :deep(.el-textarea__inner) {
  min-height: 70px !important;
  line-height: 1.55;
}

.upload-actions {
  display: flex;
  margin-top: 16px;
  padding-top: 14px;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  border-top: 1px solid var(--color-border-light);
}

.upload-actions > span {
  color: var(--color-text-muted);
  font-size: 11px;
}

@media screen and (max-width: 768px) {
  .upload-dropzone :deep(.el-upload-dragger) {
    min-height: 132px;
    padding: 24px 14px 18px;
  }

  .upload-settings {
    grid-template-columns: 1fr;
  }

  .description-field {
    grid-column: 1;
  }

  .upload-actions {
    justify-content: space-between;
  }
}

@media screen and (max-width: 380px) {
  .level-selector :deep(.el-radio-button__inner) {
    padding-right: 6px;
    padding-left: 6px;
    font-size: 12px;
  }
}
</style>
