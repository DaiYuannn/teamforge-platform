<template>
  <el-drawer
    v-model="visible"
    class="finance-record-drawer"
    :size="drawerSize"
    append-to-body
    destroy-on-close
  >
    <template #header>
      <div v-if="row" class="drawer-heading">
        <span>资金追溯详情</span>
        <h2>{{ row.project_name }} · {{ row.competition_entry_name }}</h2>
        <p>{{ row.event_name }}{{ row.event_edition ? ` · ${row.event_edition}` : '' }}</p>
      </div>
    </template>

    <template v-if="row">
      <dl class="drawer-metrics">
        <div><dt>预计 / 确认奖金</dt><dd>{{ money(row.expected_bonus) }} / {{ money(row.confirmed_bonus) }}</dd></div>
        <div><dt>奖金已到账</dt><dd class="positive">{{ money(row.received_bonus) }}</dd></div>
        <div><dt>成员垫付 / 已预留</dt><dd>{{ money(row.member_advanced) }} / {{ money(row.reserved) }}</dd></div>
        <div><dt>已支付 / 待覆盖</dt><dd>{{ money(row.paid) }} / <span :class="{ danger: row.outstanding > 0 }">{{ money(row.outstanding) }}</span></dd></div>
      </dl>

      <el-tabs v-model="activeTab" class="drawer-tabs">
        <el-tab-pane :label="`支出与报销（${row.expenses.length}）`" name="expenses">
          <el-table :data="row.expenses" row-key="id" size="small" @row-click="selectExpense">
            <el-table-column type="expand" width="40">
              <template #default="{ row: expense }">
                <section class="payment-section">
                  <header><strong>付款记录</strong><span>{{ expense.payments?.length || 0 }} 笔</span></header>
                  <div v-if="expense.payments?.length" class="payment-list">
                    <article v-for="payment in expense.payments" :key="payment.id">
                      <div><strong>{{ money(payment.amount) }}</strong><span>{{ payment.recipient_name || expense.payee_name || expense.spender_name }}</span></div>
                      <div><el-tag size="small" :type="payment.status === 'completed' ? 'success' : payment.status === 'failed' ? 'danger' : 'warning'">{{ payment.status_display || paymentStatusLabel(payment.status) }}</el-tag><span>{{ payment.payment_reference || '无流水号' }}</span></div>
                      <div class="proof-links">
                        <a v-for="attachment in payment.attachments || payment.receipts || []" :key="attachment.id" :href="attachmentUrl(attachment)" target="_blank" rel="noopener noreferrer">{{ attachmentKindLabel(attachment) }}</a>
                      </div>
                    </article>
                  </div>
                  <EmptyState v-else text="暂无付款记录" description="审核通过后可分多次向收款人付款。" compact />
                </section>
              </template>
            </el-table-column>
            <el-table-column prop="expense_date" label="日期" width="108" />
            <el-table-column label="用途" min-width="180"><template #default="{ row: expense }"><div class="record-title"><strong>{{ expense.title }}</strong><span>{{ expense.purpose || '未填用途' }}</span></div></template></el-table-column>
            <el-table-column label="垫付 / 收款人" min-width="140"><template #default="{ row: expense }">{{ expense.spender_name || '-' }} / {{ expense.payee_name || expense.spender_name || '-' }}</template></el-table-column>
            <el-table-column label="状态" width="146"><template #default="{ row: expense }"><el-tag size="small" :type="expenseStatusTone(expense.reimbursement_status)">{{ expenseStatusLabel(expense.reimbursement_status) }}</el-tag></template></el-table-column>
            <el-table-column label="金额" width="112" align="right"><template #default="{ row: expense }">{{ money(expense.amount) }}</template></el-table-column>
            <el-table-column label="已付 / 待付" width="142" align="right"><template #default="{ row: expense }">{{ money(expensePaid(expense)) }} / {{ money(expensePayable(expense)) }}</template></el-table-column>
            <el-table-column label="操作" width="142" fixed="right"><template #default="{ row: expense }"><el-button v-if="expense.can_review" link type="warning" @click.stop="reviewExpense(expense)">审核</el-button><el-button v-if="expense.can_pay && expensePayable(expense) > 0" link type="primary" @click.stop="payExpense(expense)">付款</el-button><el-button link @click.stop="selectExpense(expense)">时间线</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="`奖金与收入（${row.incomes.length}）`" name="incomes">
          <el-table :data="row.incomes" row-key="id" size="small" @row-click="selectIncome">
            <el-table-column prop="income_date" label="记录日期" width="112"><template #default="{ row: income }">{{ income.received_date || income.confirmed_date || income.expected_date || income.income_date || '-' }}</template></el-table-column>
            <el-table-column label="收入" min-width="210"><template #default="{ row: income }"><div class="record-title"><strong>{{ income.title }}</strong><span>{{ income.source || '未填来源' }}</span></div></template></el-table-column>
            <el-table-column label="阶段" width="132"><template #default="{ row: income }"><el-tag size="small" :type="income.stage === 'received' ? 'success' : income.stage === 'confirmed' ? 'warning' : 'info'">{{ incomeStageLabel(income.stage) }}</el-tag></template></el-table-column>
            <el-table-column label="金额" width="130" align="right"><template #default="{ row: income }"><strong>{{ money(income.amount) }}</strong></template></el-table-column>
            <el-table-column label="凭证" width="100" align="center"><template #default="{ row: income }">{{ income.attachments?.length || 0 }} 份</template></el-table-column>
            <el-table-column label="操作" width="150" fixed="right"><template #default="{ row: income }"><el-button v-if="income.can_manage && income.stage !== 'received'" link type="primary" @click.stop="advanceIncome(income)">推进阶段</el-button><el-button link @click.stop="selectIncome(income)">时间线</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="附件与操作时间线" name="timeline">
          <section class="record-inspection">
            <header>
              <div><span>当前记录</span><strong>{{ selectedRecordTitle }}</strong></div>
              <el-tag v-if="selectedExpense" size="small" :type="expenseStatusTone(selectedExpense.reimbursement_status)">{{ expenseStatusLabel(selectedExpense.reimbursement_status) }}</el-tag>
              <el-tag v-else-if="selectedIncome" size="small" :type="selectedIncome.stage === 'received' ? 'success' : 'warning'">{{ incomeStageLabel(selectedIncome.stage) }}</el-tag>
            </header>

            <div v-if="selectedAttachments.length" class="attachment-grid">
              <a v-for="attachment in selectedAttachments" :key="attachment.id" :href="attachmentUrl(attachment)" target="_blank" rel="noopener noreferrer">
                <el-icon><Document /></el-icon>
                <span><strong>{{ attachmentKindLabel(attachment) }}</strong><small>{{ attachment.file_name || fileName(attachmentUrl(attachment)) }}</small></span>
              </a>
            </div>
            <EmptyState v-else text="当前记录暂无附件" compact />

            <el-timeline v-loading="timelineLoading" v-if="timeline.length" class="record-timeline">
              <el-timeline-item v-for="event in timeline" :key="event.id" :timestamp="formatDateTime(event.occurred_at || event.created_at)">
                <strong>{{ event.title || event.action_display }}</strong>
                <p>{{ event.description || '无补充说明' }}</p>
                <small>{{ event.operator_name || '系统' }}</small>
              </el-timeline-item>
            </el-timeline>
            <EmptyState v-else-if="!timelineLoading" text="请先选择一笔支出或收入" description="时间线将展示登记、提交、审核、付款和凭证归档记录。" compact />
          </section>
        </el-tab-pane>
      </el-tabs>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { getFinanceTimeline } from '@/api/finance'
