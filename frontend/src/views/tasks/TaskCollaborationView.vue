<template>
  <div class="page-container collaboration-page">
    <PageHeader
      :title="task?.title || '任务协作详情'"
      :subtitle="task ? `${task.project_name || '所属项目'} · ${task.assignee_name || '未分配负责人'}` : '检查清单、依赖关系与协作讨论'"
    >
      <template #actions>
        <el-button :icon="ArrowLeft" @click="router.back()">返回</el-button>
        <el-button v-if="task" :icon="FolderOpened" @click="openProject">项目详情</el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="loadError"
      class="load-alert"
      :title="loadError"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button type="primary" link @click="loadWorkspace">重新加载</el-button>
      </template>
    </el-alert>

    <div v-loading="loading" class="task-collaboration-shell">
      <section v-if="task" class="task-summary" aria-label="任务摘要">
        <div>
          <span>状态</span>
          <el-tag :type="getTaskStatusTagType(task.status) as any" size="small">
            {{ getTaskStatusLabel(task.status) }}
          </el-tag>
        </div>
        <div>
          <span>优先级</span>
          <strong>{{ task.priority_display || getTaskPriorityLabel(task.priority || 'medium') }}</strong>
        </div>
        <div>
          <span>截止时间</span>
          <strong>{{ formatDateTime(task.deadline) }}</strong>
        </div>
        <div>
          <span>协作进度</span>
          <strong>{{ completedSubTasks }}/{{ subTasks.length }} 项完成</strong>
        </div>
      </section>

      <el-tabs v-if="task" v-model="activeTab" class="collaboration-tabs">
        <el-tab-pane name="checklist">
          <template #label>
            <span class="tab-label"><List />检查清单 <small>{{ subTasks.length }}</small></span>
          </template>
          <section class="workspace-section">
            <header class="section-heading">
              <div>
                <h2>任务拆解</h2>
                <p>按执行顺序维护可验证的子任务。</p>
              </div>
              <el-button v-if="canManage" type="primary" :icon="Plus" @click="openSubTaskDialog()">
                添加子任务
              </el-button>
            </header>

            <el-progress
              v-if="subTasks.length"
              class="checklist-progress"
              :percentage="subTaskProgress"
              :stroke-width="8"
            />
            <EmptyState
              v-if="!subTasks.length"
              text="暂无子任务"
              description="将任务拆解为可分配、可完成的检查项"
              accent="var(--color-primary)"
            />
            <div v-else class="checklist">
              <article v-for="item in subTasks" :key="item.id" class="checklist-item">
                <el-checkbox
                  :model-value="item.is_completed"
                  :aria-label="`${item.is_completed ? '取消完成' : '完成'} ${item.title}`"
                  @change="toggleChecklistItem(item)"
                />
                <div class="checklist-copy" :class="{ 'is-done': item.is_completed }">
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.assignee_name || '未分配' }} · 顺序 {{ item.sort_order }}</span>
                </div>
                <div v-if="canManage" class="item-actions">
                  <el-tooltip content="编辑子任务">
                    <el-button circle :icon="Edit" aria-label="编辑子任务" @click="openSubTaskDialog(item)" />
                  </el-tooltip>
                  <el-tooltip content="删除子任务">
                    <el-button circle plain type="danger" :icon="Delete" aria-label="删除子任务" @click="removeSubTask(item)" />
                  </el-tooltip>
                </div>
              </article>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane name="dependencies">
          <template #label>
            <span class="tab-label"><Connection />前置依赖 <small>{{ dependencies.length }}</small></span>
          </template>
          <section class="workspace-section">
            <header class="section-heading">
              <div>
                <h2>前置任务</h2>
                <p>当前任务需要等待以下任务完成。</p>
              </div>
              <el-button
                v-if="canManage"
                type="primary"
                :icon="Plus"
                :disabled="!dependencyOptions.length"
                @click="dependencyDialogVisible = true"
              >
                添加依赖
              </el-button>
            </header>
            <EmptyState
              v-if="!dependencies.length"
              text="暂无前置依赖"
              description="该任务当前可独立推进"
              accent="var(--color-success)"
            />
            <div v-else class="dependency-list">
              <article v-for="item in dependencies" :key="item.id" class="dependency-item">
                <div class="dependency-icon"><Connection /></div>
                <div>
                  <strong>{{ item.depends_on_title }}</strong>
                  <span>任务 #{{ item.depends_on }}</span>
                </div>
                <el-button
                  v-if="canManage"
                  type="danger"
                  link
                  :icon="Delete"
                  @click="removeDependency(item)"
                >
                  移除
                </el-button>
              </article>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane name="comments">
          <template #label>
            <span class="tab-label"><ChatDotRound />讨论 <small>{{ rootComments.length }}</small></span>
          </template>
          <section class="workspace-section comments-section">
            <header class="section-heading">
              <div>
                <h2>协作讨论</h2>
                <p>记录决策、问题和交付反馈。</p>
              </div>
            </header>

            <div class="comment-composer">
              <div class="composer-tools">
                <el-select
                  v-model="mentionUserId"
                  placeholder="@ 项目成员"
                  clearable
                  filterable
                  size="small"
                  @change="insertMention"
                >
                  <el-option v-for="member in members" :key="member.id" :label="member.name" :value="member.id" />
                </el-select>
              </div>
              <el-input
                v-model="commentDraft"
                type="textarea"
                :rows="3"
                maxlength="2000"
                show-word-limit
                placeholder="写下进展、问题或反馈"
                @keydown.ctrl.enter="submitComment()"
              />
              <el-button
                type="primary"
                :icon="Promotion"
                :loading="commentSubmitting"
                :disabled="!commentDraft.trim()"
                @click="submitComment()"
              >
                发表评论
              </el-button>
            </div>

            <EmptyState
              v-if="!rootComments.length"
              text="暂无讨论"
              description="发布第一条进展或问题"
              accent="var(--color-primary)"
            />
            <div v-else class="comment-list">
              <article v-for="comment in rootComments" :key="comment.id" class="comment-thread">
                <div class="comment-row">
                  <el-avatar :size="34">{{ initial(comment.author_name) }}</el-avatar>
                  <div class="comment-body">
                    <header>
                      <strong>{{ comment.author_name || '成员' }}</strong>
                      <span>{{ formatDateTime(comment.created_at) }}</span>
                    </header>
                    <p>{{ comment.content }}</p>
                    <div class="comment-actions">
                      <el-button type="primary" link @click="beginReply(comment.id)">回复</el-button>
                      <el-button v-if="canModifyComment(comment)" link @click="openCommentEdit(comment)">编辑</el-button>
                      <el-button v-if="canModifyComment(comment)" type="danger" link @click="removeComment(comment)">删除</el-button>
                    </div>
                  </div>
                </div>

                <div v-for="reply in comment.replies || []" :key="reply.id" class="comment-row reply-row">
                  <el-avatar :size="28">{{ initial(reply.author_name) }}</el-avatar>
                  <div class="comment-body">
                    <header>
                      <strong>{{ reply.author_name || '成员' }}</strong>
                      <span>{{ formatDateTime(reply.created_at) }}</span>
                    </header>
                    <p>{{ reply.content }}</p>
                    <div v-if="canModifyComment(reply)" class="comment-actions">
                      <el-button link @click="openCommentEdit(reply)">编辑</el-button>
                      <el-button type="danger" link @click="removeComment(reply)">删除</el-button>
                    </div>
                  </div>
                </div>

                <div v-if="replyingTo === comment.id" class="reply-composer">
                  <el-input v-model="replyDraft" placeholder="回复该讨论" @keyup.enter="submitComment(comment.id)" />
                  <el-button type="primary" :loading="commentSubmitting" @click="submitComment(comment.id)">发送</el-button>
                  <el-button @click="cancelReply">取消</el-button>
                </div>
              </article>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>

      <EmptyState
        v-else-if="!loading && !loadError"
        text="任务不存在"
        description="该任务可能已删除或你无权访问"
        accent="var(--color-danger)"
      />
    </div>

    <el-dialog v-model="subTaskDialogVisible" :title="editingSubTask ? '编辑子任务' : '添加子任务'" width="min(520px, 92vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="saveSubTask">
        <el-form-item label="标题" required>
          <el-input v-model="subTaskForm.title" maxlength="200" show-word-limit autofocus />
        </el-form-item>
        <div class="dialog-grid">
          <el-form-item label="负责人">
            <el-select v-model="subTaskForm.assignee" clearable filterable placeholder="暂不分配">
              <el-option v-for="member in members" :key="member.id" :label="member.name" :value="member.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="subTaskForm.sort_order" :min="0" :max="999" controls-position="right" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="subTaskDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveSubTask">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dependencyDialogVisible" title="添加前置依赖" width="min(520px, 92vw)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="saveDependency">
        <el-form-item label="前置任务" required>
          <el-select v-model="dependencyTaskId" filterable placeholder="选择当前任务需要等待的任务">
            <el-option
              v-for="candidate in dependencyOptions"
              :key="candidate.id"
              :label="candidate.title"
              :value="candidate.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dependencyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveDependency">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="commentEditVisible" title="编辑评论" width="min(560px, 92vw)" destroy-on-close>
      <el-input v-model="commentEditDraft" type="textarea" :rows="4" maxlength="2000" show-word-limit />
      <template #footer>
        <el-button @click="commentEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCommentEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ChatDotRound,
  Connection,
  Delete,
  Edit,
  FolderOpened,
  List,
  Plus,
  Promotion,
} from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import {
  createSubTask,
  createTaskComment,
  createTaskDependency,
  deleteSubTask,
  deleteTaskComment,
  deleteTaskDependency,
  getSubTasks,
  getTask,
  getTaskComments,
  getTaskDependencies,
  getTasksByProject,
  toggleSubTask,
  updateSubTask,
  updateTaskComment,
  type SubTask,
  type TaskComment,
  type TaskDependency,
} from '@/api/tasks'
import { getProject, getProjectMembers } from '@/api/projects'
import { useUserStore } from '@/stores/user'
import { formatDateTime, getTaskPriorityLabel, getTaskStatusLabel, getTaskStatusTagType } from '@/utils/format'
import type { Project, Task, User } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const taskId = Number(route.params.id)

