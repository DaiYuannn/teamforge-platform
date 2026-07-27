<template>
  <div class="announcement-list page-container">
    <PageHeader title="公告管理" subtitle="发布与维护团队公告">
      <template #actions>
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="showDialog = true">
          发布公告
        </el-button>
      </template>
    </PageHeader>

    <div class="surface-panel filter-panel">
      <div class="filter-control">
        <span class="filter-label">公告分类</span>
        <el-select
          v-model="filterCategory"
          placeholder="全部分类"
          clearable
          class="category-filter"
          @change="handleCategoryChange"
        >
          <el-option label="系统公告" value="system" />
          <el-option label="项目公告" value="project" />
          <el-option label="活动公告" value="activity" />
          <el-option label="其他" value="other" />
        </el-select>
      </div>
      <span class="result-count">共 {{ total }} 条公告</span>
    </div>

    <section class="surface-panel content-panel">
      <el-table v-if="!isMobile" v-loading="loading" :data="announcements" style="width: 100%">
        <template #empty>
          <el-empty description="暂无公告" />
        </template>
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <div class="announcement-title">
              <el-icon v-if="row.is_pinned" class="pin-icon"><Top /></el-icon>
              <span>{{ row.title }}</span>
            </div>
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
        <el-table-column v-if="canCreate" label="操作" width="104" align="right" fixed="right">
          <template #default="{ row }">
            <el-tooltip :content="row.is_pinned ? '取消置顶' : '置顶'" placement="top">
              <el-button
                text
                :icon="row.is_pinned ? Bottom : Top"
                :aria-label="row.is_pinned ? '取消置顶' : '置顶'"
                @click="handlePin(row)"
              />
            </el-tooltip>
            <el-tooltip content="删除公告" placement="top">
              <el-button text type="danger" :icon="Delete" aria-label="删除公告" @click="handleDelete(row)" />
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <div v-else v-loading="loading" class="mobile-list">
        <el-empty v-if="announcements.length === 0 && !loading" description="暂无公告" />
        <article v-for="row in announcements" :key="row.id" class="mobile-announcement">
          <div class="mobile-title-row">
            <h2 class="mobile-title">
              <el-icon v-if="row.is_pinned" class="pin-icon"><Top /></el-icon>
              <span>{{ row.title }}</span>
            </h2>
            <el-tag
              :type="row.status === 'published' ? 'success' : row.status === 'archived' ? 'info' : 'warning'"
              size="small"
            >
              {{ row.status_display }}
            </el-tag>
          </div>
          <div class="mobile-meta">
            <span>{{ row.category_display }}</span>
            <span>{{ row.author_name || '-' }}</span>
            <time>{{ formatDate(row.published_at) }}</time>
          </div>
          <div v-if="canCreate" class="mobile-actions">
            <el-button text :icon="row.is_pinned ? Bottom : Top" @click="handlePin(row)">
              {{ row.is_pinned ? '取消置顶' : '置顶' }}
            </el-button>
            <el-button text type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </div>
        </article>
      </div>

      <div class="pagination-wrapper">
        <AccessiblePagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          :layout="isMobile ? 'prev, pager, next' : 'total, prev, pager, next'"
          @current-change="loadData"
        />
      </div>
    </section>

    <!-- 发布公告对话框 -->
    <el-dialog
      v-model="showDialog"
      title="发布公告"
      width="620px"
      :fullscreen="isMobile"
      append-to-body
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        :label-width="isMobile ? 'auto' : '80px'"
        :label-position="isMobile ? 'top' : 'right'"
      >
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
import { Bottom, Delete, Plus, Top } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { useUserStore } from '@/stores/user'
import { get, post, del } from '@/api/request'
import { formatDate } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'

const userStore = useUserStore()
const canCreate = computed(() => userStore.isAdmin || userStore.isTeacher)
const { isMobile } = useDevice()

const loading = ref(false)
const announcements = ref<any[]>([])
const page = ref(1)
const pageSize = userStore.itemsPerPage
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

function handleCategoryChange(): void {
  page.value = 1
  loadData()
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
  display: flex;
  flex-direction: column;
}

.filter-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 12px 14px;
}

.filter-control {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.filter-label,
.result-count {
  font-size: 12px;
  color: var(--color-text-muted);
}

.category-filter {
  width: 168px;
}

.content-panel {
  padding: 0;
  margin-top: var(--space-4);
  overflow: hidden;
}

.announcement-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-weight: 500;
  color: var(--color-text);
}

.pin-icon {
  flex: 0 0 auto;
  color: var(--color-warning);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 0 14px 14px;
}

.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.mobile-list {
  min-height: 160px;
  padding: 0 12px;
}

.mobile-announcement {
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.mobile-announcement:last-child {
  border-bottom: 0;
}

.mobile-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.mobile-title {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  min-width: 0;
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.45;
  color: var(--color-text);
}

.mobile-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 12px;
  margin-top: 7px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.mobile-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

@media screen and (max-width: 768px) {
  .filter-panel {
    align-items: flex-end;
    padding: 10px 12px;
  }

  .filter-control {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .category-filter {
    width: min(200px, 58vw);
  }

  .pagination-wrapper {
    justify-content: center;
    padding: 0 6px 12px;
  }

  .form-tip {
    display: block;
    margin: 6px 0 0;
    line-height: 1.5;
  }
}
</style>
