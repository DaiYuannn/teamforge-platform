<template>
  <div class="page-container finance-page">
    <PageHeader title="经费管理" subtitle="查看团队预算使用、支出结构和需要关注的项目">
      <template #actions>
        <el-button v-if="canSetBudget" :icon="Setting" @click="openBudgetDialog">
          设置预算
        </el-button>
        <el-button v-if="canRegisterIncome" :icon="Plus" @click="() => openIncomeDialog()">
          登记收入
        </el-button>
        <el-button type="primary" :icon="Plus" @click="openExpenseDialog">
          新增支出
        </el-button>
        <el-button :icon="CameraFilled" @click="openOCRDialog">
          票据 OCR
        </el-button>
        <el-dropdown @command="handleExport">
          <el-button :icon="Download">
            导出数据
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="xlsx">导出 Excel</el-dropdown-item>
              <el-dropdown-item command="pdf">导出 PDF</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </PageHeader>

    <div v-if="loadError" class="status-banner" role="alert">
      <el-icon><WarningFilled /></el-icon>
      <span>经费数据未完整加载，请重新尝试。</span>
      <el-button link type="primary" @click="loadData">重新加载</el-button>
    </div>

    <section v-loading="loading" class="metric-strip" aria-label="经费概览">
      <div class="metric-item metric-item--spending">
        <span>已记录支出</span>
        <strong class="tabular-nums">{{ formatMoneyWithComma(totalRecordedExpense) }}</strong>
        <small>{{ expenseList.length }} 笔；先看实际花在哪里，再看报销和余额</small>
      </div>
      <div class="metric-item">
        <span>报销进度</span>
        <strong class="tabular-nums">{{ formatMoneyWithComma(totalExpense) }}</strong>
        <small>已完成；流程中 {{ formatMoneyWithComma(totalPending) }}，未进入流程 {{ formatMoneyWithComma(totalUncommitted) }}</small>
      </div>
      <div class="metric-item">
        <span>核定预算上限</span>
        <strong class="tabular-nums">{{ formatMoneyWithComma(totalPlanned) }}</strong>
        <small>累计入账 {{ formatMoneyWithComma(totalIncome) }}；未单设时沿用入账额</small>
      </div>
      <div class="metric-item" :class="{ 'metric-item--danger': totalAvailable < 0 }">
        <span>计算可用额度</span>
        <strong class="tabular-nums">{{ formatMoneyWithComma(totalAvailable) }}</strong>
        <small>{{ totalAvailable < 0 ? '计算结果已超预算' : '计算值＝预算控制基准－已完成及流程中支出' }}</small>
      </div>
    </section>

    <section class="workspace-panel spending-destination-panel">
      <header class="panel-header">
        <div>
          <h2>钱花在哪里</h2>
          <p>按项目汇总已记录支出，并列出经手人、用途和报销进度</p>
        </div>
        <el-tag v-if="spendingDestinations.length" type="primary" effect="plain">
          {{ spendingDestinations.length }} 个项目
        </el-tag>
      </header>
      <el-table v-if="spendingDestinations.length" :data="spendingDestinations" class="destination-table">
        <el-table-column prop="projectName" label="项目" min-width="150" show-overflow-tooltip />
        <el-table-column label="已记录支出" width="138" align="right">
          <template #default="{ row }">
            <strong class="destination-amount tabular-nums">{{ formatMoneyWithComma(row.total) }}</strong>
            <small>{{ row.count }} 笔</small>
          </template>
        </el-table-column>
        <el-table-column label="谁花的" min-width="190">
          <template #default="{ row }">
            <div class="destination-lines">
              <span v-for="person in row.people" :key="person.name">
                {{ person.name }} {{ formatMoneyWithComma(person.amount) }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="花在什么地方" min-width="240">
          <template #default="{ row }">
            <div class="destination-lines">
              <span v-for="purpose in row.purposes" :key="purpose.name">
                {{ purpose.name }} {{ formatMoneyWithComma(purpose.amount) }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="报销情况" min-width="185">
          <template #default="{ row }">
            <div class="destination-status">
              <span>完成 {{ formatMoneyWithComma(row.completed) }}</span>
              <span>流程中 {{ formatMoneyWithComma(row.pending) }}</span>
              <span v-if="row.uncommitted > 0">未进入流程 {{ formatMoneyWithComma(row.uncommitted) }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-else-if="!loading"
        text="暂无支出明细"
        description="新增支出后，这里会直接显示项目、经手人和用途。"
        icon="Wallet"
        compact
      />
    </section>

    <div class="finance-overview-grid">
      <section class="workspace-panel category-panel">
        <header class="panel-header">
          <div>
            <h2>支出结构</h2>
            <p>按全部已记录支出的类别比较金额</p>
          </div>
        </header>
        <div v-if="categoryBreakdown.length" ref="chartRef" class="chart-container" />
        <EmptyState
          v-else-if="!loading"
          text="暂无支出数据"
          description="记录支出后会在这里形成类别对比。"
          icon="DataAnalysis"
          compact
        />
      </section>

      <section class="workspace-panel risk-panel">
        <header class="panel-header">
          <div>
            <h2>项目支出与计算余额</h2>
            <p>每个项目先显示支出，再显示预算上限和系统计算值</p>
          </div>
          <el-tag v-if="riskProjects.length" type="warning" size="small">
            {{ riskProjects.length }} 项需关注
          </el-tag>
        </header>

        <div v-if="projectFinance.length" class="project-budget-list">
          <article v-for="item in projectFinance.slice(0, 6)" :key="item.projectId" class="project-budget-row">
            <div class="project-budget-head">
              <div>
                <h3>{{ item.projectName }}</h3>
                <span>已记录支出 {{ formatMoneyWithComma(item.recorded) }} / 上限 {{ formatMoneyWithComma(item.budget) }}</span>
                <span>进入预算占用 {{ formatMoneyWithComma(item.expense) }} · 计算可用 {{ formatMoneyWithComma(item.available) }}</span>
              </div>
              <span class="utilization" :data-tone="item.tone">{{ item.rate }}%</span>
            </div>
            <el-progress
              :percentage="Math.min(item.rate, 100)"
              :show-text="false"
              :stroke-width="6"
              :color="progressColor(item.tone)"
            />
          </article>
        </div>
        <EmptyState
          v-else-if="!loading"
          text="暂无项目预算"
          description="创建项目预算后可查看使用风险。"
          icon="Wallet"
          compact
        />
      </section>
    </div>

    <section class="workspace-panel details-panel">
      <header class="details-toolbar">
        <div>
          <h2>收支与报销流水</h2>
          <p>每笔资金都有状态、审核人和付款凭证</p>
        </div>
        <el-select
          v-model="filterProject"
          aria-label="按项目筛选收支流水"
          placeholder="全部项目"
          clearable
          filterable
          class="project-filter"
          @change="loadData"
        >
          <el-option v-for="project in projectOptions" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
      </header>

      <el-alert
        class="workflow-explanation"
        type="info"
        :closable="false"
        show-icon
        title="报销流程：保存草稿 → 待报销审核 → 审核通过、待打款 → 已打款、报销完成。这里的“已打款”指团队向申请人完成报销，不是申请人向商家付款。"
      />

      <el-tabs v-model="financeTab" class="finance-tabs">
        <el-tab-pane :label="`支出与报销（${expenseList.length}）`" name="expenses">
          <FinanceTable
            :expenses="expenseList"
            :show-budget="false"
            :show-actions="false"
            :show-workflow-actions="true"
            :can-submit="canSubmitExpense"
            :can-review="canReviewExpense"
            :can-pay="canPayExpense"
            @submit-reimbursement="handleSubmitReimbursement"
            @review-reimbursement="openReviewDialog"
            @mark-paid="openPaymentDialog"
          />
        </el-tab-pane>
        <el-tab-pane :label="`收入流水（${incomeList.length}）`" name="incomes">
          <el-table :data="incomeList">
            <template #empty>
              <EmptyState text="暂无收入流水" description="登记奖金、拨款或赞助后，预算将自动汇总。" icon="Wallet" compact />
            </template>
            <el-table-column prop="income_date" label="入账日期" width="112" />
            <el-table-column prop="income_type_display" label="类型" width="110" />
            <el-table-column prop="project_name" label="项目" min-width="150" show-overflow-tooltip />
            <el-table-column prop="title" label="收入说明" min-width="170" show-overflow-tooltip />
            <el-table-column prop="source" label="来源" min-width="130" show-overflow-tooltip />
            <el-table-column prop="reference_number" label="凭证号" min-width="130" show-overflow-tooltip />
            <el-table-column prop="amount" label="金额" width="132" align="right">
              <template #default="{ row }">
                <strong class="tabular-nums">{{ formatMoneyWithComma(row.amount) }}</strong>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="116" fixed="right">
              <template #default="{ row }">
                <template v-if="canManageProjectFinance((row as FinanceIncome).project)">
                  <el-button link type="primary" @click="openIncomeDialog(row as FinanceIncome)">编辑</el-button>
                  <el-button link type="danger" @click="handleDeleteIncome(row as FinanceIncome)">删除</el-button>
                </template>
                <span v-else class="text-muted">只读</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="budgetDialogVisible" title="设置项目核定预算" width="520px" append-to-body>
      <el-alert
        title="核定预算是预计允许支出的上限，与奖金、拨款等实际入账分开统计。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-form :model="budgetForm" label-position="top">
        <el-form-item label="所属项目" required>
          <el-select v-model="budgetForm.project" filterable @change="syncBudgetForm">
            <el-option
              v-for="project in projectOptions"
              :key="project.id"
              :label="project.name"
              :value="project.id"
              :disabled="!canConfigureProjectBudget(project.id)"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="核定预算上限" required>
          <el-input-number
            v-model="budgetForm.planned_amount"
            :min="0"
            :precision="2"
            :controls="false"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="budgetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="budgetSaving" @click="saveBudget">保存预算</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="expenseDialogVisible" title="新增支出" width="620px" append-to-body>
      <el-alert
        title="先记录已经发生的支出，保存后为草稿；确认票据和信息无误后再提交报销。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-form :model="expenseForm" label-position="top">
        <div class="ocr-form-grid">
          <el-form-item label="所属项目" required>
            <el-select v-model="expenseForm.project" filterable>
              <el-option v-for="project in projectOptions" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="金额" required>
            <el-input-number v-model="expenseForm.amount" :min="0.01" :precision="2" :controls="false" />
          </el-form-item>
          <el-form-item label="支出日期" required>
            <el-date-picker v-model="expenseForm.expense_date" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="类别" required>
            <el-select v-model="expenseForm.category">
              <el-option label="材料费" value="material" />
              <el-option label="设备费" value="equipment" />
              <el-option label="打印费" value="printing" />
              <el-option label="差旅费" value="travel" />
              <el-option label="软件费" value="software" />
              <el-option label="比赛报名费" value="competition_fee" />
              <el-option label="推广费" value="promotion" />
              <el-option label="劳务费" value="labor" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="支出标题" required>
          <el-input v-model="expenseForm.title" maxlength="200" />
        </el-form-item>
        <el-form-item label="用途说明">
          <el-input v-model="expenseForm.purpose" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="票据（选填）">
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="handleManualReceiptChange"
            :on-remove="handleManualReceiptRemove"
          >
            <el-button>选择票据图片</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="expenseDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="expenseSaving" @click="saveExpense">保存为草稿</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="incomeDialogVisible"
      :title="editingIncome ? '编辑收入流水' : '登记收入流水'"
      width="620px"
      append-to-body
    >
      <el-form :model="incomeForm" label-position="top">
        <div class="ocr-form-grid">
          <el-form-item label="所属项目" required>
            <el-select v-model="incomeForm.project" filterable>
              <el-option v-for="project in projectOptions" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="收入类型" required>
            <el-select v-model="incomeForm.income_type">
              <el-option label="比赛奖金" value="bonus" />
              <el-option label="项目拨款" value="grant" />
              <el-option label="赞助收入" value="sponsorship" />
              <el-option label="退款入账" value="refund" />
              <el-option label="其他收入" value="other" />
            </el-select>
          </el-form-item>
          <el-form-item label="金额" required>
            <el-input-number v-model="incomeForm.amount" :min="0.01" :precision="2" :controls="false" />
          </el-form-item>
          <el-form-item label="入账日期" required>
            <el-date-picker v-model="incomeForm.income_date" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
        </div>
        <el-form-item label="收入标题" required>
          <el-input v-model="incomeForm.title" maxlength="200" />
        </el-form-item>
        <div class="ocr-form-grid">
          <el-form-item label="收入来源">
            <el-input v-model="incomeForm.source" />
          </el-form-item>
          <el-form-item label="入账凭证号">
            <el-input v-model="incomeForm.reference_number" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="incomeForm.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="incomeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="incomeSaving" @click="saveIncome">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reviewDialogVisible" title="审核报销" width="520px" append-to-body>
      <el-form :model="reviewForm" label-position="top">
        <el-form-item label="审核结果">
          <el-radio-group v-model="reviewForm.approved">
            <el-radio :value="true">审核通过</el-radio>
            <el-radio :value="false">驳回补充</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="审核意见">
          <el-input v-model="reviewForm.opinion" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="workflowSaving" @click="saveReview">提交审核</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="paymentDialogVisible" title="登记报销打款" width="520px" append-to-body>
      <el-form :model="paymentForm" label-position="top">
        <el-form-item label="付款方式" required>
          <el-select v-model="paymentForm.payment_method">
            <el-option label="银行转账" value="银行转账" />
            <el-option label="微信支付" value="微信支付" />
            <el-option label="支付宝" value="支付宝" />
            <el-option label="现金" value="现金" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款流水号">
          <el-input v-model="paymentForm.payment_reference" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="paymentDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="workflowSaving" @click="savePayment">确认已向申请人打款</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="ocrVisible"
      title="票据 OCR 识别"
      width="680px"
      append-to-body
      destroy-on-close
    >
      <div class="ocr-workspace">
        <el-alert
          v-if="ocrDraftExpenseId"
          type="warning"
          :closable="false"
          show-icon
          :title="`票据尚未关联，重试将继续使用草稿支出 #${ocrDraftExpenseId}`"
        />
        <el-upload
          drag
          :auto-upload="false"
          :limit="1"
          accept="image/jpeg,image/png,image/gif,image/webp"
          :on-change="handleReceiptSelect"
          :on-remove="handleReceiptRemove"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖入票据图片，或<em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 JPG、PNG、GIF、WebP，单张不超过 10MB。</div>
          </template>
        </el-upload>

        <div v-if="receiptFile" class="ocr-action-row">
          <span>{{ receiptFile.name }}</span>
          <el-button
            type="primary"
            :loading="ocrLoading"
            :disabled="!receiptFile"
            @click="handleRecognizeReceipt"
          >
            开始识别
          </el-button>
        </div>

        <template v-if="ocrResult">
          <el-alert
            v-if="ocrResult.recognized.warnings.length"
            type="warning"
            :closable="false"
            show-icon
          >
            <template #title>请人工核对：{{ ocrResult.recognized.warnings.join('；') }}</template>
          </el-alert>
          <div class="ocr-result-head">
            <div>
              <strong>识别结果</strong>
              <span>保存前可修正所有字段</span>
            </div>
            <el-tag :type="ocrResult.recognized.confidence >= 0.7 ? 'success' : 'warning'">
              综合置信度 {{ Math.round(ocrResult.recognized.confidence * 100) }}%
            </el-tag>
          </div>
          <el-form label-position="top" :model="ocrForm">
            <div class="ocr-form-grid">
              <el-form-item label="所属项目" required>
                <el-select v-model="ocrForm.project" filterable placeholder="请选择项目">
                  <el-option
                    v-for="project in projectOptions"
                    :key="project.id"
                    :label="project.name"
                    :value="project.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="金额" required>
                <el-input-number v-model="ocrForm.amount" :min="0.01" :precision="2" :controls="false" />
              </el-form-item>
              <el-form-item label="支出日期" required>
                <el-date-picker
                  v-model="ocrForm.expense_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="选择日期"
                />
              </el-form-item>
              <el-form-item label="类别" required>
                <el-select v-model="ocrForm.category">
                  <el-option label="差旅交通" value="travel" />
                  <el-option label="设备采购" value="equipment" />
                  <el-option label="材料耗材" value="material" />
                  <el-option label="打印费" value="printing" />
                  <el-option label="软件费" value="software" />
                  <el-option label="比赛报名费" value="competition_fee" />
                  <el-option label="推广费" value="promotion" />
                  <el-option label="劳务费" value="labor" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
            </div>
            <el-form-item label="支出标题" required>
              <el-input v-model="ocrForm.title" maxlength="200" />
            </el-form-item>
            <el-form-item label="用途与票据信息">
              <el-input v-model="ocrForm.purpose" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>
          <el-collapse class="ocr-raw-text">
            <el-collapse-item title="查看 OCR 原文">
              <pre>{{ ocrResult.raw_text || '未识别到文本' }}</pre>
            </el-collapse-item>
          </el-collapse>
        </template>
      </div>
      <template #footer>
        <el-button @click="ocrVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="ocrSaving"
          :disabled="!ocrResult"
          @click="saveOCRExpense"
        >
          保存支出并关联票据
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import { ArrowDown, CameraFilled, Download, Plus, Setting, UploadFilled, WarningFilled } from '@element-plus/icons-vue'
import {
  createFinanceBudget,
  createFinanceIncome,
  createFinanceExpense,
  deleteFinanceExpense,
  deleteFinanceIncome,
  getAllFinanceBudgets,
  getAllFinanceExpenses,
  getAllFinanceIncomes,
  markReimbursementPaid,
  recognizeReceipt,
  resolveFinanceExportTarget,
  reviewReimbursement,
  submitReimbursement,
  updateFinanceIncome,
  updateFinanceBudget,
  updateFinanceExpense,
  uploadReceipt,
  type FinanceExportFormat,
  type OCRReceiptResult,
} from '@/api/finance'
import { getProjects } from '@/api/projects'
import { exportData } from '@/api/exports'
import { downloadBlob, formatMoneyWithComma, getFinanceCategoryLabel } from '@/utils/format'
import { useUserStore } from '@/stores/user'
import {
  createEChartsTooltipStyle,
  readEChartsThemePalette,
  useEChartsTheme,
} from '@/composables/useEChartsTheme'
import type {
  FinanceBudget,
  FinanceCategory,
  FinanceExpense,
  FinanceIncome,
  FinanceIncomeType,
  Project,
} from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import FinanceTable from '@/components/FinanceTable.vue'
import PageHeader from '@/components/PageHeader.vue'

type BudgetTone = 'success' | 'warning' | 'danger' | 'neutral'

interface ProjectFinanceRow {
  projectId: number
  projectName: string
  budget: number
  expense: number
  recorded: number
  available: number
  rate: number
  tone: BudgetTone
}

interface SpendingGroup {
  name: string
  amount: number
}

interface SpendingDestinationRow {
  projectId: number
  projectName: string
  total: number
  count: number
  people: SpendingGroup[]
  purposes: SpendingGroup[]
  completed: number
  pending: number
  uncommitted: number
}

const route = useRoute()
const requestedProjectId = Number(route.query.project_id)
const expenseList = ref<FinanceExpense[]>([])
const incomeList = ref<FinanceIncome[]>([])
const budgetList = ref<FinanceBudget[]>([])
const projectOptions = ref<Project[]>([])
const filterProject = ref<number | undefined>(
  Number.isInteger(requestedProjectId) && requestedProjectId > 0
    ? requestedProjectId
    : undefined,
)
const financeTab = ref('expenses')
const chartRef = ref<HTMLElement>()
const loading = ref(false)
const loadError = ref(false)
const ocrVisible = ref(false)
const ocrLoading = ref(false)
const ocrSaving = ref(false)
const receiptFile = ref<File | null>(null)
const ocrResult = ref<OCRReceiptResult | null>(null)
const ocrDraftExpenseId = ref<number | null>(null)
const budgetDialogVisible = ref(false)
const budgetSaving = ref(false)
const expenseDialogVisible = ref(false)
const expenseSaving = ref(false)
const manualReceiptFile = ref<File | null>(null)
const incomeDialogVisible = ref(false)
const incomeSaving = ref(false)
const editingIncome = ref<FinanceIncome | null>(null)
const reviewDialogVisible = ref(false)
const paymentDialogVisible = ref(false)
const workflowSaving = ref(false)
const workflowExpense = ref<FinanceExpense | null>(null)
const userStore = useUserStore()
const incomeForm = reactive({
  project: undefined as number | undefined,
  title: '',
  amount: undefined as number | undefined,
  income_type: 'grant' as FinanceIncomeType,
  income_date: '',
  source: '',
  reference_number: '',
  note: '',
})
const reviewForm = reactive({ approved: true, opinion: '' })
const paymentForm = reactive({ payment_method: '银行转账', payment_reference: '' })
const budgetForm = reactive({
  project: undefined as number | undefined,
  planned_amount: undefined as number | undefined,
})
const expenseForm = reactive({
  project: undefined as number | undefined,
  amount: undefined as number | undefined,
  expense_date: '',
  category: 'other' as FinanceCategory,
  title: '',
  purpose: '',
})
const ocrForm = reactive({
  project: undefined as number | undefined,
  amount: undefined as number | undefined,
  expense_date: '',
  category: 'other' as FinanceCategory,
  title: '',
  purpose: '',
})
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

function toAmount(value: number | string | null | undefined): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

const paidExpenses = computed(() =>
  expenseList.value.filter((item) => ['paid', 'not_required'].includes(item.reimbursement_status || 'draft')),
)
const totalRecordedExpense = computed(() =>
  expenseList.value.reduce((sum, item) => sum + toAmount(item.amount), 0),
)
const totalExpense = computed(() => paidExpenses.value.reduce((sum, item) => sum + toAmount(item.amount), 0))
const pendingExpenses = computed(() =>
  expenseList.value.filter((item) => ['pending', 'approved'].includes(item.reimbursement_status || 'draft')),
)
const totalPending = computed(() => pendingExpenses.value.reduce((sum, item) => sum + toAmount(item.amount), 0))
const totalCommitted = computed(() => totalExpense.value + totalPending.value)
const totalUncommitted = computed(() =>
  Math.max(0, totalRecordedExpense.value - totalCommitted.value),
)
const totalIncome = computed(() =>
  budgetList.value.reduce((sum, item) => sum + toAmount(item.bonus_amount) + toAmount(item.other_income), 0),
)
const totalPlanned = computed(() =>
  budgetList.value.reduce((sum, item) => sum + toAmount(item.budget_basis), 0),
)
const totalAvailable = computed(() =>
  budgetList.value.reduce((sum, item) => sum + toAmount(item.available_amount), 0),
)

const categoryBreakdown = computed(() => {
  const totals = new Map<string, number>()
  expenseList.value.forEach((item) => {
    const key = item.category || 'other'
    totals.set(key, (totals.get(key) || 0) + toAmount(item.amount))
  })
  return Array.from(totals.entries())
    .map(([key, value]) => ({ key, name: getFinanceCategoryLabel(key), value }))
    .filter((item) => item.value > 0)
    .sort((left, right) => right.value - left.value)
})

function topSpendingGroups(totals: Map<string, number>, limit = 3): SpendingGroup[] {
  return Array.from(totals.entries())
    .map(([name, amount]) => ({ name, amount }))
    .sort((left, right) => right.amount - left.amount)
    .slice(0, limit)
}

const spendingDestinations = computed<SpendingDestinationRow[]>(() => {
  const rows = new Map<number, {
    projectName: string
    total: number
    count: number
    people: Map<string, number>
    purposes: Map<string, number>
    completed: number
    pending: number
    uncommitted: number
  }>()

  expenseList.value.forEach((item) => {
    const amount = toAmount(item.amount)
    const row = rows.get(item.project) || {
      projectName: item.project_name || `项目 ${item.project}`,
      total: 0,
      count: 0,
      people: new Map<string, number>(),
      purposes: new Map<string, number>(),
      completed: 0,
      pending: 0,
      uncommitted: 0,
    }
    const person = item.spender_name || '未登记经手人'
    const purpose = item.purpose?.trim() || item.title || '未填写用途'
    const status = item.reimbursement_status || 'draft'

    row.total += amount
    row.count += 1
    row.people.set(person, (row.people.get(person) || 0) + amount)
    row.purposes.set(purpose, (row.purposes.get(purpose) || 0) + amount)
    if (['paid', 'not_required'].includes(status)) row.completed += amount
    else if (['pending', 'approved'].includes(status)) row.pending += amount
    else row.uncommitted += amount
    rows.set(item.project, row)
  })

  return Array.from(rows.entries())
    .map(([projectId, row]) => ({
      projectId,
      projectName: row.projectName,
      total: row.total,
      count: row.count,
      people: topSpendingGroups(row.people),
      purposes: topSpendingGroups(row.purposes),
      completed: row.completed,
      pending: row.pending,
      uncommitted: row.uncommitted,
    }))
    .sort((left, right) => right.total - left.total)
})

const projectFinance = computed<ProjectFinanceRow[]>(() => {
  const rows = new Map<number, Omit<ProjectFinanceRow, 'rate' | 'tone'>>()

  budgetList.value.forEach((item) => {
    const current = rows.get(item.project) || {
      projectId: item.project,
      projectName: item.project_name || `项目 ${item.project}`,
      budget: 0,
      expense: 0,
      recorded: 0,
      available: 0,
    }
    current.budget += toAmount(item.budget_basis)
    current.expense += toAmount(item.committed_amount)
    current.available += toAmount(item.available_amount)
    rows.set(item.project, current)
  })

  expenseList.value.forEach((item) => {
    const current = rows.get(item.project) || {
      projectId: item.project,
      projectName: item.project_name || `项目 ${item.project}`,
      budget: 0,
      expense: 0,
      recorded: 0,
      available: 0,
    }
    current.recorded += toAmount(item.amount)
    rows.set(item.project, current)
  })

  return Array.from(rows.values())
    .map((item) => {
      const rate = item.budget > 0 ? Math.round((item.recorded / item.budget) * 100) : item.recorded > 0 ? 100 : 0
      const tone: BudgetTone = rate > 100 ? 'danger' : rate >= 80 ? 'warning' : rate > 0 ? 'success' : 'neutral'
      return { ...item, rate, tone }
    })
    .sort((left, right) => right.rate - left.rate)
})

const riskProjects = computed(() => projectFinance.value.filter((item) => item.rate >= 80))

function progressColor(tone: BudgetTone): string {
  if (tone === 'danger') return '#B64242'
  if (tone === 'warning') return '#A66116'
  if (tone === 'success') return '#237A55'
  return '#98A29E'
}

async function loadData(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const params = filterProject.value ? { project: filterProject.value } : {}

    const [expenses, budgets, incomes] = await Promise.all([
      getAllFinanceExpenses(params),
      getAllFinanceBudgets(params),
      getAllFinanceIncomes(params),
    ])
    expenseList.value = expenses
    budgetList.value = budgets
    incomeList.value = incomes
    await nextTick()
    renderChart()
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function isFinanceManager(): boolean {
  return ['teacher', 'sys_admin'].includes(userStore.userInfo?.global_role || '')
    || Boolean(userStore.userInfo?.permission_codes?.includes('finance.manage'))
}

function projectLeaderId(projectId: number): number | undefined {
  return projectOptions.value.find((item) => item.id === projectId)?.leader
}

function canManageProjectFinance(projectId: number): boolean {
  return isFinanceManager()
    || Boolean(projectOptions.value.find((item) => item.id === projectId)?.can_manage)
}

function canCreateProjectFinance(projectId: number): boolean {
  return ['teacher', 'sys_admin'].includes(userStore.userInfo?.global_role || '')
    || Boolean(userStore.userInfo?.permission_codes?.includes('finance.create'))
    || Boolean(projectOptions.value.find((item) => item.id === projectId)?.can_manage)
}

const canRegisterIncome = computed(() =>
  projectOptions.value.some((item) => canCreateProjectFinance(item.id)),
)
const canSetBudget = computed(() =>
  projectOptions.value.some((item) => canConfigureProjectBudget(item.id)),
)

function canConfigureProjectBudget(projectId: number): boolean {
  const existing = budgetList.value.some((item) => item.project === projectId)
  return existing
    ? canManageProjectFinance(projectId)
    : canCreateProjectFinance(projectId)
}

function canSubmitExpense(expense: FinanceExpense): boolean {
  if (!['draft', 'rejected'].includes(expense.reimbursement_status || 'draft')) return false
  const userId = userStore.userInfo?.id
  return Boolean(
    isFinanceManager()
    || expense.spender === userId
    || projectLeaderId(expense.project) === userId,
  )
}

function canReviewExpense(expense: FinanceExpense): boolean {
  if (expense.reimbursement_status !== 'pending') return false
  return canManageProjectFinance(expense.project)
}

function canPayExpense(expense: FinanceExpense): boolean {
  return expense.reimbursement_status === 'approved' && isFinanceManager()
}

function openBudgetDialog(): void {
  budgetForm.project = filterProject.value
    && canConfigureProjectBudget(filterProject.value)
    ? filterProject.value
    : projectOptions.value.find((item) => canConfigureProjectBudget(item.id))?.id
  syncBudgetForm()
  budgetDialogVisible.value = true
}

function syncBudgetForm(): void {
  const existing = budgetList.value.find((item) => item.project === budgetForm.project)
  budgetForm.planned_amount = existing
    ? toAmount(existing.planned_amount)
    : undefined
}

async function saveBudget(): Promise<void> {
  if (!budgetForm.project || budgetForm.planned_amount === undefined) {
    ElMessage.warning('请选择项目并填写核定预算上限')
    return
  }
  budgetSaving.value = true
  try {
    const existing = budgetList.value.find((item) => item.project === budgetForm.project)
    if (existing) {
      await updateFinanceBudget(existing.id, {
        planned_amount: budgetForm.planned_amount,
      })
    } else {
      await createFinanceBudget({
        project: budgetForm.project,
        planned_amount: budgetForm.planned_amount,
      })
    }
    budgetDialogVisible.value = false
    ElMessage.success('项目核定预算已保存')
    await loadData()
  } finally {
    budgetSaving.value = false
  }
}

function openExpenseDialog(): void {
  Object.assign(expenseForm, {
    project: filterProject.value,
    amount: undefined,
    expense_date: new Date().toISOString().slice(0, 10),
    category: 'other',
    title: '',
    purpose: '',
  })
  manualReceiptFile.value = null
  expenseDialogVisible.value = true
}

function handleManualReceiptChange(file: UploadFile): void {
  manualReceiptFile.value = file.raw || null
}

function handleManualReceiptRemove(): void {
  manualReceiptFile.value = null
}

async function saveExpense(): Promise<void> {
  if (
    !expenseForm.project
    || !expenseForm.amount
    || !expenseForm.expense_date
    || !expenseForm.title.trim()
  ) {
    ElMessage.warning('请补全项目、金额、日期和支出标题')
    return
  }
  expenseSaving.value = true
  try {
    const expense = await createFinanceExpense({
      project: expenseForm.project,
      amount: expenseForm.amount,
      expense_date: expenseForm.expense_date,
      category: expenseForm.category,
      title: expenseForm.title.trim(),
      purpose: expenseForm.purpose.trim(),
    })
    if (manualReceiptFile.value) {
      try {
        await uploadReceipt(expense.id, manualReceiptFile.value)
      } catch {
        ElMessage.warning('支出草稿已保存，但票据上传失败，可稍后重新上传')
      }
    }
    expenseDialogVisible.value = false
    ElMessage.success('支出已保存为草稿，请核对后提交报销')
    await loadData()
  } finally {
    expenseSaving.value = false
  }
}

function openIncomeDialog(income?: FinanceIncome): void {
  editingIncome.value = income || null
  incomeForm.project = income?.project || filterProject.value
  incomeForm.title = income?.title || ''
  incomeForm.amount = income ? toAmount(income.amount) : undefined
  incomeForm.income_type = income?.income_type || 'grant'
  incomeForm.income_date = income?.income_date || new Date().toISOString().slice(0, 10)
  incomeForm.source = income?.source || ''
  incomeForm.reference_number = income?.reference_number || ''
  incomeForm.note = income?.note || ''
  incomeDialogVisible.value = true
}

async function saveIncome(): Promise<void> {
  if (!incomeForm.project || !incomeForm.title.trim() || !incomeForm.amount || !incomeForm.income_date) {
    ElMessage.warning('请补全项目、标题、金额和入账日期')
    return
  }
  incomeSaving.value = true
  const payload = {
    project: incomeForm.project,
    title: incomeForm.title.trim(),
    amount: incomeForm.amount,
    income_type: incomeForm.income_type,
    income_date: incomeForm.income_date,
    source: incomeForm.source.trim(),
    reference_number: incomeForm.reference_number.trim(),
    note: incomeForm.note.trim(),
  }
  try {
    if (editingIncome.value) {
      await updateFinanceIncome(editingIncome.value.id, payload)
      ElMessage.success('收入流水已更新')
    } else {
      await createFinanceIncome(payload)
      ElMessage.success('收入流水已登记，预算已自动汇总')
    }
    incomeDialogVisible.value = false
    await loadData()
  } finally {
    incomeSaving.value = false
  }
}

async function handleDeleteIncome(income: FinanceIncome): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除收入“${income.title}”后预算将自动重算，是否继续？`,
      '删除收入流水',
      { type: 'warning' },
    )
    await deleteFinanceIncome(income.id)
    ElMessage.success('收入流水已删除')
    await loadData()
  } catch {
    // 用户取消或请求错误已由拦截器处理。
  }
}

async function handleSubmitReimbursement(expense: FinanceExpense): Promise<void> {
  try {
    await ElMessageBox.confirm(`提交“${expense.title}”的报销申请？`, '提交报销')
    await submitReimbursement(expense.id)
    ElMessage.success('报销已提交审核')
    await loadData()
  } catch {
    // 用户取消或请求错误已由拦截器处理。
  }
}

function openReviewDialog(expense: FinanceExpense): void {
  workflowExpense.value = expense
  reviewForm.approved = true
  reviewForm.opinion = ''
  reviewDialogVisible.value = true
}

async function saveReview(): Promise<void> {
  if (!workflowExpense.value) return
  workflowSaving.value = true
  try {
    await reviewReimbursement(
      workflowExpense.value.id,
      reviewForm.approved,
      reviewForm.opinion.trim(),
    )
    ElMessage.success(reviewForm.approved ? '报销已审核通过' : '报销已驳回')
    reviewDialogVisible.value = false
    await loadData()
  } finally {
    workflowSaving.value = false
  }
}

function openPaymentDialog(expense: FinanceExpense): void {
  workflowExpense.value = expense
  paymentForm.payment_method = '银行转账'
  paymentForm.payment_reference = ''
  paymentDialogVisible.value = true
}

function openRequestedTodo(): void {
  const expenseId = Number(route.query.expense_id)
  const action = String(route.query.action || '')
  if (!Number.isInteger(expenseId) || expenseId <= 0) return
  const expense = expenseList.value.find((item) => item.id === expenseId)
  if (!expense) return
  financeTab.value = 'expenses'
  if (action === 'finance_review' && expense.reimbursement_status === 'pending') {
    openReviewDialog(expense)
  } else if (
    action === 'finance_payment'
    && expense.reimbursement_status === 'approved'
  ) {
    openPaymentDialog(expense)
  }
}

async function savePayment(): Promise<void> {
  if (!workflowExpense.value || !paymentForm.payment_method) return
  workflowSaving.value = true
  try {
    await markReimbursementPaid(
      workflowExpense.value.id,
      paymentForm.payment_method,
      paymentForm.payment_reference.trim(),
    )
    ElMessage.success('报销打款已登记，预算汇总已更新')
    paymentDialogVisible.value = false
    await loadData()
  } finally {
    workflowSaving.value = false
  }
}

async function loadProjects(): Promise<void> {
  try {
    const response = await getProjects({ page: 1, page_size: 100 })
    projectOptions.value = response.results
  } catch {
    // The finance page remains usable without the optional project filter.
  }
}

function openOCRDialog(): void {
  ocrVisible.value = true
  ocrResult.value = null
  receiptFile.value = null
  ocrForm.project = filterProject.value
  ocrForm.amount = undefined
  ocrForm.expense_date = ''
  ocrForm.category = 'other'
  ocrForm.title = ''
  ocrForm.purpose = ''
}

function handleReceiptSelect(uploadFile: UploadFile): void {
  receiptFile.value = uploadFile.raw || null
  ocrResult.value = null
}

function handleReceiptRemove(): void {
  receiptFile.value = null
  ocrResult.value = null
}

async function handleRecognizeReceipt(): Promise<void> {
  if (!receiptFile.value) return
  ocrLoading.value = true
  try {
    const result = await recognizeReceipt(receiptFile.value)
    ocrResult.value = result
    const recognized = result.recognized
    ocrForm.amount = recognized.amount ? Number(recognized.amount) : undefined
    ocrForm.expense_date = recognized.expense_date
    ocrForm.category = recognized.category as FinanceCategory
    ocrForm.title = recognized.title
    const details = [
      recognized.vendor ? `商户：${recognized.vendor}` : '',
      recognized.invoice_number ? `票号：${recognized.invoice_number}` : '',
    ].filter(Boolean)
    ocrForm.purpose = details.join('；')
    ElMessage.success('识别完成，请核对关键字段')
  } catch {
    // 请求拦截器展示后端的 OCR 错误。
  } finally {
    ocrLoading.value = false
  }
}

async function saveOCRExpense(): Promise<void> {
  if (!receiptFile.value || !ocrResult.value) return
  if (!ocrForm.project || !ocrForm.amount || !ocrForm.expense_date || !ocrForm.title.trim()) {
    ElMessage.warning('请补全项目、金额、日期和标题')
    return
  }
  ocrSaving.value = true
  try {
    const payload = {
      project: ocrForm.project,
      amount: ocrForm.amount,
      expense_date: ocrForm.expense_date,
      category: ocrForm.category,
      title: ocrForm.title.trim(),
      purpose: ocrForm.purpose,
    }
    let expenseId = ocrDraftExpenseId.value
    if (expenseId) {
      await updateFinanceExpense(expenseId, payload)
    } else {
      const expense = await createFinanceExpense(payload)
      expenseId = expense.id
      ocrDraftExpenseId.value = expense.id
    }

    try {
      await uploadReceipt(expenseId, receiptFile.value)
    } catch (uploadError) {
      try {
        await deleteFinanceExpense(expenseId)
        ocrDraftExpenseId.value = null
      } catch {
        ElMessage.warning(`票据上传失败，草稿支出 #${expenseId} 已保留；重试不会重复创建支出`)
      }
      throw uploadError
    }

    ocrDraftExpenseId.value = null
    ElMessage.success('支出与原票据已保存为草稿，请继续提交报销')
    ocrVisible.value = false
    await loadData()
  } catch {
    // 请求拦截器展示保存错误，弹窗保留以便修正。
  } finally {
    ocrSaving.value = false
  }
}

