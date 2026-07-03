<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑任务' : '新建任务'"
    width="600px"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="任务标题" prop="title">
        <el-input v-model="form.title" placeholder="请输入任务标题" />
      </el-form-item>
      <el-form-item label="所属项目" prop="project">
        <el-select v-model="form.project" placeholder="选择项目" style="width: 100%">
          <el-option
            v-for="p in projects"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="负责人" prop="assignee">
        <el-input-number v-model="form.assignee" :min="1" placeholder="负责人ID" style="width: 100%" />
      </el-form-item>
      <el-form-item label="优先级" prop="priority">
        <el-select v-model="form.priority" placeholder="选择优先级" style="width: 100%">
          <el-option
            v-for="(item, key) in TASK_PRIORITY_MAP"
            :key="key"
            :label="item.label"
            :value="key"
          />
        </el-select>
      </el-form-item>
      <el-form-item v-if="isEdit" label="状态" prop="status">
        <el-select v-model="form.status" placeholder="选择状态" style="width: 100%">
          <el-option
            v-for="(item, key) in TASK_STATUS_MAP"
            :key="key"
            :label="item.label"
            :value="key"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="开始日期" prop="start_date">
        <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="截止日期" prop="due_date">
        <el-date-picker v-model="form.due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="任务描述" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入任务描述" />
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
import { createTask, updateTask } from '@/api/tasks'
import { TASK_STATUS_MAP, TASK_PRIORITY_MAP } from '@/utils/constants'
import type { TaskFormData, Project } from '@/types'

/**
 * 新建/编辑任务弹窗
 */
const props = defineProps<{
  visible: boolean
  formData: TaskFormData | null
  projects: Project[]
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const isEdit = computed(() => !!props.formData)

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

const defaultForm: TaskFormData = {
  title: '',
  description: '',
  project: 0,
  assignee: 0,
  status: 'todo',
  priority: 'medium',
  start_date: '',
  deadline: '',
  due_date: '',
}

const form = reactive<TaskFormData>({ ...defaultForm })

const rules: FormRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  project: [{ required: true, message: '请选择所属项目', trigger: 'change' }],
  assignee: [{ required: true, message: '请输入负责人', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  due_date: [{ required: true, message: '请选择截止日期', trigger: 'change' }],
}

watch(
  () => props.formData,
  (val) => {
    if (val) {
      Object.assign(form, val)
    } else {
      Object.assign(form, defaultForm)
    }
  },
  { immediate: true }
)

async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value && props.formData) {
        await updateTask((props.formData as TaskFormData & { id?: number }).id || 0, form)
        ElMessage.success('任务更新成功')
      } else {
        await createTask(form)
        ElMessage.success('任务创建成功')
      }
      emit('success')
      dialogVisible.value = false
    } catch {
      // 已处理
    } finally {
      submitting.value = false
    }
  })
}

function handleClose(): void {
  formRef.value?.resetFields()
  Object.assign(form, defaultForm)
}
</script>
