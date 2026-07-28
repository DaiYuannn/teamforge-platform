<template>
  <div class="finance-table">
    <section v-if="showBudget" class="budget-summary" aria-label="预算概览">
      <div>
        <span>总预算</span>
        <strong>{{ formatMoneyWithComma(totalBudget) }}</strong>
      </div>
      <div>
        <span>总支出</span>
        <strong>{{ formatMoneyWithComma(totalExpense) }}</strong>
      </div>
      <div :class="{ danger: remaining < 0 }">
        <span>剩余</span>
        <strong>{{ formatMoneyWithComma(remaining) }}</strong>
      </div>
    </section>

    <el-table v-if="!isMobile" :data="expenses" class="expense-table">
      <template #empty>
        <EmptyState text="暂无经费记录" description="添加支出后将在此展示" icon="Wallet" compact />
      </template>
      <el-table-column prop="expense_date" label="日期" width="112">
        <template #default="{ row }">{{ formatDate(row.expense_date) }}</template>
      </el-table-column>
      <el-table-column prop="category" label="类别" width="104">
        <template #default="{ row }">
          <span class="category-label">
            <i :style="{ backgroundColor: getFinanceCategoryColor(row.category) }" />
            {{ getFinanceCategoryLabel(row.category) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目" min-width="150" show-overflow-tooltip />
      <el-table-column prop="title" label="支出说明" min-width="170" show-overflow-tooltip />
      <el-table-column prop="purpose" label="具体用途" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.purpose || '-' }}</template>
      </el-table-column>
      <el-table-column prop="reimbursement_status" label="报销状态" width="104">
        <template #default="{ row }">
          <el-tag :type="reimbursementTone(row.reimbursement_status)" size="small">
            {{ reimbursementLabel(row.reimbursement_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="spender_name" label="经手人" width="96" />
      <el-table-column prop="amount" label="金额" width="132" align="right">
        <template #default="{ row }">
          <span class="amount tabular-nums">{{ formatMoneyWithComma(row.amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="票据" width="84" align="center">
        <template #default="{ row }">
          <el-button v-if="row.receipts?.length" link type="primary" @click="showReceipts(row as FinanceExpense)">
            {{ row.receipts.length }} 张
          </el-button>
          <span v-else class="text-muted">无</span>
        </template>
      </el-table-column>
      <el-table-column
        v-if="showActions || showWorkflowActions"
        label="操作"
        :width="showWorkflowActions ? 224 : 96"
        fixed="right"
        align="center"
      >
        <template #default="{ row }">
          <template v-if="showWorkflowActions">
            <el-button
              v-if="canSubmitExpense(row as FinanceExpense)"
              link
              type="primary"
              @click="$emit('submit-reimbursement', row as FinanceExpense)"
            >提交报销</el-button>
            <el-button
              v-if="canReviewExpense(row as FinanceExpense)"
              link
              type="warning"
              @click="$emit('review-reimbursement', row as FinanceExpense)"
            >审核报销</el-button>
            <el-button
              v-if="canPayExpense(row as FinanceExpense)"
              link
              type="success"
              @click="$emit('mark-paid', row as FinanceExpense)"
            >登记打款</el-button>
          </template>
          <template v-if="showActions">
            <el-tooltip content="编辑支出">
              <el-button circle text :icon="Edit" aria-label="编辑支出" @click="$emit('edit', row as FinanceExpense)" />
            </el-tooltip>
            <el-tooltip content="删除支出">
              <el-button circle text type="danger" :icon="Delete" aria-label="删除支出" @click="$emit('delete', row as FinanceExpense)" />
            </el-tooltip>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <div v-else-if="expenses.length" class="expense-mobile-list">
      <article v-for="expense in expenses" :key="expense.id" class="expense-mobile-card">
        <div class="expense-mobile-head">
          <span class="category-label">
            <i :style="{ backgroundColor: getFinanceCategoryColor(expense.category) }" />
            {{ getFinanceCategoryLabel(expense.category) }}
          </span>
          <strong class="amount tabular-nums">{{ formatMoneyWithComma(expense.amount) }}</strong>
        </div>
        <el-tag :type="reimbursementTone(expense.reimbursement_status)" size="small" class="workflow-tag">
          {{ reimbursementLabel(expense.reimbursement_status) }}
        </el-tag>
        <h3>{{ expense.title }}</h3>
        <p v-if="expense.purpose">{{ expense.purpose }}</p>
        <dl>
          <div><dt>项目</dt><dd>{{ expense.project_name || '-' }}</dd></div>
          <div><dt>日期</dt><dd>{{ formatDate(expense.expense_date) }}</dd></div>
          <div><dt>经手人</dt><dd>{{ expense.spender_name || '-' }}</dd></div>
        </dl>
        <div class="expense-mobile-actions">
          <el-button v-if="expense.receipts?.length" size="small" :icon="Picture" @click="showReceipts(expense)">
            票据 {{ expense.receipts.length }} 张
          </el-button>
          <span v-else class="text-muted">无票据</span>
          <span class="action-spacer" />
          <template v-if="showActions">
            <el-tooltip content="编辑支出">
              <el-button circle text :icon="Edit" aria-label="编辑支出" @click="$emit('edit', expense)" />
            </el-tooltip>
            <el-tooltip content="删除支出">
              <el-button circle text type="danger" :icon="Delete" aria-label="删除支出" @click="$emit('delete', expense)" />
            </el-tooltip>
          </template>
          <template v-if="showWorkflowActions">
            <el-button
              v-if="canSubmitExpense(expense)"
              link
              type="primary"
              @click="$emit('submit-reimbursement', expense)"
            >提交报销</el-button>
            <el-button
              v-if="canReviewExpense(expense)"
              link
              type="warning"
              @click="$emit('review-reimbursement', expense)"
            >审核</el-button>
            <el-button
              v-if="canPayExpense(expense)"
              link
              type="success"
              @click="$emit('mark-paid', expense)"
            >登记打款</el-button>
          </template>
        </div>
      </article>
    </div>

    <EmptyState v-else text="暂无经费记录" description="添加支出后将在此展示" icon="Wallet" compact />

    <el-dialog v-model="receiptDialogVisible" title="票据预览" width="600px">
      <div class="receipt-list">
        <article v-for="receipt in currentReceipts" :key="receipt.id" class="receipt-item">
          <el-image
            :src="receipt.file"
            :preview-src-list="[receipt.file || '']"
            fit="contain"
            class="receipt-image"
          >
            <template #error>
              <div class="image-error">
                <el-icon size="32"><Picture /></el-icon>
                <span>{{ getFileName(receipt.file) }}</span>
              </div>
            </template>
          </el-image>
          <div class="receipt-info">
            <span class="receipt-name">{{ getFileName(receipt.file) }}</span>
            <span>{{ formatDateTime(receipt.created_at) }}</span>
          </div>
        </article>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Delete, Edit, Picture } from '@element-plus/icons-vue'
import { useDevice } from '@/composables/useDevice'
import {
  formatDate,
  formatDateTime,
  formatMoneyWithComma,
  getFinanceCategoryColor,
  getFinanceCategoryLabel,
} from '@/utils/format'
import type { FinanceExpense, FinanceReceipt } from '@/types'
import EmptyState from '@/components/EmptyState.vue'

const props = withDefaults(
  defineProps<{
    expenses: FinanceExpense[]
    totalBudget?: number
    showActions?: boolean
    showBudget?: boolean
    showWorkflowActions?: boolean
    canSubmit?: (expense: FinanceExpense) => boolean
    canReview?: (expense: FinanceExpense) => boolean
    canPay?: (expense: FinanceExpense) => boolean
  }>(),
  {
    totalBudget: 0,
    showActions: true,
    showBudget: true,
    showWorkflowActions: false,
  },
)

defineEmits<{
  (event: 'edit', expense: FinanceExpense): void
  (event: 'delete', expense: FinanceExpense): void
  (event: 'submit-reimbursement', expense: FinanceExpense): void
  (event: 'review-reimbursement', expense: FinanceExpense): void
  (event: 'mark-paid', expense: FinanceExpense): void
}>()

const { isMobile } = useDevice()
const receiptDialogVisible = ref(false)
const currentReceipts = ref<FinanceReceipt[]>([])

function toAmount(value: number | string | null | undefined): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

const totalExpense = computed(() => props.expenses.reduce((sum, item) => sum + toAmount(item.amount), 0))
const remaining = computed(() => toAmount(props.totalBudget) - totalExpense.value)

function showReceipts(expense: FinanceExpense): void {
  currentReceipts.value = expense.receipts || []
  receiptDialogVisible.value = true
}

function getFileName(filePath: string | undefined): string {
  if (!filePath) return '-'
  return filePath.split('/').pop() || filePath
}

const REIMBURSEMENT_LABELS: Record<string, string> = {
  draft: '草稿',
  pending: '待报销审核',
  approved: '审核通过·待打款',
  rejected: '已驳回',
  paid: '已打款·报销完成',
  not_required: '无需报销',
}

function reimbursementLabel(status?: string): string {
  return REIMBURSEMENT_LABELS[status || 'draft'] || status || '草稿'
}

function reimbursementTone(status?: string): 'info' | 'warning' | 'success' | 'danger' {
  if (status === 'paid' || status === 'not_required') return 'success'
  if (status === 'pending' || status === 'approved') return 'warning'
  if (status === 'rejected') return 'danger'
  return 'info'
}

function canSubmitExpense(expense: FinanceExpense): boolean {
  return Boolean(props.canSubmit?.(expense))
}

function canReviewExpense(expense: FinanceExpense): boolean {
  return Boolean(props.canReview?.(expense))
}

function canPayExpense(expense: FinanceExpense): boolean {
  return Boolean(props.canPay?.(expense))
}
</script>

<style lang="scss" scoped>
.budget-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 16px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.budget-summary > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 12px 14px;
}

.budget-summary > div + div { border-left: 1px solid var(--color-border-light); }
.budget-summary span { color: var(--color-text-muted); font-size: 12px; }
.budget-summary strong { overflow: hidden; font-size: 17px; text-overflow: ellipsis; white-space: nowrap; }
.budget-summary .danger strong { color: var(--color-danger); }

.category-label {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--color-text-regular);
  font-size: 12px;
  white-space: nowrap;
}

.category-label i {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
}

.amount {
  color: var(--color-text);
  font-weight: 650;
}

.workflow-tag {
  margin-top: 8px;
}

.text-muted {
  color: var(--color-text-muted);
  font-size: 12px;
}

.receipt-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.receipt-item {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.receipt-image,
.image-error {
  width: 100%;
  height: 180px;
  border-radius: var(--radius-xs);
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
}

.receipt-info {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.receipt-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.expense-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.expense-mobile-card {
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.expense-mobile-head,
.expense-mobile-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.expense-mobile-card h3 {
  margin-top: 10px;
  font-size: 14px;
  font-weight: 600;
}

.expense-mobile-card > p {
  display: -webkit-box;
  margin-top: 5px;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.expense-mobile-card dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 14px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border-light);
}

.expense-mobile-card dl div:first-child { grid-column: 1 / -1; }
.expense-mobile-card dt { color: var(--color-text-muted); font-size: 11px; }
.expense-mobile-card dd { margin-top: 2px; color: var(--color-text-regular); font-size: 12px; }

.expense-mobile-actions {
  margin-top: 12px;
}

.action-spacer { flex: 1; }

@media screen and (max-width: 480px) {
  .receipt-list {
    grid-template-columns: 1fr;
  }

  .budget-summary strong {
    font-size: 14px;
  }
}
</style>