const activeTab = ref('checklist')
const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const task = ref<Task | null>(null)
const project = ref<Project | null>(null)
const subTasks = ref<SubTask[]>([])
const dependencies = ref<TaskDependency[]>([])
const comments = ref<TaskComment[]>([])
const projectTasks = ref<Task[]>([])
const members = ref<User[]>([])

const subTaskDialogVisible = ref(false)
const editingSubTask = ref<SubTask | null>(null)
const subTaskForm = reactive({ title: '', assignee: undefined as number | undefined, sort_order: 0 })
const dependencyDialogVisible = ref(false)
const dependencyTaskId = ref<number>()
const commentDraft = ref('')
const commentSubmitting = ref(false)
const mentionUserId = ref<number>()
const replyingTo = ref<number | null>(null)
const replyDraft = ref('')
const commentEditVisible = ref(false)
const editingComment = ref<TaskComment | null>(null)
const commentEditDraft = ref('')

const canManage = computed(() => {
  const userId = userStore.userInfo?.id
  return ['teacher', 'sys_admin'].includes(userStore.role) || project.value?.leader === userId
})
const completedSubTasks = computed(() => subTasks.value.filter((item) => item.is_completed).length)
const subTaskProgress = computed(() => subTasks.value.length
  ? Math.round(completedSubTasks.value / subTasks.value.length * 100)
  : 0)
