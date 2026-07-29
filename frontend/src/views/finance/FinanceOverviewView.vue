<template>
  <div class="page-container finance-ledger-page">
    <PageHeader
      title="经费管理"
      subtitle="按项目、比赛届次与参赛队追溯奖金、成员垫付、审核预留和真实付款"
    >
      <template #actions>
        <el-button :icon="CameraFilled" @click="openOCRDialog">票据识别</el-button>
        <el-button v-if="canRegisterIncome" :icon="Plus" @click="openIncomeDialog">登记收入</el-button>
        <el-button type="primary" :icon="Plus" @click="openExpenseDialog">登记成员垫付</el-button>
        <el-dropdown @command="handleExport">
          <el-button :icon="Download">
            导出<el-icon class="el-icon--right"><ArrowDown /></el-icon>
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
      <span>部分经费数据未能加载，请重试。</span>
      <el-button link type="primary" @click="loadData">重新加载</el-button>
    </div>

    <el-tabs v-model="workspaceTab" class="workspace-tabs">
      <el-tab-pane label="资金追溯台账" name="ledger">
        <section v-loading="loading" class="metric-strip" aria-label="资金状态">
          <article>
            <span>实际到账资金</span>
            <strong class="positive">{{ money(metrics.received_funds) }}</strong>
            <small>仅“已到账”收入进入可用资金</small>
          </article>
          <article>
            <span>待审核预留</span>
            <strong>{{ money(metrics.pending_review_reserved) }}</strong>
            <small>提交后暂时占用额度</small>
          </article>
          <article>
            <span>已审核待转账</span>
            <strong>{{ money(metrics.approved_pending_payment) }}</strong>
            <small>含部分支付的剩余金额</small>
          </article>
          <article>
            <span>团队实际支付</span>
            <strong>{{ money(metrics.actual_paid) }}</strong>
            <small>付款凭证归档后才计入</small>
          </article>
          <article>
            <span>奖金待到账</span>
            <strong>{{ money(metrics.expected_bonus + metrics.confirmed_bonus) }}</strong>
            <small>预计 {{ money(metrics.expected_bonus) }} · 已确认 {{ money(metrics.confirmed_bonus) }}</small>
          </article>
          <article :class="{ danger: metrics.available_funds < 0 }">
            <span>当前可动用资金</span>
            <strong>{{ money(metrics.available_funds) }}</strong>
            <small>到账－预留－待转账－已支付</small>
          </article>
        </section>

        <section class="workspace-panel todo-panel">
          <header class="panel-heading">
            <div>
              <h2>资金待办</h2>
              <p>先处理缺票据、待审核、待付款和异常记录；点击卡片可筛选流水。</p>
            </div>
            <el-button :icon="Refresh" circle aria-label="刷新" @click="loadData" />
          </header>
          <div class="todo-grid">
            <button
              v-for="item in todoCards"
              :key="item.key"
              type="button"
              class="todo-card"
              :class="[{ active: todoFilter === item.key }, `todo-card--${item.tone}`]"
              @click="selectTodo(item.key)"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.hint }}</small>
            </button>
          </div>
        </section>

        <section class="workspace-panel traceability-panel">
          <header class="traceability-toolbar">
            <div>
              <h2>项目—比赛—参赛队资金追溯</h2>
              <p>同一批流水按两个方向分组，不重复登记、不重复计算。</p>
            </div>
            <el-segmented
              v-model="perspective"
              :options="perspectiveOptions"
              aria-label="切换资金追溯视角"
            />
          </header>

          <div class="filter-row">
            <el-select v-model="filterProject" clearable filterable placeholder="全部项目" aria-label="按项目筛选">
              <el-option v-for="project in projectOptions" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
            <el-select v-model="filterEvent" clearable filterable placeholder="全部比赛届次" aria-label="按比赛届次筛选">
              <el-option v-for="event in eventOptions" :key="event.id" :label="eventLabel(event)" :value="event.id" />
            </el-select>
            <el-input v-model="ledgerKeyword" clearable placeholder="搜索项目、比赛、参赛队或流水标题" aria-label="搜索资金台账" />
            <el-button v-if="filterProject || filterEvent || ledgerKeyword" @click="resetFilters">清空筛选</el-button>
          </div>

          <FinanceTraceabilityTable
            v-loading="loading"
            :perspective="perspective"
            :groups="visibleGroups"
            @open="openTraceabilityRow"
          />
        </section>

        <section ref="flowSection" class="workspace-panel flow-panel">
          <header class="panel-heading">
            <div>
              <h2>资金流水与处理</h2>
              <p>成员垫付、付款和内部转付分开记录；内部转付不重复计为收入或支出。</p>
            </div>
            <el-tag v-if="todoFilter" closable type="warning" @close="todoFilter = ''">
              待办筛选：{{ todoFilterLabel }}
            </el-tag>
          </header>

          <el-tabs v-model="flowTab">
            <el-tab-pane :label="`支出与报销（${visibleExpenses.length}）`" name="expenses">
              <el-table :data="visibleExpenses" row-key="id" size="small">
                <template #empty><EmptyState text="暂无支出记录" compact /></template>
                <el-table-column prop="expense_date" label="日期" width="108" />
                <el-table-column label="项目 / 比赛 / 参赛队" min-width="220">
                  <template #default="{ row }">
                    <div class="stacked-cell"><strong>{{ row.project_name }}</strong><span>{{ expenseScopeLabel(row) }}</span></div>
                  </template>
                </el-table-column>
                <el-table-column label="用途" min-width="190">
                  <template #default="{ row }"><div class="stacked-cell"><strong>{{ row.title }}</strong><span>{{ row.purpose || row.category_display || getFinanceCategoryLabel(row.category) }}</span></div></template>
                </el-table-column>
                <el-table-column label="垫付 / 收款人" min-width="145">
                  <template #default="{ row }">{{ row.spender_name || '-' }} / {{ row.payee_name || row.spender_name || '-' }}</template>
                </el-table-column>
                <el-table-column label="金额" width="116" align="right"><template #default="{ row }"><strong>{{ money(row.amount) }}</strong></template></el-table-column>
                <el-table-column label="已付 / 待付" width="152" align="right"><template #default="{ row }">{{ money(expensePaid(row)) }} / {{ money(expensePayable(row)) }}</template></el-table-column>
                <el-table-column label="状态" width="154"><template #default="{ row }"><el-tag size="small" :type="expenseStatusTone(row.reimbursement_status)">{{ expenseStatusLabel(row.reimbursement_status) }}</el-tag></template></el-table-column>
                <el-table-column label="操作" width="196" fixed="right">
                  <template #default="{ row }">
                    <el-button v-if="canSubmitExpense(row)" link type="primary" @click="submitExpense(row)">提交</el-button>
                    <el-button v-if="canReviewExpense(row)" link type="warning" @click="openReviewDialog(row)">审核</el-button>
                    <el-button v-if="canPayExpense(row) && expensePayable(row) > 0" link type="primary" @click="openPaymentDialog(row)">付款</el-button>
                    <el-button link @click="openExpenseTrace(row)">追溯</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`奖金与收入（${visibleIncomes.length}）`" name="incomes">
              <el-table :data="visibleIncomes" row-key="id" size="small">
                <template #empty><EmptyState text="暂无收入记录" compact /></template>
                <el-table-column label="记录日期" width="112"><template #default="{ row }">{{ row.received_at?.slice(0, 10) || row.confirmed_at?.slice(0, 10) || row.income_date || '-' }}</template></el-table-column>
                <el-table-column label="项目 / 比赛 / 参赛队" min-width="220"><template #default="{ row }"><div class="stacked-cell"><strong>{{ row.project_name }}</strong><span>{{ incomeScopeLabel(row) }}</span></div></template></el-table-column>
                <el-table-column label="收入" min-width="190"><template #default="{ row }"><div class="stacked-cell"><strong>{{ row.title }}</strong><span>{{ row.source || row.income_type_display || incomeTypeLabel(row.income_type) }}</span></div></template></el-table-column>
                <el-table-column label="阶段" width="126"><template #default="{ row }"><el-tag size="small" :type="row.stage === 'received' ? 'success' : row.stage === 'confirmed' ? 'warning' : 'info'">{{ incomeStageLabel(row.stage) }}</el-tag></template></el-table-column>
                <el-table-column label="金额" width="130" align="right"><template #default="{ row }"><strong>{{ money(row.amount) }}</strong></template></el-table-column>
                <el-table-column label="操作" width="160" fixed="right"><template #default="{ row }"><el-button v-if="canAdvanceIncome(row)" link type="primary" @click="openIncomeStageDialog(row)">推进阶段</el-button><el-button link @click="openIncomeTrace(row)">追溯</el-button></template></el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`付款记录（${visiblePayments.length}）`" name="payments">
              <el-table :data="visiblePayments" row-key="id" size="small">
                <template #empty><EmptyState text="暂无付款记录" compact /></template>
                <el-table-column label="支出" min-width="230"><template #default="{ row }"><div class="stacked-cell"><strong>{{ row.expense_title || expenseById(row.expense)?.title || `支出 #${row.expense}` }}</strong><span>{{ row.project_name || expenseById(row.expense)?.project_name }}</span></div></template></el-table-column>
                <el-table-column prop="recipient_name" label="收款人" min-width="110" />
                <el-table-column label="金额" width="126" align="right"><template #default="{ row }"><strong>{{ money(row.amount) }}</strong></template></el-table-column>
                <el-table-column label="付款信息" min-width="180"><template #default="{ row }"><div class="stacked-cell"><strong>{{ row.payment_method || '-' }}</strong><span>{{ row.payment_reference || '未填流水号' }}</span></div></template></el-table-column>
                <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag size="small" :type="paymentStatusTone(row.status)">{{ row.status_display || paymentStatusLabel(row.status) }}</el-tag></template></el-table-column>
                <el-table-column label="操作" width="170" fixed="right"><template #default="{ row }"><el-button v-if="row.status === 'pending_proof' && canOperatePayment(row)" link type="primary" @click="openCompletePaymentDialog(row)">补凭证完成</el-button><el-button v-if="row.status === 'pending_proof' && canOperatePayment(row)" link type="danger" @click="markPaymentFailed(row)">标记异常</el-button></template></el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`内部转付（${visibleTransfers.length}）`" name="transfers">
              <div class="tab-actions"><el-button v-if="canRegisterTransfer" type="primary" plain :icon="Plus" @click="openTransferDialog">登记内部转付</el-button></div>
              <el-table :data="visibleTransfers" row-key="id" size="small">
                <template #empty><EmptyState text="暂无内部转付记录" description="学校或经办人之间的转付只记录资金去向，不重复计算收支。" compact /></template>
                <el-table-column label="项目 / 参赛队" min-width="190"><template #default="{ row }"><div class="stacked-cell"><strong>{{ row.project_name }}</strong><span>{{ row.competition_entry_name || '项目公共' }}</span></div></template></el-table-column>
                <el-table-column label="转出来源" min-width="135"><template #default="{ row }">{{ row.from_user_name || row.source_label || '外部来源' }}</template></el-table-column>
                <el-table-column prop="to_user_name" label="接收人" min-width="110" />
                <el-table-column label="金额" width="126" align="right"><template #default="{ row }"><strong>{{ money(row.amount) }}</strong></template></el-table-column>
                <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag size="small" :type="transferStatusTone(row.status)">{{ row.status_display || transferStatusLabel(row.status) }}</el-tag></template></el-table-column>
                <el-table-column label="转账信息" min-width="180"><template #default="{ row }">{{ row.payment_method || '-' }} · {{ row.payment_reference || '无流水号' }}</template></el-table-column>
                <el-table-column label="操作" width="170" fixed="right"><template #default="{ row }"><el-button v-if="row.status === 'pending_proof' && canOperateTransfer(row)" link type="primary" @click="openCompleteTransferDialog(row)">补凭证完成</el-button><el-button v-if="row.status === 'pending_proof' && canOperateTransfer(row)" link type="danger" @click="markTransferFailed(row)">标记异常</el-button></template></el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </section>
      </el-tab-pane>

      <el-tab-pane label="数据分析" name="analysis">
        <div class="analysis-grid">
          <section class="workspace-panel analysis-card">
            <header class="panel-heading"><div><h2>支出结构</h2><p>作为辅助分析，不占用经费首页第一屏。</p></div></header>
            <div v-if="categoryBreakdown.length" class="breakdown-list">
              <article v-for="item in categoryBreakdown" :key="item.key">
                <div><span>{{ item.label }}</span><strong>{{ money(item.amount) }}</strong></div>
                <el-progress :percentage="item.percentage" :show-text="false" :stroke-width="7" />
              </article>
            </div>
            <EmptyState v-else text="暂无支出数据" compact />
          </section>

          <section class="workspace-panel analysis-card">
            <header class="panel-heading">
              <div><h2>项目支出与预算</h2><p>核定上限与计算余额仅作风险参考。</p></div>
              <el-button v-if="canSetBudget" link type="primary" @click="openBudgetDialog">设置预算</el-button>
            </header>
            <div v-if="projectAnalysis.length" class="project-analysis-list">
              <article v-for="item in projectAnalysis" :key="item.id">
                <div class="analysis-row-head"><strong>{{ item.name }}</strong><span>已发生 {{ money(item.spent) }} / 上限 {{ money(item.budget) }}</span></div>
                <el-progress :percentage="Math.min(item.rate, 100)" :status="item.rate > 100 ? 'exception' : item.rate >= 80 ? 'warning' : undefined" :stroke-width="7" />
              </article>
            </div>
            <EmptyState v-else text="暂无项目预算数据" compact />
          </section>
        </div>
      </el-tab-pane>
    </el-tabs>

    <FinanceRecordDrawer
      v-model="drawerVisible"
      :row="drawerRow"
      @review="openReviewDialog"
      @pay="openPaymentDialog"
      @advance-income="openIncomeStageDialog"
    />

    <el-dialog v-model="expenseDialogVisible" title="登记成员垫付 / 项目支出" width="min(760px, 94vw)" destroy-on-close>
      <el-alert title="成员垫付不等于团队已支出；只有实际转账并归档付款凭证后才计入团队实际支付。" type="info" :closable="false" show-icon />
      <el-form label-position="top" class="dialog-form">
        <div class="form-grid form-grid--3">
          <el-form-item :label="expenseForm.scope === 'allocated' ? '发起 / 归账项目' : '项目'" required><el-select v-model="expenseForm.project" filterable @change="resetExpenseScope"><el-option v-for="item in projectOptions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="资金归属" required><el-select v-model="expenseForm.scope" @change="resetExpenseScopeTarget"><el-option label="单个比赛参赛队" value="competition_entry" /><el-option label="项目公共支出" value="project_common" /><el-option v-if="expenseForm.project && canManageProjectById(expenseForm.project)" label="一笔流水、跨队分摊" value="allocated" /></el-select></el-form-item>
          <el-form-item v-if="expenseForm.scope === 'competition_entry'" label="比赛 / 参赛队" required><el-select v-model="expenseForm.competition_entry" filterable><el-option v-for="item in expenseEntryOptions" :key="item.id" :label="competitionLabel(item)" :value="item.id" /></el-select></el-form-item>
        </div>
        <div v-if="expenseForm.scope === 'allocated'" class="allocation-editor">
          <el-alert :title="expenseForm.allocation_mode === 'same_event' ? '一笔流水、跨队分摊：只登记一次总支出，再分到同一比赛届次下的不同项目参赛队。' : '兼容单项目分摊：流水仍归属当前项目，可分到该项目参加的多个比赛。'" type="info" :closable="false" show-icon />
          <div class="allocation-mode">
            <span>分摊范围</span>
            <el-radio-group v-model="expenseForm.allocation_mode" @change="resetExpenseAllocationMode">
              <el-radio-button value="same_event">同届次跨项目 / 跨队</el-radio-button>
              <el-radio-button value="same_project">仅当前项目（兼容旧版）</el-radio-button>
            </el-radio-group>
          </div>
          <header><div><strong>分摊明细</strong><span>{{ expenseForm.allocation_mode === 'same_event' ? '先选锚点比赛届次，也可直接选择首个参赛队自动锁定同届' : '只显示当前归账项目的参赛条目，可跨比赛选择' }}；合计必须等于支出金额</span></div><el-button link type="primary" @click="addExpenseAllocation">添加分摊</el-button></header>
          <div v-if="expenseForm.allocation_mode === 'same_event'" class="allocation-anchor">
            <span>锚点比赛届次</span>
            <el-select v-model="expenseForm.allocation_event" clearable filterable placeholder="选择届次，或由首个分摊自动锁定" @change="handleExpenseAllocationEventChange">
              <el-option v-for="event in allocationEventOptions" :key="event.id" :label="eventLabel(event)" :value="event.id" />
            </el-select>
          </div>
          <small v-if="expenseForm.allocation_mode === 'same_event' && expenseForm.allocation_event" class="allocation-scope-summary">已锁定 {{ allocationEventLabel(expenseForm.allocation_event) }}，可选 {{ expenseAllocationProjectCount }} 个项目的 {{ expenseAllocationEntryOptions.length }} 个参赛队。</small>
          <small v-else-if="expenseForm.allocation_mode === 'same_project'" class="allocation-scope-summary">当前仅可选择 {{ projectName(expenseForm.project) }} 的 {{ expenseAllocationEntryOptions.length }} 个参赛条目。</small>
          <div v-for="(allocation, index) in expenseForm.allocations" :key="index" class="allocation-row">
            <el-select v-model="allocation.competition_entry" filterable placeholder="项目 / 参赛队" @change="handleExpenseAllocationEntryChange"><el-option v-for="item in expenseAllocationEntryOptions" :key="item.id" :label="allocationCompetitionLabel(item)" :value="item.id" :disabled="isExpenseAllocationEntrySelected(item.id, index)" /></el-select>
            <el-input-number v-model="allocation.amount" :min="0" :precision="2" :controls="false" placeholder="金额" />
            <el-input v-model="allocation.note" placeholder="分摊说明（可选）" />
            <el-button link type="danger" @click="expenseForm.allocations.splice(index, 1)">移除</el-button>
          </div>
          <small :class="{ danger: !expenseAllocationBalanced }">分摊合计 {{ money(expenseAllocationTotal) }} / 支出 {{ money(expenseForm.amount || 0) }}</small>
        </div>
        <div class="form-grid form-grid--3">
          <el-form-item label="垫付人 / 经办人" required><el-select v-model="expenseForm.spender" filterable :disabled="!expenseForm.project || !canManageProjectById(expenseForm.project)"><el-option v-for="member in memberOptions" :key="memberUserId(member)" :label="memberName(member)" :value="memberUserId(member)" /></el-select></el-form-item>
          <el-form-item label="实际收款人" required><el-select v-model="expenseForm.payee" filterable :disabled="!expenseForm.project || !canManageProjectById(expenseForm.project)"><el-option v-for="member in memberOptions" :key="memberUserId(member)" :label="memberName(member)" :value="memberUserId(member)" /></el-select></el-form-item>
          <el-form-item label="支出类别" required><el-select v-model="expenseForm.category"><el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        </div>
        <div class="form-grid form-grid--3">
          <el-form-item label="金额" required><el-input-number v-model="expenseForm.amount" :min="0.01" :precision="2" :controls="false" /></el-form-item>
          <el-form-item label="支出日期" required><el-date-picker v-model="expenseForm.expense_date" type="date" value-format="YYYY-MM-DD" /></el-form-item>
          <el-form-item label="票据类型"><el-select v-model="expenseForm.attachment_type"><el-option label="发票" value="invoice" /><el-option label="原始票据 / 车票" value="original_receipt" /><el-option label="其他附件" value="other" /></el-select></el-form-item>
        </div>
        <el-form-item label="支出标题" required><el-input v-model="expenseForm.title" maxlength="100" show-word-limit placeholder="例如：省赛现场往返打车费" /></el-form-item>
        <el-form-item label="用途说明"><el-input v-model="expenseForm.purpose" type="textarea" :rows="2" placeholder="说明行程、用途或费用覆盖范围" /></el-form-item>
        <el-form-item label="发票 / 原始票据"><el-upload :auto-upload="false" :limit="1" :on-change="handleExpenseFile" :on-remove="clearExpenseFile"><el-button>选择文件</el-button><template #tip><span class="upload-tip">提交审核前必须上传发票或原始票据；保存草稿可稍后补充。</span></template></el-upload></el-form-item>
      </el-form>
      <template #footer><el-button @click="expenseDialogVisible = false">取消</el-button><el-button :loading="expenseSaving" @click="saveExpense(false)">保存草稿</el-button><el-button type="primary" :loading="expenseSaving" @click="saveExpense(true)">保存并提交审核</el-button></template>
    </el-dialog>

    <el-dialog v-model="incomeDialogVisible" title="登记奖金 / 收入" width="min(720px, 94vw)" destroy-on-close>
      <el-alert title="预计奖金不计入可用资金；获奖后转为已确认应收，凭到账记录转为已到账。" type="info" :closable="false" show-icon />
      <el-form label-position="top" class="dialog-form">
        <div class="form-grid form-grid--3">
          <el-form-item :label="incomeForm.scope === 'allocated' ? '发起 / 归账项目' : '项目'" required><el-select v-model="incomeForm.project" filterable @change="resetIncomeScope"><el-option v-for="item in manageableProjects" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="资金归属" required><el-select v-model="incomeForm.scope" @change="resetIncomeScopeTarget"><el-option label="单个比赛参赛队" value="competition_entry" /><el-option label="项目公共收入" value="project_common" /><el-option label="一笔流水、跨队分摊" value="allocated" /></el-select></el-form-item>
          <el-form-item v-if="incomeForm.scope === 'competition_entry'" label="比赛 / 参赛队" required><el-select v-model="incomeForm.competition_entry" filterable><el-option v-for="item in incomeEntryOptions" :key="item.id" :label="competitionLabel(item)" :value="item.id" /></el-select></el-form-item>
        </div>
        <div v-if="incomeForm.scope === 'allocated'" class="allocation-editor">
          <el-alert :title="incomeForm.allocation_mode === 'same_event' ? '一笔流水、跨队分摊：只登记一次总收入，再分到同一比赛届次下的不同项目参赛队。' : '兼容单项目分摊：流水仍归属当前项目，可分到该项目参加的多个比赛。'" type="info" :closable="false" show-icon />
          <div class="allocation-mode">
            <span>分摊范围</span>
            <el-radio-group v-model="incomeForm.allocation_mode" @change="resetIncomeAllocationMode">
              <el-radio-button value="same_event">同届次跨项目 / 跨队</el-radio-button>
              <el-radio-button value="same_project">仅当前项目（兼容旧版）</el-radio-button>
            </el-radio-group>
          </div>
          <header><div><strong>分摊明细</strong><span>{{ incomeForm.allocation_mode === 'same_event' ? '先选锚点比赛届次，也可直接选择首个参赛队自动锁定同届' : '只显示当前归账项目的参赛条目，可跨比赛选择' }}；合计必须一致</span></div><el-button link type="primary" @click="addIncomeAllocation">添加分摊</el-button></header>
          <div v-if="incomeForm.allocation_mode === 'same_event'" class="allocation-anchor">
            <span>锚点比赛届次</span>
            <el-select v-model="incomeForm.allocation_event" clearable filterable placeholder="选择届次，或由首个分摊自动锁定" @change="handleIncomeAllocationEventChange">
              <el-option v-for="event in allocationEventOptions" :key="event.id" :label="eventLabel(event)" :value="event.id" />
            </el-select>
          </div>
          <small v-if="incomeForm.allocation_mode === 'same_event' && incomeForm.allocation_event" class="allocation-scope-summary">已锁定 {{ allocationEventLabel(incomeForm.allocation_event) }}，可选 {{ incomeAllocationProjectCount }} 个项目的 {{ incomeAllocationEntryOptions.length }} 个参赛队。</small>
          <small v-else-if="incomeForm.allocation_mode === 'same_project'" class="allocation-scope-summary">当前仅可选择 {{ projectName(incomeForm.project) }} 的 {{ incomeAllocationEntryOptions.length }} 个参赛条目。</small>
          <div v-for="(allocation, index) in incomeForm.allocations" :key="index" class="allocation-row">
            <el-select v-model="allocation.competition_entry" filterable placeholder="项目 / 参赛队" @change="handleIncomeAllocationEntryChange"><el-option v-for="item in incomeAllocationEntryOptions" :key="item.id" :label="allocationCompetitionLabel(item)" :value="item.id" :disabled="isIncomeAllocationEntrySelected(item.id, index)" /></el-select>
            <el-input-number v-model="allocation.amount" :min="0" :precision="2" :controls="false" placeholder="金额" />
            <el-input v-model="allocation.note" placeholder="分摊说明（可选）" />
            <el-button link type="danger" @click="incomeForm.allocations.splice(index, 1)">移除</el-button>
          </div>
          <small :class="{ danger: !incomeAllocationBalanced }">分摊合计 {{ money(incomeAllocationTotal) }} / 收入 {{ money(incomeForm.amount || 0) }}</small>
        </div>
        <div class="form-grid form-grid--3">
          <el-form-item label="收入类型" required><el-select v-model="incomeForm.income_type"><el-option v-for="item in incomeTypeOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
          <el-form-item label="当前阶段" required><el-select v-model="incomeForm.stage"><el-option label="预计" value="expected" /><el-option label="已确认应收" value="confirmed" /><el-option label="已到账" value="received" /></el-select></el-form-item>
          <el-form-item label="业务日期" required><el-date-picker v-model="incomeForm.income_date" type="date" value-format="YYYY-MM-DD" /></el-form-item>
        </div>
        <div class="form-grid form-grid--2"><el-form-item label="金额" required><el-input-number v-model="incomeForm.amount" :min="0.01" :precision="2" :controls="false" /></el-form-item><el-form-item label="收入标题" required><el-input v-model="incomeForm.title" placeholder="例如：互联网+省赛奖金" /></el-form-item></div>
        <div class="form-grid form-grid--2"><el-form-item label="来源"><el-input v-model="incomeForm.source" placeholder="主办方 / 学校 / 赞助方" /></el-form-item><el-form-item label="凭证编号"><el-input v-model="incomeForm.reference_number" placeholder="通知编号或到账流水号" /></el-form-item></div>
        <el-form-item label="备注"><el-input v-model="incomeForm.note" type="textarea" :rows="2" /></el-form-item>
        <el-form-item v-if="incomeForm.stage === 'received'" label="到账凭证" required><el-upload :auto-upload="false" :limit="1" :on-change="handleIncomeProof" :on-remove="clearIncomeProof"><el-button>选择到账截图 / 回单</el-button></el-upload></el-form-item>
      </el-form>
      <template #footer><el-button @click="incomeDialogVisible = false">取消</el-button><el-button type="primary" :loading="incomeSaving" @click="saveIncome">保存收入记录</el-button></template>
    </el-dialog>

    <el-dialog v-model="reviewDialogVisible" title="审核报销并预留额度" width="min(520px, 94vw)">
      <el-alert v-if="workflowExpense" :title="`${workflowExpense.title} · ${money(workflowExpense.amount)}`" type="info" :closable="false" />
      <el-form label-position="top" class="dialog-form"><el-form-item label="审核结果"><el-radio-group v-model="reviewForm.approved"><el-radio-button :value="true">通过并进入待转账</el-radio-button><el-radio-button :value="false">驳回并释放预留</el-radio-button></el-radio-group></el-form-item><el-form-item label="审核意见"><el-input v-model="reviewForm.opinion" type="textarea" :rows="3" /></el-form-item></el-form>
      <template #footer><el-button @click="reviewDialogVisible = false">取消</el-button><el-button type="primary" :loading="workflowSaving" @click="saveReview">确认审核</el-button></template>
    </el-dialog>

    <el-dialog v-model="paymentDialogVisible" :title="paymentMode === 'create' ? '登记付款' : '补充凭证并完成付款'" width="min(600px, 94vw)">
      <el-alert title="只有状态为“已完成”且付款凭证归档成功的金额，才计入团队实际支付。" type="warning" :closable="false" show-icon />
      <el-form label-position="top" class="dialog-form">
        <div class="form-grid form-grid--2"><el-form-item label="收款人" required><el-select v-model="paymentForm.recipient" filterable :disabled="paymentMode === 'complete'"><el-option v-for="member in memberOptions" :key="memberUserId(member)" :label="memberName(member)" :value="memberUserId(member)" /></el-select></el-form-item><el-form-item label="付款金额" required><el-input-number v-model="paymentForm.amount" :min="0.01" :max="paymentMaxAmount" :precision="2" :controls="false" :disabled="paymentMode === 'complete'" /></el-form-item></div>
        <div class="form-grid form-grid--2"><el-form-item label="付款方式" required><el-input v-model="paymentForm.payment_method" :disabled="paymentMode === 'complete'" placeholder="银行转账 / 微信 / 支付宝" /></el-form-item><el-form-item label="流水号" required><el-input v-model="paymentForm.payment_reference" /></el-form-item></div>
        <div class="form-grid form-grid--2"><el-form-item label="付款时间"><el-date-picker v-model="paymentForm.payment_date" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" /></el-form-item><el-form-item v-if="paymentMode === 'create'" label="登记状态"><el-select v-model="paymentForm.status"><el-option label="已转账并归档凭证" value="completed" /><el-option label="已登记，待补付款凭证" value="pending_proof" /></el-select></el-form-item></div>
        <el-form-item v-if="paymentForm.status === 'completed' || paymentMode === 'complete'" label="转账截图 / 银行回单" required><el-upload :auto-upload="false" :limit="1" :on-change="handlePaymentProof" :on-remove="clearPaymentProof"><el-button>选择付款凭证</el-button></el-upload></el-form-item>
      </el-form>
      <template #footer><el-button @click="paymentDialogVisible = false">取消</el-button><el-button type="primary" :loading="workflowSaving" @click="savePayment">{{ paymentMode === 'create' && paymentForm.status === 'pending_proof' ? '登记待补凭证' : '确认付款完成' }}</el-button></template>
    </el-dialog>

    <el-dialog v-model="incomeStageDialogVisible" title="推进收入阶段" width="min(520px, 94vw)">
      <el-alert v-if="workflowIncome" :title="`${workflowIncome.title} · ${money(workflowIncome.amount)} · ${incomeStageLabel(workflowIncome.stage)}`" type="info" :closable="false" />
      <el-form label-position="top" class="dialog-form"><el-form-item label="推进到" required><el-select v-model="incomeStageForm.stage"><el-option v-if="workflowIncome?.stage === 'expected'" label="已确认应收" value="confirmed" /><el-option label="已到账" value="received" /></el-select></el-form-item><el-form-item v-if="incomeStageForm.stage === 'received'" label="到账凭证" required><el-upload :auto-upload="false" :limit="1" :on-change="handleIncomeStageProof" :on-remove="clearIncomeStageProof"><el-button>选择到账凭证</el-button></el-upload></el-form-item></el-form>
      <template #footer><el-button @click="incomeStageDialogVisible = false">取消</el-button><el-button type="primary" :loading="workflowSaving" @click="saveIncomeStage">确认推进</el-button></template>
    </el-dialog>

    <el-dialog v-model="transferDialogVisible" title="登记内部资金转付" width="min(650px, 94vw)">
      <el-alert title="学校拨款给老师或经办人、经办人再转给成员，都属于内部资金移动，不重复计入收入和支出。" type="info" :closable="false" show-icon />
      <el-form label-position="top" class="dialog-form">
        <div class="form-grid form-grid--2"><el-form-item label="项目" required><el-select v-model="transferForm.project" filterable @change="transferForm.competition_entry = undefined"><el-option v-for="item in payableProjects" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="比赛 / 参赛队"><el-select v-model="transferForm.competition_entry" clearable filterable><el-option v-for="item in transferEntryOptions" :key="item.id" :label="competitionLabel(item)" :value="item.id" /></el-select></el-form-item></div>
        <el-form-item label="转出来源类型"><el-radio-group v-model="transferForm.source_type"><el-radio-button value="member">团队经办人</el-radio-button><el-radio-button value="external">学校 / 外部来源</el-radio-button></el-radio-group></el-form-item>
        <div class="form-grid form-grid--2"><el-form-item v-if="transferForm.source_type === 'member'" label="转出人" required><el-select v-model="transferForm.from_user" filterable><el-option v-for="member in memberOptions" :key="memberUserId(member)" :label="memberName(member)" :value="memberUserId(member)" /></el-select></el-form-item><el-form-item v-else label="资金来源" required><el-input v-model="transferForm.source_label" placeholder="例如：学校创新创业中心" /></el-form-item><el-form-item label="接收人" required><el-select v-model="transferForm.to_user" filterable><el-option v-for="member in memberOptions" :key="memberUserId(member)" :label="memberName(member)" :value="memberUserId(member)" /></el-select></el-form-item></div>
        <div class="form-grid form-grid--3"><el-form-item label="金额" required><el-input-number v-model="transferForm.amount" :min="0.01" :precision="2" :controls="false" /></el-form-item><el-form-item label="状态"><el-select v-model="transferForm.status"><el-option label="已完成" value="completed" /><el-option label="待补凭证" value="pending_proof" /><el-option label="转付失败" value="failed" /></el-select></el-form-item><el-form-item label="转付时间"><el-date-picker v-model="transferForm.transfer_date" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" /></el-form-item></div>
        <div class="form-grid form-grid--2"><el-form-item label="付款方式"><el-input v-model="transferForm.payment_method" /></el-form-item><el-form-item label="流水号"><el-input v-model="transferForm.payment_reference" /></el-form-item></div>
        <el-form-item v-if="transferForm.status === 'failed'" label="失败原因" required><el-input v-model="transferForm.failure_reason" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="transferForm.note" type="textarea" :rows="2" /></el-form-item>
        <el-form-item v-if="transferForm.status === 'completed'" label="内部转账凭证" required><el-upload :auto-upload="false" :limit="1" :on-change="handleTransferProof" :on-remove="clearTransferProof"><el-button>选择凭证</el-button></el-upload></el-form-item>
      </el-form>
      <template #footer><el-button @click="transferDialogVisible = false">取消</el-button><el-button type="primary" :loading="workflowSaving" @click="saveTransfer">保存转付记录</el-button></template>
    </el-dialog>

    <el-dialog v-model="transferCompletionVisible" title="补充内部转付凭证" width="min(480px, 94vw)">
      <el-form label-position="top" class="dialog-form"><el-form-item label="转付时间"><el-date-picker v-model="transferCompletionDate" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" /></el-form-item><el-form-item label="流水号"><el-input v-model="transferCompletionReference" placeholder="银行或支付平台流水号" /></el-form-item><el-form-item label="转账凭证" required><el-upload :auto-upload="false" :limit="1" :on-change="handleTransferCompletionProof" :on-remove="clearTransferCompletionProof"><el-button>选择凭证</el-button></el-upload></el-form-item></el-form>
      <template #footer><el-button @click="transferCompletionVisible = false">取消</el-button><el-button type="primary" :loading="workflowSaving" @click="completeTransfer">确认完成</el-button></template>
    </el-dialog>

    <el-dialog v-model="ocrVisible" title="票据 OCR 识别" width="min(660px, 94vw)">
      <el-upload drag :auto-upload="false" :limit="1" accept="image/*" :on-change="handleOCRFile" :on-remove="clearOCRFile"><div class="el-upload__text">拖入票据图片，或点击选择</div></el-upload>
      <div v-if="ocrResult" class="ocr-result"><el-alert :title="ocrResult.message" type="success" :closable="false" /><dl><div><dt>金额</dt><dd>{{ ocrResult.recognized.amount || '未识别' }}</dd></div><div><dt>日期</dt><dd>{{ ocrResult.recognized.expense_date || '未识别' }}</dd></div><div><dt>标题</dt><dd>{{ ocrResult.recognized.title || '未识别' }}</dd></div><div><dt>商户</dt><dd>{{ ocrResult.recognized.vendor || '未识别' }}</dd></div></dl></div>
      <template #footer><el-button @click="ocrVisible = false">取消</el-button><el-button :disabled="!ocrFile" :loading="ocrLoading" @click="recognizeOCRFile">开始识别</el-button><el-button type="primary" :disabled="!ocrResult" @click="applyOCRToExpense">带入支出登记</el-button></template>
    </el-dialog>

    <el-dialog v-model="budgetDialogVisible" title="设置项目核定预算上限" width="min(480px, 94vw)">
      <el-form label-position="top" class="dialog-form"><el-form-item label="项目" required><el-select v-model="budgetForm.project" filterable @change="syncBudgetAmount"><el-option v-for="item in manageableProjects" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="核定预算上限" required><el-input-number v-model="budgetForm.planned_amount" :min="0" :precision="2" :controls="false" /></el-form-item></el-form>
      <template #footer><el-button @click="budgetDialogVisible = false">取消</el-button><el-button type="primary" :loading="budgetSaving" @click="saveBudget">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import { ArrowDown, CameraFilled, Download, Plus, Refresh, WarningFilled } from '@element-plus/icons-vue'
