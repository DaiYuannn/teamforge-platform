<template>
  <div class="page-container contributions-page">
    <PageHeader title="我的贡献" subtitle="记录项目产出并跟踪审核结果">
      <template #actions>
        <el-dropdown
          :disabled="contributionProjects.length === 0"
          @command="handleExport"
        >
          <el-button :icon="Download">
            导出项目贡献
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="project in contributionProjects"
                :key="project.id"
                :command="project.id"
              >
                {{ project.name }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="primary" :icon="Plus" @click="handleCreate">填写贡献</el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="projectFilter"
      :title="`当前仅显示项目 #${projectFilter} 的贡献记录`"
      type="info"
      :closable="true"
      show-icon
      @close="clearProjectFilter"
    />

    <section class="contribution-summary" aria-label="贡献状态摘要">
      <div class="contribution-summary__intro">
        <span>贡献记录</span>
        <strong>共 {{ contributionList.length }} 条</strong>
      </div>
      <dl>
        <div>
          <dt>待审核</dt>
          <dd :class="{ 'is-warning': pendingCount > 0 }">{{ pendingCount }}</dd>
        </div>
        <div>
          <dt>已通过</dt>
          <dd class="is-success">{{ approvedCount }}</dd>
        </div>
        <div>
          <dt>已驳回</dt>
          <dd :class="{ 'is-danger': rejectedCount > 0 }">{{ rejectedCount }}</dd>
        </div>
      </dl>
    </section>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="贡献记录暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <section v-loading="loading" class="contribution-surface" aria-label="我的贡献列表">
      <el-table v-if="!isMobile" :data="contributionList" table-layout="fixed">
        <template #empty>
          <EmptyState
            v-if="!loading"
            text="暂无贡献记录"
            description="填写贡献后，审核状态会显示在这里"
          >
            <template #action>
              <el-button type="primary" :icon="Plus" @click="handleCreate">填写贡献</el-button>
            </template>
          </EmptyState>
        </template>
        <el-table-column label="状态" width="94">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status) as any" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="项目" min-width="170" show-overflow-tooltip>
          <template #default="{ row }"><strong class="project-name">{{ row.project_name || '-' }}</strong></template>
        </el-table-column>
        <el-table-column label="类型" width="112">
          <template #default="{ row }">
            <el-tag :type="typeTagType(row.contribution_type) as any" size="small" effect="plain">
              {{ typeLabel(row.contribution_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="贡献内容" min-width="240" show-overflow-tooltip />
        <el-table-column label="权重" width="76" align="right">
          <template #default="{ row }">
            <span class="weight-value">{{ row.weight ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="审核时间" width="118">
          <template #default="{ row }">{{ displayDate(row.reviewed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="124" fixed="right" align="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="primary" link :icon="Edit" @click="handleEdit(row as Contribution)">
                编辑
              </el-button>
              <el-button type="danger" link :icon="Delete" @click="handleDelete(row as Contribution)">
                删除
              </el-button>
            </template>
            <span v-else class="no-action">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-contribution-list">
        <EmptyState
          v-if="!loading && contributionList.length === 0"
          text="暂无贡献记录"
          description="填写贡献后，审核状态会显示在这里"
          compact
        />
        <article v-for="item in contributionList" :key="item.id" class="contribution-card">
          <header>
            <div>
              <strong>{{ item.project_name || '-' }}</strong>
              <span>{{ typeLabel(item.contribution_type) }}</span>
            </div>
            <el-tag :type="statusTagType(item.status) as any" size="small">
              {{ statusLabel(item.status) }}
            </el-tag>
          </header>
          <p>{{ item.content }}</p>
          <dl>
            <div>
              <dt>权重</dt>
              <dd>{{ item.weight ?? '-' }}</dd>
            </div>
            <div>
              <dt>审核时间</dt>
              <dd>{{ displayDate(item.reviewed_at) }}</dd>
            </div>
          </dl>
          <footer v-if="item.status === 'pending'">
            <el-button type="primary" link :icon="Edit" @click="handleEdit(item)">编辑</el-button>
            <el-button type="danger" link :icon="Delete" @click="handleDelete(item)">删除</el-button>
          </footer>
        </article>
      </div>
    </section>

    <ContributionFormDialog
      v-model:visible="formDialogVisible"
      :contribution="editingContribution"
      @success="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Delete, Download, Edit, Plus } from '@element-plus/icons-vue'
import { deleteContribution, getMyContributions } from '@/api/contributions'
import { exportData } from '@/api/exports'
import { downloadBlob, formatDate } from '@/utils/format'
import { CONTRIBUTION_STATUS_MAP, CONTRIBUTION_TYPE_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import type { Contribution } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import ContributionFormDialog from './ContributionFormDialog.vue'

const { isMobile } = useDevice()
const route = useRoute()
const router = useRouter()
const projectFilter = computed(() => {
  const value = Number(route.query.project_id)
  return Number.isInteger(value) && value > 0 ? value : undefined
})
const loading = ref(false)
const loadFailed = ref(false)
const contributionList = ref<Contribution[]>([])
const formDialogVisible = ref(false)
const editingContribution = ref<Contribution | null>(null)
const pendingCount = computed(() => contributionList.value.filter((item) => item.status === 'pending').length)
const approvedCount = computed(() => contributionList.value.filter((item) => item.status === 'approved').length)
const rejectedCount = computed(() => contributionList.value.filter((item) => item.status === 'rejected').length)
const contributionProjects = computed(() => {
  const projects = new Map<number, string>()
  contributionList.value.forEach((item) => {
    if (item.project) projects.set(item.project, item.project_name || `项目 ${item.project}`)
  })
  return Array.from(projects, ([id, name]) => ({ id, name }))
})

function typeLabel(type: string): string {
  return CONTRIBUTION_TYPE_MAP[type]?.label || type
}

function typeTagType(type: string): string {
  return CONTRIBUTION_TYPE_MAP[type]?.tagType || 'info'
}

function statusLabel(status: string): string {
  return CONTRIBUTION_STATUS_MAP[status]?.label || status
}

function statusTagType(status: string): string {
  return CONTRIBUTION_STATUS_MAP[status]?.tagType || 'info'
}

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '-'
}

async function loadData(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    contributionList.value = await getMyContributions(
      projectFilter.value ? { project: projectFilter.value } : {},
    )
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

function handleCreate(): void {
  editingContribution.value = null
  formDialogVisible.value = true
}

async function clearProjectFilter(): Promise<void> {
  await router.replace({ path: '/contributions' })
  await loadData()
}

function handleEdit(contribution: Contribution): void {
  editingContribution.value = contribution
  formDialogVisible.value = true
}

async function handleDelete(contribution: Contribution): Promise<void> {
  try {
    await ElMessageBox.confirm('确定删除这条待审核贡献吗？', '删除贡献', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteContribution(contribution.id)
    ElMessage.success('贡献已删除')
    loadData()
  } catch {
    // 用户取消或请求错误已由拦截器处理。
  }
}

async function handleExport(projectId: number): Promise<void> {
  try {
    const blob = await exportData('contributions', 'xlsx', projectId)
    const projectName = contributionProjects.value.find((item) => item.id === projectId)?.name
    downloadBlob(blob, `项目贡献_${projectName || projectId}_${Date.now()}.xlsx`)
    ElMessage.success('导出成功')
  } catch {
    // 请求错误已由拦截器处理。
  }
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.contributions-page {
  display: flex;
  flex-direction: column;
  gap: 12px;

  :deep(.page-header) {
    margin-bottom: 6px;
  }
}

.contribution-summary {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.contribution-summary__intro {
  display: flex;
  flex-direction: column;
  justify-content: center;

  span {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  strong {
    margin-top: 2px;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
  }
}

.contribution-summary dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(78px, 1fr));
  min-width: 280px;

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
    font-size: 20px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;

    &.is-warning {
      color: var(--color-warning);
    }

    &.is-success {
      color: var(--color-success);
    }

    &.is-danger {
      color: var(--color-danger);
    }
  }
}

.load-alert {
  margin-bottom: 0;
}

.contribution-surface {
  min-height: 220px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  :deep(.el-table::before) {
    display: none;
  }
}

.project-name {
  color: var(--color-text);
  font-weight: 600;
}

.weight-value {
  color: var(--color-text-regular);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.no-action {
  color: var(--text-placeholder);
}

.mobile-contribution-list {
  display: grid;
  gap: 10px;
}

.contribution-card {
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

    span {
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

  dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    padding-top: 12px;
    margin-top: 14px;
    border-top: 1px solid var(--color-border-light);
  }

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 2px;
    color: var(--color-text-regular);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }

  > footer {
    display: flex;
    justify-content: flex-end;
    gap: 4px;
    padding-top: 10px;
    margin-top: 12px;
    border-top: 1px solid var(--color-border-light);
  }
}

@media screen and (max-width: 768px) {
  .contribution-summary {
    flex-direction: column;
    gap: 12px;
    padding: 14px;
  }

  .contribution-summary dl {
    width: 100%;
    min-width: 0;

    > div {
      padding: 1px 12px;

      &:first-child {
        padding-left: 0;
        border-left: 0;
      }
    }
  }

  .contribution-surface {
    overflow: visible;
    background: transparent;
    border: 0;
  }
}
</style>
