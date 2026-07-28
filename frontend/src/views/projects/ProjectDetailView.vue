<template>
  <div class="page-container project-detail-page">
    <section v-loading="loading" class="project-summary" aria-label="项目摘要">
      <div class="summary-toolbar">
        <el-button class="back-button" :icon="ArrowLeft" text @click="$router.back()">返回项目列表</el-button>
        <div class="summary-actions">
          <el-button
            :icon="Operation"
            @click="openProjectOperations"
          >
            协作工作台
          </el-button>
          <el-button
            v-if="canManageProjectWorkflow"
            :icon="EditPen"
            :disabled="!project || project.status === 'closed'"
            @click="openLeaderUpdate"
          >
            更新项目进度
          </el-button>
          <el-button
            v-if="!isExternalCollaborator"
            type="primary"
            :icon="Download"
            :loading="exportingReport"
            @click="handleExportReport"
          >
            导出报告
          </el-button>
        </div>
      </div>

      <div class="summary-identity">
        <div class="summary-title-block">
          <div class="summary-kicker">
            <span>{{ project?.code || 'PROJECT' }}</span>
            <el-tag
              v-if="project"
              :type="getProjectStatusTagType(project.status) as any"
              size="small"
              effect="light"
            >
              {{ getProjectStatusLabel(project.status) }}
            </el-tag>
          </div>
          <h1>{{ project?.name || '项目详情' }}</h1>
          <p>{{ project?.intro || '暂无项目描述' }}</p>
        </div>
      </div>

      <div class="summary-grid">
        <div class="summary-metric">
          <span>项目负责人</span>
          <strong>{{ project?.leader_names?.join('、') || project?.leader_name || '-' }}</strong>
          <small class="leader-update-copy">{{ leaderUpdateSummary }}</small>
        </div>
        <div class="summary-metric">
          <span>当前阶段</span>
          <strong>{{ project?.current_stage_display || getStageLabel(project?.current_stage || '') || '-' }}</strong>
        </div>
        <div class="summary-metric">
          <span>优先级</span>
          <el-tag :type="projectPriority.type as any" size="small" effect="plain">
            {{ projectPriority.label }}
          </el-tag>
        </div>
        <div class="summary-metric risk-metric">
          <span>进度风险</span>
          <el-tag :type="projectRisk.type as any" size="small" effect="plain">
            {{ projectRisk.label }}
          </el-tag>
          <small>{{ projectRisk.detail }}</small>
        </div>
        <div class="summary-metric">
          <span>计划周期</span>
          <strong class="tabular-nums">{{ projectPlanRange }}</strong>
        </div>
        <div class="summary-metric">
          <span>项目成员</span>
          <strong>{{ projectMemberCount }} 人</strong>
        </div>
      </div>
    </section>

    <div class="detail-workspace">
      <nav class="project-section-nav" aria-label="项目详情栏目">
        <div v-for="group in projectSections" :key="group.label" class="section-nav-group">
          <p class="section-nav-label">{{ group.label }}</p>
          <button
            v-for="item in group.items"
            v-show="
              (!item.roles || item.roles.includes(userStore.role))
              && (!item.internalOnly || !isExternalCollaborator)
            "
            :key="item.name"
            class="section-nav-item"
            :class="{ 'is-active': activeTab === item.name }"
            type="button"
            :aria-current="activeTab === item.name ? 'page' : undefined"
            @click="handleTabSelect(item.name)"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </button>
        </div>
      </nav>

      <main class="detail-content">
        <el-tabs v-model="activeTab" class="detail-tabs">
      <el-tab-pane label="档案" name="profile">
        <div v-loading="loading" class="pane-section">
          <div class="pane-heading">
            <h2>项目档案</h2>
          </div>
          <el-descriptions :column="descriptionColumns" border>
            <el-descriptions-item label="项目编号">{{ project?.code }}</el-descriptions-item>
            <el-descriptions-item label="项目名称">{{ project?.name }}</el-descriptions-item>
            <el-descriptions-item label="项目牵头 / 共同负责人">
              {{ project?.leader_names?.join('、') || project?.leader_name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="关联小组">
              {{ project?.team_names?.join('、') || '未限定小组' }}
            </el-descriptions-item>
            <el-descriptions-item label="可见范围">
              {{ project?.visibility_display || '全团队' }}
            </el-descriptions-item>
            <el-descriptions-item label="当前阶段">
              <el-tag type="info" effect="plain" size="small">
                {{ project?.current_stage_display || getStageLabel(project?.current_stage || '') }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="开始日期">{{ formatDate(project?.start_date) }}</el-descriptions-item>
            <el-descriptions-item label="预计结束">{{ formatDate(project?.planned_end_date) }}</el-descriptions-item>
            <el-descriptions-item label="项目描述" :span="2">{{ project?.intro || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div class="subsection-heading">
            <h3>项目成员</h3>
            <div class="heading-actions">
              <span>{{ activeMemberCount }} 人参与中</span>
              <el-button
                v-if="canManageProjectWorkflow"
                type="primary"
                size="small"
                @click="openAddMember"
              >
                添加成员
              </el-button>
            </div>
          </div>
          <el-table :data="members" border size="small">
            <el-table-column prop="user_detail" label="姓名" width="120">
              <template #default="{ row }">{{ row.user_detail?.name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="role_in_project" label="项目角色" width="150">
              <template #default="{ row }">
                {{ row.role_in_project_display || getProjectRoleLabel(row.role_in_project) }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="参与状态" width="100">
              <template #default="{ row }">
                <el-tag :type="projectMemberStatusType(row.status)" size="small">
                  {{ row.status_display || projectMemberStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="joined_at" label="加入时间">
              <template #default="{ row }">{{ formatDate(row.joined_at) }}</template>
            </el-table-column>
            <el-table-column v-if="canManageProjectWorkflow" label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" link @click="openEditMember(row as ProjectMember)">管理</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="阶段" name="stage">
        <div class="pane-section">
          <div class="pane-heading">
            <h2>阶段进度</h2>
          </div>
          <el-alert
            v-if="stageActionError"
            class="workflow-action-error"
            :title="stageActionError"
            type="error"
            :closable="false"
            show-icon
          />
          <StageStepper
            v-if="project"
            :current-stage="project.current_stage || 1"
            :project-status="project.status"
            :stage-logs="stageLogs"
            :can-manage="canManageProjectWorkflow"
            :submitting="stageSubmitting"
            @advance="handleAdvanceStage"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="任务" name="task">
        <div class="pane-section pane-section-wide">
          <div class="pane-heading">
            <h2>任务执行</h2>
            <div class="pane-heading-actions">
              <span>{{ tasks.length }} 项任务</span>
              <el-button type="primary" link @click="() => openProjectTasks()">在任务中心管理</el-button>
            </div>
          </div>
          <TaskBoard
            :tasks="tasks"
            :can-change-status="canChangeTaskStatus"
            :can-change-to-status="canChangeTaskToStatus"
            @change-status="handleTaskStatusChange"
            @task-click="handleTaskClick"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="比赛" name="competition">
        <div class="pane-section">
          <div class="pane-heading">
            <h2>关联比赛</h2>
            <el-button type="primary" link @click="openProjectCompetitions">查看全部比赛</el-button>
          </div>
          <div v-loading="competitionLoading">
            <el-empty v-if="!competitionInfo" description="暂无关联比赛数据" />
            <el-descriptions v-else :column="descriptionColumns" border>
              <el-descriptions-item label="比赛名称">{{ competitionInfo?.name || '暂无数据' }}</el-descriptions-item>
              <el-descriptions-item label="比赛级别">
                <el-tag
                  :type="getCompetitionStageTagType(competitionInfo?.level || '') as any"
                  size="small"
                  effect="light"
                  :style="getCompetitionStageTagStyle(competitionInfo?.level || '')"
                >
                  {{ competitionInfo?.level_display || getCompetitionLevelLabel(competitionInfo?.level || '') }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="主办方">{{ competitionInfo?.organizer || '暂无数据' }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="getCompetitionStatusTagType(competitionInfo?.status || '') as any" size="small">
                  {{ competitionInfo?.status_display || getCompetitionStatusLabel(competitionInfo?.status || '') }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="报名日期">{{ competitionInfo?.register_date ? formatDate(competitionInfo.register_date) : '暂无数据' }}</el-descriptions-item>
              <el-descriptions-item label="答辩日期">{{ competitionInfo?.defense_date ? formatDate(competitionInfo.defense_date) : '暂无数据' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="!isExternalCollaborator" label="经费" name="finance">
        <div class="pane-section pane-section-wide">
          <div class="pane-heading">
            <h2>项目经费</h2>
            <div class="pane-heading-actions">
              <span>{{ expenses.length }} 条支出记录</span>
              <el-button type="primary" link @click="() => openProjectFinance()">打开经费台账</el-button>
            </div>
          </div>
          <FinanceTable
            :expenses="expenses"
            :total-budget="totalBudget"
            :show-actions="canManageProjectWorkflow"
            @edit="handleEditExpense"
            @delete="handleDeleteExpense"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="文件" name="file">
        <div class="pane-section pane-section-wide">
          <div class="pane-heading">
            <h2>项目文件</h2>
            <span>{{ files.length }} 个文件</span>
          </div>
          <FileUploader
            v-if="project"
            :project-id="project.id"
            @success="loadFiles"
          />
          <el-divider />
          <el-table :data="files" border size="small">
            <el-table-column prop="name" label="文件名" min-width="200" show-overflow-tooltip />
            <el-table-column prop="content_type" label="类型" width="80" />
            <el-table-column prop="size" label="大小" width="100">
              <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
            </el-table-column>
            <el-table-column prop="level" label="级别" width="100">
              <template #default="{ row }">
                <el-tag :type="FILE_LEVEL_MAP[row.level]?.tagType as any" size="small">
                  {{ row.level_display || FILE_LEVEL_MAP[row.level]?.label || row.level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="uploader_name" label="上传者" width="100" />
            <el-table-column prop="created_at" label="上传时间" width="120">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" link @click="handleDownload(row as FileAsset)">下载</el-button>
                <el-button v-permission="['teacher', 'sys_admin']" type="danger" link @click="handleDeleteFile(row as FileAsset)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="成果与知识产权" name="ip">
        <div class="pane-section">
          <div class="pane-heading">
            <h2>成果与知识产权</h2>
          </div>
          <div class="project-link-panel">
            <div>
              <strong>从项目档案进入完整责任链</strong>
              <p>查看本项目的软件著作权、专利等申请，继续处理责任分工、材料版本、退回、异议、证书与归档。</p>
            </div>
            <div class="project-link-actions">
              <el-button type="primary" @click="openProjectIP">查看项目成果</el-button>
              <el-button v-if="canManageProjectWorkflow" @click="createProjectIP">新建申请</el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="成员排序" name="ranking">
        <div class="pane-section pane-section-wide">
          <div class="pane-heading">
            <h2>成员排序与异议</h2>
            <div class="pane-heading-actions">
              <el-button type="primary" link @click="openProjectContributions">查看项目贡献</el-button>
              <el-button
                v-if="canManageProjectWorkflow"
                type="primary"
                link
                @click="openProjectContributionReviews"
              >
                审核项目贡献
              </el-button>
            </div>
          </div>
          <div class="ranking-header">
            <h3>成员排序</h3>
            <div class="ranking-actions">
              <el-input
                v-model="rankingPeriod"
                placeholder="统计周期，如 2026-07"
                class="ranking-period"
              />
              <el-button
                v-if="isProjectLeader"
                type="primary"
                :icon="Sort"
                @click="handleGenerateRanking"
              >
                生成排序
              </el-button>
              <el-button
                v-permission="['teacher', 'sys_admin']"
                type="success"
                @click="handleConfirmRanking"
              >
                确认排序
              </el-button>
              <el-button :icon="Download" @click="handleExportReport">导出报告</el-button>
            </div>
          </div>

          <el-table v-loading="rankingLoading" :data="displayRankings" border size="small">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="ranking-evidence">
                  <el-descriptions :column="3" border size="small">
                    <el-descriptions-item label="统计周期">{{ row.period }}</el-descriptions-item>
                    <el-descriptions-item label="规则版本">{{ row.rule_version || '历史规则' }}</el-descriptions-item>
                    <el-descriptions-item label="证据条数">{{ row.score_snapshot?.evidence_count ?? '-' }}</el-descriptions-item>
                    <el-descriptions-item label="实际项目">
                      {{ row.score_snapshot?.breakdown?.actual_project || '0.00' }}
                    </el-descriptions-item>
                    <el-descriptions-item label="资源贡献">
                      {{ row.score_snapshot?.breakdown?.resource || '0.00' }}
                    </el-descriptions-item>
                    <el-descriptions-item label="管理责任">
                      {{ row.score_snapshot?.breakdown?.management || '0.00' }}
                    </el-descriptions-item>
                  </el-descriptions>
                  <p>每条已审核贡献只计分一次；规则和证据在生成时固化，确认后不可覆盖。</p>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="排名" width="100">
              <template #default="{ row }">
                <el-input-number
                  v-if="isProjectLeader && row.status !== 'confirmed'"
                  v-model="row.rank"
                  :min="1"
                  size="small"
                  controls-position="right"
                  style="width: 90px"
                  @change="handleRankChange(row as any)"
                />
                <span v-else>{{ row.rank }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="user_detail" label="成员" width="120">
              <template #default="{ row }">{{ row.user_detail?.name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="total_score" label="得分" width="100" align="center" />
            <el-table-column prop="contribution_count" label="贡献数" width="90" align="center">
              <template #default="{ row }">{{ row.score_snapshot?.evidence_count ?? '-' }}</template>
            </el-table-column>
            <el-table-column prop="task_completed_count" label="任务完成数" width="110" align="center" />
            <el-table-column prop="ip_contribution_count" label="IP贡献数" width="100" align="center" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="RANKING_STATUS_MAP[row.status]?.tagType as any" size="small">
                  {{ RANKING_STATUS_MAP[row.status]?.label || row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <el-divider />

          <div class="ranking-header">
            <h3>排序异议</h3>
            <el-tooltip
              content="排名确认并公开后可提交异议"
              placement="top"
              :disabled="publicRankings.length > 0"
            >
              <span>
                <el-button
                  type="warning"
                  :icon="ChatDotRound"
                  :disabled="publicRankings.length === 0"
                  @click="handleOpenObjection"
                >
                  提交异议
                </el-button>
              </span>
            </el-tooltip>
          </div>
          <el-table :data="objections" border size="small">
            <el-table-column prop="objector_name" label="异议人" width="100" />
            <el-table-column prop="ranking_user_name" label="异议对象" width="100">
              <template #default="{ row }">{{ row.ranking_user_name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="OBJECTION_STATUS_MAP[row.status]?.tagType as any" size="small">
                  {{ OBJECTION_STATUS_MAP[row.status]?.label || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button
                  v-if="isProjectLeader && row.status === 'pending'"
                  type="primary"
                  link
                  @click="handleReviewObjection(row as any, 'leader')"
                >
                  负责人初审
                </el-button>
                <el-button
                  v-permission="['teacher', 'sys_admin']"
                  v-if="row.status === 'leader_reviewed'"
                  type="success"
                  link
                  @click="handleReviewObjection(row as any, 'teacher')"
                >
                  老师确认
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="时间线" name="timeline">
        <div class="pane-section">
          <div class="pane-heading">
            <h2>项目时间线</h2>
          </div>
          <ProjectTimeline :key="timelineRefreshKey" :project-id="projectId" />
        </div>
      </el-tab-pane>

      <el-tab-pane
        v-if="userStore.isTeacher || userStore.isAdmin"
        label="操作审计"
        name="audit"
      >
        <div class="pane-section">
          <div class="pane-heading">
            <h2>项目操作审计</h2>
          </div>
          <div class="project-link-panel">
            <div>
              <strong>按项目定位操作记录</strong>
              <p>跳转到审计中心后将按当前项目接口路径筛选，可继续限定模块、操作人和时间范围并导出。</p>
            </div>
            <el-button type="primary" @click="openProjectAudit">查看项目日志</el-button>
          </div>
        </div>
      </el-tab-pane>
        </el-tabs>
      </main>
    </div>

    <!-- 项目负责人周期更新 -->
    <el-dialog
      v-model="leaderUpdateDialogVisible"
      title="更新项目进度"
      width="520px"
      destroy-on-close
    >
      <div class="leader-update-context">
        <strong>负责人更新周期：每 11 天一次</strong>
        <span>{{ leaderUpdateSummary }}</span>
      </div>
      <el-alert
        v-if="leaderUpdateError"
        class="workflow-action-error"
        :title="leaderUpdateError"
        type="error"
        :closable="false"
        show-icon
      />
      <el-form label-position="top">
        <el-form-item label="本次更新说明" required>
          <el-input
            v-model="leaderUpdateNote"
            type="textarea"
            :rows="5"
            maxlength="500"
            show-word-limit
            resize="vertical"
            placeholder="说明本周期已完成事项、当前进度、风险及下一步安排"
            :disabled="leaderUpdateSubmitting"
            @input="leaderUpdateError = ''"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="leaderUpdateSubmitting" @click="leaderUpdateDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="leaderUpdateSubmitting"
          @click="submitLeaderUpdate"
        >
          保存负责人更新
        </el-button>
      </template>
    </el-dialog>

    <!-- 提交异议弹窗 -->
    <el-dialog v-model="objectionDialogVisible" title="提交排序异议" width="500px">
      <el-form ref="objectionFormRef" :model="objectionForm" :rules="objectionRules" label-width="90px">
        <el-form-item label="异议对象" prop="ranking">
          <el-select v-model="objectionForm.ranking" placeholder="选择成员排名" style="width: 100%">
            <el-option
              v-for="ranking in publicRankings"
              :key="ranking.id"
              :label="`第 ${ranking.rank} 名 · ${ranking.user_detail?.name || ranking.user_name || '未命名成员'}`"
              :value="ranking.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="异议内容" prop="content">
          <el-input v-model="objectionForm.content" type="textarea" :rows="3" placeholder="请输入异议内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="objectionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="objectionSubmitting" @click="handleSubmitObjection">提交</el-button>
      </template>
    </el-dialog>

    <!-- 异议处理弹窗 -->
    <el-dialog v-model="reviewObjectionVisible" :title="reviewMode === 'leader' ? '负责人初审' : '老师确认'" width="500px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="异议对象">{{ currentObjection?.ranking_user_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="异议内容">{{ currentObjection?.content }}</el-descriptions-item>
      </el-descriptions>
      <el-form class="mt-16" :model="reviewObjectionForm" label-width="90px">
        <el-form-item v-if="reviewMode === 'leader'" label="初审意见">
          <el-input v-model="reviewObjectionForm.leader_opinion" type="textarea" :rows="3" placeholder="请输入初审意见" />
        </el-form-item>
        <template v-else>
          <el-form-item label="负责人意见">
            <span>{{ currentObjection?.leader_opinion || '暂无' }}</span>
          </el-form-item>
          <el-form-item label="老师意见">
            <el-input v-model="reviewObjectionForm.teacher_opinion" type="textarea" :rows="3" placeholder="请输入确认意见" />
          </el-form-item>
          <el-form-item label="处理决定">
            <el-radio-group v-model="reviewObjectionForm.final_status">
              <el-radio value="approved">异议成立</el-radio>
              <el-radio value="rejected">异议不成立</el-radio>
            </el-radio-group>
          </el-form-item>
          <template v-if="reviewObjectionForm.final_status === 'approved'">
            <el-form-item label="更正名次">
              <el-input-number
                v-model="reviewObjectionForm.corrected_rank"
                :min="1"
                :max="Math.max(publicRankings.length, 1)"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="更正总分">
              <el-input-number
                v-model="reviewObjectionForm.corrected_total_score"
                :min="0"
                :precision="2"
                controls-position="right"
                placeholder="不修改可留空"
              />
            </el-form-item>
          </template>
          <el-form-item label="最终说明">
            <el-input
              v-model="reviewObjectionForm.final_result"
              type="textarea"
              :rows="3"
              placeholder="可填写更正依据或驳回原因"
            />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="reviewObjectionVisible = false">取消</el-button>
        <el-button type="primary" :loading="objectionSubmitting" @click="handleConfirmReviewObjection">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="memberDialogVisible"
      :title="editingMember ? '项目成员与交接' : '添加项目成员'"
      width="560px"
      :fullscreen="isMobile"
      append-to-body
    >
      <el-alert
        v-if="editingMember"
        title="退出项目只结束活动权限，不会删除该成员的任务、贡献、文件或历史排名。"
        type="info"
        :closable="false"
        show-icon
        class="member-dialog-alert"
      />
      <el-form label-width="94px" :label-position="isMobile ? 'top' : 'right'">
        <el-form-item v-if="!editingMember" label="成员" required>
          <el-select v-model="memberForm.user" filterable placeholder="选择团队成员" style="width: 100%">
            <el-option
              v-for="user in availableUsers"
              :key="user.id"
              :label="`${user.name} · ${user.email}`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="成员">
          <strong>{{ editingMember.user_detail?.name || '-' }}</strong>
        </el-form-item>
        <el-form-item label="项目角色" required>
          <el-select v-model="memberForm.role_in_project" style="width: 100%">
            <el-option label="负责人" value="leader" />
            <el-option label="核心成员" value="core" />
            <el-option label="普通参与" value="participant" />
            <el-option label="项目顾问" value="advisor" />
            <el-option label="外部协作者" value="external" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingMember" label="参与状态" required>
          <el-select v-model="memberForm.status" style="width: 100%">
            <el-option label="参与中" value="active" />
            <el-option label="暂离" value="on_leave" />
            <el-option label="已退出" value="exited" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingMember && memberForm.status === 'exited'" label="项目交接">
          <el-select
            v-model="memberForm.handover_to"
            clearable
            placeholder="负责人退出时必须选择接手人"
            style="width: 100%"
          >
            <el-option
              v-for="member in handoverProjectMembers"
              :key="member.id"
              :label="`${member.user_detail?.name || '-'} · ${member.role_in_project_display || getProjectRoleLabel(member.role_in_project)}`"
              :value="member.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingMember" label="原因说明">
          <el-input v-model="memberForm.reason" type="textarea" :rows="3" placeholder="记录角色调整、暂离或退出原因" />
        </el-form-item>
        <el-form-item v-if="editingMember && memberForm.status === 'exited'" label="交接说明">
          <el-input v-model="memberForm.handover_notes" type="textarea" :rows="3" placeholder="记录任务、资料和责任交接" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memberDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="memberSubmitting" @click="submitMember">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="expenseDialogVisible"
      title="编辑支出记录"
      width="560px"
      :fullscreen="isMobile"
      append-to-body
    >
      <el-form :model="expenseForm" label-position="top">
        <div class="expense-form-grid">
          <el-form-item label="支出标题" required>
            <el-input v-model="expenseForm.title" maxlength="200" />
          </el-form-item>
          <el-form-item label="支出金额" required>
            <el-input-number
              v-model="expenseForm.amount"
              :min="0.01"
              :precision="2"
              :controls="false"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="支出日期" required>
            <el-date-picker
              v-model="expenseForm.expense_date"
              type="date"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="支出类别" required>
            <el-select v-model="expenseForm.category" style="width: 100%">
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
        <el-form-item label="用途说明">
          <el-input v-model="expenseForm.purpose" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="expenseSubmitting" @click="expenseDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="expenseSubmitting" @click="submitExpenseEdit">
          保存修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  ArrowLeft,
  ChatDotRound,
  Clock,
  DataLine,
  Document,
  Download,
  EditPen,
  FolderOpened,
  DocumentChecked,
  Medal,
  Operation,
  Sort,
  Tickets,
  Trophy,
  UserFilled,
  Wallet,
} from '@element-plus/icons-vue'
import {
  getProject,
  getProjectMembers,
  addProjectMember,
  advanceStage,
  leaderUpdate,
  updateProjectMember,
  getStageLogs,
} from '@/api/projects'
import { getUsers } from '@/api/users'
import { getCompetitions, getCompetition } from '@/api/competitions'
import { getTasksByProject, changeTaskStatus } from '@/api/tasks'
import {
  getFinanceBudgetByProject,
  getFinanceExpensesByProject,
  deleteFinanceExpense,
  updateFinanceExpense,
} from '@/api/finance'
import { getFilesByProject, deleteFile, downloadFile } from '@/api/files'
import {
  generateRanking,
  confirmRanking,
  getRankingsByProject,
  updateRank,
  getObjections,
  createObjection,
  leaderReviewObjection,
  teacherConfirmObjection,
} from '@/api/contributions'
import { exportProjectReport } from '@/api/exports'
import { useUserStore } from '@/stores/user'
import { useDevice } from '@/composables/useDevice'
import {
  formatDate,
  formatFileSize,
  getStageLabel,
  getProjectStatusLabel,
  getProjectStatusTagType,
  getProjectRoleLabel,
  getCompetitionLevelLabel,
  getCompetitionStageTagType,
  getCompetitionStageTagStyle,
  getCompetitionStatusLabel,
  getCompetitionStatusTagType,
  downloadBlob,
} from '@/utils/format'
import {
  FILE_LEVEL_MAP,
  RANKING_STATUS_MAP,
  OBJECTION_STATUS_MAP,
} from '@/utils/constants'
import { getLeaderUpdateCadence } from '@/utils/projectWorkflow'
import {
  canTransitionTaskStatus,
  getAllowedTaskStatusTargets,
} from '@/views/tasks/taskWorkflow'
import type { AdvanceStageParams, Project, ProjectMember, StageLog, Competition, Task, FinanceCategory, FinanceExpense, FileAsset, TaskStatus, MemberRanking, RankingObjection, User } from '@/types'
import StageStepper from '@/components/StageStepper.vue'
import TaskBoard from '@/components/TaskBoard.vue'
import FinanceTable from '@/components/FinanceTable.vue'
import FileUploader from '@/components/FileUploader.vue'
import ProjectTimeline from '@/components/ProjectTimeline.vue'

interface ProjectRisk {
  label: string
  detail: string
  type: 'success' | 'warning' | 'danger' | 'info'
}

interface ProjectSectionItem {
  name: string
  label: string
  icon: Component
  roles?: string[]
  internalOnly?: boolean
}

interface ProjectSection {
  label: string
  items: ProjectSectionItem[]
}

const projectSections: ProjectSection[] = [
  {
    label: '项目信息',
    items: [
      { name: 'profile', label: '档案', icon: Document },
      { name: 'stage', label: '阶段', icon: DataLine },
      { name: 'timeline', label: '时间线', icon: Clock },
    ],
  },
  {
    label: '执行管理',
    items: [
      { name: 'task', label: '任务', icon: Tickets },
      { name: 'competition', label: '比赛', icon: Trophy },
    ],
  },
  {
    label: '资源管理',
    items: [
      { name: 'finance', label: '经费', icon: Wallet, internalOnly: true },
      { name: 'file', label: '文件', icon: FolderOpened },
      { name: 'ip', label: '成果与知识产权', icon: Medal },
    ],
  },
  {
    label: '协作复盘',
    items: [
      { name: 'ranking', label: '成员排序', icon: UserFilled },
      {
        name: 'audit',
        label: '操作审计',
        icon: DocumentChecked,
        roles: ['teacher', 'sys_admin'],
      },
    ],
  },
]

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { isMobile } = useDevice()
const projectId = Number(route.params.id)
const isExternalCollaborator = computed(
  () => userStore.userInfo?.membership_status === 'external',
)

const loading = ref(false)
const activeTab = ref('profile')
const project = ref<Project | null>(null)
const members = ref<ProjectMember[]>([])
const availableUsers = ref<User[]>([])
const memberDialogVisible = ref(false)
const memberSubmitting = ref(false)
const editingMember = ref<ProjectMember | null>(null)
const memberForm = reactive({
  user: undefined as number | undefined,
  role_in_project: 'participant',
  status: 'active',
  reason: '',
  handover_to: undefined as number | undefined,
  handover_notes: '',
})
const activeMemberCount = computed(() =>
  members.value.filter((member) => !member.status || member.status === 'active').length
)
const handoverProjectMembers = computed(() =>
  members.value.filter((member) =>
    member.id !== editingMember.value?.id
    && (!member.status || member.status === 'active')
  )
)
const stageLogs = ref<StageLog[]>([])
const stageSubmitting = ref(false)
const stageActionError = ref('')
const timelineRefreshKey = ref(0)
const tasks = ref<Task[]>([])
const competitionInfo = ref<Competition | null>(null)
const competitionLoading = ref(false)
const expenses = ref<FinanceExpense[]>([])
const totalBudget = ref(0)
const expenseDialogVisible = ref(false)
const expenseSubmitting = ref(false)
const editingExpense = ref<FinanceExpense | null>(null)
const expenseForm = reactive({
  title: '',
  amount: undefined as number | undefined,
  expense_date: '',
  category: 'other' as FinanceCategory,
  purpose: '',
})
const files = ref<FileAsset[]>([])

const descriptionColumns = computed(() => (isMobile.value ? 1 : 2))
const projectMemberCount = computed(() => activeMemberCount.value || project.value?.member_count || 0)
const projectPlanRange = computed(() => {
  if (!project.value) return '-'
  return `${formatDate(project.value.start_date)} 至 ${formatDate(project.value.planned_end_date)}`
})

const projectPriority = computed(() => {
  const priority = project.value?.priority || 'normal'
  const labelMap: Record<string, string> = {
    normal: '普通',
    high: '高',
    urgent: '紧急',
  }
  const typeMap: Record<string, 'info' | 'warning' | 'danger'> = {
    normal: 'info',
    high: 'warning',
    urgent: 'danger',
  }
  return {
    label: project.value?.priority_display || labelMap[priority] || priority,
    type: typeMap[priority] || 'info',
  }
})

function parseProjectDate(value?: string | null): Date | null {
  if (!value) return null
  const normalized = value.length === 10 ? `${value}T00:00:00` : value
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

const projectRisk = computed<ProjectRisk>(() => {
  const currentProject = project.value
  if (!currentProject) {
    return { label: '待加载', detail: '项目数据加载中', type: 'info' }
  }
  if (currentProject.status === 'closed') {
    return { label: '已结项', detail: '项目已关闭', type: 'info' }
  }
  if (currentProject.status === 'paused') {
    return { label: '已暂停', detail: '项目当前处于暂停状态', type: 'warning' }
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const plannedEnd = parseProjectDate(currentProject.planned_end_date)
  const oneDay = 24 * 60 * 60 * 1000

  if (plannedEnd && plannedEnd.getTime() < today.getTime()) {
    const days = Math.ceil((today.getTime() - plannedEnd.getTime()) / oneDay)
    return { label: '计划逾期', detail: `已超过计划结束日期 ${days} 天`, type: 'danger' }
  }

  const cadence = getLeaderUpdateCadence(
    currentProject.last_leader_update,
    currentProject.created_at,
    today,
  )
  if (cadence.isOverdue) {
    const detail = cadence.isFirstUpdate
      ? `项目创建后已有 ${cadence.daysSinceUpdate} 天未提交负责人更新`
      : `负责人已有 ${cadence.daysSinceUpdate} 天未更新`
    return { label: '更新滞后', detail, type: 'warning' }
  }

  if (plannedEnd) {
    const days = Math.ceil((plannedEnd.getTime() - today.getTime()) / oneDay)
    if (days <= 14) {
      return { label: '临近截止', detail: `距计划结束还有 ${Math.max(days, 0)} 天`, type: 'warning' }
    }
  }

  return { label: '节奏正常', detail: '当前进度正常', type: 'success' }
})

// 导出报告加载状态
const exportingReport = ref(false)

// 排序相关状态
const rankingLoading = ref(false)
const rankings = ref<MemberRanking[]>([])
const rankingPeriod = ref(new Date().toISOString().slice(0, 7))
const rankingPeriodInitialized = ref(false)
const objections = ref<RankingObjection[]>([])
const objectionDialogVisible = ref(false)
const objectionSubmitting = ref(false)
const objectionFormRef = ref<FormInstance>()
const objectionForm = reactive({
  ranking: '' as number | string,
  content: '',
})
const objectionRules: FormRules = {
  ranking: [{ required: true, message: '请选择异议对象', trigger: 'change' }],
  content: [{ required: true, message: '请输入异议内容', trigger: 'blur' }],
}

// 异议处理状态
const reviewObjectionVisible = ref(false)
const reviewMode = ref<'leader' | 'teacher'>('leader')
const currentObjection = ref<RankingObjection | null>(null)
const reviewObjectionForm = reactive({
  leader_opinion: '',
  teacher_opinion: '',
  final_status: 'approved' as 'approved' | 'rejected',
  corrected_rank: 1,
  corrected_total_score: undefined as number | undefined,
  final_result: '',
})
const displayRankings = computed(() =>
  rankings.value.filter((item) => !rankingPeriod.value || item.period === rankingPeriod.value),
)
const publicRankings = computed(() => displayRankings.value.filter((item) => item.is_public))

// 牵头负责人和项目成员表中的共同负责人拥有同级项目管理权限。
const isProjectLeader = computed(() => {
  const currentUserId = userStore.userInfo?.id
  if (!currentUserId) return false
  if (currentUserId === project.value?.leader) return true
  return members.value.some(
    (member) =>
      member.user === currentUserId
      && member.role_in_project === 'leader'
      && member.status !== 'exited',
  )
})
const canManageProjectWorkflow = computed(() =>
  Boolean(project.value?.can_manage)
  || isProjectLeader.value
  || userStore.isTeacher
  || userStore.isAdmin
)
const leaderUpdateCadence = computed(() =>
  getLeaderUpdateCadence(
    project.value?.last_leader_update,
    project.value?.created_at,
  )
)
const leaderUpdateSummary = computed(() => {
  const cadence = leaderUpdateCadence.value
  if (!cadence.baseline) return '暂无负责人更新记录'
  if (cadence.isFirstUpdate) {
    return cadence.daysSinceUpdate === 0
      ? '待提交首次负责人更新'
      : `待首次更新 · 自创建起 ${cadence.daysSinceUpdate} 天`
  }
  return cadence.daysSinceUpdate === 0
    ? '负责人今天已更新'
    : `最近更新于 ${formatDate(project.value?.last_leader_update)} · ${cadence.daysSinceUpdate} 天前`
})

const leaderUpdateDialogVisible = ref(false)
const leaderUpdateSubmitting = ref(false)
const leaderUpdateNote = ref('')
const leaderUpdateError = ref('')

// 加载项目详情
async function loadProject(): Promise<void> {
  loading.value = true
  try {
    project.value = await getProject(projectId)
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

// 加载关联比赛（通过项目 ID 过滤比赛列表）
async function loadCompetitions(): Promise<void> {
  if (competitionInfo.value) return
  competitionLoading.value = true
  try {
    const res = await getCompetitions({ project: projectId, page: 1, page_size: 10 } as any)
    const list = res.results || []
    if (list.length > 0) {
      // 获取第一条比赛的完整详情
      competitionInfo.value = await getCompetition(list[0].id)
    }
  } catch {
    // 忽略
  } finally {
    competitionLoading.value = false
  }
}

// 加载成员
async function loadMembers(): Promise<void> {
  try {
    members.value = await getProjectMembers(projectId)
  } catch {
    // 忽略
  }
}

// 加载阶段日志
async function loadStageLogs(): Promise<void> {
  try {
    stageLogs.value = await getStageLogs(projectId)
  } catch {
    // 忽略
  }
}

function getWorkflowErrorMessage(error: unknown, fallback: string): string {
  const candidate = error as {
    message?: string
    response?: {
      data?: {
        message?: string
        detail?: string
      }
    }
  }
  return candidate?.response?.data?.message
    || candidate?.response?.data?.detail
    || candidate?.message
    || fallback
}

async function refreshProjectWorkflow(): Promise<void> {
  await Promise.all([loadProject(), loadStageLogs()])
  timelineRefreshKey.value += 1
}

function openLeaderUpdate(): void {
  leaderUpdateNote.value = ''
  leaderUpdateError.value = ''
  leaderUpdateDialogVisible.value = true
}

async function submitLeaderUpdate(): Promise<void> {
  const note = leaderUpdateNote.value.trim()
  leaderUpdateError.value = ''
  if (!note) {
    leaderUpdateError.value = '请填写本次项目进度更新说明'
    return
  }

  leaderUpdateSubmitting.value = true
  try {
    await leaderUpdate(projectId, note)
    await refreshProjectWorkflow()
    leaderUpdateDialogVisible.value = false
    ElMessage.success('项目进度已更新，新的 11 天周期已开始')
  } catch (error) {
    leaderUpdateError.value = getWorkflowErrorMessage(error, '项目进度更新失败，请稍后重试')
  } finally {
    leaderUpdateSubmitting.value = false
  }
}

async function handleAdvanceStage(payload: AdvanceStageParams): Promise<void> {
  stageActionError.value = ''
  const targetStage = Number(payload.target_stage)
  if (targetStage === 15 || targetStage === 16) {
    const actionLabel = targetStage === 15 ? '暂停项目' : '终止项目'
    const detail = targetStage === 15
      ? '暂停会改变项目执行状态，并写入阶段记录。'
      : '终止属于不可逆的结束操作，请确认项目确实不再继续。'
    try {
      await ElMessageBox.confirm(detail, `确认${actionLabel}`, {
        type: targetStage === 16 ? 'error' : 'warning',
        confirmButtonText: `确认${actionLabel}`,
        cancelButtonText: '返回检查',
      })
    } catch {
      return
    }
  }

  stageSubmitting.value = true
  try {
    await advanceStage(projectId, payload)
    await refreshProjectWorkflow()
    ElMessage.success('项目阶段已推进，详情和时间线已刷新')
  } catch (error) {
    stageActionError.value = getWorkflowErrorMessage(error, '阶段操作失败，请检查当前状态后重试')
  } finally {
    stageSubmitting.value = false
  }
}

// 加载任务
async function loadTasks(): Promise<void> {
  try {
    tasks.value = await getTasksByProject(projectId)
  } catch {
    // 忽略
  }
}

// 加载经费
async function loadExpenses(): Promise<void> {
  try {
    const [projectExpenses, budgets] = await Promise.all([
      getFinanceExpensesByProject(projectId),
      getFinanceBudgetByProject(projectId),
    ])
    expenses.value = projectExpenses
    totalBudget.value = budgets.reduce(
      (sum, budget) => sum + Number(budget.total_income || 0),
      0,
    )
  } catch {
    // 忽略
  }
}

// 加载文件
async function loadFiles(): Promise<void> {
  try {
    files.value = await getFilesByProject(projectId)
  } catch {
    // 忽略
  }
}

// 加载排序
async function loadRankings(): Promise<void> {
  rankingLoading.value = true
  try {
    const res: any = await getRankingsByProject(projectId)
    rankings.value = Array.isArray(res) ? res : (res.results || [])
    if (!rankingPeriodInitialized.value && rankings.value.length) {
      const periods = Array.from(
        new Set(rankings.value.map((item) => item.period)),
      ).filter(Boolean)
      if (!periods.includes(rankingPeriod.value) && periods.length) {
        rankingPeriod.value = periods.sort().reverse()[0]
      }
      rankingPeriodInitialized.value = true
    }
  } catch {
    // 忽略
  } finally {
    rankingLoading.value = false
  }
}

// 加载异议
async function loadObjections(): Promise<void> {
  try {
    const res: any = await getObjections({ project: projectId })
    objections.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 忽略
  }
}

// 生成排序
async function handleGenerateRanking(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要生成成员排序吗？', '提示', { type: 'warning' })
    if (!rankingPeriod.value.trim()) {
      ElMessage.warning('请填写统计周期')
      return
    }
    await generateRanking(projectId, rankingPeriod.value.trim())
    ElMessage.success('排序已生成')
    loadRankings()
  } catch {
    // 取消
  }
}

// 确认排序
async function handleConfirmRanking(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要确认成员排序吗？确认后不可修改。', '提示', { type: 'warning' })
    if (!rankingPeriod.value.trim()) {
      ElMessage.warning('请填写要确认的统计周期')
      return
    }
    await confirmRanking(projectId, rankingPeriod.value.trim())
    ElMessage.success('排序已确认')
    loadRankings()
  } catch {
    // 取消
  }
}

// 修改排名
async function handleRankChange(row: any): Promise<void> {
  try {
    await updateRank(row.id, { rank: row.rank })
    ElMessage.success('排名已更新')
  } catch {
    // 错误已处理
    loadRankings()
  }
}

// 打开提交异议弹窗
function handleOpenObjection(): void {
  objectionForm.ranking = ''
  objectionForm.content = ''
  objectionDialogVisible.value = true
}

// 提交异议
async function handleSubmitObjection(): Promise<void> {
  if (!objectionFormRef.value) return
  await objectionFormRef.value.validate(async (valid) => {
    if (!valid) return
    objectionSubmitting.value = true
    try {
      await createObjection({
        ranking: Number(objectionForm.ranking),
        content: objectionForm.content.trim(),
      })
      ElMessage.success('异议已提交')
      objectionDialogVisible.value = false
      loadObjections()
    } catch {
      // 错误已处理
    } finally {
      objectionSubmitting.value = false
    }
  })
}

// 打开异议处理弹窗
function handleReviewObjection(row: any, mode: 'leader' | 'teacher'): void {
  currentObjection.value = row as RankingObjection
  reviewMode.value = mode
  reviewObjectionForm.leader_opinion = ''
  reviewObjectionForm.teacher_opinion = ''
  reviewObjectionForm.final_status = 'approved'
  const currentRanking = rankings.value.find((item) => item.id === row.ranking)
  reviewObjectionForm.corrected_rank = currentRanking?.rank || 1
  reviewObjectionForm.corrected_total_score = undefined
  reviewObjectionForm.final_result = ''
  reviewObjectionVisible.value = true
}

// 确认处理异议
async function handleConfirmReviewObjection(): Promise<void> {
  if (!currentObjection.value) return
  objectionSubmitting.value = true
  try {
    const data: any = {}
    if (reviewMode.value === 'leader') {
      const opinion = reviewObjectionForm.leader_opinion.trim()
      if (!opinion) {
        ElMessage.warning('请填写初审意见')
        return
      }
      data.leader_opinion = opinion
    } else {
      data.teacher_opinion = reviewObjectionForm.teacher_opinion.trim()
      data.final_status = reviewObjectionForm.final_status
      data.final_result = reviewObjectionForm.final_result.trim()
      if (reviewObjectionForm.final_status === 'approved') {
        const ranking = rankings.value.find(
          (item) => item.id === currentObjection.value?.ranking,
        )
        const scoreChanged = (
          typeof reviewObjectionForm.corrected_total_score === 'number'
          && Number(reviewObjectionForm.corrected_total_score) !== Number(ranking?.total_score)
        )
        const rankChanged = reviewObjectionForm.corrected_rank !== ranking?.rank
        if (!rankChanged && !scoreChanged) {
          ElMessage.warning('异议成立时，请实际更正名次或总分')
          return
        }
        data.corrected_rank = reviewObjectionForm.corrected_rank
        if (typeof reviewObjectionForm.corrected_total_score === 'number') {
          data.corrected_total_score = reviewObjectionForm.corrected_total_score
        }
      }
    }
    if (reviewMode.value === 'leader') {
      await leaderReviewObjection(currentObjection.value.id, data)
    } else {
      await teacherConfirmObjection(currentObjection.value.id, data)
    }
    ElMessage.success('处理成功')
    reviewObjectionVisible.value = false
    await Promise.all([loadObjections(), loadRankings()])
  } catch {
    // 错误已处理
  } finally {
    objectionSubmitting.value = false
  }
}

// 导出项目完整报告（Word，使用专用报告接口）
async function handleExportReport(): Promise<void> {
  exportingReport.value = true
  try {
    const blob = await exportProjectReport(projectId)
    downloadBlob(blob, `项目报告_${project.value?.name || projectId}_${Date.now()}.docx`)
    ElMessage.success('导出成功')
  } catch {
    // 错误已处理
  } finally {
    exportingReport.value = false
  }
}

function handleTabSelect(tabName: string): void {
  if (activeTab.value === tabName) return
  activeTab.value = tabName
  handleTabChange(tabName)
}

function openProjectTasks(taskId?: number): void {
  router.push({
    path: '/tasks',
    query: {
      project_id: String(projectId),
      ...(taskId ? { task_id: String(taskId) } : {}),
    },
  })
}

function openProjectOperations(): void {
  router.push({ name: 'ProjectOperations', params: { id: projectId } })
}

function openProjectCompetitions(): void {
  router.push({ path: '/competitions', query: { project_id: String(projectId) } })
}

function openProjectFinance(): void {
  router.push({
    path: '/finance',
    query: { project_id: String(projectId) },
  })
}

function openProjectContributions(): void {
  router.push({ path: '/contributions', query: { project_id: String(projectId) } })
}

function openProjectContributionReviews(): void {
  router.push({ path: '/contributions/pending', query: { project_id: String(projectId) } })
}

function openProjectIP(): void {
  router.push({ path: '/intellectual-property', query: { project_id: String(projectId) } })
}

function createProjectIP(): void {
  router.push({
    path: '/intellectual-property/create',
    query: { project_id: String(projectId) },
  })
}

function openProjectAudit(): void {
  router.push({
    path: '/audit/logs',
    query: { search: `/projects/${projectId}/` },
  })
}

// Tab 切换
function handleTabChange(tabName: string): void {
  switch (tabName) {
    case 'stage':
      if (!stageLogs.value.length) loadStageLogs()
      break
    case 'task':
      if (!tasks.value.length) loadTasks()
      break
    case 'competition':
      loadCompetitions()
      break
    case 'finance':
      if (!expenses.value.length) loadExpenses()
      break
    case 'file':
      if (!files.value.length) loadFiles()
      break
    case 'ranking':
      loadRankings()
      loadObjections()
      break
    case 'timeline':
      // 时间线组件内部自行加载数据
      break
  }
}

function canChangeTaskStatus(task: Task): boolean {
  return getAllowedTaskStatusTargets(
    task,
    userStore.userInfo?.id,
    canManageProjectWorkflow.value,
  ).length > 0
}

function canChangeTaskToStatus(task: Task, status: TaskStatus): boolean {
  return canTransitionTaskStatus(
    task,
    status,
    userStore.userInfo?.id,
    canManageProjectWorkflow.value,
  )
}

// 任务状态变更（拖拽）
async function handleTaskStatusChange(task: Task, newStatus: TaskStatus): Promise<void> {
  if (!canChangeTaskToStatus(task, newStatus) || task.status === newStatus) return
  let delayReason: string | undefined
  let completionNote: string | undefined
  if (newStatus === 'overdue') {
    try {
      const result = await ElMessageBox.prompt(
        '进入已逾期状态必须记录延期原因，该说明会保留在任务详情中。',
        '填写延期原因',
        {
          confirmButtonText: '确认延期',
          cancelButtonText: '取消',
          inputPlaceholder: '说明延期原因和新的处理计划',
          inputValidator: (value) => Boolean(value?.trim()) || '请填写延期原因',
        },
      )
      delayReason = result.value.trim()
    } catch {
      return
    }
  }
  if (newStatus === 'pending_review') {
    try {
      const result = await ElMessageBox.prompt(
        '请概述已完成内容、交付物位置和需要审核人关注的事项。',
        '提交任务审核',
        {
          confirmButtonText: '提交审核',
          cancelButtonText: '取消',
          inputPlaceholder: '填写完成说明（可后续补充）',
          inputValue: task.completion_note || '',
        },
      )
      completionNote = result.value.trim()
    } catch {
      return
    }
  }

  const previousStatus = task.status
  task.status = newStatus
  try {
    await changeTaskStatus(task.id, newStatus, delayReason, completionNote)
    ElMessage.success('任务状态已更新')
  } catch {
    task.status = previousStatus
    await loadTasks()
  }
}

// 任务点击
function handleTaskClick(task: Task): void {
  openProjectTasks(task.id)
}

function projectMemberStatusLabel(value?: string): string {
  return { active: '参与中', on_leave: '暂离', exited: '已退出' }[value || 'active'] || '参与中'
}

function projectMemberStatusType(value?: string): 'success' | 'warning' | 'info' {
  if (value === 'on_leave') return 'warning'
  if (value === 'exited') return 'info'
  return 'success'
}

async function openAddMember(): Promise<void> {
  editingMember.value = null
  Object.assign(memberForm, {
    user: undefined,
    role_in_project: 'participant',
    status: 'active',
    reason: '',
    handover_to: undefined,
    handover_notes: '',
  })
  try {
    const response = await getUsers({ page_size: 100 })
    const existing = new Set(
      members.value.filter((member) => member.status !== 'exited').map((member) => member.user)
    )
    availableUsers.value = response.results.filter((user) =>
      user.membership_status !== 'exited' && !existing.has(user.id)
    )
  } catch {
    availableUsers.value = []
  }
  memberDialogVisible.value = true
}

function openEditMember(member: ProjectMember): void {
  editingMember.value = member
  Object.assign(memberForm, {
    user: member.user,
    role_in_project: member.role_in_project,
    status: member.status || 'active',
    reason: member.exit_reason || '',
    handover_to: member.handover_to || undefined,
    handover_notes: member.handover_notes || '',
  })
  memberDialogVisible.value = true
}

async function submitMember(): Promise<void> {
  if (!editingMember.value && !memberForm.user) {
    ElMessage.warning('请选择成员')
    return
  }
  memberSubmitting.value = true
  try {
    if (editingMember.value) {
      await updateProjectMember(projectId, {
        member_id: editingMember.value.id,
        role_in_project: memberForm.role_in_project,
        status: memberForm.status,
        reason: memberForm.reason.trim(),
        ...(memberForm.handover_to ? { handover_to: memberForm.handover_to } : {}),
        handover_notes: memberForm.handover_notes.trim(),
      })
      ElMessage.success('成员状态与交接记录已保存')
    } else {
      await addProjectMember(projectId, {
        user: memberForm.user!,
        role_in_project: memberForm.role_in_project,
      })
      ElMessage.success('项目成员已添加')
    }
    memberDialogVisible.value = false
    await loadProject()
    await loadMembers()
  } catch {
    // 错误已统一处理
  } finally {
    memberSubmitting.value = false
  }
}

// 编辑支出
function handleEditExpense(expense: FinanceExpense): void {
  editingExpense.value = expense
  Object.assign(expenseForm, {
    title: expense.title,
    amount: Number(expense.amount),
    expense_date: expense.expense_date,
    category: expense.category,
    purpose: expense.purpose || '',
  })
  expenseDialogVisible.value = true
}

async function submitExpenseEdit(): Promise<void> {
  if (
    !editingExpense.value
    || !expenseForm.title.trim()
    || !expenseForm.amount
    || !expenseForm.expense_date
  ) {
    ElMessage.warning('请补全支出标题、金额和日期')
    return
  }
  expenseSubmitting.value = true
  try {
    await updateFinanceExpense(editingExpense.value.id, {
      project: projectId,
      title: expenseForm.title.trim(),
      amount: expenseForm.amount,
      expense_date: expenseForm.expense_date,
      category: expenseForm.category,
      purpose: expenseForm.purpose.trim(),
    })
    ElMessage.success('支出记录已更新')
    expenseDialogVisible.value = false
    await loadExpenses()
  } finally {
    expenseSubmitting.value = false
  }
}

// 删除支出
async function handleDeleteExpense(expense: FinanceExpense): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要删除该支出记录吗？', '提示', { type: 'warning' })
    await deleteFinanceExpense(expense.id)
    ElMessage.success('删除成功')
    loadExpenses()
  } catch {
    // 取消
  }
}

// 下载文件
async function handleDownload(file: FileAsset): Promise<void> {
  try {
    const blob = await downloadFile(file.id)
    downloadBlob(blob, file.name)
  } catch {
    ElMessage.error('下载失败')
  }
}

// 删除文件
async function handleDeleteFile(file: FileAsset): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除文件「${file.name}」吗？`, '提示', { type: 'warning' })
    await deleteFile(file.id)
    ElMessage.success('删除成功')
    loadFiles()
  } catch {
    // 取消
  }
}

onMounted(() => {
  loadProject()
  loadMembers()
  const requestedTab = String(route.query.tab || '')
  const requestedSection = projectSections
    .flatMap((group) => group.items)
    .find((item) => item.name === requestedTab)
  if (
    requestedSection
    && (!requestedSection.internalOnly || !isExternalCollaborator.value)
  ) {
    activeTab.value = requestedTab
    handleTabChange(requestedTab)
  }
})
</script>

<style lang="scss" scoped>
.project-detail-page {
  padding-bottom: 32px;
}

.project-summary {
  overflow: hidden;
  margin-bottom: 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.summary-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 18px;
  border-bottom: 1px solid var(--color-border-light);
}

.back-button {
  padding-left: 0;
}

.summary-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.summary-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.summary-identity {
  padding: 22px 24px 20px;
}

.summary-title-block {
  min-width: 0;
}

.summary-kicker {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 7px;
  color: var(--color-text-muted);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 12px;
}

.summary-title-block h1 {
  max-width: 920px;
  overflow-wrap: anywhere;
  color: var(--color-text);
  font-size: 24px;
  font-weight: 600;
  line-height: 1.35;
}

.summary-title-block p {
  display: -webkit-box;
  max-width: 920px;
  margin-top: 8px;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(120px, 1fr));
  border-top: 1px solid var(--color-border-light);
}

.summary-metric {
  display: flex;
  min-width: 0;
  min-height: 82px;
  padding: 14px 16px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 5px;
  border-right: 1px solid var(--color-border-light);
}

.summary-metric:last-child {
  border-right: 0;
}

.summary-metric > span:first-child {
  color: var(--color-text-muted);
  font-size: 11px;
}

.summary-metric strong {
  max-width: 100%;
  overflow: hidden;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.45;
  text-overflow: ellipsis;
}

.leader-update-copy {
  max-width: 100%;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 10px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.risk-metric small {
  max-width: 100%;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-workspace {
  display: grid;
  grid-template-columns: 196px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.project-section-nav {
  position: sticky;
  top: 16px;
  padding: 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.section-nav-group + .section-nav-group {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-light);
}

.section-nav-label {
  padding: 4px 9px 5px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.section-nav-item {
  display: flex;
  width: 100%;
  min-height: 36px;
  padding: 7px 9px;
  align-items: center;
  gap: 9px;
  color: var(--color-text-regular);
  font: inherit;
  font-size: 13px;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: color var(--transition-fast), background var(--transition-fast);
}

.section-nav-item:hover {
  color: var(--color-primary);
  background: var(--color-surface-subtle);
}

.section-nav-item.is-active {
  color: var(--color-primary);
  font-weight: 600;
  background: var(--color-primary-soft);
}

.section-nav-item .el-icon {
  flex: 0 0 auto;
  font-size: 16px;
}

.detail-content {
  min-width: 0;
  min-height: 560px;
  padding: 18px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.detail-tabs {
  min-width: 0;
}

:deep(.detail-tabs > .el-tabs__header) {
  display: none;
}

:deep(.detail-tabs > .el-tabs__content) {
  overflow: visible;
}

.pane-section {
  min-width: 0;
}

.pane-heading {
  display: flex;
  min-height: 38px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.pane-heading h2 {
  color: var(--color-text);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.4;
}

.pane-heading > span {
  color: var(--color-text-muted);
  font-size: 12px;
}

.pane-heading-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.pane-heading-actions > span {
  color: var(--color-text-muted);
  font-size: 12px;
}

.project-link-panel {
  display: flex;
  min-height: 132px;
  padding: 20px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.project-link-panel strong {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
}

.project-link-panel p {
  max-width: 680px;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.7;
}

.project-link-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}

.expense-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.subsection-heading,
.ranking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 22px 0 12px;
}

.subsection-heading h3,
.ranking-header h3 {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
}

.subsection-heading span {
  color: var(--color-text-muted);
  font-size: 12px;
}

.heading-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.member-dialog-alert {
  margin-bottom: 18px;
}

.workflow-action-error {
  margin-bottom: 14px;
}

.leader-update-context {
  display: flex;
  margin-bottom: 16px;
  padding: 12px 14px;
  flex-direction: column;
  gap: 4px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.leader-update-context strong {
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.leader-update-context span {
  color: var(--color-text-muted);
  font-size: 12px;
}

.ranking-header:first-of-type {
  margin-top: 0;
}

.ranking-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.ranking-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.ranking-period {
  width: 180px;
}

.ranking-evidence {
  padding: 12px 18px;
}

.ranking-evidence p {
  margin-top: 10px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.pane-section :deep(.el-descriptions__label) {
  width: 112px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.pane-section :deep(.el-divider) {
  margin: 22px 0;
}

.mt-16 {
  margin-top: 16px;
}

@media screen and (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(150px, 1fr));
  }

  .summary-metric:nth-child(3n) {
    border-right: 0;
  }

  .summary-metric:nth-child(-n + 3) {
    border-bottom: 1px solid var(--color-border-light);
  }
}

@media screen and (max-width: 960px) {
  .detail-workspace {
    grid-template-columns: 1fr;
  }

  .project-section-nav {
    position: static;
    display: flex;
    gap: 4px;
    padding: 8px;
    overflow-x: auto;
    overscroll-behavior-x: contain;
  }

  .section-nav-group {
    display: flex;
    gap: 4px;
    flex: 0 0 auto;
  }

  .section-nav-group + .section-nav-group {
    margin-top: 0;
    padding-top: 0;
    padding-left: 4px;
    border-top: 0;
    border-left: 1px solid var(--color-border-light);
  }

  .section-nav-label {
    display: none;
  }

  .section-nav-item {
    width: auto;
    flex: 0 0 auto;
    white-space: nowrap;
  }
}

@media screen and (max-width: 768px) {
  .project-detail-page {
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }

  .summary-toolbar {
    padding: 10px 14px;
  }

  .summary-actions {
    gap: 4px;
  }

  .summary-identity {
    padding: 18px 16px 16px;
  }

  .summary-title-block h1 {
    font-size: 20px;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .summary-metric {
    min-height: 78px;
    padding: 12px;
    border-bottom: 1px solid var(--color-border-light);
  }

  .summary-metric:nth-child(3n) {
    border-right: 1px solid var(--color-border-light);
  }

  .summary-metric:nth-child(2n) {
    border-right: 0;
  }

  .summary-metric:nth-last-child(-n + 2) {
    border-bottom: 0;
  }

  .summary-metric strong {
    white-space: normal;
  }

  .detail-workspace {
    gap: 12px;
  }

  .detail-content {
    min-height: 480px;
    padding: 14px;
  }

  .pane-heading {
    margin-bottom: 14px;
  }

  .pane-heading-actions,
  .project-link-panel,
  .project-link-actions {
    width: 100%;
    align-items: stretch;
    flex-direction: column;
  }

  .expense-form-grid {
    grid-template-columns: 1fr;
  }

  .ranking-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .ranking-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .ranking-period {
    width: 100%;
  }

  .pane-section :deep(.el-descriptions__label) {
    width: 96px;
  }
}

@media screen and (max-width: 420px) {
  .summary-actions .el-button {
    padding-right: 10px;
    padding-left: 10px;
  }

  .summary-actions .el-button:first-child {
    font-size: 0;
  }

  .summary-actions .el-button:first-child :deep(.el-icon) {
    margin-right: 0;
    font-size: 15px;
  }

  .section-nav-item {
    min-height: 34px;
    padding: 6px 8px;
  }
}
</style>
