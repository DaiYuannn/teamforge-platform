<template>
  <div class="page-container">
    <PageHeader title="敏感资料管理" subtitle="管理敏感资料与访问申请" />

    <el-tabs v-model="activeTab" class="card tabs-card" @tab-change="handleTabChange">
      <!-- 我的资料 Tab -->
      <el-tab-pane label="我的资料" name="my-data">
        <el-table v-loading="myDataLoading" :data="myDataList" border stripe>
          <el-table-column prop="title" label="名称" min-width="150" />
          <el-table-column prop="data_type" label="类型" width="130">
            <template #default="{ row }">
              <el-tag :type="SENSITIVE_DATA_TYPE_MAP[row.data_type]?.tagType as any" size="small">
                {{ row.data_type_display || SENSITIVE_DATA_TYPE_MAP[row.data_type]?.label || row.data_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="masked_value" label="脱敏值" min-width="180" />
        </el-table>
      </el-tab-pane>

      <!-- 资料查看申请 Tab -->
      <el-tab-pane label="资料查看申请" name="requests">
        <div class="section-header">
          <span></span>
          <el-button type="primary" :icon="Plus" @click="handleApply">申请查看</el-button>
        </div>
        <el-table v-loading="requestsLoading" :data="myRequestsList" border stripe>
          <el-table-column prop="sensitive_data_type" label="资料类型" width="120">
            <template #default="{ row }">
              <el-tag :type="SENSITIVE_DATA_TYPE_MAP[row.sensitive_data_type]?.tagType as any" size="small">
                {{ row.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[row.sensitive_data_type]?.label || row.sensitive_data_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="ACCESS_REQUEST_STATUS_MAP[row.status]?.tagType as any" size="small">
                {{ ACCESS_REQUEST_STATUS_MAP[row.status]?.label || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="申请时间" width="120">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="剩余时间" width="100">
            <template #default="{ row }">
              <span v-if="row.status === 'approved' && !isExpired(row)" class="remaining-time">
                {{ getRemainingTime(row.access_expires_at) }}
              </span>
              <span v-else-if="row.status === 'approved' && isExpired(row)" class="text-expired">已过期</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'approved' && !isExpired(row)"
                type="primary"
                link
                @click="handleViewData(row as any)"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 待我审批 Tab -->
      <el-tab-pane label="待我审批" name="pending">
        <div v-permission="['sens_approver', 'sys_admin']">
          <el-table v-loading="pendingLoading" :data="pendingList" border stripe>
            <el-table-column prop="applicant_name" label="申请人" width="110" />
            <el-table-column prop="sensitive_data_type" label="资料类型" width="120">
              <template #default="{ row }">
                <el-tag :type="SENSITIVE_DATA_TYPE_MAP[row.sensitive_data_type]?.tagType as any" size="small">
                  {{ row.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[row.sensitive_data_type]?.label || row.sensitive_data_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />
            <el-table-column prop="is_download" label="需下载" width="80" align="center">
              <template #default="{ row }">{{ row.is_download ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button type="success" link @click="handleApprove(row as any)">批准</el-button>
                <el-button type="danger" link @click="handleReject(row as any)">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 申请弹窗 -->
    <el-dialog v-model="applyDialogVisible" title="申请查看敏感资料" width="600px" @close="handleCloseApply">
      <el-form ref="applyFormRef" :model="applyForm" :rules="applyRules" label-width="110px">
        <el-form-item label="敏感资料" prop="sensitive_data">
          <el-select v-model="applyForm.sensitive_data" placeholder="请选择敏感资料" filterable style="width: 100%">
            <el-option
              v-for="d in sensitiveDataOptions"
              :key="d.id"
              :label="d.title"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="使用场景" prop="usage_scenario">
          <el-input v-model="applyForm.usage_scenario" placeholder="请描述使用场景" />
        </el-form-item>
        <el-form-item label="申请理由" prop="reason">
          <el-input v-model="applyForm.reason" type="textarea" :rows="3" placeholder="请输入申请理由" />
        </el-form-item>
        <el-form-item label="所属项目">
          <el-select v-model="applyForm.project" placeholder="可选" clearable filterable style="width: 100%">
            <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计使用时间">
          <el-date-picker v-model="applyForm.expected_use_time" type="datetime" placeholder="选择时间" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="是否需要下载">
          <el-switch v-model="applyForm.is_download" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="applyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitApply">提交申请</el-button>
      </template>
    </el-dialog>

    <!-- 批准弹窗 -->
    <el-dialog v-model="approveDialogVisible" title="批准访问申请" width="420px">
      <el-form :model="approveForm" label-width="100px">
        <el-form-item label="有效时长(小时)">
          <el-input-number v-model="approveForm.expire_hours" :min="1" :max="24" />
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

    <!-- 驳回弹窗 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回访问申请" width="420px">
      <el-form :model="rejectForm" label-width="100px">
        <el-form-item label="驳回理由">
          <el-input v-model="rejectForm.approval_opinion" type="textarea" :rows="2" placeholder="请输入驳回理由" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="handleConfirmReject">确认驳回</el-button>
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
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getMySensitiveData,
  getSensitiveData,
  getMyAccessRequests,
  getPendingApproveRequests,
  createAccessRequest,
  approveAccessRequest,
  rejectAccessRequest,
} from '@/api/sensitive'
import { getMembers } from '@/api/members'
import { getProjects } from '@/api/projects'
import { formatDate } from '@/utils/format'
import { SENSITIVE_DATA_TYPE_MAP, ACCESS_REQUEST_STATUS_MAP } from '@/utils/constants'
import PageHeader from '@/components/PageHeader.vue'
import SensitiveViewDialog from './SensitiveViewDialog.vue'
import type { SensitiveData, SensitiveAccessRequest } from '@/types'

const activeTab = ref('my-data')
const myDataLoading = ref(false)
const requestsLoading = ref(false)
const pendingLoading = ref(false)
const submitting = ref(false)

const myDataList = ref<SensitiveData[]>([])
const myRequestsList = ref<SensitiveAccessRequest[]>([])
const pendingList = ref<SensitiveAccessRequest[]>([])
const memberOptions = ref<any[]>([])
const projectOptions = ref<any[]>([])
const sensitiveDataOptions = ref<any[]>([])

// 弹窗状态
const applyDialogVisible = ref(false)
const approveDialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const viewDialogVisible = ref(false)
const applyFormRef = ref<FormInstance>()

const viewingRequest = ref<SensitiveAccessRequest | null>(null)

// 申请表单
const applyForm = reactive({
  sensitive_data: undefined as number | undefined,
  usage_scenario: '',
  reason: '',
  project: undefined as number | undefined,
  expected_use_time: '',
  is_download: false,
})

const applyRules = {
  sensitive_data: [{ required: true, message: '请选择敏感资料', trigger: 'change' }],
  usage_scenario: [{ required: true, message: '请描述使用场景', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入申请理由', trigger: 'blur' }],
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

// 判断是否过期
function isExpired(row: any): boolean {
  if (!row.access_expires_at) return false
  return new Date(row.access_expires_at).getTime() < Date.now()
}

// 实时倒计时：每秒更新当前时间
const now = ref(Date.now())
let countdownTimer: ReturnType<typeof setInterval> | null = null

// 计算剩余时间（格式：Xm Ys）
function getRemainingTime(expiresAt: string | undefined): string {
  if (!expiresAt) return '-'
  const diff = new Date(expiresAt).getTime() - now.value
  if (diff <= 0) return '已过期'
  const m = Math.floor(diff / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  if (m > 0) return `${m}分${s}秒`
  return `${s}秒`
}

// Tab 切换
function handleTabChange(tab: any): void {
  if (tab === 'my-data' && myDataList.value.length === 0) loadMyData()
  if (tab === 'requests' && myRequestsList.value.length === 0) loadMyRequests()
  if (tab === 'pending' && pendingList.value.length === 0) loadPending()
}

// 加载我的资料
async function loadMyData(): Promise<void> {
  myDataLoading.value = true
  try {
    const res: any = await getMySensitiveData()
    myDataList.value = Array.isArray(res) ? res : (res.results || [])
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
    const res: any = await getMyAccessRequests()
    myRequestsList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    requestsLoading.value = false
  }
}

// 加载待审批
async function loadPending(): Promise<void> {
  pendingLoading.value = true
  try {
    const res: any = await getPendingApproveRequests()
    pendingList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    pendingLoading.value = false
  }
}

// 加载选项数据
async function loadOptions(): Promise<void> {
  try {
    const [membersRes, projectsRes, sensitiveRes] = await Promise.all([
      getMembers({ page: 1, page_size: 999 }),
      getProjects({ page: 1, page_size: 999 }),
      getSensitiveData({ page: 1, page_size: 999 }),
    ])
    memberOptions.value = (membersRes as any).results || []
    projectOptions.value = (projectsRes as any).results || []
    sensitiveDataOptions.value = (sensitiveRes as any).results || []
  } catch {
    // 忽略
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
function handleViewData(row: any): void {
  viewingRequest.value = row as SensitiveAccessRequest
  viewDialogVisible.value = true
}

// 批准
function handleApprove(row: any): void {
  currentRequest.value = row as SensitiveAccessRequest
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
function handleReject(row: any): void {
  currentRequest.value = row as SensitiveAccessRequest
  rejectForm.approval_opinion = ''
  rejectDialogVisible.value = true
}

// 确认驳回
async function handleConfirmReject(): Promise<void> {
  if (!currentRequest.value) return
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

onMounted(() => {
  loadMyData()
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
.tabs-card {
  padding: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

/* 剩余时间倒计时 */
.remaining-time {
  color: #e6a23c;
  font-weight: 600;
  font-size: 13px;
}

.text-expired {
  color: #c0c4cc;
  font-size: 13px;
}
</style>
