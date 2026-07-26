<template>
  <div class="page-container member-list-page">
    <PageHeader title="人员管理" subtitle="查看团队成员的角色、专业与联系方式" />

    <section class="filter-panel" aria-label="成员筛选">
      <el-form
        class="filter-form"
        :inline="!isMobile"
        :label-position="isMobile ? 'top' : 'left'"
        :model="queryParams"
        @submit.prevent="handleSearch"
      >
        <el-form-item label="关键词">
          <el-input
            v-model="queryParams.search"
            :prefix-icon="Search"
            placeholder="姓名、手机号或邮箱"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="queryParams.grade" placeholder="全部年级" clearable />
        </el-form-item>
        <el-form-item label="专业">
          <el-input v-model="queryParams.major" placeholder="全部专业" clearable />
        </el-form-item>
        <el-form-item label="成员状态">
          <el-select v-model="queryParams.membership_status" placeholder="全部状态" clearable>
            <el-option label="在队" value="active" />
            <el-option label="暂离" value="on_leave" />
            <el-option label="已离队" value="exited" />
            <el-option label="外部协作者" value="external" />
          </el-select>
        </el-form-item>
        <el-form-item class="filter-actions">
          <el-button type="primary" :icon="Search" native-type="submit">查询</el-button>
          <el-button :icon="Refresh" :disabled="!hasActiveFilters" @click="handleReset">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </section>

    <el-alert
      v-if="loadFailed"
      class="load-alert"
      title="成员数据暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <section v-loading="loading" class="member-surface" aria-label="团队成员列表">
      <header class="surface-heading">
        <div>
          <h2>团队成员</h2>
          <p>共 {{ total }} 人</p>
        </div>
      </header>

      <el-table
        v-if="!isMobile"
        :data="memberList"
        table-layout="fixed"
        class="member-table"
        @row-click="handleRowClick"
      >
        <template #empty>
          <EmptyState v-if="!loading" text="暂无成员" description="没有符合当前条件的成员" />
        </template>
        <el-table-column label="成员" min-width="190">
          <template #default="{ row }">
            <AvatarWithName :name="memberName(row as Member)" :avatar-url="row.avatar" :size="34" />
          </template>
        </el-table-column>
        <el-table-column label="角色" width="106">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.global_role) as any" size="small">
              {{ row.global_role_display || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="成员状态" width="104">
          <template #default="{ row }">
            <el-tag :type="membershipStatusType(row.membership_status)" size="small" effect="plain">
              {{ membershipStatusLabel(row.membership_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="年级 / 专业" min-width="170">
          <template #default="{ row }">
            <div class="academic-cell">
              <span>{{ row.grade || '-' }}</span>
              <span>{{ row.major || '未填写专业' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="联系电话" width="132">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="190" show-overflow-tooltip />
        <el-table-column label="操作" width="86" fixed="right" align="right">
          <template #default="{ row }">
            <el-button type="primary" link :icon="View" @click.stop="handleDetail(row as Member)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-member-list">
        <EmptyState
          v-if="!loading && memberList.length === 0"
          text="暂无成员"
          description="没有符合当前条件的成员"
          compact
        />
        <article
          v-for="member in memberList"
          :key="member.id"
          class="member-card"
          tabindex="0"
          @click="handleDetail(member)"
          @keydown.enter="handleDetail(member)"
        >
          <header class="member-card__header">
            <AvatarWithName :name="memberName(member)" :avatar-url="member.avatar" :size="40" />
            <el-tag :type="roleTagType(member.global_role) as any" size="small">
              {{ member.global_role_display || '-' }}
            </el-tag>
            <el-tag :type="membershipStatusType(member.membership_status)" size="small" effect="plain">
              {{ membershipStatusLabel(member.membership_status) }}
            </el-tag>
          </header>
          <dl class="member-card__details">
            <div>
              <dt>年级</dt>
              <dd>{{ member.grade || '-' }}</dd>
            </div>
            <div>
              <dt>专业</dt>
              <dd>{{ member.major || '-' }}</dd>
            </div>
            <div>
              <dt>电话</dt>
              <dd>{{ member.phone || '-' }}</dd>
            </div>
            <div>
              <dt>邮箱</dt>
              <dd>{{ member.email || '-' }}</dd>
            </div>
          </dl>
          <footer class="member-card__footer">
            <el-button type="primary" link :icon="View" @click.stop="handleDetail(member)">
              查看详情
            </el-button>
          </footer>
        </article>
      </div>

      <div v-if="total > 0" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          :layout="paginationLayout"
          :size="isMobile ? 'small' : 'default'"
          background
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh, Search, View } from '@element-plus/icons-vue'
import { getMembers, type MemberQueryParams } from '@/api/members'
import { useDevice } from '@/composables/useDevice'
import { useMobileNavigate } from '@/composables/useMobileNavigate'
import type { Member } from '@/types'
import AvatarWithName from '@/components/AvatarWithName.vue'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const { isMobile } = useDevice()
const { smartNavigate } = useMobileNavigate()
const loading = ref(false)
const loadFailed = ref(false)
const memberList = ref<Member[]>([])
const total = ref(0)

const queryParams = reactive<MemberQueryParams>({
  page: 1,
  page_size: appStore.itemsPerPage,
  search: '',
  grade: '',
  major: '',
  membership_status: '',
})

const hasActiveFilters = computed(
  () => Boolean(
    queryParams.search || queryParams.grade || queryParams.major || queryParams.membership_status
  ),
)
const paginationLayout = computed(() =>
  isMobile.value ? 'prev, pager, next' : 'total, sizes, prev, pager, next',
)

function memberName(member: Member): string {
  return member.name || member.user_name || member.username || '未命名成员'
}

function roleTagType(role?: string): string {
  if (role === 'sys_admin') return 'danger'
  if (role === 'teacher') return 'warning'
  return 'info'
}

function membershipStatusLabel(value?: string): string {
  return {
    active: '在队',
    on_leave: '暂离',
    exited: '已离队',
    external: '外部协作者',
  }[value || 'active'] || '在队'
}

function membershipStatusType(value?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (value === 'exited') return 'danger'
  if (value === 'on_leave') return 'warning'
  if (value === 'external') return 'info'
  return 'success'
}

async function loadData(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    const response = await getMembers(queryParams)
    memberList.value = response.results
    total.value = response.count
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  queryParams.page = 1
  loadData()
}

function handleReset(): void {
  queryParams.search = ''
  queryParams.grade = ''
  queryParams.major = ''
  queryParams.membership_status = ''
  queryParams.page = 1
  loadData()
}

function handleDetail(member: Member): void {
  smartNavigate(`/members/${member.id}`)
}

function handleRowClick(member: Member): void {
  handleDetail(member)
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.filter-panel,
.member-surface {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.filter-panel {
  padding: 14px 16px 0;
  margin-bottom: 12px;
}

.filter-form {
  :deep(.el-form-item) {
    margin-right: 12px;
    margin-bottom: 14px;
  }

  :deep(.el-input) {
    width: 150px;
  }

  :deep(.el-form-item:first-child .el-input) {
    width: 230px;
  }
}

.filter-actions {
  margin-left: auto;
  margin-right: 0 !important;
}

.load-alert {
  margin-bottom: 12px;
}

.member-surface {
  overflow: hidden;
}

.surface-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border-light);

  h2 {
    color: var(--color-text);
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0;
  }

  p {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
}

.member-table {
  :deep(.el-table::before) {
    display: none;
  }

  :deep(.el-table__row) {
    cursor: pointer;
  }

  :deep(th.el-table__cell) {
    height: 42px;
    background: var(--color-surface-subtle);
  }

  :deep(td.el-table__cell) {
    height: 56px;
  }
}

.academic-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;

  span:first-child {
    color: var(--color-text-regular);
    font-size: 13px;
  }

  span:last-child {
    overflow: hidden;
    color: var(--color-text-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.mobile-member-list {
  display: grid;
  gap: 10px;
}

.member-card {
  padding: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
}

.member-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.member-card__details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  margin-top: 16px;

  dt {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  dd {
    margin-top: 2px;
    overflow-wrap: anywhere;
    color: var(--color-text-regular);
    font-size: 13px;
  }
}

.member-card__footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
  margin-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 0 16px 16px;
  border-top: 1px solid var(--color-border-light);
}

@media screen and (max-width: 768px) {
  .filter-panel {
    padding: 14px;
  }

  .filter-form {
    :deep(.el-form-item) {
      margin-right: 0;
      margin-bottom: 12px;
    }

    :deep(.el-form-item__label) {
      margin-bottom: 5px;
      line-height: 1.2;
    }

    :deep(.el-input),
    :deep(.el-form-item:first-child .el-input) {
      width: 100%;
    }
  }

  .filter-actions {
    margin-bottom: 0 !important;

    :deep(.el-form-item__content) {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    :deep(.el-button) {
      width: 100%;
      margin-left: 0;
    }
  }

  .member-surface {
    overflow: visible;
    background: transparent;
    border: 0;
  }

  .surface-heading {
    padding: 0 0 10px;
    border-bottom: 0;
  }

  .pagination-wrapper {
    justify-content: center;
    padding: 14px 8px 0;
    border-top: 0;
  }
}
</style>
