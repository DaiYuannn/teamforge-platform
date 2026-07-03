<template>
  <div class="page-container">
    <PageHeader title="文件管理" subtitle="管理所有项目文件" />

    <!-- 搜索筛选 -->
    <div class="card search-bar">
      <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="项目">
          <el-select v-model="queryParams.project" placeholder="全部项目" clearable style="width: 180px" @change="handleSearch">
            <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="权限">
          <el-select v-model="queryParams.level" placeholder="全部" clearable style="width: 120px" @change="handleSearch">
            <el-option
              v-for="(item, key) in FILE_PERMISSION_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 文件列表表格 -->
    <div class="card mt-16">
      <el-table v-loading="loading" :data="fileList" border stripe>
        <el-table-column prop="name" label="文件名" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-icon class="file-icon"><Document /></el-icon>
            {{ row.name }}
          </template>
        </el-table-column>
        <el-table-column prop="project_name" label="所属项目" width="150" show-overflow-tooltip />
        <el-table-column prop="file_type" label="类型" width="80" />
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="permission" label="权限" width="110">
          <template #default="{ row }">
            <el-tag :type="FILE_PERMISSION_MAP[row.permission]?.tagType as any" size="small">
              {{ FILE_PERMISSION_MAP[row.permission]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploader_name" label="上传者" width="100" />
        <el-table-column prop="created_at" label="上传时间" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleDownload(row as FileAsset)">下载</el-button>
            <el-button v-permission="['teacher', 'sys_admin']" type="danger" link @click="handleDelete(row as FileAsset)">删除</el-button>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Document } from '@element-plus/icons-vue'
import { getFiles, deleteFile, downloadFile, type FileQueryParams } from '@/api/files'
import { getProjects } from '@/api/projects'
import { formatDate, formatFileSize, downloadBlob } from '@/utils/format'
import { FILE_PERMISSION_MAP } from '@/utils/constants'
import type { FileAsset, Project } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const loading = ref(false)
const fileList = ref<FileAsset[]>([])
const total = ref(0)
const projectOptions = ref<Project[]>([])

const queryParams = reactive<FileQueryParams>({
  page: 1,
  page_size: 10,
  project: undefined,
  level: undefined,
})

async function loadProjects(): Promise<void> {
  try {
    const res = await getProjects({ page: 1, page_size: 999 })
    projectOptions.value = res.results
  } catch {
    // 忽略
  }
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res = await getFiles(queryParams)
    fileList.value = res.results
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
  queryParams.project = undefined
  queryParams.level = undefined
  queryParams.page = 1
  loadData()
}

async function handleDownload(file: FileAsset): Promise<void> {
  try {
    const blob = await downloadFile(file.id)
    downloadBlob(blob, file.name)
  } catch {
    ElMessage.error('下载失败')
  }
}

async function handleDelete(file: FileAsset): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除文件「${file.name}」吗？`, '提示', { type: 'warning' })
    await deleteFile(file.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // 取消
  }
}

onMounted(() => {
  loadProjects()
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
.file-icon {
  vertical-align: middle;
  margin-right: 4px;
  color: #409eff;
}
</style>
