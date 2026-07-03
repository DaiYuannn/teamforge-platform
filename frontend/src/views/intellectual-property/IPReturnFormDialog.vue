<template>
  <el-dialog
    v-model="dialogVisible"
    title="创建退回记录"
    width="600px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="退回来源" prop="return_source">
        <el-select v-model="form.return_source" placeholder="请选择退回来源" style="width: 100%">
          <el-option
            v-for="(label, key) in IP_RETURN_SOURCE_MAP"
            :key="key"
            :label="label"
            :value="key"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="退回原因" prop="return_reason">
        <el-input
          v-model="form.return_reason"
          type="textarea"
          :rows="3"
          placeholder="请输入退回原因"
        />
      </el-form-item>

      <el-form-item label="责任类型" prop="responsibility_type">
        <el-select v-model="form.responsibility_type" placeholder="请选择责任类型" style="width: 100%">
          <el-option
            v-for="(label, key) in IP_RESPONSIBILITY_TYPE_MAP"
            :key="key"
            :label="label"
            :value="key"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="责任人" prop="responsible_user">
        <el-select
          v-model="form.responsible_user"
          placeholder="请选择责任人"
          clearable
          filterable
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

      <el-form-item label="修改截止时间" prop="modify_deadline">
        <el-date-picker
          v-model="form.modify_deadline"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          placeholder="选择修改截止时间"
          style="width: 100%"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createIPReturn } from '@/api/intellectualProperty'
import { getUsers } from '@/api/users'
import { IP_RETURN_SOURCE_MAP, IP_RESPONSIBILITY_TYPE_MAP } from '@/utils/constants'
import type { User } from '@/types'

/**
 * 创建退回记录弹窗
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
const userList = ref<User[]>([])

// 弹窗可见性（双向绑定）
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

// 表单数据
const form = reactive({
  return_source: '',
  return_reason: '',
  responsibility_type: '',
  responsible_user: null as number | null,
  modify_deadline: '',
})

// 验证规则
const rules: FormRules = {
  return_source: [{ required: true, message: '请选择退回来源', trigger: 'change' }],
  return_reason: [{ required: true, message: '请输入退回原因', trigger: 'blur' }],
  responsibility_type: [{ required: true, message: '请选择责任类型', trigger: 'change' }],
}

// 加载用户列表
async function loadUsers(): Promise<void> {
  try {
    const res = await getUsers({ page: 1, page_size: 999 }) as any
    userList.value = res.results || []
  } catch {
    // 忽略
  }
}

// 提交表单
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await createIPReturn(props.applicationId, { ...form })
      ElMessage.success('退回记录创建成功')
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
    return_source: '',
    return_reason: '',
    responsibility_type: '',
    responsible_user: null,
    modify_deadline: '',
  })
}

// 弹窗打开时加载用户列表
watch(
  () => props.visible,
  (val) => {
    if (val) {
      loadUsers()
    }
  }
)
</script>
