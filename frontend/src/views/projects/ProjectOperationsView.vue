<template>
  <div class="page-container operations-page">
    <PageHeader
      :title="project ? `${project.name} · 协作工作台` : '项目协作工作台'"
      subtitle="集中维护里程碑、风险、讨论、知识沉淀与项目复盘"
    >
      <template #actions>
        <el-button :icon="ArrowLeft" @click="router.back()">返回</el-button>
        <el-button v-if="project" :icon="FolderOpened" @click="openProjectDetail">项目详情</el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="loadError"
      class="load-alert"
      :title="loadError"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button type="primary" link @click="loadWorkspace">重新加载</el-button>
      </template>
    </el-alert>

    <div v-loading="loading" class="operations-shell">
      <section v-if="project" class="operations-summary" aria-label="项目协作摘要">
        <div>
          <span>当前阶段</span>
          <strong>{{ project.current_stage_display || `阶段 ${project.current_stage || '-'}` }}</strong>
        </div>
        <div>
          <span>里程碑</span>
          <strong>{{ completedMilestones }}/{{ milestones.length }} 已完成</strong>
        </div>
        <div>
          <span>开放风险</span>
          <strong :class="{ danger: openRiskCount > 0 }">{{ openRiskCount }} 项</strong>
        </div>
        <div>
          <span>协作沉淀</span>
          <strong>{{ discussions.length }} 个讨论 · {{ articles.length }} 篇知识</strong>
        </div>
      </section>

      <el-tabs v-if="project" v-model="activeTab" class="operations-tabs" @tab-change="handleTabChange">
        <el-tab-pane v-if="isInternalMember" name="insights">
          <template #label><span class="tab-label"><DataAnalysis />分析</span></template>
          <section class="workspace-section insights-section">
            <header class="section-heading">
              <div>
                <h2>项目洞察</h2>
                <p>根据当前任务、预算、成员和风险数据实时计算。</p>
              </div>
              <el-button :icon="Refresh" :loading="insightsLoading" @click="loadInsights">重新分析</el-button>
            </header>

            <el-alert
              v-if="insightsError"
              :title="insightsError"
              type="warning"
              :closable="false"
              show-icon
            />
            <div class="insight-overview">
              <div class="score-panel">
                <span>项目健康度</span>
                <strong>{{ healthScore?.overall_score ?? '-' }}</strong>
                <el-tag :type="healthGradeType" effect="dark">{{ healthScore ? `${healthScore.grade} 级` : '待分析' }}</el-tag>
              </div>
              <div class="score-panel risk-score-panel">
                <span>预测风险分</span>
                <strong>{{ riskPrediction?.risk_score ?? '-' }}</strong>
                <el-tag :type="riskLevelType(riskPrediction?.risk_level)" effect="dark">
                  {{ riskLevelLabel(riskPrediction?.risk_level) }}
                </el-tag>
              </div>
              <div class="score-panel material-score-panel">
                <span>材料完整度</span>
                <strong>{{ materialCheck ? Math.round(materialCheck.completion_rate * 100) : '-' }}<small v-if="materialCheck">%</small></strong>
                <el-tag :type="materialStatusType(materialCheck?.overall_status)" effect="dark">
                  {{ materialStatusLabel(materialCheck?.overall_status) }}
                </el-tag>
              </div>
            </div>

            <div v-if="healthScore" class="insight-grid">
              <article v-for="(item, key) in healthScore.category_scores" :key="key" class="metric-row">
                <header><strong>{{ item.label }}</strong><span>{{ item.score }} 分</span></header>
                <el-progress :percentage="item.score" :show-text="false" :stroke-width="7" />
                <p>{{ item.detail }}</p>
              </article>
            </div>

            <div class="analysis-columns">
              <section>
                <h3>风险因子与建议</h3>
                <EmptyState v-if="!riskPrediction?.risk_factors.length" text="未发现明显风险" description="当前数据未触发风险规则" accent="var(--color-success)" />
                <div v-else class="factor-list">
                  <article v-for="factor in riskPrediction.risk_factors" :key="factor.category">
                    <div>
                      <el-tag :type="riskLevelType(factor.severity)" size="small">{{ factor.label }}</el-tag>
                      <strong>+{{ factor.score }}</strong>
                    </div>
                    <p>{{ factor.detail }}</p>
                  </article>
                </div>
                <ul v-if="riskPrediction?.recommendations.length" class="recommendation-list">
                  <li v-for="item in riskPrediction.recommendations" :key="item">{{ item }}</li>
                </ul>
              </section>

              <section>
                <h3>材料检查</h3>
                <div v-if="materialCheck" class="material-list">
                  <article v-for="item in materialCheck.checklist" :key="item.key">
                    <el-icon :class="`status-${item.status}`">
                      <CircleCheck v-if="item.status === 'complete'" />
                      <Warning v-else />
                    </el-icon>
                    <div><strong>{{ item.label }}</strong><p>{{ item.detail }}</p></div>
                  </article>
                </div>
                <EmptyState v-else text="暂无材料检查结果" description="点击重新分析获取最新结果" accent="var(--color-primary)" />
              </section>
            </div>

            <section class="smart-review-panel">
              <header>
                <div><h3>智能复盘草案</h3><p>{{ smartReview?.summary || '分析后将基于项目事实生成复盘草案。' }}</p></div>
                <el-button v-if="canManageReview && smartReview" type="primary" :icon="DocumentAdd" @click="useSmartReview">
                  带入正式复盘
                </el-button>
              </header>
              <div v-if="smartReview" class="smart-review-grid">
                <div><span>任务完成</span><strong>{{ smartReview.task_statistics.done }}/{{ smartReview.task_statistics.total }}</strong></div>
                <div><span>逾期任务</span><strong>{{ smartReview.task_statistics.overdue }}</strong></div>
                <div><span>问题领域</span><strong>{{ smartReview.problem_areas.length }}</strong></div>
                <div><span>改进建议</span><strong>{{ smartReview.improvements.length }}</strong></div>
              </div>
            </section>
          </section>
        </el-tab-pane>

        <el-tab-pane name="milestones">
          <template #label><span class="tab-label"><Flag />里程碑 <small>{{ milestones.length }}</small></span></template>
          <section class="workspace-section">
            <header class="section-heading">
              <div><h2>项目里程碑</h2><p>明确关键交付节点与计划日期。</p></div>
              <el-button v-if="canManageProject" type="primary" :icon="Plus" @click="openMilestoneDialog()">新建里程碑</el-button>
            </header>
            <EmptyState v-if="!milestones.length" text="暂无里程碑" description="建立首个关键交付节点" accent="var(--color-primary)" />
            <div v-else class="milestone-list">
              <article v-for="item in milestones" :key="item.id" class="milestone-item" :class="{ 'is-complete': item.is_completed }">
                <button class="milestone-toggle" type="button" :aria-label="item.is_completed ? '标记未完成' : '标记完成'" @click="handleToggleMilestone(item)">
                  <CircleCheckFilled v-if="item.is_completed" />
                  <CircleCheck v-else />
                </button>
                <div class="item-main">
                  <header><strong>{{ item.title }}</strong><span>{{ item.due_date ? formatDate(item.due_date) : '未设置日期' }}</span></header>
                  <p>{{ item.description || '暂无描述' }}</p>
                </div>
                <div v-if="canManageProject" class="row-actions">
                  <el-tooltip content="编辑里程碑"><el-button circle :icon="Edit" @click="openMilestoneDialog(item)" /></el-tooltip>
                  <el-tooltip content="删除里程碑"><el-button circle type="danger" plain :icon="Delete" @click="removeMilestone(item)" /></el-tooltip>
                </div>
              </article>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane name="risks">
          <template #label><span class="tab-label"><Warning />风险 <small>{{ openRiskCount }}</small></span></template>
          <section class="workspace-section">
            <header class="section-heading">
              <div><h2>风险台账</h2><p>识别风险、记录缓解措施并跟踪关闭。</p></div>
              <el-button v-if="canManageProject" type="primary" :icon="Plus" @click="openRiskDialog()">登记风险</el-button>
            </header>
            <EmptyState v-if="!risks.length" text="暂无风险记录" description="当前项目尚未登记风险" accent="var(--color-success)" />
            <div v-else class="risk-list">
              <article v-for="item in risks" :key="item.id" class="risk-item">
                <div class="risk-heading">
                  <div>
                    <el-tag :type="riskLevelType(item.level)" size="small">{{ item.level_display || riskLevelLabel(item.level) }}</el-tag>
                    <el-tag :type="item.status === 'closed' ? 'success' : item.status === 'mitigating' ? 'warning' : 'danger'" size="small" effect="plain">
                      {{ item.status_display || riskStatusLabel(item.status) }}
                    </el-tag>
                  </div>
                  <span>{{ formatDate(item.identified_at) }}</span>
                </div>
                <h3>{{ item.title }}</h3>
                <p>{{ item.description || '暂无风险描述' }}</p>
                <div class="mitigation"><strong>缓解措施</strong><span>{{ item.mitigation_plan || '尚未制定' }}</span></div>
                <footer v-if="canManageProject">
                  <el-button v-if="item.status !== 'closed'" type="success" link :icon="CircleCheck" @click="handleResolveRisk(item)">关闭风险</el-button>
                  <el-button link :icon="Edit" @click="openRiskDialog(item)">编辑</el-button>
                  <el-button type="danger" link :icon="Delete" @click="removeRisk(item)">删除</el-button>
                </footer>
              </article>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane name="discussions">
          <template #label><span class="tab-label"><ChatDotRound />讨论 <small>{{ discussions.length }}</small></span></template>
          <section class="workspace-section">
            <header class="section-heading">
              <div><h2>项目讨论</h2><p>围绕决策、方案和问题展开持续讨论。</p></div>
              <el-button type="primary" :icon="Plus" @click="openDiscussionForm()">发起讨论</el-button>
            </header>
            <EmptyState v-if="!discussions.length" text="暂无讨论" description="发起第一个项目话题" accent="var(--color-primary)" />
            <div v-else class="discussion-list">
              <article
                v-for="topic in discussions"
                :key="topic.id"
                class="discussion-item"
                role="button"
                tabindex="0"
                @click="openDiscussion(topic)"
                @keydown.enter="openDiscussion(topic)"
                @keydown.space.prevent="openDiscussion(topic)"
              >
                <div class="discussion-state">
                  <el-icon v-if="topic.is_pinned"><Top /></el-icon>
                  <el-icon v-else><ChatDotRound /></el-icon>
                </div>
                <div class="item-main">
                  <header>
                    <strong>{{ topic.title }}</strong>
                    <el-tag v-if="topic.is_closed" type="info" size="small">已关闭</el-tag>
                  </header>
                  <p>{{ topic.author_name || '成员' }} · {{ formatDateTime(topic.updated_at) }}</p>
                </div>
                <span class="discussion-count"><ChatLineRound />{{ topic.reply_count }}</span>
              </article>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane name="knowledge">
          <template #label><span class="tab-label"><Collection />知识库 <small>{{ articles.length }}</small></span></template>
          <section class="workspace-section">
            <header class="section-heading">
              <div><h2>项目知识库</h2><p>沉淀指南、模板、常见问题和实战经验。</p></div>
              <el-button type="primary" :icon="Plus" @click="openArticleForm()">撰写文章</el-button>
            </header>
            <EmptyState v-if="!articles.length" text="暂无知识文章" description="将可复用经验沉淀到项目知识库" accent="var(--color-primary)" />
            <div v-else class="article-grid">
              <article
                v-for="article in articles"
                :key="article.id"
                class="article-item"
                role="button"
                tabindex="0"
                @click="openArticle(article)"
                @keydown.enter="openArticle(article)"
                @keydown.space.prevent="openArticle(article)"
              >
                <header>
                  <el-tag size="small" effect="plain">{{ article.category_display || knowledgeCategoryLabel(article.category) }}</el-tag>
                  <span><View />{{ article.view_count }}</span>
                </header>
                <h3>{{ article.title }}</h3>
                <p>{{ article.tags || '暂无标签' }}</p>
                <footer>{{ article.author_name || '成员' }} · {{ formatDate(article.created_at) }}</footer>
              </article>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane name="review">
          <template #label><span class="tab-label"><DocumentChecked />复盘</span></template>
          <section class="workspace-section">
            <header class="section-heading">
              <div><h2>项目复盘</h2><p>形成可审阅、可追踪的正式复盘记录。</p></div>
              <el-button v-if="canManageReview" type="primary" :icon="review ? Edit : Plus" @click="openReviewForm()">
                {{ review ? '编辑复盘' : '创建复盘' }}
              </el-button>
            </header>
            <EmptyState v-if="!review" text="尚未创建正式复盘" description="老师或管理员可基于项目事实建立复盘" accent="var(--color-primary)" />
            <div v-else class="review-document">
              <header>
                <div>
                  <el-tag :type="reviewStatusType(review.status)">{{ review.status_display || reviewStatusLabel(review.status) }}</el-tag>
                  <span>复盘人：{{ review.reviewer_name || '尚未提交' }}</span>
                </div>
                <div v-if="canManageReview" class="review-actions">
                  <el-button v-if="review.status === 'draft'" type="primary" :icon="Promotion" @click="handleSubmitReview">提交复盘</el-button>
                  <el-button v-if="review.status === 'submitted'" type="success" :icon="CircleCheck" @click="handleApproveReview">完成审阅</el-button>
                  <el-button type="danger" plain :icon="Delete" @click="removeReview">删除</el-button>
                </div>
              </header>
              <div class="review-scores">
                <div v-for="item in reviewScoreItems" :key="item.label"><span>{{ item.label }}</span><strong>{{ item.value ?? '-' }}</strong></div>
              </div>
              <div class="review-sections">
                <article v-for="item in reviewTextItems" :key="item.label"><h3>{{ item.label }}</h3><p>{{ item.value || '暂无内容' }}</p></article>
              </div>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane v-if="isInternalMember" name="templates">
          <template #label><span class="tab-label"><Files />模板 <small>{{ templates.length }}</small></span></template>
          <section class="workspace-section">
            <header class="section-heading">
              <div><h2>项目模板</h2><p>维护可复用的任务与里程碑结构。</p></div>
              <el-button v-if="canManageReview" type="primary" :icon="Plus" @click="openTemplateForm()">新建模板</el-button>
            </header>
            <EmptyState v-if="!templates.length" text="暂无项目模板" description="创建标准项目结构以便快速复用" accent="var(--color-primary)" />
            <div v-else class="template-list">
              <article v-for="item in templates" :key="item.id" class="template-item">
                <div class="item-main">
                  <header>
                    <strong>{{ item.name }}</strong>
                    <el-tag :type="item.is_active ? 'success' : 'info'" size="small">{{ item.is_active ? '启用' : '停用' }}</el-tag>
                  </header>
                  <p>{{ item.description || '暂无描述' }}</p>
                  <span>{{ item.category || '未分类' }} · {{ item.config.milestones?.length || 0 }} 个里程碑 · {{ item.config.tasks?.length || 0 }} 个任务</span>
                </div>
                <div v-if="canManageReview" class="template-actions">
                  <el-button type="primary" :icon="CopyDocument" @click="openInstantiate(item)">创建项目</el-button>
                  <el-tooltip content="编辑模板"><el-button circle :icon="Edit" @click="openTemplateForm(item)" /></el-tooltip>
                  <el-tooltip content="删除模板"><el-button circle type="danger" plain :icon="Delete" @click="removeTemplate(item)" /></el-tooltip>
                </div>
              </article>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>

      <EmptyState v-else-if="!loading && !loadError" text="项目不存在" description="项目可能已删除或你无权访问" accent="var(--color-danger)" />
    </div>

    <el-dialog v-model="milestoneDialogVisible" :title="editingMilestone ? '编辑里程碑' : '新建里程碑'" width="min(560px, 92vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="saveMilestone">
        <el-form-item label="标题" required><el-input v-model="milestoneForm.title" maxlength="200" show-word-limit /></el-form-item>
        <el-form-item label="描述"><el-input v-model="milestoneForm.description" type="textarea" :rows="3" /></el-form-item>
        <div class="dialog-grid">
          <el-form-item label="截止日期"><el-date-picker v-model="milestoneForm.due_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" /></el-form-item>
          <el-form-item label="排序"><el-input-number v-model="milestoneForm.sort_order" :min="0" :max="999" controls-position="right" /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="milestoneDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveMilestone">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="riskDialogVisible" :title="editingRisk ? '编辑风险' : '登记风险'" width="min(620px, 92vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="saveRisk">
        <el-form-item label="风险标题" required><el-input v-model="riskForm.title" maxlength="200" show-word-limit /></el-form-item>
        <div class="dialog-grid">
          <el-form-item label="级别" required><el-select v-model="riskForm.level"><el-option v-for="option in riskLevelOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item>
          <el-form-item label="状态"><el-select v-model="riskForm.status"><el-option label="开放" value="open" /><el-option label="处理中" value="mitigating" /><el-option label="已关闭" value="closed" /></el-select></el-form-item>
        </div>
        <el-form-item label="风险描述"><el-input v-model="riskForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="缓解措施"><el-input v-model="riskForm.mitigation_plan" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="riskDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveRisk">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="discussionFormVisible" :title="editingDiscussion ? '编辑讨论' : '发起讨论'" width="min(640px, 92vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="saveDiscussion">
        <el-form-item label="标题" required><el-input v-model="discussionForm.title" maxlength="200" show-word-limit /></el-form-item>
        <el-form-item label="内容" required><el-input v-model="discussionForm.content" type="textarea" :rows="6" maxlength="5000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer><el-button @click="discussionFormVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveDiscussion">发布</el-button></template>
    </el-dialog>

    <el-drawer v-model="discussionDetailVisible" :size="drawerSize" destroy-on-close>
      <template #header><div class="drawer-title"><el-tag v-if="selectedDiscussion?.is_pinned" size="small">置顶</el-tag><strong>{{ selectedDiscussion?.title }}</strong></div></template>
      <div v-if="selectedDiscussion" class="discussion-detail">
        <div class="detail-meta"><span>{{ selectedDiscussion.author_name }}</span><span>{{ formatDateTime(selectedDiscussion.created_at) }}</span></div>
        <p class="detail-content-text">{{ selectedDiscussion.content }}</p>
        <div class="detail-actions">
          <el-button v-if="canModifyDiscussion(selectedDiscussion)" :icon="Edit" @click="editSelectedDiscussion">编辑</el-button>
          <el-button v-if="isStaff" :icon="Top" @click="handleToggleDiscussionPin">{{ selectedDiscussion.is_pinned ? '取消置顶' : '置顶' }}</el-button>
          <el-button v-if="isStaff" :icon="Lock" @click="handleToggleDiscussionClose">{{ selectedDiscussion.is_closed ? '重新开启' : '关闭' }}</el-button>
          <el-button v-if="canModifyDiscussion(selectedDiscussion)" type="danger" plain :icon="Delete" @click="removeDiscussion(selectedDiscussion)">删除</el-button>
        </div>
        <el-divider content-position="left">{{ discussionReplies.length }} 条回复</el-divider>
        <div class="reply-list">
          <article v-for="reply in discussionReplies" :key="reply.id"><el-avatar :size="30">{{ initial(reply.author_name) }}</el-avatar><div><header><strong>{{ reply.author_name }}</strong><span>{{ formatDateTime(reply.created_at) }}</span></header><p>{{ reply.content }}</p></div></article>
          <EmptyState v-if="!discussionReplies.length" text="暂无回复" description="继续这个话题" accent="var(--color-primary)" />
        </div>
        <div v-if="!selectedDiscussion.is_closed" class="drawer-composer"><el-input v-model="discussionReplyDraft" type="textarea" :rows="3" placeholder="回复讨论" /><el-button type="primary" :loading="saving" @click="sendDiscussionReply">发送回复</el-button></div>
        <el-alert v-else title="该讨论已关闭，暂不能回复" type="info" :closable="false" show-icon />
      </div>
    </el-drawer>

    <el-dialog v-model="articleFormVisible" :title="editingArticle ? '编辑文章' : '撰写文章'" width="min(720px, 94vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="saveArticle">
        <el-form-item label="标题" required><el-input v-model="articleForm.title" maxlength="200" show-word-limit /></el-form-item>
        <div class="dialog-grid">
          <el-form-item label="分类"><el-select v-model="articleForm.category"><el-option v-for="option in knowledgeCategoryOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item>
          <el-form-item label="发布状态"><el-switch v-model="articleForm.is_published" active-text="已发布" inactive-text="草稿" /></el-form-item>
        </div>
        <el-form-item label="标签"><el-input v-model="articleForm.tags" placeholder="多个标签用英文逗号分隔" /></el-form-item>
        <el-form-item label="正文" required><el-input v-model="articleForm.content" type="textarea" :rows="10" maxlength="20000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer><el-button @click="articleFormVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveArticle">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="articleDetailVisible" :size="drawerSize" destroy-on-close>
      <template #header><div class="drawer-title"><el-tag size="small">{{ selectedArticle?.category_display || knowledgeCategoryLabel(selectedArticle?.category) }}</el-tag><strong>{{ selectedArticle?.title }}</strong></div></template>
      <div v-if="selectedArticle" class="article-detail">
        <div class="detail-meta"><span>{{ selectedArticle.author_name }}</span><span>{{ formatDateTime(selectedArticle.created_at) }} · {{ selectedArticle.view_count }} 次浏览</span></div>
        <div class="article-tags"><el-tag v-for="tag in selectedArticle.tag_list || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag></div>
        <p class="detail-content-text">{{ selectedArticle.content }}</p>
        <div v-if="canModifyArticle(selectedArticle)" class="detail-actions"><el-button :icon="Edit" @click="editSelectedArticle">编辑</el-button><el-button type="danger" plain :icon="Delete" @click="removeArticle(selectedArticle)">删除</el-button></div>
      </div>
    </el-drawer>

    <el-dialog v-model="reviewDialogVisible" :title="review ? '编辑项目复盘' : '创建项目复盘'" width="min(820px, 96vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="saveReview">
        <el-form-item label="项目总结"><el-input v-model="reviewForm.summary" type="textarea" :rows="3" /></el-form-item>
        <div class="review-form-grid">
          <el-form-item label="主要成果"><el-input v-model="reviewForm.achievements" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="遇到的问题"><el-input v-model="reviewForm.problems" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="经验教训"><el-input v-model="reviewForm.lessons" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="改进建议"><el-input v-model="reviewForm.improvements" type="textarea" :rows="4" /></el-form-item>
        </div>
        <el-form-item label="团队反馈"><el-input v-model="reviewForm.team_feedback" type="textarea" :rows="3" /></el-form-item>
        <div class="score-form-grid"><el-form-item v-for="field in reviewScoreFields" :key="field.key" :label="field.label"><el-rate v-model="reviewForm[field.key]" /></el-form-item></div>
      </el-form>
      <template #footer><el-button @click="reviewDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveReview">保存草稿</el-button></template>
    </el-dialog>

    <el-dialog v-model="templateDialogVisible" :title="editingTemplate ? '编辑项目模板' : '新建项目模板'" width="min(720px, 94vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="saveTemplate">
        <el-form-item label="模板名称" required><el-input v-model="templateForm.name" maxlength="200" show-word-limit /></el-form-item>
        <div class="dialog-grid"><el-form-item label="分类"><el-input v-model="templateForm.category" /></el-form-item><el-form-item label="启用状态"><el-switch v-model="templateForm.is_active" active-text="启用" inactive-text="停用" /></el-form-item></div>
        <el-form-item label="描述"><el-input v-model="templateForm.description" type="textarea" :rows="3" /></el-form-item>
        <section class="template-builder-section">
          <header><div><h3>里程碑结构</h3><span>{{ templateMilestones.length }} 项</span></div><el-button :icon="Plus" @click="addTemplateMilestone">添加里程碑</el-button></header>
          <EmptyState v-if="!templateMilestones.length" text="暂无预设里程碑" description="实例化后不会自动创建里程碑" accent="var(--color-primary)" />
          <div v-else class="template-builder-list">
            <div v-for="(item, index) in templateMilestones" :key="`milestone-${index}`" class="template-builder-row">
              <el-input v-model="item.title" :aria-label="`里程碑 ${index + 1} 标题`" placeholder="里程碑标题" />
              <el-date-picker v-model="item.due_date" type="date" value-format="YYYY-MM-DD" :aria-label="`里程碑 ${index + 1} 日期`" placeholder="截止日期" />
              <el-tooltip content="移除里程碑"><el-button circle type="danger" plain :icon="Delete" :aria-label="`移除里程碑 ${index + 1}`" @click="templateMilestones.splice(index, 1)" /></el-tooltip>
            </div>
          </div>
        </section>
        <section class="template-builder-section">
          <header><div><h3>任务结构</h3><span>{{ templateTasks.length }} 项</span></div><el-button :icon="Plus" @click="addTemplateTask">添加任务</el-button></header>
          <EmptyState v-if="!templateTasks.length" text="暂无预设任务" description="实例化后不会自动创建任务" accent="var(--color-primary)" />
          <div v-else class="template-builder-list">
            <div v-for="(item, index) in templateTasks" :key="`task-${index}`" class="template-builder-row task-builder-row">
              <el-input v-model="item.title" :aria-label="`任务 ${index + 1} 标题`" placeholder="任务标题" />
              <el-select v-model="item.priority" :aria-label="`任务 ${index + 1} 优先级`"><el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /><el-option label="紧急" value="urgent" /></el-select>
              <el-tooltip content="移除任务"><el-button circle type="danger" plain :icon="Delete" :aria-label="`移除任务 ${index + 1}`" @click="templateTasks.splice(index, 1)" /></el-tooltip>
            </div>
          </div>
        </section>
      </el-form>
      <template #footer><el-button @click="templateDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveTemplate">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="instantiateDialogVisible" title="从模板创建项目" width="min(640px, 94vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="instantiateTemplate">
        <div class="dialog-grid"><el-form-item label="项目名称" required><el-input v-model="instantiateForm.name" /></el-form-item><el-form-item label="项目编号" required><el-input v-model="instantiateForm.code" /></el-form-item></div>
        <el-form-item label="负责人" required><el-select v-model="instantiateForm.leader" filterable><el-option v-for="user in leaderOptions" :key="user.id" :label="user.name || user.username" :value="user.id" /></el-select></el-form-item>
        <el-form-item label="项目简介"><el-input v-model="instantiateForm.intro" type="textarea" :rows="3" /></el-form-item>
        <div class="dialog-grid"><el-form-item label="开始日期"><el-date-picker v-model="instantiateForm.start_date" type="date" value-format="YYYY-MM-DD" /></el-form-item><el-form-item label="计划结束"><el-date-picker v-model="instantiateForm.planned_end_date" type="date" value-format="YYYY-MM-DD" /></el-form-item></div>
      </el-form>
      <template #footer><el-button @click="instantiateDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="instantiateTemplate">创建项目</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ChatDotRound,
  ChatLineRound,
  CircleCheck,
  CircleCheckFilled,
  Collection,
  CopyDocument,
  DataAnalysis,
  Delete,
  DocumentAdd,
  DocumentChecked,
  Edit,
  Files,
  Flag,
  FolderOpened,
  Lock,
  Plus,
  Promotion,
  Refresh,
  Top,
  View,
  Warning,
} from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { getUsers } from '@/api/users'
import {
  approveProjectReview,
  createDiscussionTopic,
  createKnowledgeArticle,
  createMilestone,
  createProjectReview,
  createProjectRisk,
  createProjectTemplate,
  deleteDiscussionTopic,
  deleteKnowledgeArticle,
  deleteMilestone,
  deleteProjectReview,
  deleteProjectRisk,
  deleteProjectTemplate,
  getDiscussionReplies,
  getDiscussionTopic,
  getDiscussionTopics,
  getKnowledgeArticle,
  getKnowledgeArticles,
  getMaterialCheck,
  getMilestones,
  getProject,
  getProjectHealthScore,
  getProjectReviews,
  getProjectRisks,
  getProjectTemplates,
  getRiskPrediction,
  getSmartReview,
  instantiateProjectTemplate,
  replyDiscussionTopic,
  resolveProjectRisk,
  submitProjectReview,
  toggleDiscussionClose,
  toggleDiscussionPin,
  toggleMilestone,
  updateDiscussionTopic,
  updateKnowledgeArticle,
  updateMilestone,
  updateProjectReview,
  updateProjectRisk,
  updateProjectTemplate,
  type DiscussionReply,
  type DiscussionTopic,
  type KnowledgeArticle,
  type KnowledgeCategory,
  type MaterialCheck,
  type MaterialStatus,
  type Milestone,
  type ProjectHealthScore,
  type ProjectReview,
  type ProjectRisk,
  type ProjectRiskLevel,
  type ProjectTemplate,
  type ProjectTemplateConfig,
  type RiskPrediction,
  type SmartReview,
} from '@/api/projects'
import { useUserStore } from '@/stores/user'
import { formatDate, formatDateTime } from '@/utils/format'
import { positiveQueryId } from '@/utils/globalSearch'
import type { Project, User } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const projectId = Number(route.params.id)

