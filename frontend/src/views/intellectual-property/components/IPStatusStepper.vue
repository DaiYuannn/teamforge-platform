<template>
  <div class="ip-status-progress">
    <div v-if="isAbnormalStatus" class="abnormal-state">
      <div>
        <span>当前流程状态</span>
        <strong>{{ statusLabel }}</strong>
      </div>
      <p>该申请已离开常规申报流程，请根据处理记录确认后续安排。</p>
    </div>

    <template v-else>
      <div class="progress-heading">
        <div>
          <span>申请进度</span>
          <strong>{{ statusLabel }}</strong>
        </div>
        <small>第 {{ currentStage + 1 }} / {{ stages.length }} 阶段</small>
      </div>

      <div class="stage-track" role="progressbar" :aria-valuenow="currentStage + 1" :aria-valuemax="stages.length">
        <div
          v-for="(stage, index) in stages"
          :key="stage.label"
          class="stage-item"
          :data-state="getStageState(index)"
          :aria-current="index === currentStage ? 'step' : undefined"
        >
          <div class="stage-marker">
            <span class="stage-dot">
              <el-icon v-if="index < currentStage"><Check /></el-icon>
              <template v-else>{{ index + 1 }}</template>
            </span>
          </div>
          <span class="stage-label">{{ stage.label }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check } from '@element-plus/icons-vue'
import { IP_STATUS_MAP } from '@/utils/constants'
import type { IPStatus } from '@/types/intellectualProperty'

const props = defineProps<{
  currentStatus: IPStatus
}>()

const stages = [
  { label: '准备材料', min: 0, max: 1 },
  { label: '内部审核', min: 2, max: 3 },
  { label: '科研处申报', min: 4, max: 7 },
  { label: '正式受理', min: 8, max: 8 },
  { label: '授权归档', min: 9, max: 10 },
]

const statusInfo = computed(() => IP_STATUS_MAP[props.currentStatus])
const statusStep = computed(() => statusInfo.value?.step ?? -1)
const statusLabel = computed(() => statusInfo.value?.label || props.currentStatus)
const isAbnormalStatus = computed(() => statusStep.value < 0)
const currentStage = computed(() => {
  const index = stages.findIndex((stage) => statusStep.value >= stage.min && statusStep.value <= stage.max)
  return Math.max(index, 0)
})

function getStageState(index: number): 'complete' | 'current' | 'upcoming' {
  if (index < currentStage.value) return 'complete'
  if (index === currentStage.value) return 'current'
  return 'upcoming'
}
</script>

<style lang="scss" scoped>
.ip-status-progress { min-width: 0; }

.progress-heading,
.abnormal-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.progress-heading > div,
.abnormal-state > div { display: flex; align-items: baseline; gap: 8px; }
.progress-heading span,
.abnormal-state span { color: var(--color-text-muted); font-size: 11px; }
.progress-heading strong { color: var(--color-primary); font-size: 13px; font-weight: 600; }
.progress-heading small { color: var(--color-text-muted); font-size: 11px; }

.stage-track {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-top: 8px;
}

.stage-item {
  position: relative;
  min-width: 0;
  text-align: center;
}

.stage-marker {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stage-marker::before,
.stage-marker::after {
  position: absolute;
  top: 50%;
  z-index: 0;
  width: 50%;
  height: 2px;
  background: var(--color-border);
  content: '';
}

.stage-marker::before { left: 0; }
.stage-marker::after { right: 0; }
.stage-item:first-child .stage-marker::before,
.stage-item:last-child .stage-marker::after { display: none; }
.stage-item[data-state='complete'] .stage-marker::before,
.stage-item[data-state='complete'] .stage-marker::after,
.stage-item[data-state='current'] .stage-marker::before { background: var(--color-primary); }

.stage-dot {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 600;
  background: var(--color-surface);
  border: 2px solid var(--color-border);
  border-radius: 50%;
}

.stage-item[data-state='complete'] .stage-dot,
.stage-item[data-state='current'] .stage-dot {
  color: #fff;
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.stage-item[data-state='current'] .stage-dot { box-shadow: 0 0 0 3px var(--color-primary-soft); }
.stage-label { display: block; margin-top: 5px; overflow: hidden; color: var(--color-text-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.stage-item[data-state='current'] .stage-label { color: var(--color-primary); font-weight: 600; }
.stage-item[data-state='complete'] .stage-label { color: var(--color-text-regular); }

.abnormal-state {
  min-height: 42px;
  padding: 8px 10px;
  color: #7f3030;
  background: var(--danger-light);
  border-left: 3px solid var(--color-danger);
}

.abnormal-state strong { color: var(--color-danger); font-size: 13px; }
.abnormal-state p { color: #744343; font-size: 11px; line-height: 1.45; text-align: right; }

@media screen and (max-width: 520px) {
  .progress-heading { align-items: flex-end; }
  .progress-heading > div { flex-direction: column; gap: 1px; }
  .stage-label { font-size: 9px; }
  .abnormal-state { align-items: flex-start; flex-direction: column; gap: 4px; }
  .abnormal-state p { text-align: left; }
}
</style>