function renderChart(): void {
  if (!chartRef.value || !categoryBreakdown.value.length) {
    chart?.dispose()
    chart = null
    return
  }

  chart ||= echarts.init(chartRef.value)
  const palette = readEChartsThemePalette()
  chart.setOption(
    {
      animationDuration: 250,
      grid: { top: 8, right: 74, bottom: 8, left: 72, containLabel: false },
      tooltip: {
        ...createEChartsTooltipStyle(palette),
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: palette.surfaceStrong } },
        formatter: (items: any[]) => {
          const item = items[0]
          return `${item.name}<br/>${formatMoneyWithComma(item.value)}`
        },
      },
      xAxis: {
        type: 'value',
        axisLabel: { show: false },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: palette.borderLight } },
      },
      yAxis: {
        type: 'category',
        inverse: true,
        data: categoryBreakdown.value.map((item) => item.name),
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { color: palette.textRegular, fontSize: 12 },
      },
      series: [
        {
          type: 'bar',
          data: categoryBreakdown.value.map((item) => item.value),
          barWidth: 12,
          itemStyle: { color: palette.primary, borderRadius: [0, 4, 4, 0] },
          label: {
            show: true,
            position: 'right',
            color: palette.textRegular,
            fontSize: 11,
            formatter: ({ value }: { value: number }) => formatMoneyWithComma(value),
          },
        },
      ],
    },
    true,
  )

  resizeObserver?.disconnect()
  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(chartRef.value)
}