const activeTab = ref('insights')
const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const project = ref<Project | null>(null)
const milestones = ref<Milestone[]>([])
const risks = ref<ProjectRisk[]>([])
const discussions = ref<DiscussionTopic[]>([])
const articles = ref<KnowledgeArticle[]>([])
const review = ref<ProjectReview | null>(null)
const templates = ref<ProjectTemplate[]>([])
const leaderOptions = ref<User[]>([])

const insightsLoading = ref(false)
const insightsError = ref('')
const riskPrediction = ref<RiskPrediction | null>(null)
const healthScore = ref<ProjectHealthScore | null>(null)
const smartReview = ref<SmartReview | null>(null)
const materialCheck = ref<MaterialCheck | null>(null)

const milestoneDialogVisible = ref(false)
const editingMilestone = ref<Milestone | null>(null)
const milestoneForm = reactive({ title: '', description: '', due_date: '', sort_order: 0 })
const riskDialogVisible = ref(false)
const editingRisk = ref<ProjectRisk | null>(null)
const riskForm = reactive({ title: '', description: '', level: 'medium' as ProjectRiskLevel, status: 'open' as ProjectRisk['status'], mitigation_plan: '' })

const discussionFormVisible = ref(false)
const editingDiscussion = ref<DiscussionTopic | null>(null)
const discussionForm = reactive({ title: '', content: '' })
const discussionDetailVisible = ref(false)
const selectedDiscussion = ref<DiscussionTopic | null>(null)
const discussionReplies = ref<DiscussionReply[]>([])
const discussionReplyDraft = ref('')

