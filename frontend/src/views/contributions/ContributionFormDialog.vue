<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑贡献' : '填写贡献'"
    width="600px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="项目" prop="project">
        <el-select v-model="form.project" placeholder="请选择项目" filterable style="width: 100%">
          <el-option
            v-for="p in projectOptions"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="贡献类型" prop="contribution_type">
        <el-select v-model="form.contribution_type" placeholder="请选择贡献类型" style="width: 100%">
          <el-option
            v-for="(item, key) in CONTRIBUTION_TYPE_MAP"
            :key="key"
            :label="item.label"
            :value="key"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="贡献内容" prop="content">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="4"
          placeholder="请描述贡献内容"
        />
      </el-form-item>
      <el-form-item label="证明材料">
        <el-upload
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <el-button :icon="Upload">选择文件</el-button>
          <template #tip>
            <div class="el-form-item__help">上传证明材料（可选）</div>
          </template>
        </el-upload>
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
import { Upload } from '@element-plus/icons-vue'
import { createContribution, updateContribution } from '@/api/contributions'
import { getProjects } from '@/api/projects'
import { CONTRIBUTION_TYPE_MAP } from '@/utils/constants'
import type { Contribution, Project } from '@/types'

/**
 * 贡献记录填写/编辑弹窗
 */
const props = defineProps<{
  /** 是否显示 */
  visible: boolean
  /** 编辑时的贡献数据 */
  contribution?: Contribution | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const projectOptions = ref<Project[]>([])
const evidenceFile = ref<File | null>(null)

// 弹窗可见性
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

// 是否编辑模式
const isEdit = computed(() => !!props.contribution)

// 表单数据
const form = reactive({
  project: '' as number | string,
  contribution_type: '',
  content: '',
})

// 验证规则
const rules: FormRules = {
  project: [{ required: true, message: '请选择项目', trigger: 'change' }],
  contribution_type: [{ required: true, message: '请选择贡献类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入贡献内容', trigger: 'blur' }],
}

// 加载项目选项
async function loadProjects(): Promise<void> {
  try {
    const res = await getProjects({ page: 1, page_size: 999 })
    projectOptions.value = res.results
  } catch {
    // 忽略
  }
}

// 文件选择
function handleFileChange(file: any): void {
  evidenceFile.value = file.raw
}

// 文件移除
function handleFileRemove(): void {
  evidenceFile.value = null
}

// 提交表单
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data: any = {
        project: form.project,
        contribution_type: form.contribution_type,
        content: form.content,
      }
      if (evidenceFile.value) {
        data.evidence_file = evidenceFile.value
      }
      if (isEdit.value && props.contribution) {
        await updateContribution(props.contribution.id, data)
        ElMessage.success('修改成功')
      } else {
        await createContribution(data)
        ElMessage.success('提交成功')
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
  Object.assign(form, {
    project: '',
    contribution_type: '',
    content: '',
  })
  evidenceFile.value = null
}

// 弹窗打开时初始化
watch(
  () => props.visible,
  (val) => {
    if (val) {
      loadProjects()
      if (props.contribution) {
        Object.assign(form, {
          project: props.contribution.project,
          contribution_type: props.contribution.contribution_type,
          content: props.contribution.content,
        })
      }
    }
  }
)
</script>
