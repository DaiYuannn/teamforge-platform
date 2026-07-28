<template>
  <div class="page-container platform-page">
    <PageHeader title="平台能力中心" subtitle="统一管理角色授权、审批流程、自定义表单与外部系统连接">
      <template #actions>
        <el-tooltip content="刷新当前工作区" placement="bottom">
          <el-button :icon="Refresh" circle aria-label="刷新当前工作区" :loading="refreshing" @click="refreshActiveTab" />
        </el-tooltip>
      </template>
    </PageHeader>

    <div class="metric-strip" aria-label="平台能力概览">
      <div class="metric-item"><span>自定义角色</span><strong>{{ roles.length }}</strong><small>{{ assignments.length }} 条分配</small></div>
      <div class="metric-item"><span>审批流程</span><strong>{{ activeFlowCount }}</strong><small>{{ pendingRequestCount }} 条待处理</small></div>
      <div class="metric-item"><span>在线表单</span><strong>{{ activeFormCount }}</strong><small>{{ submissions.length }} 条提交</small></div>
      <div class="metric-item"><span>系统连接</span><strong>{{ activeIntegrationCount }}</strong><small>外部平台与 Git</small></div>
    </div>

    <el-tabs v-model="activeTab" class="workspace-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="角色与授权" name="roles">
        <el-alert
          v-if="!isAdmin"
          title="当前为只读模式，只有系统管理员可以维护角色和分配关系。"
          type="info"
          :closable="false"
          show-icon
          class="permission-alert"
        />

        <section class="team-context" aria-labelledby="team-context-title">
          <div>
            <span class="section-kicker">只读关联</span>
            <h2 id="team-context-title">团队成员范围</h2>
            <p>团队归属沿用团队管理中的现有数据，此处只用于核对授权对象。</p>
          </div>
          <el-select
            v-model="selectedTeamId"
            aria-label="选择团队查看成员范围"
            placeholder="选择团队"
            clearable
            filterable
            @change="loadSelectedTeamMembers"
          >
            <el-option v-for="team in teams" :key="team.id" :label="`${team.name} · ${team.member_count} 人`" :value="team.id" />
          </el-select>
          <div class="team-members" :aria-busy="teamLoading">
            <el-tag v-for="member in selectedTeamMembers.slice(0, 12)" :key="member.id" effect="plain" size="small">
              {{ member.user_name }} · {{ member.role_display || member.role }}
            </el-tag>
            <span v-if="selectedTeamMembers.length > 12" class="muted">另有 {{ selectedTeamMembers.length - 12 }} 人</span>
            <span v-if="selectedTeamId && !teamLoading && !selectedTeamMembers.length" class="muted">该团队暂无有效成员</span>
            <span v-if="!selectedTeamId" class="muted">选择团队后查看成员范围</span>
          </div>
        </section>

        <section class="collection-section">
          <div class="section-toolbar">
            <div><h2>自定义角色</h2><p>以权限点组合出可复用的业务角色。</p></div>
            <el-button v-if="isAdmin" type="primary" :icon="Plus" @click="openRoleDialog()">新建角色</el-button>
          </div>
          <el-alert v-if="errors.roles" :title="errors.roles" type="error" show-icon :closable="false">
            <template #default><el-button link type="primary" @click="loadRoles">重试</el-button></template>
          </el-alert>
          <div v-loading="loading.roles" class="record-grid role-grid">
            <article v-for="role in roles" :key="role.id" class="record-card">
              <div class="record-heading">
                <div><h3>{{ role.name }}</h3><p>{{ role.description || '暂无角色说明' }}</p></div>
                <el-tag :type="role.is_system ? 'info' : 'success'" size="small">{{ role.is_system ? '系统角色' : '自定义' }}</el-tag>
              </div>
              <div class="tag-list">
                <el-tag v-for="permission in role.permissions.slice(0, 5)" :key="permission" size="small" effect="plain">{{ permissionLabel(permission) }}</el-tag>
                <span v-if="role.permissions.length > 5" class="muted">+{{ role.permissions.length - 5 }}</span>
                <span v-if="!role.permissions.length" class="muted">未配置权限点</span>
              </div>
              <div v-if="isAdmin" class="record-actions">
                <el-button text :icon="Edit" :disabled="role.is_system" @click="openRoleDialog(role)">编辑</el-button>
                <el-button text type="danger" :icon="Delete" :disabled="role.is_system" @click="removeRole(role)">删除</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-if="!loading.roles && !errors.roles && !roles.length" text="暂无自定义角色" description="创建角色后即可为成员授予业务权限。" :compact="true" />
        </section>

        <section class="collection-section">
          <div class="section-toolbar">
            <div><h2>角色分配</h2><p>支持全局授权或限定到单个项目。</p></div>
            <el-button v-if="isAdmin" type="primary" plain :icon="Plus" :disabled="!roles.length" @click="openAssignmentDialog()">分配角色</el-button>
          </div>
          <el-alert v-if="errors.assignments" :title="errors.assignments" type="error" show-icon :closable="false" />
          <div v-loading="loading.assignments" class="record-grid assignment-grid">
            <article v-for="assignment in assignments" :key="assignment.id" class="record-card compact-card">
              <div class="assignment-line">
                <span class="initial">{{ (assignment.user_name || '?').slice(0, 1) }}</span>
                <div><h3>{{ assignment.user_name || `用户 #${assignment.user}` }}</h3><p>{{ assignment.role_name }}</p></div>
              </div>
              <el-tag size="small" :type="assignment.project ? 'warning' : 'success'" effect="plain">
                {{ assignment.project_name || '全局范围' }}
              </el-tag>
              <div v-if="isAdmin" class="record-actions">
                <el-button text :icon="Edit" @click="openAssignmentDialog(assignment)">调整</el-button>
                <el-button text type="danger" :icon="Delete" @click="removeAssignment(assignment)">撤销</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-if="!loading.assignments && !errors.assignments && !assignments.length" text="暂无角色分配" :compact="true" />
        </section>
      </el-tab-pane>

      <el-tab-pane label="审批流程" name="approvals">
        <el-alert
          v-if="!isManager"
          title="你可以提交申请并处理明确指派给你的节点；流程设计仅对老师和系统管理员开放。"
          type="info"
          :closable="false"
          show-icon
          class="permission-alert"
        />
        <section class="collection-section">
          <div class="section-toolbar">
            <div><h2>流程设计</h2><p>按顺序设置审批节点和节点角色。</p></div>
            <el-button v-if="isManager" type="primary" :icon="Plus" @click="openFlowDialog()">新建流程</el-button>
          </div>
          <el-alert v-if="errors.flows" :title="errors.flows" type="error" show-icon :closable="false" />
          <div v-loading="loading.flows" class="record-grid flow-grid">
            <article v-for="flow in flows" :key="flow.id" class="record-card">
              <div class="record-heading">
                <div><h3>{{ flow.name }}</h3><p>{{ flowTypeLabel(flow.flow_type) }}</p></div>
                <el-tag :type="flow.is_active ? 'success' : 'info'" size="small">{{ flow.is_active ? '启用' : '停用' }}</el-tag>
              </div>
              <ol class="step-preview">
                <li v-for="(step, index) in flow.steps" :key="`${flow.id}-${index}`">
                  <span>{{ index + 1 }}</span><strong>{{ step.name || `第 ${index + 1} 级审批` }}</strong><small>{{ reviewerLabel(step) }}</small>
                </li>
              </ol>
              <div v-if="isManager" class="record-actions">
                <el-button text :icon="Edit" @click="openFlowDialog(flow)">编辑</el-button>
                <el-button text type="danger" :icon="Delete" @click="removeFlow(flow)">删除</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-if="!loading.flows && !errors.flows && !flows.length" text="暂无审批流程" description="先创建启用的流程，成员才能发起申请。" :compact="true" />
        </section>

        <section class="collection-section">
          <div class="section-toolbar">
            <div><h2>审批申请</h2><p>查看本人申请及当前可处理的审批事项。</p></div>
            <el-button type="primary" plain :icon="Plus" :disabled="!activeFlows.length" @click="openRequestDialog">发起申请</el-button>
          </div>
          <el-alert v-if="errors.requests" :title="errors.requests" type="error" show-icon :closable="false" />
          <div v-loading="loading.requests" class="record-list">
            <article v-for="request in approvalRequests" :key="request.id" class="request-row">
              <div class="request-main">
                <div class="record-heading">
                  <div><h3>{{ request.title }}</h3><p>{{ request.flow_name }} · {{ request.applicant_name }}</p></div>
                  <el-tag :type="approvalStatusTone(request.status)" size="small">{{ request.status_display || approvalStatusLabel(request.status) }}</el-tag>
                </div>
                <p class="request-content">{{ request.content || '未填写申请说明' }}</p>
              </div>
              <div class="request-meta"><span>当前节点 {{ request.current_step + 1 }}</span><time>{{ formatDateTime(request.created_at) }}</time></div>
              <div class="row-actions">
                <template v-if="canReview(request)">
                  <el-button size="small" type="success" plain @click="reviewRequest(request, 'approve')">通过</el-button>
                  <el-button size="small" type="danger" plain @click="reviewRequest(request, 'reject')">驳回</el-button>
                </template>
                <el-button v-if="canCancel(request)" size="small" plain @click="cancelRequest(request)">取消申请</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-if="!loading.requests && !errors.requests && !approvalRequests.length" text="暂无审批申请" :compact="true" />
        </section>
      </el-tab-pane>

      <el-tab-pane label="表单与提交" name="forms">
        <el-alert
          v-if="!isManager"
          title="你可以填写启用中的表单并查看自己的提交记录；表单设计仅对老师和系统管理员开放。"
          type="info"
          :closable="false"
          show-icon
          class="permission-alert"
        />
        <section class="collection-section">
          <div class="section-toolbar">
            <div><h2>自定义表单</h2><p>用结构化字段收集团队信息。</p></div>
            <el-button v-if="isManager" type="primary" :icon="Plus" @click="openFormDialog()">新建表单</el-button>
          </div>
          <el-alert v-if="errors.forms" :title="errors.forms" type="error" show-icon :closable="false" />
          <div v-loading="loading.forms" class="record-grid form-grid">
            <article v-for="formItem in forms" :key="formItem.id" class="record-card">
              <div class="record-heading">
                <div><h3>{{ formItem.name }}</h3><p>{{ formItem.description || '暂无表单说明' }}</p></div>
                <el-tag :type="formItem.is_active ? 'success' : 'info'" size="small">{{ formItem.is_active ? '收集中' : '已停用' }}</el-tag>
              </div>
              <div class="field-summary">
                <span>{{ formItem.fields.length }} 个字段</span>
                <span>{{ requiredFieldCount(formItem) }} 个必填</span>
                <span>{{ formItem.created_by_name || '系统' }}创建</span>
              </div>
              <div class="record-actions">
                <el-button v-if="formItem.is_active" text type="primary" :icon="Document" @click="openSubmissionDialog(formItem)">填写</el-button>
                <el-button v-if="isManager" text :icon="Edit" @click="openFormDialog(formItem)">编辑</el-button>
                <el-button v-if="isManager" text type="danger" :icon="Delete" @click="removeForm(formItem)">删除</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-if="!loading.forms && !errors.forms && !forms.length" text="暂无自定义表单" :compact="true" />
        </section>

        <section class="collection-section">
          <div class="section-toolbar"><div><h2>提交记录</h2><p>{{ isManager ? '可查看全部成员提交。' : '仅展示你自己的提交。' }}</p></div></div>
          <el-alert v-if="errors.submissions" :title="errors.submissions" type="error" show-icon :closable="false" />
          <div v-loading="loading.submissions" class="record-list">
            <article v-for="submission in submissions" :key="submission.id" class="request-row submission-row">
              <div class="request-main"><h3>{{ submission.form_name }}</h3><p class="request-content">{{ submissionSummary(submission) }}</p></div>
              <div class="request-meta"><span>{{ submission.user_name || '匿名用户' }}</span><time>{{ formatDateTime(submission.created_at) }}</time></div>
              <div class="row-actions"><el-button v-if="canDeleteSubmission(submission)" text type="danger" :icon="Delete" @click="removeSubmission(submission)">删除</el-button></div>
            </article>
          </div>
          <EmptyState v-if="!loading.submissions && !errors.submissions && !submissions.length" text="暂无提交记录" :compact="true" />
        </section>
      </el-tab-pane>

      <el-tab-pane label="外部连接" name="integrations">
        <el-alert
          v-if="!isAdmin"
          title="连接配置可能包含敏感凭据，只有系统管理员可以新建、编辑或删除；当前为脱敏只读视图。"
          type="info"
          :closable="false"
          show-icon
          class="permission-alert"
        />
        <div class="integration-toolbar">
          <el-segmented v-model="integrationMode" :options="integrationModes" />
          <el-button v-if="isAdmin" type="primary" :icon="Plus" @click="integrationMode === 'platforms' ? openPlatformDialog() : openRepositoryDialog()">
            {{ integrationMode === 'platforms' ? '新增平台' : '关联仓库' }}
          </el-button>
        </div>

        <section v-if="integrationMode === 'platforms'" class="collection-section">
          <el-alert v-if="errors.platforms" :title="errors.platforms" type="error" show-icon :closable="false" />
          <div v-loading="loading.platforms" class="record-grid integration-grid">
            <article v-for="platform in externalPlatforms" :key="platform.id" class="record-card integration-card">
              <div class="integration-icon"><el-icon><Connection /></el-icon></div>
              <div class="record-heading">
                <div><h3>{{ platform.name }}</h3><p>{{ platformTypeLabel(platform.platform_type) }}</p></div>
                <el-tag :type="connectionTone(platform.connection_status)" size="small">{{ platform.is_active ? connectionLabel(platform.connection_status) : '已停用' }}</el-tag>
              </div>
              <p class="mono-line">{{ platform.api_url || '未配置 API 地址' }}</p>
              <p v-if="platform.last_checked_at" class="connection-detail">最近检测 {{ formatDateTime(platform.last_checked_at) }}</p>
              <p v-if="platform.last_error" class="connection-error">{{ platform.last_error }}</p>
              <div v-if="isAdmin" class="record-actions">
                <el-button text :icon="Connection" :loading="connectionAction === `platform-test-${platform.id}`" @click="runPlatformAction(platform, false)">检测</el-button>
                <el-button text :icon="Refresh" :loading="connectionAction === `platform-sync-${platform.id}`" @click="runPlatformAction(platform, true)">同步</el-button>
                <el-button text :icon="Edit" @click="openPlatformDialog(platform)">编辑</el-button>
                <el-button text type="danger" :icon="Delete" @click="removePlatform(platform)">删除</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-if="!loading.platforms && !errors.platforms && !externalPlatforms.length" text="暂无外部平台连接" :compact="true" />
        </section>

        <section v-else class="collection-section">
          <el-alert v-if="errors.repositories" :title="errors.repositories" type="error" show-icon :closable="false" />
          <div v-loading="loading.repositories" class="record-grid integration-grid">
            <article v-for="repository in gitRepositories" :key="repository.id" class="record-card integration-card">
              <div class="integration-icon git-icon"><el-icon><FolderOpened /></el-icon></div>
              <div class="record-heading">
                <div><h3>{{ repository.project_name || `项目 #${repository.project}` }}</h3><p>{{ repository.branch }}</p></div>
                <el-tag :type="connectionTone(repository.connection_status)" size="small">{{ repository.is_active ? connectionLabel(repository.connection_status) : '已停用' }}</el-tag>
              </div>
              <p class="mono-line">{{ repository.url }}</p>
              <p v-if="repository.remote_commit" class="connection-detail">远端提交 {{ repository.remote_commit.slice(0, 12) }}</p>
              <p v-if="repository.last_error" class="connection-error">{{ repository.last_error }}</p>
              <div v-if="isAdmin" class="record-actions">
                <el-button text :icon="Connection" :loading="connectionAction === `repository-test-${repository.id}`" @click="runRepositoryAction(repository, false)">检测</el-button>
                <el-button text :icon="Refresh" :loading="connectionAction === `repository-sync-${repository.id}`" @click="runRepositoryAction(repository, true)">同步</el-button>
                <el-button text :icon="Edit" @click="openRepositoryDialog(repository)">编辑</el-button>
                <el-button text type="danger" :icon="Delete" @click="removeRepository(repository)">删除</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-if="!loading.repositories && !errors.repositories && !gitRepositories.length" text="暂无 Git 仓库关联" :compact="true" />
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="roleDialog.visible" :title="roleDialog.id ? '编辑角色' : '新建角色'" width="620px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top">
        <el-form-item label="角色名称" required><el-input v-model="roleDialog.name" maxlength="100" /></el-form-item>
        <el-form-item label="角色说明"><el-input v-model="roleDialog.description" type="textarea" :rows="2" maxlength="300" /></el-form-item>
        <el-form-item label="权限点" required>
          <el-checkbox-group v-model="roleDialog.permissions" class="permission-grid">
            <el-checkbox v-for="option in permissionOptions" :key="option.value" :value="option.value">{{ option.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="roleDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveRole">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="assignmentDialog.visible" :title="assignmentDialog.id ? '调整角色分配' : '分配角色'" width="520px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top">
        <el-form-item label="成员" required><el-select v-model="assignmentDialog.user" filterable :disabled="Boolean(assignmentDialog.id)"><el-option v-for="user in users" :key="user.id" :label="`${user.name || user.username} · ${user.email}`" :value="user.id" /></el-select></el-form-item>
        <el-form-item label="角色" required><el-select v-model="assignmentDialog.role"><el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" /></el-select></el-form-item>
        <el-form-item label="作用范围"><el-select v-model="assignmentDialog.project" clearable placeholder="全局范围"><el-option v-for="project in projects" :key="project.id" :label="`${project.name} · ${project.code}`" :value="project.id" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="assignmentDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveAssignment">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="flowDialog.visible" :title="flowDialog.id ? '编辑审批流程' : '新建审批流程'" width="700px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top">
        <div class="dialog-grid"><el-form-item label="流程名称" required><el-input v-model="flowDialog.name" maxlength="100" /></el-form-item><el-form-item label="流程类型" required><el-select v-model="flowDialog.flow_type" allow-create filterable><el-option v-for="option in flowTypeOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item></div>
        <div class="dialog-section-heading"><strong>审批节点</strong><el-button text type="primary" :icon="Plus" @click="addFlowStep">添加节点</el-button></div>
        <div class="designer-list">
          <div v-for="(step, index) in flowDialog.steps" :key="index" class="designer-row">
            <span class="step-index">{{ index + 1 }}</span>
            <el-input v-model="step.name" :placeholder="`第 ${index + 1} 级审批`" />
            <el-select v-model="step.reviewer_role" placeholder="审批角色"><el-option v-for="option in reviewerRoleOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select>
            <el-button :icon="Delete" circle plain type="danger" aria-label="删除节点" :disabled="flowDialog.steps.length === 1" @click="flowDialog.steps.splice(index, 1)" />
          </div>
        </div>
        <el-form-item label="流程状态"><el-switch v-model="flowDialog.is_active" active-text="启用" inactive-text="停用" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="flowDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveFlow">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="requestDialog.visible" title="发起审批申请" width="560px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top"><el-form-item label="审批流程" required><el-select v-model="requestDialog.flow"><el-option v-for="flow in activeFlows" :key="flow.id" :label="flow.name" :value="flow.id" /></el-select></el-form-item><el-form-item label="申请标题" required><el-input v-model="requestDialog.title" maxlength="100" /></el-form-item><el-form-item label="申请说明"><el-input v-model="requestDialog.content" type="textarea" :rows="5" maxlength="1000" /></el-form-item></el-form>
      <template #footer><el-button @click="requestDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveRequest">提交申请</el-button></template>
    </el-dialog>

    <el-dialog v-model="formDialog.visible" :title="formDialog.id ? '编辑自定义表单' : '新建自定义表单'" width="780px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top">
        <div class="dialog-grid"><el-form-item label="表单名称" required><el-input v-model="formDialog.name" maxlength="100" /></el-form-item><el-form-item label="状态"><el-switch v-model="formDialog.is_active" active-text="启用" inactive-text="停用" /></el-form-item></div>
        <el-form-item label="表单说明"><el-input v-model="formDialog.description" type="textarea" :rows="2" maxlength="300" /></el-form-item>
        <div class="dialog-section-heading"><strong>字段设计</strong><el-button text type="primary" :icon="Plus" @click="addFormField">添加字段</el-button></div>
        <div class="designer-list field-designer">
          <div v-for="(field, index) in formDialog.fields" :key="index" class="designer-row field-row">
            <el-input v-model="field.label" placeholder="字段标题" />
            <el-input v-model="field.key" placeholder="字段标识" />
            <el-select v-model="field.type"><el-option v-for="option in formFieldTypeOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select>
            <el-input v-if="field.type === 'select'" v-model="field.optionsText" placeholder="选项用逗号分隔" />
            <el-checkbox v-model="field.required">必填</el-checkbox>
            <el-button :icon="Delete" circle plain type="danger" aria-label="删除字段" @click="formDialog.fields.splice(index, 1)" />
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="formDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveForm">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="submissionDialog.visible" :title="submissionDialog.form?.name || '填写表单'" width="600px" :fullscreen="isMobile" append-to-body>
      <p v-if="submissionDialog.form?.description" class="dialog-description">{{ submissionDialog.form.description }}</p>
      <el-form label-position="top">
        <el-form-item v-for="field in submissionDialog.form?.fields || []" :key="field.key" :label="field.label" :required="field.required">
          <el-input v-if="field.type === 'text'" v-model="submissionDialog.data[field.key]" :placeholder="field.placeholder" />
          <el-input v-else-if="field.type === 'textarea'" v-model="submissionDialog.data[field.key]" type="textarea" :rows="3" :placeholder="field.placeholder" />
          <el-input-number v-else-if="field.type === 'number'" v-model="submissionDialog.data[field.key]" controls-position="right" />
          <el-date-picker v-else-if="field.type === 'date'" v-model="submissionDialog.data[field.key]" type="date" value-format="YYYY-MM-DD" />
          <el-select v-else-if="field.type === 'select'" v-model="submissionDialog.data[field.key]"><el-option v-for="option in field.options || []" :key="option" :label="option" :value="option" /></el-select>
          <el-switch v-else v-model="submissionDialog.data[field.key]" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="submissionDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveSubmission">提交</el-button></template>
    </el-dialog>

    <el-dialog v-model="platformDialog.visible" :title="platformDialog.id ? '编辑外部平台' : '新增外部平台'" width="620px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top"><div class="dialog-grid"><el-form-item label="平台名称" required><el-input v-model="platformDialog.name" /></el-form-item><el-form-item label="平台类型" required><el-select v-model="platformDialog.platform_type" allow-create filterable><el-option v-for="option in platformTypeOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item></div><el-form-item label="API 地址"><el-input v-model="platformDialog.api_url" placeholder="https://" /></el-form-item><el-form-item label="API 密钥"><el-input v-model="platformDialog.api_key" show-password :placeholder="platformDialog.id ? '留空则保持原密钥' : '可选'" /></el-form-item><el-form-item label="扩展配置 JSON"><el-input v-model="platformDialog.configText" type="textarea" :rows="4" /></el-form-item><el-form-item label="连接状态"><el-switch v-model="platformDialog.is_active" active-text="启用" inactive-text="停用" /></el-form-item></el-form>
      <template #footer><el-button @click="platformDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="savePlatform">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="repositoryDialog.visible" :title="repositoryDialog.id ? '编辑 Git 仓库' : '关联 Git 仓库'" width="620px" :fullscreen="isMobile" append-to-body>
      <el-form label-position="top"><el-form-item label="关联项目" required><el-select v-model="repositoryDialog.project" filterable><el-option v-for="project in projects" :key="project.id" :label="`${project.name} · ${project.code}`" :value="project.id" /></el-select></el-form-item><el-form-item label="仓库地址" required><el-input v-model="repositoryDialog.url" placeholder="https://example.com/team/repo.git" /></el-form-item><div class="dialog-grid"><el-form-item label="分支" required><el-input v-model="repositoryDialog.branch" /></el-form-item><el-form-item label="访问令牌"><el-input v-model="repositoryDialog.token" show-password :placeholder="repositoryDialog.id ? '留空则保持原令牌' : '私有仓库时填写'" /></el-form-item></div><el-form-item label="连接状态"><el-switch v-model="repositoryDialog.is_active" active-text="启用" inactive-text="停用" /></el-form-item></el-form>
      <template #footer><el-button @click="repositoryDialog.visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveRepository">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Delete, Document, Edit, FolderOpened, Plus, Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useDevice } from '@/composables/useDevice'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/format'
import { getUsers } from '@/api/users'
import { getProjects } from '@/api/projects'
import { getTeams, getTeamMembers, type Team, type TeamMember } from '@/api/teams'
import type { Project, User } from '@/types'
import { canCancelApprovalRequest, canReviewApprovalRequest } from './platformAccess'
import {
  approveApprovalRequest,
  cancelApprovalRequest,
  createApprovalFlow,
  createApprovalRequest,
  createCustomForm,
  createCustomRole,
  createExternalPlatform,
  createFormSubmission,
  createGitRepository,
  createRoleAssignment,
  deleteApprovalFlow,
  deleteCustomForm,
  deleteCustomRole,
  deleteExternalPlatform,
  deleteFormSubmission,
  deleteGitRepository,
  deleteRoleAssignment,
  getApprovalFlows,
  getApprovalRequests,
  getCustomForms,
  getCustomRoles,
  getExternalPlatforms,
  getFormSubmissions,
  getGitRepositories,
  getRoleAssignments,
  rejectApprovalRequest,
  syncExternalPlatform,
  syncGitRepository,
  testExternalPlatform,
  testGitRepository,
  updateApprovalFlow,
  updateCustomForm,
  updateCustomRole,
  updateExternalPlatform,
  updateGitRepository,
  updateRoleAssignment,
  type ApprovalFlow,
  type ApprovalRequest,
  type ApprovalStatus,
  type ApprovalStep,
  type CustomForm,
  type CustomFormField,
  type CustomFormFieldType,
  type CustomRole,
  type ExternalPlatform,
  type FormSubmission,
  type GitRepository,
  type RoleAssignment,
} from '@/api/platform'

const { isMobile } = useDevice()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'sys_admin')
const isManager = computed(() => isAdmin.value || userStore.role === 'teacher')
const activeTab = ref('roles')
const integrationMode = ref<'platforms' | 'repositories'>('platforms')
const integrationModes = [{ label: '外部平台', value: 'platforms' }, { label: 'Git 仓库', value: 'repositories' }]
const refreshing = ref(false)
const saving = ref(false)
const connectionAction = ref('')
const loading = reactive({ roles: false, assignments: false, flows: false, requests: false, forms: false, submissions: false, platforms: false, repositories: false })
const errors = reactive({ roles: '', assignments: '', flows: '', requests: '', forms: '', submissions: '', platforms: '', repositories: '' })

const roles = ref<CustomRole[]>([])
const assignments = ref<RoleAssignment[]>([])
const flows = ref<ApprovalFlow[]>([])
const approvalRequests = ref<ApprovalRequest[]>([])
const forms = ref<CustomForm[]>([])
const submissions = ref<FormSubmission[]>([])
const externalPlatforms = ref<ExternalPlatform[]>([])
const gitRepositories = ref<GitRepository[]>([])
const users = ref<User[]>([])
const projects = ref<Project[]>([])
const teams = ref<Team[]>([])
const selectedTeamId = ref<number | null>(null)
const selectedTeamMembers = ref<TeamMember[]>([])
const teamLoading = ref(false)

const responseItems = <T,>(response: { results: T[] } | T[]): T[] => Array.isArray(response) ? response : response.results
const activeFlowCount = computed(() => flows.value.filter((item) => item.is_active).length)
const pendingRequestCount = computed(() => approvalRequests.value.filter((item) => item.status === 'pending').length)
const activeFormCount = computed(() => forms.value.filter((item) => item.is_active).length)
const activeIntegrationCount = computed(() => externalPlatforms.value.filter((item) => item.is_active).length + gitRepositories.value.filter((item) => item.is_active).length)
const activeFlows = computed(() => flows.value.filter((item) => item.is_active))

const permissionOptions = [
  { value: 'project.view', label: '查看项目' }, { value: 'project.create', label: '创建项目' },
  { value: 'project.manage', label: '管理项目' }, { value: 'task.view', label: '查看任务' },
  { value: 'task.create', label: '创建任务' }, { value: 'task.manage', label: '管理任务' },
  { value: 'finance.view', label: '查看经费' }, { value: 'finance.manage', label: '管理经费' },
  { value: 'report.view', label: '查看报表' }, { value: 'report.manage', label: '管理报表' },
  { value: 'announcement.manage', label: '管理公告' },
  { value: 'member.view', label: '查看成员' }, { value: 'member.manage', label: '管理成员' },
]
const reviewerRoleOptions = [
  { value: 'teacher', label: '指导老师' }, { value: 'sys_admin', label: '系统管理员' },
  { value: 'sens_approver', label: '敏感信息审批人' }, { value: 'member', label: '普通成员' },
]
const flowTypeOptions = [
  { value: 'leave', label: '请假审批' }, { value: 'expense', label: '经费审批' },
  { value: 'sensitive', label: '敏感信息审批' }, { value: 'project', label: '项目事项审批' },
]
const formFieldTypeOptions: Array<{ value: CustomFormFieldType; label: string }> = [
  { value: 'text', label: '单行文本' }, { value: 'textarea', label: '多行文本' },
  { value: 'number', label: '数字' }, { value: 'date', label: '日期' },
  { value: 'select', label: '单选项' }, { value: 'switch', label: '开关' },
]
const platformTypeOptions = [
  { value: 'dingtalk', label: '钉钉' }, { value: 'wecom', label: '企业微信' },
  { value: 'feishu', label: '飞书' }, { value: 'jira', label: 'Jira' },
  { value: 'github', label: 'GitHub' }, { value: 'other', label: '其他平台' },
]

const roleDialog = reactive({ visible: false, id: null as number | null, name: '', description: '', permissions: [] as string[] })
const assignmentDialog = reactive({ visible: false, id: null as number | null, user: null as number | null, role: null as number | null, project: null as number | null })
const flowDialog = reactive({ visible: false, id: null as number | null, name: '', flow_type: 'project', steps: [] as ApprovalStep[], is_active: true })
const requestDialog = reactive({ visible: false, flow: null as number | null, title: '', content: '' })
interface FormFieldDraft extends CustomFormField { optionsText: string }
const formDialog = reactive({ visible: false, id: null as number | null, name: '', description: '', fields: [] as FormFieldDraft[], is_active: true })
// Dynamic Element Plus controls expose different model value unions per field type.
const submissionDialog = reactive({ visible: false, form: null as CustomForm | null, data: {} as Record<string, any> })
const platformDialog = reactive({ visible: false, id: null as number | null, name: '', platform_type: 'other', api_url: '', api_key: '', configText: '{}', is_active: true })
const repositoryDialog = reactive({ visible: false, id: null as number | null, url: '', branch: 'main', token: '', project: null as number | null, is_active: true })

async function loadResource(key: keyof typeof loading, loader: () => Promise<void>, label: string): Promise<void> {
  loading[key] = true
  errors[key] = ''
  try { await loader() } catch { errors[key] = `${label}加载失败，请检查网络后重试。` } finally { loading[key] = false }
}
const loadRoles = () => loadResource('roles', async () => { roles.value = responseItems(await getCustomRoles()) }, '角色')
const loadAssignments = () => loadResource('assignments', async () => { assignments.value = responseItems(await getRoleAssignments()) }, '角色分配')
const loadFlows = () => loadResource('flows', async () => { flows.value = responseItems(await getApprovalFlows()) }, '审批流程')
const loadRequests = () => loadResource('requests', async () => { approvalRequests.value = responseItems(await getApprovalRequests()) }, '审批申请')
const loadForms = () => loadResource('forms', async () => { forms.value = responseItems(await getCustomForms()) }, '表单')
const loadSubmissions = () => loadResource('submissions', async () => { submissions.value = responseItems(await getFormSubmissions()) }, '提交记录')
const loadPlatforms = () => loadResource('platforms', async () => { externalPlatforms.value = responseItems(await getExternalPlatforms()) }, '外部平台')
const loadRepositories = () => loadResource('repositories', async () => { gitRepositories.value = responseItems(await getGitRepositories()) }, 'Git 仓库')

async function loadLookups(): Promise<void> {
  const [userResult, projectResult, teamResult] = await Promise.allSettled([
    getUsers({ page: 1, page_size: 100 }), getProjects({ page: 1, page_size: 100 }), getTeams(),
  ])
  if (userResult.status === 'fulfilled') users.value = responseItems(userResult.value)
  if (projectResult.status === 'fulfilled') projects.value = responseItems(projectResult.value)
  if (teamResult.status === 'fulfilled') teams.value = responseItems(teamResult.value)
}

async function loadSelectedTeamMembers(): Promise<void> {
  selectedTeamMembers.value = []
  if (!selectedTeamId.value) return
  teamLoading.value = true
  try { selectedTeamMembers.value = await getTeamMembers(selectedTeamId.value) } catch { ElMessage.error('团队成员信息加载失败') } finally { teamLoading.value = false }
}

async function refreshActiveTab(): Promise<void> {
  refreshing.value = true
  try {
    if (activeTab.value === 'roles') await Promise.all([loadRoles(), loadAssignments(), loadLookups()])
    if (activeTab.value === 'approvals') await Promise.all([loadFlows(), loadRequests()])
    if (activeTab.value === 'forms') await Promise.all([loadForms(), loadSubmissions()])
    if (activeTab.value === 'integrations') await Promise.all([loadPlatforms(), loadRepositories(), loadLookups()])
  } finally { refreshing.value = false }
}
function handleTabChange(): void { void refreshActiveTab() }

function permissionLabel(value: string): string { return permissionOptions.find((item) => item.value === value)?.label || value }
function flowTypeLabel(value: string): string { return flowTypeOptions.find((item) => item.value === value)?.label || value }
function platformTypeLabel(value: string): string { return platformTypeOptions.find((item) => item.value === value)?.label || value }
function connectionLabel(value: string): string { return ({ unchecked: '未检测', connected: '已连接', error: '连接异常' } as Record<string, string>)[value] || '未检测' }
function connectionTone(value: string): 'success' | 'danger' | 'info' { return value === 'connected' ? 'success' : value === 'error' ? 'danger' : 'info' }
function reviewerLabel(step: ApprovalStep): string { return reviewerRoleOptions.find((item) => item.value === step.reviewer_role)?.label || (step.reviewer_ids?.length ? `${step.reviewer_ids.length} 位指定成员` : '管理角色') }
function approvalStatusLabel(status: ApprovalStatus): string { return ({ pending: '待审批', approved: '已通过', rejected: '已驳回', cancelled: '已取消' })[status] }
function approvalStatusTone(status: ApprovalStatus): 'warning' | 'success' | 'danger' | 'info' { const tones: Record<ApprovalStatus, 'warning' | 'success' | 'danger' | 'info'> = { pending: 'warning', approved: 'success', rejected: 'danger', cancelled: 'info' }; return tones[status] }
function requiredFieldCount(item: CustomForm): number { return item.fields.filter((field) => field.required).length }
function submissionSummary(item: FormSubmission): string { const entries = Object.entries(item.data || {}); return entries.length ? entries.slice(0, 4).map(([key, value]) => `${key}: ${String(value)}`).join(' · ') : '未提交字段内容' }
async function confirmAction(message: string, title: string): Promise<boolean> {
  try {
    await ElMessageBox.confirm(message, title, { type: 'warning' })
    return true
  } catch {
    return false
  }
}

function openRoleDialog(role?: CustomRole): void { Object.assign(roleDialog, { visible: true, id: role?.id || null, name: role?.name || '', description: role?.description || '', permissions: [...(role?.permissions || [])] }) }
async function saveRole(): Promise<void> {
  if (!roleDialog.name.trim() || !roleDialog.permissions.length) return void ElMessage.warning('请填写角色名称并选择至少一个权限点')
  saving.value = true
  try {
    const payload = { name: roleDialog.name.trim(), description: roleDialog.description.trim(), permissions: roleDialog.permissions }
    if (roleDialog.id) await updateCustomRole(roleDialog.id, payload)
    else await createCustomRole(payload)
    roleDialog.visible = false
    ElMessage.success('角色已保存')
    await loadRoles()
  } finally { saving.value = false }
}
async function removeRole(role: CustomRole): Promise<void> { if (!await confirmAction(`删除角色“${role.name}”？`, '删除角色')) return; await deleteCustomRole(role.id); ElMessage.success('角色已删除'); await Promise.all([loadRoles(), loadAssignments()]) }

function openAssignmentDialog(item?: RoleAssignment): void { Object.assign(assignmentDialog, { visible: true, id: item?.id || null, user: item?.user || null, role: item?.role || null, project: item?.project || null }) }
async function saveAssignment(): Promise<void> {
  if (!assignmentDialog.user || !assignmentDialog.role) return void ElMessage.warning('请选择成员和角色')
  saving.value = true
  try {
    const payload = { user: assignmentDialog.user, role: assignmentDialog.role, project: assignmentDialog.project }
    if (assignmentDialog.id) await updateRoleAssignment(assignmentDialog.id, payload)
    else await createRoleAssignment(payload)
    assignmentDialog.visible = false
    ElMessage.success('角色分配已保存')
    await loadAssignments()
  } finally { saving.value = false }
}
async function removeAssignment(item: RoleAssignment): Promise<void> { if (!await confirmAction(`撤销 ${item.user_name} 的“${item.role_name}”角色？`, '撤销角色')) return; await deleteRoleAssignment(item.id); ElMessage.success('角色已撤销'); await loadAssignments() }

function openFlowDialog(flow?: ApprovalFlow): void { Object.assign(flowDialog, { visible: true, id: flow?.id || null, name: flow?.name || '', flow_type: flow?.flow_type || 'project', steps: flow?.steps?.map((step) => ({ ...step })) || [{ name: '负责人审批', reviewer_role: 'teacher' }], is_active: flow?.is_active ?? true }) }
function addFlowStep(): void { flowDialog.steps.push({ name: `第 ${flowDialog.steps.length + 1} 级审批`, reviewer_role: 'teacher' }) }
async function saveFlow(): Promise<void> {
  if (!flowDialog.name.trim() || !flowDialog.flow_type || !flowDialog.steps.length || flowDialog.steps.some((step) => !step.name.trim() || !step.reviewer_role)) return void ElMessage.warning('请完整填写流程名称、类型和审批节点')
  saving.value = true
  try {
    const payload = { name: flowDialog.name.trim(), flow_type: flowDialog.flow_type, steps: flowDialog.steps.map((step) => ({ name: step.name.trim(), reviewer_role: step.reviewer_role })), is_active: flowDialog.is_active }
    if (flowDialog.id) await updateApprovalFlow(flowDialog.id, payload)
    else await createApprovalFlow(payload)
    flowDialog.visible = false
    ElMessage.success('审批流程已保存')
    await loadFlows()
  } finally { saving.value = false }
}
async function removeFlow(flow: ApprovalFlow): Promise<void> { if (!await confirmAction(`删除流程“${flow.name}”？已有申请可能受影响。`, '删除审批流程')) return; await deleteApprovalFlow(flow.id); ElMessage.success('审批流程已删除'); await loadFlows() }
function openRequestDialog(): void { Object.assign(requestDialog, { visible: true, flow: activeFlows.value[0]?.id || null, title: '', content: '' }) }
async function saveRequest(): Promise<void> { if (!requestDialog.flow || !requestDialog.title.trim()) return void ElMessage.warning('请选择流程并填写申请标题'); saving.value = true; try { await createApprovalRequest({ flow: requestDialog.flow, title: requestDialog.title.trim(), content: requestDialog.content.trim() }); requestDialog.visible = false; ElMessage.success('审批申请已提交'); await loadRequests() } finally { saving.value = false } }
function canReview(item: ApprovalRequest): boolean { return canReviewApprovalRequest(item, flows.value, { id: userStore.userInfo?.id, role: userStore.role, isManager: isManager.value }) }
function canCancel(item: ApprovalRequest): boolean { return canCancelApprovalRequest(item, userStore.userInfo?.id) }
async function reviewRequest(item: ApprovalRequest, action: 'approve' | 'reject'): Promise<void> {
  let opinion: string
  try {
    const result = await ElMessageBox.prompt('填写审批意见（可选）', action === 'approve' ? '通过申请' : '驳回申请', { inputType: 'textarea', confirmButtonText: action === 'approve' ? '通过' : '驳回', cancelButtonText: '取消' })
    opinion = result.value || ''
  } catch { return }
  if (action === 'approve') await approveApprovalRequest(item.id, opinion)
  else await rejectApprovalRequest(item.id, opinion)
  ElMessage.success(action === 'approve' ? '审批已通过' : '申请已驳回')
  await loadRequests()
}
async function cancelRequest(item: ApprovalRequest): Promise<void> { if (!await confirmAction(`取消申请“${item.title}”？`, '取消申请')) return; await cancelApprovalRequest(item.id); ElMessage.success('申请已取消'); await loadRequests() }

function openFormDialog(item?: CustomForm): void { Object.assign(formDialog, { visible: true, id: item?.id || null, name: item?.name || '', description: item?.description || '', fields: item?.fields.map((field) => ({ ...field, optionsText: (field.options || []).join(',') })) || [{ key: 'content', label: '内容', type: 'textarea', required: true, optionsText: '' }], is_active: item?.is_active ?? true }) }
function addFormField(): void { formDialog.fields.push({ key: `field_${formDialog.fields.length + 1}`, label: '', type: 'text', required: false, optionsText: '' }) }
async function saveForm(): Promise<void> {
  if (!formDialog.name.trim() || !formDialog.fields.length || formDialog.fields.some((field) => !field.key.trim() || !field.label.trim())) return void ElMessage.warning('请填写表单名称及完整字段信息')
  if (new Set(formDialog.fields.map((field) => field.key.trim())).size !== formDialog.fields.length) return void ElMessage.warning('字段标识不能重复')
  const fields: CustomFormField[] = formDialog.fields.map(({ optionsText, ...field }) => ({ ...field, key: field.key.trim(), label: field.label.trim(), ...(field.type === 'select' ? { options: optionsText.split(/[,，]/).map((item) => item.trim()).filter(Boolean) } : {}) }))
  saving.value = true
  try {
    const payload = { name: formDialog.name.trim(), description: formDialog.description.trim(), fields, is_active: formDialog.is_active }
    if (formDialog.id) await updateCustomForm(formDialog.id, payload)
    else await createCustomForm(payload)
    formDialog.visible = false
    ElMessage.success('表单已保存')
    await loadForms()
  } finally { saving.value = false }
}
async function removeForm(item: CustomForm): Promise<void> { if (!await confirmAction(`删除表单“${item.name}”？其提交记录也会删除。`, '删除表单')) return; await deleteCustomForm(item.id); ElMessage.success('表单已删除'); await Promise.all([loadForms(), loadSubmissions()]) }
function openSubmissionDialog(item: CustomForm): void { const data: Record<string, unknown> = {}; item.fields.forEach((field) => { data[field.key] = field.type === 'switch' ? false : field.type === 'number' ? undefined : '' }); Object.assign(submissionDialog, { visible: true, form: item, data }) }
async function saveSubmission(): Promise<void> { const item = submissionDialog.form; if (!item) return; const missing = item.fields.find((field) => field.required && (submissionDialog.data[field.key] === '' || submissionDialog.data[field.key] === undefined || submissionDialog.data[field.key] === null)); if (missing) return void ElMessage.warning(`请填写“${missing.label}”`); saving.value = true; try { await createFormSubmission(item.id, submissionDialog.data); submissionDialog.visible = false; ElMessage.success('表单已提交'); await loadSubmissions() } finally { saving.value = false } }
function canDeleteSubmission(item: FormSubmission): boolean { return isManager.value || item.user === userStore.userInfo?.id }
async function removeSubmission(item: FormSubmission): Promise<void> { if (!await confirmAction('删除这条提交记录？', '删除提交')) return; await deleteFormSubmission(item.id); ElMessage.success('提交记录已删除'); await loadSubmissions() }

function openPlatformDialog(item?: ExternalPlatform): void { Object.assign(platformDialog, { visible: true, id: item?.id || null, name: item?.name || '', platform_type: item?.platform_type || 'other', api_url: item?.api_url || '', api_key: '', configText: JSON.stringify(item?.config || {}, null, 2), is_active: item?.is_active ?? true }) }
async function savePlatform(): Promise<void> { if (!platformDialog.name.trim() || !platformDialog.platform_type) return void ElMessage.warning('请填写平台名称和类型'); let config: Record<string, unknown>; try { config = JSON.parse(platformDialog.configText || '{}') } catch { return void ElMessage.warning('扩展配置必须是有效 JSON') } const payload = { name: platformDialog.name.trim(), platform_type: platformDialog.platform_type, api_url: platformDialog.api_url.trim(), is_active: platformDialog.is_active, config, ...(platformDialog.api_key ? { api_key: platformDialog.api_key } : {}) }; saving.value = true; try { if (platformDialog.id) await updateExternalPlatform(platformDialog.id, payload); else await createExternalPlatform(payload); platformDialog.visible = false; ElMessage.success('外部平台已保存'); await loadPlatforms() } finally { saving.value = false } }
async function removePlatform(item: ExternalPlatform): Promise<void> { if (!await confirmAction(`删除连接“${item.name}”？`, '删除外部平台')) return; await deleteExternalPlatform(item.id); ElMessage.success('连接已删除'); await loadPlatforms() }
async function runPlatformAction(item: ExternalPlatform, sync: boolean): Promise<void> {
  connectionAction.value = `platform-${sync ? 'sync' : 'test'}-${item.id}`
  try {
    if (sync) await syncExternalPlatform(item.id)
    else await testExternalPlatform(item.id)
    ElMessage.success(sync ? '平台数据已同步' : '平台连接正常')
    await loadPlatforms()
  } finally { connectionAction.value = '' }
}
function openRepositoryDialog(item?: GitRepository): void { Object.assign(repositoryDialog, { visible: true, id: item?.id || null, url: item?.url || '', branch: item?.branch || 'main', token: '', project: item?.project || null, is_active: item?.is_active ?? true }) }
async function saveRepository(): Promise<void> { if (!repositoryDialog.project || !repositoryDialog.url.trim() || !repositoryDialog.branch.trim()) return void ElMessage.warning('请选择项目并填写仓库地址和分支'); const payload = { url: repositoryDialog.url.trim(), branch: repositoryDialog.branch.trim(), project: repositoryDialog.project, is_active: repositoryDialog.is_active, ...(repositoryDialog.token ? { token: repositoryDialog.token } : {}) }; saving.value = true; try { if (repositoryDialog.id) await updateGitRepository(repositoryDialog.id, payload); else await createGitRepository(payload); repositoryDialog.visible = false; ElMessage.success('Git 仓库已保存'); await loadRepositories() } finally { saving.value = false } }
async function removeRepository(item: GitRepository): Promise<void> { if (!await confirmAction(`解除项目“${item.project_name}”的仓库关联？`, '解除 Git 关联')) return; await deleteGitRepository(item.id); ElMessage.success('仓库关联已解除'); await loadRepositories() }
async function runRepositoryAction(item: GitRepository, sync: boolean): Promise<void> {
  connectionAction.value = `repository-${sync ? 'sync' : 'test'}-${item.id}`
  try {
    if (sync) await syncGitRepository(item.id)
    else await testGitRepository(item.id)
    ElMessage.success(sync ? '远端分支已同步' : 'Git 连接正常')
    await loadRepositories()
  } finally { connectionAction.value = '' }
}

onMounted(async () => {
  await Promise.all([
    loadRoles(), loadAssignments(), loadFlows(), loadRequests(), loadForms(),
    loadSubmissions(), loadPlatforms(), loadRepositories(), loadLookups(),
  ])
})
</script>

<style scoped lang="scss">
.platform-page { padding-bottom: 48px; }
.metric-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 18px; overflow: hidden; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.metric-item { display: grid; gap: 4px; min-height: 96px; padding: 15px 18px; border-left: 1px solid var(--color-border-light); &:first-child { border-left: 0; } span, small { color: var(--color-text-muted); font-size: 12px; } strong { color: var(--color-text); font-size: 24px; font-variant-numeric: tabular-nums; } }
.workspace-tabs :deep(.el-tabs__header) { margin-bottom: 18px; }
.permission-alert { margin-bottom: 16px; }
.team-context { display: grid; grid-template-columns: minmax(240px, .8fr) minmax(220px, .45fr) minmax(280px, 1fr); align-items: center; gap: 18px; padding: 16px 18px; margin-bottom: 26px; background: var(--color-surface-subtle); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); h2 { margin: 2px 0 3px; font-size: 15px; } p { color: var(--color-text-muted); font-size: 12px; } }
.section-kicker { color: var(--color-primary); font-size: 11px; font-weight: 600; }
.team-members, .tag-list { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.collection-section { margin-bottom: 30px; }
.section-toolbar { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 12px; h2 { margin: 0; font-size: 17px; } p { margin-top: 3px; color: var(--color-text-muted); font-size: 12px; } }
.record-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; min-height: 80px; }
.role-grid, .flow-grid { grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
.record-card { display: grid; align-content: start; gap: 14px; min-width: 0; padding: 16px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.compact-card { grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 10px; .record-actions { grid-column: 1 / -1; } }
.record-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; min-width: 0; h3 { margin: 0; color: var(--color-text); font-size: 14px; overflow-wrap: anywhere; } p { margin-top: 4px; color: var(--color-text-muted); font-size: 12px; line-height: 1.5; overflow-wrap: anywhere; } }
.record-actions { display: flex; justify-content: flex-end; gap: 4px; padding-top: 10px; border-top: 1px solid var(--color-border-light); }
.muted { color: var(--color-text-muted); font-size: 12px; }
.assignment-line { display: flex; align-items: center; gap: 10px; min-width: 0; h3 { margin: 0; font-size: 14px; } p { color: var(--color-text-muted); font-size: 12px; } }
.initial { display: grid; place-items: center; width: 34px; height: 34px; flex: 0 0 auto; color: var(--color-primary); font-weight: 600; background: var(--color-primary-soft); border-radius: 50%; }
.step-preview { display: grid; gap: 8px; li { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; align-items: center; gap: 8px; span { display: grid; place-items: center; width: 22px; height: 22px; color: var(--color-primary); background: var(--color-primary-soft); border-radius: 50%; font-size: 11px; } strong { font-size: 12px; font-weight: 500; } small { color: var(--color-text-muted); } } }
.record-list { display: grid; gap: 8px; min-height: 80px; }
.request-row { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: center; gap: 20px; padding: 14px 16px; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); }
.request-content { margin-top: 7px; color: var(--color-text-regular); font-size: 12px; line-height: 1.5; }
.request-meta { display: grid; gap: 4px; color: var(--color-text-muted); font-size: 11px; text-align: right; }
.row-actions { display: flex; gap: 6px; }
.field-summary { display: flex; gap: 14px; color: var(--color-text-muted); font-size: 12px; }
.integration-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.integration-card { grid-template-columns: 42px minmax(0, 1fr); .record-actions, .mono-line { grid-column: 1 / -1; } }
.integration-icon { display: grid; place-items: center; width: 40px; height: 40px; color: var(--color-primary); background: var(--color-primary-soft); border-radius: var(--radius-sm); font-size: 20px; }
.connection-detail { grid-column: 1 / -1; margin: 0; color: var(--color-text-secondary); font-size: 12px; }
.connection-error { grid-column: 1 / -1; margin: 0; color: var(--color-danger); font-size: 12px; overflow-wrap: anywhere; }
.git-icon { color: var(--color-text); background: var(--color-surface-strong); }
.mono-line { overflow: hidden; color: var(--color-text-muted); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.permission-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); width: 100%; gap: 6px; }
.dialog-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.dialog-section-heading { display: flex; align-items: center; justify-content: space-between; margin: 4px 0 10px; }
.designer-list { display: grid; gap: 8px; margin-bottom: 16px; }
.designer-row { display: grid; grid-template-columns: 30px minmax(0, 1fr) minmax(140px, .6fr) 34px; align-items: center; gap: 8px; }
.field-row { grid-template-columns: minmax(130px, 1fr) minmax(110px, .8fr) 120px minmax(130px, 1fr) auto 34px; }
.step-index { display: grid; place-items: center; width: 26px; height: 26px; color: var(--color-primary); background: var(--color-primary-soft); border-radius: 50%; font-size: 12px; }
.dialog-description { margin: 0 0 16px; color: var(--color-text-muted); line-height: 1.6; }
:deep(.el-select), :deep(.el-date-editor) { width: 100%; }
@media (max-width: 980px) { .metric-strip { grid-template-columns: repeat(2, 1fr); } .metric-item:nth-child(3) { border-left: 0; border-top: 1px solid var(--color-border-light); } .metric-item:nth-child(4) { border-top: 1px solid var(--color-border-light); } .team-context { grid-template-columns: 1fr 1fr; .team-members { grid-column: 1 / -1; } } .request-row { grid-template-columns: minmax(0, 1fr) auto; .row-actions { grid-column: 1 / -1; justify-content: flex-end; } } .field-row { grid-template-columns: repeat(2, minmax(0, 1fr)) 110px; > :last-child { justify-self: end; } } }
@media (max-width: 640px) { .metric-strip { grid-template-columns: 1fr 1fr; } .metric-item { min-height: 82px; padding: 12px; strong { font-size: 20px; } } .team-context { grid-template-columns: 1fr; .team-members { grid-column: auto; } } .section-toolbar, .integration-toolbar { align-items: stretch; flex-direction: column; } .record-grid, .role-grid, .flow-grid { grid-template-columns: minmax(0, 1fr); } .request-row { grid-template-columns: 1fr; gap: 10px; } .request-meta { grid-auto-flow: column; justify-content: space-between; text-align: left; } .row-actions { grid-column: auto !important; justify-content: flex-start !important; flex-wrap: wrap; } .permission-grid, .dialog-grid { grid-template-columns: 1fr; } .designer-row, .field-row { grid-template-columns: 26px minmax(0, 1fr) 34px; > :nth-child(3), > :nth-child(4), > :nth-child(5) { grid-column: 2 / -1; } > :last-child { grid-column: 3; grid-row: 1; } } }
</style>