const articleFormVisible = ref(false)
const editingArticle = ref<KnowledgeArticle | null>(null)
const articleForm = reactive({ title: '', content: '', category: 'other' as KnowledgeCategory, tags: '', is_published: true })
const articleDetailVisible = ref(false)
const selectedArticle = ref<KnowledgeArticle | null>(null)

type ReviewScoreKey = 'overall_score' | 'schedule_score' | 'budget_score' | 'team_score' | 'quality_score'
const reviewDialogVisible = ref(false)
const reviewForm = reactive<Record<ReviewScoreKey, number> & {
  summary: string
  achievements: string
  problems: string
  lessons: string
  improvements: string
  team_feedback: string
}>({
  summary: '', achievements: '', problems: '', lessons: '', improvements: '', team_feedback: '',
  overall_score: 0, schedule_score: 0, budget_score: 0, team_score: 0, quality_score: 0,
})

const templateDialogVisible = ref(false)
const editingTemplate = ref<ProjectTemplate | null>(null)
const templateForm = reactive({ name: '', description: '', category: '', is_active: true })
const templateMilestones = ref<Array<{ title: string; description: string; due_date: string; sort_order: number }>>([])
const templateTasks = ref<Array<{ title: string; description: string; priority: string }>>([])
const instantiateDialogVisible = ref(false)
const instantiatingTemplate = ref<ProjectTemplate | null>(null)
const instantiateForm = reactive({ name: '', code: '', leader: undefined as number | undefined, intro: '', start_date: '', planned_end_date: '' })

