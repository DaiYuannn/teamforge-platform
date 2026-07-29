<template>
  <div class="page-container sensitive-center-page">
    <PageHeader title="敏感资料" subtitle="资料目录、我的访问申请与访问审批工作区">
      <template #meta>
        <span class="page-meta">安全访问全程受授权时限控制</span>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab" class="sensitive-workspace" @tab-change="handleTabChange">
      <el-tab-pane label="资料目录" name="my-data">
        <template #label>
          <span class="tab-label"><el-icon><Files /></el-icon>资料目录</span>
        </template>
        <div class="pane-heading">
          <div>
            <h2>团队敏感资料目录</h2>
            <span>
              {{ myDataList.length }} 项脱敏资料
              <template v-if="requestedSubjectUserId"> · 已按成员筛选</template>
            </span>
          </div>
          <div class="panel-actions">
            <el-button :icon="Plus" @click="handleCreate">录入资料</el-button>
            <el-button type="primary" :icon="View" @click="handleApply">申请查看</el-button>
          </div>
        </div>

        <el-alert
          v-if="requestedSubjectUserId"
          class="subject-filter-alert"
          type="info"
          :closable="false"
          show-icon
        >
          <template #title>
            当前仅显示资料本人为“{{ filteredSubjectName }}”的可见条目
          </template>
          <el-button link type="primary" @click="clearSubjectFilter">查看全部可见资料</el-button>
        </el-alert>

        <el-table v-if="!isMobile" v-loading="myDataLoading" :data="myDataList" stripe size="small">
          <el-table-column prop="title" label="名称" min-width="160">
            <template #default="{ row }"><strong class="record-name">{{ row.title || row.label || '暂无名称' }}</strong></template>
          </el-table-column>
          <el-table-column prop="data_type" label="类型" width="130">
            <template #default="{ row }">
              <el-tag :type="SENSITIVE_DATA_TYPE_MAP[row.data_type]?.tagType as any" size="small" effect="plain">
                {{ row.data_type_display || SENSITIVE_DATA_TYPE_MAP[row.data_type]?.label || row.data_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="masked_value" label="脱敏值" min-width="200">
            <template #default="{ row }"><code class="masked-value">{{ row.masked_value || '-' }}</code></template>
          </el-table-column>
          <el-table-column prop="subject_name" label="资料本人" min-width="110">
            <template #default="{ row }">{{ row.subject_name || row.owner_name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="team_name" label="所属小团队" min-width="120">
            <template #default="{ row }">{{ row.team_name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="120">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.active_direct_grant?.can_view"
                link
                type="primary"
                :icon="View"
                @click="handleGrantView(row as SensitiveData)"
              >授权查看</el-button>
              <el-button
                v-if="row.active_direct_grant?.can_download && row.has_file"
                link
                type="success"
                :icon="Download"
                @click="handleGrantDownload(row as SensitiveData)"
              >授权下载</el-button>
              <el-button
                v-if="row.can_manage_grants"
                link
                @click="openGrantDialog(row as SensitiveData)"
              >授权管理</el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无敏感资料" /></template>
        </el-table>

        <div v-else v-loading="myDataLoading" class="mobile-record-list">
          <article v-for="item in myDataList" :key="item.id" class="mobile-record-card">
            <div class="mobile-card-heading">
              <div><h3>{{ item.title || item.label || '暂无名称' }}</h3><span>{{ formatDate(item.created_at) }}</span></div>
              <el-tag :type="SENSITIVE_DATA_TYPE_MAP[item.data_type]?.tagType as any" size="small" effect="plain">
                {{ SENSITIVE_DATA_TYPE_MAP[item.data_type]?.label || item.data_type }}
              </el-tag>
            </div>
            <div class="mobile-masked-value"><span>脱敏值</span><code>{{ item.masked_value || '-' }}</code></div>
            <dl class="mobile-meta-grid">
              <div><dt>资料本人</dt><dd>{{ item.subject_name || item.owner_name || '-' }}</dd></div>
              <div><dt>所属小团队</dt><dd>{{ item.team_name || '-' }}</dd></div>
            </dl>
            <div v-if="item.active_direct_grant || item.can_manage_grants" class="mobile-access-buttons">
              <el-button v-if="item.active_direct_grant?.can_view" size="small" @click="handleGrantView(item)">授权查看</el-button>
              <el-button v-if="item.can_manage_grants" size="small" @click="openGrantDialog(item)">授权管理</el-button>
            </div>
          </article>
          <el-empty v-if="myDataList.length === 0 && !myDataLoading" description="暂无敏感资料" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="我的访问申请" name="requests">
        <template #label>
          <span class="tab-label"><el-icon><View /></el-icon>我的访问申请</span>
        </template>
        <div class="pane-heading">
          <div>
            <h2>我的访问申请</h2>
            <span>{{ myRequestsTotal }} 条申请记录</span>
          </div>
          <el-button type="primary" :icon="Plus" @click="handleApply">申请查看</el-button>
        </div>

        <div v-if="!isMobile" class="table-shell">
          <el-table v-loading="requestsLoading" :data="myRequestsList" stripe size="small">
          <el-table-column prop="sensitive_data_type" label="资料" min-width="156">
            <template #default="{ row }">
              <div class="data-cell">
                <strong>{{ row.sensitive_data_title || getSensitiveTypeLabel(row as SensitiveAccessRequest) }}</strong>
                <span>{{ getSensitiveTypeLabel(row as SensitiveAccessRequest) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="usage_scenario" label="使用场景" min-width="130" show-overflow-tooltip />
          <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />
          <el-table-column prop="project_name" label="所属项目" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.project_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="访问范围" width="94">
            <template #default="{ row }">
              <el-tag v-if="row.is_download || row.need_download" type="danger" size="small" effect="plain">含下载</el-tag>
              <span v-else>仅查看</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getRequestStatus(row as SensitiveAccessRequest).type as any" size="small" effect="plain">
                {{ getRequestStatus(row as SensitiveAccessRequest).label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="申请时间" width="120">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="剩余时间" width="100">
            <template #default="{ row }">
              <span v-if="row.status === 'approved' && !isExpired(row as SensitiveAccessRequest)" class="remaining-time">
                {{ getRemainingTime(getRequestExpiry(row as SensitiveAccessRequest)) }}
              </span>
              <span v-else-if="row.status === 'approved' && isExpired(row as SensitiveAccessRequest)" class="text-expired">已过期</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="168" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'approved' && !isExpired(row as SensitiveAccessRequest)"
                :icon="View"
                type="primary"
                link
                @click="handleViewData(row as SensitiveAccessRequest)"
              >
                查看
              </el-button>
              <el-button
                v-if="canDownloadAttachment(row as SensitiveAccessRequest)"
                :icon="Download"
                type="success"
                link
                :loading="downloadingRequestId === row.id"
                @click="handleDownloadAttachment(row as SensitiveAccessRequest)"
              >
                下载
              </el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无访问申请" /></template>
        </el-table>
        </div>

        <div v-else v-loading="requestsLoading" class="mobile-record-list">
          <article v-for="item in myRequestsList" :key="item.id" class="mobile-record-card request-card">
            <div class="mobile-card-heading">
              <div><h3>{{ item.sensitive_data_title || getSensitiveTypeLabel(item) }}</h3><span>{{ getSensitiveTypeLabel(item) }}</span></div>
              <el-tag :type="getRequestStatus(item).type as any" size="small" effect="plain">{{ getRequestStatus(item).label }}</el-tag>
            </div>
            <dl class="mobile-meta-grid">
              <div class="meta-wide"><dt>申请理由</dt><dd>{{ item.reason || '-' }}</dd></div>
              <div><dt>所属项目</dt><dd>{{ item.project_name || '-' }}</dd></div>
              <div><dt>访问范围</dt><dd :class="{ 'danger-text': item.is_download || item.need_download }">{{ item.is_download || item.need_download ? '查看并下载' : '仅查看' }}</dd></div>
              <div><dt>申请时间</dt><dd>{{ formatDate(item.created_at) }}</dd></div>
            </dl>
            <div v-if="item.status === 'approved' && !isExpired(item)" class="mobile-access-action">
              <span>剩余 {{ getRemainingTime(getRequestExpiry(item)) }}</span>
              <div class="mobile-access-buttons">
                <el-button :icon="View" type="primary" size="small" @click="handleViewData(item)">查看明文</el-button>
                <el-button
                  v-if="canDownloadAttachment(item)"
                  :icon="Download"
                  type="success"
                  size="small"
                  :loading="downloadingRequestId === item.id"
                  @click="handleDownloadAttachment(item)"
                >
                  下载附件
                </el-button>
              </div>
            </div>
          </article>
          <el-empty v-if="myRequestsList.length === 0 && !requestsLoading" description="暂无访问申请" />
        </div>
        <footer v-if="myRequestsTotal > 0" class="pagination-wrapper">
          <AccessiblePagination
            v-model:current-page="myRequestsPage"
            v-model:page-size="myRequestsPageSize"
            :total="myRequestsTotal"
            :page-sizes="[10, 20, 50]"
            :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next'"
            :pager-count="isMobile ? 5 : 7"
            background
            @size-change="handleMyRequestsPageSizeChange"
            @current-change="loadMyRequests"
          />
        </footer>
      </el-tab-pane>

      <el-tab-pane v-if="canApprove" label="访问审批队列" name="pending">
        <template #label>
          <span class="tab-label"><el-icon><CircleCheck /></el-icon>访问审批队列</span>
        </template>
        <div>
          <div class="pane-heading pending-heading">
            <div>
              <h2>访问审批队列</h2>
              <span>{{ pendingTotal }} 项待处理</span>
            </div>
            <el-tag v-if="pendingTotal" type="warning" size="small" effect="plain">需要处理</el-tag>
          </div>

          <div v-if="!isMobile" class="table-shell">
            <el-table v-loading="pendingLoading" :data="pendingList" stripe size="small">
            <el-table-column prop="applicant_name" label="申请人" width="110">
              <template #default="{ row }"><strong class="record-name">{{ row.applicant_name || row.requester_name || '-' }}</strong></template>
            </el-table-column>
            <el-table-column prop="sensitive_data_type" label="资料" min-width="150">
              <template #default="{ row }">
                <div class="data-cell">
                  <strong>{{ row.sensitive_data_title || getSensitiveTypeLabel(row as SensitiveAccessRequest) }}</strong>
                  <span>{{ getSensitiveTypeLabel(row as SensitiveAccessRequest) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="usage_scenario" label="使用场景" min-width="130" show-overflow-tooltip />
            <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />
            <el-table-column prop="project_name" label="所属项目" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.project_name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="is_download" label="访问范围" width="96">
              <template #default="{ row }">
                <el-tag v-if="row.is_download || row.need_download" type="danger" size="small" effect="plain">申请下载</el-tag>
                <span v-else>仅查看</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="154" fixed="right" align="right">
              <template #default="{ row }">
                <el-button :icon="CircleCheck" type="success" link @click="handleApprove(row as SensitiveAccessRequest)">批准</el-button>
                <el-button :icon="CircleClose" type="danger" link @click="handleReject(row as SensitiveAccessRequest)">驳回</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无待审批申请" /></template>
            </el-table>
          </div>

          <div v-else v-loading="pendingLoading" class="mobile-record-list">
            <article v-for="item in pendingList" :key="item.id" class="mobile-record-card approval-card" :class="{ 'has-download-risk': item.is_download || item.need_download }">
              <div class="mobile-card-heading">
                <div><h3>{{ item.applicant_name || item.requester_name || '-' }}</h3><span>{{ item.sensitive_data_title || getSensitiveTypeLabel(item) }}</span></div>
                <el-tag :type="item.is_download || item.need_download ? 'danger' : 'warning'" size="small" effect="plain">{{ item.is_download || item.need_download ? '申请下载' : '待审批' }}</el-tag>
              </div>
              <dl class="mobile-meta-grid">
                <div class="meta-wide"><dt>使用场景</dt><dd>{{ item.usage_scenario || '-' }}</dd></div>
                <div class="meta-wide"><dt>申请理由</dt><dd>{{ item.reason || '-' }}</dd></div>
                <div><dt>所属项目</dt><dd>{{ item.project_name || '-' }}</dd></div>
                <div><dt>申请时间</dt><dd>{{ formatDate(item.created_at) }}</dd></div>
              </dl>
              <div class="mobile-decision-actions">
                <el-button :icon="CircleClose" type="danger" plain @click="handleReject(item)">驳回</el-button>
                <el-button :icon="CircleCheck" type="success" @click="handleApprove(item)">批准</el-button>
              </div>
            </article>
            <el-empty v-if="pendingList.length === 0 && !pendingLoading" description="暂无待审批申请" />
          </div>
          <footer v-if="pendingTotal > 0" class="pagination-wrapper">
            <AccessiblePagination
              v-model:current-page="pendingPage"
              v-model:page-size="pendingPageSize"
              :total="pendingTotal"
              :page-sizes="[10, 20, 50]"
              :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next'"
              :pager-count="isMobile ? 5 : 7"
              background
              @size-change="handlePendingPageSizeChange"
              @current-change="loadPending"
            />
          </footer>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="applyDialogVisible" title="申请查看敏感资料" width="680px" :close-on-click-modal="false" @close="handleCloseApply">
      <el-form ref="applyFormRef" class="apply-form" :model="applyForm" :rules="applyRules" label-position="top">
        <div class="apply-form-grid">
          <el-form-item class="form-wide" label="敏感资料" prop="sensitive_data">
          <el-select v-model="applyForm.sensitive_data" :loading="optionsLoading" placeholder="请选择敏感资料" filterable>
            <el-option
              v-for="d in sensitiveDataOptions"
              :key="d.id"
              :label="sensitiveOptionLabel(d)"
              :value="d.id"
            />
          </el-select>
          </el-form-item>
          <el-form-item class="form-wide" label="使用场景" prop="usage_scenario">
            <el-input v-model="applyForm.usage_scenario" placeholder="请描述使用场景" />
          </el-form-item>
          <el-form-item class="form-wide" label="申请理由" prop="reason">
            <el-input v-model="applyForm.reason" type="textarea" :rows="3" placeholder="请输入申请理由" />
          </el-form-item>
          <el-form-item label="所属项目">
          <el-select v-model="applyForm.project" placeholder="可选" clearable filterable>
            <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          </el-form-item>
          <el-form-item label="预计使用时间">
            <el-date-picker v-model="applyForm.expected_use_time" type="datetime" placeholder="选择时间" value-format="YYYY-MM-DD HH:mm:ss" />
          </el-form-item>
          <el-form-item class="form-wide download-option" :class="{ 'is-selected': applyForm.is_download }" label="下载权限">
            <div class="download-control">
              <div>
                <strong>{{ applyForm.is_download ? '申请查看并下载' : '仅申请在线查看' }}</strong>
                <span>{{ applyForm.is_download ? '审批人将重点核验下载必要性' : '明文将在授权时限内显示' }}</span>
              </div>
              <el-switch v-model="applyForm.is_download" />
            </div>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="applyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitApply">提交申请</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="createDialogVisible"
      title="录入敏感资料"
      width="680px"
      :close-on-click-modal="false"
      @close="handleCloseCreate"
    >
      <el-alert
        class="sensitive-create-alert"
        title="明文提交后会加密保存，资料目录只展示脱敏值；代其他成员录入时由后端核验团队负责人或审批权限。"
        type="warning"
        :closable="false"
        show-icon
      />
      <el-form
        ref="createFormRef"
        class="apply-form"
        :model="createForm"
        :rules="createRules"
        label-position="top"
      >
        <div class="apply-form-grid">
          <el-form-item label="资料类型" prop="data_type">
            <el-select v-model="createForm.data_type" placeholder="请选择资料类型" style="width: 100%">
              <el-option
                v-for="item in sensitiveTypeOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="所属小团队" prop="team">
            <el-select
              v-model="createForm.team"
              :loading="createOptionsLoading"
              placeholder="请选择所属小团队"
              filterable
              style="width: 100%"
              @change="handleCreateTeamChange"
            >
              <el-option
                v-for="team in teamOptions"
                :key="team.id"
                :label="team.parent_name ? `${team.parent_name} / ${team.name}` : team.name"
                :value="team.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="资料本人" prop="subject_user">
            <el-select
              v-model="createForm.subject_user"
              :loading="subjectOptionsLoading"
              placeholder="请选择资料本人"
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="member in subjectOptions"
                :key="member.user"
                :label="`${member.user_name}${member.user_email ? `（${member.user_email}）` : ''}`"
                :value="member.user"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="关联项目">
            <el-select
              v-model="createForm.project"
              placeholder="可选"
              clearable
              filterable
              style="width: 100%"
              @change="handleSensitiveProjectChange"
            >
              <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item class="form-wide" label="资料标题" prop="title">
            <el-input v-model="createForm.title" placeholder="例如：张三身份证号（专利申报）" maxlength="200" show-word-limit />
          </el-form-item>
          <el-form-item class="form-wide" label="资料明文" prop="plaintext">
            <el-input
              v-model="createForm.plaintext"
              type="textarea"
              :rows="3"
              autocomplete="off"
              placeholder="请输入需要加密保存的完整内容"
            />
          </el-form-item>
          <el-form-item class="form-wide" label="资料附件">
            <el-radio-group v-model="createForm.attachment_mode" @change="handleAttachmentModeChange">
              <el-radio-button value="none">无附件</el-radio-button>
              <el-radio-button value="existing">选择已有文件</el-radio-button>
              <el-radio-button value="upload">直接上传</el-radio-button>
            </el-radio-group>
            <el-select
              v-if="createForm.attachment_mode === 'existing'"
              v-model="createForm.file_attachment"
              class="attachment-control"
              clearable
              filterable
              :loading="attachmentOptionsLoading"
              placeholder="请选择本人上传或有权管理的项目文件"
            >
              <el-option
                v-for="file in attachmentOptions"
                :key="file.id"
                :label="`${file.name} · ${file.level_display || file.level}`"
                :value="file.id"
              />
            </el-select>
            <el-upload
              v-if="createForm.attachment_mode === 'upload'"
              class="attachment-control"
              drag
              :auto-upload="false"
              :limit="1"
              :file-list="createAttachmentFileList"
              :on-change="handleCreateAttachmentChange"
              :on-remove="handleCreateAttachmentRemove"
            >
              <el-icon><UploadFilled /></el-icon>
              <div>选择证件照、授权书、PPT、计划书或其他资料</div>
              <template #tip><span>上传后立即按敏感附件保存并撤销分享链接</span></template>
            </el-upload>
            <p class="form-help">明文与附件至少填写一项；也可只上传证件照或扫描件。</p>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitCreate">加密保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="approveDialogVisible" title="批准访问申请" width="460px" :close-on-click-modal="false">
      <div v-if="currentRequest" class="dialog-request-summary">
        <strong>{{ currentRequest.applicant_name || currentRequest.requester_name || '-' }}</strong>
        <span>{{ currentRequest.sensitive_data_title || getSensitiveTypeLabel(currentRequest) }}</span>
        <el-tag v-if="currentRequest.is_download || currentRequest.need_download" type="danger" size="small" effect="plain">包含下载权限</el-tag>
      </div>
      <el-form class="decision-form" :model="approveForm" label-position="top">
        <el-form-item label="有效时长（小时）">
          <el-input-number v-model="approveForm.expire_hours" :min="1" :max="24" controls-position="right" />
        </el-form-item>
        <el-form-item label="审批意见">
          <el-input v-model="approveForm.approval_opinion" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="submitting" @click="handleConfirmApprove">确认批准</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rejectDialogVisible" title="驳回访问申请" width="460px" :close-on-click-modal="false">
      <div v-if="currentRequest" class="dialog-request-summary">
        <strong>{{ currentRequest.applicant_name || currentRequest.requester_name || '-' }}</strong>
        <span>{{ currentRequest.sensitive_data_title || getSensitiveTypeLabel(currentRequest) }}</span>
      </div>
      <el-form class="decision-form" :model="rejectForm" label-position="top">
        <el-form-item label="驳回理由">
          <el-input v-model="rejectForm.approval_opinion" type="textarea" :rows="2" placeholder="请输入驳回理由" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="handleConfirmReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="grantDialogVisible"
      title="单份敏感资料授权"
      width="min(760px, calc(100vw - 28px))"
      :close-on-click-modal="false"
    >
      <el-alert
        :title="`仅授权「${grantTarget?.title || '-'}」，不会获得本团队其他敏感资料权限。`"
        type="warning"
        :closable="false"
        show-icon
      />
      <el-form class="grant-form" label-position="top">
        <el-form-item label="被授权同学" required>
          <el-select
            v-model="grantForm.granted_to"
            filterable
            remote
            clearable
            :remote-method="loadGrantCandidates"
            :loading="grantCandidatesLoading"
            placeholder="姓名、拼音、首字母、邮箱或手机号"
          >
            <el-option
              v-for="member in grantCandidates"
              :key="member.id"
              :label="[member.name, member.email, member.school].filter(Boolean).join(' · ')"
              :value="member.id"
            />
          </el-select>
        </el-form-item>
        <div class="grant-form-grid">
          <el-form-item label="授权能力">
            <el-checkbox v-model="grantForm.can_view">查看明文</el-checkbox>
            <el-checkbox v-model="grantForm.can_download" :disabled="!grantTarget?.has_file">下载附件</el-checkbox>
          </el-form-item>
          <el-form-item label="授权截止" required>
            <el-date-picker
              v-model="grantForm.expires_at"
              type="datetime"
              :disabled-date="disablePastDate"
              placeholder="选择到期时间"
              style="width: 100%"
            />
          </el-form-item>
        </div>
        <el-form-item label="限定用途" required>
          <el-input
            v-model="grantForm.purpose"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
            placeholder="例如：仅用于 2026 年专利申请材料整理，不得另存或转发"
          />
        </el-form-item>
        <el-button type="primary" :loading="grantSaving" @click="saveGrant">保存单份授权</el-button>
      </el-form>

      <el-divider content-position="left">现有授权</el-divider>
      <el-table :data="grants" size="small" max-height="220">
        <el-table-column prop="granted_to_name" label="被授权人" min-width="110" />
        <el-table-column prop="purpose" label="用途" min-width="180" show-overflow-tooltip />
        <el-table-column label="权限" width="105">
          <template #default="{ row }">{{ [row.can_view ? '查看' : '', row.can_download ? '下载' : ''].filter(Boolean).join('+') }}</template>
        </el-table-column>
        <el-table-column label="截止" width="150">
          <template #default="{ row }">{{ formatDateTime(row.expires_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="82">
          <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '有效' : '失效' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="72">
          <template #default="{ row }"><el-button v-if="row.is_active" link type="danger" @click="revokeGrant(row.id)">撤销</el-button></template>
        </el-table-column>
      </el-table>

      <el-divider content-position="left">访问审计</el-divider>
      <el-table :data="grantAccessLogs" size="small" max-height="200">
        <el-table-column prop="accessor_name" label="访问人" width="100" />
        <el-table-column prop="action_display" label="动作" width="92" />
        <el-table-column prop="purpose_snapshot" label="用途快照" min-width="180" show-overflow-tooltip />
        <el-table-column label="结果" width="76">
          <template #default="{ row }"><el-tag :type="row.is_success ? 'success' : 'danger'" size="small">{{ row.is_success ? '成功' : '拒绝' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="时间" width="150">
          <template #default="{ row }">{{ formatDateTime(row.accessed_at) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 限时查看弹窗 -->
    <SensitiveViewDialog
      v-model:visible="viewDialogVisible"
      :request="viewingRequest"
    />
    <SensitiveViewDialog
      v-model:visible="grantViewDialogVisible"
      :sensitive-data="grantViewingData"
      :grant-id="grantViewingData?.active_direct_grant?.id"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
  type UploadFile,
  type UploadUserFile,
} from 'element-plus'
import { CircleCheck, CircleClose, Download, Files, Plus, UploadFilled, View } from '@element-plus/icons-vue'
import {
  createSensitiveData,
  downloadSensitiveAttachment,
  getAccessRequest,
  getSensitiveData,
  getMyAccessRequests,
  getPendingApproveRequests,
  createAccessRequest,
  approveAccessRequest,
  rejectAccessRequest,
  downloadSensitiveAttachmentByGrant,
  getSensitiveDataGrants,
  getSensitiveGrantAccessLogs,
  getSensitiveGrantCandidates,
  revokeSensitiveDataGrant,
  saveSensitiveDataGrant,
} from '@/api/sensitive'
import { getProjects } from '@/api/projects'
import { getFilesByProject, type ManagedFileAsset } from '@/api/files'
import {
  getTeamMembers,
  getTeams,
  type Team,
  type TeamMember,
} from '@/api/teams'
import { downloadBlob, formatDate, formatDateTime } from '@/utils/format'
import { SENSITIVE_DATA_TYPE_MAP, ACCESS_REQUEST_STATUS_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import { useUserStore } from '@/stores/user'
import PageHeader from '@/components/PageHeader.vue'
import SensitiveViewDialog from './SensitiveViewDialog.vue'
import {
  canApproveSensitive,
  normalizeSensitiveWorkspaceTab,
  type SensitiveWorkspaceTab,
} from './sensitiveWorkspace'
import type {
  Project,
  SensitiveData,
  SensitiveDataCreateParams,
  SensitiveDataGrant,
  SensitiveGrantAccessLog,
  SensitiveAccessRequest,
} from '@/types'

const { isMobile } = useDevice()
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const canApprove = computed(() => canApproveSensitive(userStore.role))
const activeTab = ref<SensitiveWorkspaceTab>(
  normalizeSensitiveWorkspaceTab(route.query.tab, userStore.role),
)
const requestedId = computed(() => {
  const value = Number(route.query.request_id)
  return Number.isInteger(value) && value > 0 ? value : undefined
})
const requestedSubjectUserId = computed(() => {
  const value = Number(route.query.subject_user)
  return Number.isInteger(value) && value > 0 ? value : undefined
})
const requestedTeamId = computed(() => {
  const value = Number(route.query.team)
  return Number.isInteger(value) && value > 0 ? value : undefined
})
const myDataLoading = ref(false)
const requestsLoading = ref(false)
const pendingLoading = ref(false)
const submitting = ref(false)
const optionsLoading = ref(false)
const createOptionsLoading = ref(false)
const subjectOptionsLoading = ref(false)
const attachmentOptionsLoading = ref(false)

const myDataList = ref<SensitiveData[]>([])
const myRequestsList = ref<SensitiveAccessRequest[]>([])
const pendingList = ref<SensitiveAccessRequest[]>([])
const projectOptions = ref<Project[]>([])
const sensitiveDataOptions = ref<SensitiveData[]>([])
const teamOptions = ref<Team[]>([])
const subjectOptions = ref<TeamMember[]>([])
const attachmentOptions = ref<ManagedFileAsset[]>([])
const createAttachmentFileList = ref<UploadUserFile[]>([])
const downloadingRequestId = ref<number | null>(null)
const myRequestsTotal = ref(0)
const myRequestsPage = ref(1)
const myRequestsPageSize = ref(userStore.itemsPerPage)
const pendingTotal = ref(0)
const pendingPage = ref(1)
const pendingPageSize = ref(userStore.itemsPerPage)

// 弹窗状态
const applyDialogVisible = ref(false)
const createDialogVisible = ref(false)
const approveDialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const viewDialogVisible = ref(false)
const grantDialogVisible = ref(false)
const grantViewDialogVisible = ref(false)
const applyFormRef = ref<FormInstance>()
const createFormRef = ref<FormInstance>()

const viewingRequest = ref<SensitiveAccessRequest | null>(null)
const grantViewingData = ref<SensitiveData | null>(null)
const grantTarget = ref<SensitiveData | null>(null)
const grants = ref<SensitiveDataGrant[]>([])
const grantAccessLogs = ref<SensitiveGrantAccessLog[]>([])
const grantCandidates = ref<Array<{
  id: number
  name: string
  email: string
  school?: string
  major?: string
}>>([])
const grantCandidatesLoading = ref(false)
const grantSaving = ref(false)
const grantForm = reactive({
  granted_to: undefined as number | undefined,
  can_view: true,
  can_download: false,
  purpose: '',
  expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000) as Date | null,
})

// 申请表单
const applyForm = reactive({
  sensitive_data: undefined as number | undefined,
  usage_scenario: '',
  reason: '',
  project: undefined as number | undefined,
  expected_use_time: '',
  is_download: false,
})

const applyRules: FormRules = {
  sensitive_data: [{ required: true, message: '请选择敏感资料', trigger: 'change' }],
  usage_scenario: [{ required: true, message: '请描述使用场景', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入申请理由', trigger: 'blur' }],
}

const sensitiveTypeOptions = [
  { value: 'id_card', label: '身份证号' },
  { value: 'bank_account', label: '银行账号' },
  { value: 'phone', label: '手机号' },
  { value: 'address', label: '住址' },
  { value: 'signature', label: '签名' },
  { value: 'other', label: '其他' },
]

const createForm = reactive({
  data_type: 'id_card',
  title: '',
  plaintext: '',
  team: undefined as number | undefined,
  subject_user: undefined as number | undefined,
  project: undefined as number | undefined,
  attachment_mode: 'none' as 'none' | 'existing' | 'upload',
  file_attachment: undefined as number | undefined,
  attachment_upload: null as File | null,
})

const createRules: FormRules = {
  data_type: [{ required: true, message: '请选择资料类型', trigger: 'change' }],
  team: [{ required: true, message: '请选择所属小团队', trigger: 'change' }],
  subject_user: [{ required: true, message: '请选择资料本人', trigger: 'change' }],
  title: [{ required: true, message: '请输入资料标题', trigger: 'blur' }],
}

// 批准表单
const approveForm = reactive({
  expire_hours: 1,
  approval_opinion: '',
})

// 驳回表单
const rejectForm = reactive({
  approval_opinion: '',
})

// 当前操作的申请
const currentRequest = ref<SensitiveAccessRequest | null>(null)

const filteredSubjectName = computed(() => {
  const queryName = Array.isArray(route.query.subject_name)
    ? route.query.subject_name[0]
    : route.query.subject_name
  if (queryName) return String(queryName)
  const dataName = myDataList.value.find(
    (item) => item.subject_user === requestedSubjectUserId.value,
  )?.subject_name
  if (dataName) return dataName
  const optionName = subjectOptions.value.find(
    (item) => item.user === requestedSubjectUserId.value,
  )?.user_name
  return optionName || `成员 #${requestedSubjectUserId.value}`
})

function getSensitiveTypeLabel(row: SensitiveAccessRequest): string {
  const type = row.sensitive_data_type || row.data_type || ''
  return row.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[type]?.label || type || '未知类型'
}

function sensitiveOptionLabel(row: SensitiveData): string {
  const title = row.title || row.label || row.display_name || `敏感资料 #${row.id}`
  const subject = row.subject_name || row.owner_name || '未标注本人'
  const team = row.team_name || '未标注团队'
  return `${title} · ${subject} · ${team}`
}

function getRequestExpiry(row: SensitiveAccessRequest): string | undefined {
  return row.access_expires_at || row.expires_at
}

function isExpired(row: SensitiveAccessRequest): boolean {
  const expiresAt = getRequestExpiry(row)
  if (!expiresAt) return false
  return new Date(expiresAt).getTime() <= now.value
}

// 实时倒计时：每秒更新当前时间
const now = ref(Date.now())
let countdownTimer: ReturnType<typeof setInterval> | null = null

function getRequestStatus(row: SensitiveAccessRequest): { label: string; type: string } {
  if (row.status === 'approved' && isExpired(row)) {
    return { label: '已过期', type: 'info' }
  }
  const status = row.status || ''
  const mapped = ACCESS_REQUEST_STATUS_MAP[status]
  return {
    label: mapped?.label || status || '未知',
    type: status === 'pending' ? 'warning' : (mapped?.tagType || 'info'),
  }
}

// 计算剩余时间（格式：Xm Ys）
function getRemainingTime(expiresAt: string | undefined): string {
  if (!expiresAt) return '-'
  const expiresAtMs = new Date(expiresAt).getTime()
  if (Number.isNaN(expiresAtMs)) return '-'
  const diff = expiresAtMs - now.value
  if (diff <= 0) return '已过期'
  const m = Math.floor(diff / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  if (m > 0) return `${m}分${s}秒`
  return `${s}秒`
}

// Tab 切换
function handleTabChange(tab: string | number): void {
  const tabName = normalizeSensitiveWorkspaceTab(String(tab), userStore.role)
  const query: LocationQueryRaw = { ...route.query, tab: tabName }
  if (tabName !== 'pending') delete query.request_id
  void router.replace({ query })
}

// 加载我的资料
async function loadMyData(): Promise<void> {
  myDataLoading.value = true
  try {
    const res = await getSensitiveData({ page: 1, page_size: 100 })
    const rows = Array.isArray(res) ? res : (res.results || [])
    myDataList.value = requestedSubjectUserId.value
      ? rows.filter((item) => item.subject_user === requestedSubjectUserId.value)
      : rows
  } catch {
    // 错误已由拦截器处理
  } finally {
    myDataLoading.value = false
  }
}

// 加载我的申请
async function loadMyRequests(): Promise<void> {
  requestsLoading.value = true
  try {
    const res = await getMyAccessRequests({
      page: myRequestsPage.value,
      page_size: myRequestsPageSize.value,
    })
    myRequestsList.value = Array.isArray(res) ? res : (res.results || [])
    myRequestsTotal.value = Array.isArray(res) ? res.length : res.count
    const maxPage = Math.max(1, Math.ceil(myRequestsTotal.value / myRequestsPageSize.value))
    if (myRequestsPage.value > maxPage) {
      myRequestsPage.value = maxPage
      return await loadMyRequests()
    }
  } catch {
    // 错误已由拦截器处理
  } finally {
    requestsLoading.value = false
  }
}

// 加载待审批
async function loadPending(): Promise<void> {
  if (!canApprove.value) return
  pendingLoading.value = true
  try {
    const res = await getPendingApproveRequests({
      page: pendingPage.value,
      page_size: pendingPageSize.value,
    })
    pendingList.value = Array.isArray(res) ? res : (res.results || [])
    pendingTotal.value = Array.isArray(res) ? res.length : res.count
    const maxPage = Math.max(1, Math.ceil(pendingTotal.value / pendingPageSize.value))
    if (pendingPage.value > maxPage) {
      pendingPage.value = maxPage
      return await loadPending()
    }
  } catch {
    // 错误已由拦截器处理
  } finally {
    pendingLoading.value = false
  }
}

function handleMyRequestsPageSizeChange(): void {
  myRequestsPage.value = 1
  void loadMyRequests()
}

function handlePendingPageSizeChange(): void {
  pendingPage.value = 1
  void loadPending()
}

async function loadWorkspaceTab(tab: SensitiveWorkspaceTab): Promise<void> {
  if (tab === 'my-data') await loadMyData()
  if (tab === 'requests') await loadMyRequests()
  if (tab === 'pending') await loadPending()
}

function clearRequestedId(): void {
  const query = { ...route.query }
  delete query.request_id
  void router.replace({ query })
}

async function openRequestedApproval(): Promise<void> {
  const id = requestedId.value
  if (!id || activeTab.value !== 'pending' || !canApprove.value) return
  try {
    const request = pendingList.value.find((item) => item.id === id) || await getAccessRequest(id)
    if (request.applicant === userStore.userInfo?.id) {
      ElMessage.warning('不能审批自己提交的访问申请')
      return
    }
    if (request.status !== 'pending') {
      ElMessage.info('该访问申请已处理')
      return
    }
    handleApprove(request)
  } finally {
    clearRequestedId()
  }
}

// 加载选项数据
async function loadOptions(): Promise<void> {
  optionsLoading.value = true
  try {
    const [projectsRes, sensitiveRes] = await Promise.all([
      getProjects({ page: 1, page_size: 100 }),
      getSensitiveData({ page: 1, page_size: 100 }),
    ])
    projectOptions.value = (projectsRes as any).results || []
    const rows = Array.isArray(sensitiveRes)
      ? sensitiveRes
      : ((sensitiveRes as any).results || [])
    sensitiveDataOptions.value = requestedSubjectUserId.value
      ? rows.filter((item: SensitiveData) => item.subject_user === requestedSubjectUserId.value)
      : rows
    if (requestedSubjectUserId.value && sensitiveDataOptions.value.length) {
      applyForm.sensitive_data = sensitiveDataOptions.value[0].id
    }
  } catch {
    // 忽略
  } finally {
    optionsLoading.value = false
  }
}

// 申请查看
function handleApply(): void {
  Object.assign(applyForm, {
    sensitive_data: undefined,
    usage_scenario: '',
    reason: '',
    project: undefined,
    expected_use_time: '',
    is_download: false,
  })
  loadOptions()
  applyDialogVisible.value = true
}

function clearSubjectFilter(): void {
  const query = { ...route.query }
  delete query.subject_user
  delete query.subject_name
  delete query.team
  void router.replace({ query })
}

async function loadSubjectOptions(teamId?: number): Promise<void> {
  subjectOptions.value = []
  if (!teamId) return
  subjectOptionsLoading.value = true
  try {
    const members = await getTeamMembers(teamId)
    subjectOptions.value = members.filter((item) => item.status === 'active')
    const requestedSubject = requestedSubjectUserId.value
    const fallbackUser = userStore.userInfo?.id
    if (
      requestedSubject
      && subjectOptions.value.some((item) => item.user === requestedSubject)
    ) {
      createForm.subject_user = requestedSubject
    } else if (
      fallbackUser
      && subjectOptions.value.some((item) => item.user === fallbackUser)
    ) {
      createForm.subject_user = fallbackUser
    }
  } catch {
    // 选项加载失败时保留后端权限校验，不缓存其他团队的成员信息。
  } finally {
    subjectOptionsLoading.value = false
  }
}

async function loadCreateOptions(): Promise<void> {
  createOptionsLoading.value = true
  try {
    const [teamsRes, projectsRes] = await Promise.all([
      getTeams(),
      getProjects({ page: 1, page_size: 100 }),
    ])
    teamOptions.value = (teamsRes as any).results || teamsRes || []
    projectOptions.value = (projectsRes as any).results || []
    const queryTeam = requestedTeamId.value
    createForm.team = (
      queryTeam && teamOptions.value.some((item) => item.id === queryTeam)
    )
      ? queryTeam
      : (teamOptions.value.length === 1 ? teamOptions.value[0].id : undefined)
    await loadSubjectOptions(createForm.team)
  } catch {
    // 错误已由统一拦截器处理。
  } finally {
    createOptionsLoading.value = false
  }
}

async function handleCreateTeamChange(teamId?: number): Promise<void> {
  createForm.subject_user = undefined
  await loadSubjectOptions(teamId)
}

async function handleSensitiveProjectChange(projectId?: number): Promise<void> {
  createForm.file_attachment = undefined
  attachmentOptions.value = []
  if (!projectId) return
  attachmentOptionsLoading.value = true
  try {
    attachmentOptions.value = await getFilesByProject(projectId) as ManagedFileAsset[]
  } finally {
    attachmentOptionsLoading.value = false
  }
}

function handleAttachmentModeChange(): void {
  createForm.file_attachment = undefined
  createForm.attachment_upload = null
  createAttachmentFileList.value = []
  if (createForm.attachment_mode === 'existing') {
    void handleSensitiveProjectChange(createForm.project)
  }
}

function handleCreateAttachmentChange(file: UploadFile): void {
  createForm.attachment_upload = file.raw || null
  createAttachmentFileList.value = file.raw ? [file] : []
}

function handleCreateAttachmentRemove(): void {
  createForm.attachment_upload = null
  createAttachmentFileList.value = []
}

function handleCreate(): void {
  Object.assign(createForm, {
    data_type: 'id_card',
    title: '',
    plaintext: '',
    team: undefined,
    subject_user: undefined,
    project: undefined,
    attachment_mode: 'none',
    file_attachment: undefined,
    attachment_upload: null,
  })
  attachmentOptions.value = []
  createAttachmentFileList.value = []
  createDialogVisible.value = true
  void loadCreateOptions()
}

async function handleSubmitCreate(): Promise<void> {
  if (!createFormRef.value) return
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid || !createForm.team || !createForm.subject_user) return
  const hasAttachment = (
    (createForm.attachment_mode === 'existing' && createForm.file_attachment)
    || (createForm.attachment_mode === 'upload' && createForm.attachment_upload)
  )
  if (!createForm.plaintext.trim() && !hasAttachment) {
    ElMessage.warning('资料明文与附件至少填写一项')
    return
  }
  submitting.value = true
  try {
    const payload: SensitiveDataCreateParams = {
      data_type: createForm.data_type,
      title: createForm.title.trim(),
      display_name: createForm.title.trim(),
      plaintext: createForm.plaintext,
      team: createForm.team,
      subject_user: createForm.subject_user,
      project: createForm.project || null,
      file_attachment: createForm.attachment_mode === 'existing'
        ? createForm.file_attachment || null
        : null,
      attachment_upload: createForm.attachment_mode === 'upload'
        ? createForm.attachment_upload
        : null,
    }
    await createSensitiveData(payload)
    createForm.plaintext = ''
    createForm.attachment_upload = null
    createAttachmentFileList.value = []
    createDialogVisible.value = false
    ElMessage.success('敏感资料已加密保存，目录中仅展示脱敏值')
    await loadMyData()
  } catch {
    // 错误已由统一拦截器处理。
  } finally {
    submitting.value = false
  }
}

function handleCloseCreate(): void {
  createForm.plaintext = ''
  createForm.attachment_upload = null
  createAttachmentFileList.value = []
  createFormRef.value?.resetFields()
}

// 提交申请
async function handleSubmitApply(): Promise<void> {
  if (!applyFormRef.value) return
  await applyFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data: any = { ...applyForm }
      if (!data.project) delete data.project
      if (!data.expected_use_time) delete data.expected_use_time
      await createAccessRequest(data)
      ElMessage.success('申请已提交')
      applyDialogVisible.value = false
      loadMyRequests()
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

function handleCloseApply(): void {
  applyFormRef.value?.resetFields()
}

// 查看资料
function handleViewData(row: SensitiveAccessRequest): void {
  viewingRequest.value = row
  viewDialogVisible.value = true
}

function handleGrantView(row: SensitiveData): void {
  if (!row.active_direct_grant?.can_view) return
  grantViewingData.value = row
  grantViewDialogVisible.value = true
}

async function handleGrantDownload(row: SensitiveData): Promise<void> {
  const grant = row.active_direct_grant
  if (!grant?.can_download) return
  const blob = await downloadSensitiveAttachmentByGrant(row.id, grant.id)
  downloadBlob(blob, row.file_attachment_name || `敏感资料附件_${row.id}`)
  ElMessage.success('附件已依据单份授权通过受保护通道下载')
}

function disablePastDate(date: Date): boolean {
  return date.getTime() < Date.now() - 24 * 60 * 60 * 1000
}

async function loadGrantCandidates(search = ''): Promise<void> {
  if (!grantTarget.value) return
  grantCandidatesLoading.value = true
  try {
    grantCandidates.value = await getSensitiveGrantCandidates(grantTarget.value.id, search)
  } finally {
    grantCandidatesLoading.value = false
  }
}

async function refreshGrantWorkspace(): Promise<void> {
  if (!grantTarget.value) return
  const [grantRows, accessRows] = await Promise.all([
    getSensitiveDataGrants(grantTarget.value.id),
    getSensitiveGrantAccessLogs(grantTarget.value.id),
  ])
  grants.value = grantRows
  grantAccessLogs.value = accessRows
}

async function openGrantDialog(row: SensitiveData): Promise<void> {
  grantTarget.value = row
  Object.assign(grantForm, {
    granted_to: undefined,
    can_view: true,
    can_download: false,
    purpose: '',
    expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000),
  })
  grantCandidates.value = []
  grants.value = []
  grantAccessLogs.value = []
  grantDialogVisible.value = true
  await Promise.all([loadGrantCandidates(), refreshGrantWorkspace()])
}

async function saveGrant(): Promise<void> {
  if (!grantTarget.value || !grantForm.granted_to) {
    ElMessage.warning('请选择被授权同学')
    return
  }
  if (!grantForm.can_view && !grantForm.can_download) {
    ElMessage.warning('查看和下载权限至少选择一项')
    return
  }
  if (!grantForm.purpose.trim() || !grantForm.expires_at) {
    ElMessage.warning('请填写限定用途并设置到期时间')
    return
  }
  grantSaving.value = true
  try {
    await saveSensitiveDataGrant(grantTarget.value.id, {
      granted_to: grantForm.granted_to,
      can_view: grantForm.can_view,
      can_download: grantForm.can_download,
      purpose: grantForm.purpose.trim(),
      expires_at: grantForm.expires_at.toISOString(),
    })
    ElMessage.success('单份资料授权已保存')
    await Promise.all([refreshGrantWorkspace(), loadMyData()])
  } finally {
    grantSaving.value = false
  }
}

async function revokeGrant(grantId: number): Promise<void> {
  if (!grantTarget.value) return
  await ElMessageBox.confirm('确定立即撤销这份资料授权吗？', '撤销授权', { type: 'warning' })
  await revokeSensitiveDataGrant(grantTarget.value.id, grantId)
  ElMessage.success('授权已撤销')
  await Promise.all([refreshGrantWorkspace(), loadMyData()])
}

function canDownloadAttachment(row: SensitiveAccessRequest): boolean {
  if (typeof row.can_download_attachment === 'boolean') {
    return row.can_download_attachment
  }
  return Boolean(
    row.status === 'approved' &&
    !isExpired(row) &&
    row.is_download &&
    row.has_attachment
  )
}

async function handleDownloadAttachment(row: SensitiveAccessRequest): Promise<void> {
  downloadingRequestId.value = row.id
  try {
    const blob = await downloadSensitiveAttachment(row.id)
    downloadBlob(blob, row.attachment_name || `敏感资料附件_${row.id}`)
    ElMessage.success('附件已通过受保护通道下载')
  } catch {
    // 错误已由统一拦截器处理
  } finally {
    downloadingRequestId.value = null
  }
}

// 批准
function handleApprove(row: SensitiveAccessRequest): void {
  currentRequest.value = row
  approveForm.expire_hours = 1
  approveForm.approval_opinion = ''
  approveDialogVisible.value = true
}

// 确认批准
async function handleConfirmApprove(): Promise<void> {
  if (!currentRequest.value) return
  submitting.value = true
  try {
    await approveAccessRequest(currentRequest.value.id, {
      action: 'approve',
      approval_opinion: approveForm.approval_opinion,
      expire_hours: approveForm.expire_hours,
    })
    ElMessage.success('已批准')
    approveDialogVisible.value = false
    loadPending()
  } catch {
    // 错误已由拦截器处理
  } finally {
    submitting.value = false
  }
}

// 驳回
function handleReject(row: SensitiveAccessRequest): void {
  currentRequest.value = row
  rejectForm.approval_opinion = ''
  rejectDialogVisible.value = true
}

// 确认驳回
async function handleConfirmReject(): Promise<void> {
  if (!currentRequest.value) return
  if (!rejectForm.approval_opinion.trim()) {
    ElMessage.warning('请输入驳回理由')
    return
  }
  submitting.value = true
  try {
    await rejectAccessRequest(currentRequest.value.id, {
      action: 'reject',
      approval_opinion: rejectForm.approval_opinion,
    })
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    loadPending()
  } catch {
    // 错误已由拦截器处理
  } finally {
    submitting.value = false
  }
}

watch(
  [() => route.query.tab, () => userStore.role],
  () => {
    const tab = normalizeSensitiveWorkspaceTab(route.query.tab, userStore.role)
    activeTab.value = tab
    if (userStore.role && route.query.tab !== tab) {
      void router.replace({ query: { ...route.query, tab } })
    }
    void loadWorkspaceTab(tab)
  },
  { immediate: true },
)

watch(
  [requestedId, canApprove],
  () => { void openRequestedApproval() },
  { immediate: true },
)

watch(
  requestedSubjectUserId,
  () => {
    if (activeTab.value === 'my-data') void loadMyData()
  },
)

onMounted(() => {
  // 启动倒计时定时器（每秒更新）
  countdownTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style lang="scss" scoped>
.attachment-control {
  width: 100%;
  margin-top: 10px;
}

.grant-form {
  margin-top: 16px;
}

.grant-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media screen and (max-width: 640px) {
  .grant-form-grid {
    grid-template-columns: 1fr;
  }
}
.sensitive-center-page {
  padding-bottom: 32px;
}

.page-meta {
  display: inline-block;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.sensitive-workspace {
  min-width: 0;
  padding: 0 18px 18px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

:deep(.sensitive-workspace > .el-tabs__header) {
  margin: 0 -18px 18px;
  padding: 0 18px;
  background: var(--color-surface-subtle);
}

:deep(.sensitive-workspace > .el-tabs__header .el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--color-border-light);
}

:deep(.sensitive-workspace > .el-tabs__content) {
  overflow: visible;
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tab-label .el-icon {
  font-size: 15px;
}

.pane-heading {
  display: flex;
  min-height: 42px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.pane-heading > div {
  min-width: 0;
}

.pane-heading .panel-actions {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 8px;
}

.subject-filter-alert {
  margin-bottom: 14px;
}

.subject-filter-alert :deep(.el-alert__content) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  width: 100%;
  gap: 12px;
}

.sensitive-create-alert {
  margin-bottom: 18px;
}

.pane-heading h2 {
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
}

.pane-heading span {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.pending-heading h2 {
  color: var(--color-warning);
}

.record-name,
.data-cell strong {
  color: var(--color-text);
  font-weight: 600;
}

.masked-value,
.mobile-masked-value code {
  color: var(--color-text-regular);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
}

.table-shell {
  min-width: 0;
  overflow-x: auto;
}

.table-shell :deep(.el-table) {
  min-width: 950px;
}

.pagination-wrapper {
  display: flex;
  padding-top: 16px;
  overflow-x: auto;
  justify-content: flex-end;
}

.data-cell {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.data-cell strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-cell span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.remaining-time {
  color: var(--color-warning);
  font-weight: 600;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.text-expired {
  color: var(--color-text-muted);
  font-size: 13px;
}

.mobile-record-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-record-card {
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.mobile-record-card.has-download-risk {
  border-color: rgba(182, 66, 66, 0.38);
}

.mobile-card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mobile-card-heading > div {
  min-width: 0;
}

.mobile-card-heading h3 {
  overflow: hidden;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-card-heading span {
  display: -webkit-box;
  margin-top: 2px;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.mobile-masked-value {
  display: flex;
  margin-top: 12px;
  padding: 10px 12px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.mobile-masked-value span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.mobile-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-meta-grid .meta-wide {
  grid-column: 1 / -1;
}

.mobile-meta-grid dt {
  margin-bottom: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.mobile-meta-grid dd {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-regular);
  font-size: 13px;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.danger-text {
  color: var(--color-danger) !important;
  font-weight: 600;
}

.mobile-access-action {
  display: flex;
  margin: 12px -14px -14px;
  padding: 10px 14px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--color-primary-soft);
  border-top: 1px solid rgba(23, 107, 115, 0.18);
}

.mobile-access-action span {
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.mobile-access-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-access-buttons :deep(.el-button + .el-button) {
  margin-left: 0;
}

.mobile-decision-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-decision-actions :deep(.el-button) {
  width: 100%;
  margin-left: 0;
}

.apply-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 18px;
}

.apply-form-grid .form-wide {
  grid-column: 1 / -1;
}

.apply-form :deep(.el-form-item) {
  min-width: 0;
  margin-bottom: 0;
}

.apply-form :deep(.el-form-item__label),
.decision-form :deep(.el-form-item__label) {
  height: auto;
  margin-bottom: 7px;
  color: var(--color-text-regular);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
}

.apply-form :deep(.el-select),
.apply-form :deep(.el-date-editor),
.decision-form :deep(.el-input-number) {
  width: 100%;
}

.download-option {
  padding: 12px 14px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.download-option.is-selected {
  background: var(--danger-light);
  border-color: rgba(182, 66, 66, 0.32);
}

.download-control {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.download-control > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.download-control strong {
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.download-control span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.dialog-request-summary {
  display: flex;
  margin-bottom: 18px;
  padding: 12px 14px;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.dialog-request-summary strong {
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.dialog-request-summary span {
  min-width: 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.decision-form :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

@media screen and (max-width: 768px) {
  .sensitive-center-page {
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }

  .sensitive-workspace {
    padding: 0 14px 14px;
  }

  :deep(.sensitive-workspace > .el-tabs__header) {
    margin-right: -14px;
    margin-left: -14px;
    padding: 0 14px;
  }

  :deep(.sensitive-workspace > .el-tabs__header .el-tabs__nav-wrap) {
    overflow-x: auto;
  }

  .pane-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .pane-heading .panel-actions {
    width: 100%;
  }

  .pane-heading .panel-actions .el-button {
    flex: 1;
    margin-left: 0;
  }

  .subject-filter-alert :deep(.el-alert__content) {
    align-items: flex-start;
    flex-direction: column;
  }

  .apply-form-grid {
    grid-template-columns: 1fr;
    gap: 15px;
  }

  .apply-form-grid .form-wide {
    grid-column: 1;
  }
}

@media screen and (max-width: 400px) {
  .tab-label {
    gap: 4px;
    font-size: 12px;
  }

  .pane-heading {
    align-items: flex-start;
  }
}
</style>
