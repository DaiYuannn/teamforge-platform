<template>
  <div class="finance-table">
    <!-- 预算概览 -->
    <div v-if="showBudget" class="budget-summary">
      <el-row :gutter="16">
        <el-col :span="8">
          <div class="summary-card">
            <div class="summary-label">总预算</div>
            <div class="summary-value">{{ formatMoneyWithComma(totalBudget) }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="summary-card">
            <div class="summary-label">总支出</div>
            <div class="summary-value danger">{{ formatMoneyWithComma(totalExpense) }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="summary-card">
            <div class="summary-label">剩余</div>
            <div class="summary-value" :class="{ danger: remaining < 0 }">
              {{ formatMoneyWithComma(remaining) }}
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 经费支出表格 -->
    <el-table :data="expenses" border stripe style="width: 100%" class="expense-table">
      <el-table-column prop="expense_date" label="日期" width="120">
        <template #default="{ row }">{{ formatDate(row.expense_date) }}</template>
      </el-table-column>
      <el-table-column prop="category" label="类别" width="100">
        <template #default="{ row }">
          <el-tag :color="getFinanceCategoryColor(row.category)" effect="plain" size="small">
            {{ getFinanceCategoryLabel(row.category) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="说明" min-width="150" show-overflow-tooltip />
      <el-table-column prop="amount" label="金额" width="120" align="right">
        <template #default="{ row }">
          <span class="amount">{{ formatMoneyWithComma(row.amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="spender_name" label="经手人" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getFinanceExpenseStatusTagType(row.status) as any" size="small">
            {{ getFinanceExpenseStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="票据" width="80" align="center">
        <template #default="{ row }">
          <el-button
            v-if="row.receipts && row.receipts.length > 0"
            type="primary"
            link
            @click="showReceipts(row as any)"
          >
            查看({{ row.receipts.length }})
          </el-button>
          <span v-else class="text-muted">无</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showActions" label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="$emit('edit', row as FinanceExpense)">编辑</el-button>
          <el-button type="danger" link @click="$emit('delete', row as FinanceExpense)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 票据图片预览弹窗 -->
    <el-dialog v-model="receiptDialogVisible" title="票据预览" width="600px">
      <div class="receipt-list">
        <div v-for="receipt in currentReceipts" :key="receipt.id" class="receipt-item">
          <el-image
            :src="receipt.file"
            :preview-src-list="[receipt.file || '']"
            fit="contain"
            class="receipt-image"
          >
            <template #error>
              <div class="image-error">
                <el-icon size="40"><Picture /></el-icon>
                <span>{{ getFileName(receipt.file) }}</span>
              </div>
            </template>
          </el-image>
          <div class="receipt-info">
            <span class="receipt-name">{{ getFileName(receipt.file) }}</span>
            <span class="receipt-date">{{ formatDateTime(receipt.uploaded_at) }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  formatDate,
  formatDateTime,
  formatMoneyWithComma,
  getFinanceCategoryLabel,
  getFinanceCategoryColor,
  getFinanceExpenseStatusLabel,
  getFinanceExpenseStatusTagType,
} from '@/utils/format'
import type { FinanceExpense, FinanceReceipt } from '@/types'

/**
 * 经费表格组件
 * 显示经费支出列表，含票据图片预览
 */
const props = withDefaults(
  defineProps<{
    /** 经费支出列表 */
    expenses: FinanceExpense[]
    /** 预算总额 */
    totalBudget?: number
    /** 是否显示操作列 */
    showActions?: boolean
    /** 是否显示预算概览 */
    showBudget?: boolean
  }>(),
  {
    totalBudget: 0,
    showActions: true,
    showBudget: true,
  }
)

defineEmits<{
  /** 编辑支出 */
  (e: 'edit', expense: FinanceExpense): void
  /** 删除支出 */
  (e: 'delete', expense: FinanceExpense): void
}>()

function toAmount(value: number | string | null | undefined): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

// 总支出
const totalExpense = computed(() => props.expenses.reduce((sum, e) => sum + toAmount(e.amount), 0))

// 剩余预算
const remaining = computed(() => toAmount(props.totalBudget) - totalExpense.value)

// 票据预览弹窗
const receiptDialogVisible = ref(false)
const currentReceipts = ref<FinanceReceipt[]>([])

// 显示票据
function showReceipts(expense: FinanceExpense & { receipts?: FinanceReceipt[] }): void {
  currentReceipts.value = expense.receipts || []
  receiptDialogVisible.value = true
}

// 从 file 字段中提取文件名
function getFileName(filePath: string | undefined): string {
  if (!filePath) return '-'
  return filePath.split('/').pop() || filePath
}
</script>

<style lang="scss" scoped>
.finance-table {
  .budget-summary {
    margin-bottom: 16px;

    .summary-card {
      background: #fff;
      border-radius: 8px;
      padding: 16px;
      text-align: center;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);

      .summary-label {
        font-size: 13px;
        color: #909399;
        margin-bottom: 8px;
      }

      .summary-value {
        font-size: 22px;
        font-weight: 600;
        color: #303133;

        &.danger {
          color: #f56c6c;
        }
      }
    }
  }

  .amount {
    font-weight: 600;
    color: #f56c6c;
  }

  .text-muted {
    color: #c0c4cc;
    font-size: 13px;
  }
}

.receipt-list {
  .receipt-item {
    margin-bottom: 16px;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 12px;

    .receipt-image {
      width: 100%;
      height: 200px;
      border-radius: 4px;
    }

    .image-error {
      width: 100%;
      height: 200px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: #f5f7fa;
      color: #c0c4cc;
      gap: 8px;
      font-size: 13px;
    }

    .receipt-info {
      margin-top: 8px;
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #909399;
    }
  }
}
</style>