import {
  completeFinancePayment,
  completeFinanceTransfer,
  createFinanceBudget,
  createFinanceExpense,
  createFinanceIncome,
  createFinancePayment,
  createFinanceTransfer,
  failFinancePayment,
  failFinanceTransfer,
  getAllFinanceBudgets,
  getAllFinanceExpenses,
  getAllFinanceIncomes,
  getAllFinancePayments,
  getFinanceFundTodos,
  getFinanceTraceabilitySummary,
  getFinanceTransfers,
  recognizeReceipt,
  resolveFinanceExportTarget,
  reviewReimbursement,
  setExpenseAllocations,
  setFinanceIncomeStage,
  setIncomeAllocations,
  submitReimbursement,
  updateFinanceBudget,
  uploadFinanceAttachment,
  type FinanceExportFormat,
  type FinanceFundTodosResponse,
  type FinanceTraceabilitySummaryResponse,
  type OCRReceiptResult,
} from '@/api/finance'
import { getCompetitionEvents, getCompetitions, type CompetitionEvent } from '@/api/competitions'
import { getMembers } from '@/api/members'
import { getProjects } from '@/api/projects'
import { exportData } from '@/api/exports'
import { useUserStore } from '@/stores/user'
import { FINANCE_CATEGORY_MAP } from '@/utils/constants'
import { downloadBlob, formatMoneyWithComma, getFinanceCategoryLabel } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import FinanceRecordDrawer from './FinanceRecordDrawer.vue'
import FinanceTraceabilityTable from './FinanceTraceabilityTable.vue'
import {
  allocationEntriesForEvent,
  allocationTargetsBelongToProject,
  allocationTargetsShareEvent,
  attributedRecordAmount,
  allExpenseAttachments,
  buildMetricSummary,
  buildTraceEntryMetadataIndex,
  buildTraceabilityGroups,
  completedPaymentAmount,
  expenseStatusLabel,
  expenseStatusTone,
  filterLedgerRecordByDestination,
  incomeStageLabel,
  mergePaymentsIntoExpenses,
  moneyNumber,
  normalizeFundTodos,
  normalizedExpenseStatus,
  remainingPayable,
  resolveAllocationEventId,
} from './financeLedger'
import type {
  Competition,
  FinanceBudget,
  FinanceCategory,
  FinanceIncomeType,
  Member,
  Project,
} from '@/types'
import type {
  FinanceAttachmentKind,
  FinanceIncomeStage,
  FinanceInternalTransfer,
  FinanceLedgerExpense,
  FinanceLedgerIncome,
  FinanceLedgerPayment,
  FinancePerspective,
  FinanceTraceabilityLeaf,
} from '@/types/financeLedger'

