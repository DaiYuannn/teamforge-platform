<template>
  <div class="page-container">
    <!-- 顶部：返回 + 成果名称 + 状态Tag + 内部编号 -->
    <div class="detail-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      <h2 class="detail-title">{{ application?.title || '申请详情' }}</h2>
      <el-tag v-if="application" :type="getStatusColor(application.status)" effect="dark">
        {{ IP_STATUS_MAP[application.status]?.label || application.status }}
      </el-tag>
      <span v-if="application" class="detail-code">编号：{{ application.application_code }}</span>
    </div>

    <!-- 状态步骤条 -->
    <div v-if="application" class="card">
      <IPStatusStepper :current-status="application.status" />
    </div>

    <!-- 责任分工一览 -->
    <el-card v-if="application" class="responsibility-overview" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-header-title">责任分工一览</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :xs="12" :sm="8" :md="4" v-for="role in responsibilityRoles" :key="role.key">
          <div class="role-card" :style="{ borderTopColor: role.color }">
            <el-icon class="role-icon" :style="{ color: role.color }"><component :is="role.icon" /></el-icon>
            <div class="role-label">{{ role.label }}</div>
            <div class="role-name" :style="{ color: role.name ? '#303133' : '#c0c4cc' }">
              {{ role.name || '未分配' }}
            </div>
            <div class="role-desc">{{ role.desc }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- Tab 页 -->
    <el-tabs v-model="activeTab" class="detail-tabs" @tab-change="handleTabChange">
      <!-- Tab1: 基础信息 -->
      <el-tab-pane label="基础信息" name="info">
        <div v-loading="loading" class="card tab-card">
          <el-descriptions :column="isMobile ? 1 : 2" border>
            <el-descriptions-item label="成果名称">{{ application?.title }}</el-descriptions-item>
            <el-descriptions-item label="内部编号">{{ application?.application_code }}</el-descriptions-item>
            <el-descriptions-item label="成果类型">
              <el-tag :type="getTypeColor(application?.ip_type || '')" size="small">
                {{ IP_TYPE_MAP[application?.ip_type || '']?.label || application?.ip_type }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="关联项目">{{ application?.related_project_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="主导撰写人">{{ application?.main_writer_detail?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="申请执行人">{{ application?.applicant_executor_detail?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="材料整理人">{{ application?.material_manager_detail?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="项目审核人">{{ application?.project_reviewer_detail?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="老师确认人">{{ application?.teacher_confirmer_detail?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="退回次数">{{ application?.return_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="开始日期">{{ formatDate(application?.start_date) }}</el-descriptions-item>
            <el-descriptions-item label="提交日期">{{ formatDate(application?.submit_date) }}</el-descriptions-item>
            <el-descriptions-item label="受理日期">{{ formatDate(application?.accepted_date) }}</el-descriptions-item>
            <el-descriptions-item label="授权日期">{{ formatDate(application?.authorized_date) }}</el-descriptions-item>
            <el-descriptions-item label="创建人">{{ application?.created_by_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(application?.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="当前问题" :span="isMobile ? 1 : 2">
              {{ application?.current_problem || '无' }}
            </el-descriptions-item>
            <el-descriptions-item label="成果简介" :span="isMobile ? 1 : 2">
              {{ application?.intro || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- 编辑按钮（项目负责人/老师/管理员可编辑） -->
          <div v-permission="['teacher', 'sys_admin']" class="tab-actions">
            <el-button type="primary" :icon="Edit" @click="handleEdit">编辑基础信息</el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab2: 责任分工 -->
      <el-tab-pane label="责任分工" name="contributors">
        <div class="card tab-card">
          <div class="tab-header">
            <h4 class="section-title">责任分工</h4>
            <el-button
              v-permission="['teacher', 'sys_admin']"
              type="primary"
              :icon="Plus"
              @click="contributorDialogVisible = true"
            >
              添加贡献者
            </el-button>
          </div>
          <el-table :data="contributors" border size="small" v-loading="loading">
            <el-table-column prop="user_detail" label="姓名" width="100">
              <template #default="{ row }">{{ row.user_detail?.name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="role" label="角色" width="130">
              <template #default="{ row }">
                <el-tag size="small">{{ IP_CONTRIBUTOR_ROLE_MAP[row.role] || row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="contribution_description" label="贡献描述" min-width="200" show-overflow-tooltip />
            <el-table-column prop="responsibility_description" label="责任描述" min-width="200" show-overflow-tooltip />
            <el-table-column prop="is_confirmed" label="确认状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_confirmed ? 'success' : 'warning'" size="small">
                  {{ row.is_confirmed ? '已确认' : '待确认' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="confirmed_by_name" label="确认人" width="100">
              <template #default="{ row }">{{ row.confirmed_by_name || '-' }}</template>
            </el-table-column>
            <el-table-column v-permission="['teacher', 'sys_admin']" label="操作" width="100">
              <template #default="{ row }">
                <el-button
                  v-if="!row.is_confirmed"
                  type="success"
                  link
                  @click="handleConfirmContributor(row as IPContributor)"
                >
                  确认
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="contributors.length === 0" description="暂无贡献者" />
        </div>
      </el-tab-pane>

      <!-- Tab3: 材料版本 -->
      <el-tab-pane label="材料版本" name="materials">
        <div class="card tab-card">
          <div class="tab-header">
            <h4 class="section-title">材料版本</h4>
            <el-upload
              :show-file-list="false"
              :auto-upload="false"
              :on-change="handleMaterialUpload"
            >
              <el-button type="primary" :icon="Upload">上传材料</el-button>
            </el-upload>
          </div>
          <el-table :data="materials" border size="small" v-loading="loading">
            <el-table-column prop="file_asset_name" label="文件名" min-width="200" show-overflow-tooltip />
            <el-table-column prop="material_type" label="材料类型" width="140">
              <template #default="{ row }">
                <el-tag size="small">{{ IP_MATERIAL_TYPE_MAP[row.material_type] || row.material_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column prop="uploaded_by_name" label="上传人" width="100" />
            <el-table-column prop="change_note" label="变更说明" min-width="180" show-overflow-tooltip />
            <el-table-column prop="is_final" label="最终版" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.is_final" type="success" size="small">最终</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="120">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="materials.length === 0" description="暂无材料" />
        </div>
      </el-tab-pane>

      <!-- Tab4: 申请流程 -->
      <el-tab-pane label="申请流程" name="process">
        <div class="card tab-card">
          <h4 class="section-title">申请流程时间线</h4>
          <el-timeline v-if="processTimeline.length > 0">
            <el-timeline-item
              v-for="(item, index) in processTimeline"
              :key="index"
              :timestamp="formatDateTime(item.time)"
              placement="top"
              :type="item.type as any"
            >
              <div class="timeline-content">
                <span class="timeline-title">{{ item.title }}</span>
                <p v-if="item.description" class="timeline-desc">{{ item.description }}</p>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无流程记录" />
        </div>
      </el-tab-pane>

      <!-- Tab5: 退回记录 -->
      <el-tab-pane label="退回记录" name="returns">
        <div class="card tab-card">
          <div class="tab-header">
            <h4 class="section-title">退回记录</h4>
            <el-button
              v-permission="['teacher', 'sys_admin']"
              type="primary"
              :icon="Plus"
              @click="returnDialogVisible = true"
            >
              创建退回记录
            </el-button>
          </div>
          <div v-loading="loading">
            <!-- 退回历史时间线 -->
            <el-timeline v-if="returnTimeline.length > 0" class="return-timeline">
              <el-timeline-item
                v-for="(item, index) in returnTimeline"
                :key="index"
                :timestamp="formatDateTime(item.time)"
                placement="top"
                :type="item.type as any"
                :hollow="item.hollow"
              >
                <div class="return-timeline-content">
                  <div class="return-timeline-title">
                    <el-tag :type="item.tagType as any" size="small" effect="dark">{{ item.title }}</el-tag>
                  </div>
                  <div v-for="field in item.fields" :key="field.label" class="return-timeline-field">
                    <span class="field-label">{{ field.label }}：</span>
                    <span class="field-value">{{ field.value }}</span>
                  </div>
                  <!-- 完成修改按钮 -->
                  <el-button
                    v-if="item.showResolve"
                    type="primary"
                    size="small"
                    @click="handleResolveReturn(item.record)"
                  >
                    完成修改
                  </el-button>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无退回记录" />
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab6: 贡献同步 -->
      <el-tab-pane label="贡献同步" name="contribution">
        <div class="card tab-card">
          <div class="tab-header">
            <h4 class="section-title">贡献同步</h4>
            <el-button
              v-permission="['teacher', 'sys_admin']"
              type="primary"
              :icon="Refresh"
              :loading="syncing"
              @click="handleSyncContribution"
            >
              同步贡献
            </el-button>
          </div>
          <el-table :data="contributors" border size="small">
            <el-table-column prop="user_detail" label="贡献人" width="120">
              <template #default="{ row }">{{ row.user_detail?.name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="role" label="角色" width="130">
              <template #default="{ row }">
                {{ IP_CONTRIBUTOR_ROLE_MAP[row.role] || row.role }}
              </template>
            </el-table-column>
            <el-table-column prop="contribution_description" label="贡献内容" min-width="200" show-overflow-tooltip />
            <el-table-column prop="is_confirmed" label="同步状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_confirmed ? 'success' : 'info'" size="small">
                  {{ row.is_confirmed ? '已同步' : '待同步' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="contributors.length === 0" description="暂无贡献记录" />
        </div>
      </el-tab-pane>

      <!-- Tab7: 异议反馈 -->
      <el-tab-pane label="异议反馈" name="objections">
        <div class="card tab-card">
          <div class="tab-header">
            <h4 class="section-title">异议反馈</h4>
            <el-button type="primary" :icon="ChatDotRound" @click="objectionDialogVisible = true">
              提交异议
            </el-button>
          </div>
          <div v-loading="loading">
            <el-card
              v-for="obj in objections"
              :key="obj.id"
              class="objection-card"
              shadow="hover"
            >
              <div class="objection-header">
                <el-tag size="small" :type="objectionStatusColor(obj.status)">
                  {{ IP_OBJECTION_STATUS_MAP[obj.status]?.label || obj.status }}
                </el-tag>
                <el-tag size="small" type="info">
                  {{ IP_OBJECTION_TYPE_MAP[obj.objection_type] || obj.objection_type }}
                </el-tag>
                <span class="objection-objector">异议人：{{ obj.objector_detail?.name || '-' }}</span>
              </div>
              <div class="objection-content">{{ obj.content }}</div>
              <div v-if="obj.leader_opinion" class="objection-opinion">
                <span class="label">负责人意见：</span>{{ obj.leader_opinion }}
              </div>
              <div v-if="obj.teacher_opinion" class="objection-opinion">
                <span class="label">老师意见：</span>{{ obj.teacher_opinion }}
              </div>
              <div v-if="obj.final_result" class="objection-opinion">
                <span class="label">最终结果：</span>{{ obj.final_result }}
              </div>
              <div class="objection-actions">
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
                  type="success"
                  size="small"
                  @click="handleReviewObjection(obj, 'teacher')"
                >
                  老师确认
                </el-button>
              </div>
            </el-card>
            <el-empty v-if="objections.length === 0" description="暂无异议" />
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab8: 操作日志 -->
      <el-tab-pane label="操作日志" name="logs">
        <div class="card tab-card">
          <h4 class="section-title">操作日志</h4>
          <el-timeline v-if="processTimeline.length > 0">
            <el-timeline-item
              v-for="(item, index) in processTimeline"
              :key="index"
              :timestamp="formatDateTime(item.time)"
              placement="top"
            >
              <span>{{ item.title }}</span>
              <p v-if="item.description" class="timeline-desc">{{ item.description }}</p>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无操作日志" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 退回记录弹窗 -->
    <IPReturnFormDialog
      v-model:visible="returnDialogVisible"
      :application-id="applicationId"
      @success="loadDetail"
    />

    <!-- 异议提交弹窗 -->
    <IPObjectionFormDialog
      v-model:visible="objectionDialogVisible"
      :application-id="applicationId"
      @success="loadDetail"
    />

    <!-- 异议处理弹窗 -->
    <IPObjectionReviewDialog
      v-model:visible="objectionReviewDialogVisible"
      :objection="reviewingObjection"
      :review-mode="reviewMode"
      @success="loadDetail"
    />

    <!-- 添加贡献者弹窗 -->
    <el-dialog v-model="contributorDialogVisible" title="添加贡献者" width="500px">
      <el-form ref="contributorFormRef" :model="contributorForm" :rules="contributorRules" label-width="100px">
        <el-form-item label="贡献人" prop="user">
          <el-select v-model="contributorForm.user" placeholder="请选择贡献人" filterable style="width: 100%">
            <el-option
              v-for="user in userList"
              :key="user.id"
              :label="user.name || user.username || user.email"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="contributorForm.role" placeholder="请选择角色" style="width: 100%">
            <el-option
              v-for="(label, key) in IP_CONTRIBUTOR_ROLE_MAP"
              :key="key"
              :label="label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="贡献描述" prop="contribution_description">
          <el-input v-model="contributorForm.contribution_description" type="textarea" :rows="2" placeholder="请输入贡献描述" />
        </el-form-item>
        <el-form-item label="责任描述" prop="responsibility_description">
          <el-input v-model="contributorForm.responsibility_description" type="textarea" :rows="2" placeholder="请输入责任描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="contributorDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAddContributor">确定</el-button>
      </template>
    </el-dialog>

    <!-- 材料上传弹窗 -->
    <el-dialog v-model="materialDialogVisible" title="上传材料" width="500px">
      <el-form ref="materialFormRef" :model="materialForm" :rules="materialRules" label-width="100px">
        <el-form-item label="文件">
          <span class="material-filename">{{ pendingFile?.name }}</span>
        </el-form-item>
        <el-form-item label="材料类型" prop="material_type">
          <el-select v-model="materialForm.material_type" placeholder="请选择材料类型" style="width: 100%">
            <el-option
              v-for="(label, key) in IP_MATERIAL_TYPE_MAP"
              :key="key"
              :label="label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="变更说明" prop="change_note">
          <el-input v-model="materialForm.change_note" type="textarea" :rows="2" placeholder="请输入变更说明" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { ArrowLeft, Plus, Edit, Upload, Refresh, ChatDotRound } from '@element-plus/icons-vue'
import {
  getIPApplication,
  syncIPContribution,
  resolveIPReturn,
  addIPContributor,
  updateIPContributor,
  uploadIPMaterial,
} from '@/api/intellectualProperty'
import { getUsers } from '@/api/users'
import { formatDate, formatDateTime } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import {
  IP_TYPE_MAP,
  IP_STATUS_MAP,
  IP_CONTRIBUTOR_ROLE_MAP,
  IP_MATERIAL_TYPE_MAP,
  IP_OBJECTION_TYPE_MAP,
  IP_OBJECTION_STATUS_MAP,
  IP_RETURN_SOURCE_MAP,
  IP_RETURN_RESULT_MAP,
  IP_RESPONSIBILITY_TYPE_MAP,
} from '@/utils/constants'
import { useUserStore } from '@/stores/user'
import type { IPApplication, IPContributor, IPReturnRecord, IPMaterialVersion, IPObjection } from '@/types/intellectualProperty'
import type { User } from '@/types'
import IPStatusStepper from './components/IPStatusStepper.vue'
import ReturnRecordCard from './components/ReturnRecordCard.vue'
import IPReturnFormDialog from './IPReturnFormDialog.vue'
import IPObjectionFormDialog from './IPObjectionFormDialog.vue'
import IPObjectionReviewDialog from './IPObjectionReviewDialog.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { isMobile } = useDevice()

const applicationId = Number(route.params.id)

const loading = ref(false)
const submitting = ref(false)
const syncing = ref(false)
const activeTab = ref('info')
const application = ref<IPApplication | null>(null)
const contributors = ref<IPContributor[]>([])
const materials = ref<IPMaterialVersion[]>([])
const returnRecords = ref<IPReturnRecord[]>([])
const objections = ref<IPObjection[]>([])
const userList = ref<User[]>([])

// 弹窗控制
const returnDialogVisible = ref(false)
const objectionDialogVisible = ref(false)
const objectionReviewDialogVisible = ref(false)
const contributorDialogVisible = ref(false)
const materialDialogVisible = ref(false)

// 异议审核相关
const reviewingObjection = ref<IPObjection>({} as IPObjection)
const reviewMode = ref<'leader' | 'teacher'>('leader')

// 贡献者表单
const contributorFormRef = ref<FormInstance>()
const contributorForm = reactive({
  user: null as number | null,
  role: '',
  contribution_description: '',
  responsibility_description: '',
})
const contributorRules: FormRules = {
  user: [{ required: true, message: '请选择贡献人', trigger: 'change' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

// 材料上传表单
const materialFormRef = ref<FormInstance>()
const pendingFile = ref<File | null>(null)
const materialForm = reactive({
  material_type: '',
  change_note: '',
})
const materialRules: FormRules = {
  material_type: [{ required: true, message: '请选择材料类型', trigger: 'change' }],
}

// 权限判断
const canResolveReturn = computed(() => {
  return userStore.role === 'teacher' || userStore.role === 'sys_admin'
})
const canLeaderReview = computed(() => {
  return userStore.role === 'teacher' || userStore.role === 'sys_admin'
})
const canTeacherConfirm = computed(() => {
  return userStore.role === 'teacher' || userStore.role === 'sys_admin'
})

// 申请流程时间线（从申请数据中构建）
const processTimeline = computed(() => {
  if (!application.value) return []
  const app = application.value
  const timeline: { time: string; title: string; description?: string; type?: string }[] = []

  // 创建申请
  if (app.created_at) {
    timeline.push({ time: app.created_at, title: '申请创建', description: `创建人：${app.created_by_name || '-'}`, type: 'primary' })
  }
  // 开始日期
  if (app.start_date) {
    timeline.push({ time: app.start_date, title: '开始撰写', type: 'info' })
  }
  // 提交日期
  if (app.submit_date) {
    timeline.push({ time: app.submit_date, title: '提交申请', type: 'info' })
  }
  // 退回记录
  returnRecords.value.forEach((r) => {
    timeline.push({
      time: r.return_time,
      title: `申请退回 - ${r.return_reason}`,
      description: `责任人：${r.responsible_user_name || '-'}`,
      type: 'danger',
    })
  })
  // 受理日期
  if (app.accepted_date) {
    timeline.push({ time: app.accepted_date, title: '申请受理', type: 'success' })
  }
  // 授权日期
  if (app.authorized_date) {
    timeline.push({ time: app.authorized_date, title: '授权/登记', type: 'success' })
  }

  // 按时间排序
  return timeline.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
})

// 责任分工一览角色数据
const responsibilityRoles = computed(() => {
  if (!application.value) return []
  const app = application.value
  // 从贡献者列表中查找协作撰写人
  const coWriter = contributors.value.find((c) => c.role === 'co_writer')
  return [
    { key: 'main_writer', label: '主导撰写人', name: app.main_writer_detail?.name, desc: '对成果内容真实性负责', color: '#409EFF', icon: 'Edit' },
    { key: 'co_writer', label: '协作撰写人', name: coWriter?.user_detail?.name, desc: '协助撰写', color: '#36CFC9', icon: 'EditPen' },
    { key: 'applicant_executor', label: '申请执行人', name: app.applicant_executor_detail?.name, desc: '对科研处对接负责', color: '#E6A23C', icon: 'Promotion' },
    { key: 'material_manager', label: '材料整理人', name: app.material_manager_detail?.name, desc: '对材料完整性负责', color: '#9B59B6', icon: 'FolderOpened' },
    { key: 'project_reviewer', label: '项目负责人', name: app.project_reviewer_detail?.name, desc: '初审', color: '#67C23A', icon: 'User' },
    { key: 'teacher_confirmer', label: '老师确认人', name: app.teacher_confirmer_detail?.name, desc: '最终确认', color: '#F56C6C', icon: 'Avatar' },
  ]
})

// 退回记录时间线（红色节点=退回，绿色节点=修改完成）
const returnTimeline = computed(() => {
  const items: any[] = []
  returnRecords.value.forEach((r) => {
    // 退回节点（红色）
    items.push({
      time: r.return_time,
      type: 'danger',
      hollow: false,
      title: `退回 - ${IP_RETURN_SOURCE_MAP[r.return_source] || r.return_source}`,
      tagType: 'danger',
      fields: [
        { label: '退回原因', value: r.return_reason },
        { label: '责任类型', value: IP_RESPONSIBILITY_TYPE_MAP[r.responsibility_type] || r.responsibility_type },
        { label: '责任人', value: r.responsible_user_name || '-' },
        { label: '修改截止', value: r.modify_deadline ? formatDate(r.modify_deadline) : '-' },
      ],
      showResolve: false,
      record: r,
    })
    // 修改完成节点（绿色）
    if (r.result !== 'pending') {
      items.push({
        time: r.updated_at,
        type: 'success',
        hollow: false,
        title: '修改完成',
        tagType: 'success',
        fields: [
          { label: '修改人', value: r.actual_modifier_name || '-' },
          { label: '修改说明', value: r.modify_description || '-' },
          { label: '结果', value: IP_RETURN_RESULT_MAP[r.result]?.label || r.result },
        ],
        showResolve: false,
        record: r,
      })
    } else if (canResolveReturn.value) {
      // 待修改且当前用户可操作，显示完成修改按钮
      items[items.length - 1].showResolve = true
    }
  })
  // 按时间排序
  return items.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
})

// 加载申请详情
async function loadDetail(): Promise<void> {
  loading.value = true
  try {
    const res = await getIPApplication(applicationId) as any
    application.value = res
    contributors.value = res.contributors || []
    materials.value = res.material_versions || []
    returnRecords.value = res.return_records || []
    objections.value = res.objections || []
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 加载用户列表
async function loadUsers(): Promise<void> {
  try {
    const res = await getUsers({ page: 1, page_size: 999 }) as any
    userList.value = res.results || []
  } catch {
    // 忽略
  }
}

// Tab切换
function handleTabChange(tabName: any): void {
  // 详情已在 loadDetail 中全部加载，无需额外请求
}

// 编辑基础信息
function handleEdit(): void {
  router.push(`/intellectual-property/create?id=${applicationId}`)
}

// 确认贡献者
async function handleConfirmContributor(row: IPContributor): Promise<void> {
  try {
    await updateIPContributor(row.id, { is_confirmed: true })
    ElMessage.success('已确认贡献者')
    loadDetail()
  } catch {
    // 错误已由拦截器处理
  }
}

// 添加贡献者
async function handleAddContributor(): Promise<void> {
  if (!contributorFormRef.value) return
  await contributorFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await addIPContributor(applicationId, { ...contributorForm })
      ElMessage.success('贡献者添加成功')
      contributorDialogVisible.value = false
      contributorFormRef.value?.resetFields()
      loadDetail()
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 材料上传文件选择
function handleMaterialUpload(file: UploadFile): void {
  pendingFile.value = file.raw || null
  materialDialogVisible.value = true
}

// 执行材料上传
async function handleUploadMaterial(): Promise<void> {
  if (!materialFormRef.value || !pendingFile.value) return
  await materialFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const formData = new FormData()
      formData.append('file', pendingFile.value!)
      formData.append('material_type', materialForm.material_type)
      formData.append('change_note', materialForm.change_note)
      await uploadIPMaterial(applicationId, formData)
      ElMessage.success('材料上传成功')
      materialDialogVisible.value = false
      materialFormRef.value?.resetFields()
      pendingFile.value = null
      loadDetail()
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 解决退回记录
async function handleResolveReturn(record: IPReturnRecord): Promise<void> {
  try {
    const { value } = await ElMessageBox.prompt('请输入修改说明', '完成修改', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputType: 'textarea',
    })
    await resolveIPReturn(record.id, { modify_description: value, result: 'modified' })
    ElMessage.success('退回记录已解决')
    loadDetail()
  } catch {
    // 取消或错误
  }
}

// 同步贡献
async function handleSyncContribution(): Promise<void> {
  syncing.value = true
  try {
    await syncIPContribution(applicationId)
    ElMessage.success('贡献同步成功')
    loadDetail()
  } catch {
    // 错误已由拦截器处理
  } finally {
    syncing.value = false
  }
}

// 处理异议审核
function handleReviewObjection(obj: IPObjection, mode: 'leader' | 'teacher'): void {
  reviewingObjection.value = obj
  reviewMode.value = mode
  objectionReviewDialogVisible.value = true
}

// 获取类型Tag颜色
function getTypeColor(type: string): any {
  return (IP_TYPE_MAP[type]?.color || '') as any
}

// 获取状态Tag颜色
function getStatusColor(status: string): any {
  return (IP_STATUS_MAP[status]?.color || '') as any
}

// 获取异议状态颜色
function objectionStatusColor(status: string): any {
  return (IP_OBJECTION_STATUS_MAP[status]?.color || '') as any
}

onMounted(() => {
  loadDetail()
  loadUsers()
})
</script>

<style lang="scss" scoped>
.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;

  .detail-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }

  .detail-code {
    font-size: 13px;
    color: #909399;
  }
}

.detail-tabs {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .tab-card {
    box-shadow: none;
    padding: 0;
  }
}

.tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  color: #303133;
  margin: 0;
}

.tab-actions {
  margin-top: 20px;
  text-align: right;
}

.timeline-content {
  .timeline-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }

  .timeline-desc {
    font-size: 13px;
    color: #606266;
    margin-top: 4px;
  }
}

.objection-card {
  margin-bottom: 16px;

  .objection-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;

    .objection-objector {
      font-size: 13px;
      color: #909399;
    }
  }

  .objection-content {
    font-size: 14px;
    color: #303133;
    margin-bottom: 8px;
    line-height: 1.6;
  }

  .objection-opinion {
    font-size: 13px;
    color: #606266;
    margin-bottom: 4px;

    .label {
      color: #909399;
    }
  }

  .objection-actions {
    margin-top: 12px;
    display: flex;
    gap: 8px;
  }
}

.material-filename {
  font-size: 13px;
  color: #606266;
}

/* ==================== 责任分工一览 ==================== */
.responsibility-overview {
  margin-bottom: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .card-header {
    display: flex;
    align-items: center;

    .card-header-title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }

  .role-card {
    text-align: center;
    padding: 16px 8px;
    border-top: 3px solid #409eff;
    background: #fafbfc;
    border-radius: 6px;
    transition: all 0.2s;
    height: 100%;

    &:hover {
      background: #f0f7ff;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    .role-icon {
      font-size: 28px;
      margin-bottom: 8px;
    }

    .role-label {
      font-size: 13px;
      color: #909399;
      margin-bottom: 4px;
    }

    .role-name {
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 6px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .role-desc {
      font-size: 12px;
      color: #c0c4cc;
      line-height: 1.4;
    }
  }
}

/* ==================== 退回记录时间线 ==================== */
.return-timeline {
  padding: 8px 0;

  .return-timeline-content {
    .return-timeline-title {
      margin-bottom: 8px;
    }

    .return-timeline-field {
      font-size: 13px;
      line-height: 1.8;
      margin-bottom: 2px;

      .field-label {
        color: #909399;
      }

      .field-value {
        color: #303133;
      }
    }

    .el-button {
      margin-top: 8px;
    }
  }
}

@media screen and (max-width: 768px) {
  .detail-header {
    .detail-title {
      font-size: 16px;
    }
  }

  .tab-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