const rootComments = computed(() => comments.value.filter((comment) => !comment.parent))
const dependencyOptions = computed(() => {
  const used = new Set(dependencies.value.map((item) => item.depends_on))
  return projectTasks.value.filter((item) => item.id !== taskId && !used.has(item.id))
})

function initial(value?: string): string {
  return value?.trim().slice(0, 1).toUpperCase() || '?'
}

function canModifyComment(comment: TaskComment): boolean {
  return ['teacher', 'sys_admin'].includes(userStore.role)
    || comment.author === userStore.userInfo?.id
}

function openProject(): void {
  if (task.value) router.push({ name: 'ProjectDetail', params: { id: task.value.project } })
}

async function loadWorkspace(): Promise<void> {
  if (!Number.isInteger(taskId) || taskId <= 0) {
    loadError.value = '任务编号无效'
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const detail = await getTask(taskId)
    task.value = detail
    const [projectDetail, subTaskPage, dependencyPage, commentPage, tasks, memberships] = await Promise.all([
      getProject(detail.project),
      getSubTasks({ parent: taskId, page_size: 100, ordering: 'sort_order' }),
      getTaskDependencies({ task: taskId, page_size: 100 }),
      getTaskComments({ task: taskId, page_size: 100, ordering: 'created_at' }),
      getTasksByProject(detail.project),
      getProjectMembers(detail.project),
    ])
    project.value = projectDetail
    subTasks.value = subTaskPage.results
    dependencies.value = dependencyPage.results
    comments.value = commentPage.results
    projectTasks.value = tasks
    members.value = memberships
      .filter((membership) => membership.status !== 'exited')
      .map((membership) => membership.user_detail as User)
      .filter(Boolean)
  } catch {
    loadError.value = '协作数据加载失败，请检查访问权限或网络连接。'
  } finally {
    loading.value = false
  }
}

