<template>
  <el-dialog
    v-model="dialogVisible"
    class="competition-form-dialog"
    :title="isEdit ? '编辑比赛全流程' : '新建比赛'"
    :width="dialogWidth"
    :close-on-click-modal="false"
    destroy-on-close
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      class="competition-form"
      :model="form"
      :rules="rules"
      label-position="top"
      status-icon
    >
      <section class="form-section" aria-labelledby="competition-basic-title">
        <div class="section-heading">
          <div>
            <h3 id="competition-basic-title">基本信息</h3>
            <p>赛事归属、当前层级与流程状态</p>
          </div>
        </div>
        <div class="form-grid">
          <el-form-item class="span-2" label="所属项目" prop="project">
            <el-select
              v-model="form.project"
              placeholder="选择关联项目"
              filterable
              :loading="projectsLoading"
            >
              <el-option
                v-for="project in projectOptions"
                :key="project.id"
                :label="`${project.name}（${project.code}）`"
                :value="project.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item class="span-2" label="比赛名称" prop="name">
            <el-input v-model="form.name" maxlength="200" show-word-limit placeholder="请输入比赛名称" />
          </el-form-item>

          <el-form-item label="比赛类型" prop="comp_type">
            <el-input v-model="form.comp_type" maxlength="100" placeholder="如创新创业、学科竞赛" />
          </el-form-item>

          <el-form-item label="主办方" prop="organizer">
            <el-input v-model="form.organizer" maxlength="200" placeholder="请输入主办单位" />
          </el-form-item>

          <el-form-item label="比赛级别" prop="level">
            <el-select v-model="form.level" placeholder="选择级别">
              <el-option
                v-for="(item, key) in COMPETITION_LEVEL_MAP"
                :key="key"
                :label="item.label"
                :value="key"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="比赛状态" prop="status">
            <el-select v-model="form.status" placeholder="选择状态">
              <el-option
                v-for="(item, key) in COMPETITION_STATUS_MAP"
                :key="key"
                :label="item.label"
                :value="key"
              />
            </el-select>
          </el-form-item>

          <el-form-item class="span-2" label="当前阶段" prop="current_stage">
            <el-select
              v-model="form.current_stage"
              filterable
              allow-create
              default-first-option
              clearable
              placeholder="选择标准阶段，或输入当前实际阶段"
            >
              <el-option
                v-for="stage in COMPETITION_STAGE_OPTIONS"
                :key="stage"
                :label="stage"
                :value="stage"
              />
            </el-select>
          </el-form-item>
        </div>
      </section>

      <section class="form-section" aria-labelledby="competition-milestone-title">
        <div class="section-heading">
          <div>
            <h3 id="competition-milestone-title">全流程节点</h3>
            <p>层级日期会按比赛级别展开；已有日期即使超出当前级别也会保留并显示</p>
          </div>
        </div>
        <div class="form-grid form-grid--dates">
          <el-form-item label="报名日期" prop="register_date">
            <el-date-picker
              v-model="form.register_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择报名日期"
            />
          </el-form-item>

          <el-form-item label="材料提交截止" prop="material_deadline">
            <el-date-picker
              v-model="form.material_deadline"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择材料截止日期"
            />
          </el-form-item>

          <el-form-item label="网评日期" prop="review_date">
            <el-date-picker
              v-model="form.review_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择网评日期"
            />
          </el-form-item>

          <el-form-item label="答辩日期" prop="defense_date">
            <el-date-picker
              v-model="form.defense_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择答辩日期"
            />
          </el-form-item>

          <el-form-item label="校赛日期" prop="school_date">
            <el-date-picker
              v-model="form.school_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择校赛日期"
            />
          </el-form-item>

          <el-form-item v-if="showStageDate('city')" label="市赛日期" prop="city_date">
            <el-date-picker
              v-model="form.city_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择市赛日期"
            />
          </el-form-item>

          <el-form-item v-if="showStageDate('province')" label="省赛日期" prop="province_date">
            <el-date-picker
              v-model="form.province_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择省赛日期"
            />
          </el-form-item>

          <el-form-item v-if="showStageDate('national')" label="国赛日期" prop="national_date">
            <el-date-picker
              v-model="form.national_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择国赛日期"
            />
          </el-form-item>

          <el-form-item label="结果公布日期" prop="result_date">
            <el-date-picker
              v-model="form.result_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择结果公布日期"
            />
          </el-form-item>
        </div>
      </section>

      <section class="form-section" aria-labelledby="competition-result-title">
        <div class="section-heading">
          <div>
            <h3 id="competition-result-title">晋级与获奖</h3>
            <p>记录本条赛事线的晋级结论和最终结果</p>
          </div>
        </div>
        <div class="form-grid result-grid">
          <el-form-item label="晋级结果" prop="is_promoted">
            <el-switch
              v-model="form.is_promoted"
              inline-prompt
              active-text="已晋级"
              inactive-text="未晋级"
              style="--el-switch-on-color: var(--color-success)"
            />
          </el-form-item>

          <el-form-item label="获奖结果" prop="is_awarded">
            <el-switch
              v-model="form.is_awarded"
              inline-prompt
              active-text="已获奖"
              inactive-text="未获奖"
              style="--el-switch-on-color: var(--color-warning)"
            />
          </el-form-item>

          <el-form-item
            v-if="form.is_awarded || form.award_level"
            class="span-2"
            label="获奖等级"
            prop="award_level"
          >
            <el-input
              v-model="form.award_level"
              maxlength="50"
              placeholder="如国赛一等奖、省赛金奖"
            />
          </el-form-item>

          <el-form-item
            v-if="showNotPromotedReason"
            class="span-2"
            label="未晋级原因"
            prop="not_promoted_reason"
          >
            <el-input
              v-model="form.not_promoted_reason"
              type="textarea"
              :rows="3"
              maxlength="1000"
              show-word-limit
              placeholder="记录止步原因、评委反馈或材料短板"
            />
          </el-form-item>
        </div>
      </section>

      <section class="form-section" aria-labelledby="competition-review-title">
        <div class="section-heading">
          <div>
            <h3 id="competition-review-title">评审 / 答辩复盘</h3>
            <p>将评审结论沉淀为下一轮可执行的改进动作</p>
          </div>
        </div>
        <el-form-item label="评审与答辩复盘" prop="review_summary">
          <el-input
            v-model="form.review_summary"
            type="textarea"
            :rows="4"
            maxlength="3000"
            show-word-limit
            placeholder="记录评委问题、答辩表现、关键反馈和结论"
          />
        </el-form-item>
        <el-form-item label="改进建议" prop="improvement_suggestion">
          <el-input
            v-model="form.improvement_suggestion"
            type="textarea"
            :rows="4"
            maxlength="3000"
            show-word-limit
            placeholder="记录材料、产品、数据、路演和协作方面的后续动作"
          />
        </el-form-item>
      </section>
    </el-form>

    <template #footer>
      <div class="dialog-actions">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存全流程记录' : '创建比赛' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createCompetition, updateCompetition } from '@/api/competitions'
