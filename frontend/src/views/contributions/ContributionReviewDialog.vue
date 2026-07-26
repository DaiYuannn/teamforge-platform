<template>
  <el-dialog
    v-model="dialogVisible"
    title="审核贡献"
    :width="dialogWidth"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <section v-if="contribution" class="contribution-summary" aria-label="待审核贡献信息">
      <header>
        <div>
          <span>所属项目</span>
          <strong>{{ contribution.project_name || '-' }}</strong>
        </div>
        <el-tag :type="contributionTypeTag as any" size="small">
          {{ contributionTypeLabel }}
        </el-tag>
      </header>
      <dl>
        <div>
          <dt>提交成员</dt>
          <dd>{{ contribution.user_name || '-' }}</dd>
        </div>
        <div>
          <dt>提交时间</dt>
          <dd>{{ displayDate(contribution.created_at) }}</dd>
        </div>
      </dl>
      <div class="contribution-content">
        <span>贡献内容</span>
        <p>{{ contribution.content }}</p>
      </div>
    </section>

    <el-form ref="formRef" class="review-form" :model="form" :rules="rules" label-position="top">
      <el-form-item label="审核结果" prop="status">
        <el-radio-group v-model="form.status" class="review-segment">
          <el-radio-button value="approved">通过</el-radio-button>
          <el-radio-button value="rejected">驳回</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.status === 'approved'" label="贡献权重" prop="weight">
        <el-input-number v-model="form.weight" :min="0" :max="100" :precision="1" />
      </el-form-item>
      <el-form-item label="审核意见" prop="review_opinion">
        <el-input
          v-model="form.review_opinion"
          type="textarea"
          :rows="4"
          maxlength="1000"
          show-word-limit
          :placeholder="form.status === 'approved' ? '填写通过意见' : '说明驳回原因'"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-actions">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          :type="form.status === 'rejected' ? 'danger' : 'primary'"
          :loading="submitting"
          @click="handleSubmit"
        >
          确认{{ form.status === 'approved' ? '通过' : '驳回' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { reviewContribution } from '@/api/contributions'
import { CONTRIBUTION_TYPE_MAP } from '@/utils/constants'
import { formatDate } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import type { Contribution } from '@/types'

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
const submitting = ref(false)
const dialogWidth = computed(() => (isMobile.value ? 'calc(100vw - 24px)' : '620px'))
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})
const contributionTypeLabel = computed(() => {
  const type = props.contribution?.contribution_type || ''
  return CONTRIBUTION_TYPE_MAP[type]?.label || type || '-'
})
const contributionTypeTag = computed(() => {
  const type = props.contribution?.contribution_type || ''
  return CONTRIBUTION_TYPE_MAP[type]?.tagType || 'info'
})
const defaultForm = {
  status: 'approved' as 'approved' | 'rejected',
  weight: 50,
  review_opinion: '',
}
const form = reactive({ ...defaultForm })
const rules: FormRules = {
  status: [{ required: true, message: '请选择审核结果', trigger: 'change' }],
  review_opinion: [{ required: true, message: '请输入审核意见', trigger: 'blur' }],
}

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '-'
}

function resetForm(): void {
  formRef.value?.clearValidate()
  Object.assign(form, defaultForm)
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value || !props.contribution) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const payload: { status: string; review_opinion: string; weight?: number } = {
    status: form.status,
    review_opinion: form.review_opinion.trim(),
  }
  if (form.status === 'approved') payload.weight = form.weight

  submitting.value = true
  try {
    await reviewContribution(props.contribution.id, payload)
    ElMessage.success(form.status === 'approved' ? '贡献已通过' : '贡献已驳回')
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
    if (visible) resetForm()
  },
)
</script>

<style lang="scss" scoped>
.contribution-summary {
  overflow: hidden;
  margin-bottom: 20px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  > header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--color-border-light);

    > div {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    span {
      color: var(--color-text-muted);
      font-size: 11px;
    }

    strong {
      margin-top: 2px;
      overflow-wrap: anywhere;
      color: var(--color-text);
      font-size: 14px;
      font-weight: 600;
    }
  }

  dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 12px 16px;
    border-bottom: 1px solid var(--color-border-light);

    > div + div {
      padding-left: 16px;
      border-left: 1px solid var(--color-border-light);
    }
  }

  dt,
  .contribution-content > span {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 2px;
    color: var(--color-text-regular);
    font-size: 13px;
  }
}

.contribution-content {
  padding: 12px 16px 14px;

  p {
    margin-top: 4px;
    overflow-wrap: anywhere;
    color: var(--color-text-regular);
    font-size: 13px;
    line-height: 1.55;
  }
}

.review-form {
  :deep(.el-input-number) {
    width: 180px;
  }
}

.review-segment {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  width: 260px;

  :deep(.el-radio-button__inner) {
    width: 100%;
  }
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media screen and (max-width: 768px) {
  .review-segment,
  .review-form :deep(.el-input-number) {
    width: 100%;
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
