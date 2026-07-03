<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑项目' : '新建项目'"
    width="600px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="项目名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入项目名称" />
      </el-form-item>
      <el-form-item label="项目编号" prop="code">
        <el-input v-model="form.code" placeholder="请输入项目编号" />
      </el-form-item>
      <el-form-item label="负责人" prop="leader">
        <el-input-number v-model="form.leader" :min="1" placeholder="负责人ID" style="width: 100%" />
      </el-form-item>
      <el-form-item label="关联比赛" prop="competition">
        <el-select v-model="form.competition" placeholder="选择比赛（可选）" clearable style="width: 100%">
          <el-option
            v-for="comp in competitions"
            :key="comp.id"
            :label="comp.name"
            :value="comp.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="开始日期" prop="start_date">
        <el-date-picker
          v-model="form.start_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择开始日期"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="预计结束" prop="expected_end_date">
        <el-date-picker
          v-model="form.expected_end_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择预计结束日期"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item v-if="isEdit" label="项目状态" prop="status">
        <el-select v-model="form.status" placeholder="选择状态" style="width: 100%">
          <el-option
            v-for="(item, key) in PROJECT_STATUS_MAP"
            :key="key"
            :label="item.label"
            :value="key"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="项目描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="请输入项目描述"
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
import { createProject, updateProject } from '@/api/projects'
import { getCompetitions } from '@/api/competitions'
import { PROJECT_STATUS_MAP } from '@/utils/constants'
import type { ProjectFormData, Competition } from '@/types'

/**
 * 新建/编辑项目弹窗
 */
const props = defineProps<{
  /** 是否显示 */
  visible: boolean
  /** 编辑时的表单数据（null 表示新建） */
  formData: ProjectFormData | null
}>()

const emit = defineEmits<{
  /** 更新 visible */
  (e: 'update:visible', val: boolean): void
  /** 操作成功 */
  (e: 'success'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const competitions = ref<Competition[]>([])

// 是否编辑模式
const isEdit = computed(() => !!props.formData)

// 弹窗可见性（双向绑定）
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

// 默认表单
const defaultForm: ProjectFormData = {
  name: '',
  code: '',
  description: '',
  competition: null,
  leader: 0,
  start_date: '',
  expected_end_date: '',
  status: 'planning',
}

// 表单数据
const form = reactive<ProjectFormData>({ ...defaultForm })

// 验证规则
const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入项目编号', trigger: 'blur' }],
  leader: [{ required: true, message: '请输入负责人', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  expected_end_date: [{ required: true, message: '请选择预计结束日期', trigger: 'change' }],
}

// 监听 props.formData 变化，初始化表单
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

// 加载比赛列表
async function loadCompetitions(): Promise<void> {
  try {
    const res = await getCompetitions({ page: 1, page_size: 999 })
    competitions.value = res.results
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
      if (isEdit.value && props.formData) {
        // 编辑模式：需要项目 ID
        await updateProject((props.formData as ProjectFormData & { id?: number }).id || 0, form)
        ElMessage.success('项目更新成功')
      } else {
        await createProject(form)
        ElMessage.success('项目创建成功')
      }
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
  Object.assign(form, defaultForm)
}

// 监听弹窗打开时加载比赛列表
watch(
  () => props.visible,
  (val) => {
    if (val) {
      loadCompetitions()
    }
  }
)
</script>
