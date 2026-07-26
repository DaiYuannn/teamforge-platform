<template>
  <el-card class="return-record-card" shadow="hover">
    <!-- 卡片头部：退回时间 + 结果标签 -->
    <div class="card-header">
      <div class="header-left">
        <span class="return-time">{{ formatDateTime(record.return_time) }}</span>
        <el-tag size="small" :type="returnSourceColor">
          {{ IP_RETURN_SOURCE_MAP[record.return_source] || record.return_source }}
        </el-tag>
      </div>
      <el-tag size="small" :type="resultColor" effect="dark">
        {{ IP_RETURN_RESULT_MAP[record.result]?.label || record.result }}
      </el-tag>
    </div>

    <!-- 退回原因 -->
    <div class="card-field">
      <span class="field-label">退回原因：</span>
      <span class="field-value">{{ record.return_reason }}</span>
    </div>

    <!-- 责任类型 + 责任人 -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12">
        <div class="card-field">
          <span class="field-label">责任类型：</span>
          <el-tag size="small" type="warning">
            {{ IP_RESPONSIBILITY_TYPE_MAP[record.responsibility_type] || record.responsibility_type }}
          </el-tag>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12">
        <div class="card-field">
          <span class="field-label">责任人：</span>
          <span class="field-value">{{ record.responsible_user_name || '-' }}</span>
        </div>
      </el-col>
    </el-row>

    <!-- 修改截止时间 + 实际修改人 -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12">
        <div class="card-field">
          <span class="field-label">修改截止：</span>
          <span class="field-value">{{ record.modify_deadline ? formatDate(record.modify_deadline) : '-' }}</span>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12">
        <div class="card-field">
          <span class="field-label">实际修改人：</span>
          <span class="field-value">{{ record.actual_modifier_name || '-' }}</span>
        </div>
      </el-col>
    </el-row>

    <!-- 修改说明 -->
    <div v-if="record.modify_description" class="card-field">
      <span class="field-label">修改说明：</span>
      <span class="field-value">{{ record.modify_description }}</span>
    </div>

    <!-- 分配人 -->
    <div v-if="record.assigned_by_name" class="card-field">
      <span class="field-label">分配人：</span>
      <span class="field-value">{{ record.assigned_by_name }}</span>
    </div>

    <!-- 操作按钮 -->
    <div v-if="showResolveButton" class="card-actions">
      <el-button type="primary" size="small" @click="$emit('resolve', record)">
        完成修改
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDate, formatDateTime } from '@/utils/format'
import {
  IP_RETURN_SOURCE_MAP,
  IP_RESPONSIBILITY_TYPE_MAP,
  IP_RETURN_RESULT_MAP,
} from '@/utils/constants'
import type { IPReturnRecord } from '@/types/intellectualProperty'

/**
 * 退回记录卡片组件
 * 展示单条退回记录的详细信息
 */
const props = defineProps<{
  /** 退回记录数据 */
  record: IPReturnRecord
  /** 是否显示"完成修改"按钮 */
  canResolve?: boolean
}>()

defineEmits<{
  /** 完成修改 */
  (e: 'resolve', record: IPReturnRecord): void
}>()

// 是否显示"完成修改"按钮：结果为pending且有权限
const showResolveButton = computed(() => {
  return props.record.result === 'pending' && props.canResolve
})

// 退回来源标签颜色
const returnSourceColor = computed(() => {
  return '' as any
})

// 退回结果标签颜色
const resultColor = computed(() => {
  const color = IP_RETURN_RESULT_MAP[props.record.result]?.color
  return (color || '') as any
})
</script>

<style lang="scss" scoped>
.return-record-card {
  margin-bottom: 16px;

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .return-time {
        font-size: 14px;
        font-weight: 600;
        color: var(--color-text);
      }
    }
  }

  .card-field {
    margin-bottom: 8px;
    font-size: 13px;
    line-height: 1.6;

    .field-label {
      color: var(--color-text-muted);
      flex-shrink: 0;
    }

    .field-value {
      color: var(--color-text);
    }
  }

  .card-actions {
    margin-top: 12px;
    text-align: right;
  }
}
</style>