const isStaff = computed(() => ['teacher', 'sys_admin'].includes(userStore.role))
const isInternalMember = computed(() => !['external', 'exited'].includes(userStore.userInfo?.membership_status || 'active'))
const canManageProject = computed(() => isStaff.value || project.value?.leader === userStore.userInfo?.id)
const canManageReview = computed(() => isStaff.value)
const completedMilestones = computed(() => milestones.value.filter((item) => item.is_completed).length)
const openRiskCount = computed(() => risks.value.filter((item) => item.status !== 'closed').length)
const drawerSize = computed(() => window.innerWidth <= 768 ? '100%' : 'min(680px, 70vw)')
const healthGradeType = computed(() => {
  const grade = healthScore.value?.grade
  if (grade === 'A') return 'success'
  if (grade === 'B') return 'primary'
  if (grade === 'C') return 'warning'
  return grade ? 'danger' : 'info'
})
const reviewScoreFields: Array<{ key: ReviewScoreKey; label: string }> = [
  { key: 'overall_score', label: '总体评分' },
  { key: 'schedule_score', label: '进度管理' },
  { key: 'budget_score', label: '经费管理' },
  { key: 'team_score', label: '团队协作' },
  { key: 'quality_score', label: '成果质量' },
]
const reviewScoreItems = computed(() => reviewScoreFields.map((item) => ({ label: item.label, value: review.value?.[item.key] })))
const reviewTextItems = computed(() => review.value ? [
  { label: '项目总结', value: review.value.summary },
  { label: '主要成果', value: review.value.achievements },
  { label: '遇到的问题', value: review.value.problems },
  { label: '经验教训', value: review.value.lessons },
  { label: '改进建议', value: review.value.improvements },
  { label: '团队反馈', value: review.value.team_feedback },
] : [])

