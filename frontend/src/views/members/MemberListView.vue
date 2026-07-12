<template>
  <div class="page-container">
    <PageHeader title="人员管理" subtitle="团队成员信息管理" />

    <!-- 搜索筛选 -->
    <div class="card search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="queryParams.search"
            placeholder="姓名/手机号"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="queryParams.grade" placeholder="年级" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="专业">
          <el-input v-model="queryParams.major" placeholder="专业" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 成员列表表格（PC 端）/ 卡片列表（移动端） -->
    <div class="card mt-16">
      <!-- PC 端：表格 -->
      <el-table
        v-if="!isCardView"
        v-loading="loading"
        :data="memberList"
        border
        stripe
        @row-click="handleRowClick"
      >
        <el-table-column label="姓名" width="180">
          <template #default="{ row }">
            <AvatarWithName :name="row.name" :avatar-url="row.avatar" :size="36" />
          </template>
        </el-table-column>
        <el-table-column prop="global_role_display" label="角色" width="100" />
        <el-table-column prop="grade" label="年级" width="80" />
        <el-table-column prop="major" label="专业" width="150" show-overflow-tooltip />
        <el-table-column prop="phone" label="联系方式" width="130" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="handleDetail(row as Member)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 移动端：卡片列表 -->
      <div v-else v-loading="loading" class="mobile-card-list">
        <div
          v-for="card in cardData"
          :key="card.raw.id"
          class="mobile-card"
          role="button"
          tabindex="0"
          @click="handleDetail(card.raw)"
          @keydown.enter="handleDetail(card.raw)"
        >
          <div class="mobile-card-header">
            <AvatarWithName :name="card.title" :avatar-url="card.avatar" :size="40" />
            <el-tag
              v-if="card.raw.global_role_display"
              size="small"
              type="info"
            >
              {{ card.raw.global_role_display }}
            </el-tag>
          </div>
          <div class="mobile-card-fields">
            <div v-for="field in card.fields" :key="field.label" class="mobile-card-field">
              <span class="field-label">{{ field.label }}</span>
              <span class="field-value">{{ field.value }}</span>
            </div>
          </div>
        </div>
        <el-empty v-if="cardData.length === 0 && !loading" description="暂无成员" />
      </div>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getMembers, type MemberQueryParams } from '@/api/members'
import { useMobileList } from '@/composables/useMobileList'
import { useMobileNavigate } from '@/composables/useMobileNavigate'
import type { Member } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import AvatarWithName from '@/components/AvatarWithName.vue'

// 移动端智能跳转：列表跳详情
const { smartNavigate } = useMobileNavigate()
const loading = ref(false)
const memberList = ref<Member[]>([])
const total = ref(0)

// 移动端列表优化：PC 端表格 / 移动端卡片
const { isCardView, cardData } = useMobileList<Member>(memberList, {
  title: (item) => item.name || item.user_name || '未命名',
  avatar: (item) => item.avatar,
  fields: (item) => [
    {
      label: '角色',
      value: item.global_role_display || '-',
      type: 'text',
    },
    {
      label: '年级',
      value: item.grade || '-',
      type: 'text',
    },
    {
      label: '专业',
      value: item.major || '-',
      type: 'text',
    },
    {
      label: '联系方式',
      value: item.phone || '-',
      type: 'text',
    },
    {
      label: '邮箱',
      value: item.email || '-',
      type: 'text',
    },
  ],
})

const queryParams = reactive<MemberQueryParams>({
  page: 1,
  page_size: 10,
  search: '',
  grade: '',
  major: '',
})

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res = await getMembers(queryParams)
    memberList.value = res.results
    total.value = res.count
  } catch {
    // 已处理
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
  queryParams.page = 1
  loadData()
}

function handleDetail(row: Member): void {
  // 移动端 push 跳转详情；PC 端亦 push（如需新窗口可传 openNew=true）
  smartNavigate(`/members/${row.id}`)
}

function handleRowClick(row: Member): void {
  handleDetail(row)
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.mt-16 { margin-top: 16px; }
.search-bar { padding: 16px; }
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ===================== 移动端卡片列表 ===================== */
.mobile-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;

  &:active {
    transform: scale(0.99);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .mobile-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 12px;
  }

  .mobile-card-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;

    .mobile-card-field {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;

      .field-label {
        color: #909399;
      }

      .field-value {
        color: #303133;
        font-weight: 500;
      }
    }
  }
}
</style>
