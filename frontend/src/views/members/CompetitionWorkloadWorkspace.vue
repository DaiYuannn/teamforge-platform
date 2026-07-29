<template>
  <div class="page-container workload-page">
    <PageHeader :title="pageTitle" :subtitle="pageSubtitle">
      <template #actions>
        <el-button
          v-if="mineMode || !contextReady || canManageEntry"
          type="primary"
          :disabled="!contextReady"
          @click="openWorkItemDialog()"
        >
          {{ mineMode ? '登记我的任务' : '登记成员任务' }}
        </el-button>
        <el-button
          v-if="!mineMode && (!contextReady || canManageEntry)"
          :disabled="!contextReady || eligibleParticipants.length === 0"
          @click="openAssessmentDialog"
        >
          填写有效工作量占比
        </el-button>
      </template>
    </PageHeader>

    <section class="context-panel surface-panel" aria-label="比赛与项目选择">
      <div class="context-panel__copy">
        <span>当前工作区</span>
        <strong>先选择比赛届次，再选择该届比赛中的项目参赛条目</strong>
        <p>同一成员可以在多个比赛或项目中承担不同任务，数据按参赛条目分别保存。</p>
      </div>
      <div class="context-selectors">
        <label>
          <span>比赛届次 <b aria-hidden="true">*</b></span>
          <el-select
            v-model="selectedEventId"
            filterable
            clearable
            placeholder="请选择比赛届次"
            :loading="eventsLoading"
            aria-label="选择比赛届次"
          >
            <el-option
              v-for="event in events"
              :key="event.id"
              :label="eventLabel(event)"
              :value="event.id"
            />
          </el-select>
        </label>
        <label>
          <span>参赛项目 <b aria-hidden="true">*</b></span>
          <el-select
            v-model="selectedCompetitionId"
            filterable
            clearable
            :disabled="!selectedEventId"
            :loading="entriesLoading"
            placeholder="请选择项目参赛条目"
            aria-label="选择项目参赛条目"
          >
            <el-option
              v-for="entry in entries"
              :key="entry.id"
              :label="entryLabel(entry)"
              :value="entry.id"
            />
          </el-select>
        </label>
      </div>
    </section>

    <el-alert
      v-if="loadError"
      title="有效工作量工作区暂时无法加载"
      type="error"
      :closable="false"
      show-icon
      class="load-alert"
    >
      <template #default>
        <el-button link type="primary" @click="retryLoad">重新加载</el-button>
      </template>
    </el-alert>

    <EmptyState
      v-if="!contextReady"
      text="请选择比赛届次和项目"
      description="完成两级选择后，才能登记任务、查看组内占比或处理异议。"
      icon="Trophy"
      accent="#176B73"
    />

    <template v-else>
      <section class="entry-summary surface-panel" aria-label="当前项目工作区摘要">
        <div class="entry-summary__identity">
          <span>{{ selectedEntry?.event_name || selectedEvent?.name }}</span>
          <h2>{{ selectedEntry?.project_name || `项目 ${selectedEntry?.project}` }}</h2>
          <p>
            {{
              [
                selectedEntry?.event_edition || selectedEvent?.edition,
                selectedEntry?.entry_name || `参赛条目 #${selectedEntry?.id}`,
              ].filter(Boolean).join(' · ')
            }}
          </p>
        </div>
        <dl>
          <div>
            <dt>{{ mineMode ? '我的任务' : '全组任务' }}</dt>
            <dd>{{ workItems.length }}</dd>
          </div>
          <div>
            <dt>临近或逾期 DDL</dt>
            <dd>{{ approachingDeadlineCount }}</dd>
          </div>
          <div>
            <dt>已发布版本</dt>
            <dd>{{ publishedAssessments.length }}</dd>
          </div>
          <div>
            <dt>待处理异议</dt>
            <dd>{{ pendingObjectionCount }}</dd>
          </div>
        </dl>
      </section>

      <section v-loading="workspaceLoading" class="workspace-panel surface-panel">
        <el-tabs v-model="activeTab">
          <el-tab-pane :label="mineMode ? '我的任务与 DDL' : '全组任务与 DDL'" name="tasks">
            <div class="pane-heading">
              <div>
                <h3>{{ mineMode ? '我的任务清单' : '参赛队任务清单' }}</h3>
                <p>参考说明只描述任务规模、难点或验收标准，不记录个人实际工时。</p>
              </div>
              <el-button
                v-if="mineMode || canManageEntry"
                type="primary"
                plain
                :disabled="!contextReady"
                @click="openWorkItemDialog()"
              >
                {{ mineMode ? '登记任务' : '登记成员任务' }}
              </el-button>
            </div>

            <el-table
              v-if="workItems.length"
              :data="sortedWorkItems"
              row-key="id"
              table-layout="fixed"
              size="small"
            >
              <el-table-column label="任务" min-width="220">
                <template #default="{ row }">
                  <div class="primary-cell">
                    <strong>{{ row.title }}</strong>
                    <span>{{ row.description || '未填写任务说明' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column
                v-if="!mineMode"
                prop="assignee_name"
                label="任务负责人"
                min-width="120"
              />
              <el-table-column label="DDL" min-width="132">
                <template #default="{ row }">
                  <el-tag :type="deadlineTagType(row as CompetitionWorkItem)" size="small">
                    {{ formatDate(row.deadline) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" min-width="108">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" size="small">
                    {{ row.status_display || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="参考说明" min-width="210" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ row.reference_note || '未填写参考说明' }}
                </template>
              </el-table-column>
              <el-table-column label="协作与验收" min-width="190">
                <template #default="{ row }">
                  <div class="primary-cell task-collaboration">
                    <span>
                      协作者：
                      {{ row.collaborator_names?.join('、') || '无' }}
                    </span>
                    <small>验收人：{{ row.reviewer_name || '未指定' }}</small>
                    <small>
                      子任务：
                      {{ completedSubtaskCount(row as CompetitionWorkItem) }}/{{ row.subtasks?.length || 0 }}
                    </small>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="登记人" min-width="112">
                <template #default="{ row }">
                  {{ row.created_by_name || '—' }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="126" align="right">
                <template #default="{ row }">
                  <template v-if="row.can_manage">
                    <el-button link type="primary" @click="openWorkItemDialog(row as CompetitionWorkItem)">
                      {{ row.can_edit ? '编辑' : '验收' }}
                    </el-button>
                    <el-button
                      v-if="row.can_edit"
                      link
                      type="danger"
                      @click="removeWorkItem(row as CompetitionWorkItem)"
                    >
                      删除
                    </el-button>
                  </template>
                  <span v-else class="muted">仅查看</span>
                </template>
              </el-table-column>
            </el-table>
            <EmptyState
              v-else
              :text="mineMode ? '我在当前参赛项目中还没有任务' : '当前参赛项目还没有任务'"
              description="登记任务和 DDL 后，组内成员可以在同一上下文中查看进展。"
              compact
            >
              <template #action>
                <el-button
                  v-if="mineMode || canManageEntry"
                  type="primary"
                  @click="openWorkItemDialog()"
                >
                  {{ mineMode ? '登记我的第一个任务' : '登记第一个成员任务' }}
                </el-button>
              </template>
            </EmptyState>
          </el-tab-pane>

          <el-tab-pane label="有效工作量占比" name="assessments">
            <div class="pane-heading">
              <div>
                <h3>组内公开的有效工作量</h3>
                <p>已发布版本对本参赛条目成员公开；占比评价工作结果，不按个人耗时长短排名。</p>
              </div>
              <el-button
                v-if="!mineMode && canManageEntry"
                type="primary"
                plain
                :disabled="eligibleParticipants.length === 0"
                @click="openAssessmentDialog"
              >
                保存占比草稿
              </el-button>
            </div>

            <div v-if="visibleAssessments.length" class="assessment-list">
              <article
                v-for="assessment in visibleAssessments"
                :key="assessment.id"
                class="assessment-card"
              >
                <header>
                  <div>
                    <div class="assessment-title">
                      <strong>第 {{ assessment.version }} 版分配</strong>
                      <el-tag :type="assessmentStatusType(assessment)" size="small">
                        {{ assessment.status_display || assessment.status }}
                      </el-tag>
                      <el-tag v-if="assessment.is_current" type="success" effect="plain" size="small">
                        当前版本
                      </el-tag>
                    </div>
                    <p>
                      {{
                        assessment.published_at
                          ? `${assessment.decided_by_name || '负责人'} 发布于 ${formatDateTime(assessment.published_at)}`
                          : `${assessment.decided_by_name || '负责人'} 保存的草稿`
                      }}
                    </p>
                  </div>
                  <div class="assessment-actions">
                    <span>合计 {{ percentageLabel(assessment.allocation_total) }}</span>
                    <el-button
                      v-if="!isPublishedAssessment(assessment) && assessment.can_manage"
                      link
                      type="primary"
                      @click="publishExistingAssessment(assessment)"
                    >
                      发布
                    </el-button>
                  </div>
                </header>
                <p v-if="assessment.decision_note" class="decision-note">
                  评价说明：{{ assessment.decision_note }}
                </p>
                <el-table
                  :data="assessment.allocations"
                  row-key="id"
                  table-layout="fixed"
                  size="small"
                >
                  <el-table-column prop="user_name" label="成员" min-width="150" />
                  <el-table-column label="有效工作量占比" min-width="140">
                    <template #default="{ row }">
                      <strong class="percentage-value">{{ percentageLabel(row.percentage) }}</strong>
                    </template>
                  </el-table-column>
                  <el-table-column label="分配依据" min-width="260">
                    <template #default="{ row }">
                      {{ row.rationale || '未填写分配依据' }}
                    </template>
                  </el-table-column>
                  <el-table-column
                    v-if="isPublishedAssessment(assessment) && assessment.can_object"
                    label="异议"
                    width="94"
                    align="right"
                  >
                    <template #default="{ row }">
                      <el-button
                        link
                        type="warning"
                        @click="openObjectionDialog(row as WorkloadAllocation)"
                      >
                        提出异议
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </article>
            </div>
            <EmptyState
              v-else
              text="当前参赛项目还没有已发布的有效工作量"
              :description="
                canManageEntry
                  ? '负责人可以先保存草稿，合计达到 100% 后再发布。'
                  : '负责人发布后，组内成员可查看完整分配并提出异议。'
              "
              compact
            />
          </el-tab-pane>

          <el-tab-pane :label="`异议处理${pendingObjectionCount ? ` (${pendingObjectionCount})` : ''}`" name="objections">
            <div class="pane-heading">
              <div>
                <h3>有效工作量异议</h3>
                <p>异议与具体分配行关联，处理意见和结果在当前参赛条目内留痕。</p>
              </div>
            </div>
            <el-table
              v-if="objections.length"
              :data="objections"
              row-key="id"
              table-layout="fixed"
              size="small"
            >
              <el-table-column label="涉及成员" min-width="128">
                <template #default="{ row }">
                  {{ row.allocation_user_name || `成员 ${row.allocation_user}` }}
                </template>
              </el-table-column>
              <el-table-column label="提出人" min-width="112">
                <template #default="{ row }">
                  {{ row.raised_by_name || `成员 ${row.raised_by}` }}
                </template>
              </el-table-column>
              <el-table-column prop="reason" label="异议内容" min-width="250" />
              <el-table-column label="状态" min-width="108">
                <template #default="{ row }">
                  <el-tag :type="objectionStatusType(row.status)" size="small">
                    {{ row.status_display || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="处理结果" min-width="220">
                <template #default="{ row }">
                  <div class="primary-cell">
                    <span>{{ row.response || '等待负责人处理' }}</span>
                    <small v-if="row.resolved_by_name">
                      {{ row.resolved_by_name }} · {{ formatDateTime(row.resolved_at) }}
                    </small>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="104" align="right">
                <template #default="{ row }">
                  <el-button
                    v-if="row.can_resolve && isPendingObjection(row as WorkloadObjection)"
                    link
                    type="primary"
                    @click="openResolveDialog(row as WorkloadObjection)"
                  >
                    处理
                  </el-button>
                  <span v-else class="muted">—</span>
                </template>
              </el-table-column>
            </el-table>
            <EmptyState
              v-else
              text="当前参赛项目暂无异议"
              description="成员可在已发布分配的任意一行提出具体异议。"
              compact
            />
          </el-tab-pane>
        </el-tabs>
      </section>
    </template>

    <el-dialog
      v-model="workItemDialogVisible"
      :title="reviewOnly ? '验收任务' : editingWorkItem ? '编辑任务与 DDL' : mineMode ? '登记我的任务与 DDL' : '登记成员任务与 DDL'"
      width="720px"
      append-to-body
      destroy-on-close
    >
      <el-alert
        :title="contextDescription"
        type="info"
        :closable="false"
        class="dialog-context"
      />
      <el-alert
        v-if="reviewOnly"
        title="你是该任务的验收人，只需确认任务状态并填写验收说明；任务负责人、DDL 和分工不会被改动。"
        type="warning"
        :closable="false"
        class="dialog-context"
      />
      <el-form label-position="top">
        <el-form-item v-if="!mineMode && !reviewOnly" label="任务负责人" required>
          <el-select
            v-model="workItemForm.assignee"
            filterable
            placeholder="请选择当前参赛条目成员"
            style="width: 100%"
          >
            <el-option
              v-for="participant in taskAssignableParticipants"
              :key="participant.user"
              :label="participantName(participant)"
              :value="participant.user"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!reviewOnly" label="协作者">
          <el-select
            v-model="workItemForm.collaborators"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="可选择共同完成该任务的参赛成员"
            style="width: 100%"
          >
            <el-option
              v-for="participant in collaboratorOptions"
              :key="participant.user"
              :label="participantName(participant)"
              :value="participant.user"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!reviewOnly" label="任务验收人">
          <el-select
            v-model="workItemForm.reviewer"
            filterable
            clearable
            placeholder="可指定另一位成员验收，负责人不能自审"
            style="width: 100%"
          >
            <el-option
              v-for="participant in reviewerOptions"
              :key="participant.user"
              :label="participantName(participant)"
              :value="participant.user"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!reviewOnly" label="任务名称" required>
          <el-input
            v-model="workItemForm.title"
            maxlength="120"
            show-word-limit
            placeholder="例如：完成答辩演示稿终版"
          />
        </el-form-item>
        <el-form-item v-if="!reviewOnly" label="任务说明">
          <el-input
            v-model="workItemForm.description"
            type="textarea"
            :rows="3"
            maxlength="800"
            show-word-limit
            placeholder="描述交付内容、协作边界或验收条件"
          />
        </el-form-item>
        <el-form-item v-if="!reviewOnly" label="DDL" required>
          <el-date-picker
            v-model="workItemForm.deadline"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择截止日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="!reviewOnly" label="优先级">
          <el-select v-model="workItemForm.priority" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务状态" required>
          <el-select v-model="workItemForm.status" style="width: 100%">
            <el-option label="待开始" value="todo" />
            <el-option label="进行中" value="doing" />
            <el-option label="待验收" value="pending_review" />
            <el-option label="已完成" value="done" />
            <el-option label="暂停" value="paused" />
            <el-option label="需要帮助" value="need_help" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="完成 / 验收说明">
          <el-input
            v-model="workItemForm.completion_note"
            type="textarea"
            :rows="3"
            maxlength="800"
            show-word-limit
            :placeholder="reviewOnly ? '填写验收结论；需要修改时可退回“进行中”' : '提交待验收或完成时，说明实际交付内容'"
          />
        </el-form-item>
        <el-form-item v-if="!reviewOnly" label="参考说明">
          <el-input
            v-model="workItemForm.reference_note"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="例如：需完成 20 页核心内容并通过组内评审；无需填写精细小时数"
          />
        </el-form-item>
        <el-form-item v-if="!reviewOnly" label="子任务与具体负责人">
          <div class="subtask-editor">
            <div
              v-for="(subtask, index) in workItemForm.subtasks"
              :key="subtask.id || `new-${index}`"
              class="subtask-editor__row"
            >
              <el-checkbox v-model="subtask.is_completed" aria-label="子任务是否完成" />
              <el-input
                v-model="subtask.title"
                maxlength="120"
                placeholder="子任务名称"
              />
              <el-select
                v-model="subtask.assignee"
                filterable
                clearable
                placeholder="负责人"
              >
                <el-option
                  v-for="participant in taskAssignableParticipants"
                  :key="participant.user"
                  :label="participantName(participant)"
                  :value="participant.user"
                />
              </el-select>
              <el-button text type="danger" @click="removeSubtask(index)">移除</el-button>
            </div>
            <el-button plain size="small" @click="addSubtask">添加子任务</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="workItemDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingWorkItem" @click="saveWorkItem">
          {{ reviewOnly ? '提交验收结果' : '保存任务' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="assessmentDialogVisible"
      title="填写有效工作量占比"
      width="880px"
      append-to-body
      destroy-on-close
    >
      <el-alert
        :title="`${contextDescription}。指导成员可查看，但不进入占比合计。`"
        type="info"
        :closable="false"
        class="dialog-context"
      />
      <el-form label-position="top">
        <el-form-item label="评价说明">
          <el-input
            v-model="assessmentForm.decision_note"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            placeholder="说明本次占比依据，例如任务质量、实际交付和关键问题解决情况"
          />
        </el-form-item>
      </el-form>
      <div class="allocation-heading">
        <div>
          <strong>参赛成员分配</strong>
          <span>仅比赛负责人和参赛成员参与分配</span>
        </div>
        <span :class="{ invalid: !allocationTotalValid }">
          当前合计 {{ percentageLabel(allocationTotal) }}
        </span>
      </div>
      <el-table
        :data="assessmentForm.allocations"
        row-key="user"
        table-layout="fixed"
        size="small"
        max-height="420"
      >
        <el-table-column prop="user_name" label="成员" min-width="150" />
        <el-table-column label="占比" width="180">
          <template #default="{ row }">
            <el-input-number
              v-model="row.percentage"
              :min="0"
              :max="100"
              :step="1"
              :precision="2"
              controls-position="right"
            />
            <span class="percent-suffix">%</span>
          </template>
        </el-table-column>
        <el-table-column label="分配依据" min-width="340">
          <template #default="{ row }">
            <el-input
              v-model="row.rationale"
              maxlength="300"
              placeholder="写明该成员的有效交付或关键贡献"
            />
          </template>
        </el-table-column>
      </el-table>
      <p v-if="!allocationTotalValid" class="form-warning">
        发布前占比必须合计 100.00%；草稿可以暂未分配完整。
      </p>
      <template #footer>
        <el-button @click="assessmentDialogVisible = false">取消</el-button>
        <el-button :loading="savingAssessment" @click="saveAssessment(false)">
          保存草稿
        </el-button>
        <el-button
          type="primary"
          :loading="savingAssessment"
          :disabled="!allocationTotalValid"
          @click="saveAssessment(true)"
        >
          保存并发布
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="objectionDialogVisible"
      title="提出有效工作量异议"
      width="560px"
      append-to-body
      destroy-on-close
    >
      <el-alert
        v-if="selectedAllocation"
        :title="`针对 ${selectedAllocation.user_name} 的 ${percentageLabel(selectedAllocation.percentage)} 分配提出异议`"
        type="warning"
        :closable="false"
        class="dialog-context"
      />
      <el-form label-position="top">
        <el-form-item label="异议说明" required>
          <el-input
            v-model="objectionForm.reason"
            type="textarea"
            :rows="5"
            maxlength="1000"
            show-word-limit
            placeholder="请具体说明有异议的事实、交付或分配依据"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="objectionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingObjection" @click="submitObjection">
          提交异议
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="resolveDialogVisible"
      title="处理有效工作量异议"
      width="580px"
      append-to-body
      destroy-on-close
    >
      <div v-if="selectedObjection" class="objection-detail">
        <span>{{ selectedObjection.raised_by_name }} 对 {{ selectedObjection.allocation_user_name }} 的分配提出：</span>
        <strong>{{ selectedObjection.reason }}</strong>
      </div>
      <el-form label-position="top">
        <el-form-item label="处理结果" required>
          <el-radio-group v-model="resolveForm.status">
            <el-radio value="resolved">已解决</el-radio>
            <el-radio value="rejected">不予采纳</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理说明" required>
          <el-input
            v-model="resolveForm.response"
            type="textarea"
            :rows="5"
            maxlength="1000"
            show-word-limit
            placeholder="写明核对结果、调整情况或不予采纳的依据"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="resolvingObjection" @click="resolveObjection">
          确认处理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getCompetitionEvents,
  getCompetitionParticipants,
  getCompetitions,
  type CompetitionEvent,
} from '@/api/competitions'
import {
  createCompetitionWorkItem,
  createWorkloadObjection,
  deleteCompetitionWorkItem,
  getCompetitionWorkItems,
  getWorkloadAssessments,
  getWorkloadObjections,
  publishWorkloadAssessment,
  resolveWorkloadObjection,
  saveWorkloadAssessmentDraft,
  updateCompetitionWorkItem,
} from '@/api/workloads'
import { useUserStore } from '@/stores/user'
import type { Competition, CompetitionParticipant } from '@/types'
import type {
  CompetitionSubTask,
  CompetitionWorkItem,
  CompetitionWorkItemInput,
  CompetitionWorkItemStatus,
  WorkloadAllocation,
  WorkloadAssessment,
  WorkloadObjection,
  WorkloadObjectionResolutionStatus,
} from '@/types/workload'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'

const props = defineProps<{
  mode: 'mine' | 'team'
}>()

interface AssessmentAllocationForm {
  user: number
  user_name: string
  percentage: number
  rationale: string
}

const userStore = useUserStore()
const mineMode = computed(() => props.mode === 'mine')
const pageTitle = computed(() => mineMode.value ? '我的任务与工作量' : '团队有效工作量')
const pageSubtitle = computed(() => mineMode.value
  ? '按比赛与项目登记我的任务和 DDL，查看组内公开占比，并对具体分配提出异议。'
  : '按比赛与项目维护全组任务，由负责人发布有效工作量占比并处理组内异议。')

const events = ref<CompetitionEvent[]>([])
const entries = ref<Competition[]>([])
const participants = ref<CompetitionParticipant[]>([])
const selectedEventId = ref<number | null>(null)
const selectedCompetitionId = ref<number | null>(null)
const workItems = ref<CompetitionWorkItem[]>([])
const assessments = ref<WorkloadAssessment[]>([])
const objections = ref<WorkloadObjection[]>([])
const activeTab = ref<'tasks' | 'assessments' | 'objections'>('tasks')
const eventsLoading = ref(false)
const entriesLoading = ref(false)
const workspaceLoading = ref(false)
const loadError = ref(false)
let entriesRequestId = 0
let workspaceRequestId = 0

const workItemDialogVisible = ref(false)
const editingWorkItem = ref<CompetitionWorkItem | null>(null)
const savingWorkItem = ref(false)
const workItemForm = reactive({
  assignee: null as number | null,
  collaborators: [] as number[],
  reviewer: null as number | null,
  title: '',
  description: '',
  deadline: '',
  priority: 'medium' as 'low' | 'medium' | 'high' | 'urgent',
  completion_note: '',
  reference_note: '',
  subtasks: [] as CompetitionSubTask[],
  status: 'todo' as CompetitionWorkItemStatus,
})

const assessmentDialogVisible = ref(false)
const savingAssessment = ref(false)
const assessmentForm = reactive<{
  decision_note: string
  allocations: AssessmentAllocationForm[]
}>({
  decision_note: '',
  allocations: [],
})

const objectionDialogVisible = ref(false)
const selectedAllocation = ref<WorkloadAllocation | null>(null)
const savingObjection = ref(false)
const objectionForm = reactive({ reason: '' })

const resolveDialogVisible = ref(false)
const selectedObjection = ref<WorkloadObjection | null>(null)
const resolvingObjection = ref(false)
const resolveForm = reactive<{
  status: WorkloadObjectionResolutionStatus
  response: string
}>({
  status: 'resolved',
  response: '',
})

const selectedEvent = computed(() =>
  events.value.find((event) => event.id === selectedEventId.value),
)
const selectedEntry = computed(() =>
  entries.value.find((entry) => entry.id === selectedCompetitionId.value),
)
const contextReady = computed(() =>
  Boolean(selectedEventId.value && selectedCompetitionId.value && selectedEntry.value),
)
const contextDescription = computed(() => {
  if (!selectedEntry.value) return '尚未选择比赛与项目'
  return [
    selectedEntry.value.event_name || selectedEvent.value?.name,
    selectedEntry.value.event_edition || selectedEvent.value?.edition,
    selectedEntry.value.project_name || `项目 ${selectedEntry.value.project}`,
    selectedEntry.value.entry_name || `参赛条目 #${selectedEntry.value.id}`,
  ].filter(Boolean).join(' · ')
})
const activeParticipants = computed(() =>
  participants.value.filter((participant) => participant.participation_status !== 'withdrawn'),
)
const taskAssignableParticipants = computed(() =>
  activeParticipants.value.filter((participant) => participant.role !== 'advisor'),
)
const collaboratorOptions = computed(() =>
  taskAssignableParticipants.value.filter(
    (participant) => participant.user !== workItemForm.assignee,
  ),
)
const reviewerOptions = computed(() =>
  taskAssignableParticipants.value.filter(
    (participant) => participant.user !== workItemForm.assignee,
  ),
)
const reviewOnly = computed(() =>
  Boolean(
    editingWorkItem.value
    && !editingWorkItem.value.can_edit
    && editingWorkItem.value.can_review,
  ),
)
const eligibleParticipants = computed(() =>
  activeParticipants.value.filter((participant) =>
    participant.role === 'leader' || participant.role === 'member',
  ),
)
const canManageEntry = computed(() =>
  selectedEntry.value?.can_manage === true
  || assessments.value.some((assessment) => assessment.can_manage),
)
const sortedWorkItems = computed(() =>
  [...workItems.value].sort((left, right) =>
    left.deadline.localeCompare(right.deadline)
    || left.assignee_name.localeCompare(right.assignee_name, 'zh-CN')
    || left.id - right.id,
  ),
)
const publishedAssessments = computed(() =>
  assessments.value.filter(isPublishedAssessment),
)
const visibleAssessments = computed(() => {
  const items = mineMode.value || !canManageEntry.value
    ? publishedAssessments.value
    : assessments.value
  return [...items].sort((left, right) =>
    Number(right.is_current) - Number(left.is_current)
    || right.version - left.version,
  )
})
const currentAssessment = computed(() => {
  const latestDraft = assessments.value
    .filter((assessment) => !isPublishedAssessment(assessment))
    .sort((left, right) => right.version - left.version)[0]
  if (latestDraft) return latestDraft
  return [...assessments.value].sort((left, right) =>
    Number(right.is_current) - Number(left.is_current)
    || right.version - left.version,
  )[0]
})
const allocationTotal = computed(() =>
  assessmentForm.allocations.reduce(
    (total, allocation) => total + Number(allocation.percentage || 0),
    0,
  ),
)
const allocationTotalValid = computed(() =>
  assessmentForm.allocations.length > 0
  && Math.round(allocationTotal.value * 100) === 10000,
)
const approachingDeadlineCount = computed(() =>
  workItems.value.filter((item) => {
    if (isCompletedWorkItem(item)) return false
    const days = dayjs(item.deadline).startOf('day').diff(dayjs().startOf('day'), 'day')
    return days <= 7
  }).length,
)
const pendingObjectionCount = computed(() =>
  objections.value.filter(isPendingObjection).length,
)

function eventLabel(event: CompetitionEvent): string {
  return [event.name, event.edition].filter(Boolean).join(' · ')
}

function entryLabel(entry: Competition): string {
  return [
    entry.project_name || `项目 ${entry.project}`,
    entry.entry_name || `参赛条目 #${entry.id}`,
  ].filter(Boolean).join(' · ')
}

function participantName(participant: CompetitionParticipant): string {
  return participant.user_detail?.name || `成员 ${participant.user}`
}

function formatDate(value?: string | null): string {
  return value && dayjs(value).isValid() ? dayjs(value).format('YYYY-MM-DD') : '—'
}

function formatDateTime(value?: string | null): string {
  return value && dayjs(value).isValid() ? dayjs(value).format('YYYY-MM-DD HH:mm') : '—'
}

function percentageLabel(value: number | string): string {
  const numberValue = Number(value || 0)
  return `${Number.isFinite(numberValue) ? numberValue.toFixed(2) : '0.00'}%`
}

function isCompletedWorkItem(item: CompetitionWorkItem): boolean {
  return Boolean(item.completed_at)
    || ['done', 'completed', 'cancelled'].includes(item.status)
}

function deadlineTagType(
  item: CompetitionWorkItem,
): 'success' | 'warning' | 'danger' | 'info' {
  if (isCompletedWorkItem(item)) return 'success'
  const days = dayjs(item.deadline).startOf('day').diff(dayjs().startOf('day'), 'day')
  if (days < 0) return 'danger'
  if (days <= 7) return 'warning'
  return 'info'
}

function statusTagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (['done', 'completed'].includes(status)) return 'success'
  if (['overdue', 'cancelled', 'need_help'].includes(status)) return 'danger'
  if (['doing', 'in_progress', 'pending_review', 'paused'].includes(status)) return 'warning'
  return 'info'
}

function normalizeWorkItemStatus(status?: string): CompetitionWorkItemStatus {
  return [
    'todo',
    'doing',
    'pending_review',
    'done',
    'paused',
    'cancelled',
    'need_help',
  ].includes(status || '')
    ? status as CompetitionWorkItemStatus
    : 'todo'
}

function completedSubtaskCount(item: CompetitionWorkItem): number {
  return (item.subtasks || []).filter((subtask) => subtask.is_completed).length
}

function isPublishedAssessment(assessment: WorkloadAssessment): boolean {
  return assessment.status === 'published' || Boolean(assessment.published_at)
}

function assessmentStatusType(
  assessment: WorkloadAssessment,
): 'success' | 'warning' | 'info' {
  if (isPublishedAssessment(assessment)) return 'success'
  if (assessment.status === 'draft') return 'warning'
  return 'info'
}

function isPendingObjection(objection: WorkloadObjection): boolean {
  return !['resolved', 'rejected'].includes(objection.status)
}

function objectionStatusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'resolved') return 'success'
  if (status === 'rejected') return 'danger'
  if (status === 'open' || status === 'pending') return 'warning'
  return 'info'
}

function clearWorkspace(): void {
  workItems.value = []
  assessments.value = []
  objections.value = []
  participants.value = []
}

async function loadEvents(): Promise<void> {
  eventsLoading.value = true
  loadError.value = false
  try {
    const response = await getCompetitionEvents({ page: 1, page_size: 100 })
    events.value = response.results
  } catch {
    loadError.value = true
  } finally {
    eventsLoading.value = false
  }
}

async function loadEntries(eventId: number): Promise<void> {
  const requestId = ++entriesRequestId
  entriesLoading.value = true
  loadError.value = false
  try {
    const response = await getCompetitions({
      event: eventId,
      page: 1,
      page_size: 100,
    })
    if (requestId !== entriesRequestId || selectedEventId.value !== eventId) return
    entries.value = response.results
  } catch {
    if (requestId === entriesRequestId) loadError.value = true
  } finally {
    if (requestId === entriesRequestId) entriesLoading.value = false
  }
}

async function loadWorkspace(competitionId: number): Promise<void> {
  const requestId = ++workspaceRequestId
  workspaceLoading.value = true
  loadError.value = false
  try {
    const [items, assessmentItems, objectionItems, participantItems] = await Promise.all([
      getCompetitionWorkItems({
        competition: competitionId,
        ...(mineMode.value ? { mine: 1 as const } : {}),
      }),
      getWorkloadAssessments(competitionId),
      getWorkloadObjections(competitionId),
      getCompetitionParticipants(competitionId),
    ])
    if (
      requestId !== workspaceRequestId
      || selectedCompetitionId.value !== competitionId
    ) return
    workItems.value = items
    assessments.value = assessmentItems
    objections.value = objectionItems
    participants.value = participantItems
  } catch {
    if (requestId === workspaceRequestId) loadError.value = true
  } finally {
    if (requestId === workspaceRequestId) workspaceLoading.value = false
  }
}

async function retryLoad(): Promise<void> {
  if (!events.value.length) {
    await loadEvents()
    return
  }
  if (selectedCompetitionId.value) {
    await loadWorkspace(selectedCompetitionId.value)
    return
  }
  if (selectedEventId.value) await loadEntries(selectedEventId.value)
}

async function refreshWorkspace(): Promise<void> {
  if (selectedCompetitionId.value) await loadWorkspace(selectedCompetitionId.value)
}

function openWorkItemDialog(item?: CompetitionWorkItem): void {
  if (!contextReady.value) return
  if (!mineMode.value && !canManageEntry.value && !item?.can_manage) return
  editingWorkItem.value = item || null
  Object.assign(workItemForm, {
    assignee: item?.assignee
      ?? (mineMode.value ? userStore.userInfo?.id ?? null : null),
    title: item?.title || '',
    description: item?.description || '',
    deadline: item?.deadline ? formatDate(item.deadline) : '',
    collaborators: [...(item?.collaborators || [])],
    reviewer: item?.reviewer ?? null,
    priority: item?.priority || 'medium',
    completion_note: item?.completion_note || '',
    reference_note: item?.reference_note || '',
    subtasks: (item?.subtasks || []).map((subtask, index) => ({
      id: subtask.id,
      title: subtask.title,
      assignee: subtask.assignee ?? null,
      assignee_name: subtask.assignee_name,
      is_completed: subtask.is_completed,
      completed_at: subtask.completed_at,
      sort_order: subtask.sort_order ?? index,
    })),
    status: normalizeWorkItemStatus(item?.status),
  })
  workItemDialogVisible.value = true
}

async function saveWorkItem(): Promise<void> {
  const competition = selectedCompetitionId.value
  if (!competition) {
    ElMessage.warning('请先选择比赛届次和项目')
    return
  }
  if (!workItemForm.title.trim() || !workItemForm.deadline) {
    ElMessage.warning('请填写任务名称和 DDL')
    return
  }
  if (!mineMode.value && !workItemForm.assignee) {
    ElMessage.warning('请选择执行成员')
    return
  }

  if (reviewOnly.value) {
    if (!editingWorkItem.value) return
    savingWorkItem.value = true
    try {
      await updateCompetitionWorkItem(editingWorkItem.value.id, {
        status: workItemForm.status,
        completion_note: workItemForm.completion_note.trim(),
      })
      ElMessage.success('任务验收状态已更新')
      workItemDialogVisible.value = false
      await refreshWorkspace()
    } finally {
      savingWorkItem.value = false
    }
    return
  }

  const payload: CompetitionWorkItemInput = {
    competition,
    ...(workItemForm.assignee ? { assignee: workItemForm.assignee } : {}),
    collaborators: [...workItemForm.collaborators],
    reviewer: workItemForm.reviewer,
    title: workItemForm.title.trim(),
    description: workItemForm.description.trim(),
    deadline: dayjs(workItemForm.deadline).endOf('day').format(),
    priority: workItemForm.priority,
    completion_note: workItemForm.completion_note.trim(),
    reference_note: workItemForm.reference_note.trim(),
    subtasks: workItemForm.subtasks
      .filter((subtask) => subtask.title.trim())
      .map((subtask, index) => ({
        ...(subtask.id ? { id: subtask.id } : {}),
        title: subtask.title.trim(),
        assignee: subtask.assignee,
        is_completed: subtask.is_completed,
        sort_order: index,
      })),
    status: workItemForm.status,
  }
  savingWorkItem.value = true
  try {
    if (editingWorkItem.value) {
      await updateCompetitionWorkItem(editingWorkItem.value.id, payload)
      ElMessage.success('任务与 DDL 已更新')
    } else {
      await createCompetitionWorkItem(payload)
      ElMessage.success('任务与 DDL 已登记')
    }
    workItemDialogVisible.value = false
    await refreshWorkspace()
  } finally {
    savingWorkItem.value = false
  }
}

function addSubtask(): void {
  workItemForm.subtasks.push({
    title: '',
    assignee: workItemForm.assignee,
    is_completed: false,
    sort_order: workItemForm.subtasks.length,
  })
}

function removeSubtask(index: number): void {
  workItemForm.subtasks.splice(index, 1)
}

async function removeWorkItem(item: CompetitionWorkItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除任务“${item.title}”吗？`,
      '删除任务',
      { type: 'warning' },
    )
    await deleteCompetitionWorkItem(item.id)
    ElMessage.success('任务已删除')
    await refreshWorkspace()
  } catch {
    // 用户取消或统一请求拦截器已处理错误。
  }
}

function openAssessmentDialog(): void {
  if (!contextReady.value || !canManageEntry.value) return
  if (!eligibleParticipants.value.length) {
    ElMessage.warning('当前参赛条目没有可参与占比分配的负责人或成员')
    return
  }
  const source = currentAssessment.value
  const sourceByUser = new Map(
    (source?.allocations || []).map((allocation) => [allocation.user, allocation]),
  )
  assessmentForm.decision_note = source?.decision_note || ''
  assessmentForm.allocations = eligibleParticipants.value.map((participant) => {
    const existing = sourceByUser.get(participant.user)
    return {
      user: participant.user,
      user_name: existing?.user_name || participantName(participant),
      percentage: Number(existing?.percentage || 0),
      rationale: existing?.rationale || '',
    }
  })
  assessmentDialogVisible.value = true
}

async function saveAssessment(publishAfterSave: boolean): Promise<void> {
  const competition = selectedCompetitionId.value
  if (!competition) {
    ElMessage.warning('请先选择比赛届次和项目')
    return
  }
  if (!assessmentForm.allocations.length) {
    ElMessage.warning('当前没有可参与分配的参赛成员')
    return
  }
  if (publishAfterSave && !allocationTotalValid.value) {
    ElMessage.warning('发布前占比必须合计 100.00%')
    return
  }

  savingAssessment.value = true
  try {
    const draft = await saveWorkloadAssessmentDraft({
      competition,
      decision_note: assessmentForm.decision_note.trim(),
      allocations: assessmentForm.allocations.map((allocation) => ({
        user: allocation.user,
        percentage: Number(Number(allocation.percentage || 0).toFixed(2)),
        rationale: allocation.rationale.trim(),
      })),
    })
    if (publishAfterSave) {
      await publishWorkloadAssessment(draft.id)
      ElMessage.success('有效工作量占比已发布并对组内公开')
    } else {
      ElMessage.success('占比草稿已保存')
    }
    assessmentDialogVisible.value = false
    await refreshWorkspace()
  } finally {
    savingAssessment.value = false
  }
}

async function publishExistingAssessment(assessment: WorkloadAssessment): Promise<void> {
  if (Math.round(Number(assessment.allocation_total || 0) * 100) !== 10000) {
    ElMessage.warning('发布前占比必须合计 100.00%')
    return
  }
  try {
    await ElMessageBox.confirm(
      '发布后，本参赛条目成员将看到完整分配与评价说明。确定发布吗？',
      '发布有效工作量',
      { type: 'warning' },
    )
    await publishWorkloadAssessment(assessment.id)
    ElMessage.success('有效工作量占比已发布')
    await refreshWorkspace()
  } catch {
    // 用户取消或统一请求拦截器已处理错误。
  }
}

function openObjectionDialog(allocation: WorkloadAllocation): void {
  selectedAllocation.value = allocation
  objectionForm.reason = ''
  objectionDialogVisible.value = true
}

async function submitObjection(): Promise<void> {
  if (!selectedAllocation.value) return
  if (!objectionForm.reason.trim()) {
    ElMessage.warning('请填写具体异议说明')
    return
  }
  savingObjection.value = true
  try {
    await createWorkloadObjection({
      allocation: selectedAllocation.value.id,
      reason: objectionForm.reason.trim(),
    })
    ElMessage.success('异议已提交')
    objectionDialogVisible.value = false
    activeTab.value = 'objections'
    await refreshWorkspace()
  } finally {
    savingObjection.value = false
  }
}

function openResolveDialog(objection: WorkloadObjection): void {
  selectedObjection.value = objection
  resolveForm.status = 'resolved'
  resolveForm.response = objection.response || ''
  resolveDialogVisible.value = true
}

async function resolveObjection(): Promise<void> {
  if (!selectedObjection.value) return
  if (!resolveForm.response.trim()) {
    ElMessage.warning('请填写处理说明')
    return
  }
  resolvingObjection.value = true
  try {
    await resolveWorkloadObjection(selectedObjection.value.id, {
      status: resolveForm.status,
      response: resolveForm.response.trim(),
    })
    ElMessage.success('异议处理结果已保存')
    resolveDialogVisible.value = false
    await refreshWorkspace()
  } finally {
    resolvingObjection.value = false
  }
}

watch(
  () => workItemForm.assignee,
  (assignee) => {
    if (!assignee) return
    workItemForm.collaborators = workItemForm.collaborators.filter(
      (userId) => userId !== assignee,
    )
    if (workItemForm.reviewer === assignee) {
      workItemForm.reviewer = null
    }
  },
)

watch(selectedEventId, (eventId) => {
  entriesRequestId += 1
  workspaceRequestId += 1
  selectedCompetitionId.value = null
  entries.value = []
  clearWorkspace()
  loadError.value = false
  if (eventId) loadEntries(eventId)
})

watch(selectedCompetitionId, (competitionId) => {
  workspaceRequestId += 1
  clearWorkspace()
  loadError.value = false
  if (competitionId) loadWorkspace(competitionId)
})

onMounted(loadEvents)
</script>

<style lang="scss" scoped>
.workload-page {
  display: flex;
  max-width: 1480px;
  min-width: 0;
  margin: 0 auto;
  flex-direction: column;
  gap: 16px;
}

.surface-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.context-panel {
  display: flex;
  padding: 18px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.context-panel__copy {
  display: grid;
  min-width: 0;
  gap: 3px;

  > span,
  p {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  strong {
    color: var(--color-text);
    font-size: 15px;
  }
}

.context-selectors {
  display: grid;
  width: min(700px, 56%);
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 12px;

  label {
    display: grid;
    gap: 6px;

    > span {
      color: var(--color-text-regular);
      font-size: 12px;
      font-weight: 600;
    }

    b {
      color: var(--color-danger);
    }
  }

  :deep(.el-select) {
    width: 100%;
  }
}

.load-alert {
  flex: 0 0 auto;
}

.entry-summary {
  display: flex;
  padding: 16px 18px;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
}

.entry-summary__identity {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;

  span,
  p {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  h2 {
    margin: 3px 0;
    color: var(--color-text);
    font-size: 19px;
  }
}

.entry-summary dl {
  display: grid;
  min-width: 480px;
  grid-template-columns: repeat(4, minmax(100px, 1fr));

  > div {
    padding: 2px 16px;
    text-align: right;
    border-left: 1px solid var(--color-border-light);
  }

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin: 3px 0 0;
    color: var(--color-text);
    font-size: 22px;
    font-weight: 650;
    font-variant-numeric: tabular-nums;
  }
}

.workspace-panel {
  min-height: 420px;
  padding: 6px 18px 18px;
}

.workspace-panel :deep(.el-tabs__header) {
  margin-bottom: 10px;
}

.pane-heading {
  display: flex;
  min-height: 60px;
  padding: 4px 0 14px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  h3 {
    color: var(--color-text);
    font-size: 16px;
  }

  p {
    margin-top: 4px;
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.primary-cell {
  display: grid;
  min-width: 0;
  gap: 3px;

  strong,
  span,
  small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span,
  small {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}

.assessment-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.assessment-card {
  overflow: hidden;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  > header {
    display: flex;
    padding: 13px 15px;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    background: var(--color-surface-subtle);
    border-bottom: 1px solid var(--color-border-light);

    p {
      margin-top: 4px;
      color: var(--color-text-muted);
      font-size: 12px;
    }
  }
}

.assessment-title,
.assessment-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.assessment-actions {
  justify-content: flex-end;

  > span {
    color: var(--color-text-regular);
    font-size: 13px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
}

.decision-note {
  margin: 12px 15px 0;
  padding: 10px 12px;
  color: var(--color-text-regular);
  font-size: 12px;
  line-height: 1.6;
  background: var(--color-surface-subtle);
  border-radius: var(--radius-sm);
}

.percentage-value {
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

.dialog-context {
  margin-bottom: 16px;
}

.subtask-editor {
  display: grid;
  width: 100%;
  gap: 8px;
}

.subtask-editor__row {
  display: grid;
  grid-template-columns: auto minmax(180px, 1fr) minmax(140px, 0.65fr) auto;
  align-items: center;
  gap: 8px;
}

.allocation-heading {
  display: flex;
  margin: 6px 0 10px;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;

  > div {
    display: grid;
    gap: 3px;

    span {
      color: var(--color-text-muted);
      font-size: 12px;
    }
  }

  > span {
    color: var(--color-success);
    font-size: 13px;
    font-weight: 650;
    font-variant-numeric: tabular-nums;
  }

  > span.invalid {
    color: var(--color-warning);
  }
}

.percent-suffix {
  margin-left: 5px;
  color: var(--color-text-muted);
}

.form-warning {
  margin-top: 10px;
  color: var(--color-warning);
  font-size: 12px;
}

.objection-detail {
  display: grid;
  margin-bottom: 16px;
  padding: 12px 14px;
  gap: 5px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  strong {
    color: var(--color-text);
    font-size: 13px;
    line-height: 1.6;
  }
}

@media screen and (max-width: 980px) {
  .context-panel,
  .entry-summary {
    align-items: flex-start;
    flex-direction: column;
  }

  .context-selectors,
  .entry-summary dl {
    width: 100%;
    min-width: 0;
  }

  .entry-summary dl > div:first-child {
    padding-left: 0;
    border-left: 0;
  }
}

@media screen and (max-width: 680px) {
  .context-selectors {
    grid-template-columns: minmax(0, 1fr);
  }

  .entry-summary dl {
    grid-template-columns: repeat(2, minmax(0, 1fr));

    > div {
      padding: 10px 12px;
      text-align: left;
      border-left: 0;
      border-top: 1px solid var(--color-border-light);
    }
  }

  .pane-heading,
  .assessment-card > header,
  .allocation-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .workspace-panel {
    padding-inline: 12px;
  }

  .subtask-editor__row {
    grid-template-columns: auto minmax(0, 1fr) auto;

    :deep(.el-select) {
      grid-column: 2 / -1;
      width: 100%;
    }
  }
}
</style>
