<template>
  <div class="page-container skills-page">
    <PageHeader title="技能标签" subtitle="维护个人技能熟练度与团队技能词库" />

    <section class="skills-surface" aria-labelledby="my-skills-title">
      <header class="section-heading">
        <div>
          <h2 id="my-skills-title">我的技能</h2>
          <p>{{ mySkills.length }} 项技能</p>
        </div>
        <el-button type="primary" :icon="Plus" @click="handleAddSkill">添加技能</el-button>
      </header>

      <div v-loading="loading" class="skill-list">
        <EmptyState
          v-if="!loading && mySkills.length === 0"
          text="暂未添加技能"
          description="添加技能并记录当前熟练度"
          compact
        />
        <article v-for="item in mySkills" :key="item.id" class="skill-row">
          <div class="skill-row__identity">
            <span class="skill-mark" aria-hidden="true"><el-icon><Collection /></el-icon></span>
            <div>
              <strong>{{ skillName(item) }}</strong>
              <span>熟练度 {{ item.proficiency }} / 5</span>
            </div>
          </div>
          <el-rate :model-value="item.proficiency" disabled />
          <el-tooltip content="移除技能" placement="top">
            <el-button
              type="danger"
              link
              :icon="Delete"
              aria-label="移除技能"
              @click="handleDeleteSkill(item)"
            />
          </el-tooltip>
        </article>
      </div>
    </section>

    <section v-permission="['sys_admin']" class="skills-surface" aria-labelledby="skill-library-title">
      <header class="section-heading">
        <div>
          <h2 id="skill-library-title">技能词库</h2>
          <p>{{ skillTags.length }} 个可用标签</p>
        </div>
        <el-button :icon="Plus" @click="handleCreateTag">添加标签</el-button>
      </header>

      <div v-loading="tagLoading" class="tag-library">
        <EmptyState v-if="!tagLoading && skillTags.length === 0" text="暂无技能标签" compact />
        <el-tag
          v-for="tag in skillTags"
          :key="tag.id"
          type="info"
          closable
          @close="handleDeleteTag(tag)"
        >
          {{ tag.name }}
        </el-tag>
      </div>
    </section>

    <el-dialog
      v-model="skillDialogVisible"
      title="添加技能"
      :width="dialogWidth"
      :close-on-click-modal="false"
      @close="resetSkillForm"
    >
      <el-form ref="skillFormRef" :model="skillForm" :rules="skillRules" label-position="top">
        <el-form-item label="技能标签" prop="skill">
          <el-select v-model="skillForm.skill" placeholder="选择技能标签" filterable>
            <el-option v-for="tag in skillTags" :key="tag.id" :label="tag.name" :value="tag.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="熟练度" prop="proficiency">
          <div class="proficiency-control">
            <el-rate v-model="skillForm.proficiency" :max="5" />
            <span>{{ skillForm.proficiency }} / 5</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="skillDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmitSkill">
            添加技能
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="tagDialogVisible"
      title="添加技能标签"
      :width="dialogWidth"
      :close-on-click-modal="false"
      @close="resetTagForm"
    >
      <el-form ref="tagFormRef" :model="tagForm" :rules="tagRules" label-position="top">
        <el-form-item label="标签名称" prop="name">
          <el-input v-model="tagForm.name" maxlength="100" show-word-limit placeholder="请输入标签名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="tagDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmitTag">
            添加标签
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Collection, Delete, Plus } from '@element-plus/icons-vue'
import {
  addMemberSkill,
  createSkillTag,
  deleteMemberSkill,
  getMySkills,
  getSkillTags,
} from '@/api/members'
import { del } from '@/api/request'
import { useDevice } from '@/composables/useDevice'
import type { MemberSkill, SkillTag } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'

type MemberSkillRecord = MemberSkill & { skill?: number; skill_name?: string }

const { isMobile } = useDevice()
const loading = ref(false)
const tagLoading = ref(false)
const submitting = ref(false)
const mySkills = ref<MemberSkillRecord[]>([])
const skillTags = ref<SkillTag[]>([])
const skillDialogVisible = ref(false)
const tagDialogVisible = ref(false)
const skillFormRef = ref<FormInstance>()
const tagFormRef = ref<FormInstance>()

const dialogWidth = computed(() => (isMobile.value ? 'calc(100vw - 24px)' : '440px'))
const skillForm = reactive({ skill: '' as number | string, proficiency: 3 })
const tagForm = reactive({ name: '' })
const skillRules: FormRules = {
  skill: [{ required: true, message: '请选择技能标签', trigger: 'change' }],
  proficiency: [{ required: true, message: '请选择熟练度', trigger: 'change' }],
}
const tagRules: FormRules = {
  name: [{ required: true, message: '请输入标签名称', trigger: 'blur' }],
}