import { formatDateTime, formatMoneyWithComma } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import EmptyState from '@/components/EmptyState.vue'
import {
  allExpenseAttachments,
  attachmentKindLabel,
  attachmentUrl,
  completedPaymentAmount,
  expenseStatusLabel,
  expenseStatusTone,
  incomeStageLabel,
  remainingPayable,
} from './financeLedger'
import type {
  FinanceLedgerAttachment,
  FinanceLedgerExpense,
  FinanceLedgerIncome,
  FinanceTimelineEvent,
  FinanceTraceabilityLeaf,
} from '@/types/financeLedger'

const props = defineProps<{
  modelValue: boolean
  row: FinanceTraceabilityLeaf | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'review', expense: FinanceLedgerExpense): void
  (event: 'pay', expense: FinanceLedgerExpense): void
  (event: 'advance-income', income: FinanceLedgerIncome): void
}>()

const { isMobile } = useDevice()
const drawerSize = computed(() => isMobile.value ? '100%' : 'min(1080px, 88vw)')
const visible = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
const activeTab = ref('expenses')
const selectedExpense = ref<FinanceLedgerExpense | null>(null)
const selectedIncome = ref<FinanceLedgerIncome | null>(null)
const timeline = ref<FinanceTimelineEvent[]>([])
const timelineLoading = ref(false)

const selectedRecordTitle = computed(() => selectedExpense.value?.title || selectedIncome.value?.title || '未选择')
const selectedAttachments = computed<FinanceLedgerAttachment[]>(() => {
  if (selectedExpense.value) {
    return [
      ...allExpenseAttachments(selectedExpense.value),
      ...(selectedExpense.value.payments || []).flatMap((payment) => payment.attachments || payment.receipts || []),
    ]
  }
  return selectedIncome.value?.attachments || selectedIncome.value?.receipts || []
})