async function refreshSubTasks(): Promise<void> {
  const response = await getSubTasks({ parent: taskId, page_size: 100, ordering: 'sort_order' })
  subTasks.value = response.results
}

async function refreshDependencies(): Promise<void> {
  const response = await getTaskDependencies({ task: taskId, page_size: 100 })
  dependencies.value = response.results
}

async function refreshComments(): Promise<void> {
  const response = await getTaskComments({ task: taskId, page_size: 100, ordering: 'created_at' })
  comments.value = response.results
}

function openSubTaskDialog(item?: SubTask): void {
  editingSubTask.value = item || null
  subTaskForm.title = item?.title || ''
  subTaskForm.assignee = item?.assignee || undefined
  subTaskForm.sort_order = item?.sort_order ?? subTasks.value.length
  subTaskDialogVisible.value = true
}

async function saveSubTask(): Promise<void> {
  if (!subTaskForm.title.trim()) {
    ElMessage.warning('请输入子任务标题')
    return
  }
  saving.value = true
  try {
    const payload = {
      parent: taskId,
      title: subTaskForm.title.trim(),
      assignee: subTaskForm.assignee || null,
      sort_order: subTaskForm.sort_order,
    }
    if (editingSubTask.value) await updateSubTask(editingSubTask.value.id, payload)
    else await createSubTask(payload)
    ElMessage.success(editingSubTask.value ? '子任务已更新' : '子任务已添加')
    subTaskDialogVisible.value = false
    await refreshSubTasks()
  } catch {
    // 请求层统一展示错误。
  } finally {
    saving.value = false
  }
}

async function toggleChecklistItem(item: SubTask): Promise<void> {
  try {
    await toggleSubTask(item.id)
    await refreshSubTasks()
  } catch {
    // 请求层统一展示错误。
  }
}

async function removeSubTask(item: SubTask): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除子任务“${item.title}”吗？`, '删除子任务', { type: 'warning' })
    await deleteSubTask(item.id)
    ElMessage.success('子任务已删除')
    await refreshSubTasks()
  } catch {
    // 用户取消或请求失败。
  }
}

async function saveDependency(): Promise<void> {
  if (!dependencyTaskId.value) {
    ElMessage.warning('请选择前置任务')
    return
  }
  saving.value = true
  try {
    await createTaskDependency({ task: taskId, depends_on: dependencyTaskId.value })
    ElMessage.success('前置依赖已添加')
    dependencyDialogVisible.value = false
    dependencyTaskId.value = undefined
    await refreshDependencies()
  } catch {
    // 后端会返回循环依赖等具体原因。
  } finally {
    saving.value = false
  }
}

async function removeDependency(item: TaskDependency): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定移除对“${item.depends_on_title}”的依赖吗？`, '移除依赖', { type: 'warning' })
    await deleteTaskDependency(item.id)
    ElMessage.success('依赖已移除')
    await refreshDependencies()
  } catch {
    // 用户取消或请求失败。
  }
}

function insertMention(userId: number | undefined): void {
  const member = members.value.find((item) => item.id === userId)
  if (member) commentDraft.value += `${commentDraft.value && !commentDraft.value.endsWith(' ') ? ' ' : ''}@${member.name || member.username} `
  mentionUserId.value = undefined
}

function beginReply(commentId: number): void {
  replyingTo.value = commentId
  replyDraft.value = ''
}

function cancelReply(): void {
  replyingTo.value = null
  replyDraft.value = ''
}

async function submitComment(parent?: number): Promise<void> {
  const content = (parent ? replyDraft.value : commentDraft.value).trim()
  if (!content) return
  commentSubmitting.value = true
  try {
    await createTaskComment({ task: taskId, content, parent: parent || null })
    if (parent) cancelReply()
    else commentDraft.value = ''
    ElMessage.success(parent ? '回复已发布' : '评论已发布')
    await refreshComments()
  } catch {
    // 请求层统一展示错误。
  } finally {
    commentSubmitting.value = false
  }
}

