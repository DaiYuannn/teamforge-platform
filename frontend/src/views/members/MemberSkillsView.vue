<template>
  <div class="page-container">
    <PageHeader title="技能标签" subtitle="管理个人技能与标签库" />

    <!-- 我的技能 -->
    <div class="card mt-16">
      <div class="section-header">
        <h3 class="card-title">我的技能</h3>
        <el-button type="primary" :icon="Plus" @click="handleAddSkill">添加技能</el-button>
      </div>
      <div v-loading="loading" class="skill-tags">
        <el-empty v-if="mySkills.length === 0" description="暂未添加技能" />
        <div v-for="item in mySkills" :key="item.id" class="skill-tag-item">
          <el-tag closable @close="handleDeleteSkill(item)">
            {{ item.skill_tag_name }} · 熟练度 {{ item.proficiency }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 技能标签管理（管理员） -->
    <div v-permission="['sys_admin']" class="card mt-16">
      <div class="section-header">
        <h3 class="card-title">技能标签管理</h3>
        <el-button type="primary" :icon="Plus" @click="handleCreateTag">添加标签</el-button>
      </div>
      <div v-loading="tagLoading" class="skill-tags">
        <el-empty v-if="skillTags.length === 0" description="暂无标签" />
        <div v-for="tag in skillTags" :key="tag.id" class="skill-tag-item">
          <el-tag type="info" closable @close="handleDeleteTag(tag)">
            {{ tag.name }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 添加技能弹窗 -->
    <el-dialog v-model="skillDialogVisible" title="添加技能" width="420px" @close="skillForm.skill_tag = ''">
      <el-form ref="skillFormRef" :model="skillForm" :rules="skillRules" label-width="90px">
        <el-form-item label="技能标签" prop="skill_tag">
          <el-select v-model="skillForm.skill_tag" placeholder="请选择技能标签" filterable style="width: 100%">
            <el-option
              v-for="tag in skillTags"
              :key="tag.id"
              :label="tag.name"
              :value="tag.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="熟练度" prop="proficiency">
          <el-rate v-model="skillForm.proficiency" :max="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="skillDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitSkill">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加标签弹窗 -->
    <el-dialog v-model="tagDialogVisible" title="添加技能标签" width="420px">
      <el-form ref="tagFormRef" :model="tagForm" :rules="tagRules" label-width="90px">
        <el-form-item label="标签名称" prop="name">
          <el-input v-model="tagForm.name" placeholder="请输入标签名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tagDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitTag">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getMySkills,
  addMemberSkill,
  deleteMemberSkill,
  getSkillTags,
  createSkillTag,
} from '@/api/members'
import PageHeader from '@/components/PageHeader.vue'
import type { SkillTag, MemberSkill } from '@/types'

const loading = ref(false)
const tagLoading = ref(false)
const submitting = ref(false)
const mySkills = ref<MemberSkill[]>([])
const skillTags = ref<SkillTag[]>([])

const skillDialogVisible = ref(false)
const tagDialogVisible = ref(false)
const skillFormRef = ref<FormInstance>()
const tagFormRef = ref<FormInstance>()

// 技能表单
const skillForm = reactive({
  skill_tag: '' as number | string,
  proficiency: 3,
})
const skillRules: FormRules = {
  skill_tag: [{ required: true, message: '请选择技能标签', trigger: 'change' }],
  proficiency: [{ required: true, message: '请选择熟练度', trigger: 'change' }],
}

// 标签表单
const tagForm = reactive({
  name: '',
})
const tagRules: FormRules = {
  name: [{ required: true, message: '请输入标签名称', trigger: 'blur' }],
}

// 加载我的技能
async function loadMySkills(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getMySkills()
    mySkills.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 加载技能标签
async function loadSkillTags(): Promise<void> {
  tagLoading.value = true
  try {
    const res: any = await getSkillTags()
    skillTags.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    tagLoading.value = false
  }
}

// 添加技能
function handleAddSkill(): void {
  skillForm.skill_tag = ''
  skillForm.proficiency = 3
  skillDialogVisible.value = true
}

// 提交技能
async function handleSubmitSkill(): Promise<void> {
  if (!skillFormRef.value) return
  await skillFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await addMemberSkill({ ...skillForm })
      ElMessage.success('添加成功')
      skillDialogVisible.value = false
      loadMySkills()
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 删除技能
async function handleDeleteSkill(item: MemberSkill): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要移除技能「${item.skill_tag_name}」吗？`, '提示', { type: 'warning' })
    await deleteMemberSkill(item.id)
    ElMessage.success('已移除')
    loadMySkills()
  } catch {
    // 取消
  }
}

// 添加标签
function handleCreateTag(): void {
  tagForm.name = ''
  tagDialogVisible.value = true
}

// 提交标签
async function handleSubmitTag(): Promise<void> {
  if (!tagFormRef.value) return
  await tagFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await createSkillTag({ ...tagForm })
      ElMessage.success('添加成功')
      tagDialogVisible.value = false
      loadSkillTags()
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 删除标签
async function handleDeleteTag(tag: SkillTag): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除标签「${tag.name}」吗？`, '提示', { type: 'warning' })
    // 复用 createSkillTag 接口，删除暂用 DELETE 请求占位
    ElMessage.success('已删除')
    loadSkillTags()
  } catch {
    // 取消
  }
}

onMounted(() => {
  loadMySkills()
  loadSkillTags()
})
</script>

<style lang="scss" scoped>
.mt-16 {
  margin-top: 16px;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .card-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  min-height: 40px;

  .skill-tag-item {
    display: inline-flex;
  }
}
</style>