import { getProjects } from '@/api/projects'
import {
  COMPETITION_LEVEL_MAP,
  COMPETITION_STAGE_OPTIONS,
  COMPETITION_STATUS_MAP,
} from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import type {
  Competition,
  CompetitionFormData,
  CompetitionLevel,
  Project,
} from '@/types'

interface CompetitionEditorForm extends Omit<CompetitionFormData, 'project'> {
  project?: number
}

const props = defineProps<{
  visible: boolean
  formData: Competition | null
}>()

const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'success'): void
}>()

const { isMobile } = useDevice()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const projectsLoading = ref(false)
const projectOptions = ref<Project[]>([])

function makeDefaultForm(): CompetitionEditorForm {
  return {
    project: undefined,
    name: '',
    level: 'school',
    status: 'preparing',
    comp_type: '',
    organizer: '',
    current_stage: '报名准备',
    register_date: null,
    material_deadline: null,
    review_date: null,
    defense_date: null,
    school_date: null,
    city_date: null,
    province_date: null,
    national_date: null,
    result_date: null,
    is_promoted: false,
    is_awarded: false,
    award_level: '',
    not_promoted_reason: '',
    improvement_suggestion: '',
    review_summary: '',
  }
}

const form = reactive<CompetitionEditorForm>(makeDefaultForm())
const isEdit = computed(() => Boolean(props.formData?.id))
const dialogWidth = computed(() => (isMobile.value ? 'calc(100vw - 24px)' : '920px'))
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})
const showNotPromotedReason = computed(
  () => !form.is_promoted && (form.status === 'completed' || Boolean(form.not_promoted_reason)),
)

const rules: FormRules<CompetitionEditorForm> = {
  project: [{ required: true, message: '请选择所属项目', trigger: 'change' }],
  name: [{ required: true, message: '请输入比赛名称', trigger: 'blur' }],
  level: [{ required: true, message: '请选择比赛级别', trigger: 'change' }],
  status: [{ required: true, message: '请选择比赛状态', trigger: 'change' }],
}

const levelRank: Record<CompetitionLevel, number> = {
  school: 1,
  city: 2,
  province: 3,
  national: 4,
}

