<template>
  <div class="page-container pending-review-page">
    <PageHeader title="待我审核" subtitle="只接收明确分派给你的贡献记录，老师不会默认收到全部待办">
      <template #actions>
        <el-button v-if="projectFilter" :icon="Setting" @click="openReviewerConfig">
          配置项目审核人
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="projectFilter"
      :title="`当前仅显示项目 #${projectFilter} 的待审核贡献`"
      type="info"
      :closable="true"
      show-icon
      @close="clearProjectFilter"
    />

    <section class="review-policy" aria-label="贡献审核规则">
      <div>
        <strong>当前审核方式：一条贡献只交给一名明确审核人</strong>
        <span>不是所有负责人和老师逐级审核；各项目可以单独配置审核人池，团队讨论后只需调整配置。</span>
      </div>
      <dl>
        <div><dt>普通成员</dt><dd>按审核池优先级分派</dd></div>
        <div><dt>负责人自报</dt><dd>必须交独立审核人</dd></div>
        <div><dt>利益回避</dt><dd>贡献人和代填人不能自审</dd></div>
      </dl>
    </section>

    <section class="review-summary" aria-label="待审核贡献摘要">
      <div>
        <span>待处理</span>
        <strong :class="{ 'is-warning': pendingList.length > 0 }">{{ pendingList.length }}</strong>
      </div>
      <dl>
        <div>
          <dt>涉及项目</dt>
          <dd>{{ projectCount }}</dd>
        </div>
        <div>
          <dt>提交成员</dt>
          <dd>{{ memberCount }}</dd>
        </div>
      </dl>
    </section>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="待审核贡献暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <section v-loading="loading" class="review-surface" aria-label="待审核贡献列表">
      <el-table v-if="!isMobile" :data="pendingList" table-layout="fixed">
        <template #empty>
          <EmptyState
            v-if="!loading"
            text="暂无待审核贡献"
            description="当前负责项目的贡献均已处理"
          />
        </template>
        <el-table-column label="状态" width="86">
          <template #default>
            <span class="pending-status"><i />待审核</span>
          </template>
        </el-table-column>
        <el-table-column label="项目 / 成员" min-width="190">
          <template #default="{ row }">
            <div class="submitter-cell">
              <strong>{{ row.project_name || '-' }}</strong>
              <span>{{ row.user_name || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="贡献类型" width="116">
          <template #default="{ row }">
            <el-tag :type="typeTagType(row.contribution_type) as any" size="small" effect="plain">
              {{ typeLabel(row.contribution_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="证据来源" width="116">
          <template #default="{ row }">
            <el-tag :type="row.source_verified ? 'success' : 'info'" size="small" effect="plain">
              {{ row.source_type_display || sourceTypeLabel(row.source_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="贡献内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="提交时间" width="118">
          <template #default="{ row }">{{ displayDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="92" fixed="right" align="right">
          <template #default="{ row }">
            <el-button type="primary" link :icon="EditPen" @click="handleReview(row as Contribution)">
              审核
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-review-list">
        <EmptyState
          v-if="!loading && pendingList.length === 0"
          text="暂无待审核贡献"
          description="当前负责项目的贡献均已处理"
          compact
        />
        <article v-for="item in pendingList" :key="item.id" class="review-card">
          <header>
            <div>
              <strong>{{ item.project_name || '-' }}</strong>
              <span>{{ item.user_name || '-' }} · {{ typeLabel(item.contribution_type) }}</span>
            </div>
            <span class="pending-status"><i />待审核</span>
          </header>
          <p>{{ item.content }}</p>
          <footer>
            <span>{{ displayDate(item.created_at) }}</span>
            <el-button type="primary" :icon="EditPen" @click="handleReview(item)">审核</el-button>
          </footer>
        </article>
      </div>
    </section>

    <ContributionReviewDialog
      v-model:visible="reviewDialogVisible"
      :contribution="reviewingContribution"
      @success="loadData"
    />

    <el-dialog v-model="reviewerDialogVisible" title="项目贡献审核人" width="min(680px, 92vw)">
      <el-alert
        title="普通成员的申报按优先级分派；项目负责人自报时，只能分给标记为“独立审核”的其他成员。"
        type="info"
        :closable="false"
        show-icon
      />
      <div class="reviewer-config-form">
        <el-select v-model="reviewerForm.user" filterable placeholder="选择组织内有效成员">
          <el-option
            v-for="member in reviewerCandidates"
            :key="member.id"
            :label="reviewerCandidateLabel(member)"
            :value="member.id"
            :disabled="reviewerAssignments.some((item) => item.user === member.id)"
          />
        </el-select>
        <el-input-number v-model="reviewerForm.priority" :min="1" :max="999" controls-position="right" />
        <el-checkbox v-model="reviewerForm.is_independent">可独立审核负责人申报</el-checkbox>
        <el-button type="primary" :icon="Plus" :loading="reviewerSaving" @click="addReviewer">
          添加
        </el-button>
      </div>
      <el-table v-loading="reviewerLoading" :data="reviewerAssignments" size="small">
        <el-table-column prop="user_name" label="审核人" min-width="130" />
        <el-table-column prop="priority" label="优先级" width="88" />
        <el-table-column label="独立审核" width="96">
          <template #default="{ row }">{{ row.is_independent ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="72" align="right">
          <template #default="{ row }">
            <el-button type="danger" link :icon="Delete" @click="removeReviewer(row.id)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Delete, EditPen, Plus, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  createProjectContributionReviewer,
  deleteProjectContributionReviewer,
  getPendingReview,
  getProjectContributionReviewers,
} from '@/api/contributions'
import { getProjectMembers } from '@/api/projects'
import { getMembers } from '@/api/members'
import { formatDate } from '@/utils/format'
import { CONTRIBUTION_TYPE_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import type {
  Contribution,
  Member,
  ProjectContributionReviewer,
} from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import ContributionReviewDialog from './ContributionReviewDialog.vue'

const { isMobile } = useDevice()
const route = useRoute()
const router = useRouter()
const projectFilter = computed(() => {
  const value = Number(route.query.project_id)
  return Number.isInteger(value) && value > 0 ? value : undefined
})
const requestedContributionId = computed(() => {
  const value = Number(route.query.contribution_id)
  return Number.isInteger(value) && value > 0 ? value : undefined
})
const loading = ref(false)
const loadFailed = ref(false)
const pendingList = ref<Contribution[]>([])
const reviewDialogVisible = ref(false)
const reviewingContribution = ref<Contribution | null>(null)
const reviewerDialogVisible = ref(false)
const reviewerLoading = ref(false)
const reviewerSaving = ref(false)
const reviewerAssignments = ref<ProjectContributionReviewer[]>([])
const reviewerCandidates = ref<Array<Member & { is_project_member?: boolean }>>([])
const reviewerForm = ref({ user: undefined as number | undefined, priority: 100, is_independent: false })
const projectCount = computed(
  () => new Set(pendingList.value.map((item) => item.project)).size,
)
const memberCount = computed(
  () => new Set(pendingList.value.map((item) => item.user)).size,
)

function typeLabel(type: string): string {
  return CONTRIBUTION_TYPE_MAP[type]?.label || type
}

function typeTagType(type: string): string {
  return CONTRIBUTION_TYPE_MAP[type]?.tagType || 'info'
}

function sourceTypeLabel(source?: string): string {
  return {
    manual: '手工登记',
    task: '任务验收',
    competition: '比赛记录',
    ip: '知识产权流程',
    system: '系统证据',
  }[source || 'manual'] || source || '手工登记'
}

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '-'
}

async function loadData(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    pendingList.value = await getPendingReview(
      projectFilter.value ? { project: projectFilter.value } : {},
    )
    if (requestedContributionId.value) {
      const contribution = pendingList.value.find(
        (item) => item.id === requestedContributionId.value,
      )
      if (contribution) handleReview(contribution)
      await router.replace({
        path: '/contributions/pending',
        query: projectFilter.value
          ? { project_id: String(projectFilter.value) }
          : {},
      })
    }
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

function handleReview(contribution: Contribution): void {
  reviewingContribution.value = contribution
  reviewDialogVisible.value = true
}

async function loadReviewerConfig(): Promise<void> {
  if (!projectFilter.value) return
  reviewerLoading.value = true
  try {
    const [reviewers, projectMembers, organizationMembers] = await Promise.all([
      getProjectContributionReviewers(projectFilter.value),
      getProjectMembers(projectFilter.value),
      getMembers({ page: 1, page_size: 500, is_active: true }),
    ])
    reviewerAssignments.value = Array.isArray(reviewers) ? reviewers : reviewers.results
    const projectMemberIds = new Set(
      projectMembers
        .filter((member) => !member.status || member.status === 'active')
        .map((member) => member.user),
    )
    reviewerCandidates.value = organizationMembers.results
      .filter((member) =>
        member.is_active !== false
        && ['active', 'on_leave'].includes(member.membership_status || 'active'),
      )
      .map((member) => ({
        ...member,
        is_project_member: projectMemberIds.has(member.id),
      }))
      .sort((left, right) =>
        Number(Boolean(right.is_project_member)) - Number(Boolean(left.is_project_member))
        || (left.name || '').localeCompare(right.name || '', 'zh-CN'),
      )
  } finally {
    reviewerLoading.value = false
  }
}

function reviewerCandidateLabel(
  member: Member & { is_project_member?: boolean },
): string {
  const scope = member.is_project_member ? '本项目' : '组织内其他小组'
  const detail = [member.school, member.major].filter(Boolean).join(' · ')
  return `${member.name || `成员 ${member.id}`}（${scope}）${detail ? ` · ${detail}` : ''}`
}

async function openReviewerConfig(): Promise<void> {
  reviewerDialogVisible.value = true
  await loadReviewerConfig()
}

async function addReviewer(): Promise<void> {
  if (!projectFilter.value || !reviewerForm.value.user) {
    ElMessage.warning('请选择审核人')
    return
  }
  reviewerSaving.value = true
  try {
    await createProjectContributionReviewer({
      project: projectFilter.value,
      user: reviewerForm.value.user,
      priority: reviewerForm.value.priority,
      is_independent: reviewerForm.value.is_independent,
    })
    reviewerForm.value.user = undefined
    reviewerForm.value.is_independent = false
    await loadReviewerConfig()
    ElMessage.success('贡献审核人已配置')
  } finally {
    reviewerSaving.value = false
  }
}

async function removeReviewer(id: number): Promise<void> {
  await deleteProjectContributionReviewer(id)
  await loadReviewerConfig()
  ElMessage.success('贡献审核人已移除')
}

async function clearProjectFilter(): Promise<void> {
  await router.replace({ path: '/contributions/pending' })
  await loadData()
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.pending-review-page {
  display: flex;
  flex-direction: column;
  gap: 12px;

  :deep(.page-header) {
    margin-bottom: 6px;
  }
}

.review-policy {
  display: grid;
  grid-template-columns: minmax(260px, 1.25fr) minmax(360px, 1fr);
  gap: 20px;
  padding: 14px 18px;
  background: var(--color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: var(--radius-md);

  > div {
    display: grid;
    align-content: center;
    gap: 4px;

    strong { color: var(--color-text); font-size: 13px; }
    span { color: var(--color-text-muted); font-size: 12px; line-height: 1.55; }
  }

  dl {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 0;

    div {
      padding: 0 12px;
      border-left: 1px solid var(--el-color-primary-light-7);
    }

    dt { color: var(--color-text-muted); font-size: 11px; }
    dd { margin: 3px 0 0; color: var(--color-text); font-size: 12px; font-weight: 600; }
  }
}

.review-summary {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  > div {
    display: flex;
    align-items: baseline;
    gap: 10px;

    span {
      color: var(--color-text-muted);
      font-size: 12px;
    }

    strong {
      color: var(--color-text);
      font-size: 24px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;

      &.is-warning {
        color: var(--color-warning);
      }
    }
  }

  dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(90px, 1fr));

    > div {
      padding: 1px 18px;
      text-align: right;
      border-left: 1px solid var(--color-border-light);
    }

    dt {
      color: var(--color-text-muted);
      font-size: 11px;
    }

    dd {
      margin-top: 2px;
      color: var(--color-text);
      font-size: 18px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }
  }
}

.reviewer-config-form {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 120px auto auto;
  gap: 10px;
  align-items: center;
  margin: 14px 0;
}

.load-alert {
  margin-bottom: 0;
}

.review-surface {
  min-height: 220px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  :deep(.el-table::before) {
    display: none;
  }
}

.pending-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-warning);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;

  i {
    width: 6px;
    height: 6px;
    background: var(--color-warning);
    border-radius: 50%;
  }
}

.submitter-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;

  strong {
    overflow: hidden;
    color: var(--color-text);
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.mobile-review-list {
  display: grid;
  gap: 10px;
}

.review-card {
  padding: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  > header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;

    > div {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    strong {
      overflow-wrap: anywhere;
      color: var(--color-text);
      font-size: 14px;
      font-weight: 600;
    }

    span:not(.pending-status) {
      margin-top: 2px;
      color: var(--color-text-muted);
      font-size: 11px;
    }
  }

  > p {
    margin-top: 14px;
    overflow-wrap: anywhere;
    color: var(--color-text-regular);
    font-size: 13px;
    line-height: 1.55;
  }

  > footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-top: 12px;
    margin-top: 14px;
    color: var(--color-text-muted);
    font-size: 11px;
    border-top: 1px solid var(--color-border-light);
  }
}

@media screen and (max-width: 768px) {
  .review-policy {
    grid-template-columns: 1fr;

    dl {
      grid-template-columns: 1fr;
      gap: 8px;

      div {
        padding: 0;
        border-left: 0;
      }
    }
  }

  .reviewer-config-form {
    grid-template-columns: minmax(0, 1fr);
  }
  .review-summary {
    padding: 14px;
  }

  .review-summary dl > div {
    padding: 1px 12px;
  }

  .review-surface {
    overflow: visible;
    background: transparent;
    border: 0;
  }
}

@media screen and (max-width: 420px) {
  .review-summary {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;

    dl {
      width: 100%;

      > div:first-child {
        padding-left: 0;
        border-left: 0;
      }
    }
  }
}
</style>
