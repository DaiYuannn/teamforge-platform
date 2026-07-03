<template>
  <el-dialog
    v-model="dialogVisible"
    title="审核贡献"
    width="600px"
    @close="handleClose"
  >
    <!-- 贡献信息展示 -->
    <el-descriptions v-if="contribution" :column="1" border class="contribution-info">
      <el-descriptions-item label="项目">{{ contribution.project_name }}</el-descriptions-item>
      <el-descriptions-item label="成员">{{ contribution.user_name }}</el-descriptions-item>
      <el-descriptions-item label="贡献类型">
        {{ CONTRIBUTION_TYPE_MAP[contribution.contribution_type]?.label || contribution.contribution_type }}
      </el-descriptions-item>
      <el-descriptions-item label="贡献内容">{{ contribution.content }}</el-descriptions-item>
    </el-descriptions>

    <el-divider />

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="审核结果" prop="status">
        <el-radio-group v-model="form.status">
          <el-radio value="approved">通过</el-radio>
          <el-radio value="rejected">驳回</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.status === 'approved'" label="权重" prop="weight">
        <el-input-number v-model="form.weight" :min="0" :max="100" :precision="1" />
        <span class="form-help">贡献权重（0-100）</span>
      </el-form-item>
      <el-form-item label="审核意见" prop="review_comment">
        <el-input
          v-model="form.review_comment"
          type="textarea"
          :rows="3"
          placeholder="请输入审核意见"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确认审核</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { reviewContribution } from '@/api/contributions'
import { CONTRIBUTION_TYPE_MAP } from '@/utils/constants'
import type { Contribution } from '@/types'

/**
 * 贡献审核弹窗
 */
const props = defineProps<{
  /** 是否显示 */
  visible: boolean
  /** 贡献数据 */
  contribution?: Contribution | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

// 弹窗可见性
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

// 表单数据
const form = reactive({
  status: 'approved' as 'approved' | 'rejected',
  weight: 50,
  review_comment: '',
})

// 验证规则
const rules: FormRules = {
  status: [{ required: true, message: '请选择审核结果', trigger: 'change' }],
  review_comment: [{ required: true, message: '请输入审核意见', trigger: 'blur' }],
}

// 提交审核
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data: any = {
        status: form.status,
        review_comment: form.review_comment,
      }
      if (form.status === 'approved') {
        data.weight = form.weight
      }
      await reviewContribution(props.contribution!.id, data)
      ElMessage.success('审核成功')
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
    status: 'approved',
    weight: 50,
    review_comment: '',
  })
}

// 弹窗打开时重置
watch(
  () => props.visible,
  (val) => {
    if (val) {
      Object.assign(form, {
        status: 'approved',
        weight: 50,
        review_comment: '',
      })
    }
  }
)
</script>

<style lang="scss" scoped>
.contribution-info {
  margin-bottom: 16px;
}

.form-help {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
