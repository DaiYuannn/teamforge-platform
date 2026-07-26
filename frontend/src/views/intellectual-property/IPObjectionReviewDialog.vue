<template>
  <el-dialog
    v-model="dialogVisible"
    title="处理异议"
    width="600px"
    @close="handleClose"
  >
    <!-- 异议信息展示 -->
    <el-descriptions :column="1" border class="objection-info">
      <el-descriptions-item label="异议类型">
        {{ IP_OBJECTION_TYPE_MAP[objection.objection_type] || objection.objection_type }}
      </el-descriptions-item>
      <el-descriptions-item label="异议人">
        {{ objection.objector_name || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="异议内容">
        {{ objection.content }}
      </el-descriptions-item>
      <el-descriptions-item label="当前状态">
        <el-tag :type="objectionStatusColor" size="small">
          {{ IP_OBJECTION_STATUS_MAP[objection.status]?.label || objection.status }}
        </el-tag>
      </el-descriptions-item>
    </el-descriptions>

    <el-divider />

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <!-- 负责人初审意见 -->
      <el-form-item v-if="reviewMode === 'leader'" label="负责人意见" prop="leader_opinion">
        <el-input
          v-model="form.leader_opinion"
          type="textarea"
          :rows="3"
          placeholder="请输入初审意见"
        />
      </el-form-item>

      <!-- 老师最终确认 -->
      <template v-if="reviewMode === 'teacher'">
        <el-form-item label="负责人初审">
          <span class="reviewed-text">{{ objection.leader_opinion || '暂无初审意见' }}</span>
        </el-form-item>
        <el-form-item label="老师意见" prop="teacher_opinion">
          <el-input
            v-model="form.teacher_opinion"
            type="textarea"
            :rows="3"
            placeholder="请输入老师确认意见"
          />
        </el-form-item>
        <el-form-item label="最终结果" prop="final_result">
          <el-input
            v-model="form.final_result"
            type="textarea"
            :rows="2"
            placeholder="请输入最终处理结果"
          />
        </el-form-item>
        <el-form-item label="处理决定" prop="final_status">
          <el-radio-group v-model="form.final_status">
            <el-radio value="resolved">通过并解决</el-radio>
            <el-radio value="rejected">驳回异议</el-radio>
          </el-radio-group>
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确认处理</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { reviewIPObjection } from '@/api/intellectualProperty'
import { IP_OBJECTION_TYPE_MAP, IP_OBJECTION_STATUS_MAP } from '@/utils/constants'
import type { IPObjection } from '@/types/intellectualProperty'

/**
 * 处理异议弹窗
 * 支持负责人初审和老师最终确认两种模式
 */
const props = defineProps<{
  /** 是否显示 */
  visible: boolean
  /** 异议数据 */
  objection: IPObjection
  /** 审核模式：leader=负责人初审，teacher=老师确认 */
  reviewMode: 'leader' | 'teacher'
}>()

const emit = defineEmits<{
  /** 更新 visible */
  (e: 'update:visible', val: boolean): void
  /** 操作成功 */
  (e: 'success'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

// 弹窗可见性（双向绑定）
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

// 表单数据
const form = reactive({
  leader_opinion: '',
  teacher_opinion: '',
  final_result: '',
  final_status: 'resolved' as 'resolved' | 'rejected',
})

// 异议状态颜色
const objectionStatusColor = computed(() => {
  const color = IP_OBJECTION_STATUS_MAP[props.objection.status]?.color
  return (color || '') as any
})

// 验证规则（根据模式动态生成）
const rules = computed<FormRules>(() => {
  if (props.reviewMode === 'leader') {
    return {
      leader_opinion: [{ required: true, message: '请输入初审意见', trigger: 'blur' }],
    }
  }
  return {
    teacher_opinion: [{ required: true, message: '请输入老师确认意见', trigger: 'blur' }],
    final_result: [{ required: true, message: '请输入最终处理结果', trigger: 'blur' }],
    final_status: [{ required: true, message: '请选择处理决定', trigger: 'change' }],
  }
})

// 提交表单
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (props.reviewMode === 'leader') {
        await reviewIPObjection(props.objection.id, {
          action: 'leader_review',
          leader_opinion: form.leader_opinion,
        })
      } else {
        await reviewIPObjection(props.objection.id, {
          action: 'teacher_confirm',
          teacher_opinion: form.teacher_opinion,
          final_result: form.final_result,
          final_status: form.final_status,
        })
      }
      ElMessage.success('异议处理成功')
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
    leader_opinion: '',
    teacher_opinion: '',
    final_result: '',
    final_status: 'resolved',
  })
}

// 弹窗打开时初始化表单
watch(
  () => props.visible,
  (val) => {
    if (val) {
      // 预填已有的初审意见
      form.leader_opinion = props.objection.leader_opinion || ''
    }
  }
)
</script>

<style lang="scss" scoped>
.objection-info {
  margin-bottom: 16px;
}

.reviewed-text {
  color: var(--color-text-regular);
  font-size: 13px;
}
</style>