const riskLevelOptions: Array<{ value: ProjectRiskLevel; label: string }> = [
  { value: 'low', label: '低' }, { value: 'medium', label: '中' }, { value: 'high', label: '高' }, { value: 'critical', label: '严重' },
]
const knowledgeCategoryOptions: Array<{ value: KnowledgeCategory; label: string }> = [
  { value: 'guide', label: '指南' }, { value: 'template', label: '模板' }, { value: 'faq', label: '常见问题' }, { value: 'experience', label: '经验分享' }, { value: 'other', label: '其他' },
]

function initial(value?: string): string { return value?.trim().slice(0, 1).toUpperCase() || '?' }
function riskLevelLabel(level?: ProjectRiskLevel): string { return ({ low: '低风险', medium: '中风险', high: '高风险', critical: '严重风险' } as Record<string, string>)[level || ''] || '待分析' }
function riskLevelType(level?: ProjectRiskLevel): 'success' | 'warning' | 'danger' | 'info' { return level === 'low' ? 'success' : level === 'medium' ? 'warning' : level ? 'danger' : 'info' }
function riskStatusLabel(status: ProjectRisk['status']): string { return ({ open: '开放', mitigating: '处理中', closed: '已关闭' })[status] }
function knowledgeCategoryLabel(category?: KnowledgeCategory): string { return knowledgeCategoryOptions.find((item) => item.value === category)?.label || '其他' }
function materialStatusLabel(status?: MaterialStatus): string { return ({ complete: '材料齐备', incomplete: '部分齐备', missing: '材料缺失' } as Record<string, string>)[status || ''] || '待检查' }
function materialStatusType(status?: MaterialStatus): 'success' | 'warning' | 'danger' | 'info' { return status === 'complete' ? 'success' : status === 'incomplete' ? 'warning' : status === 'missing' ? 'danger' : 'info' }
function reviewStatusLabel(status: ProjectReview['status']): string { return ({ draft: '草稿', submitted: '已提交', reviewed: '已审阅' })[status] }
function reviewStatusType(status: ProjectReview['status']): 'info' | 'warning' | 'success' { return status === 'reviewed' ? 'success' : status === 'submitted' ? 'warning' : 'info' }
function openProjectDetail(): void { router.push({ name: 'ProjectDetail', params: { id: projectId } }) }

async function loadMilestones(): Promise<void> { milestones.value = (await getMilestones({ project: projectId, page_size: 100, ordering: 'sort_order' })).results }
async function loadRisks(): Promise<void> { risks.value = (await getProjectRisks({ project: projectId, page_size: 100, ordering: '-identified_at' })).results }
async function loadDiscussions(): Promise<void> { discussions.value = (await getDiscussionTopics({ project: projectId, page_size: 100, ordering: '-is_pinned,-updated_at' })).results }
async function loadArticles(): Promise<void> { articles.value = (await getKnowledgeArticles({ project: projectId, page_size: 100, ordering: '-created_at' })).results }
async function loadReview(): Promise<void> { review.value = (await getProjectReviews({ project: projectId, page_size: 1 })).results[0] || null }
async function loadTemplates(): Promise<void> { templates.value = (await getProjectTemplates({ page_size: 100, ordering: '-created_at' })).results }

async function loadWorkspace(): Promise<void> {
  if (!Number.isInteger(projectId) || projectId <= 0) { loadError.value = '项目编号无效'; return }
  loading.value = true
  loadError.value = ''
  try {
    project.value = await getProject(projectId)
    await Promise.all([loadMilestones(), loadRisks(), loadDiscussions(), loadArticles(), loadReview(), ...(isInternalMember.value ? [loadTemplates()] : [])])
    if (isStaff.value) {
      try { leaderOptions.value = (await getUsers({ page_size: 100, is_active: true })).results } catch { leaderOptions.value = [] }
    }
    if (!leaderOptions.value.some((item) => item.id === project.value?.leader) && project.value) {
      leaderOptions.value.push({ id: project.value.leader, name: project.value.leader_name || `用户 ${project.value.leader}`, username: '', email: '', global_role: 'member', is_active: true, date_joined: '' })
    }
    if (isInternalMember.value) await loadInsights()
    else activeTab.value = 'milestones'
    await openRequestedWorkspaceItem()
  } catch {
    loadError.value = '项目协作数据加载失败，请检查访问权限或网络连接。'
  } finally { loading.value = false }
}

async function openRequestedWorkspaceItem(): Promise<void> {
  const requestedTab = String(route.query.tab || '')
  if (requestedTab === 'discussions') {
    activeTab.value = 'discussions'
    const discussionId = positiveQueryId(route.query.discussion_id)
    if (discussionId) {
      const topic = discussions.value.find((item) => item.id === discussionId)
      if (topic) await openDiscussion(topic)
      else {
        try {
          selectedDiscussion.value = await getDiscussionTopic(discussionId)
          discussionReplies.value = await getDiscussionReplies(discussionId)
          discussionDetailVisible.value = true
        } catch {}
      }
    }
  } else if (requestedTab === 'knowledge') {
    activeTab.value = 'knowledge'
    const articleId = positiveQueryId(route.query.article_id)
    if (articleId) {
      const article = articles.value.find((item) => item.id === articleId)
      if (article) await openArticle(article)
      else {
        try {
          selectedArticle.value = await getKnowledgeArticle(articleId)
          articleDetailVisible.value = true
        } catch {}
      }
    }
  }
}

async function loadInsights(): Promise<void> {
  if (!isInternalMember.value) return
  insightsLoading.value = true
  insightsError.value = ''
  const results = await Promise.allSettled([getRiskPrediction(projectId), getProjectHealthScore(projectId), getSmartReview(projectId), getMaterialCheck(projectId)])
  if (results[0].status === 'fulfilled') riskPrediction.value = results[0].value
  if (results[1].status === 'fulfilled') healthScore.value = results[1].value
  if (results[2].status === 'fulfilled') smartReview.value = results[2].value
  if (results[3].status === 'fulfilled') materialCheck.value = results[3].value
  if (results.some((item) => item.status === 'rejected')) insightsError.value = '部分分析暂时不可用，已保留成功返回的结果。'
  insightsLoading.value = false
}

function handleTabChange(name: string | number): void { if (name === 'insights' && !healthScore.value) loadInsights() }

function openMilestoneDialog(item?: Milestone): void {
  editingMilestone.value = item || null
  Object.assign(milestoneForm, { title: item?.title || '', description: item?.description || '', due_date: item?.due_date || '', sort_order: item?.sort_order ?? milestones.value.length })
  milestoneDialogVisible.value = true
}
async function saveMilestone(): Promise<void> {
  if (!milestoneForm.title.trim()) { ElMessage.warning('请输入里程碑标题'); return }
  saving.value = true
  try {
    const payload = { project: projectId, title: milestoneForm.title.trim(), description: milestoneForm.description.trim(), due_date: milestoneForm.due_date || null, sort_order: milestoneForm.sort_order }
    if (editingMilestone.value) await updateMilestone(editingMilestone.value.id, payload); else await createMilestone(payload)
    ElMessage.success(editingMilestone.value ? '里程碑已更新' : '里程碑已创建'); milestoneDialogVisible.value = false; await loadMilestones()
  } catch {} finally { saving.value = false }
}
async function handleToggleMilestone(item: Milestone): Promise<void> { try { await toggleMilestone(item.id); await loadMilestones() } catch {} }
async function removeMilestone(item: Milestone): Promise<void> { try { await ElMessageBox.confirm(`确定删除里程碑“${item.title}”吗？`, '删除里程碑', { type: 'warning' }); await deleteMilestone(item.id); ElMessage.success('里程碑已删除'); await loadMilestones() } catch {} }

