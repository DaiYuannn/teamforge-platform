<template>
  <div class="page-container file-list-page">
    <PageHeader title="文件管理" subtitle="项目文件、访问级别与下载记录入口">
      <template #meta>
        <span class="page-meta">共 {{ total }} 个文件</span>
      </template>
    </PageHeader>

    <section class="file-workspace">
      <div class="filter-toolbar">
        <el-form :inline="true" :model="queryParams" @submit.prevent>
        <el-form-item label="项目">
          <el-select v-model="queryParams.project" class="project-filter" placeholder="全部项目" clearable filterable @change="handleSearch">
            <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="queryParams.level" class="level-filter" placeholder="全部级别" clearable @change="handleSearch">
            <el-option
              v-for="(item, key) in FILE_LEVEL_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      </div>

      <div class="list-heading">
        <div>
          <h2>文件清单</h2>
          <span v-if="sensitiveCount > 0" class="sensitive-count">本页 {{ sensitiveCount }} 个敏感文件</span>
        </div>
        <span>{{ fileList.length }} 个当前结果</span>
      </div>

      <div v-if="!isMobile" class="file-table-shell">
        <el-table
          v-loading="loading"
          :data="fileList"
          stripe
          size="small"
          :row-class-name="getFileRowClass"
        >
        <el-table-column prop="name" label="文件" min-width="230" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="file-cell">
              <span class="file-icon-box" :class="{ 'is-sensitive': row.level === 'sensitive' }">
                <el-icon><Document /></el-icon>
              </span>
              <div>
                <strong>{{ row.name }}</strong>
                <span>{{ row.content_type || '未知类型' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="project_name" label="所属项目" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.project_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="level" label="级别" width="110">
          <template #default="{ row }">
            <el-tag :type="FILE_LEVEL_MAP[row.level]?.tagType as any" size="small" effect="plain">
              {{ row.level_display || FILE_LEVEL_MAP[row.level]?.label || row.level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploader_name" label="上传者" width="100" />
        <el-table-column prop="created_at" label="上传时间" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right" align="right">
          <template #default="{ row }">
            <el-button :icon="View" type="primary" link @click="handlePreview(row as FileAsset)">预览</el-button>
            <el-button :icon="Download" type="primary" link @click="handleDownload(row as FileAsset)">下载</el-button>
            <el-button :icon="Clock" type="primary" link @click="openVersionDialog(row as FileAsset)">版本</el-button>
            <el-button v-permission="['teacher', 'sys_admin']" :icon="Delete" type="danger" link @click="handleDelete(row as FileAsset)">删除</el-button>
          </template>
        </el-table-column>
          <template #empty><el-empty description="暂无文件" /></template>
        </el-table>
      </div>

      <div v-else v-loading="loading" class="mobile-file-list">
        <article v-for="item in fileList" :key="item.id" class="mobile-file-card" :class="{ 'is-sensitive': item.level === 'sensitive' }">
          <div class="mobile-file-heading">
            <div class="mobile-file-title">
              <span class="file-icon-box" :class="{ 'is-sensitive': item.level === 'sensitive' }"><el-icon><Document /></el-icon></span>
              <div><h3>{{ item.name }}</h3><span>{{ item.content_type || '未知类型' }}</span></div>
            </div>
            <el-tag :type="FILE_LEVEL_MAP[item.level]?.tagType as any" size="small" effect="plain">
              {{ item.level_display || FILE_LEVEL_MAP[item.level]?.label || item.level }}
            </el-tag>
          </div>

          <dl class="mobile-file-meta">
            <div class="meta-wide"><dt>所属项目</dt><dd>{{ item.project_name || '-' }}</dd></div>
            <div><dt>文件大小</dt><dd>{{ formatFileSize(item.size) }}</dd></div>
            <div><dt>上传者</dt><dd>{{ item.uploader_name || '-' }}</dd></div>
            <div><dt>上传时间</dt><dd>{{ formatDate(item.created_at) }}</dd></div>
          </dl>

          <div class="mobile-file-actions">
            <el-button :icon="View" type="primary" link @click="handlePreview(item)">预览</el-button>
            <el-button :icon="Download" type="primary" link @click="handleDownload(item)">下载</el-button>
            <el-button :icon="Clock" type="primary" link @click="openVersionDialog(item)">版本</el-button>
            <el-button v-permission="['teacher', 'sys_admin']" :icon="Delete" type="danger" link @click="handleDelete(item)">删除</el-button>
          </div>
        </article>
        <el-empty v-if="fileList.length === 0 && !loading" description="暂无文件" />
      </div>

      <div v-if="total > 0" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next'"
          background
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </section>

    <el-dialog
      v-model="previewVisible"
      :title="previewFile?.name || '文件预览'"
      width="min(1040px, calc(100vw - 32px))"
      top="4vh"
      @close="handlePreviewClose"
    >
      <div v-if="previewFile?.level === 'sensitive'" class="sensitive-preview-alert">
        <el-icon><WarningFilled /></el-icon>
        <span>敏感文件，访问与下载操作将按权限校验</span>
      </div>
      <div v-if="previewLoading" v-loading="true" class="preview-loading"></div>
      <div v-else-if="previewUrl" class="preview-container">
        <img v-if="previewType === 'image'" :src="previewUrl" class="preview-image" alt="预览" />
        <iframe v-else-if="previewType === 'pdf'" :src="previewUrl" class="preview-iframe" title="PDF预览"></iframe>
        <video v-else-if="previewType === 'video'" :src="previewUrl" controls class="preview-video"></video>
        <audio v-else-if="previewType === 'audio'" :src="previewUrl" controls class="preview-audio"></audio>
        <el-empty v-else description="该文件类型不支持在线预览，请下载后查看" />
      </div>
      <el-empty v-else description="该文件类型不支持在线预览，请下载后查看" />
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button :icon="Download" type="primary" :disabled="!previewFile" @click="previewFile && handleDownload(previewFile)">下载</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="versionVisible"
      :title="`${versionFile?.name || '文件'} · 版本历史`"
      width="min(760px, calc(100vw - 32px))"
    >
      <div class="version-toolbar">
        <div>
          <strong>当前版本 v{{ versionFile?.version || 1 }}</strong>
          <span>恢复历史版本会生成一个新的当前版本，不会覆盖审计记录。</span>
        </div>
        <el-upload
          v-if="versionFile && canManageVersion(versionFile)"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleVersionUpload"
        >
          <el-button type="primary" :icon="Upload" :loading="versionUploading">上传新版本</el-button>
        </el-upload>
      </div>
      <el-table v-loading="versionLoading" :data="versions" size="small">
        <template #empty><el-empty description="暂无历史版本" /></template>
        <el-table-column prop="version" label="版本" width="90">
          <template #default="{ row }">v{{ row.version }}</template>
        </el-table-column>
        <el-table-column prop="uploader_name" label="上传者" min-width="120">
          <template #default="{ row }">{{ row.uploader_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="归档时间" min-width="150">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleVersionDownload(row as FileVersion)">下载</el-button>
            <el-button
              v-if="versionFile && canManageVersion(versionFile)"
              link
              type="warning"
              @click="handleVersionRestore(row as FileVersion)"
            >
              恢复
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { Clock, Delete, Document, Download, Refresh, Search, Upload, View, WarningFilled } from '@element-plus/icons-vue'
import {
  getFiles,
  deleteFile,
  downloadFile,
  downloadFileVersion,
  getFileVersions,
  restoreFileVersion,
  uploadFileVersion,
  type FileQueryParams,
} from '@/api/files'
import { getProjects } from '@/api/projects'
import { formatDate, formatFileSize, downloadBlob } from '@/utils/format'
import { FILE_LEVEL_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import type { FileAsset, FileVersion, Project } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'

const appStore = useAppStore()
const userStore = useUserStore()

const { isMobile } = useDevice()
const loading = ref(false)
const fileList = ref<FileAsset[]>([])
const total = ref(0)
const projectOptions = ref<Project[]>([])
const sensitiveCount = computed(() => fileList.value.filter((item) => item.level === 'sensitive').length)

const queryParams = reactive<FileQueryParams>({
  page: 1,
  page_size: appStore.itemsPerPage,
  project: undefined,
  level: undefined,
})

async function loadProjects(): Promise<void> {
  try {
    const res = await getProjects({ page: 1, page_size: 100 })
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

function getFileRowClass({ row }: { row: FileAsset }): string {
  return row.level === 'sensitive' ? 'sensitive-file-row' : ''
}

async function handleDownload(file: FileAsset): Promise<void> {
  try {
    const blob = await downloadFile(file.id)
    downloadBlob(blob, file.name)
  } catch {
    ElMessage.error('下载失败')
  }
}

// ============================================
// P2: 文件在线预览
// ============================================
const previewVisible = ref(false)
const previewFile = ref<FileAsset | null>(null)
const previewUrl = ref('')
const previewType = ref<'image' | 'pdf' | 'video' | 'audio' | 'unknown'>('unknown')
const previewLoading = ref(false)

/** 判断文件预览类型 */
function getPreviewType(file: FileAsset): 'image' | 'pdf' | 'video' | 'audio' | 'unknown' {
  const contentType = (file.content_type || '').toLowerCase()
  const name = (file.name || '').toLowerCase()
  if (contentType.startsWith('image/') || /\.(jpg|jpeg|png|gif|bmp|webp|svg)$/.test(name)) return 'image'
  if (contentType === 'application/pdf' || name.endsWith('.pdf')) return 'pdf'
  if (contentType.startsWith('video/') || /\.(mp4|webm|ogg|mov|avi)$/.test(name)) return 'video'
  if (contentType.startsWith('audio/') || /\.(mp3|wav|flac|aac|m4a)$/.test(name)) return 'audio'
  return 'unknown'
}

/** 预览文件 */
async function handlePreview(file: FileAsset): Promise<void> {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
  previewFile.value = file
  previewType.value = getPreviewType(file)
  previewVisible.value = true
  previewLoading.value = true
  previewUrl.value = ''

  if (previewType.value === 'unknown') {
    previewLoading.value = false
    return
  }

  try {
    const blob = await downloadFile(file.id)
    previewUrl.value = URL.createObjectURL(blob)
  } catch {
    ElMessage.error('预览加载失败')
    previewType.value = 'unknown'
  } finally {
    previewLoading.value = false
  }
}

function handlePreviewClose(): void {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
  previewUrl.value = ''
  previewFile.value = null
  previewType.value = 'unknown'
  previewLoading.value = false
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

const versionVisible = ref(false)
const versionFile = ref<FileAsset | null>(null)
const versions = ref<FileVersion[]>([])
const versionLoading = ref(false)
const versionUploading = ref(false)

async function loadVersions(): Promise<void> {
  if (!versionFile.value) return
  versionLoading.value = true
  try {
    versions.value = await getFileVersions(versionFile.value.id)
  } finally {
    versionLoading.value = false
  }
}

function openVersionDialog(file: FileAsset): void {
  versionFile.value = file
  versionVisible.value = true
  loadVersions()
}

function canManageVersion(file: FileAsset): boolean {
  if (['teacher', 'sys_admin'].includes(userStore.role)) return true
  const project = projectOptions.value.find((item) => item.id === file.project)
  return Boolean(project && project.leader === userStore.userInfo?.id)
}

async function handleVersionUpload(file: UploadFile): Promise<void> {
  if (!versionFile.value || !file.raw || versionUploading.value) return
  versionUploading.value = true
  try {
    versionFile.value = await uploadFileVersion(versionFile.value.id, file.raw)
    ElMessage.success(`已上传 v${versionFile.value.version}`)
    await Promise.all([loadVersions(), loadData()])
  } finally {
    versionUploading.value = false
  }
}

async function handleVersionDownload(version: FileVersion): Promise<void> {
  if (!versionFile.value) return
  const blob = await downloadFileVersion(versionFile.value.id, version.id)
  downloadBlob(blob, `${versionFile.value.name}_v${version.version}`)
}

async function handleVersionRestore(version: FileVersion): Promise<void> {
  if (!versionFile.value) return
  await ElMessageBox.confirm(
    `确定将 v${version.version} 恢复为新的当前版本吗？`,
    '恢复历史版本',
    { type: 'warning' },
  )
  versionFile.value = await restoreFileVersion(versionFile.value.id, version.id)
  ElMessage.success(`已恢复为 v${versionFile.value.version}`)
  await Promise.all([loadVersions(), loadData()])
}

onMounted(() => {
  loadProjects()
  loadData()
})

onUnmounted(() => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
})
</script>

<style lang="scss" scoped>
.file-list-page {
  padding-bottom: 32px;
}

.page-meta {
  display: inline-block;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.file-workspace {
  min-width: 0;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.filter-toolbar {
  padding: 15px 18px;
  border-bottom: 1px solid var(--color-border-light);
}

.filter-toolbar :deep(.el-form) {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-toolbar :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}

.project-filter {
  width: 220px;
}

.level-filter {
  width: 132px;
}

.list-heading {
  display: flex;
  min-height: 54px;
  padding: 12px 18px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.list-heading > div {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.list-heading h2 {
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
}

.list-heading > span {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
}

.sensitive-count {
  color: var(--color-danger);
  font-size: 11px;
  font-weight: 600;
}

.file-table-shell {
  min-width: 0;
  overflow-x: auto;
}

.file-table-shell :deep(.el-table) {
  min-width: 980px;
}

.file-table-shell :deep(.sensitive-file-row > td.el-table__cell) {
  background: #fffafa;
}

.version-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0 18px;

  > div {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  strong {
    color: var(--color-text);
    font-size: 14px;
  }

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.file-cell,
.mobile-file-title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.file-icon-box {
  display: inline-flex;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border: 1px solid rgba(23, 107, 115, 0.18);
  border-radius: var(--radius-sm);
}

.file-icon-box.is-sensitive {
  color: var(--color-danger);
  background: var(--danger-light);
  border-color: rgba(182, 66, 66, 0.22);
}

.file-cell > div,
.mobile-file-title > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.file-cell strong,
.mobile-file-title h3 {
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-cell > div > span,
.mobile-file-title > div > span {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-file-list {
  display: flex;
  padding: 12px;
  flex-direction: column;
  gap: 10px;
}

.mobile-file-card {
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.mobile-file-card.is-sensitive {
  border-color: rgba(182, 66, 66, 0.34);
}

.mobile-file-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mobile-file-title {
  flex: 1;
}

.mobile-file-title h3 {
  max-width: 100%;
  font-size: 14px;
}

.mobile-file-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-file-meta .meta-wide {
  grid-column: 1 / -1;
}

.mobile-file-meta dt {
  margin-bottom: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.mobile-file-meta dd {
  overflow: hidden;
  color: var(--color-text-regular);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-file-actions {
  display: flex;
  margin-top: 12px;
  padding-top: 9px;
  justify-content: flex-end;
  gap: 4px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-file-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 0 18px 16px;
  border-top: 1px solid var(--color-border-light);
}

.sensitive-preview-alert {
  display: flex;
  margin-bottom: 12px;
  padding: 10px 12px;
  align-items: center;
  gap: 8px;
  color: var(--color-danger);
  font-size: 12px;
  font-weight: 600;
  background: var(--danger-light);
  border: 1px solid rgba(182, 66, 66, 0.24);
  border-radius: var(--radius-sm);
}

.preview-container {
  display: flex;
  min-height: 420px;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.preview-image {
  max-width: 100%;
  max-height: 68vh;
  object-fit: contain;
}

.preview-iframe {
  width: 100%;
  height: 68vh;
  border: none;
}

.preview-video {
  max-width: 100%;
  max-height: 68vh;
}

.preview-audio {
  width: min(640px, calc(100% - 32px));
}

.preview-loading {
  display: flex;
  min-height: 420px;
  justify-content: center;
  align-items: center;
}

@media screen and (max-width: 768px) {
  .version-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .file-list-page {
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }

  .filter-toolbar {
    padding: 14px;
  }

  .filter-toolbar :deep(.el-form) {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 112px;
    gap: 12px 10px;
  }

  .filter-toolbar :deep(.el-form-item) {
    display: block;
    min-width: 0;
  }

  .filter-toolbar :deep(.el-form-item:last-child) {
    grid-column: 1 / -1;
  }

  .filter-toolbar :deep(.el-form-item__label) {
    display: block;
    width: 100%;
    height: auto;
    margin-bottom: 5px;
    line-height: 1.4;
  }

  .project-filter,
  .level-filter {
    width: 100%;
  }

  .list-heading {
    padding-right: 14px;
    padding-left: 14px;
  }

  .pagination-wrapper {
    justify-content: center;
    padding-right: 8px;
    padding-left: 8px;
  }

  .preview-container,
  .preview-loading {
    min-height: 300px;
  }

  .preview-iframe {
    height: 62vh;
  }
}
</style>