function openCommentEdit(comment: TaskComment): void {
  editingComment.value = comment
  commentEditDraft.value = comment.content
  commentEditVisible.value = true
}

async function saveCommentEdit(): Promise<void> {
  if (!editingComment.value || !commentEditDraft.value.trim()) return
  saving.value = true
  try {
    await updateTaskComment(editingComment.value.id, { content: commentEditDraft.value.trim() })
    ElMessage.success('评论已更新')
    commentEditVisible.value = false
    await refreshComments()
  } catch {
    // 请求层统一展示错误。
  } finally {
    saving.value = false
  }
}

async function removeComment(comment: TaskComment): Promise<void> {
  try {
    await ElMessageBox.confirm('确定删除这条评论吗？', '删除评论', { type: 'warning' })
    await deleteTaskComment(comment.id)
    ElMessage.success('评论已删除')
    await refreshComments()
  } catch {
    // 用户取消或请求失败。
  }
}

onMounted(loadWorkspace)
</script>

<style lang="scss" scoped>
.collaboration-page {
  padding-bottom: 32px;
}

.load-alert {
  margin-bottom: 16px;
}

.task-collaboration-shell {
  min-height: 520px;
}

.task-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.task-summary > div {
  display: flex;
  min-width: 0;
  min-height: 78px;
  padding: 14px 18px;
  flex-direction: column;
  justify-content: center;
  gap: 7px;
  border-right: 1px solid var(--color-border-light);
}

.task-summary > div:last-child {
  border-right: 0;
}

.task-summary span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.task-summary strong {
  overflow: hidden;
  color: var(--color-text);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collaboration-tabs {
  padding: 0 18px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.tab-label svg {
  width: 15px;
}

.tab-label small {
  min-width: 20px;
  padding: 1px 6px;
  color: var(--color-text-muted);
  text-align: center;
  background: var(--color-surface-subtle);
  border-radius: 8px;
}

.workspace-section {
  min-height: 390px;
  padding-top: 8px;
}

.section-heading {
  display: flex;
  margin-bottom: 18px;
  padding-bottom: 14px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.section-heading h2 {
  color: var(--color-text);
  font-size: 17px;
  font-weight: 600;
}

.section-heading p {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.checklist-progress {
  margin-bottom: 16px;
}

.checklist,
.dependency-list,
.comment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checklist-item,
.dependency-item {
  display: flex;
  min-height: 58px;
  padding: 10px 12px;
  align-items: center;
  gap: 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.checklist-copy,
.dependency-item > div:nth-child(2) {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}

.checklist-copy strong,
.dependency-item strong {
  overflow-wrap: anywhere;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.checklist-copy span,
.dependency-item span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.checklist-copy.is-done strong {
  color: var(--color-text-muted);
  text-decoration: line-through;
}

.item-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 6px;
}

.dependency-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);
}

.dependency-icon svg {
  width: 17px;
}

.comment-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  margin-bottom: 20px;
  padding: 14px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.composer-tools {
  grid-column: 1 / -1;
}

.composer-tools .el-select {
  width: 180px;
}

.comment-thread {
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.comment-row {
  display: flex;
  gap: 10px;
}

.comment-body {
  min-width: 0;
  flex: 1;
}

.comment-body header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.comment-body header strong {
  color: var(--color-text);
  font-size: 13px;
}

.comment-body header span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.comment-body p {
  margin-top: 6px;
  overflow-wrap: anywhere;
  color: var(--color-text-regular);
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.comment-actions {
  display: flex;
  margin-top: 4px;
  gap: 2px;
}

.reply-row {
  margin: 12px 0 0 44px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.reply-composer {
  display: flex;
  margin: 12px 0 0 44px;
  gap: 8px;
}

.dialog-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  gap: 14px;
}

@media screen and (max-width: 768px) {
  .task-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .task-summary > div:nth-child(2) {
    border-right: 0;
  }

  .task-summary > div:nth-child(-n + 2) {
    border-bottom: 1px solid var(--color-border-light);
  }

  .collaboration-tabs {
    padding: 0 12px 14px;
  }

  .section-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .comment-composer {
    grid-template-columns: 1fr;
  }

  .reply-row,
  .reply-composer {
    margin-left: 20px;
  }

  .reply-composer {
    align-items: stretch;
    flex-direction: column;
  }

  .dialog-grid {
    grid-template-columns: 1fr;
  }
}
</style>
