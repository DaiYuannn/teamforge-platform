<template>
  <el-dialog
    v-model="dialogVisible"
    title="提交异议"
    width="600px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="异议类型" prop="objection_type">
        <el-select v-model="form.objection_type" placeholder="请选择异议类型" style="width: 100%">
          <el-option
            v-for="(label, key) in IP_OBJECTION_TYPE_MAP"
            :key="key"
            :label="label"
            :value="key"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="异议内容" prop="content">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="4"
          placeholder="请详细描述您的异议内容"
        />
      </el-form-item>

      <el-form-item label="证明材料">
        <el-upload
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <el-button type="primary" plain>选择文件</el-button>
          <template #tip>
            <div class="el-upload__tip">支持上传图片、文档等证明材料（可选）</div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">提交异议</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { createIPObjection } from '@/api/intellectualProperty'
import { IP_OBJECTION_TYPE_MAP } from '@/utils/constants'

/**
 * 提交异议弹窗
 */
const props = defineProps<{
  /** 是否显示 */
  visible: boolean
  /** 申请ID */
  applicationId: number
}>()

const emit = defineEmits<{
  /** 更新 visible */
  (e: 'update:visible', val: boolean): void
  /** 操作成功 */
  (e: 'success'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const proofFile = ref<File | null>(null)

// 弹窗可见性（双向绑定）
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

// 表单数据
const form = reactive({
  objection_type: '',
  content: '',
})

// 验证规则
const rules: FormRules = {
  objection_type: [{ required: true, message: '请选择异议类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入异议内容', trigger: 'blur' }],
}

// 文件选择变化
function handleFileChange(file: UploadFile): void {
  proofFile.value = file.raw || null
}

// 文件移除
function handleFileRemove(): void {
  proofFile.value = null
}

// 提交表单
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      // 如果有证明材料，使用FormData上传
      if (proofFile.value) {
        const formData = new FormData()
        formData.append('objection_type', form.objection_type)
        formData.append('content', form.content)
        formData.append('proof_upload', proofFile.value)
        await createIPObjection(props.applicationId, formData)
      } else {
        await createIPObjection(props.applicationId, { ...form })
      }
      ElMessage.success('异议提交成功')
      emit('success')
      dialogVisible.value = false
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 关闭弹窗
function handleClose(): void {
  formRef.value?.resetFields()
  Object.assign(form, {
    objection_type: '',
    content: '',
  })
  proofFile.value = null
}
</script>
