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

    <!-- 成员列表表格 -->
    <div class="card mt-16">
      <el-table v-loading="loading" :data="memberList" border stripe @row-click="handleRowClick">
        <el-table-column prop="name" label="姓名" width="100" />
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
import { useRouter } from 'vue-router'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getMembers, type MemberQueryParams } from '@/api/members'
import type { Member } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()
const loading = ref(false)
const memberList = ref<Member[]>([])
const total = ref(0)

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
  router.push(`/members/${row.id}`)
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
</style>