function money(value: number | string | null | undefined): string { return formatMoneyWithComma(Number(value || 0)) }
function fileName(url: string): string { return url.split('/').pop() || '附件' }
function paymentStatusLabel(status?: string): string { return ({ pending_proof: '待补凭证', completed: '已完成', failed: '付款失败', reversed: '已冲正' } as Record<string, string>)[status || ''] || status || '未知' }

function expensePaid(expense: unknown): number { return completedPaymentAmount(expense as FinanceLedgerExpense) }
function expensePayable(expense: unknown): number { return remainingPayable(expense as FinanceLedgerExpense) }
function reviewExpense(expense: unknown): void { emit('review', expense as FinanceLedgerExpense) }
function payExpense(expense: unknown): void { emit('pay', expense as FinanceLedgerExpense) }
function advanceIncome(income: unknown): void { emit('advance-income', income as FinanceLedgerIncome) }

async function selectExpense(expense: unknown): Promise<void> {
  selectedExpense.value = expense as FinanceLedgerExpense
  selectedIncome.value = null
  activeTab.value = 'timeline'
  await loadTimeline({ expense: (expense as FinanceLedgerExpense).id })
}

async function selectIncome(income: unknown): Promise<void> {
  selectedIncome.value = income as FinanceLedgerIncome
  selectedExpense.value = null
  activeTab.value = 'timeline'
  await loadTimeline({ income: (income as FinanceLedgerIncome).id })
}

async function loadTimeline(params: { expense?: number; income?: number }): Promise<void> {
  timelineLoading.value = true
  timeline.value = []
  try {
    const response = await getFinanceTimeline(params)
    timeline.value = Array.isArray(response)
      ? response
      : ((response as unknown as { results?: FinanceTimelineEvent[] }).results || [])
  } finally {
    timelineLoading.value = false
  }
}

watch(() => props.row?.key, () => {
  activeTab.value = 'expenses'
  selectedExpense.value = null
  selectedIncome.value = null
  timeline.value = []
})
</script>

<style scoped lang="scss">
.drawer-heading span { color: var(--color-primary); font-size: 11px; font-weight: 700; letter-spacing: .05em; }
.drawer-heading h2 { margin: 3px 0 0; font-size: 18px; }
.drawer-heading p { margin: 3px 0 0; color: var(--color-text-muted); font-size: 12px; }
.drawer-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0 0 16px; overflow: hidden; border: 1px solid var(--color-border-light); border-radius: 8px; }
.drawer-metrics div { min-width: 0; padding: 12px; background: var(--color-surface-subtle); }
.drawer-metrics div + div { border-left: 1px solid var(--color-border-light); }
.drawer-metrics dt { color: var(--color-text-muted); font-size: 11px; }
.drawer-metrics dd { margin: 5px 0 0; font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; }
.positive { color: var(--color-success); }
.danger { color: var(--color-danger); }
.record-title { display: grid; gap: 3px; }
.record-title span { color: var(--color-text-muted); font-size: 11px; }
.payment-section { padding: 8px 44px 12px; }
.payment-section > header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.payment-list { display: grid; gap: 8px; }
.payment-list article { display: grid; grid-template-columns: minmax(160px, 1fr) minmax(180px, 1fr) minmax(160px, .8fr); gap: 12px; padding: 10px 12px; background: var(--color-surface-subtle); border-radius: 7px; }
.payment-list article > div { display: flex; align-items: center; gap: 8px; }
.payment-list article span { color: var(--color-text-muted); font-size: 11px; }
.proof-links a { color: var(--color-primary); font-size: 12px; }
.record-inspection { display: grid; gap: 16px; }
.record-inspection > header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; background: var(--color-surface-subtle); border-radius: 8px; }
.record-inspection > header div { display: grid; gap: 3px; }
.record-inspection > header span { color: var(--color-text-muted); font-size: 11px; }
.attachment-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
.attachment-grid a { display: flex; align-items: center; gap: 10px; min-width: 0; padding: 11px 12px; color: var(--color-text); background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: 8px; text-decoration: none; }
.attachment-grid a:hover { border-color: var(--color-primary); }
.attachment-grid a > span { display: grid; min-width: 0; }
.attachment-grid small { overflow: hidden; color: var(--color-text-muted); text-overflow: ellipsis; white-space: nowrap; }
.record-timeline { padding: 8px 8px 0; }
.record-timeline p { margin: 4px 0; color: var(--color-text-secondary); }
.record-timeline small { color: var(--color-text-muted); }

@media (max-width: 760px) {
  .drawer-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .drawer-metrics div:nth-child(3) { border-left: 0; border-top: 1px solid var(--color-border-light); }
  .drawer-metrics div:nth-child(4) { border-top: 1px solid var(--color-border-light); }
  .payment-list article { grid-template-columns: 1fr; }
}
</style>
