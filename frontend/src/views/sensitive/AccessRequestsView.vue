<template>
  <div class="page-container access-requests-page">
    <PageHeader title="我的访问申请" subtitle="敏感资料访问记录与授权状态">
      <template #meta>
        <span class="page-meta">共 {{ requestList.length }} 条申请</span>
      </template>
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="handleApply">申请查看</el-button>
      </template>
    </PageHeader>

    <section class="request-overview" aria-label="申请状态概览">
      <div>
        <span>待审批</span>
        <strong :class="{ 'is-warning': requestSummary.pending > 0 }">{{ requestSummary.pending }}</strong>
      </div>
      <div>
        <span>授权有效</span>
        <strong class="is-success">{{ requestSummary.active }}</strong>
      </div>
      <div>
        <span>异常 / 失效</span>
        <strong :class="{ 'is-danger': requestSummary.exception > 0 }">{{ requestSummary.exception }}</strong>
      </div>
    </section>

    <section class="request-surface">
      <div class="surface-heading">
        <h2>申请记录</h2>
        <span>最近授权状态</span>
      </div>

      <div v-if="!isMobile" class="request-table-shell">
        <el-table v-loading="loading" :data="requestList" stripe size="small">
          <el-table-column prop="sensitive_data_type" label="资料" min-width="154">
            <template #default="{ row }">
              <div class="data-cell">
                <strong>{{ row.sensitive_data_title || getSensitiveTypeLabel(row as SensitiveAccessRequest) }}</strong>
                <span>{{ getSensitiveTypeLabel(row as SensitiveAccessRequest) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="usage_scenario" label="使用场景" min-width="140" show-overflow-tooltip />
          <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />
          <el-table-column prop="project_name" label="所属项目" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.project_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="访问范围" width="92">
            <template #default="{ row }">
              <el-tag v-if="row.is_download || row.need_download" type="danger" size="small" effect="plain">
                含下载
              </el-tag>
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
          <el-table-column prop="created_at" label="申请时间" width="116">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="授权剩余" width="108">
            <template #default="{ row }">
              <span v-if="row.status === 'approved' && !isExpired(row as SensitiveAccessRequest)" class="remaining-time">
                {{ getRemainingTime(getRequestExpiry(row as SensitiveAccessRequest)) }}
              </span>
              <span v-else-if="row.status === 'approved' && isExpired(row as SensitiveAccessRequest)" class="text-expired">已过期</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="176" fixed="right" align="right">
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
                :loading="downloadingId === row.id"
                @click="handleDownloadAttachment(row as SensitiveAccessRequest)"
              >
                下载
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无访问申请" />
          </template>
        </el-table>
      </div>

      <div v-else v-loading="loading" class="mobile-request-list">
        <article
          v-for="item in requestList"
          :key="item.id"
          class="mobile-request-card"
          :class="{ 'is-active-access': item.status === 'approved' && !isExpired(item) }"
        >
          <div class="mobile-card-heading">
            <div>
              <h3>{{ item.sensitive_data_title || getSensitiveTypeLabel(item) }}</h3>
              <span>{{ getSensitiveTypeLabel(item) }}</span>
            </div>
            <el-tag :type="getRequestStatus(item).type as any" size="small" effect="plain">
              {{ getRequestStatus(item).label }}
            </el-tag>
          </div>

          <dl class="mobile-request-meta">
            <div>
              <dt>使用场景</dt>
              <dd>{{ item.usage_scenario || '-' }}</dd>
            </div>
            <div>
              <dt>所属项目</dt>
              <dd>{{ item.project_name || '-' }}</dd>
            </div>
            <div class="meta-wide">
              <dt>申请理由</dt>
              <dd>{{ item.reason || '-' }}</dd>
            </div>
            <div>
              <dt>申请时间</dt>
              <dd>{{ formatDate(item.created_at) }}</dd>
            </div>
            <div>
              <dt>访问范围</dt>
              <dd :class="{ 'download-requested': item.is_download || item.need_download }">
                {{ item.is_download || item.need_download ? '查看并下载' : '仅查看' }}
              </dd>
            </div>
          </dl>

          <div v-if="item.status === 'approved' && !isExpired(item)" class="mobile-access-bar">
            <span>剩余 {{ getRemainingTime(getRequestExpiry(item)) }}</span>
            <div class="mobile-access-buttons">
              <el-button :icon="View" type="primary" size="small" @click="handleViewData(item)">查看明文</el-button>
              <el-button
                v-if="canDownloadAttachment(item)"
                :icon="Download"
                type="success"
                size="small"
                :loading="downloadingId === item.id"
                @click="handleDownloadAttachment(item)"
              >
                下载附件
              </el-button>
            </div>
          </div>
        </article>
        <el-empty v-if="requestList.length === 0 && !loading" description="暂无访问申请" />
      </div>
    </section>

    <el-dialog
      v-model="applyDialogVisible"
      title="申请查看敏感资料"
      width="680px"
      :close-on-click-modal="false"
      @close="handleCloseApply"
    >
      <el-form ref="applyFormRef" class="apply-form" :model="applyForm" :rules="applyRules" label-position="top">
        <div class="apply-form-grid">
          <el-form-item class="form-wide" label="敏感资料" prop="sensitive_data">
          <el-select v-model="applyForm.sensitive_data" :loading="optionsLoading" placeholder="请选择敏感资料" filterable>
            <el-option
              v-for="d in sensitiveDataOptions"
              :key="d.id"
              :label="d.title || d.label || d.display_name"
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

    <!-- 限时查看弹窗 -->
    <SensitiveViewDialog
      v-model:visible="viewDialogVisible"
      :request="viewingRequest"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Download, Plus, View } from '@element-plus/icons-vue'
import {
  createAccessRequest,
  downloadSensitiveAttachment,
  getMyAccessRequests,
  getSensitiveData,
} from '@/api/sensitive'
import { getProjects } from '@/api/projects'
import { downloadBlob, formatDate } from '@/utils/format'
import { SENSITIVE_DATA_TYPE_MAP, ACCESS_REQUEST_STATUS_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import SensitiveViewDialog from './SensitiveViewDialog.vue'
import type { Project, SensitiveAccessRequest, SensitiveData } from '@/types'

const { isMobile } = useDevice()

const loading = ref(false)
const submitting = ref(false)
const optionsLoading = ref(false)
const requestList = ref<SensitiveAccessRequest[]>([])
const projectOptions = ref<Project[]>([])
const sensitiveDataOptions = ref<SensitiveData[]>([])

const applyDialogVisible = ref(false)
const viewDialogVisible = ref(false)
const applyFormRef = ref<FormInstance>()
const viewingRequest = ref<SensitiveAccessRequest | null>(null)
const downloadingId = ref<number | null>(null)

// 申请表单
const applyForm = reactive({
  sensitive_data: undefined as number | undefined,
  usage_scenario: '',
  reason: '',
  project: '' as number | string,
  expected_use_time: '',
  is_download: false,
})
const applyRules: FormRules = {
  sensitive_data: [{ required: true, message: '请选择敏感资料', trigger: 'change' }],
  usage_scenario: [{ required: true, message: '请描述使用场景', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入申请理由', trigger: 'blur' }],
}

function getSensitiveTypeLabel(row: SensitiveAccessRequest): string {
  const type = row.sensitive_data_type || row.data_type || ''
  return row.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[type]?.label || type || '未知类型'
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

const requestSummary = computed(() => {
  const pending = requestList.value.filter((item) => item.status === 'pending').length
  const active = requestList.value.filter((item) => item.status === 'approved' && !isExpired(item)).length
  const exception = requestList.value.filter((item) =>
    ['rejected', 'expired', 'revoked'].includes(item.status || '') ||
    (item.status === 'approved' && isExpired(item))
  ).length
  return { pending, active, exception }
})

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

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getMyAccessRequests()
    requestList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 加载选项
async function loadOptions(): Promise<void> {
  optionsLoading.value = true
  try {
    const [projectsRes, sensitiveRes] = await Promise.all([
      getProjects({ page: 1, page_size: 100 }),
      getSensitiveData({ page: 1, page_size: 100 }),
    ])
    projectOptions.value = (projectsRes as any).results || []
    sensitiveDataOptions.value = (sensitiveRes as any).results || []
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
    project: '',
    expected_use_time: '',
    is_download: false,
  })
  loadOptions()
  applyDialogVisible.value = true
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
      loadData()
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
  downloadingId.value = row.id
  try {
    const blob = await downloadSensitiveAttachment(row.id)
    downloadBlob(blob, row.attachment_name || `敏感资料附件_${row.id}`)
    ElMessage.success('附件已通过受保护通道下载')
  } catch {
    // 错误已由统一拦截器处理
  } finally {
    downloadingId.value = null
  }
}

onMounted(() => {
  loadData()
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
.access-requests-page {
  padding-bottom: 32px;
}

.page-meta {
  display: inline-block;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.request-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 14px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.request-overview > div {
  display: flex;
  min-height: 70px;
  padding: 12px 18px;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  border-right: 1px solid var(--color-border-light);
}

.request-overview > div:last-child {
  border-right: 0;
}

.request-overview span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.request-overview strong {
  color: var(--color-text);
  font-size: 21px;
  font-weight: 600;
  line-height: 1.2;
}

.request-overview .is-warning {
  color: var(--color-warning);
}

.request-overview .is-success {
  color: var(--color-success);
}

.request-overview .is-danger {
  color: var(--color-danger);
}

.request-surface {
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

.request-table-shell {
  min-width: 0;
  overflow-x: auto;
}

.request-table-shell :deep(.el-table) {
  min-width: 1120px;
}

.data-cell {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.data-cell strong {
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
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

.mobile-request-list {
  display: flex;
  padding: 12px;
  flex-direction: column;
  gap: 10px;
}

.mobile-request-card {
  overflow: hidden;
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.mobile-request-card.is-active-access {
  border-color: rgba(23, 107, 115, 0.42);
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
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.mobile-request-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-request-meta .meta-wide {
  grid-column: 1 / -1;
}

.mobile-request-meta dt {
  margin-bottom: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.mobile-request-meta dd {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-regular);
  font-size: 13px;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.mobile-request-meta .download-requested {
  color: var(--color-danger);
  font-weight: 600;
}

.mobile-access-bar {
  display: flex;
  margin: 12px -14px -14px;
  padding: 10px 14px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--color-primary-soft);
  border-top: 1px solid rgba(23, 107, 115, 0.18);
}

.mobile-access-bar > span {
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

.apply-form :deep(.el-form-item__label) {
  height: auto;
  margin-bottom: 7px;
  color: var(--color-text-regular);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
}

.apply-form :deep(.el-select),
.apply-form :deep(.el-date-editor) {
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

@media screen and (max-width: 768px) {
  .access-requests-page {
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }

  .request-overview > div {
    min-height: 64px;
    padding: 10px 12px;
  }

  .request-overview strong {
    font-size: 18px;
  }

  .surface-heading {
    padding-right: 14px;
    padding-left: 14px;
  }

  .apply-form-grid {
    grid-template-columns: 1fr;
    gap: 15px;
  }

  .apply-form-grid .form-wide {
    grid-column: 1;
  }
}

@media screen and (max-width: 390px) {
  .request-overview span {
    font-size: 10px;
  }

  .mobile-access-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .mobile-access-buttons {
    width: 100%;
  }
}
</style>