function openRiskDialog(item?: ProjectRisk): void {
  editingRisk.value = item || null
  Object.assign(riskForm, { title: item?.title || '', description: item?.description || '', level: item?.level || 'medium', status: item?.status || 'open', mitigation_plan: item?.mitigation_plan || '' })
  riskDialogVisible.value = true
}
async function saveRisk(): Promise<void> {
  if (!riskForm.title.trim()) { ElMessage.warning('请输入风险标题'); return }
  saving.value = true
  try {
    const payload = { project: projectId, title: riskForm.title.trim(), description: riskForm.description.trim(), level: riskForm.level, status: riskForm.status, mitigation_plan: riskForm.mitigation_plan.trim() }
    if (editingRisk.value) await updateProjectRisk(editingRisk.value.id, payload); else await createProjectRisk(payload)
    ElMessage.success(editingRisk.value ? '风险已更新' : '风险已登记'); riskDialogVisible.value = false; await loadRisks()
  } catch {} finally { saving.value = false }
}
async function handleResolveRisk(item: ProjectRisk): Promise<void> { try { await ElMessageBox.confirm(`确认风险“${item.title}”已经解除吗？`, '关闭风险', { type: 'warning' }); await resolveProjectRisk(item.id); ElMessage.success('风险已关闭'); await loadRisks(); if (isInternalMember.value) loadInsights() } catch {} }
async function removeRisk(item: ProjectRisk): Promise<void> { try { await ElMessageBox.confirm(`确定删除风险“${item.title}”吗？`, '删除风险', { type: 'warning' }); await deleteProjectRisk(item.id); ElMessage.success('风险已删除'); await loadRisks() } catch {} }

function canModifyDiscussion(item: DiscussionTopic): boolean { return isStaff.value || item.author === userStore.userInfo?.id }
function openDiscussionForm(item?: DiscussionTopic): void { editingDiscussion.value = item || null; discussionForm.title = item?.title || ''; discussionForm.content = item?.content || ''; discussionFormVisible.value = true }
async function saveDiscussion(): Promise<void> {
  if (!discussionForm.title.trim() || !discussionForm.content.trim()) { ElMessage.warning('请填写讨论标题和内容'); return }
  saving.value = true
  try {
    const payload = { project: projectId, title: discussionForm.title.trim(), content: discussionForm.content.trim() }
    const saved = editingDiscussion.value ? await updateDiscussionTopic(editingDiscussion.value.id, payload) : await createDiscussionTopic(payload)
    ElMessage.success(editingDiscussion.value ? '讨论已更新' : '讨论已发布'); discussionFormVisible.value = false; await loadDiscussions()
    if (selectedDiscussion.value?.id === saved.id) selectedDiscussion.value = saved
  } catch {} finally { saving.value = false }
}
async function openDiscussion(topic: DiscussionTopic): Promise<void> { try { selectedDiscussion.value = await getDiscussionTopic(topic.id); discussionReplies.value = await getDiscussionReplies(topic.id); discussionReplyDraft.value = ''; discussionDetailVisible.value = true; await loadDiscussions() } catch {} }
function editSelectedDiscussion(): void { if (!selectedDiscussion.value) return; openDiscussionForm(selectedDiscussion.value) }
async function sendDiscussionReply(): Promise<void> { if (!selectedDiscussion.value || !discussionReplyDraft.value.trim()) return; saving.value = true; try { await replyDiscussionTopic(selectedDiscussion.value.id, { content: discussionReplyDraft.value.trim() }); discussionReplyDraft.value = ''; discussionReplies.value = await getDiscussionReplies(selectedDiscussion.value.id); await loadDiscussions(); ElMessage.success('回复已发布') } catch {} finally { saving.value = false } }
async function handleToggleDiscussionPin(): Promise<void> { if (!selectedDiscussion.value) return; try { selectedDiscussion.value = await toggleDiscussionPin(selectedDiscussion.value.id); await loadDiscussions() } catch {} }
async function handleToggleDiscussionClose(): Promise<void> { if (!selectedDiscussion.value) return; try { selectedDiscussion.value = await toggleDiscussionClose(selectedDiscussion.value.id); await loadDiscussions() } catch {} }
async function removeDiscussion(item: DiscussionTopic): Promise<void> { try { await ElMessageBox.confirm(`确定删除讨论“${item.title}”及其全部回复吗？`, '删除讨论', { type: 'warning' }); await deleteDiscussionTopic(item.id); discussionDetailVisible.value = false; ElMessage.success('讨论已删除'); await loadDiscussions() } catch {} }

function canModifyArticle(item: KnowledgeArticle): boolean { return isStaff.value || item.author === userStore.userInfo?.id }
function openArticleForm(item?: KnowledgeArticle): void { editingArticle.value = item || null; Object.assign(articleForm, { title: item?.title || '', content: item?.content || '', category: item?.category || 'other', tags: item?.tags || '', is_published: item?.is_published ?? true }); articleFormVisible.value = true }
async function saveArticle(): Promise<void> {
  if (!articleForm.title.trim() || !articleForm.content.trim()) { ElMessage.warning('请填写文章标题和正文'); return }
  saving.value = true
  try {
    const payload = { project: projectId, title: articleForm.title.trim(), content: articleForm.content.trim(), category: articleForm.category, tags: articleForm.tags.trim(), is_published: articleForm.is_published }
    const saved = editingArticle.value ? await updateKnowledgeArticle(editingArticle.value.id, payload) : await createKnowledgeArticle(payload)
    ElMessage.success(editingArticle.value ? '文章已更新' : '文章已发布'); articleFormVisible.value = false; await loadArticles(); if (selectedArticle.value?.id === saved.id) selectedArticle.value = saved
  } catch {} finally { saving.value = false }
}
async function openArticle(item: KnowledgeArticle): Promise<void> { try { selectedArticle.value = await getKnowledgeArticle(item.id); articleDetailVisible.value = true; await loadArticles() } catch {} }
function editSelectedArticle(): void { if (selectedArticle.value) openArticleForm(selectedArticle.value) }
async function removeArticle(item: KnowledgeArticle): Promise<void> { try { await ElMessageBox.confirm(`确定删除文章“${item.title}”吗？`, '删除文章', { type: 'warning' }); await deleteKnowledgeArticle(item.id); articleDetailVisible.value = false; ElMessage.success('文章已删除'); await loadArticles() } catch {} }

function resetReviewForm(source?: ProjectReview): void {
  Object.assign(reviewForm, { summary: source?.summary || '', achievements: source?.achievements || '', problems: source?.problems || '', lessons: source?.lessons || '', improvements: source?.improvements || '', team_feedback: source?.team_feedback || '', overall_score: source?.overall_score || 0, schedule_score: source?.schedule_score || 0, budget_score: source?.budget_score || 0, team_score: source?.team_score || 0, quality_score: source?.quality_score || 0 })
}
function openReviewForm(): void { resetReviewForm(review.value || undefined); reviewDialogVisible.value = true }
function useSmartReview(): void {
  if (!smartReview.value) return
  resetReviewForm(review.value || undefined)
  reviewForm.summary = smartReview.value.summary
  reviewForm.achievements = smartReview.value.achievements.map((item) => String(item.competition_name || item.award_level || '')).filter(Boolean).join('\n')
  reviewForm.problems = smartReview.value.problem_areas.map((item) => `${item.label}：${item.detail}`).join('\n')
  reviewForm.lessons = smartReview.value.lessons.join('\n')
  reviewForm.improvements = smartReview.value.improvements.join('\n')
  reviewDialogVisible.value = true
}
async function saveReview(): Promise<void> {
  saving.value = true
  try {
    const scores = Object.fromEntries(reviewScoreFields.map(({ key }) => [key, reviewForm[key] || null])) as Record<ReviewScoreKey, number | null>
    const payload = { project: projectId, summary: reviewForm.summary.trim(), achievements: reviewForm.achievements.trim(), problems: reviewForm.problems.trim(), lessons: reviewForm.lessons.trim(), improvements: reviewForm.improvements.trim(), team_feedback: reviewForm.team_feedback.trim(), ...scores }
    if (review.value) await updateProjectReview(review.value.id, payload); else await createProjectReview(payload)
    ElMessage.success('复盘草稿已保存'); reviewDialogVisible.value = false; await loadReview()
  } catch {} finally { saving.value = false }
}
async function handleSubmitReview(): Promise<void> { if (!review.value) return; try { await ElMessageBox.confirm('提交后复盘将进入待审阅状态，确定继续吗？', '提交复盘', { type: 'warning' }); review.value = await submitProjectReview(review.value.id); ElMessage.success('复盘已提交') } catch {} }
async function handleApproveReview(): Promise<void> { if (!review.value) return; try { await ElMessageBox.confirm('确认复盘内容已完成审阅吗？', '完成审阅', { type: 'warning' }); review.value = await approveProjectReview(review.value.id); ElMessage.success('复盘已审阅') } catch {} }
async function removeReview(): Promise<void> { if (!review.value) return; try { await ElMessageBox.confirm('确定删除当前项目复盘吗？', '删除复盘', { type: 'warning' }); await deleteProjectReview(review.value.id); review.value = null; ElMessage.success('复盘已删除') } catch {} }