function skillName(item: MemberSkillRecord): string {
  return item.skill_name || item.skill_tag_name || '未命名技能'
}

async function loadMySkills(): Promise<void> {
  loading.value = true
  try {
    const response: any = await getMySkills()
    mySkills.value = Array.isArray(response) ? response : response.results || []
  } catch {
    mySkills.value = []
  } finally {
    loading.value = false
  }
}

async function loadSkillTags(): Promise<void> {
  tagLoading.value = true
  try {
    const response: any = await getSkillTags()
    skillTags.value = Array.isArray(response) ? response : response.results || []
  } catch {
    skillTags.value = []
  } finally {
    tagLoading.value = false
  }
}

function resetSkillForm(): void {
  skillFormRef.value?.clearValidate()
  skillForm.skill = ''
  skillForm.proficiency = 3
}

function resetTagForm(): void {
  tagFormRef.value?.clearValidate()
  tagForm.name = ''
}

function handleAddSkill(): void {
  resetSkillForm()
  skillDialogVisible.value = true
}

function handleCreateTag(): void {
  resetTagForm()
  tagDialogVisible.value = true
}

async function handleSubmitSkill(): Promise<void> {
  if (!formRefValid(skillFormRef.value)) return
  const valid = await skillFormRef.value!.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await addMemberSkill({ skill: skillForm.skill, proficiency: skillForm.proficiency })
    ElMessage.success('技能添加成功')
    skillDialogVisible.value = false
    loadMySkills()
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    submitting.value = false
  }
}

async function handleDeleteSkill(item: MemberSkillRecord): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定移除技能「${skillName(item)}」吗？`, '移除技能', {
      type: 'warning',
      confirmButtonText: '移除',
      cancelButtonText: '取消',
    })
    await deleteMemberSkill(item.id)
    ElMessage.success('技能已移除')
    loadMySkills()
  } catch {
    // 用户取消或请求错误已由拦截器处理。
  }
}

async function handleSubmitTag(): Promise<void> {
  if (!formRefValid(tagFormRef.value)) return
  const valid = await tagFormRef.value!.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createSkillTag({ name: tagForm.name.trim() })
    ElMessage.success('标签添加成功')
    tagDialogVisible.value = false
    loadSkillTags()
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    submitting.value = false
  }
}

async function handleDeleteTag(tag: SkillTag): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除标签「${tag.name}」吗？`, '删除技能标签', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await del(`/members/skill-tags/${tag.id}/`)
    ElMessage.success('标签已删除')
    loadSkillTags()
  } catch {
    // 用户取消或请求错误已由拦截器处理。
  }
}

function formRefValid(instance?: FormInstance): boolean {
  return Boolean(instance)
}

onMounted(() => {
  loadMySkills()
  loadSkillTags()
})
</script>

<style lang="scss" scoped>
.skills-page {
  display: flex;
  flex-direction: column;
  gap: 12px;

  :deep(.page-header) {
    margin-bottom: 6px;
  }
}

.skills-surface {
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border-light);

  h2 {
    color: var(--color-text);
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0;
  }

  p {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
}

.skill-list {
  min-height: 120px;
  padding: 0 18px;
}

.skill-row {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 150px 32px;
  align-items: center;
  gap: 18px;
  min-height: 66px;
  border-bottom: 1px solid var(--color-border-light);

  &:last-child {
    border-bottom: 0;
  }
}

.skill-row__identity {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;

  > div {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  strong {
    overflow: hidden;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span:last-child {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.skill-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);
}

.tag-library {
  display: flex;
  align-content: flex-start;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 104px;
  padding: 18px;
}

.proficiency-control {
  display: flex;
  align-items: center;
  gap: 12px;

  span {
    color: var(--color-text-muted);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
}

:deep(.el-select) {
  width: 100%;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media screen and (max-width: 768px) {
  .section-heading {
    padding: 13px 14px;
  }

  .skill-list {
    padding: 0 14px;
  }

  .skill-row {
    grid-template-columns: minmax(0, 1fr) 32px;
    gap: 10px;
    padding: 12px 0;

    :deep(.el-rate) {
      grid-column: 1 / -1;
      grid-row: 2;
      padding-left: 42px;
    }
  }

  .tag-library {
    padding: 14px;
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
