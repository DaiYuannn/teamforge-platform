<template>
  <div class="page-container">
    <PageHeader :title="isEdit ? '编辑申请' : '新建申请'" subtitle="创建知识产权成果申请档案">
      <template #actions>
        <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      </template>
    </PageHeader>

    <div class="card form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        v-loading="loading"
      >
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="成果名称" prop="title">
              <el-input v-model="form.title" placeholder="请输入成果名称" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="内部编号" prop="application_code">
              <el-input v-model="form.application_code" placeholder="请输入内部编号" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="成果类型" prop="ip_type">
              <el-select v-model="form.ip_type" placeholder="请选择成果类型" style="width: 100%">
                <el-option
                  v-for="(item, key) in IP_TYPE_MAP"
                  :key="key"
                  :label="item.label"
                  :value="key"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="关联项目" prop="related_project">
              <el-select
                v-model="form.related_project"
                placeholder="选择关联项目（可选）"
                clearable
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="proj in projectList"
                  :key="proj.id"
                  :label="proj.name"
                  :value="proj.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="主导撰写人" prop="main_writer">
              <el-select
                v-model="form.main_writer"
                placeholder="请选择主导撰写人"
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
          </el-col>
        </el-row>

        <el-form-item label="成果简介" prop="intro">
          <el-input
            v-model="form.intro"
            type="textarea"
            :rows="4"
            placeholder="请输入成果简介，描述成果的主要内容和创新点"
          />
        </el-form-item>

        <!-- 表单操作按钮 -->
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '创建申请' }}
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { createIPApplication, updateIPApplication, getIPApplication } from '@/api/intellectualProperty'
import { getProjects } from '@/api/projects'
import { getUsers } from '@/api/users'
import { IP_TYPE_MAP } from '@/utils/constants'
import type { Project, User } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)
const projectList = ref<Project[]>([])
const userList = ref<User[]>([])

// 是否编辑模式（路由有id参数则为编辑）
const isEdit = computed(() => !!route.params.id)
const editId = computed(() => Number(route.params.id) || 0)

// 表单数据
const form = reactive({
  title: '',
  application_code: '',
  ip_type: '',
  related_project: null as number | null,
  main_writer: null as number | null,
  intro: '',
})

// 验证规则
const rules: FormRules = {
  title: [{ required: true, message: '请输入成果名称', trigger: 'blur' }],
  application_code: [{ required: true, message: '请输入内部编号', trigger: 'blur' }],
  ip_type: [{ required: true, message: '请选择成果类型', trigger: 'change' }],
}

// 加载项目列表（下拉选项）
async function loadProjects(): Promise<void> {
  try {
    const res = await getProjects({ page: 1, page_size: 999 } as any) as any
    projectList.value = res.results || []
  } catch {
    // 忽略
  }
}

// 加载用户列表（下拉选项）
async function loadUsers(): Promise<void> {
  try {
    const res = await getUsers({ page: 1, page_size: 999 }) as any
    userList.value = res.results || []
  } catch {
    // 忽略
  }
}

// 编辑模式下加载已有数据
async function loadData(): Promise<void> {
  if (!isEdit.value) return
  loading.value = true
  try {
    const res = await getIPApplication(editId.value) as any
    Object.assign(form, {
      title: res.title || '',
      application_code: res.application_code || '',
      ip_type: res.ip_type || '',
      related_project: res.related_project || null,
      main_writer: res.main_writer || null,
      intro: res.intro || '',
    })
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 提交表单
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        await updateIPApplication(editId.value, { ...form })
        ElMessage.success('申请更新成功')
      } else {
        await createIPApplication({ ...form })
        ElMessage.success('申请创建成功')
      }
      router.push('/intellectual-property')
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

onMounted(() => {
  loadProjects()
  loadUsers()
  loadData()
})
</script>

<style lang="scss" scoped>
.form-card {
  padding: 24px;
  max-width: 900px;
}
</style>
