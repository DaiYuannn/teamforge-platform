<template>
  <div class="page-container ip-detail-page">
    <PageHeader
      :title="application?.title || '知识产权申请详情'"
      :subtitle="application ? '集中查看申请进度、责任分工、材料版本和处理记录' : '正在读取申请信息'"
    >
      <template v-if="application" #meta>
        <div class="application-meta">
          <el-tag :type="getStatusColor(application.status)" size="small">
            {{ IP_STATUS_MAP[application.status]?.label || application.status }}
          </el-tag>
          <el-tag :type="getTypeColor(application.ip_type)" size="small" effect="plain">
            {{ IP_TYPE_MAP[application.ip_type]?.label || application.ip_type }}
          </el-tag>
          <span>{{ application.application_code || '暂无内部编号' }}</span>
        </div>
      </template>
      <template #actions>
        <el-button :icon="ArrowLeft" @click="router.back()">返回</el-button>
        <el-button
          v-if="application && canEditApplication"
          :icon="Edit"
          @click="handleEdit"
        >
          编辑申请
        </el-button>
        <el-button
          v-if="application && hasPrivilegedRole"
          type="danger"
          plain
          :icon="Delete"
          :loading="deleting"
          @click="handleDelete"
        >
          删除申请
        </el-button>
        <el-button
          v-if="primaryWorkflowAction"
          type="primary"
          :loading="statusTransitioning"
          @click="handleWorkflowAction(primaryWorkflowAction)"
        >
          {{ primaryWorkflowAction.label }}
        </el-button>
        <el-dropdown
          v-if="secondaryWorkflowActions.length"
          :disabled="statusTransitioning"
          trigger="click"
          @command="handleWorkflowCommand"
        >
          <el-tooltip content="更多流程操作" placement="bottom">
            <el-button :icon="MoreFilled" circle aria-label="更多流程操作" />
          </el-tooltip>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="item in secondaryWorkflowActions"
                :key="item.targetStatus"
                :command="item.targetStatus"
                :class="{ 'danger-action': item.tone === 'danger' }"
              >
                {{ item.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </PageHeader>

    <div v-if="loadError" class="status-banner" role="alert">
      <el-icon><WarningFilled /></el-icon>
      <span>申请详情加载失败。</span>
      <el-button link type="primary" @click="loadDetail">重新加载</el-button>
    </div>

    <section v-if="application" class="application-summary">
      <div class="summary-facts">
        <div class="summary-fact summary-fact--owner">
          <span>当前责任人</span>
          <strong>{{ primaryOwner }}</strong>
          <small>{{ currentResponsibility }}</small>
        </div>
        <div class="summary-fact">
          <span>关联项目</span>
          <strong>{{ application.related_project_names?.join('、') || application.related_project_name || '未关联' }}</strong>
          <small>主项目及成果复用项目</small>
        </div>
        <div class="summary-fact">
          <span>材料版本</span>
          <strong class="tabular-nums">{{ materials.length }}</strong>
          <small>{{ finalMaterialCount ? `${finalMaterialCount} 份最终版` : '暂无最终版' }}</small>
        </div>
        <div class="summary-fact" :class="{ 'summary-fact--danger': application.return_count > 0 }">
          <span>退回次数</span>
          <strong class="tabular-nums">{{ application.return_count || 0 }}</strong>
          <small>{{ pendingReturnCount ? `${pendingReturnCount} 项待修改` : '当前无待修改项' }}</small>
        </div>
        <div class="summary-fact" :class="{ 'summary-fact--warning': pendingObjectionCount > 0 }">
          <span>待处理异议</span>
          <strong class="tabular-nums">{{ pendingObjectionCount }}</strong>
          <small>共 {{ objections.length }} 条异议</small>
        </div>
      </div>
      <div class="summary-progress">
        <IPStatusStepper :current-status="application.status" />
      </div>
    </section>

    <section v-if="application?.current_problem" class="attention-banner">
      <div class="attention-icon"><el-icon><WarningFilled /></el-icon></div>
      <div>
        <span>当前问题</span>
        <p>{{ application.current_problem }}</p>
      </div>
    </section>

    <section v-if="application" class="detail-workspace">
      <el-tabs v-model="activeTab" class="business-tabs">
        <el-tab-pane name="overview">
          <template #label>
            <span class="tab-label"><el-icon><DataBoard /></el-icon>概览</span>
          </template>

          <div class="overview-grid">
            <section class="workspace-panel information-panel">
              <header class="panel-header">
                <div>
                  <h2>申请信息</h2>
                  <p>成果基础信息和关键时间</p>
                </div>
              </header>

              <dl class="detail-grid">
                <div>
                  <dt>成果类型</dt>
                  <dd>{{ IP_TYPE_MAP[application.ip_type]?.label || application.ip_type }}</dd>
                </div>
                <div>
                  <dt>内部编号</dt>
                  <dd>{{ application.application_code || '-' }}</dd>
                </div>
                <div>
                  <dt>关联项目</dt>
                  <dd>{{ application.related_project_names?.join('、') || application.related_project_name || '-' }}</dd>
                </div>
                <div>
                  <dt>创建人</dt>
                  <dd>{{ application.created_by_name || '-' }}</dd>
                </div>
                <div>
                  <dt>开始日期</dt>
                  <dd>{{ formatDate(application.start_date) }}</dd>
                </div>
                <div>
                  <dt>提交日期</dt>
                  <dd>{{ formatDate(application.submit_date) }}</dd>
                </div>
                <div>
                  <dt>受理日期</dt>
                  <dd>{{ formatDate(application.accepted_date) }}</dd>
                </div>
                <div>
                  <dt>授权日期</dt>
                  <dd>{{ formatDate(application.authorized_date) }}</dd>
                </div>
                <div>
                  <dt>创建时间</dt>
                  <dd>{{ formatDateTime(application.created_at) }}</dd>
                </div>
                <div>
                  <dt>最近更新</dt>
                  <dd>{{ formatDateTime(application.updated_at) }}</dd>
                </div>
                <div class="detail-grid__wide">
                  <dt>成果简介</dt>
                  <dd class="long-copy">{{ application.intro || '暂无简介' }}</dd>
                </div>
                <div v-if="application.status_note" class="detail-grid__wide">
                  <dt>状态说明</dt>
                  <dd class="long-copy">{{ application.status_note }}</dd>
                </div>
              </dl>
            </section>

            <section class="workspace-panel timeline-panel">
              <header class="panel-header">
                <div>
                  <h2>流程时间线</h2>
                  <p>{{ processTimeline.length }} 个关键节点</p>
                </div>
              </header>

              <el-timeline v-if="processTimeline.length" class="process-timeline">
                <el-timeline-item
                  v-for="item in processTimeline"
                  :key="`${item.time}-${item.title}`"
                  :timestamp="formatDateTime(item.time)"
                  :type="item.type"
                >
                  <strong>{{ item.title }}</strong>
                  <p v-if="item.description">{{ item.description }}</p>
                </el-timeline-item>
              </el-timeline>
              <EmptyState v-else text="暂无流程记录" icon="Clock" compact />
            </section>
          </div>
        </el-tab-pane>

        <el-tab-pane name="people">
          <template #label>
            <span class="tab-label"><el-icon><UserFilled /></el-icon>协作成员</span>
          </template>

          <section class="workspace-panel candidate-panel">
            <header class="panel-header panel-header--actions">
              <div>
                <h2>拟申报与正式提交名单</h2>
                <p>记录申报身份、署名顺序与实名核验结果；此处不展示身份证等敏感明文</p>
              </div>
              <el-button
                v-if="canManageCandidateList"
                type="primary"
                :icon="Plus"
                @click="handleAddCandidate"
              >
                添加申报成员
              </el-button>
            </header>

            <div v-if="!isMobile" class="table-wrap">
              <el-table v-loading="loading" :data="candidates">
                <template #empty>
                  <EmptyState text="暂无拟申报名单" description="创建申请后，由项目负责人在这里确认最终申报人员。" icon="UserFilled" compact />
                </template>
                <el-table-column label="姓名" min-width="120">
                  <template #default="{ row }">
                    <strong class="table-primary">{{ candidateUserName(row as IPApplicationCandidate) }}</strong>
                  </template>
                </el-table-column>
                <el-table-column label="申报身份" width="116">
                  <template #default="{ row }">{{ row.legal_role_display || candidateLegalRoleLabel(row.legal_role) }}</template>
                </el-table-column>
                <el-table-column label="署名顺序" width="92" align="center">
                  <template #default="{ row }">
                    <span class="tabular-nums">第 {{ row.planned_order }} 位</span>
                  </template>
                </el-table-column>
                <el-table-column label="实名核验" width="128">
                  <template #default="{ row }">
                    <el-tag :type="candidateIdentityTone(row.identity_check_status)" size="small" effect="plain">
                      {{ row.identity_check_status_display || candidateIdentityLabel(row.identity_check_status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="最终提交状态" width="128">
                  <template #default="{ row }">
                    <el-tag :type="candidateStatusTone(row.status)" size="small">
                      {{ row.status_display || candidateStatusLabel(row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="核验记录" min-width="140">
                  <template #default="{ row }">
                    <span v-if="row.checked_by_name">
                      {{ row.checked_by_name }} · {{ formatDate(row.checked_at) }}
                    </span>
                    <span v-else class="muted-text">尚未核验</span>
                  </template>
                </el-table-column>
                <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.note || '-' }}</template>
                </el-table-column>
                <el-table-column v-if="canManageCandidateList" label="操作" width="112" fixed="right" align="right">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="handleEditCandidate(row as IPApplicationCandidate)">编辑</el-button>
                    <el-button link type="danger" @click="handleDeleteCandidate(row as IPApplicationCandidate)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div v-else-if="candidates.length" class="mobile-record-list">
              <article v-for="row in candidates" :key="row.id" class="mobile-record">
                <div class="mobile-record__header">
                  <div>
                    <strong>{{ candidateUserName(row) }}</strong>
                    <span>{{ row.legal_role_display || candidateLegalRoleLabel(row.legal_role) }} · 第 {{ row.planned_order }} 位</span>
                  </div>
                  <el-tag :type="candidateStatusTone(row.status)" size="small">
                    {{ row.status_display || candidateStatusLabel(row.status) }}
                  </el-tag>
                </div>
                <dl class="candidate-mobile-meta">
                  <div>
                    <dt>实名核验</dt>
                    <dd>{{ row.identity_check_status_display || candidateIdentityLabel(row.identity_check_status) }}</dd>
                  </div>
                  <div>
                    <dt>核验人</dt>
                    <dd>{{ row.checked_by_name || '-' }}</dd>
                  </div>
                </dl>
                <p>{{ row.note || '暂无备注' }}</p>
                <div v-if="canManageCandidateList" class="row-actions">
                  <el-button link type="primary" @click="handleEditCandidate(row)">编辑</el-button>
                  <el-button link type="danger" @click="handleDeleteCandidate(row)">删除</el-button>
                </div>
              </article>
            </div>
            <EmptyState v-else text="暂无拟申报名单" description="创建申请后，由项目负责人在这里确认最终申报人员。" icon="UserFilled" compact />
          </section>

          <section class="workspace-panel">
            <header class="panel-header panel-header--actions">
              <div>
                <h2>责任分工</h2>
                <p>明确各环节负责人并确认实际贡献</p>
              </div>
              <div class="panel-actions">
                <el-button
                  v-if="canManageCollaboration"
                  :icon="Refresh"
                  :loading="syncing"
                  @click="handleSyncContribution"
                >
                  同步贡献
                </el-button>
                <el-button
                  v-if="canManageCollaboration"
                  type="primary"
                  :icon="Plus"
                  @click="contributorDialogVisible = true"
                >
                  添加成员
                </el-button>
              </div>
            </header>

            <div class="role-grid">
              <article v-for="role in responsibilityRoles" :key="role.key" class="role-item">
                <div class="role-icon"><el-icon><component :is="role.icon" /></el-icon></div>
                <div class="role-copy">
                  <span>{{ role.label }}</span>
                  <strong>{{ role.name || '未分配' }}</strong>
                  <small>{{ role.desc }}</small>
                </div>
              </article>
            </div>

            <div class="section-divider" />

            <div v-if="!isMobile" class="table-wrap">
              <el-table v-loading="loading" :data="contributors">
                <template #empty>
                  <EmptyState text="暂无协作成员" description="添加成员后可记录分工和确认状态。" icon="User" compact />
                </template>
                <el-table-column label="成员" min-width="120">
                  <template #default="{ row }">
                    <strong class="table-primary">{{ row.user_detail?.name || row.user_name || '-' }}</strong>
                  </template>
                </el-table-column>
                <el-table-column label="职责" width="140">
                  <template #default="{ row }">{{ IP_CONTRIBUTOR_ROLE_MAP[row.role] || row.role }}</template>
                </el-table-column>
                <el-table-column prop="contribution_description" label="贡献内容" min-width="190" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.contribution_description || '-' }}</template>
                </el-table-column>
                <el-table-column prop="responsibility_description" label="责任说明" min-width="190" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.responsibility_description || '-' }}</template>
                </el-table-column>
                <el-table-column label="确认状态" width="108">
                  <template #default="{ row }">
                    <el-tag :type="row.is_confirmed ? 'success' : 'warning'" size="small">
                      {{ row.is_confirmed ? '已确认' : '待确认' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="确认人" width="110">
                  <template #default="{ row }">{{ row.confirmed_by_name || '-' }}</template>
                </el-table-column>
                <el-table-column v-if="hasConfirmableContribution" label="操作" width="80" fixed="right">
                  <template #default="{ row }">
                    <el-button
                      v-if="canConfirmContributor(row as IPContributor)"
                      link
                      type="primary"
                      @click="handleConfirmContributor(row as IPContributor)"
                    >
                      确认
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div v-else-if="contributors.length" class="mobile-record-list">
              <article v-for="row in contributors" :key="row.id" class="mobile-record">
                <div class="mobile-record__header">
                  <div>
                    <strong>{{ row.user_detail?.name || row.user_name || '-' }}</strong>
                    <span>{{ IP_CONTRIBUTOR_ROLE_MAP[row.role] || row.role }}</span>
                  </div>
                  <el-tag :type="row.is_confirmed ? 'success' : 'warning'" size="small">
                    {{ row.is_confirmed ? '已确认' : '待确认' }}
                  </el-tag>
                </div>
                <p>{{ row.contribution_description || '暂无贡献描述' }}</p>
                <small>{{ row.responsibility_description || '暂无责任说明' }}</small>
                <el-button
                  v-if="canConfirmContributor(row)"
                  link
                  type="primary"
                  @click="handleConfirmContributor(row)"
                >
                  确认贡献
                </el-button>
              </article>
            </div>
            <EmptyState v-else text="暂无协作成员" description="添加成员后可记录分工和确认状态。" icon="User" compact />
          </section>
        </el-tab-pane>

        <el-tab-pane name="materials">
          <template #label>
            <span class="tab-label"><el-icon><FolderOpened /></el-icon>材料与退回</span>
          </template>

          <div class="materials-grid">
            <section class="workspace-panel materials-panel">
              <header class="panel-header panel-header--actions">
                <div>
                  <h2>材料版本</h2>
                  <p>共 {{ materials.length }} 个版本</p>
                </div>
                <el-upload
                  v-if="canMaintainMaterials"
                  :show-file-list="false"
                  :auto-upload="false"
                  :on-change="handleMaterialUpload"
                >
                  <el-button type="primary" :icon="Upload">上传材料</el-button>
                </el-upload>
              </header>

              <div class="archive-readiness">
                <div class="archive-readiness__item">
                  <span>最终证书</span>
                  <strong>{{ application?.final_certificate_file_name || '尚未上传' }}</strong>
                  <el-tag :type="application?.final_certificate_file ? 'success' : 'warning'" size="small">
                    {{ application?.final_certificate_file ? '已留存' : '待补充' }}
                  </el-tag>
                </div>
                <div class="archive-readiness__item">
                  <span>最终材料</span>
                  <strong>{{ finalMaterialCount ? `${finalMaterialCount} 个最终版` : '尚未标记' }}</strong>
                  <el-tag :type="finalMaterialCount ? 'success' : 'warning'" size="small">
                    {{ finalMaterialCount ? '已就绪' : '待补充' }}
                  </el-tag>
                </div>
                <el-upload
                  v-if="canEditApplication"
                  accept=".pdf,.png,.jpg,.jpeg"
                  :show-file-list="false"
                  :auto-upload="false"
                  :on-change="handleFinalCertificateUpload"
                >
                  <el-button :loading="certificateUploading" :icon="Upload">
                    {{ application?.final_certificate_file ? '替换最终证书' : '上传最终证书' }}
                  </el-button>
                </el-upload>
              </div>

              <div v-if="!isMobile" class="table-wrap">
                <el-table v-loading="loading" :data="materials">
                  <template #empty>
                    <EmptyState text="暂无材料" description="上传申请材料后会保留版本记录。" icon="FolderOpened" compact />
                  </template>
                  <el-table-column label="文件" min-width="190">
                    <template #default="{ row }"><strong class="table-primary">{{ row.file_asset_name || '-' }}</strong></template>
                  </el-table-column>
                  <el-table-column label="材料类型" width="132">
                    <template #default="{ row }">{{ IP_MATERIAL_TYPE_MAP[row.material_type] || row.material_type }}</template>
                  </el-table-column>
                  <el-table-column prop="version" label="版本" width="76" />
                  <el-table-column label="上传人" width="100">
                    <template #default="{ row }">{{ row.uploaded_by_name || '-' }}</template>
                  </el-table-column>
                  <el-table-column label="变更说明" min-width="170" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.change_note || '-' }}</template>
                  </el-table-column>
                  <el-table-column label="上传日期" width="110">
                    <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column label="状态" width="80">
                    <template #default="{ row }">
                      <el-tag v-if="row.is_final" type="success" size="small">最终版</el-tag>
                      <span v-else class="muted-text">过程版</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="116" fixed="right">
                    <template #default="{ row }">
                      <el-button
                        v-if="canEditMaterial(row)"
                        link
                        type="primary"
                        :loading="materialUpdatingId === row.id"
                        @click="handleToggleFinalMaterial(row)"
                      >
                        {{ row.is_final ? '取消最终版' : '标记最终版' }}
                      </el-button>
                      <span v-else class="muted-text">—</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>

              <div v-else-if="materials.length" class="mobile-record-list">
                <article v-for="row in materials" :key="row.id" class="mobile-record">
                  <div class="mobile-record__header">
                    <div>
                      <strong>{{ row.file_asset_name || '-' }}</strong>
                      <span>{{ IP_MATERIAL_TYPE_MAP[row.material_type] || row.material_type }} · v{{ row.version }}</span>
                    </div>
                    <el-tag v-if="row.is_final" type="success" size="small">最终版</el-tag>
                  </div>
                  <p>{{ row.change_note || '暂无变更说明' }}</p>
                  <small>{{ row.uploaded_by_name || '-' }} · {{ formatDate(row.created_at) }}</small>
                  <el-button
                    v-if="canEditMaterial(row)"
                    link
                    type="primary"
                    :loading="materialUpdatingId === row.id"
                    @click="handleToggleFinalMaterial(row)"
                  >
                    {{ row.is_final ? '取消最终版' : '标记为最终版' }}
                  </el-button>
                </article>
              </div>
              <EmptyState v-else text="暂无材料" description="上传申请材料后会保留版本记录。" icon="FolderOpened" compact />
            </section>

            <section class="workspace-panel returns-panel">
              <header class="panel-header panel-header--actions">
                <div>
                  <h2>退回与修改</h2>
                  <p>{{ pendingReturnCount ? `${pendingReturnCount} 项等待修改` : '当前无待修改项' }}</p>
                </div>
                <el-button
                  v-if="canCreateReturn"
                  :icon="Plus"
                  @click="returnDialogVisible = true"
                >
                  新建退回
                </el-button>
              </header>

              <div v-if="returnRecords.length" class="return-list">
                <article v-for="record in sortedReturnRecords" :key="record.id" class="return-row">
                  <div class="return-row__header">
                    <div class="return-tags">
                      <el-tag :type="getReturnColor(record.result)" size="small">
                        {{ IP_RETURN_RESULT_MAP[record.result]?.label || record.result }}
                      </el-tag>
                      <span>{{ IP_RETURN_SOURCE_MAP[record.return_source] || record.return_source }}</span>
                    </div>
                    <time>{{ formatDateTime(record.return_time) }}</time>
                  </div>
                  <h3>{{ record.return_reason }}</h3>
                  <dl class="return-meta">
                    <div><dt>责任类型</dt><dd>{{ IP_RESPONSIBILITY_TYPE_MAP[record.responsibility_type] || record.responsibility_type }}</dd></div>
                    <div><dt>责任人</dt><dd>{{ record.responsible_user_name || '-' }}</dd></div>
                    <div><dt>修改截止</dt><dd>{{ formatDate(record.modify_deadline) }}</dd></div>
                    <div v-if="record.actual_modifier_name"><dt>实际修改人</dt><dd>{{ record.actual_modifier_name }}</dd></div>
                  </dl>
                  <p v-if="record.modify_description" class="resolution-copy">{{ record.modify_description }}</p>
                  <el-button
                    v-if="record.result === 'pending' && canResolveReturnRecord(record)"
                    type="primary"
                    size="small"
                    @click="handleResolveReturn(record)"
                  >
                    完成修改
                  </el-button>
                </article>
              </div>
              <EmptyState v-else text="暂无退回记录" description="发生材料退回后会在这里保留责任和处理过程。" icon="RefreshLeft" compact />
            </section>
          </div>
        </el-tab-pane>

        <el-tab-pane name="records">
          <template #label>
            <span class="tab-label"><el-icon><ChatDotRound /></el-icon>异议与记录</span>
          </template>

          <div class="records-grid">
            <section class="workspace-panel objection-panel">
              <header class="panel-header panel-header--actions">
                <div>
                  <h2>异议反馈</h2>
                  <p>{{ pendingObjectionCount ? `${pendingObjectionCount} 条待处理` : '当前无待处理异议' }}</p>
                </div>
                <el-button
                  v-if="canSubmitObjection"
                  type="primary"
                  :icon="ChatDotRound"
                  @click="objectionDialogVisible = true"
                >
                  提交异议
                </el-button>
              </header>

              <div v-if="objections.length" class="objection-list">
                <article v-for="obj in sortedObjections" :key="obj.id" class="objection-row">
                  <div class="objection-row__header">
                    <div>
                      <el-tag :type="objectionStatusColor(obj.status)" size="small">
                        {{ IP_OBJECTION_STATUS_MAP[obj.status]?.label || obj.status }}
                      </el-tag>
                      <span>{{ IP_OBJECTION_TYPE_MAP[obj.objection_type] || obj.objection_type }}</span>
                    </div>
                    <time>{{ formatDate(obj.created_at) }}</time>
                  </div>
                  <div class="objection-author">{{ obj.objector_detail?.name || obj.objector_name || '未知成员' }}</div>
                  <p class="objection-content">{{ obj.content }}</p>
                  <dl v-if="obj.leader_opinion || obj.teacher_opinion || obj.final_result" class="review-notes">
                    <div v-if="obj.leader_opinion"><dt>负责人意见</dt><dd>{{ obj.leader_opinion }}</dd></div>
                    <div v-if="obj.teacher_opinion"><dt>老师意见</dt><dd>{{ obj.teacher_opinion }}</dd></div>
                    <div v-if="obj.final_result"><dt>处理结果</dt><dd>{{ obj.final_result }}</dd></div>
                  </dl>
                  <div v-if="(canLeaderReview && obj.status === 'pending') || (canTeacherConfirm && obj.status === 'leader_reviewed')" class="row-actions">
                    <el-button
                      v-if="canLeaderReview && obj.status === 'pending'"
                      type="primary"
                      size="small"
                      @click="handleReviewObjection(obj, 'leader')"
                    >
                      负责人初审
                    </el-button>
                    <el-button
                      v-if="canTeacherConfirm && obj.status === 'leader_reviewed'"
                      type="primary"
                      size="small"
                      @click="handleReviewObjection(obj, 'teacher')"
                    >
                      老师确认
                    </el-button>
                  </div>
                </article>
              </div>
              <EmptyState v-else text="暂无异议" description="对贡献、责任或排序有异议时可在这里提交。" icon="ChatDotRound" compact />
            </section>

            <section class="workspace-panel activity-panel">
              <header class="panel-header">
                <div>
                  <h2>处理记录</h2>
                  <p>申请关键操作与状态变化</p>
                </div>
              </header>
              <el-timeline v-if="activityTimeline.length" class="process-timeline">
                <el-timeline-item
                  v-for="item in activityTimeline"
                  :key="`${item.time}-${item.title}`"
                  :timestamp="formatDateTime(item.time)"
                  :type="item.type"
                >
                  <strong>{{ item.title }}</strong>
                  <p v-if="item.description">{{ item.description }}</p>
                </el-timeline-item>
              </el-timeline>
              <EmptyState v-else text="暂无处理记录" icon="Clock" compact />
            </section>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section v-else-if="!loading && !loadError" class="empty-surface">
      <EmptyState text="未找到申请" description="该申请可能已删除或当前账号无权查看。" icon="DocumentDelete">
        <template #action>
          <el-button type="primary" @click="router.push('/intellectual-property')">返回申请列表</el-button>
        </template>
      </EmptyState>
    </section>

    <IPReturnFormDialog
      v-model:visible="returnDialogVisible"
      :application-id="applicationId"
      :users="userList"
      @success="loadDetail"
    />
    <IPObjectionFormDialog
      v-model:visible="objectionDialogVisible"
      :application-id="applicationId"
      @success="loadDetail"
    />
    <IPObjectionReviewDialog
      v-model:visible="objectionReviewDialogVisible"
      :objection="reviewingObjection"
      :review-mode="reviewMode"
      @success="loadDetail"
    />

    <el-dialog
      v-model="candidateDialogVisible"
      :title="editingCandidate ? '编辑申报成员' : '添加申报成员'"
      width="560px"
      :close-on-click-modal="false"
      @close="handleCloseCandidateDialog"
    >
      <el-alert
        class="candidate-form-alert"
        title="这里只记录实名核验结果，不录入或展示身份证明文；身份证资料请通过敏感资料中心受控管理。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-form
        ref="candidateFormRef"
        :model="candidateForm"
        :rules="candidateRules"
        label-width="104px"
      >
        <el-form-item label="成员姓名" prop="user">
          <el-select
            v-model="candidateForm.user"
            placeholder="选择关联项目成员"
            filterable
            :disabled="Boolean(editingCandidate)"
            style="width: 100%"
          >
            <el-option
              v-for="user in userList"
              :key="user.id"
              :label="user.name || user.username || user.email"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="申报身份" prop="legal_role">
          <el-select v-model="candidateForm.legal_role" placeholder="请选择申报身份" style="width: 100%">
            <el-option
              v-for="item in candidateLegalRoleOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="署名顺序" prop="planned_order">
          <el-input-number v-model="candidateForm.planned_order" :min="1" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="实名核验" prop="identity_check_status">
          <el-select v-model="candidateForm.identity_check_status" style="width: 100%">
            <el-option
              v-for="item in candidateIdentityOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="提交状态" prop="status">
          <el-select v-model="candidateForm.status" style="width: 100%">
            <el-option
              v-for="item in candidateStatusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="candidateForm.note" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="可记录名单调整原因或待确认事项" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="candidateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="candidateSubmitting" @click="handleSubmitCandidate">
          {{ editingCandidate ? '保存修改' : '添加成员' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="contributorDialogVisible" title="添加协作成员" width="520px">
      <el-form ref="contributorFormRef" :model="contributorForm" :rules="contributorRules" label-width="88px">
        <el-form-item label="贡献人" prop="user">
          <el-select v-model="contributorForm.user" placeholder="选择贡献人" filterable style="width: 100%">
            <el-option
              v-for="user in userList"
              :key="user.id"
              :label="user.name || user.username || user.email"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="职责" prop="role">
          <el-select v-model="contributorForm.role" placeholder="选择职责" style="width: 100%">
            <el-option v-for="(label, key) in IP_CONTRIBUTOR_ROLE_MAP" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="贡献描述" prop="contribution_description">
          <el-input v-model="contributorForm.contribution_description" type="textarea" :rows="3" placeholder="说明该成员的实际贡献" />
        </el-form-item>
        <el-form-item label="责任说明" prop="responsibility_description">
          <el-input v-model="contributorForm.responsibility_description" type="textarea" :rows="3" placeholder="说明该成员负责的事项" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="contributorDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAddContributor">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="materialDialogVisible" title="上传申请材料" width="520px">
      <el-form ref="materialFormRef" :model="materialForm" :rules="materialRules" label-width="88px">
        <el-form-item label="文件">
          <span class="material-filename">{{ pendingFile?.name || '未选择文件' }}</span>
        </el-form-item>
        <el-form-item label="材料类型" prop="material_type">
          <el-select v-model="materialForm.material_type" placeholder="选择材料类型" style="width: 100%">
            <el-option v-for="(label, key) in IP_MATERIAL_TYPE_MAP" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="变更说明" prop="change_note">
          <el-input v-model="materialForm.change_note" type="textarea" :rows="3" placeholder="说明本版本的变更内容" />
        </el-form-item>
        <el-form-item label="版本状态" prop="is_final">
          <el-switch
            v-model="materialForm.is_final"
            active-text="上传后标记为最终版"
            inactive-text="过程版本"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="materialDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleUploadMaterial">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import {
  ArrowLeft,
  Avatar,
  ChatDotRound,
  DataBoard,
  Delete,
  DocumentChecked,
  Edit,
  EditPen,
  FolderOpened,
  MoreFilled,
  Plus,
  Promotion,
  Refresh,
  Upload,
  User,
  UserFilled,
  WarningFilled,
} from '@element-plus/icons-vue'
import {
  addIPCandidate,
  addIPContributor,
  archiveIPApplication,
  confirmIPContributor,
  deleteIPCandidate,
  deleteIPApplication,
  getIPApplication,
  getIPCandidates,
  resolveIPReturn,
  syncIPContribution,
  transitionIPStatus,
  updateIPCandidate,
  updateIPMaterial,
  uploadIPFinalCertificate,
  uploadIPMaterial,
} from '@/api/intellectualProperty'
import { getProject, getProjectMembers } from '@/api/projects'
import { getUsers } from '@/api/users'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDevice } from '@/composables/useDevice'
import { useUserStore } from '@/stores/user'
import type { Project, ProjectMember } from '@/types'
import type {
  IPApplication,
  IPApplicationCandidate,
  IPContributor,
  IPMaterialVersion,
  IPObjection,
  IPParticipantOption,
  IPReturnRecord,
  IPStatus,
} from '@/types/intellectualProperty'
import {
  IP_CONTRIBUTOR_ROLE_MAP,
  IP_MATERIAL_TYPE_MAP,
  IP_OBJECTION_STATUS_MAP,
  IP_OBJECTION_TYPE_MAP,
  IP_RESPONSIBILITY_TYPE_MAP,
  IP_RETURN_RESULT_MAP,
  IP_RETURN_SOURCE_MAP,
  IP_STATUS_MAP,
  IP_TYPE_MAP,
} from '@/utils/constants'
import { formatDate, formatDateTime } from '@/utils/format'
import IPObjectionFormDialog from './IPObjectionFormDialog.vue'
import IPObjectionReviewDialog from './IPObjectionReviewDialog.vue'
import IPReturnFormDialog from './IPReturnFormDialog.vue'
import IPStatusStepper from './components/IPStatusStepper.vue'
import {
  buildProjectParticipantOptions,
  getAvailableIPWorkflowActions,
  type IPWorkflowAction,
} from './ipWorkflow'

type TimelineTone = '' | 'primary' | 'success' | 'warning' | 'danger' | 'info'

interface TimelineItem {
  time: string
  title: string
  description?: string
  type: TimelineTone
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { isMobile } = useDevice()
const applicationId = Number(route.params.id)

const loading = ref(false)
const loadError = ref(false)
const submitting = ref(false)
const syncing = ref(false)
const statusTransitioning = ref(false)
const certificateUploading = ref(false)
const deleting = ref(false)
const materialUpdatingId = ref(0)
const candidateSubmitting = ref(false)
const activeTab = ref(route.query.tab === 'people' ? 'people' : 'overview')
const application = ref<IPApplication | null>(null)
const relatedProject = ref<Project | null>(null)
const projectMembers = ref<ProjectMember[]>([])
const candidates = ref<IPApplicationCandidate[]>([])
const contributors = ref<IPContributor[]>([])
const materials = ref<IPMaterialVersion[]>([])
const returnRecords = ref<IPReturnRecord[]>([])
const objections = ref<IPObjection[]>([])
const userList = ref<IPParticipantOption[]>([])

const returnDialogVisible = ref(false)
const objectionDialogVisible = ref(false)
const objectionReviewDialogVisible = ref(false)
const contributorDialogVisible = ref(false)
const materialDialogVisible = ref(false)
const candidateDialogVisible = ref(false)
const editingCandidate = ref<IPApplicationCandidate | null>(null)
const reviewingObjection = ref<IPObjection>({} as IPObjection)
const reviewMode = ref<'leader' | 'teacher'>('leader')

const contributorFormRef = ref<FormInstance>()
const contributorForm = reactive({
  user: null as number | null,
  role: '',
  contribution_description: '',
  responsibility_description: '',
})
const contributorRules: FormRules = {
  user: [{ required: true, message: '请选择贡献人', trigger: 'change' }],
  role: [{ required: true, message: '请选择职责', trigger: 'change' }],
}

const materialFormRef = ref<FormInstance>()
const pendingFile = ref<File | null>(null)
const materialForm = reactive({ material_type: '', change_note: '', is_final: false })
const materialRules: FormRules = {
  material_type: [{ required: true, message: '请选择材料类型', trigger: 'change' }],
}

const candidateLegalRoleOptions = [
  { value: 'inventor', label: '发明人' },
  { value: 'author', label: '著作权人 / 作者' },
  { value: 'applicant', label: '申请人' },
  { value: 'other', label: '其他' },
] as const
const candidateStatusOptions = [
  { value: 'proposed', label: '拟申报' },
  { value: 'identity_pending', label: '待实名核验' },
  { value: 'confirmed', label: '已确认入选' },
  { value: 'submitted', label: '已正式提交' },
  { value: 'withdrawn', label: '已撤回' },
] as const
const candidateIdentityOptions = [
  { value: 'pending', label: '待核验' },
  { value: 'matched', label: '实名一致' },
  { value: 'mismatched', label: '实名不一致' },
  { value: 'not_required', label: '无需核验' },
] as const

const candidateFormRef = ref<FormInstance>()
const candidateForm = reactive({
  user: null as number | null,
  legal_role: 'inventor' as IPApplicationCandidate['legal_role'],
  planned_order: 1,
  status: 'proposed' as IPApplicationCandidate['status'],
  identity_check_status: 'pending' as IPApplicationCandidate['identity_check_status'],
  note: '',
})
const candidateRules: FormRules = {
  user: [{ required: true, message: '请选择申报成员', trigger: 'change' }],
  legal_role: [{ required: true, message: '请选择申报身份', trigger: 'change' }],
  planned_order: [{ required: true, message: '请填写署名顺序', trigger: 'change' }],
  status: [{ required: true, message: '请选择提交状态', trigger: 'change' }],
  identity_check_status: [{ required: true, message: '请选择实名核验状态', trigger: 'change' }],
}

const currentUserId = computed(() => userStore.userInfo?.id || 0)
const hasPrivilegedRole = computed(() => userStore.role === 'teacher' || userStore.role === 'sys_admin')
const isProjectLeader = computed(() => Boolean(
  currentUserId.value
  && (
    relatedProject.value?.leader === currentUserId.value
    || projectMembers.value.some(
      (member) =>
        member.user === currentUserId.value
        && member.role_in_project === 'leader'
        && (!member.status || member.status === 'active'),
    )
  ),
))
const isMainWriter = computed(() => Boolean(currentUserId.value && application.value?.main_writer === currentUserId.value))
const isApplicantExecutor = computed(() => Boolean(currentUserId.value && application.value?.applicant_executor === currentUserId.value))
const isProjectReviewer = computed(() => Boolean(currentUserId.value && application.value?.project_reviewer === currentUserId.value))
const isTeacherConfirmer = computed(() => Boolean(currentUserId.value && application.value?.teacher_confirmer === currentUserId.value))
const canEditApplication = computed(() =>
  hasPrivilegedRole.value || isProjectLeader.value || isMainWriter.value || isApplicantExecutor.value,
)
const canManageCollaboration = computed(() => hasPrivilegedRole.value || isProjectLeader.value)
const canManageCandidateList = computed(() => hasPrivilegedRole.value || isProjectLeader.value)
const canAccessPrivateDetails = computed(() =>
  Boolean(application.value && Object.prototype.hasOwnProperty.call(application.value, 'contributors')),
)
const canMaintainMaterials = computed(() => canAccessPrivateDetails.value)
const canCreateReturn = computed(() =>
  ['research_office_review', 'resubmitted'].includes(application.value?.status || '')
  && (hasPrivilegedRole.value || isProjectLeader.value || isApplicantExecutor.value),
)
const canLeaderReview = computed(() => hasPrivilegedRole.value || isProjectLeader.value)
const canTeacherConfirm = computed(() => hasPrivilegedRole.value)
const canSubmitObjection = computed(() => canAccessPrivateDetails.value)
const hasConfirmableContribution = computed(() => contributors.value.some(canConfirmContributor))
const canTransitionCurrentStatus = computed(() => {
  const status = application.value?.status
  if (!status) return false
  if (hasPrivilegedRole.value) return true
  if (status === 'leader_review') return isProjectLeader.value || isProjectReviewer.value
  if (status === 'teacher_confirm') return isTeacherConfirmer.value
  if (['research_office_review', 'accepted', 'authorized'].includes(status)) return false
  return isProjectLeader.value || isMainWriter.value || isApplicantExecutor.value
})
const availableWorkflowActions = computed<readonly IPWorkflowAction[]>(() => {
  const app = application.value
  if (!app) return []
  return getAvailableIPWorkflowActions(
    app.status,
    canTransitionCurrentStatus.value,
    hasPrivilegedRole.value,
  )
})
const primaryWorkflowAction = computed(() => availableWorkflowActions.value[0] || null)
const secondaryWorkflowActions = computed(() => availableWorkflowActions.value.slice(1))
const finalMaterialCount = computed(() => materials.value.filter((item) => item.is_final).length)
const pendingReturnCount = computed(() => returnRecords.value.filter((item) => item.result === 'pending').length)
const pendingObjectionCount = computed(() =>
  objections.value.filter((item) => item.status === 'pending' || item.status === 'leader_reviewed').length,
)

const primaryOwner = computed(() => {
  const app = application.value
  if (!app) return '-'
  if (app.status === 'draft' || app.status === 'writing' || app.status === 'returned' || app.status === 'modifying') {
    return app.main_writer_detail?.name || app.main_writer_name || '未分配'
  }
  if (app.status === 'leader_review') return app.project_reviewer_detail?.name || app.project_reviewer_name || '未分配'
  if (app.status === 'teacher_confirm') return app.teacher_confirmer_detail?.name || app.teacher_confirmer_name || '未分配'
  return app.applicant_executor_detail?.name || app.applicant_executor_name || '未分配'
})

const currentResponsibility = computed(() => {
  const status = application.value?.status
  if (!status) return '-'
  if (status === 'draft' || status === 'writing') return '准备和撰写申请材料'
  if (status === 'leader_review') return '完成项目负责人审核'
  if (status === 'teacher_confirm') return '完成老师最终确认'
  if (status === 'returned' || status === 'modifying') return '处理退回修改事项'
  if (status === 'authorized' || status === 'archived') return '维护授权与归档材料'
  return '跟进外部申报流程'
})

const responsibilityRoles = computed(() => {
  if (!application.value) return []
  const app = application.value
  const coWriter = contributors.value.find((item) => item.role === 'co_writer')
  return [
    { key: 'main_writer', label: '主导撰写', name: app.main_writer_detail?.name || app.main_writer_name, desc: '成果内容真实性', icon: EditPen },
    { key: 'co_writer', label: '协作撰写', name: coWriter?.user_detail?.name || coWriter?.user_name, desc: '材料协作撰写', icon: DocumentChecked },
    { key: 'applicant_executor', label: '申请执行', name: app.applicant_executor_detail?.name || app.applicant_executor_name, desc: '外部申报对接', icon: Promotion },
    { key: 'material_manager', label: '材料整理', name: app.material_manager_detail?.name || app.material_manager_name, desc: '材料完整性', icon: FolderOpened },
    { key: 'project_reviewer', label: '项目审核', name: app.project_reviewer_detail?.name || app.project_reviewer_name, desc: '项目内初审', icon: User },
    { key: 'teacher_confirmer', label: '老师确认', name: app.teacher_confirmer_detail?.name || app.teacher_confirmer_name, desc: '最终确认', icon: Avatar },
  ]
})

const processTimeline = computed<TimelineItem[]>(() => {
  if (!application.value) return []
  const app = application.value
  const items: TimelineItem[] = []
  if (app.created_at) items.push({ time: app.created_at, title: '申请创建', description: `创建人：${app.created_by_name || '-'}`, type: 'primary' })
  if (app.start_date) items.push({ time: app.start_date, title: '开始撰写', type: 'info' })
  if (app.submit_date) items.push({ time: app.submit_date, title: '提交申请', type: 'primary' })
  returnRecords.value.forEach((record) => {
    items.push({ time: record.return_time, title: '申请退回', description: record.return_reason, type: 'danger' })
    if (record.result !== 'pending') {
      items.push({ time: record.updated_at, title: '退回事项已处理', description: record.modify_description || undefined, type: 'success' })
    }
  })
  if (app.accepted_date) items.push({ time: app.accepted_date, title: '申请受理', type: 'success' })
  if (app.authorized_date) items.push({ time: app.authorized_date, title: '授权或登记', type: 'success' })
  return items.sort((left, right) => new Date(right.time).getTime() - new Date(left.time).getTime())
})

const activityTimeline = computed<TimelineItem[]>(() => {
  const items = [...processTimeline.value]
  objections.value.forEach((item) => {
    items.push({
      time: item.updated_at || item.created_at,
      title: `异议：${IP_OBJECTION_STATUS_MAP[item.status]?.label || item.status}`,
      description: item.content,
      type: item.status === 'rejected' ? 'danger' : item.status === 'resolved' ? 'success' : 'warning',
    })
  })
  return items.sort((left, right) => new Date(right.time).getTime() - new Date(left.time).getTime())
})

const sortedReturnRecords = computed(() =>
  [...returnRecords.value].sort((left, right) => new Date(right.return_time).getTime() - new Date(left.return_time).getTime()),
)
const sortedObjections = computed(() =>
  [...objections.value].sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime()),
)

async function loadDetail(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const response = await getIPApplication(applicationId) as IPApplication
    application.value = response
    candidates.value = response.candidates || []
    contributors.value = response.contributors || []
    materials.value = response.material_versions || []
    returnRecords.value = response.return_records || []
    objections.value = response.objections || []
    relatedProject.value = null
    projectMembers.value = []
    if (response.related_project) {
      try {
        relatedProject.value = await getProject(response.related_project)
      } catch {
        // Project metadata only controls optional actions; the detail remains readable.
      }
    }
    await loadUsers()
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function loadUsers(): Promise<void> {
  try {
    const app = application.value
    if (!app?.related_project) {
      projectMembers.value = []
      if (userList.value.length) return
      if (!canManageCollaboration.value && !canCreateReturn.value) return
      const response = await getUsers({ page: 1, page_size: 100 }) as any
      userList.value = response.results || []
      return
    }

    const project = relatedProject.value || await getProject(app.related_project)
    const members = await getProjectMembers(app.related_project)
    projectMembers.value = members
    userList.value = buildProjectParticipantOptions(project, members)
  } catch {
    // The page remains usable if the optional member list cannot be loaded.
  }
}

function handleEdit(): void {
  router.push(`/intellectual-property/create?id=${applicationId}`)
}

async function handleDelete(): Promise<void> {
  if (!application.value || !hasPrivilegedRole.value) return
  try {
    await ElMessageBox.confirm(
      `确定删除成果“${application.value.title}”吗？删除后无法恢复。`,
      '删除成果与知识产权',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'error',
      },
    )
  } catch {
    return
  }

  deleting.value = true
  try {
    await deleteIPApplication(applicationId)
    ElMessage.success('成果与知识产权条目已删除')
    await router.replace('/intellectual-property')
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    deleting.value = false
  }
}

async function handleConfirmContributor(row: IPContributor): Promise<void> {
  try {
    await confirmIPContributor(row.id)
    ElMessage.success('贡献已确认')
    await loadDetail()
  } catch {
    // The request interceptor presents the backend error.
  }
}

function canConfirmContributor(row: IPContributor): boolean {
  return !row.is_confirmed && Boolean(currentUserId.value) && row.user === currentUserId.value
}

function candidateUserName(row: IPApplicationCandidate): string {
  const detail = row.user_detail
  return (
    detail?.name
    || detail?.username
    || detail?.email
    || userList.value.find((item) => item.id === row.user)?.name
    || `成员 #${row.user}`
  )
}

function candidateLegalRoleLabel(value: IPApplicationCandidate['legal_role']): string {
  return candidateLegalRoleOptions.find((item) => item.value === value)?.label || value
}

function candidateStatusLabel(value: IPApplicationCandidate['status']): string {
  return candidateStatusOptions.find((item) => item.value === value)?.label || value
}

function candidateIdentityLabel(value: IPApplicationCandidate['identity_check_status']): string {
  return candidateIdentityOptions.find((item) => item.value === value)?.label || value
}

function candidateStatusTone(value: IPApplicationCandidate['status']): 'success' | 'warning' | 'danger' | 'info' {
  if (value === 'submitted' || value === 'confirmed') return 'success'
  if (value === 'withdrawn') return 'danger'
  if (value === 'identity_pending') return 'warning'
  return 'info'
}

function candidateIdentityTone(
  value: IPApplicationCandidate['identity_check_status'],
): 'success' | 'warning' | 'danger' | 'info' {
  if (value === 'matched') return 'success'
  if (value === 'mismatched') return 'danger'
  if (value === 'pending') return 'warning'
  return 'info'
}

function resetCandidateForm(): void {
  Object.assign(candidateForm, {
    user: null,
    legal_role: 'inventor',
    planned_order: Math.max(
      1,
      ...candidates.value.map((item) => Number(item.planned_order) + 1),
    ),
    status: 'proposed',
    identity_check_status: 'pending',
    note: '',
  })
}

function handleAddCandidate(): void {
  editingCandidate.value = null
  resetCandidateForm()
  candidateDialogVisible.value = true
}

function handleEditCandidate(row: IPApplicationCandidate): void {
  editingCandidate.value = row
  Object.assign(candidateForm, {
    user: row.user,
    legal_role: row.legal_role,
    planned_order: row.planned_order,
    status: row.status,
    identity_check_status: row.identity_check_status,
    note: row.note || '',
  })
  candidateDialogVisible.value = true
}

function handleCloseCandidateDialog(): void {
  editingCandidate.value = null
  candidateFormRef.value?.clearValidate()
}

async function refreshCandidates(): Promise<void> {
  candidates.value = await getIPCandidates(applicationId)
  if (application.value) application.value.candidates = candidates.value
}

async function handleSubmitCandidate(): Promise<void> {
  if (!candidateFormRef.value || !candidateForm.user) return
  const valid = await candidateFormRef.value.validate().catch(() => false)
  if (!valid) return
  candidateSubmitting.value = true
  try {
    const payload = {
      legal_role: candidateForm.legal_role,
      planned_order: candidateForm.planned_order,
      status: candidateForm.status,
      identity_check_status: candidateForm.identity_check_status,
      note: candidateForm.note.trim(),
    }
    if (editingCandidate.value) {
      await updateIPCandidate(applicationId, editingCandidate.value.id, payload)
      ElMessage.success('申报名单已更新')
    } else {
      await addIPCandidate(applicationId, {
        user: candidateForm.user,
        ...payload,
      })
      ElMessage.success('申报成员已添加')
    }
    candidateDialogVisible.value = false
    await refreshCandidates()
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    candidateSubmitting.value = false
  }
}

async function handleDeleteCandidate(row: IPApplicationCandidate): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定从拟申报名单中移除“${candidateUserName(row)}”吗？`,
      '移除申报成员',
      {
        confirmButtonText: '移除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }
  candidateSubmitting.value = true
  try {
    await deleteIPCandidate(applicationId, row.id)
    ElMessage.success('申报成员已移除')
    await refreshCandidates()
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    candidateSubmitting.value = false
  }
}

async function handleAddContributor(): Promise<void> {
  if (!contributorFormRef.value) return
  const valid = await contributorFormRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await addIPContributor(applicationId, { ...contributorForm })
    ElMessage.success('协作成员已添加')
    contributorDialogVisible.value = false
    contributorFormRef.value.resetFields()
    await loadDetail()
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    submitting.value = false
  }
}

function handleMaterialUpload(file: UploadFile): void {
  pendingFile.value = file.raw || null
  if (pendingFile.value) materialDialogVisible.value = true
}

async function handleFinalCertificateUpload(file: UploadFile): Promise<void> {
  if (!file.raw) return
  certificateUploading.value = true
  try {
    await uploadIPFinalCertificate(applicationId, file.raw)
    ElMessage.success('最终证书已安全留存')
    await loadDetail()
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    certificateUploading.value = false
  }
}

function canEditMaterial(material: Partial<IPMaterialVersion>): boolean {
  return (
    hasPrivilegedRole.value
    || isProjectLeader.value
    || isMainWriter.value
    || isApplicantExecutor.value
    || material.uploaded_by === currentUserId.value
  )
}

async function handleToggleFinalMaterial(material: Partial<IPMaterialVersion>): Promise<void> {
  if (!material.id) return
  materialUpdatingId.value = material.id
  try {
    await updateIPMaterial(material.id, { is_final: !material.is_final })
    ElMessage.success(material.is_final ? '已取消最终版标记' : '已标记为最终版')
    await loadDetail()
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    materialUpdatingId.value = 0
  }
}

async function handleUploadMaterial(): Promise<void> {
  if (!materialFormRef.value || !pendingFile.value) return
  const valid = await materialFormRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('material_upload', pendingFile.value)
    formData.append('material_type', materialForm.material_type)
    formData.append('change_note', materialForm.change_note)
    formData.append('is_final', String(materialForm.is_final))
    await uploadIPMaterial(applicationId, formData)
    ElMessage.success('材料上传成功')
    materialDialogVisible.value = false
    materialFormRef.value.resetFields()
    materialForm.is_final = false
    pendingFile.value = null
    await loadDetail()
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    submitting.value = false
  }
}

function canResolveReturnRecord(record: IPReturnRecord): boolean {
  return hasPrivilegedRole.value ||
    isProjectLeader.value ||
    isMainWriter.value ||
    isApplicantExecutor.value ||
    record.responsible_user === currentUserId.value ||
    record.actual_modifier === currentUserId.value
}

async function handleWorkflowAction(workflowAction: IPWorkflowAction): Promise<void> {
  let statusNote = ''
  try {
    if (['paused', 'terminated', 'deferred'].includes(workflowAction.targetStatus)) {
      const result = await ElMessageBox.prompt(
        `${workflowAction.confirmation} 请填写原因，便于团队后续追踪。`,
        workflowAction.label,
        {
          confirmButtonText: workflowAction.label,
          cancelButtonText: '取消',
          inputType: 'textarea',
          inputValidator: (value) => Boolean(String(value || '').trim()) || '请填写状态原因',
        },
      )
      statusNote = String(result.value || '').trim()
    } else {
      await ElMessageBox.confirm(workflowAction.confirmation, workflowAction.label, {
        confirmButtonText: workflowAction.label,
        cancelButtonText: '取消',
        type: workflowAction.tone === 'danger' ? 'error' : (workflowAction.tone || 'info'),
      })
    }
  } catch {
    return
  }

  statusTransitioning.value = true
  try {
    if (workflowAction.kind === 'archive') {
      await archiveIPApplication(applicationId)
      ElMessage.success('成果已归档')
    } else if (workflowAction.kind === 'return') {
      activeTab.value = 'materials'
      returnDialogVisible.value = true
      return
    } else {
      await transitionIPStatus(applicationId, {
        target_status: workflowAction.targetStatus,
        note: statusNote || undefined,
      })
      ElMessage.success(`申请已进入${IP_STATUS_MAP[workflowAction.targetStatus]?.label || workflowAction.label}`)
    }
    await loadDetail()
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    statusTransitioning.value = false
  }
}

function handleWorkflowCommand(targetStatus: IPStatus): void {
  const workflowAction = availableWorkflowActions.value.find((item) => item.targetStatus === targetStatus)
  if (workflowAction) handleWorkflowAction(workflowAction)
}

async function handleResolveReturn(record: IPReturnRecord): Promise<void> {
  try {
    const { value } = await ElMessageBox.prompt('请输入本次修改说明', '完成退回修改', {
      confirmButtonText: '确认完成',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputValidator: (input) => Boolean(String(input || '').trim()) || '请输入修改说明',
    })
    await resolveIPReturn(record.id, { modify_description: value, result: 'modified' })
    ElMessage.success('退回事项已完成')
    await loadDetail()
  } catch {
    // Cancelled prompts and request errors require no additional UI.
  }
}

async function handleSyncContribution(): Promise<void> {
  syncing.value = true
  try {
    await syncIPContribution(applicationId)
    ElMessage.success('贡献记录同步成功')
    await loadDetail()
  } catch {
    // The request interceptor presents the backend error.
  } finally {
    syncing.value = false
  }
}

function handleReviewObjection(objection: IPObjection, mode: 'leader' | 'teacher'): void {
  reviewingObjection.value = objection
  reviewMode.value = mode
  objectionReviewDialogVisible.value = true
}

function getTypeColor(type: string): any {
  return (IP_TYPE_MAP[type]?.color || '') as any
}

function getStatusColor(status: string): any {
  return (IP_STATUS_MAP[status]?.color || '') as any
}

function getReturnColor(status: string): any {
  return (IP_RETURN_RESULT_MAP[status]?.color || '') as any
}

function objectionStatusColor(status: string): any {
  return (IP_OBJECTION_STATUS_MAP[status]?.color || '') as any
}

onMounted(() => {
  loadDetail()
})
</script>

<style lang="scss" scoped>
.ip-detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: visible;
}

.ip-detail-page :deep(.page-header) { margin-bottom: 0; }

:global(.el-dropdown-menu__item.danger-action) { color: var(--color-danger); }

.application-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.status-banner,
.attention-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
}

.status-banner {
  color: var(--danger-text);
  background: var(--danger-light);
  border: 1px solid var(--danger-border);
}

.status-banner span { flex: 1; }

.application-summary {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.summary-facts {
  display: grid;
  grid-template-columns: 1.2fr 1.2fr repeat(3, minmax(120px, 0.7fr));
}

.summary-fact {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 14px 18px;
}

.summary-fact + .summary-fact { border-left: 1px solid var(--color-border-light); }
.summary-fact span { color: var(--color-text-muted); font-size: 11px; }
.summary-fact strong { margin-top: 4px; overflow: hidden; color: var(--color-text); font-size: 17px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
.summary-fact small { margin-top: 2px; overflow: hidden; color: var(--color-text-muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.summary-fact--owner strong { color: var(--color-primary); }
.summary-fact--danger strong { color: var(--color-danger); }
.summary-fact--warning strong { color: var(--color-warning); }

.summary-progress {
  padding: 10px 18px 12px;
  border-top: 1px solid var(--color-border-light);
}

.attention-banner {
  align-items: flex-start;
  color: var(--warning-text);
  background: var(--warning-light);
  border: 1px solid var(--warning-border);
}

.attention-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  background: rgba(166, 97, 22, 0.1);
  border-radius: var(--radius-sm);
}

.attention-banner span { font-size: 11px; font-weight: 600; }
.attention-banner p { margin-top: 2px; color: var(--warning-text); font-size: 13px; line-height: 1.5; }

.detail-workspace {
  min-width: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.business-tabs :deep(.el-tabs__header) { margin: 0; padding: 0 18px; border-bottom: 1px solid var(--color-border-light); }
.business-tabs :deep(.el-tabs__nav-wrap::after) { display: none; }
.business-tabs :deep(.el-tabs__item) { height: 48px; padding: 0 18px; color: var(--color-text-muted); }
.business-tabs :deep(.el-tabs__item.is-active) { color: var(--color-primary); font-weight: 600; }
.business-tabs :deep(.el-tabs__content) { padding: 18px; }

.tab-label { display: inline-flex; align-items: center; gap: 6px; }
.overview-grid,
.records-grid { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.75fr); gap: 16px; }
.materials-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.85fr); gap: 16px; }

.workspace-panel { min-width: 0; }
.candidate-panel {
  margin-bottom: 22px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border-light);
}
.candidate-form-alert { margin-bottom: 18px; }
.candidate-mobile-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
  margin-top: 10px;
}
.candidate-mobile-meta dt { color: var(--color-text-muted); font-size: 10px; }
.candidate-mobile-meta dd { margin-top: 2px; color: var(--color-text-regular); font-size: 12px; }
.overview-grid > .workspace-panel,
.materials-grid > .workspace-panel,
.records-grid > .workspace-panel { padding: 0; }

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  min-height: 50px;
  margin-bottom: 14px;
}

.panel-header h2 { color: var(--color-text); font-size: 15px; font-weight: 600; }
.panel-header p { margin-top: 3px; color: var(--color-text-muted); font-size: 11px; }
.panel-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 1px solid var(--color-border-light);
  border-left: 1px solid var(--color-border-light);
}

.detail-grid > div {
  min-width: 0;
  padding: 12px 14px;
  border-right: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);
}

.detail-grid dt,
.return-meta dt,
.review-notes dt { color: var(--color-text-muted); font-size: 11px; }
.detail-grid dd { margin-top: 4px; overflow-wrap: anywhere; color: var(--color-text); font-size: 13px; }
.detail-grid__wide { grid-column: 1 / -1; }
.long-copy { line-height: 1.65; white-space: pre-wrap; }

.process-timeline { padding-top: 4px; }
.process-timeline strong { color: var(--color-text); font-size: 13px; font-weight: 600; }
.process-timeline p { display: -webkit-box; margin-top: 3px; overflow: hidden; color: var(--color-text-muted); font-size: 12px; line-height: 1.45; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
.process-timeline :deep(.el-timeline-item__timestamp) { color: var(--color-text-muted); font-size: 11px; }

.role-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--color-border-light); border-left: 1px solid var(--color-border-light); }
.role-item { display: flex; align-items: flex-start; gap: 10px; min-width: 0; padding: 13px; border-right: 1px solid var(--color-border-light); border-bottom: 1px solid var(--color-border-light); }
.role-icon { display: flex; align-items: center; justify-content: center; width: 30px; height: 30px; flex: 0 0 auto; color: var(--ip-color); background: var(--ip-light); border-radius: var(--radius-sm); }
.role-copy { display: flex; flex-direction: column; min-width: 0; }
.role-copy span { color: var(--color-text-muted); font-size: 11px; }
.role-copy strong { margin-top: 2px; overflow: hidden; color: var(--color-text); font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.role-copy small { margin-top: 2px; color: var(--color-text-muted); font-size: 10px; }
.section-divider { height: 1px; margin: 18px 0; background: var(--color-border-light); }
.archive-readiness {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) auto;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  padding: 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}
.archive-readiness__item { display: grid; grid-template-columns: 1fr auto; gap: 3px 8px; min-width: 0; }
.archive-readiness__item > span { grid-column: 1 / -1; color: var(--color-text-muted); font-size: 10px; }
.archive-readiness__item > strong { overflow: hidden; color: var(--color-text); font-size: 12px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.table-wrap { width: 100%; overflow-x: auto; }
.table-primary { color: var(--color-text); font-size: 13px; font-weight: 600; }
.muted-text { color: var(--color-text-muted); font-size: 11px; }

.return-list,
.objection-list { border-top: 1px solid var(--color-border-light); }
.return-row,
.objection-row { padding: 14px 0; border-bottom: 1px solid var(--color-border-light); }
.return-row:last-child,
.objection-row:last-child { border-bottom: 0; }
.return-row__header,
.objection-row__header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.return-tags,
.objection-row__header > div { display: flex; align-items: center; gap: 8px; min-width: 0; color: var(--color-text-muted); font-size: 11px; }
.return-row time,
.objection-row time { flex: 0 0 auto; color: var(--color-text-muted); font-size: 10px; }
.return-row h3 { margin-top: 9px; color: var(--color-text); font-size: 13px; font-weight: 600; line-height: 1.5; }
.return-meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 12px; margin-top: 10px; }
.return-meta dd { margin-top: 2px; color: var(--color-text-regular); font-size: 12px; }
.resolution-copy { margin-top: 10px; padding: 8px 10px; color: var(--color-text-regular); font-size: 12px; line-height: 1.5; background: var(--color-surface-subtle); border-left: 2px solid var(--color-success); }
.return-row > .el-button { margin-top: 10px; }

.objection-author { margin-top: 9px; color: var(--color-text); font-size: 12px; font-weight: 600; }
.objection-content { margin-top: 5px; color: var(--color-text-regular); font-size: 13px; line-height: 1.6; white-space: pre-wrap; }
.review-notes { margin-top: 10px; padding: 10px; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.review-notes > div + div { margin-top: 8px; }
.review-notes dd { margin-top: 2px; color: var(--color-text-regular); font-size: 12px; line-height: 1.5; }
.row-actions { display: flex; gap: 8px; margin-top: 10px; }
.material-filename { color: var(--color-text-regular); font-size: 13px; overflow-wrap: anywhere; }
.empty-surface { padding: 36px 18px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }

.mobile-record-list { border-top: 1px solid var(--color-border-light); }
.mobile-record { padding: 13px 0; border-bottom: 1px solid var(--color-border-light); }
.mobile-record:last-child { border-bottom: 0; }
.mobile-record__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.mobile-record__header > div { display: flex; flex-direction: column; min-width: 0; }
.mobile-record__header strong { overflow-wrap: anywhere; color: var(--color-text); font-size: 13px; font-weight: 600; }
.mobile-record__header span { margin-top: 3px; color: var(--color-text-muted); font-size: 11px; }
.mobile-record p { margin-top: 8px; color: var(--color-text-regular); font-size: 12px; line-height: 1.5; }
.mobile-record small { display: block; margin-top: 4px; color: var(--color-text-muted); font-size: 11px; }
.mobile-record > .el-button { margin-top: 6px; }

@media screen and (max-width: 1180px) {
  .summary-facts { grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .overview-grid,
  .records-grid,
  .materials-grid { grid-template-columns: 1fr; }
  .role-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media screen and (max-width: 768px) {
  .ip-detail-page { gap: 12px; }
  .application-meta { flex-wrap: wrap; }
  .application-summary { position: static; }
  .summary-facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .summary-fact { min-height: 82px; padding: 11px 12px; }
  .summary-fact + .summary-fact { border-left: 0; }
  .summary-fact:nth-child(even) { border-left: 1px solid var(--color-border-light); }
  .summary-fact:nth-child(n + 3) { border-top: 1px solid var(--color-border-light); }
  .summary-fact:last-child { grid-column: 1 / -1; }
  .archive-readiness { grid-template-columns: 1fr; align-items: stretch; }
  .summary-fact strong { font-size: 15px; }
  .summary-progress { padding: 10px 12px; }
  .business-tabs :deep(.el-tabs__header) { padding: 0 10px; }
  .business-tabs :deep(.el-tabs__nav-scroll) { overflow-x: auto; }
  .business-tabs :deep(.el-tabs__nav) { float: none; width: max-content; }
  .business-tabs :deep(.el-tabs__item) { height: 44px; padding: 0 12px; }
  .business-tabs :deep(.el-tabs__content) { padding: 14px; }
  .panel-header--actions { flex-direction: column; }
  .panel-actions { width: 100%; justify-content: flex-start; }
  .role-grid { grid-template-columns: 1fr; }
  .detail-grid { grid-template-columns: 1fr; }
  .detail-grid__wide { grid-column: auto; }
  .return-meta { grid-template-columns: 1fr; }
  .return-row__header,
  .objection-row__header { align-items: flex-start; }
}
</style>