interface AllocationFormRow {
  competition_entry?: number
  amount?: number
  note: string
}

const route = useRoute()
const userStore = useUserStore()
const requestedProject = Number(route.query.project_id)
const workspaceTab = ref('ledger')
const flowTab = ref('expenses')
const perspective = ref<FinancePerspective>('project')
const filterProject = ref<number | undefined>(Number.isInteger(requestedProject) && requestedProject > 0 ? requestedProject : undefined)
const filterEvent = ref<number | undefined>()
const ledgerKeyword = ref('')
const todoFilter = ref('')
const loading = ref(false)
const loadError = ref(false)
const expenseList = ref<FinanceLedgerExpense[]>([])
const incomeList = ref<FinanceLedgerIncome[]>([])
const paymentList = ref<FinanceLedgerPayment[]>([])
const transferList = ref<FinanceInternalTransfer[]>([])
const budgetList = ref<FinanceBudget[]>([])
const projectOptions = ref<Project[]>([])
const competitionOptions = ref<Competition[]>([])
const eventOptions = ref<CompetitionEvent[]>([])
const memberOptions = ref<Member[]>([])
const traceSummary = ref<FinanceTraceabilitySummaryResponse | null>(null)
const fundTodos = ref<FinanceFundTodosResponse | null>(null)
const flowSection = ref<HTMLElement | null>(null)
const drawerVisible = ref(false)
const drawerRow = ref<FinanceTraceabilityLeaf | null>(null)
const allocationEventOptions = computed(() => eventOptions.value.filter(
  (event) => competitionOptions.value.some((entry) => entry.event === event.id),
))

