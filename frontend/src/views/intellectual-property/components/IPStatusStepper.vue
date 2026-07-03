<template>
  <div class="ip-status-stepper">
    <!-- 异常状态提示（暂停/终止/转为后续） -->
    <div v-if="isAbnormalStatus" class="abnormal-status-bar">
      <el-tag :type="statusColor" size="large" effect="dark">
        当前状态：{{ statusLabel }}
      </el-tag>
      <span class="abnormal-hint">该申请处于非正常流程状态</span>
    </div>

    <!-- 正常流程状态步骤条 -->
    <el-steps v-else :active="currentStep" align-center finish-status="success">
      <el-step
        v-for="step in normalSteps"
        :key="step.value"
        :title="step.label"
        :status="getStepStatus(step.step)"
      />
    </el-steps>

    <!-- 当前状态信息 -->
    <div class="current-status-info">
      <el-tag :type="statusColor" size="large">
        {{ statusLabel }}
      </el-tag>
      <span v-if="!isAbnormalStatus" class="progress-text">
        进度：{{ currentStep }} / {{ normalSteps.length }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { IP_STATUS_MAP } from '@/utils/constants'
import type { IPStatus } from '@/types/intellectualProperty'

/**
 * 知识产权状态步骤条组件
 * 展示10个主要状态步骤，异常状态用特殊Tag展示
 */
const props = defineProps<{
  /** 当前状态 */
  currentStatus: IPStatus
}>()

// 正常流程步骤（按step排序，仅step >= 0的状态）
const normalSteps = computed(() => {
  return Object.entries(IP_STATUS_MAP)
    .filter(([, val]) => val.step >= 0)
    .sort((a, b) => a[1].step - b[1].step)
    .map(([key, val]) => ({
      value: key,
      label: val.label,
      step: val.step,
    }))
})

// 当前状态的step值
const currentStep = computed(() => {
  const statusInfo = IP_STATUS_MAP[props.currentStatus]
  return statusInfo ? statusInfo.step : 0
})

// 是否为异常状态
const isAbnormalStatus = computed(() => {
  return currentStep.value < 0
})

// 状态标签
const statusLabel = computed(() => {
  return IP_STATUS_MAP[props.currentStatus]?.label || props.currentStatus
})

// 状态颜色
const statusColor = computed(() => {
  const color = IP_STATUS_MAP[props.currentStatus]?.color
  // Element Plus 的 el-tag type 只接受特定值，空字符串等同于 default
  return (color || '') as any
})

// 获取步骤状态
function getStepStatus(step: number): 'wait' | 'process' | 'finish' | 'success' | 'error' {
  if (step < currentStep.value) return 'success'
  if (step === currentStep.value) return 'process'
  return 'wait'
}
</script>

<style lang="scss" scoped>
.ip-status-stepper {
  padding: 20px 0;

  .abnormal-status-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;

    .abnormal-hint {
      font-size: 13px;
      color: #909399;
    }
  }

  .current-status-info {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 20px;
    justify-content: center;

    .progress-text {
      font-size: 14px;
      color: #606266;
    }
  }
}

@media screen and (max-width: 768px) {
  .ip-status-stepper {
    :deep(.el-steps) {
      .el-step__title {
        font-size: 12px;
      }
    }
  }
}
</style>