useEChartsTheme(renderChart)

async function handleExport(format: string | number | object): Promise<void> {
  const exportFormat = String(format)
  if (exportFormat !== 'xlsx' && exportFormat !== 'pdf') return

  const target = resolveFinanceExportTarget(
    exportFormat as FinanceExportFormat,
    filterProject.value,
  )
  try {
    const blob = await exportData(
      target.type,
      exportFormat,
      target.projectId,
    )
    downloadBlob(blob, `${target.type}_${Date.now()}.${exportFormat}`)
    ElMessage.success('导出成功')
  } catch {
    // The request interceptor presents the backend error.
  }
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadData()])
  openRequestedTodo()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>

<style lang="scss" scoped>
.finance-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.finance-page :deep(.page-header) {
  margin-bottom: 0;
}

.status-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  color: var(--danger-text);
  background: var(--danger-light);
  border: 1px solid var(--danger-border);
  border-radius: var(--radius-sm);
}

.status-banner span {
  flex: 1;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  min-height: 112px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.metric-item {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding: 16px 18px;
}

.metric-item + .metric-item {
  border-left: 1px solid var(--color-border-light);
}

.metric-item > span {
  color: var(--color-text-muted);
  font-size: 12px;
}

.metric-item strong {
  max-width: 100%;
  margin-top: 7px;
  overflow: hidden;
  color: var(--color-text);
  font-size: 22px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-item small {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.metric-item--warning strong { color: var(--color-warning); }
.metric-item--danger strong { color: var(--color-danger); }

.metric-item--spending {
  background: var(--color-primary-soft);
}

.metric-item--spending strong {
  color: var(--color-primary);
}

.finance-overview-grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.8fr) minmax(440px, 1.2fr);
  gap: 16px;
}

.workspace-panel {
  min-width: 0;
  padding: 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.destination-table :deep(.el-table__cell) {
  vertical-align: top;
}

.destination-amount {
  display: block;
  color: var(--color-primary);
  font-size: 14px;
}

.destination-table small {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.destination-lines,
.destination-status {
  display: grid;
  gap: 3px;
  color: var(--color-text-regular);
  font-size: 12px;
  line-height: 1.45;
}

.destination-lines span,
.destination-status span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.destination-status span:first-child {
  color: var(--color-success);
}

.panel-header,
.details-toolbar,
.project-budget-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.panel-header,
.details-toolbar {
  margin-bottom: 16px;
}

.panel-header h2,
.details-toolbar h2 {
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
}

.panel-header p,
.details-toolbar p {
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.chart-container {
  width: 100%;
  height: 270px;
}

.project-budget-list {
  border-top: 1px solid var(--color-border-light);
}

.project-budget-row {
  padding: 13px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.project-budget-row:last-child {
  border-bottom: 0;
}

.project-budget-head {
  margin-bottom: 8px;
}

.project-budget-head h3 {
  max-width: 34ch;
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-budget-head span:not(.utilization) {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.utilization {
  flex: 0 0 auto;
  color: var(--color-success);
  font-size: 13px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.utilization[data-tone='warning'] { color: var(--color-warning); }
.utilization[data-tone='danger'] { color: var(--color-danger); }
.utilization[data-tone='neutral'] { color: var(--color-text-muted); }

.project-filter {
  width: 220px;
}

.ocr-workspace {
  display: grid;
  gap: 16px;

  :deep(.el-upload),
  :deep(.el-upload-dragger),
  :deep(.el-select),
  :deep(.el-date-editor),
  :deep(.el-input-number) {
    width: 100%;
  }
}

.ocr-action-row,
.ocr-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ocr-action-row {
  padding: 10px 12px;
  background: var(--color-surface-subtle);
  border-radius: var(--radius-md);
  color: var(--color-text-regular);
  font-size: 13px;
}

.ocr-result-head {
  padding-top: 4px;

  div {
    display: grid;
    gap: 2px;
  }

  strong {
    color: var(--color-text);
    font-size: 15px;
  }

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.ocr-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.ocr-raw-text pre {
  max-height: 180px;
  margin: 0;
  overflow: auto;
  color: var(--color-text-regular);
  font: 12px/1.6 ui-monospace, SFMono-Regular, Consolas, monospace;
  white-space: pre-wrap;
}

@media screen and (max-width: 1100px) {
  .finance-overview-grid {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 768px) {
  .metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-item {
    min-height: 98px;
    padding: 13px;
  }

  .metric-item + .metric-item {
    border-left: 0;
  }

  .metric-item:nth-child(even) {
    border-left: 1px solid var(--color-border-light);
  }

  .metric-item:nth-child(n + 3) {
    border-top: 1px solid var(--color-border-light);
  }

  .metric-item strong {
    font-size: 17px;
  }

  .workspace-panel {
    padding: 14px;
  }

  .chart-container {
    height: 230px;
  }

  .details-toolbar {
    align-items: flex-end;
  }

  .project-filter {
    width: min(48%, 190px);
  }

  .ocr-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
