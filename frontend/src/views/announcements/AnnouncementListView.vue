<template>
  <div class="announcement-list">
    <PageHeader title="公告管理" />

    <el-card shadow="never">
      <div class="toolbar">
        <el-select v-model="filterCategory" placeholder="全部分类" clearable style="width: 160px">
          <el-option label="系统公告" value="system" />
          <el-option label="项目公告" value="project" />
          <el-option label="活动公告" value="activity" />
          <el-option label="其他" value="other" />
        </el-select>
        <el-button v-if="canCreate" type="primary" @click="showDialog = true">发布公告</el-button>
      </div>

      <el-table v-loading="loading" :data="announcements" style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <el-icon v-if="row.is_pinned" color="#E6A23C"><Top /></el-icon>
            {{ row.title }}
          </template>
        </el-table-column>
        <el-table-column prop="category_display" label="分类" width="120" />
        <el-table-column prop="status_display" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : row.status === 'archived' ? 'info' : 'warning'" size="small">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="author_name" label="发布人" width="120" />
        <el-table-column prop="published_at" label="发布时间" width="180">
          <template #default="{ row }">{{ formatDate(row.published_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" v-if="canCreate">
          <template #default="{ row }">
            <el-button size="small" text @click="handlePin(row)">{{ row.is_pinned ? '取消置顶' : '置顶' }}</el-button>
            <el-button size="small" text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 发布公告对话框 -->
    <el-dialog v-model="showDialog" title="发布公告" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入公告标题" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="系统公告" value="system" />
            <el-option label="项目公告" value="project" />
            <el-option label="活动公告" value="activity" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="6" placeholder="请输入公告内容" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="draft">草稿</el-radio>
            <el-radio value="published">发布</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="公开">
          <el-switch v-model="form.is_public" />
          <span class="form-tip">公开公告可在无需登录的展示页查看</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Top } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { useUserStore } from '@/stores/user'
import { get, post, patch, del } from '@/api/request'
import { formatDate } from '@/utils/format'

const userStore = useUserStore()
const canCreate = computed(() => userStore.isAdmin || userStore.isTeacher)

const loading = ref(false)
const announcements = ref<any[]>([])
const page = ref(1)
const pageSize = 10
const total = ref(0)
const filterCategory = ref('')

const showDialog = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({
  title: '',
  content: '',
  category: 'system',
  status: 'published',
  is_public: false,
})
const rules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }],
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize }
    if (filterCategory.value) params.category = filterCategory.value
    const res = await get<any>('/notifications/announcements/', params)
    announcements.value = res.results || res
    total.value = res.count || announcements.value.length
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    submitting.value = true
    await post('/notifications/announcements/', form)
    ElMessage.success('公告发布成功')
    showDialog.value = false
    form.title = ''
    form.content = ''
    form.category = 'system'
    form.status = 'published'
    form.is_public = false
    loadData()
  } catch {
    // handled
  } finally {
    submitting.value = false
  }
}

async function handlePin(row: any): Promise<void> {
  try {
    await post(`/notifications/announcements/${row.id}/pin/`)
    ElMessage.success(row.is_pinned ? '已取消置顶' : '已置顶')
    loadData()
  } catch {
    // handled
  }
}

async function handleDelete(row: any): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除公告"${row.title}"吗？`, '确认', { type: 'warning' })
    await del(`/notifications/announcements/${row.id}/`)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // cancelled or error
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.announcement-list {
  padding: 0;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