function addTemplateMilestone(): void { templateMilestones.value.push({ title: '', description: '', due_date: '', sort_order: templateMilestones.value.length }) }
function addTemplateTask(): void { templateTasks.value.push({ title: '', description: '', priority: 'medium' }) }
function openTemplateForm(item?: ProjectTemplate): void {
  editingTemplate.value = item || null
  Object.assign(templateForm, { name: item?.name || '', description: item?.description || '', category: item?.category || '', is_active: item?.is_active ?? true })
  templateMilestones.value = (item?.config.milestones || []).map((milestone, index) => ({ title: milestone.title || '', description: milestone.description || '', due_date: milestone.due_date || '', sort_order: milestone.sort_order ?? index }))
  templateTasks.value = (item?.config.tasks || []).map((task) => ({ title: task.title || '', description: task.description || '', priority: task.priority || 'medium' }))
  templateDialogVisible.value = true
}
async function saveTemplate(): Promise<void> {
  if (!templateForm.name.trim()) { ElMessage.warning('请输入模板名称'); return }
  if (templateMilestones.value.some((item) => !item.title.trim()) || templateTasks.value.some((item) => !item.title.trim())) { ElMessage.warning('请补全模板中的里程碑和任务标题'); return }
  const config: ProjectTemplateConfig = {
    ...(editingTemplate.value?.config || {}),
    milestones: templateMilestones.value.map((item, index) => ({ ...item, title: item.title.trim(), due_date: item.due_date || undefined, sort_order: index })),
    tasks: templateTasks.value.map((item) => ({ ...item, title: item.title.trim() })),
  }
  saving.value = true
  try { const payload = { name: templateForm.name.trim(), description: templateForm.description.trim(), category: templateForm.category.trim(), config, is_active: templateForm.is_active }; if (editingTemplate.value) await updateProjectTemplate(editingTemplate.value.id, payload); else await createProjectTemplate(payload); ElMessage.success(editingTemplate.value ? '模板已更新' : '模板已创建'); templateDialogVisible.value = false; await loadTemplates() } catch {} finally { saving.value = false }
}
async function removeTemplate(item: ProjectTemplate): Promise<void> { try { await ElMessageBox.confirm(`确定删除模板“${item.name}”吗？`, '删除模板', { type: 'warning' }); await deleteProjectTemplate(item.id); ElMessage.success('模板已删除'); await loadTemplates() } catch {} }
function openInstantiate(item: ProjectTemplate): void { instantiatingTemplate.value = item; Object.assign(instantiateForm, { name: `${project.value?.name || ''}副本`, code: '', leader: project.value?.leader, intro: item.description || '', start_date: '', planned_end_date: '' }); instantiateDialogVisible.value = true }
async function instantiateTemplate(): Promise<void> {
  if (!instantiatingTemplate.value || !instantiateForm.name.trim() || !instantiateForm.code.trim() || !instantiateForm.leader) { ElMessage.warning('请填写项目名称、编号并选择负责人'); return }
  saving.value = true
  try { const created = await instantiateProjectTemplate(instantiatingTemplate.value.id, { name: instantiateForm.name.trim(), code: instantiateForm.code.trim(), leader: instantiateForm.leader, intro: instantiateForm.intro.trim(), start_date: instantiateForm.start_date || null, planned_end_date: instantiateForm.planned_end_date || null }); instantiateDialogVisible.value = false; ElMessage.success(`项目已创建，包含 ${created._instantiated?.milestones || 0} 个里程碑和 ${created._instantiated?.tasks || 0} 个任务`); await router.push({ name: 'ProjectDetail', params: { id: created.id } }) } catch {} finally { saving.value = false }
}

onMounted(loadWorkspace)
</script>

