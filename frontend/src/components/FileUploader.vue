<template>
  <div class="file-uploader">
    <!-- 文件上传区域 -->
    <el-upload
      ref="uploadRef"
      :action="''"
      :auto-upload="false"
      :on-change="handleFileChange"
      :on-remove="handleFileRemove"
      :file-list="fileList"
      :limit="limit"
      :accept="accept"
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

    <!-- 级别选择 -->
    <div class="level-selector">
      <span class="label">文件级别：</span>
      <el-radio-group v-model="permission">
        <el-radio-button value="public">公开</el-radio-button>
        <el-radio-button value="internal">内部</el-radio-button>
        <el-radio-button value="sensitive">敏感</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 描述输入 -->
    <el-input
      v-model="description"
      type="textarea"
      :rows="2"
      placeholder="文件描述（可选）"
      class="description-input"
    />

    <!-- 上传按钮 -->
    <div class="upload-actions">
      <el-button
        type="primary"
        :loading="uploading"
        :disabled="fileList.length === 0"
        @click="handleUpload"
      >
        开始上传
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
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
  .level-selector {
    margin-top: 16px;
    display: flex;
    align-items: center;
    gap: 8px;

    .label {
      font-size: 14px;
      color: #606266;
      white-space: nowrap;
    }
  }

  .description-input {
    margin-top: 12px;
  }

  .upload-actions {
    margin-top: 16px;
    text-align: right;
  }
}
</style>