const perspectiveOptions = [
  { label: '按项目查看比赛', value: 'project' },
  { label: '按比赛查看项目', value: 'competition' },
]
const categoryOptions = Object.entries(FINANCE_CATEGORY_MAP).map(([value, item]) => ({ value: value as FinanceCategory, label: item.label }))
const incomeTypeOptions: Array<{ value: FinanceIncomeType; label: string }> = [
  { value: 'bonus', label: '比赛奖金' },
  { value: 'grant', label: '学校 / 项目拨款' },
  { value: 'sponsorship', label: '赞助' },
  { value: 'refund', label: '退款 / 返还' },
  { value: 'other', label: '其他收入' },
]

const globalFinanceManager = computed(() => {
  const role = userStore.userInfo?.global_role || ''
  const permissions = userStore.userInfo?.permission_codes || []
  return ['teacher', 'sys_admin'].includes(role) || permissions.includes('finance.manage')
})

function canManageProject(project: Project): boolean {
  return globalFinanceManager.value
    || project.can_manage === true
    || project.leader === userStore.userInfo?.id
}

const manageableProjects = computed(() => projectOptions.value.filter(canManageProject))
const canRegisterIncome = computed(() => manageableProjects.value.length > 0)
const canSetBudget = computed(() => canRegisterIncome.value)
const canRegisterTransfer = computed(() => globalFinanceManager.value)
const payableProjects = computed(() => canRegisterTransfer.value ? projectOptions.value : [])

const filteredExpenses = computed(() => expenseList.value
  .map((item) => filterLedgerRecordByDestination(item, filterProject.value, filterEvent.value))
  .filter((item): item is FinanceLedgerExpense => Boolean(item)))
const filteredIncomes = computed(() => incomeList.value
  .map((item) => filterLedgerRecordByDestination(item, filterProject.value, filterEvent.value))
  .filter((item): item is FinanceLedgerIncome => Boolean(item)))

const metrics = computed(() => buildMetricSummary(filteredExpenses.value, filteredIncomes.value, traceSummary.value))
const todoCounts = computed(() => normalizeFundTodos(fundTodos.value, expenseList.value))
const traceEntryMetadata = computed(() => buildTraceEntryMetadataIndex(traceSummary.value))
const todoCards = computed(() => [
  { key: 'missing_receipt', label: '待补发票', value: todoCounts.value.missing_receipt, hint: '缺少发票或原始票据', tone: 'warning' },
  { key: 'pending_review', label: '待负责人审核', value: todoCounts.value.pending_review, hint: '额度已临时预留', tone: 'warning' },
  { key: 'pending_payment', label: '已审核待转账', value: todoCounts.value.pending_payment, hint: '等待经费经办人付款', tone: 'primary' },
  { key: 'missing_payment_proof', label: '缺付款凭证', value: todoCounts.value.missing_payment_proof, hint: '已登记转账但未归档', tone: 'danger' },
  { key: 'partially_paid', label: '部分支付', value: todoCounts.value.partially_paid, hint: '仍有金额需要覆盖', tone: 'primary' },
  { key: 'payment_exception', label: '付款异常', value: todoCounts.value.payment_exception, hint: '失败或退回待处理', tone: 'danger' },
  { key: 'stale', label: '长时间未处理', value: todoCounts.value.stale, hint: '超过 7 天未推进', tone: 'muted' },
])
const todoFilterLabel = computed(() => todoCards.value.find((item) => item.key === todoFilter.value)?.label || '')

const rawGroups = computed(() => buildTraceabilityGroups(perspective.value, filteredExpenses.value, filteredIncomes.value)
  .map((group) => ({
    ...group,
    children: group.children.map((row) => {
      const entry = competitionOptions.value.find((item) => item.id === row.competition_entry_id)
      const summaryMetadata = row.competition_entry_id
        ? traceEntryMetadata.value.get(row.competition_entry_id)
        : undefined
      if (!entry && !summaryMetadata) return row
      const activeParticipants = (entry?.participants || []).filter((item) => item.participation_status !== 'withdrawn')
      const participantName = (item: typeof activeParticipants[number]) => item.user_detail?.name || `成员 ${item.user}`
      const leaders = [
        ...(summaryMetadata?.leader_names || []),
        ...(entry?.leader_names || []),
        ...activeParticipants.filter((item) => item.role === 'leader').map(participantName),
      ].filter((name, index, list) => Boolean(name) && list.indexOf(name) === index)
      const participants = [
        ...(summaryMetadata?.participant_names || []),
        ...activeParticipants.map(participantName),
      ].filter((name, index, list) => list.indexOf(name) === index)
      const awardResult = summaryMetadata?.award_result || (
        entry?.is_awarded
          ? entry.award_level || '已获奖'
          : entry?.status === 'completed' ? '未获奖' : '结果待公布'
      )
      return { ...row, leader_names: leaders, participant_names: participants, award_result: awardResult }
    }),
  })))
