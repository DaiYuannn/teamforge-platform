<template>
  <div class="page-container pending-approve-page">
    <PageHeader title="待我审批" subtitle="敏感资料访问审批队列">
      <template #meta>
        <span class="page-meta">{{ pendingList.length }} 项待处理</span>
      </template>
    </PageHeader>

    <div v-if="pendingList.length > 0" class="pending-alert" role="status">
      <el-icon><WarningFilled /></el-icon>
      <div>
        <strong>有 {{ pendingList.length }} 项访问申请等待审批</strong>
        <span>包含下载权限的申请已单独标记</span>
      </div>
    </div>

    <section v-permission="['sens_approver', 'sys_admin', 'teacher']" class="approval-surface">
      <div class="surface-heading">
        <h2>审批队列</h2>
        <span>按申请时间排列</span>
      </div>

      <div v-if="!isMobile" class="approval-table-shell">
        <el-table v-loading="loading" :data="pendingList" stripe size="small">
        <el-table-column prop="applicant_name" label="申请人" width="110">
          <template #default="{ row }">
            <strong class="applicant-name">{{ row.applicant_name || row.requester_name || '-' }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="sensitive_data_type" label="资料" min-width="148">
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
        <el-table-column prop="created_at" label="申请时间" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="154" fixed="right" align="right">
          <template #default="{ row }">
            <el-button :icon="CircleCheck" type="success" link @click="handleApprove(row as SensitiveAccessRequest)">批准</el-button>
            <el-button :icon="CircleClose" type="danger" link @click="handleReject(row as SensitiveAccessRequest)">驳回</el-button>
          </template>
        </el-table-column>
          <template #empty>
            <el-empty description="暂无待审批申请" />
          </template>
        </el-table>
      </div>

      <div v-else v-loading="loading" class="mobile-approval-list">
        <article
          v-for="item in pendingList"
          :key="item.id"
          class="mobile-approval-card"
          :class="{ 'has-download-risk': item.is_download || item.need_download }"
        >
          <div class="mobile-card-heading">
            <div>
              <h3>{{ item.applicant_name || item.requester_name || '-' }}</h3>
              <span>申请查看 {{ item.sensitive_data_title || getSensitiveTypeLabel(item) }}</span>
            </div>
            <el-tag
              :type="item.is_download || item.need_download ? 'danger' : 'warning'"
              size="small"
              effect="plain"
            >
              {{ item.is_download || item.need_download ? '申请下载' : '待审批' }}
            </el-tag>
          </div>

          <dl class="mobile-approval-meta">
            <div>
              <dt>资料类型</dt>
              <dd>{{ getSensitiveTypeLabel(item) }}</dd>
            </div>
            <div>
              <dt>所属项目</dt>
              <dd>{{ item.project_name || '-' }}</dd>
            </div>
            <div class="meta-wide">
              <dt>使用场景</dt>
              <dd>{{ item.usage_scenario || '-' }}</dd>
            </div>
            <div class="meta-wide">
              <dt>申请理由</dt>
              <dd>{{ item.reason || '-' }}</dd>
            </div>
            <div>
              <dt>申请时间</dt>
              <dd>{{ formatDate(item.created_at) }}</dd>
            </div>
          </dl>

          <div class="mobile-approval-actions">
            <el-button :icon="CircleClose" type="danger" plain @click="handleReject(item)">驳回</el-button>
            <el-button :icon="CircleCheck" type="success" @click="handleApprove(item)">批准</el-button>
          </div>
        </article>
        <el-empty v-if="pendingList.length === 0 && !loading" description="暂无待审批申请" />
      </div>
    </section>

    <el-dialog v-model="approveDialogVisible" title="批准访问申请" width="460px" :close-on-click-modal="false">
      <div v-if="currentRequest" class="dialog-request-summary">
        <strong>{{ currentRequest.applicant_name || currentRequest.requester_name || '-' }}</strong>
        <span>{{ currentRequest.sensitive_data_title || getSensitiveTypeLabel(currentRequest) }}</span>
        <el-tag v-if="currentRequest.is_download || currentRequest.need_download" type="danger" size="small" effect="plain">包含下载权限</el-tag>
      </div>
      <el-form class="decision-form" :model="approveForm" label-position="top">
        <el-form-item label="有效时长（小时）">
          <el-input-number v-model="approveForm.expire_hours" :min="1" :max="72" controls-position="right" />
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
          <el-input v-model="rejectForm.approval_opinion" type="textarea" :rows="3" placeholder="请输入驳回理由" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="handleConfirmReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, CircleClose, WarningFilled } from '@element-plus/icons-vue'
import { getPendingApproveRequests, approveAccessRequest, rejectAccessRequest } from '@/api/sensitive'
import { formatDate } from '@/utils/format'
import { SENSITIVE_DATA_TYPE_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import type { SensitiveAccessRequest } from '@/types'

const { isMobile } = useDevice()
const route = useRoute()
const router = useRouter()
const requestedId = computed(() => {
  const value = Number(route.query.request_id)
  return Number.isInteger(value) && value > 0 ? value : undefined
})
const loading = ref(false)
const submitting = ref(false)
const pendingList = ref<SensitiveAccessRequest[]>([])

const approveDialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const currentRequest = ref<SensitiveAccessRequest | null>(null)

// 批准表单
const approveForm = reactive({
  action: 'approve' as const,
  expire_hours: 1,
  approval_opinion: '',
})

// 驳回表单
const rejectForm = reactive({
  action: 'reject' as const,
  approval_opinion: '',
})

function getSensitiveTypeLabel(row: SensitiveAccessRequest): string {
  const type = row.sensitive_data_type || row.data_type || ''
  return row.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[type]?.label || type || '未知类型'
}

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getPendingApproveRequests()
    pendingList.value = Array.isArray(res) ? res : (res.results || [])
    if (requestedId.value) {
      const request = pendingList.value.find((item) => item.id === requestedId.value)
      if (request) handleApprove(request)
      await router.replace({ path: '/sensitive/pending' })
    }
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
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
    await approveAccessRequest(currentRequest.value.id, { ...approveForm })
    ElMessage.success('已批准')
    approveDialogVisible.value = false
    loadData()
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
    await rejectAccessRequest(currentRequest.value.id, { ...rejectForm })
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    loadData()
  } catch {
    // 错误已由拦截器处理
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.pending-approve-page {
  padding-bottom: 32px;
}

.page-meta {
  display: inline-block;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.pending-alert {
  display: flex;
  margin-bottom: 14px;
  padding: 12px 16px;
  align-items: center;
  gap: 12px;
  background: var(--warning-light);
  border: 1px solid rgba(166, 97, 22, 0.26);
  border-radius: var(--radius-sm);
}

.pending-alert > .el-icon {
  flex: 0 0 auto;
  color: var(--color-warning);
  font-size: 20px;
}

.pending-alert > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.pending-alert strong {
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.pending-alert span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.approval-surface {
  min-width: 0;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.surface-heading {
  display: flex;
  min-height: 52px;
  padding: 12px 18px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.surface-heading h2 {
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
}

.surface-heading span {
  color: var(--color-text-muted);
  font-size: 12px;
}

.approval-table-shell {
  min-width: 0;
  overflow-x: auto;
}

.approval-table-shell :deep(.el-table) {
  min-width: 1040px;
}

.applicant-name,
.data-cell strong {
  color: var(--color-text);
  font-weight: 600;
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

.mobile-approval-list {
  display: flex;
  padding: 12px;
  flex-direction: column;
  gap: 10px;
}

.mobile-approval-card {
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.mobile-approval-card.has-download-risk {
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
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
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

.mobile-approval-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-approval-meta .meta-wide {
  grid-column: 1 / -1;
}

.mobile-approval-meta dt {
  margin-bottom: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.mobile-approval-meta dd {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-regular);
  font-size: 13px;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.mobile-approval-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-approval-actions :deep(.el-button) {
  width: 100%;
  margin-left: 0;
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

.decision-form :deep(.el-form-item__label) {
  height: auto;
  margin-bottom: 7px;
  color: var(--color-text-regular);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
}

.decision-form :deep(.el-input-number) {
  width: 100%;
}

@media screen and (max-width: 768px) {
  .pending-approve-page {
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }

  .surface-heading {
    padding-right: 14px;
    padding-left: 14px;
  }
}
</style>
