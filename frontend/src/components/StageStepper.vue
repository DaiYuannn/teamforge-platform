<template>
  <div class="stage-stepper">
    <!-- 阶段步骤条 -->
    <el-steps :active="currentStageIndex" align-center finish-status="success">
      <el-step
        v-for="(stage, index) in stageList"
        :key="stage.value"
        :title="stage.label"
        :status="getStepStatus(index)"
      />
    </el-steps>

    <!-- 当前阶段信息 -->
    <div class="current-stage-info">
      <el-tag :color="currentStageColor" effect="dark" size="large">
        当前阶段：{{ currentStageLabel }}
      </el-tag>
      <span class="progress-text">
        进度：{{ currentStageIndex + 1 }} / {{ stageList.length }}
      </span>
    </div>

    <!-- 阶段流转历史 -->
    <div v-if="stageLogs && stageLogs.length > 0" class="stage-history">
      <h4>阶段流转历史</h4>
      <el-timeline>
        <el-timeline-item
          v-for="log in stageLogs"
          :key="log.id"
          :timestamp="formatDateTime(log.created_at)"
          placement="top"
          :color="getStageColor(log.to_stage)"
        >
          <div class="log-item">
            <span class="log-stage">
              {{ getStageLabel(log.from_stage || '初始') }}
              <el-icon><Right /></el-icon>
              {{ getStageLabel(log.to_stage) }}
            </span>
            <span class="log-operator">操作人：{{ log.operator_name }}</span>
            <p v-if="log.remark" class="log-remark">{{ log.remark }}</p>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PROJECT_STAGE_LIST } from '@/utils/constants'
import { getStageLabel, getStageColor, formatDateTime } from '@/utils/format'
import type { ProjectStage, StageLog } from '@/types'

/**
 * 16阶段步骤器组件
 * 显示项目当前阶段和流转历史
 */
const props = defineProps<{
  /** 当前阶段 */
  currentStage: ProjectStage
  /** 阶段流转日志 */
  stageLogs?: StageLog[]
}>()

// 阶段列表
const stageList = PROJECT_STAGE_LIST

// 当前阶段索引
const currentStageIndex = computed(() => {
  const index = stageList.findIndex((s) => s.value === props.currentStage)
  return index >= 0 ? index : 0
})

// 当前阶段标签
const currentStageLabel = computed(() => getStageLabel(props.currentStage))

// 当前阶段颜色
const currentStageColor = computed(() => getStageColor(props.currentStage))

// 获取步骤状态
function getStepStatus(index: number): 'wait' | 'process' | 'finish' | 'error' | 'success' {
  if (index < currentStageIndex.value) return 'success'
  if (index === currentStageIndex.value) return 'process'
  return 'wait'
}
</script>

<style lang="scss" scoped>
.stage-stepper {
  padding: 20px;

  .current-stage-info {
    display: flex;
    align-items: center;
    gap: 16px;
    margin: 20px 0;

    .progress-text {
      font-size: 14px;
      color: #606266;
    }
  }

  .stage-history {
    margin-top: 24px;

    h4 {
      font-size: 15px;
      color: #303133;
      margin-bottom: 16px;
    }

    .log-item {
      .log-stage {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 14px;
        font-weight: 600;
        color: #303133;
      }

      .log-operator {
        display: block;
        font-size: 12px;
        color: #909399;
        margin-top: 4px;
      }

      .log-remark {
        font-size: 13px;
        color: #606266;
        margin-top: 4px;
      }
    }
  }
}
</style>
