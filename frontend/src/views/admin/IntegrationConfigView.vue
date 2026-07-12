<template>
  <div class="page-container" v-permission="'sys_admin'">
    <PageHeader title="第三方集成配置" subtitle="管理企业微信、Webhook、邮件等通知渠道">
      <template #actions>
        <el-button type="success" :icon="Promotion" @click="handleTestPush" :loading="pushLoading">测试群机器人推送</el-button>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新增配置</el-button>
        <el-button :icon="Refresh" @click="loadConfigs">刷新</el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab" class="card tabs-card" @tab-change="handleTabChange">
      <!-- 集成配置 Tab -->
      <el-tab-pane label="集成配置" name="configs">
        <el-table v-loading="configLoading" :data="configList" border stripe>
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="provider" label="Provider" width="130">
            <template #default="{ row }">
              <el-tag :type="INTEGRATION_PROVIDER_MAP[row.provider]?.tagType as any" size="small">
                {{ INTEGRATION_PROVIDER_MAP[row.provider]?.label || row.provider }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="webhook_url" label="Webhook地址" min-width="200" show-overflow-tooltip />
          <el-table-column prop="app_id" label="应用ID" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.app_id || '-' }}</template>
          </el-table-column>
          <el-table-column prop="is_enabled" label="启用状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_enabled ? 'success' : 'info' as any" size="small">
                {{ row.is_enabled ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="warning" link @click="handleEdit(row as any)">编辑</el-button>
              <el-button type="danger" link @click="handleDelete(row as any)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 集成日志 Tab -->
      <el-tab-pane label="集成日志" name="logs">
        <el-table v-loading="logLoading" :data="logList" border stripe>
          <el-table-column prop="config_name" label="配置名称" width="140" />
          <el-table-column prop="event_type" label="事件类型" width="140" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="INTEGRATION_LOG_STATUS_MAP[row.status]?.tagType as any" size="small">
                {{ INTEGRATION_LOG_STATUS_MAP[row.status]?.label || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 配置弹窗 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="isEdit ? '编辑配置' : '新增配置'"
      width="560px"
      @close="handleCloseForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入配置名称" />
        </el-form-item>
        <el-form-item label="Provider" prop="provider">
          <el-select v-model="form.provider" placeholder="请选择" style="width: 100%">
            <el-option
              v-for="(item, key) in INTEGRATION_PROVIDER_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Webhook地址" prop="webhook_url">
          <el-input v-model="form.webhook_url" placeholder="请输入Webhook地址" />
        </el-form-item>
        <el-form-item label="应用ID">
          <el-input v-model="form.app_id" placeholder="可选" />
        </el-form-item>
        <el-form-item label="密钥">
          <el-input v-model="form.app_secret" placeholder="可选" show-password />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, Promotion } from '@element-plus/icons-vue'
import {
  getIntegrationConfigs,
  createIntegrationConfig,
  updateIntegrationConfig,
  deleteIntegrationConfig,
  getIntegrationLogs,
  testBotPush,
} from '@/api/integrations'
import { formatDateTime } from '@/utils/format'
import { INTEGRATION_PROVIDER_MAP, INTEGRATION_LOG_STATUS_MAP } from '@/utils/constants'
import PageHeader from '@/components/PageHeader.vue'
import type { IntegrationConfig, IntegrationLog } from '@/types'

const activeTab = ref('configs')
const configLoading = ref(false)
const logLoading = ref(false)
const submitting = ref(false)
const configList = ref<IntegrationConfig[]>([])
const logList = ref<IntegrationLog[]>([])

const formDialogVisible = ref(false)
const formRef = ref<FormInstance>()
const editingId = ref<number | null>(null)

// 是否编辑模式
const isEdit = computed(() => editingId.value !== null)

// 表单数据
const form = reactive({
  name: '',
  provider: '',
  webhook_url: '',
  app_id: '',
  app_secret: '',
  is_enabled: true,
})

// 验证规则
const rules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择Provider', trigger: 'change' }],
  webhook_url: [{ required: true, message: '请输入Webhook地址', trigger: 'blur' }],
}

// Tab 切换
function handleTabChange(tab: any): void {
  if (tab === 'logs' && logList.value.length === 0) loadLogs()
}

// 加载配置列表
async function loadConfigs(): Promise<void> {
  configLoading.value = true
  try {
    const res: any = await getIntegrationConfigs()
    configList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    configLoading.value = false
  }
}

// 加载日志
async function loadLogs(): Promise<void> {
  logLoading.value = true
  try {
    const res: any = await getIntegrationLogs()
    logList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    logLoading.value = false
  }
}

// 新增
function handleCreate(): void {
  editingId.value = null
  Object.assign(form, {
    name: '',
    provider: '',
    webhook_url: '',
    app_id: '',
    app_secret: '',
    is_enabled: true,
  })
  formDialogVisible.value = true
}

// 编辑
function handleEdit(row: any): void {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    provider: row.provider,
    webhook_url: row.webhook_url || '',
    app_id: row.app_id || '',
    app_secret: row.app_secret || '',
    is_enabled: row.is_enabled,
  })
  formDialogVisible.value = true
}

// 提交
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data: any = { ...form }
      if (!data.app_id) delete data.app_id
      if (!data.app_secret) delete data.app_secret
      if (isEdit.value && editingId.value !== null) {
        await updateIntegrationConfig(editingId.value, data)
        ElMessage.success('修改成功')
      } else {
        await createIntegrationConfig(data)
        ElMessage.success('新增成功')
      }
      formDialogVisible.value = false
      loadConfigs()
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 关闭弹窗
function handleCloseForm(): void {
  formRef.value?.resetFields()
  editingId.value = null
}

// 删除
async function handleDelete(row: any): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除配置「${row.name}」吗？`, '提示', { type: 'warning' })
    await deleteIntegrationConfig(row.id)
    ElMessage.success('删除成功')
    loadConfigs()
  } catch {
    // 取消
  }
}

// ============================================
// 群机器人推送测试
// ============================================
const pushLoading = ref(false)

async function handleTestPush() {
  try {
    await ElMessageBox.confirm(
      '将向所有已启用的集成配置发送一条测试消息，确认继续？',
      '测试群机器人推送',
      { type: 'info', confirmButtonText: '发送测试', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  pushLoading.value = true
  try {
    const resp = await testBotPush({
      title: '群机器人推送测试',
      content: '这是一条来自团队管理系统的测试消息，收到此消息说明推送配置正常工作。',
    })
    const data = resp.data || resp
    if (data.total === 0) {
      ElMessage.warning('未找到已启用的集成配置，请先添加并启用企业微信或 Webhook 配置')
    } else {
      ElMessage.success(`推送完成: ${data.success} 成功, ${data.failed} 失败`)
    }
  } catch {
    ElMessage.error('推送测试失败')
  } finally {
    pushLoading.value = false
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style lang="scss" scoped>
.tabs-card {
  padding: 16px;
}
</style>
