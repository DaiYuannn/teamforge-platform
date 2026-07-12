<template>
  <div class="page-container">
    <!-- 返回按钮 + 项目标题 -->
    <div class="detail-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      <h2 class="detail-title">{{ project?.name || '项目详情' }}</h2>
      <el-tag v-if="project" :type="getProjectStatusTagType(project.status) as any">
        {{ getProjectStatusLabel(project.status) }}
      </el-tag>
      <div class="header-actions">
        <el-button type="primary" :icon="Download" :loading="exportingReport" @click="handleExportReport">导出报告</el-button>
      </div>
    </div>

    <!-- Tab 页 -->
    <el-tabs v-model="activeTab" class="detail-tabs" @tab-change="handleTabChange">
      <!-- 档案 Tab -->
      <el-tab-pane label="档案" name="profile">
        <div v-loading="loading" class="card">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="项目编号">{{ project?.code }}</el-descriptions-item>
            <el-descriptions-item label="项目名称">{{ project?.name }}</el-descriptions-item>
            <el-descriptions-item label="负责人">{{ project?.leader_name }}</el-descriptions-item>
            <el-descriptions-item label="当前阶段">
              <el-tag :color="getStageColor(project?.current_stage || '')" effect="dark" size="small">
                {{ project?.current_stage_display || getStageLabel(project?.current_stage || '') }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="开始日期">{{ formatDate(project?.start_date) }}</el-descriptions-item>
            <el-descriptions-item label="预计结束">{{ formatDate(project?.planned_end_date) }}</el-descriptions-item>
            <el-descriptions-item label="项目描述" :span="2">{{ project?.intro || '-' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 项目成员 -->
          <h4 class="section-title">项目成员</h4>
          <el-table :data="members" border size="small">
            <el-table-column prop="user_detail" label="姓名" width="120">
              <template #default="{ row }">{{ row.user_detail?.name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="role_in_project" label="项目角色" width="150" />
            <el-table-column prop="joined_at" label="加入时间">
              <template #default="{ row }">{{ formatDate(row.joined_at) }}</template>
            </el-table-column>
            <el-table-column v-permission="['teacher', 'sys_admin']" label="操作" width="100">
              <template #default="{ row }">
                <el-button type="danger" link @click="handleRemoveMember(row as ProjectMember)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 阶段 Tab -->
      <el-tab-pane label="阶段" name="stage">
        <div class="card">
          <StageStepper
            v-if="project"
            :current-stage="project.current_stage || 1"
            :stage-logs="stageLogs"
          />
        </div>
      </el-tab-pane>

      <!-- 任务 Tab -->
      <el-tab-pane label="任务" name="task">
        <div class="card">
          <TaskBoard
            :tasks="tasks"
            @change-status="handleTaskStatusChange"
            @task-click="handleTaskClick"
          />
        </div>
      </el-tab-pane>

      <!-- 比赛 Tab -->
      <el-tab-pane label="比赛" name="competition">
        <div class="card">
          <div v-loading="competitionLoading">
            <el-empty v-if="!competitionInfo" description="暂无关联比赛数据" />
            <el-descriptions v-else :column="2" border>
              <el-descriptions-item label="比赛名称">{{ competitionInfo?.name || '暂无数据' }}</el-descriptions-item>
              <el-descriptions-item label="比赛级别">
                <el-tag
                  :type="getCompetitionStageTagType(competitionInfo?.level || '') as any"
                  size="small"
                  effect="light"
                  :style="getCompetitionStageTagStyle(competitionInfo?.level || '')"
                >
                  {{ competitionInfo?.level_display || getCompetitionLevelLabel(competitionInfo?.level || '') }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="主办方">{{ competitionInfo?.organizer || '暂无数据' }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="getCompetitionStatusTagType(competitionInfo?.status || '') as any" size="small">
                  {{ competitionInfo?.status_display || getCompetitionStatusLabel(competitionInfo?.status || '') }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="报名日期">{{ competitionInfo?.register_date ? formatDate(competitionInfo.register_date) : '暂无数据' }}</el-descriptions-item>
              <el-descriptions-item label="答辩日期">{{ competitionInfo?.defense_date ? formatDate(competitionInfo.defense_date) : '暂无数据' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-tab-pane>

      <!-- 经费 Tab -->
      <el-tab-pane label="经费" name="finance">
        <div class="card">
          <FinanceTable
            :expenses="expenses"
            :total-budget="totalBudget"
            @edit="handleEditExpense"
            @delete="handleDeleteExpense"
          />
        </div>
      </el-tab-pane>

      <!-- 文件 Tab -->
      <el-tab-pane label="文件" name="file">
        <div class="card">
          <FileUploader
            v-if="project"
            :project-id="project.id"
            @success="loadFiles"
          />
          <el-divider />
          <el-table :data="files" border size="small">
            <el-table-column prop="name" label="文件名" min-width="200" show-overflow-tooltip />
            <el-table-column prop="content_type" label="类型" width="80" />
            <el-table-column prop="size" label="大小" width="100">
              <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
            </el-table-column>
            <el-table-column prop="level" label="级别" width="100">
              <template #default="{ row }">
                <el-tag :type="FILE_LEVEL_MAP[row.level]?.tagType as any" size="small">
                  {{ row.level_display || FILE_LEVEL_MAP[row.level]?.label || row.level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="uploader_name" label="上传者" width="100" />
            <el-table-column prop="created_at" label="上传时间" width="120">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" link @click="handleDownload(row as FileAsset)">下载</el-button>
                <el-button v-permission="['teacher', 'sys_admin']" type="danger" link @click="handleDeleteFile(row as FileAsset)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 成员排序 Tab -->
      <el-tab-pane label="成员排序" name="ranking">
        <div class="card">
          <!-- 排序操作栏 -->
          <div class="ranking-header">
            <h4 class="section-title">成员排序</h4>
            <div>
              <el-button
                v-if="isProjectLeader"
                type="primary"
                :icon="Sort"
                @click="handleGenerateRanking"
              >
                生成排序
              </el-button>
              <el-button
                v-permission="['teacher', 'sys_admin']"
                type="success"
                @click="handleConfirmRanking"
              >
                确认排序
              </el-button>
              <el-button :icon="Download" @click="handleExportReport">导出报告</el-button>
            </div>
          </div>

          <!-- 排序列表 -->
          <el-table v-loading="rankingLoading" :data="rankings" border size="small">
            <el-table-column label="排名" width="100">
              <template #default="{ row }">
                <el-input-number
                  v-if="isProjectLeader && row.status !== 'confirmed'"
                  v-model="row.rank"
                  :min="1"
                  size="small"
                  controls-position="right"
                  style="width: 90px"
                  @change="handleRankChange(row as any)"
                />
                <span v-else>{{ row.rank }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="user_detail" label="成员" width="120">
              <template #default="{ row }">{{ row.user_detail?.name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="total_score" label="得分" width="100" align="center" />
            <el-table-column prop="contribution_count" label="贡献数" width="90" align="center">
              <template #default="{ row }">{{ row.contribution_count || '-' }}</template>
            </el-table-column>
            <el-table-column prop="task_completed_count" label="任务完成数" width="110" align="center" />
            <el-table-column prop="ip_contribution_count" label="IP贡献数" width="100" align="center" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="RANKING_STATUS_MAP[row.status]?.tagType as any" size="small">
                  {{ RANKING_STATUS_MAP[row.status]?.label || row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <el-divider />

          <!-- 异议区域 -->
          <div class="ranking-header">
            <h4 class="section-title">排序异议</h4>
            <el-button type="warning" :icon="ChatDotRound" @click="handleOpenObjection">提交异议</el-button>
          </div>
          <el-table :data="objections" border size="small">
            <el-table-column prop="objector_name" label="异议人" width="100" />
            <el-table-column prop="ranking_user_name" label="异议对象" width="100">
              <template #default="{ row }">{{ row.ranking_user_name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="OBJECTION_STATUS_MAP[row.status]?.tagType as any" size="small">
                  {{ OBJECTION_STATUS_MAP[row.status]?.label || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button
                  v-if="isProjectLeader && row.status === 'pending'"
                  type="primary"
                  link
                  @click="handleReviewObjection(row as any, 'leader')"
                >
                  负责人初审
                </el-button>
                <el-button
                  v-permission="['teacher', 'sys_admin']"
                  v-if="row.status === 'leader_reviewed'"
                  type="success"
                  link
                  @click="handleReviewObjection(row as any, 'teacher')"
                >
                  老师确认
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 时间线 Tab -->
      <el-tab-pane label="时间线" name="timeline">
        <div class="card">
          <ProjectTimeline :project-id="projectId" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 提交异议弹窗 -->
    <el-dialog v-model="objectionDialogVisible" title="提交排序异议" width="500px">
      <el-form ref="objectionFormRef" :model="objectionForm" :rules="objectionRules" label-width="90px">
        <el-form-item label="异议类型" prop="objection_type">
          <el-select v-model="objectionForm.objection_type" placeholder="请选择" style="width: 100%">
            <el-option
              v-for="(label, key) in OBJECTION_TYPE_MAP"
              :key="key"
              :label="label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="异议内容" prop="content">
          <el-input v-model="objectionForm.content" type="textarea" :rows="3" placeholder="请输入异议内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="objectionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="objectionSubmitting" @click="handleSubmitObjection">提交</el-button>
      </template>
    </el-dialog>

    <!-- 异议处理弹窗 -->
    <el-dialog v-model="reviewObjectionVisible" :title="reviewMode === 'leader' ? '负责人初审' : '老师确认'" width="500px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="异议对象">{{ currentObjection?.ranking_user_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="异议内容">{{ currentObjection?.content }}</el-descriptions-item>
      </el-descriptions>
      <el-form class="mt-16" :model="reviewObjectionForm" label-width="90px">
        <el-form-item v-if="reviewMode === 'leader'" label="初审意见">
          <el-input v-model="reviewObjectionForm.leader_opinion" type="textarea" :rows="3" placeholder="请输入初审意见" />
        </el-form-item>
        <template v-else>
          <el-form-item label="负责人意见">
            <span>{{ currentObjection?.leader_opinion || '暂无' }}</span>
          </el-form-item>
          <el-form-item label="老师意见">
            <el-input v-model="reviewObjectionForm.teacher_opinion" type="textarea" :rows="3" placeholder="请输入确认意见" />
          </el-form-item>
          <el-form-item label="处理决定">
            <el-radio-group v-model="reviewObjectionForm.action">
              <el-radio value="resolved">通过</el-radio>
              <el-radio value="rejected">驳回</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="reviewObjectionVisible = false">取消</el-button>
        <el-button type="primary" :loading="objectionSubmitting" @click="handleConfirmReviewObjection">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, Sort, Download, ChatDotRound } from '@element-plus/icons-vue'
import {
  getProject,
  getProjectMembers,
  removeProjectMember,
  getStageLogs,
} from '@/api/projects'
import { getCompetitions, getCompetition } from '@/api/competitions'
import { getTasksByProject, changeTaskStatus } from '@/api/tasks'
import { getFinanceExpensesByProject, deleteFinanceExpense } from '@/api/finance'
import { getFilesByProject, deleteFile, downloadFile } from '@/api/files'
import {
  generateRanking,
  confirmRanking,
  getRankingsByProject,
  updateRank,
  getObjections,
  createObjection,
  leaderReviewObjection,
  teacherConfirmObjection,
} from '@/api/contributions'
import { exportProjectReport } from '@/api/exports'
import { useUserStore } from '@/stores/user'
import {
  formatDate,
  formatFileSize,
  getStageLabel,
  getStageColor,
  getProjectStatusLabel,
  getProjectStatusTagType,
  getCompetitionLevelLabel,
  getCompetitionStageTagType,
  getCompetitionStageTagStyle,
  getCompetitionStatusLabel,
  getCompetitionStatusTagType,
  downloadBlob,
} from '@/utils/format'
import {
  FILE_LEVEL_MAP,
  RANKING_STATUS_MAP,
  OBJECTION_TYPE_MAP,
  OBJECTION_STATUS_MAP,
} from '@/utils/constants'
import type { Project, ProjectMember, StageLog, Competition, Task, FinanceExpense, FileAsset, TaskStatus, MemberRanking, RankingObjection } from '@/types'
import StageStepper from '@/components/StageStepper.vue'
import TaskBoard from '@/components/TaskBoard.vue'
import FinanceTable from '@/components/FinanceTable.vue'
import FileUploader from '@/components/FileUploader.vue'
import ProjectTimeline from '@/components/ProjectTimeline.vue'

const route = useRoute()
const userStore = useUserStore()
const projectId = Number(route.params.id)

const loading = ref(false)
const activeTab = ref('profile')
const project = ref<Project | null>(null)
const members = ref<ProjectMember[]>([])
const stageLogs = ref<StageLog[]>([])
const tasks = ref<Task[]>([])
const competitionInfo = ref<Competition | null>(null)
const competitionLoading = ref(false)
const expenses = ref<FinanceExpense[]>([])
const totalBudget = ref(0)
const files = ref<FileAsset[]>([])

// 导出报告加载状态
const exportingReport = ref(false)

// 排序相关状态
const rankingLoading = ref(false)
const rankings = ref<MemberRanking[]>([])
const objections = ref<RankingObjection[]>([])
const objectionDialogVisible = ref(false)
const objectionSubmitting = ref(false)
const objectionFormRef = ref<FormInstance>()
const objectionForm = reactive({
  objection_type: '',
  content: '',
})
const objectionRules: FormRules = {
  objection_type: [{ required: true, message: '请选择异议类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入异议内容', trigger: 'blur' }],
}

// 异议处理状态
const reviewObjectionVisible = ref(false)
const reviewMode = ref<'leader' | 'teacher'>('leader')
const currentObjection = ref<RankingObjection | null>(null)
const reviewObjectionForm = reactive({
  leader_opinion: '',
  teacher_opinion: '',
  action: 'resolved' as 'resolved' | 'rejected',
})

// 是否项目负责人（当前用户为项目 leader）
const isProjectLeader = computed(() => {
  return userStore.userInfo?.id === project.value?.leader
})

// 加载项目详情
async function loadProject(): Promise<void> {
  loading.value = true
  try {
    project.value = await getProject(projectId)
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

// 加载关联比赛（通过项目 ID 过滤比赛列表）
async function loadCompetitions(): Promise<void> {
  if (competitionInfo.value) return
  competitionLoading.value = true
  try {
    const res = await getCompetitions({ project: projectId, page: 1, page_size: 10 } as any)
    const list = res.results || []
    if (list.length > 0) {
      // 获取第一条比赛的完整详情
      competitionInfo.value = await getCompetition(list[0].id)
    }
  } catch {
    // 忽略
  } finally {
    competitionLoading.value = false
  }
}

// 加载成员
async function loadMembers(): Promise<void> {
  try {
    members.value = await getProjectMembers(projectId)
  } catch {
    // 忽略
  }
}

// 加载阶段日志
async function loadStageLogs(): Promise<void> {
  try {
    stageLogs.value = await getStageLogs(projectId)
  } catch {
    // 忽略
  }
}

// 加载任务
async function loadTasks(): Promise<void> {
  try {
    tasks.value = await getTasksByProject(projectId)
  } catch {
    // 忽略
  }
}

// 加载经费
async function loadExpenses(): Promise<void> {
  try {
    expenses.value = await getFinanceExpensesByProject(projectId)
  } catch {
    // 忽略
  }
}

// 加载文件
async function loadFiles(): Promise<void> {
  try {
    files.value = await getFilesByProject(projectId)
  } catch {
    // 忽略
  }
}

// 加载排序
async function loadRankings(): Promise<void> {
  rankingLoading.value = true
  try {
    const res: any = await getRankingsByProject(projectId)
    rankings.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 忽略
  } finally {
    rankingLoading.value = false
  }
}

// 加载异议
async function loadObjections(): Promise<void> {
  try {
    const res: any = await getObjections({ project: projectId })
    objections.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 忽略
  }
}

// 生成排序
async function handleGenerateRanking(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要生成成员排序吗？', '提示', { type: 'warning' })
    await generateRanking(projectId)
    ElMessage.success('排序已生成')
    loadRankings()
  } catch {
    // 取消
  }
}

// 确认排序
async function handleConfirmRanking(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要确认成员排序吗？确认后不可修改。', '提示', { type: 'warning' })
    await confirmRanking(projectId)
    ElMessage.success('排序已确认')
    loadRankings()
  } catch {
    // 取消
  }
}

// 修改排名
async function handleRankChange(row: any): Promise<void> {
  try {
    await updateRank(row.id, { rank: row.rank })
    ElMessage.success('排名已更新')
  } catch {
    // 错误已处理
    loadRankings()
  }
}

// 打开提交异议弹窗
function handleOpenObjection(): void {
  objectionForm.objection_type = ''
  objectionForm.content = ''
  objectionDialogVisible.value = true
}

// 提交异议
async function handleSubmitObjection(): Promise<void> {
  if (!objectionFormRef.value) return
  await objectionFormRef.value.validate(async (valid) => {
    if (!valid) return
    objectionSubmitting.value = true
    try {
      await createObjection({ ranking: rankings.value[0]?.id, content: objectionForm.content })
      ElMessage.success('异议已提交')
      objectionDialogVisible.value = false
      loadObjections()
    } catch {
      // 错误已处理
    } finally {
      objectionSubmitting.value = false
    }
  })
}

// 打开异议处理弹窗
function handleReviewObjection(row: any, mode: 'leader' | 'teacher'): void {
  currentObjection.value = row as RankingObjection
  reviewMode.value = mode
  reviewObjectionForm.leader_opinion = ''
  reviewObjectionForm.teacher_opinion = ''
  reviewObjectionForm.action = 'resolved'
  reviewObjectionVisible.value = true
}

// 确认处理异议
async function handleConfirmReviewObjection(): Promise<void> {
  if (!currentObjection.value) return
  objectionSubmitting.value = true
  try {
    const data: any = {}
    if (reviewMode.value === 'leader') {
      data.leader_opinion = reviewObjectionForm.leader_opinion
    } else {
      data.teacher_opinion = reviewObjectionForm.teacher_opinion
      data.action = reviewObjectionForm.action
    }
    if (reviewMode.value === 'leader') {
      await leaderReviewObjection(currentObjection.value.id, data)
    } else {
      await teacherConfirmObjection(currentObjection.value.id, data)
    }
    ElMessage.success('处理成功')
    reviewObjectionVisible.value = false
    loadObjections()
  } catch {
    // 错误已处理
  } finally {
    objectionSubmitting.value = false
  }
}

// 导出项目完整报告（Word，使用专用报告接口）
async function handleExportReport(): Promise<void> {
  exportingReport.value = true
  try {
    const res: any = await exportProjectReport(projectId)
    const blobData = res.data ? res.data : res
    downloadBlob(new Blob([blobData]), `项目报告_${project.value?.name || projectId}_${Date.now()}.docx`)
    ElMessage.success('导出成功')
  } catch {
    // 错误已处理
  } finally {
    exportingReport.value = false
  }
}

// Tab 切换
function handleTabChange(tabName: any): void {
  switch (tabName) {
    case 'stage':
      if (!stageLogs.value.length) loadStageLogs()
      break
    case 'task':
      if (!tasks.value.length) loadTasks()
      break
    case 'competition':
      loadCompetitions()
      break
    case 'finance':
      if (!expenses.value.length) loadExpenses()
      break
    case 'file':
      if (!files.value.length) loadFiles()
      break
    case 'ranking':
      loadRankings()
      loadObjections()
      break
    case 'timeline':
      // 时间线组件内部自行加载数据
      break
  }
}

// 任务状态变更（拖拽）
async function handleTaskStatusChange(task: Task, newStatus: TaskStatus): Promise<void> {
  try {
    await changeTaskStatus(task.id, newStatus)
    task.status = newStatus
    ElMessage.success('任务状态已更新')
  } catch {
    // 错误已处理
  }
}

// 任务点击
function handleTaskClick(task: Task): void {
  ElMessage.info(`任务：${task.title}`)
}

// 移除成员
async function handleRemoveMember(member: ProjectMember): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要移除成员「${member.user_detail?.name || member.user_name || ''}」吗？`, '提示', {
      type: 'warning',
    })
    await removeProjectMember(projectId, member.user)
    ElMessage.success('已移除成员')
    loadMembers()
  } catch {
    // 取消
  }
}

// 编辑支出
function handleEditExpense(_expense: FinanceExpense): void {
  ElMessage.info('编辑经费支出功能')
}

// 删除支出
async function handleDeleteExpense(expense: FinanceExpense): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要删除该支出记录吗？', '提示', { type: 'warning' })
    await deleteFinanceExpense(expense.id)
    ElMessage.success('删除成功')
    loadExpenses()
  } catch {
    // 取消
  }
}

// 下载文件
async function handleDownload(file: FileAsset): Promise<void> {
  try {
    const blob = await downloadFile(file.id)
    downloadBlob(blob, file.name)
  } catch {
    ElMessage.error('下载失败')
  }
}

// 删除文件
async function handleDeleteFile(file: FileAsset): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除文件「${file.name}」吗？`, '提示', { type: 'warning' })
    await deleteFile(file.id)
    ElMessage.success('删除成功')
    loadFiles()
  } catch {
    // 取消
  }
}

onMounted(() => {
  loadProject()
  loadMembers()
})
</script>

<style lang="scss" scoped>
.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;

  .detail-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }

  .header-actions {
    margin-left: auto;
  }
}

.detail-tabs {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .card {
    box-shadow: none;
    padding: 0;
  }
}

.section-title {
  font-size: 15px;
  color: #303133;
  margin: 20px 0 12px;
}

.ranking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  .section-title {
    margin: 0;
  }
}

.mt-16 {
  margin-top: 16px;
}
</style>