const visibleGroups = computed(() => {
  const keyword = ledgerKeyword.value.trim().toLocaleLowerCase()
  if (!keyword) return rawGroups.value
  return rawGroups.value
    .map((group) => ({
      ...group,
      children: group.children.filter((row) => [
        row.project_name,
        row.event_name,
        row.event_edition,
        row.competition_entry_name,
        ...row.expenses.map((item) => `${item.title} ${item.purpose || ''} ${item.spender_name || ''}`),
        ...row.incomes.map((item) => `${item.title} ${item.source || ''}`),
      ].join(' ').toLocaleLowerCase().includes(keyword)),
    }))
    .filter((group) => group.children.length > 0)
})

const visibleExpenses = computed(() => filteredExpenses.value.filter(expenseMatchesTodo))
const visibleIncomes = computed(() => filteredIncomes.value)
const filteredPaymentIds = computed(() => new Set(filteredExpenses.value.map((item) => item.id)))
const displayPayments = computed(() => paymentList.value.filter((item) => filteredPaymentIds.value.has(item.expense)))
const visiblePayments = computed(() => todoFilter.value === 'missing_payment_proof'
  ? displayPayments.value.filter((item) => item.status === 'pending_proof' || (item.status === 'completed' && !(item.receipts?.length || item.attachments?.length)))
  : displayPayments.value)

const visibleTransfers = computed(() => transferList.value.filter((item) => (
  (!filterProject.value || item.project === filterProject.value)
  && (!filterEvent.value || competitionOptions.value.find((entry) => entry.id === item.competition_entry)?.event === filterEvent.value)
)))

const categoryBreakdown = computed(() => {
  const totals = new Map<string, number>()
  filteredExpenses.value.forEach((item) => totals.set(
    item.category,
    (totals.get(item.category) || 0) + attributedRecordAmount(item),
  ))
  const max = Math.max(0, ...totals.values())
  return Array.from(totals.entries()).map(([key, amount]) => ({ key, label: getFinanceCategoryLabel(key), amount, percentage: max ? Math.round(amount / max * 100) : 0 })).sort((a, b) => b.amount - a.amount)
})

const projectAnalysis = computed(() => projectOptions.value.map((project) => {
  const spent = expenseList.value.reduce((sum, item) => {
    const attributed = filterLedgerRecordByDestination(item, project.id)
    return sum + (attributed ? attributedRecordAmount(attributed) : 0)
  }, 0)
  const budget = budgetList.value.filter((item) => item.project === project.id).reduce((sum, item) => sum + moneyNumber(item.budget_basis ?? item.planned_amount), 0)
  return { id: project.id, name: project.name, spent, budget, rate: budget > 0 ? Math.round(spent / budget * 100) : spent > 0 ? 100 : 0 }
}).filter((item) => item.spent > 0 || item.budget > 0).sort((a, b) => b.rate - a.rate))

function expenseMatchesTodo(item: FinanceLedgerExpense): boolean {
  if (!todoFilter.value) return true
  const status = normalizedExpenseStatus(item)
  if (todoFilter.value === 'missing_receipt') return !allExpenseAttachments(item).some((attachment) => ['invoice', 'original_receipt'].includes(attachment.attachment_type || ''))
  if (todoFilter.value === 'pending_review') return ['pending', 'pending_review', 'reserved'].includes(status)
  if (todoFilter.value === 'pending_payment') return ['approved', 'pending_payment'].includes(status)
  if (todoFilter.value === 'partially_paid') return status === 'partial_paid'
  if (todoFilter.value === 'payment_exception') return status === 'payment_exception' || (item.payments || []).some((payment) => payment.status === 'failed')
  if (todoFilter.value === 'missing_payment_proof') return (item.payments || []).some((payment) => payment.status === 'pending_proof' || (payment.status === 'completed' && !(payment.receipts?.length || payment.attachments?.length)))
  if (todoFilter.value === 'stale') return ['pending', 'approved', 'partial_paid'].includes(status) && Date.now() - new Date(item.updated_at || item.created_at).getTime() >= 7 * 86400000
  return true
}

function money(value: number | string | null | undefined): string { return formatMoneyWithComma(value) }
function memberUserId(member: Member): number { return member.user || member.id }
function memberName(member: Member): string { return member.user_name || member.name || member.username || member.email }
function eventLabel(event: CompetitionEvent): string { return `${event.name}${event.edition ? ` · ${event.edition}` : ''}` }
function competitionLabel(item: Competition): string { return `${item.event_name || item.name}${item.event_edition ? ` · ${item.event_edition}` : ''} / ${item.entry_name || item.project_name || item.name}` }
function allocationCompetitionLabel(item: Competition): string {
  const edition = item.event_edition ? ` · ${item.event_edition}` : ''
  return `${item.event_name || item.name}${edition} / ${item.project_name || `项目 ${item.project}`} / ${item.entry_name || item.name}`
}
function allocationEventLabel(eventId: number): string {
  const event = eventOptions.value.find((item) => item.id === eventId)
  return event ? eventLabel(event) : `比赛届次 ${eventId}`
}
function projectName(projectId?: number): string {
  return projectOptions.value.find((item) => item.id === projectId)?.name || '当前项目'
}
function incomeTypeLabel(type: string): string { return incomeTypeOptions.find((item) => item.value === type)?.label || type }
function paymentStatusLabel(status?: string): string { return ({ pending_proof: '待补凭证', completed: '已完成', failed: '付款异常', reversed: '已冲正' } as Record<string, string>)[status || ''] || status || '未知' }
function paymentStatusTone(status?: string): 'success' | 'warning' | 'danger' | 'info' { return status === 'completed' ? 'success' : status === 'failed' ? 'danger' : status === 'pending_proof' ? 'warning' : 'info' }
function transferStatusLabel(status?: string): string { return ({ pending_proof: '待补凭证', completed: '已完成', failed: '转付异常' } as Record<string, string>)[status || ''] || status || '未知' }
function transferStatusTone(status?: string): 'success' | 'warning' | 'danger' { return status === 'completed' ? 'success' : status === 'failed' ? 'danger' : 'warning' }
function expenseById(id: number): FinanceLedgerExpense | undefined { return expenseList.value.find((item) => item.id === id) }
function expensePaid(item: unknown): number { return completedPaymentAmount(item as FinanceLedgerExpense) }
function expensePayable(item: unknown): number { return remainingPayable(item as FinanceLedgerExpense) }
function expenseScopeLabel(value: unknown): string { const item = value as FinanceLedgerExpense; return item.allocations?.length ? `分摊至 ${item.allocations.length} 个参赛队` : item.competition_entry_name ? `${item.event_name || '比赛'} / ${item.competition_entry_name}` : '项目公共支出' }
function incomeScopeLabel(value: unknown): string { const item = value as FinanceLedgerIncome; return item.allocations?.length ? `分摊至 ${item.allocations.length} 个参赛队` : item.competition_entry_name ? `${item.event_name || '比赛'} / ${item.competition_entry_name}` : '项目公共收入' }

function normalizePage<T>(value: { results?: T[] } | T[]): T[] { return Array.isArray(value) ? value : value.results || [] }

async function loadReferenceData(): Promise<void> {
  const [projects, competitions, events, members] = await Promise.allSettled([
    getProjects({ page: 1, page_size: 100 }),
    getCompetitions({ page: 1, page_size: 100 }),
    getCompetitionEvents({ page: 1, page_size: 100 }),
    getMembers({ page: 1, page_size: 100 }),
  ])
  if (projects.status === 'fulfilled') projectOptions.value = projects.value.results
  if (competitions.status === 'fulfilled') competitionOptions.value = competitions.value.results
  if (events.status === 'fulfilled') eventOptions.value = events.value.results
  if (members.status === 'fulfilled') memberOptions.value = members.value.results
}