<style lang="scss" scoped>
.operations-page { padding-bottom: 32px; }
.load-alert { margin-bottom: 16px; }
.operations-shell { min-height: 560px; }
.operations-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 16px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.operations-summary > div { display: flex; min-width: 0; min-height: 78px; padding: 14px 18px; flex-direction: column; justify-content: center; gap: 7px; border-right: 1px solid var(--color-border-light); }
.operations-summary > div:last-child { border-right: 0; }
.operations-summary span { color: var(--color-text-muted); font-size: 11px; }
.operations-summary strong { overflow: hidden; color: var(--color-text); font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
.operations-summary strong.danger { color: var(--color-danger); }
.operations-tabs { padding: 0 18px 18px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.tab-label { display: inline-flex; align-items: center; gap: 7px; }
.tab-label svg { width: 15px; }
.tab-label small { min-width: 20px; padding: 1px 6px; color: var(--color-text-muted); text-align: center; background: var(--color-surface-subtle); border-radius: 8px; }
.workspace-section { min-height: 430px; padding-top: 8px; }
.section-heading { display: flex; margin-bottom: 18px; padding-bottom: 14px; align-items: flex-start; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--color-border-light); }
.section-heading h2 { color: var(--color-text); font-size: 17px; font-weight: 600; }
.section-heading p { margin-top: 4px; color: var(--color-text-muted); font-size: 12px; }
.insight-overview { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 16px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.score-panel { display: grid; min-height: 126px; padding: 18px; grid-template-columns: 1fr auto; align-content: center; align-items: center; gap: 4px 12px; border-right: 1px solid var(--color-border-light); }
.score-panel:last-child { border-right: 0; }
.score-panel > span { color: var(--color-text-muted); font-size: 12px; }
.score-panel > strong { grid-row: span 2; color: var(--color-text); font-size: 36px; line-height: 1; }
.score-panel > strong small { font-size: 14px; }
.score-panel .el-tag { width: fit-content; }
.insight-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin-bottom: 18px; }
.metric-row { padding: 12px; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.metric-row header { display: flex; margin-bottom: 8px; justify-content: space-between; gap: 8px; font-size: 12px; }
.metric-row header span { color: var(--color-text-muted); }
.metric-row p { margin-top: 8px; color: var(--color-text-muted); font-size: 11px; line-height: 1.55; }
.analysis-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.analysis-columns > section { min-width: 0; }
.analysis-columns h3, .smart-review-panel h3 { margin-bottom: 10px; color: var(--color-text); font-size: 14px; font-weight: 600; }
.factor-list, .material-list { display: flex; flex-direction: column; gap: 7px; }
.factor-list article, .material-list article { padding: 10px 12px; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.factor-list article > div { display: flex; align-items: center; justify-content: space-between; }
.factor-list p, .material-list p { margin-top: 5px; color: var(--color-text-muted); font-size: 11px; line-height: 1.5; }
.recommendation-list { margin: 10px 0 0; padding-left: 18px; color: var(--color-text-regular); font-size: 12px; line-height: 1.65; }
.material-list article { display: flex; gap: 10px; }
.material-list .el-icon { flex: 0 0 auto; margin-top: 2px; }
.status-complete { color: var(--color-success); } .status-incomplete { color: var(--color-warning); } .status-missing { color: var(--color-danger); }
.smart-review-panel { margin-top: 18px; padding: 16px; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.smart-review-panel > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.smart-review-panel header p { color: var(--color-text-regular); font-size: 12px; line-height: 1.65; }
.smart-review-grid { display: grid; grid-template-columns: repeat(4, 1fr); margin-top: 14px; border-top: 1px solid var(--color-border-light); }
.smart-review-grid > div { display: flex; padding: 12px 10px 0; flex-direction: column; gap: 5px; }
.smart-review-grid span { color: var(--color-text-muted); font-size: 11px; } .smart-review-grid strong { color: var(--color-text); font-size: 18px; }
.milestone-list, .discussion-list, .template-list { display: flex; flex-direction: column; gap: 8px; }
.milestone-item, .discussion-item, .template-item { display: flex; min-height: 68px; padding: 12px 14px; align-items: center; gap: 12px; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.milestone-toggle { display: grid; width: 34px; height: 34px; padding: 0; flex: 0 0 auto; place-items: center; color: var(--color-text-muted); background: transparent; border: 0; cursor: pointer; }
.milestone-toggle svg { width: 21px; }
.milestone-item.is-complete .milestone-toggle { color: var(--color-success); }
.milestone-item.is-complete .item-main strong { color: var(--color-text-muted); text-decoration: line-through; }
.item-main { min-width: 0; flex: 1; }
.item-main header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.item-main header strong { overflow-wrap: anywhere; color: var(--color-text); font-size: 13px; }
.item-main header > span, .item-main > span { color: var(--color-text-muted); font-size: 11px; }
.item-main > p { margin-top: 4px; overflow: hidden; color: var(--color-text-muted); font-size: 12px; line-height: 1.5; text-overflow: ellipsis; white-space: nowrap; }
.row-actions, .template-actions { display: flex; flex: 0 0 auto; gap: 6px; }
.risk-list, .article-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.risk-item, .article-item { min-width: 0; padding: 14px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.risk-heading, .article-item > header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.risk-heading > div { display: flex; gap: 6px; }
.risk-heading > span, .article-item header > span { display: inline-flex; align-items: center; gap: 4px; color: var(--color-text-muted); font-size: 11px; }
.risk-heading svg, .article-item svg, .discussion-count svg { width: 14px; }
.risk-item h3, .article-item h3 { margin-top: 12px; overflow-wrap: anywhere; color: var(--color-text); font-size: 14px; font-weight: 600; }
.risk-item > p, .article-item > p { margin-top: 6px; overflow-wrap: anywhere; color: var(--color-text-muted); font-size: 12px; line-height: 1.55; }
.mitigation { display: flex; margin-top: 12px; padding-top: 10px; flex-direction: column; gap: 4px; border-top: 1px solid var(--color-border-light); }
.mitigation strong { color: var(--color-text); font-size: 11px; } .mitigation span { color: var(--color-text-regular); font-size: 12px; line-height: 1.55; }
.risk-item footer { display: flex; margin-top: 8px; gap: 2px; }
.discussion-item, .article-item { cursor: pointer; transition: border-color var(--transition-fast), background var(--transition-fast); }
.discussion-item:hover, .article-item:hover { background: var(--color-surface); border-color: var(--color-primary); }
.discussion-item:focus-visible, .article-item:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.discussion-state { display: grid; width: 34px; height: 34px; flex: 0 0 auto; place-items: center; color: var(--color-primary); background: var(--color-primary-soft); border-radius: var(--radius-sm); }
.discussion-state svg { width: 17px; }
.discussion-count { display: inline-flex; align-items: center; gap: 4px; color: var(--color-text-muted); font-size: 12px; }
.article-item footer { margin-top: 14px; color: var(--color-text-muted); font-size: 11px; }
.review-document { border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.review-document > header { display: flex; padding: 14px 16px; align-items: center; justify-content: space-between; gap: 12px; background: var(--color-surface-subtle); border-bottom: 1px solid var(--color-border-light); }
.review-document > header > div { display: flex; align-items: center; gap: 10px; } .review-document > header span { color: var(--color-text-muted); font-size: 12px; }
.review-actions { flex-wrap: wrap; justify-content: flex-end; }
.review-scores { display: grid; grid-template-columns: repeat(5, 1fr); border-bottom: 1px solid var(--color-border-light); }
.review-scores > div { display: flex; padding: 14px; flex-direction: column; align-items: center; gap: 4px; border-right: 1px solid var(--color-border-light); }
.review-scores > div:last-child { border-right: 0; } .review-scores span { color: var(--color-text-muted); font-size: 11px; } .review-scores strong { color: var(--color-text); font-size: 20px; }
.review-sections { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.review-sections article { min-height: 132px; padding: 16px; border-right: 1px solid var(--color-border-light); border-bottom: 1px solid var(--color-border-light); }
.review-sections article:nth-child(2n) { border-right: 0; } .review-sections article:nth-last-child(-n + 2) { border-bottom: 0; }
.review-sections h3 { color: var(--color-text); font-size: 13px; font-weight: 600; } .review-sections p { margin-top: 8px; overflow-wrap: anywhere; color: var(--color-text-regular); font-size: 12px; line-height: 1.7; white-space: pre-wrap; }
.template-item .item-main > span { display: block; margin-top: 6px; }
.drawer-title { display: flex; min-width: 0; align-items: center; gap: 8px; } .drawer-title strong { overflow-wrap: anywhere; color: var(--color-text); font-size: 16px; }
.detail-meta { display: flex; margin-bottom: 14px; justify-content: space-between; gap: 12px; color: var(--color-text-muted); font-size: 11px; }
.detail-content-text { overflow-wrap: anywhere; color: var(--color-text-regular); font-size: 13px; line-height: 1.8; white-space: pre-wrap; }
.detail-actions { display: flex; margin-top: 18px; gap: 8px; flex-wrap: wrap; }
.reply-list { display: flex; flex-direction: column; gap: 12px; }
.reply-list article { display: flex; gap: 10px; }
.reply-list article > div { min-width: 0; flex: 1; }
.reply-list header { display: flex; justify-content: space-between; gap: 10px; } .reply-list header strong { color: var(--color-text); font-size: 12px; } .reply-list header span { color: var(--color-text-muted); font-size: 10px; }
.reply-list p { margin-top: 4px; overflow-wrap: anywhere; color: var(--color-text-regular); font-size: 12px; line-height: 1.6; white-space: pre-wrap; }
.drawer-composer { display: flex; margin-top: 18px; align-items: flex-end; gap: 8px; }
.article-tags { display: flex; margin-bottom: 12px; gap: 6px; flex-wrap: wrap; }
.dialog-grid, .review-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 14px; }
.score-form-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
.score-form-grid :deep(.el-form-item__content) { white-space: nowrap; }
.template-builder-section { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--color-border-light); }
.template-builder-section > header { display: flex; margin-bottom: 10px; align-items: center; justify-content: space-between; gap: 12px; }
.template-builder-section header > div { display: flex; align-items: baseline; gap: 8px; }
.template-builder-section h3 { color: var(--color-text); font-size: 13px; font-weight: 600; }
.template-builder-section header span { color: var(--color-text-muted); font-size: 11px; }
.template-builder-list { display: flex; flex-direction: column; gap: 7px; }
.template-builder-row { display: grid; grid-template-columns: minmax(0, 1fr) 160px 32px; align-items: center; gap: 8px; }

@media screen and (max-width: 1100px) { .insight-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } .score-form-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media screen and (max-width: 768px) {
  .operations-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .operations-summary > div:nth-child(2) { border-right: 0; } .operations-summary > div:nth-child(-n + 2) { border-bottom: 1px solid var(--color-border-light); }
  .operations-tabs { padding: 0 12px 14px; }
  .section-heading, .smart-review-panel > header, .review-document > header { align-items: stretch; flex-direction: column; }
  .insight-overview, .analysis-columns, .risk-list, .article-grid, .review-form-grid, .dialog-grid { grid-template-columns: 1fr; }
  .score-panel { border-right: 0; border-bottom: 1px solid var(--color-border-light); } .score-panel:last-child { border-bottom: 0; }
  .insight-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .smart-review-grid { grid-template-columns: repeat(2, 1fr); }
  .review-scores { grid-template-columns: repeat(3, 1fr); } .review-scores > div { border-bottom: 1px solid var(--color-border-light); }
  .review-sections { grid-template-columns: 1fr; } .review-sections article { border-right: 0; border-bottom: 1px solid var(--color-border-light); } .review-sections article:nth-last-child(-n + 2) { border-bottom: 1px solid var(--color-border-light); } .review-sections article:last-child { border-bottom: 0; }
  .template-item { align-items: stretch; flex-direction: column; } .template-actions { flex-wrap: wrap; }
  .drawer-composer { align-items: stretch; flex-direction: column; }
  .score-form-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .template-builder-row { grid-template-columns: minmax(0, 1fr) 32px; }
  .template-builder-row > :nth-child(2) { grid-column: 1; grid-row: 2; width: 100%; }
  .template-builder-row > :last-child { grid-column: 2; grid-row: 1 / span 2; }
}
@media screen and (max-width: 420px) { .insight-grid { grid-template-columns: 1fr; } .milestone-item { align-items: flex-start; } .row-actions { flex-direction: column; } .review-scores { grid-template-columns: repeat(2, 1fr); } }
</style>
