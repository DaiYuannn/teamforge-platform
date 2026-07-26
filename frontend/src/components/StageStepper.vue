<template>
  <div class="stage-stepper">
    <section class="stage-overview" :class="{ 'stage-overview--abnormal': isAbnormalStage }">
      <div class="stage-heading">
        <div>
          <span>当前阶段</span>
          <strong>{{ currentStageLabel }}</strong>
        </div>
        <small v-if="!isAbnormalStage">阶段 {{ currentStageNumber }} / 14</small>
        <small v-else>非正常执行状态</small>
      </div>

      <div v-if="!isAbnormalStage" class="phase-track" role="progressbar" :aria-valuenow="currentPhaseIndex + 1" :aria-valuemax="phases.length">
        <div
          v-for="(phase, index) in phases"
          :key="phase.label"
          class="phase-item"
          :data-state="phaseState(index)"
          :aria-current="index === currentPhaseIndex ? 'step' : undefined"
        >
          <div class="phase-marker">
            <span><el-icon v-if="index < currentPhaseIndex"><Check /></el-icon><template v-else>{{ index + 1 }}</template></span>
          </div>
          <strong>{{ phase.label }}</strong>
          <small>{{ phase.range }}</small>
        </div>
      </div>

      <p v-else class="abnormal-copy">项目已离开常规推进流程，请结合最近的阶段记录确认暂停或终止原因。</p>
    </section>

    <section class="stage-control" aria-label="阶段推进操作">
      <header>
        <div>
          <h3>阶段操作</h3>
          <p>每次推进都会记录目标阶段、操作人和说明。</p>
        </div>
        <el-tag v-if="!canManage" type="info" size="small" effect="plain">只读</el-tag>
      </header>

      <template v-if="canManage">
        <el-alert
          v-if="stageTargets.length === 0"
          title="当前状态没有可执行的阶段推进"
          type="info"
          :closable="false"
          show-icon
        />
        <div v-else class="stage-form">
          <el-select
            v-model="selectedStage"
            class="stage-target"
            placeholder="选择目标阶段"
            :disabled="submitting"
          >
            <el-option
              v-for="option in stageTargets"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            >
              <div class="stage-option">
                <span>{{ option.label }}</span>
                <small v-if="option.kind === 'next'">正常推进</small>
                <small v-else-if="option.kind === 'pause'">特殊状态</small>
                <small v-else>不可撤销</small>
              </div>
            </el-option>
          </el-select>
          <el-input
            v-model="stageRemark"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
            resize="vertical"
            placeholder="填写本次推进依据、已完成事项或风险说明"
            :disabled="submitting"
          />
          <el-alert
            v-if="validationMessage"
            class="stage-form-error"
            :title="validationMessage"
            type="warning"
            :closable="false"
            show-icon
          />
          <div class="stage-form-footer">
            <small>为避免误操作，只开放下一正常阶段以及暂停、终止。</small>
            <el-button type="primary" :loading="submitting" @click="submitAdvance">
              确认阶段操作
            </el-button>
          </div>
        </div>
      </template>
      <p v-else class="read-only-copy">
        普通项目成员可查看完整阶段记录；阶段变更仅由项目负责人、老师或管理员执行。
      </p>
    </section>

    <section v-if="stageLogs?.length" class="stage-history">
      <header>
        <h3>阶段流转历史</h3>
        <span>共 {{ stageLogs.length }} 条记录</span>
      </header>
      <el-timeline>
        <el-timeline-item
          v-for="log in sortedLogs"
          :key="log.id"
          :timestamp="formatDateTime(log.created_at)"
          :color="getStageColor(log.to_stage)"
        >
          <div class="log-item">
            <div class="log-route">
              <span>{{ log.from_stage ? getStageLabel(log.from_stage) : '项目创建' }}</span>
              <el-icon><Right /></el-icon>
              <strong>{{ getStageLabel(log.to_stage) }}</strong>
            </div>
            <span class="log-operator">{{ log.operator_name || '未知操作人' }}</span>
            <p v-if="log.note || log.remark">{{ log.note || log.remark }}</p>
          </div>
        </el-timeline-item>
      </el-timeline>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, Right } from '@element-plus/icons-vue'
import { formatDateTime, getStageColor, getStageLabel } from '@/utils/format'
import { getLegalStageTargets, normalizeProjectStage } from '@/utils/projectWorkflow'
import type { AdvanceStageParams, ProjectStage, ProjectStatus, StageLog } from '@/types'

const props = defineProps<{
  currentStage: ProjectStage
  projectStatus?: ProjectStatus
  stageLogs?: StageLog[]
  canManage?: boolean
  submitting?: boolean
}>()

const emit = defineEmits<{
  advance: [payload: AdvanceStageParams]
}>()

const phases = [
  { label: '构思立项', range: '1-2', min: 1, max: 2 },
  { label: '材料研发', range: '3-4', min: 3, max: 4 },
  { label: '报名评审', range: '5-8', min: 5, max: 8 },
  { label: '赛事晋级', range: '9-12', min: 9, max: 12 },
  { label: '获奖结项', range: '13-14', min: 13, max: 14 },
]

