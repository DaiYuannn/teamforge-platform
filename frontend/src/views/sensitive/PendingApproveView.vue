<template>
  <div class="page-container">
    <PageHeader title="待我审批" subtitle="审批敏感资料查看申请" />

    <div class="card mt-16" v-permission="['sens_approver', 'sys_admin']">
      <el-table v-loading="loading" :data="pendingList" border stripe>
        <el-table-column prop="applicant_name" label="申请人" width="110" />
        <el-table-column prop="sensitive_data_type" label="资料类型" width="130">
          <template #default="{ row }">
            <el-tag :type="SENSITIVE_DATA_TYPE_MAP[row.sensitive_data_type]?.tagType as any" size="small">
              {{ row.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[row.sensitive_data_type]?.label || row.sensitive_data_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="usage_scenario" label="使用场景" min-width="140" show-overflow-tooltip />
        <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />
        <el-table-column prop="is_download" label="需下载" width="80" align="center">
          <template #default="{ row }">{{ row.is_download ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="success" link @click="handleApprove(row as any)">批准</el-button>
            <el-button type="danger" link @click="handleReject(row as any)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 批准弹窗 -->
    <el-dialog v-model="approveDialogVisible" title="批准访问申请" width="420px">
      <el-form :model="approveForm" label-width="110px">
        <el-form-item label="有效时长(小时)">
          <el-input-number v-model="approveForm.expire_hours" :min="1" :max="72" />
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getPendingApproveRequests, approveAccessRequest, rejectAccessRequest } from '@/api/sensitive'
import { formatDate } from '@/utils/format'
import { SENSITIVE_DATA_TYPE_MAP } from '@/utils/constants'
import PageHeader from '@/components/PageHeader.vue'
import type { SensitiveAccessRequest } from '@/types'

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

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getPendingApproveRequests()
    pendingList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
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
.mt-16 {
  margin-top: 16px;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
</style>
