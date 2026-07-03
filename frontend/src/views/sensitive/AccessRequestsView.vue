<template>
  <div class="page-container">
    <PageHeader title="资料查看申请" subtitle="我的敏感资料查看申请">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="handleApply">申请查看</el-button>
      </template>
    </PageHeader>

    <!-- PC端表格 -->
    <div v-if="!isMobile" class="card mt-16">
      <el-table v-loading="loading" :data="requestList" border stripe>
        <el-table-column prop="sensitive_data_type" label="资料类型" width="130">
            <template #default="{ row }">
              <el-tag :type="SENSITIVE_DATA_TYPE_MAP[row.sensitive_data_type]?.tagType as any" size="small">
                {{ row.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[row.sensitive_data_type]?.label || row.sensitive_data_type }}
              </el-tag>
            </template>
          </el-table-column>
        <el-table-column prop="usage_scenario" label="使用场景" min-width="150" show-overflow-tooltip />
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
    </div>

    <!-- 移动端卡片列表 -->
    <div v-else v-loading="loading" class="mobile-list">
      <el-empty v-if="requestList.length === 0" description="暂无申请" />
      <el-card v-for="item in requestList" :key="item.id" class="mobile-card" shadow="hover">
        <div class="mobile-card-header">
          <span class="mobile-card-title">{{ item.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[item.sensitive_data_type || '']?.label || item.sensitive_data_type }}</span>
          <el-tag :type="ACCESS_REQUEST_STATUS_MAP[item.status || '']?.tagType as any" size="small">
            {{ ACCESS_REQUEST_STATUS_MAP[item.status || '']?.label || item.status }}
          </el-tag>
        </div>
        <div class="mobile-card-body">
          <div class="mobile-card-row">
            <el-tag :type="SENSITIVE_DATA_TYPE_MAP[item.sensitive_data_type || '']?.tagType as any" size="small">
              {{ item.sensitive_data_type_display || SENSITIVE_DATA_TYPE_MAP[item.sensitive_data_type || '']?.label || item.sensitive_data_type }}
            </el-tag>
          </div>
          <div class="mobile-card-row"><span class="label">场景：</span><span>{{ item.usage_scenario }}</span></div>
          <div class="mobile-card-row"><span class="label">理由：</span><span>{{ item.reason }}</span></div>
          <div class="mobile-card-row"><span class="label">申请：</span><span>{{ formatDate(item.created_at) }}</span></div>
          <div v-if="item.status === 'approved' && !isExpired(item)" class="mobile-card-row">
            <span class="label">剩余时间：</span>
            <span class="remaining-time">{{ getRemainingTime(item.access_expires_at) }}</span>
          </div>
        </div>
        <div v-if="item.status === 'approved' && !isExpired(item)" class="mobile-card-actions">
          <el-button type="primary" link size="small" @click="handleViewData(item as any)">查看</el-button>
        </div>
      </el-card>
    </div>

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
import { getMyAccessRequests, createAccessRequest, getSensitiveData } from '@/api/sensitive'
import { getProjects } from '@/api/projects'
import { formatDate } from '@/utils/format'
import { SENSITIVE_DATA_TYPE_MAP, ACCESS_REQUEST_STATUS_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import SensitiveViewDialog from './SensitiveViewDialog.vue'
import type { SensitiveAccessRequest } from '@/types'

const { isMobile } = useDevice()

const loading = ref(false)
const submitting = ref(false)
const requestList = ref<SensitiveAccessRequest[]>([])
const projectOptions = ref<any[]>([])
const sensitiveDataOptions = ref<any[]>([])

const applyDialogVisible = ref(false)
const viewDialogVisible = ref(false)
const applyFormRef = ref<FormInstance>()
const viewingRequest = ref<SensitiveAccessRequest | null>(null)

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
  try {
    const [projectsRes, sensitiveRes] = await Promise.all([
      getProjects({ page: 1, page_size: 999 }),
      getSensitiveData({ page: 1, page_size: 999 }),
    ])
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
function handleViewData(row: any): void {
  viewingRequest.value = row as SensitiveAccessRequest
  viewDialogVisible.value = true
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
.mt-16 {
  margin-top: 16px;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
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

/* 移动端样式 */
.mobile-list {
  .mobile-card {
    margin-bottom: 12px;

    .mobile-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;

      .mobile-card-title {
        font-size: 15px;
        font-weight: 600;
        color: #303133;
      }
    }

    .mobile-card-body {
      .mobile-card-row {
        font-size: 13px;
        color: #606266;
        margin-bottom: 4px;

        .label {
          color: #909399;
        }
      }
    }

    .mobile-card-actions {
      margin-top: 8px;
      text-align: right;
    }
  }
}
</style>