const currentStageNumber = computed(() => normalizeProjectStage(props.currentStage))
const currentStageLabel = computed(() => getStageLabel(props.currentStage))
const isAbnormalStage = computed(() => currentStageNumber.value >= 15)
const currentPhaseIndex = computed(() => {
  const index = phases.findIndex((phase) => currentStageNumber.value >= phase.min && currentStageNumber.value <= phase.max)
  return Math.max(index, 0)
})
const sortedLogs = computed(() =>
  [...(props.stageLogs || [])].sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()),
)
const stageTargets = computed(() =>
  getLegalStageTargets(props.currentStage, props.projectStatus || 'active'),
)
const selectedStage = ref<number>()
const stageRemark = ref('')
const validationMessage = ref('')

watch(
  () => [props.currentStage, props.projectStatus],
  () => {
    selectedStage.value = undefined
    stageRemark.value = ''
    validationMessage.value = ''
  },
)

function phaseState(index: number): 'complete' | 'current' | 'upcoming' {
  if (index < currentPhaseIndex.value) return 'complete'
  if (index === currentPhaseIndex.value) return 'current'
  return 'upcoming'
}

function submitAdvance(): void {
  validationMessage.value = ''
  if (!selectedStage.value) {
    validationMessage.value = '请选择目标阶段'
    return
  }
  const remark = stageRemark.value.trim()
  if (!remark) {
    validationMessage.value = '请填写本次阶段操作说明'
    return
  }
  if (!stageTargets.value.some((option) => option.value === selectedStage.value)) {
    validationMessage.value = '该目标阶段不在当前可执行范围内，请重新选择'
    return
  }
  emit('advance', {
    target_stage: selectedStage.value,
    remark,
  })
}
</script>

<style lang="scss" scoped>
.stage-stepper { min-width: 0; }

.stage-overview {
  padding: 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.stage-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.stage-heading > div { display: flex; flex-direction: column; }
.stage-heading span { color: var(--color-text-muted); font-size: 11px; }
.stage-heading strong { margin-top: 2px; color: var(--color-primary); font-size: 18px; font-weight: 650; }
.stage-heading small { color: var(--color-text-muted); font-size: 11px; }

.phase-track {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-top: 20px;
}

.phase-item { min-width: 0; text-align: center; }
.phase-marker { position: relative; display: flex; align-items: center; justify-content: center; }
.phase-marker::before,
.phase-marker::after { position: absolute; top: 50%; z-index: 0; width: 50%; height: 2px; background: var(--color-border); content: ''; }
.phase-marker::before { left: 0; }
.phase-marker::after { right: 0; }
.phase-item:first-child .phase-marker::before,
.phase-item:last-child .phase-marker::after { display: none; }
.phase-item[data-state='complete'] .phase-marker::before,
.phase-item[data-state='complete'] .phase-marker::after,
.phase-item[data-state='current'] .phase-marker::before { background: var(--color-primary); }

.phase-marker > span {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 600;
  background: var(--color-surface);
  border: 2px solid var(--color-border);
  border-radius: 50%;
}

.phase-item[data-state='complete'] .phase-marker > span,
.phase-item[data-state='current'] .phase-marker > span { color: #fff; background: var(--color-primary); border-color: var(--color-primary); }
.phase-item[data-state='current'] .phase-marker > span { box-shadow: 0 0 0 3px var(--color-primary-soft); }
.phase-item > strong { display: block; margin-top: 7px; overflow: hidden; color: var(--color-text-regular); font-size: 11px; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.phase-item > small { display: block; margin-top: 1px; color: var(--color-text-muted); font-size: 9px; }
.phase-item[data-state='current'] > strong { color: var(--color-primary); font-weight: 600; }

.stage-overview--abnormal { background: var(--danger-light); border-color: #efcfcd; }
.stage-overview--abnormal .stage-heading strong { color: var(--color-danger); }
.abnormal-copy { margin-top: 12px; color: #744343; font-size: 12px; line-height: 1.55; }

.stage-history { margin-top: 18px; padding: 18px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.stage-history > header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 18px; }
.stage-history h3 { color: var(--color-text); font-size: 15px; font-weight: 600; }
.stage-history header span { color: var(--color-text-muted); font-size: 11px; }
.stage-history :deep(.el-timeline-item__timestamp) { color: var(--color-text-muted); font-size: 11px; }
.log-route { display: flex; align-items: center; gap: 6px; color: var(--color-text-regular); font-size: 13px; }
.log-route strong { color: var(--color-text); font-weight: 600; }
.log-operator { display: block; margin-top: 4px; color: var(--color-text-muted); font-size: 11px; }
.log-item p { margin-top: 6px; color: var(--color-text-regular); font-size: 12px; line-height: 1.5; }

.stage-control {
  margin-top: 18px;
  padding: 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.stage-control > header {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.stage-control h3 {
  color: var(--color-text);
  font-size: 15px;
  font-weight: 600;
}

.stage-control header p,
.read-only-copy {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.stage-form {
  display: grid;
  grid-template-columns: minmax(180px, 0.34fr) minmax(260px, 1fr);
  gap: 12px;
  align-items: start;
}

.stage-target {
  width: 100%;
}

.stage-option {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.stage-option small {
  color: var(--color-text-muted);
  font-size: 10px;
}

.stage-form-error,
.stage-form-footer {
  grid-column: 1 / -1;
}

.stage-form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.stage-form-footer small {
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.5;
}

@media screen and (max-width: 520px) {
  .stage-overview,
  .stage-history { padding: 14px; }
  .phase-item > strong { font-size: 9px; }
  .phase-item > small { display: none; }
  .stage-heading strong { font-size: 16px; }
  .stage-form { grid-template-columns: 1fr; }
  .stage-form-footer { align-items: stretch; flex-direction: column; }
  .stage-form-footer .el-button { width: 100%; }
}
</style>