async function loadData(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const [expenses, incomes, payments, transfers, budgets, todos] = await Promise.all([
      getAllFinanceExpenses() as unknown as Promise<FinanceLedgerExpense[]>,
      getAllFinanceIncomes() as unknown as Promise<FinanceLedgerIncome[]>,
      getAllFinancePayments().catch(() => []),
      getFinanceTransfers({ page: 1, page_size: 100 }).then(normalizePage).catch(() => []),
      getAllFinanceBudgets().catch(() => []),
      getFinanceFundTodos().catch(() => null),
    ])
    paymentList.value = payments
    expenseList.value = mergePaymentsIntoExpenses(expenses, payments)
    incomeList.value = incomes
    transferList.value = transfers
    budgetList.value = budgets
    fundTodos.value = todos
    await loadTraceSummary()
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function loadTraceSummary(): Promise<void> {
  try {
    traceSummary.value = await getFinanceTraceabilitySummary({ perspective: perspective.value, project: filterProject.value, event: filterEvent.value })
  } catch {
    traceSummary.value = null
  }
}

function resetFilters(): void { filterProject.value = undefined; filterEvent.value = undefined; ledgerKeyword.value = '' }
function selectTodo(key: string): void {
  todoFilter.value = todoFilter.value === key ? '' : key
  flowTab.value = key === 'missing_payment_proof' ? 'payments' : 'expenses'
  nextTick(() => flowSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

function openTraceabilityRow(row: FinanceTraceabilityLeaf): void { drawerRow.value = row; drawerVisible.value = true }
function openExpenseTrace(value: unknown): void {
  const expense = value as FinanceLedgerExpense
  const row = buildTraceabilityGroups('project', [expense], []).flatMap((group) => group.children)[0]
  if (row) openTraceabilityRow(row)
}
function openIncomeTrace(value: unknown): void {
  const income = value as FinanceLedgerIncome
  const row = buildTraceabilityGroups('project', [], [income]).flatMap((group) => group.children)[0]
  if (row) openTraceabilityRow(row)
}

function canSubmitExpense(value: unknown): boolean {
  const item = value as FinanceLedgerExpense
  if (!['draft', 'rejected', 'missing_receipt'].includes(normalizedExpenseStatus(item))) return false
  const userId = userStore.userInfo?.id
  return item.can_manage === true || globalFinanceManager.value || item.spender === userId || projectOptions.value.find((project) => project.id === item.project)?.leader === userId
}
function canReviewExpense(value: unknown): boolean { const item = value as FinanceLedgerExpense; return ['pending', 'pending_review', 'reserved'].includes(normalizedExpenseStatus(item)) && (item.can_review ?? canManageProjectById(item.project)) }
function canPayExpense(value: unknown): boolean { const item = value as FinanceLedgerExpense; return ['approved', 'pending_payment', 'partial_paid', 'payment_exception'].includes(normalizedExpenseStatus(item)) && (item.can_pay ?? canManageProjectById(item.project)) }
function canAdvanceIncome(value: unknown): boolean { const item = value as FinanceLedgerIncome; return item.stage !== 'received' && (item.can_manage ?? canManageProjectById(item.project)) }
function canManageProjectById(id: number): boolean { const project = projectOptions.value.find((item) => item.id === id); return project ? canManageProject(project) : globalFinanceManager.value }
function canOperatePayment(value: unknown): boolean { const item = value as FinanceLedgerPayment; return canPayExpense(expenseById(item.expense) || ({ project: 0, reimbursement_status: 'approved' } as FinanceLedgerExpense)) }
function canOperateTransfer(value: unknown): boolean { const item = value as FinanceInternalTransfer; return item.can_manage ?? canManageProjectById(item.project) }

async function submitExpense(value: unknown): Promise<void> {
  const item = value as FinanceLedgerExpense
  try {
    await ElMessageBox.confirm(`提交“${item.title}”并预留 ${money(item.amount)}？`, '提交报销')
    await submitReimbursement(item.id)
    ElMessage.success('已提交负责人审核，额度已进入预留')
    await loadData()
  } catch { /* 用户取消或请求拦截器已提示 */ }
}

const expenseDialogVisible = ref(false)
const expenseSaving = ref(false)
const expenseFile = ref<File | null>(null)
const expenseDraftId = ref<number | null>(null)
const expenseAttachmentUploaded = ref(false)
const expenseAllocationsSaved = ref(false)
const expenseForm = reactive({ project: undefined as number | undefined, scope: 'competition_entry' as 'competition_entry' | 'project_common' | 'allocated', competition_entry: undefined as number | undefined, allocation_mode: 'same_event' as 'same_event' | 'same_project', allocation_event: undefined as number | undefined, allocations: [] as AllocationFormRow[], spender: undefined as number | undefined, payee: undefined as number | undefined, category: 'travel' as FinanceCategory, amount: undefined as number | undefined, expense_date: '', attachment_type: 'invoice' as FinanceAttachmentKind, title: '', purpose: '' })
const expenseEntryOptions = computed(() => competitionOptions.value.filter((item) => !expenseForm.project || item.project === expenseForm.project))
const expenseAllocationEventId = computed(() => resolveAllocationEventId(
  expenseForm.allocation_event,
  expenseForm.allocations.map((item) => item.competition_entry),
  competitionOptions.value,
))
const expenseAllocationEntryOptions = computed(() => allocationEntriesForEvent(
  expenseForm.allocation_mode === 'same_project'
    ? competitionOptions.value.filter((item) => item.project === expenseForm.project)
    : competitionOptions.value.filter((item) => Boolean(item.event)),
  expenseForm.allocation_mode === 'same_event' ? expenseAllocationEventId.value : undefined,
))
const expenseAllocationProjectCount = computed(() => new Set(
  expenseAllocationEntryOptions.value.map((item) => item.project),
).size)
const expenseAllocationTotal = computed(() => expenseForm.allocations.reduce((sum, item) => sum + Number(item.amount || 0), 0))
const expenseAllocationBalanced = computed(() => Math.abs(expenseAllocationTotal.value - Number(expenseForm.amount || 0)) < 0.005)

function openExpenseDialog(): void {
  const currentUser = userStore.userInfo?.id
  Object.assign(expenseForm, { project: filterProject.value || projectOptions.value[0]?.id, scope: 'competition_entry', competition_entry: undefined, allocation_mode: 'same_event', allocation_event: undefined, allocations: [], spender: currentUser, payee: currentUser, category: 'travel', amount: undefined, expense_date: new Date().toISOString().slice(0, 10), attachment_type: 'invoice', title: '', purpose: '' })
  expenseFile.value = null; expenseDraftId.value = null; expenseAttachmentUploaded.value = false; expenseAllocationsSaved.value = false; expenseDialogVisible.value = true
}
function resetExpenseScope(): void { expenseForm.competition_entry = undefined; expenseForm.allocation_event = undefined; expenseForm.allocations = []; expenseDraftId.value = null; if (!expenseForm.project || !canManageProjectById(expenseForm.project)) { expenseForm.scope = 'competition_entry'; expenseForm.spender = userStore.userInfo?.id; expenseForm.payee = userStore.userInfo?.id } }
function resetExpenseScopeTarget(): void { expenseForm.competition_entry = undefined; expenseForm.allocation_event = undefined; expenseForm.allocations = []; if (expenseForm.scope === 'allocated') addExpenseAllocation() }
function addExpenseAllocation(): void { expenseForm.allocations.push({ competition_entry: undefined, amount: undefined, note: '' }) }
function resetExpenseAllocationMode(): void {
  expenseForm.allocation_event = undefined
  expenseForm.allocations = []
  addExpenseAllocation()
  expenseAllocationsSaved.value = false
}
function handleExpenseAllocationEventChange(eventId?: number): void {
  expenseForm.allocation_event = eventId || undefined
  expenseForm.allocations.forEach((allocation) => {
    const entry = competitionOptions.value.find((item) => item.id === allocation.competition_entry)
    if (!eventId || entry?.event !== eventId) allocation.competition_entry = undefined
  })
  expenseAllocationsSaved.value = false
}
function handleExpenseAllocationEntryChange(entryId?: number): void {
  const entry = competitionOptions.value.find((item) => item.id === entryId)
  if (expenseForm.allocation_mode === 'same_event' && !expenseForm.allocation_event && entry?.event) expenseForm.allocation_event = entry.event
  expenseAllocationsSaved.value = false
}
function isExpenseAllocationEntrySelected(entryId: number, rowIndex: number): boolean {
  return expenseForm.allocations.some((allocation, index) => index !== rowIndex && allocation.competition_entry === entryId)
}
function handleExpenseFile(file: UploadFile): void { expenseFile.value = file.raw || null; expenseAttachmentUploaded.value = false }
function clearExpenseFile(): void { expenseFile.value = null; expenseAttachmentUploaded.value = false }

function validateExpense(submitNow: boolean): string | null {
  if (!expenseForm.project || !expenseForm.amount || !expenseForm.expense_date || !expenseForm.title.trim()) return '请补全项目、金额、日期和支出标题'
  if (!expenseForm.spender || !expenseForm.payee) return '请选择垫付人和实际收款人'
  if (expenseForm.scope === 'competition_entry' && !expenseForm.competition_entry) return '请选择具体比赛和参赛队'
  if (expenseForm.scope === 'allocated') {
    const entryIds = expenseForm.allocations.map((item) => item.competition_entry)
    if (expenseForm.allocation_mode === 'same_event' && (!expenseForm.allocation_event || !allocationTargetsShareEvent(entryIds, competitionOptions.value, expenseForm.allocation_event))) return '跨项目分摊的所有参赛队必须属于同一比赛届次'
    if (expenseForm.allocation_mode === 'same_project' && !allocationTargetsBelongToProject(entryIds, competitionOptions.value, expenseForm.project)) return '单项目兼容分摊只能选择当前归账项目的参赛条目'
    if (new Set(entryIds).size !== entryIds.length) return '同一个参赛队不能重复分摊'
    if (!expenseForm.allocations.length || expenseForm.allocations.some((item) => !item.competition_entry || !item.amount) || !expenseAllocationBalanced.value) return '请完整填写分摊明细，并确保合计等于支出金额'
  }
  if (submitNow && (!expenseFile.value || !['invoice', 'original_receipt'].includes(expenseForm.attachment_type))) return '提交审核前必须上传发票或原始票据'
  return null
}

async function saveExpense(submitNow: boolean): Promise<void> {
  const invalid = validateExpense(submitNow)
  if (invalid) { ElMessage.warning(invalid); return }
  expenseSaving.value = true
  try {
    if (!expenseDraftId.value) {
      const created = await createFinanceExpense({ project: expenseForm.project!, competition_entry: expenseForm.scope === 'competition_entry' ? expenseForm.competition_entry : null, scope: expenseForm.scope, category: expenseForm.category, title: expenseForm.title.trim(), purpose: expenseForm.purpose.trim(), amount: expenseForm.amount!, expense_date: expenseForm.expense_date, spender: expenseForm.spender, payee: expenseForm.payee })
      expenseDraftId.value = created.id
    }
    if (expenseForm.scope === 'allocated' && !expenseAllocationsSaved.value) {
      await setExpenseAllocations(expenseDraftId.value, expenseForm.allocations.map((item) => ({ competition_entry: item.competition_entry!, amount: item.amount!, note: item.note.trim() })))
      expenseAllocationsSaved.value = true
    }
    if (expenseFile.value && !expenseAttachmentUploaded.value) {
      await uploadFinanceAttachment({ expense: expenseDraftId.value, file: expenseFile.value, attachment_type: expenseForm.attachment_type })
      expenseAttachmentUploaded.value = true
    }
    if (submitNow) await submitReimbursement(expenseDraftId.value)
    ElMessage.success(submitNow ? '支出已提交审核，额度已预留' : '支出已保存为草稿')
    expenseDialogVisible.value = false
    await loadData()
  } finally { expenseSaving.value = false }
}

const incomeDialogVisible = ref(false)
const incomeSaving = ref(false)
const incomeProof = ref<File | null>(null)
const incomeDraftId = ref<number | null>(null)
const incomeAllocationsSaved = ref(false)
const incomeForm = reactive({ project: undefined as number | undefined, scope: 'competition_entry' as 'competition_entry' | 'project_common' | 'allocated', competition_entry: undefined as number | undefined, allocation_mode: 'same_event' as 'same_event' | 'same_project', allocation_event: undefined as number | undefined, allocations: [] as AllocationFormRow[], income_type: 'bonus' as FinanceIncomeType, stage: 'expected' as FinanceIncomeStage, income_date: '', amount: undefined as number | undefined, title: '', source: '', reference_number: '', note: '' })
const incomeEntryOptions = computed(() => competitionOptions.value.filter((item) => !incomeForm.project || item.project === incomeForm.project))
const incomeAllocationEventId = computed(() => resolveAllocationEventId(
  incomeForm.allocation_event,
  incomeForm.allocations.map((item) => item.competition_entry),
  competitionOptions.value,
))
const incomeAllocationEntryOptions = computed(() => allocationEntriesForEvent(
  incomeForm.allocation_mode === 'same_project'
    ? competitionOptions.value.filter((item) => item.project === incomeForm.project)
    : competitionOptions.value.filter((item) => Boolean(item.event)),
  incomeForm.allocation_mode === 'same_event' ? incomeAllocationEventId.value : undefined,
))
const incomeAllocationProjectCount = computed(() => new Set(
  incomeAllocationEntryOptions.value.map((item) => item.project),
).size)
const incomeAllocationTotal = computed(() => incomeForm.allocations.reduce((sum, item) => sum + Number(item.amount || 0), 0))
const incomeAllocationBalanced = computed(() => Math.abs(incomeAllocationTotal.value - Number(incomeForm.amount || 0)) < 0.005)

function openIncomeDialog(): void { Object.assign(incomeForm, { project: filterProject.value && manageableProjects.value.some((item) => item.id === filterProject.value) ? filterProject.value : manageableProjects.value[0]?.id, scope: 'competition_entry', competition_entry: undefined, allocation_mode: 'same_event', allocation_event: undefined, allocations: [], income_type: 'bonus', stage: 'expected', income_date: new Date().toISOString().slice(0, 10), amount: undefined, title: '', source: '', reference_number: '', note: '' }); incomeProof.value = null; incomeDraftId.value = null; incomeAllocationsSaved.value = false; incomeDialogVisible.value = true }
function resetIncomeScope(): void { incomeForm.competition_entry = undefined; incomeForm.allocation_event = undefined; incomeForm.allocations = []; incomeDraftId.value = null }
function resetIncomeScopeTarget(): void { incomeForm.competition_entry = undefined; incomeForm.allocation_event = undefined; incomeForm.allocations = []; if (incomeForm.scope === 'allocated') addIncomeAllocation() }
function addIncomeAllocation(): void { incomeForm.allocations.push({ competition_entry: undefined, amount: undefined, note: '' }) }
function resetIncomeAllocationMode(): void {
  incomeForm.allocation_event = undefined
  incomeForm.allocations = []
  addIncomeAllocation()
  incomeAllocationsSaved.value = false
}
function handleIncomeAllocationEventChange(eventId?: number): void {
  incomeForm.allocation_event = eventId || undefined
  incomeForm.allocations.forEach((allocation) => {
    const entry = competitionOptions.value.find((item) => item.id === allocation.competition_entry)
    if (!eventId || entry?.event !== eventId) allocation.competition_entry = undefined
  })
  incomeAllocationsSaved.value = false
}
function handleIncomeAllocationEntryChange(entryId?: number): void {
  const entry = competitionOptions.value.find((item) => item.id === entryId)
  if (incomeForm.allocation_mode === 'same_event' && !incomeForm.allocation_event && entry?.event) incomeForm.allocation_event = entry.event
  incomeAllocationsSaved.value = false
}
function isIncomeAllocationEntrySelected(entryId: number, rowIndex: number): boolean {
  return incomeForm.allocations.some((allocation, index) => index !== rowIndex && allocation.competition_entry === entryId)
}
function handleIncomeProof(file: UploadFile): void { incomeProof.value = file.raw || null }
function clearIncomeProof(): void { incomeProof.value = null }

async function saveIncome(): Promise<void> {
  if (!incomeForm.project || !incomeForm.amount || !incomeForm.title.trim() || !incomeForm.income_date) { ElMessage.warning('请补全项目、标题、金额和业务日期'); return }
  if (incomeForm.scope === 'competition_entry' && !incomeForm.competition_entry) { ElMessage.warning('请选择具体比赛和参赛队'); return }
  if (incomeForm.scope === 'allocated') {
    const entryIds = incomeForm.allocations.map((item) => item.competition_entry)
    if (incomeForm.allocation_mode === 'same_event' && (!incomeForm.allocation_event || !allocationTargetsShareEvent(entryIds, competitionOptions.value, incomeForm.allocation_event))) { ElMessage.warning('跨项目分摊的所有参赛队必须属于同一比赛届次'); return }
    if (incomeForm.allocation_mode === 'same_project' && !allocationTargetsBelongToProject(entryIds, competitionOptions.value, incomeForm.project)) { ElMessage.warning('单项目兼容分摊只能选择当前归账项目的参赛条目'); return }
    if (new Set(entryIds).size !== entryIds.length) { ElMessage.warning('同一个参赛队不能重复分摊'); return }
    if (!incomeForm.allocations.length || incomeForm.allocations.some((item) => !item.competition_entry || !item.amount) || !incomeAllocationBalanced.value) { ElMessage.warning('请完整填写分摊，并确保合计等于收入金额'); return }
  }
  if (incomeForm.stage === 'received' && !incomeProof.value) { ElMessage.warning('登记已到账收入必须上传到账凭证'); return }
  incomeSaving.value = true
  try {
    if (!incomeDraftId.value) {
      const created = await createFinanceIncome({ project: incomeForm.project, competition_entry: incomeForm.scope === 'competition_entry' ? incomeForm.competition_entry : null, title: incomeForm.title.trim(), amount: incomeForm.amount, income_type: incomeForm.income_type, stage: 'expected', income_date: incomeForm.income_date, source: incomeForm.source.trim(), reference_number: incomeForm.reference_number.trim(), note: incomeForm.note.trim() })
      incomeDraftId.value = created.id
    }
    if (incomeForm.scope === 'allocated' && !incomeAllocationsSaved.value) {
      await setIncomeAllocations(incomeDraftId.value, incomeForm.allocations.map((item) => ({ competition_entry: item.competition_entry!, amount: item.amount!, note: item.note.trim() })))
      incomeAllocationsSaved.value = true
    }
    if (incomeForm.stage !== 'expected') await setFinanceIncomeStage(incomeDraftId.value, incomeForm.stage, incomeForm.stage === 'received' ? incomeProof.value || undefined : undefined)
    ElMessage.success(incomeForm.stage === 'received' ? '收入已登记为到账资金' : incomeForm.stage === 'confirmed' ? '收入已登记为确认应收' : '预计收入已登记')
    incomeDialogVisible.value = false
    await loadData()
  } finally { incomeSaving.value = false }
}

const workflowExpense = ref<FinanceLedgerExpense | null>(null)
const workflowIncome = ref<FinanceLedgerIncome | null>(null)
const workflowSaving = ref(false)
const reviewDialogVisible = ref(false)
const reviewForm = reactive({ approved: true, opinion: '' })
function openReviewDialog(value: unknown): void { const item = value as FinanceLedgerExpense; workflowExpense.value = item; reviewForm.approved = true; reviewForm.opinion = ''; reviewDialogVisible.value = true }
async function saveReview(): Promise<void> { if (!workflowExpense.value) return; workflowSaving.value = true; try { await reviewReimbursement(workflowExpense.value.id, reviewForm.approved, reviewForm.opinion.trim()); ElMessage.success(reviewForm.approved ? '审核通过，进入待转账' : '已驳回并释放预留'); reviewDialogVisible.value = false; await loadData() } finally { workflowSaving.value = false } }

const paymentDialogVisible = ref(false)
const paymentMode = ref<'create' | 'complete'>('create')
const selectedPayment = ref<FinanceLedgerPayment | null>(null)
const paymentProof = ref<File | null>(null)
const paymentForm = reactive({ recipient: undefined as number | undefined, amount: undefined as number | undefined, payment_method: '银行转账', payment_reference: '', payment_date: '', status: 'completed' as 'completed' | 'pending_proof' })
const paymentMaxAmount = computed(() => paymentMode.value === 'complete' ? Number(selectedPayment.value?.amount || 0) : workflowExpense.value ? remainingPayable(workflowExpense.value) : 0)
function openPaymentDialog(value: unknown): void { const item = value as FinanceLedgerExpense; workflowExpense.value = item; selectedPayment.value = null; paymentMode.value = 'create'; Object.assign(paymentForm, { recipient: item.payee || item.spender || undefined, amount: remainingPayable(item), payment_method: '银行转账', payment_reference: '', payment_date: '', status: 'completed' }); paymentProof.value = null; paymentDialogVisible.value = true }
function openCompletePaymentDialog(value: unknown): void { const item = value as FinanceLedgerPayment; selectedPayment.value = item; workflowExpense.value = expenseById(item.expense) || null; paymentMode.value = 'complete'; Object.assign(paymentForm, { recipient: item.recipient || undefined, amount: moneyNumber(item.amount), payment_method: item.payment_method || '银行转账', payment_reference: item.payment_reference || '', payment_date: '', status: 'completed' }); paymentProof.value = null; paymentDialogVisible.value = true }
function handlePaymentProof(file: UploadFile): void { paymentProof.value = file.raw || null }
function clearPaymentProof(): void { paymentProof.value = null }
async function savePayment(): Promise<void> {
  if (!paymentForm.recipient || !paymentForm.amount || !paymentForm.payment_method.trim() || !paymentForm.payment_reference.trim()) { ElMessage.warning('请补全收款人、金额、付款方式和流水号'); return }
  if ((paymentMode.value === 'complete' || paymentForm.status === 'completed') && !paymentProof.value) { ElMessage.warning('完成付款必须上传转账凭证'); return }
  workflowSaving.value = true
  try {
    if (paymentMode.value === 'complete' && selectedPayment.value && paymentProof.value) {
      await completeFinancePayment(selectedPayment.value.id, { recipient: paymentForm.recipient, amount: paymentForm.amount, payment_method: paymentForm.payment_method.trim(), payment_reference: paymentForm.payment_reference.trim(), payment_date: paymentForm.payment_date || undefined, proof: paymentProof.value })
    } else if (workflowExpense.value) {
      await createFinancePayment({ expense: workflowExpense.value.id, recipient: paymentForm.recipient, amount: paymentForm.amount, payment_method: paymentForm.payment_method.trim(), payment_reference: paymentForm.payment_reference.trim(), payment_date: paymentForm.payment_date || undefined, status: paymentForm.status, proof: paymentProof.value || undefined })
    }
    ElMessage.success(paymentForm.status === 'pending_proof' ? '付款已登记为待补凭证，尚未计入实际支出' : '付款凭证已归档，金额计入团队实际支付')
    paymentDialogVisible.value = false
    await loadData()
  } finally { workflowSaving.value = false }
}
async function markPaymentFailed(input: unknown): Promise<void> { const item = input as FinanceLedgerPayment; try { const { value } = await ElMessageBox.prompt('填写付款失败、退回或其他异常原因', '标记付款异常', { inputValidator: (text) => Boolean(String(text || '').trim()) || '必须填写原因' }); await failFinancePayment(item.id, value.trim()); ElMessage.success('已标记付款异常'); await loadData() } catch { /* 用户取消 */ } }

const incomeStageDialogVisible = ref(false)
const incomeStageProof = ref<File | null>(null)
const incomeStageForm = reactive({ stage: 'confirmed' as FinanceIncomeStage })
function openIncomeStageDialog(value: unknown): void { const item = value as FinanceLedgerIncome; workflowIncome.value = item; incomeStageForm.stage = item.stage === 'expected' ? 'confirmed' : 'received'; incomeStageProof.value = null; incomeStageDialogVisible.value = true }
function handleIncomeStageProof(file: UploadFile): void { incomeStageProof.value = file.raw || null }
function clearIncomeStageProof(): void { incomeStageProof.value = null }
async function saveIncomeStage(): Promise<void> { if (!workflowIncome.value) return; if (incomeStageForm.stage === 'received' && !incomeStageProof.value) { ElMessage.warning('转为已到账必须上传到账凭证'); return } workflowSaving.value = true; try { await setFinanceIncomeStage(workflowIncome.value.id, incomeStageForm.stage, incomeStageProof.value || undefined); ElMessage.success(`收入已推进为${incomeStageLabel(incomeStageForm.stage)}`); incomeStageDialogVisible.value = false; await loadData() } finally { workflowSaving.value = false } }

const transferDialogVisible = ref(false)
const transferProof = ref<File | null>(null)
const transferForm = reactive({ project: undefined as number | undefined, competition_entry: undefined as number | undefined, source_type: 'member' as 'member' | 'external', from_user: undefined as number | undefined, source_label: '', to_user: undefined as number | undefined, amount: undefined as number | undefined, status: 'completed' as 'completed' | 'pending_proof' | 'failed', payment_method: '银行转账', payment_reference: '', transfer_date: '', failure_reason: '', note: '' })
const transferEntryOptions = computed(() => competitionOptions.value.filter((item) => !transferForm.project || item.project === transferForm.project))
function openTransferDialog(): void { Object.assign(transferForm, { project: filterProject.value && payableProjects.value.some((item) => item.id === filterProject.value) ? filterProject.value : payableProjects.value[0]?.id, competition_entry: undefined, source_type: 'member', from_user: userStore.userInfo?.id, source_label: '', to_user: undefined, amount: undefined, status: 'completed', payment_method: '银行转账', payment_reference: '', transfer_date: '', failure_reason: '', note: '' }); transferProof.value = null; transferDialogVisible.value = true }
function handleTransferProof(file: UploadFile): void { transferProof.value = file.raw || null }
function clearTransferProof(): void { transferProof.value = null }
async function saveTransfer(): Promise<void> {
  if (!transferForm.project || !transferForm.to_user || !transferForm.amount) { ElMessage.warning('请补全项目、接收人和金额'); return }
  if (transferForm.source_type === 'member' && !transferForm.from_user) { ElMessage.warning('请选择转出人'); return }
  if (transferForm.source_type === 'external' && !transferForm.source_label.trim()) { ElMessage.warning('请填写外部资金来源'); return }
  if (transferForm.source_type === 'member' && transferForm.from_user === transferForm.to_user) { ElMessage.warning('转出人与接收人不能相同'); return }
  if (transferForm.status === 'completed' && !transferProof.value) { ElMessage.warning('完成内部转付必须上传转账凭证'); return }
  if (transferForm.status === 'failed' && !transferForm.failure_reason.trim()) { ElMessage.warning('转付失败必须填写原因'); return }
  workflowSaving.value = true
  try { await createFinanceTransfer({ project: transferForm.project, competition_entry: transferForm.competition_entry, from_user: transferForm.source_type === 'member' ? transferForm.from_user : null, to_user: transferForm.to_user, source_label: transferForm.source_type === 'external' ? transferForm.source_label.trim() : '', amount: transferForm.amount, status: transferForm.status, payment_method: transferForm.payment_method.trim(), payment_reference: transferForm.payment_reference.trim(), transfer_date: transferForm.transfer_date || undefined, failure_reason: transferForm.failure_reason.trim(), note: transferForm.note.trim(), proof_file: transferProof.value || undefined }); ElMessage.success('内部转付已登记，不重复计入收支'); transferDialogVisible.value = false; await loadData() } finally { workflowSaving.value = false }
}

const transferCompletionVisible = ref(false)
const selectedTransfer = ref<FinanceInternalTransfer | null>(null)
const transferCompletionProof = ref<File | null>(null)
const transferCompletionDate = ref('')
const transferCompletionReference = ref('')
function openCompleteTransferDialog(value: unknown): void { const item = value as FinanceInternalTransfer; selectedTransfer.value = item; transferCompletionProof.value = null; transferCompletionDate.value = ''; transferCompletionReference.value = item.payment_reference || ''; transferCompletionVisible.value = true }
function handleTransferCompletionProof(file: UploadFile): void { transferCompletionProof.value = file.raw || null }
function clearTransferCompletionProof(): void { transferCompletionProof.value = null }
async function completeTransfer(): Promise<void> { if (!selectedTransfer.value || !transferCompletionProof.value) { ElMessage.warning('请选择内部转账凭证'); return } workflowSaving.value = true; try { await completeFinanceTransfer(selectedTransfer.value.id, transferCompletionProof.value, transferCompletionDate.value || undefined, transferCompletionReference.value.trim() || undefined); ElMessage.success('内部转付凭证已归档'); transferCompletionVisible.value = false; await loadData() } finally { workflowSaving.value = false } }
async function markTransferFailed(input: unknown): Promise<void> { const item = input as FinanceInternalTransfer; try { const { value } = await ElMessageBox.prompt('填写内部转付失败原因', '标记转付异常', { inputValidator: (text) => Boolean(String(text || '').trim()) || '必须填写原因' }); await failFinanceTransfer(item.id, value.trim()); ElMessage.success('已标记转付异常'); await loadData() } catch { /* 用户取消 */ } }

const ocrVisible = ref(false)
const ocrLoading = ref(false)
const ocrFile = ref<File | null>(null)
const ocrResult = ref<OCRReceiptResult | null>(null)
function openOCRDialog(): void { ocrFile.value = null; ocrResult.value = null; ocrVisible.value = true }
function handleOCRFile(file: UploadFile): void { ocrFile.value = file.raw || null; ocrResult.value = null }
function clearOCRFile(): void { ocrFile.value = null; ocrResult.value = null }
async function recognizeOCRFile(): Promise<void> { if (!ocrFile.value) return; ocrLoading.value = true; try { ocrResult.value = await recognizeReceipt(ocrFile.value); ElMessage.success('识别完成，请核对后带入支出登记') } finally { ocrLoading.value = false } }
function applyOCRToExpense(): void { if (!ocrResult.value || !ocrFile.value) return; const result = ocrResult.value.recognized; openExpenseDialog(); expenseForm.amount = result.amount ? Number(result.amount) : undefined; expenseForm.expense_date = result.expense_date || expenseForm.expense_date; expenseForm.category = (result.category || 'other') as FinanceCategory; expenseForm.title = result.title || ''; expenseForm.purpose = [result.vendor ? `商户：${result.vendor}` : '', result.invoice_number ? `票号：${result.invoice_number}` : ''].filter(Boolean).join('；'); expenseForm.attachment_type = 'invoice'; expenseFile.value = ocrFile.value; ocrVisible.value = false }

const budgetDialogVisible = ref(false)
const budgetSaving = ref(false)
const budgetForm = reactive({ project: undefined as number | undefined, planned_amount: undefined as number | undefined })
function openBudgetDialog(): void { budgetForm.project = filterProject.value && manageableProjects.value.some((item) => item.id === filterProject.value) ? filterProject.value : manageableProjects.value[0]?.id; syncBudgetAmount(); budgetDialogVisible.value = true }
function syncBudgetAmount(): void { const existing = budgetList.value.find((item) => item.project === budgetForm.project); budgetForm.planned_amount = existing ? moneyNumber(existing.planned_amount) : undefined }
async function saveBudget(): Promise<void> { if (!budgetForm.project || budgetForm.planned_amount === undefined) { ElMessage.warning('请选择项目并填写核定预算上限'); return } budgetSaving.value = true; try { const existing = budgetList.value.find((item) => item.project === budgetForm.project); if (existing) await updateFinanceBudget(existing.id, { planned_amount: budgetForm.planned_amount }); else await createFinanceBudget({ project: budgetForm.project, planned_amount: budgetForm.planned_amount }); ElMessage.success('预算上限已保存'); budgetDialogVisible.value = false; await loadData() } finally { budgetSaving.value = false } }

async function handleExport(command: string | number | object): Promise<void> { const format = String(command); if (format !== 'xlsx' && format !== 'pdf') return; const target = resolveFinanceExportTarget(format as FinanceExportFormat, filterProject.value); try { const blob = await exportData(target.type, format, target.projectId, undefined, { event_id: filterEvent.value }); downloadBlob(blob, `${target.type}_${Date.now()}.${format}`); ElMessage.success('导出成功') } catch { /* 请求拦截器已提示 */ } }

watch([perspective, filterProject, filterEvent], () => { void loadTraceSummary() })
watch(workspaceTab, () => { if (workspaceTab.value === 'analysis') todoFilter.value = '' })

onMounted(async () => {
  await loadReferenceData()
  await loadData()
  const action = String(route.query.action || '')
  const expenseId = Number(route.query.expense_id)
  const target = expenseList.value.find((item) => item.id === expenseId)
  if (target && action === 'finance_review' && canReviewExpense(target)) openReviewDialog(target)
  if (target && action === 'finance_payment' && canPayExpense(target)) openPaymentDialog(target)
})
</script>

<style scoped lang="scss">
.finance-ledger-page { display: grid; gap: 14px; }
.workspace-tabs { min-width: 0; }
.workspace-tabs > :deep(.el-tabs__header) { margin-bottom: 14px; }
.status-banner { display: flex; align-items: center; gap: 8px; padding: 10px 14px; color: var(--color-danger); background: var(--color-danger-light, #fdf0f0); border: 1px solid color-mix(in srgb, var(--color-danger) 22%, transparent); border-radius: var(--radius-md); }
.status-banner .el-button { margin-left: auto; }
.workspace-panel { min-width: 0; padding: 18px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.metric-strip { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); margin-bottom: 14px; overflow: hidden; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.metric-strip article { display: grid; gap: 5px; min-width: 0; padding: 15px; }
.metric-strip article + article { border-left: 1px solid var(--color-border-light); }
.metric-strip span { color: var(--color-text-muted); font-size: 11px; }
.metric-strip strong { font-size: 18px; font-variant-numeric: tabular-nums; }
.metric-strip small { color: var(--color-text-muted); font-size: 10px; line-height: 1.45; }
.positive { color: var(--color-success); }
.danger { color: var(--color-danger) !important; }
.panel-heading, .traceability-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-bottom: 14px; }
.panel-heading h2, .traceability-toolbar h2 { margin: 0; font-size: 16px; }
.panel-heading p, .traceability-toolbar p { margin: 4px 0 0; color: var(--color-text-muted); font-size: 12px; }
.todo-panel, .traceability-panel, .flow-panel { margin-bottom: 14px; }
.todo-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; }
.todo-card { display: grid; gap: 5px; min-width: 0; padding: 12px; color: var(--color-text); text-align: left; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: 8px; cursor: pointer; transition: border-color .16s, transform .16s; }
.todo-card:hover, .todo-card.active { border-color: var(--color-primary); transform: translateY(-1px); }
.todo-card span, .todo-card small { overflow: hidden; color: var(--color-text-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.todo-card strong { font-size: 22px; font-variant-numeric: tabular-nums; }
.todo-card--danger strong { color: var(--color-danger); }
.todo-card--warning strong { color: var(--color-warning); }
.todo-card--primary strong { color: var(--color-primary); }
.filter-row { display: grid; grid-template-columns: minmax(170px, .7fr) minmax(190px, .8fr) minmax(260px, 1.5fr) auto; gap: 10px; margin-bottom: 14px; }
.stacked-cell { display: grid; gap: 3px; }
.stacked-cell span { overflow: hidden; color: var(--color-text-muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.tab-actions { display: flex; justify-content: flex-end; margin-bottom: 10px; }
.analysis-grid { display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); gap: 14px; }
.breakdown-list, .project-analysis-list { display: grid; gap: 14px; }
.breakdown-list article, .project-analysis-list article { display: grid; gap: 7px; }
.breakdown-list article > div, .analysis-row-head { display: flex; justify-content: space-between; gap: 12px; font-size: 12px; }
.analysis-row-head span { color: var(--color-text-muted); }
.dialog-form { margin-top: 14px; }
.form-grid { display: grid; gap: 12px; }
.form-grid--2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.form-grid--3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.dialog-form :deep(.el-select), .dialog-form :deep(.el-date-editor), .dialog-form :deep(.el-input-number) { width: 100%; }
.allocation-editor { display: grid; gap: 9px; margin-bottom: 15px; padding: 12px; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: 8px; }
.allocation-editor > header { display: flex; align-items: center; justify-content: space-between; }
.allocation-editor > header div { display: grid; gap: 2px; }
.allocation-editor > header span, .allocation-editor > small { color: var(--color-text-muted); font-size: 11px; }
.allocation-anchor, .allocation-mode { display: grid; grid-template-columns: 112px minmax(240px, 1fr); align-items: center; gap: 10px; }
.allocation-anchor > span, .allocation-mode > span { color: var(--color-text-secondary); font-size: 12px; font-weight: 600; }
.allocation-scope-summary { padding-left: 122px; }
.allocation-row { display: grid; grid-template-columns: minmax(190px, 1.35fr) minmax(100px, .55fr) minmax(150px, 1fr) auto; gap: 8px; }
.upload-tip { color: var(--color-text-muted); font-size: 11px; }
.ocr-result { display: grid; gap: 12px; margin-top: 14px; }
.ocr-result dl { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0; overflow: hidden; border: 1px solid var(--color-border-light); border-radius: 8px; }
.ocr-result dl div { padding: 10px; }
.ocr-result dl div + div { border-left: 1px solid var(--color-border-light); }
.ocr-result dt { color: var(--color-text-muted); font-size: 10px; }
.ocr-result dd { margin: 4px 0 0; overflow: hidden; font-size: 12px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }

@media (max-width: 1180px) {
  .metric-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .metric-strip article:nth-child(4) { border-left: 0; border-top: 1px solid var(--color-border-light); }
  .metric-strip article:nth-child(5), .metric-strip article:nth-child(6) { border-top: 1px solid var(--color-border-light); }
  .todo-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-strip article:nth-child(odd) { border-left: 0; }
  .metric-strip article:nth-child(n + 3) { border-top: 1px solid var(--color-border-light); }
  .todo-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .traceability-toolbar, .panel-heading { align-items: stretch; flex-direction: column; }
  .filter-row, .analysis-grid, .form-grid--2, .form-grid--3 { grid-template-columns: 1fr; }
  .allocation-anchor, .allocation-mode, .allocation-row { grid-template-columns: 1fr; }
  .allocation-scope-summary { padding-left: 0; }
  .ocr-result dl { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ocr-result dl div:nth-child(3) { border-left: 0; border-top: 1px solid var(--color-border-light); }
  .ocr-result dl div:nth-child(4) { border-top: 1px solid var(--color-border-light); }
}
</style>
