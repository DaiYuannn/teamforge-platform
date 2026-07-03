<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑比赛' : '新建比赛'"
    width="600px"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="比赛名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入比赛名称" />
      </el-form-item>
      <el-form-item label="比赛级别" prop="level">
        <el-select v-model="form.level" placeholder="选择级别" style="width: 100%">
          <el-option
            v-for="(item, key) in COMPETITION_LEVEL_MAP"
            :key="key"
            :label="item.label"
            :value="key"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="比赛状态" prop="status">
        <el-select v-model="form.status" placeholder="选择状态" style="width: 100%">
          <el-option
            v-for="(item, key) in COMPETITION_STATUS_MAP"
            :key="key"
            :label="item.label"
            :value="key"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="主办方" prop="organizer">
        <el-input v-model="form.organizer" placeholder="请输入主办方" />
      </el-form-item>
      <el-form-item label="开始日期" prop="start_date">
        <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="结束日期" prop="end_date">
        <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="报名截止" prop="registration_deadline">
        <el-date-picker v-model="form.registration_deadline" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="比赛官网" prop="website">
        <el-input v-model="form.website" placeholder="请输入比赛官网URL" />
      </el-form-item>
      <el-form-item label="比赛描述" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入比赛描述" />
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
import { createCompetition, updateCompetition } from '@/api/competitions'
import { COMPETITION_LEVEL_MAP, COMPETITION_STATUS_MAP } from '@/utils/constants'
import type { CompetitionFormData } from '@/types'

/**
 * 新建/编辑比赛弹窗
 */
const props = defineProps<{
  visible: boolean
  formData: CompetitionFormData | null
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

const defaultForm: CompetitionFormData = {
  name: '',
  level: 'school',
  status: 'upcoming',
  description: '',
  organizer: '',
  start_date: '',
  end_date: '',
  registration_deadline: '',
  website: '',
}

const form = reactive<CompetitionFormData>({ ...defaultForm })

const rules: FormRules = {
  name: [{ required: true, message: '请输入比赛名称', trigger: 'blur' }],
  level: [{ required: true, message: '请选择比赛级别', trigger: 'change' }],
  status: [{ required: true, message: '请选择比赛状态', trigger: 'change' }],
  organizer: [{ required: true, message: '请输入主办方', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  registration_deadline: [{ required: true, message: '请选择报名截止日期', trigger: 'change' }],
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
        await updateCompetition((props.formData as CompetitionFormData & { id?: number }).id || 0, form)
        ElMessage.success('比赛更新成功')
      } else {
        await createCompetition(form)
        ElMessage.success('比赛创建成功')
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