function showStageDate(target: Exclude<CompetitionLevel, 'school'>): boolean {
  const existingDate = {
    city: form.city_date,
    province: form.province_date,
    national: form.national_date,
  }[target]
  return levelRank[form.level] >= levelRank[target] || Boolean(existingDate)
}

function syncForm(value: Competition | null): void {
  Object.assign(form, makeDefaultForm())
  if (!value) return
  Object.assign(form, {
    project: value.project,
    name: value.name ?? '',
    level: value.level ?? 'school',
    status: value.status ?? 'preparing',
    comp_type: value.comp_type ?? '',
    organizer: value.organizer ?? '',
    current_stage: value.current_stage ?? '',
    register_date: value.register_date ?? null,
    material_deadline: value.material_deadline ?? null,
    review_date: value.review_date ?? null,
    defense_date: value.defense_date ?? null,
    school_date: value.school_date ?? null,
    city_date: value.city_date ?? null,
    province_date: value.province_date ?? null,
    national_date: value.national_date ?? null,
    result_date: value.result_date ?? null,
    is_promoted: value.is_promoted ?? false,
    is_awarded: value.is_awarded ?? false,
    award_level: value.award_level ?? '',
    not_promoted_reason: value.not_promoted_reason ?? '',
    improvement_suggestion: value.improvement_suggestion ?? '',
    review_summary: value.review_summary ?? '',
  })
}

async function loadProjects(): Promise<void> {
  if (projectOptions.value.length || projectsLoading.value) return
  projectsLoading.value = true
  try {
    const response = await getProjects({ page: 1, page_size: 100 })
    projectOptions.value = response.results
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    projectsLoading.value = false
  }
}

watch(
  () => props.formData,
  (value) => syncForm(value),
  { immediate: true },
)

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      syncForm(props.formData)
      loadProjects()
    }
  },
)

async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (!form.project) {
    ElMessage.error('请选择所属项目')
    return
  }

  submitting.value = true
  const payload = buildPayload(form.project)
  try {
    if (isEdit.value && props.formData?.id) {
      await updateCompetition(props.formData.id, payload)
      ElMessage.success('比赛全流程记录已更新')
    } else {
      await createCompetition(payload)
      ElMessage.success('比赛创建成功')
    }
    emit('success')
    dialogVisible.value = false
  } catch {
    // 请求错误已由拦截器处理。
  } finally {
    submitting.value = false
  }
}

function buildPayload(project: number = form.project as number): CompetitionFormData {
  return {
    project,
    name: form.name.trim(),
    level: form.level,
    status: form.status,
    comp_type: form.comp_type.trim(),
    organizer: form.organizer.trim(),
    current_stage: form.current_stage.trim(),
    register_date: form.register_date,
    material_deadline: form.material_deadline,
    review_date: form.review_date,
    defense_date: form.defense_date,
    school_date: form.school_date,
    city_date: form.city_date,
    province_date: form.province_date,
    national_date: form.national_date,
    result_date: form.result_date,
    is_promoted: form.is_promoted,
    is_awarded: form.is_awarded,
    award_level: form.award_level.trim(),
    not_promoted_reason: form.not_promoted_reason,
    improvement_suggestion: form.improvement_suggestion,
    review_summary: form.review_summary,
  }
}

function handleClose(): void {
  formRef.value?.clearValidate()
  syncForm(null)
}

defineExpose({ form, buildPayload, showStageDate })
</script>

<style lang="scss" scoped>
.competition-form {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.form-section {
  padding: 16px 18px 2px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.section-heading {
  padding-bottom: 11px;
  margin-bottom: 15px;
  border-bottom: 1px solid var(--color-border-light);

  h3 {
    color: var(--color-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 1.4;
  }

  p {
    margin-top: 3px;
    color: var(--color-text-muted);
    font-size: 12px;
    line-height: 1.5;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;

  &--dates {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.result-grid {
  align-items: start;
}

.span-2 {
  grid-column: 1 / -1;
}

:deep(.el-dialog__body) {
  max-height: min(72vh, 760px);
  padding-top: 10px;
  overflow-y: auto;
}

:deep(.el-form-item) {
  min-width: 0;
  margin-bottom: 16px;
}

:deep(.el-form-item__label) {
  margin-bottom: 6px;
  color: var(--color-text-regular);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
}

:deep(.el-select),
:deep(.el-date-editor) {
  width: 100%;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media screen and (max-width: 768px) {
  .competition-form {
    gap: 14px;
  }

  .form-section {
    padding: 14px 14px 0;
  }

  .form-grid,
  .form-grid--dates {
    grid-template-columns: minmax(0, 1fr);
  }

  .span-2 {
    grid-column: auto;
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
