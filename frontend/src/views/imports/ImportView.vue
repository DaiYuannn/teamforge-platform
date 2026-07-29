<template>
  <div class="page-container">
    <PageHeader title="导入中心" subtitle="批量导入数据" />

    <!-- 导入步骤 -->
    <section class="surface-panel import-workspace">
      <div v-if="isMobile" class="mobile-step-indicator">
        <span>步骤 {{ currentStep + 1 }} / {{ stepTitles.length }}</span>
        <strong>{{ stepTitles[currentStep] }}</strong>
      </div>
      <el-steps v-else :active="currentStep" align-center finish-status="success" class="import-steps">
        <el-step title="选择模块" />
        <el-step title="上传文件" />
        <el-step title="字段映射" />
        <el-step title="预览数据" />
        <el-step title="确认导入" />
      </el-steps>

      <!-- 步骤1：选择模块 -->
      <div v-if="currentStep === 0" class="step-content">
        <el-form-item label="导入到团队">
          <el-select v-model="selectedTeamId" clearable placeholder="请选择你负责的团队" style="width: 320px">
            <el-option v-for="team in manageableTeams" :key="team.id" :label="team.name" :value="team.id" />
          </el-select>
        </el-form-item>
        <el-radio-group v-model="selectedModule" class="module-group">
          <el-radio-button
            v-for="(label, key) in IMPORT_MODULE_MAP"
            :key="key"
            :value="key"
          >
            {{ label }}
          </el-radio-button>
        </el-radio-group>
        <div class="step-actions">
          <el-button type="primary" :disabled="!selectedModule" @click="currentStep = 1">下一步</el-button>
        </div>
      </div>

      <!-- 步骤2：上传文件 -->
      <div v-if="currentStep === 1" class="step-content">
        <el-alert
          :title="selectedModule === 'materials' ? 'ZIP 资料包会先安全预览，再分流确认导入' : '这里仅导入结构化表格数据'"
          :description="selectedModule === 'materials'
            ? '压缩包根目录必须包含 manifest.json；系统会校验路径穿越、软链接、压缩炸弹、危险扩展名和每项权限。'
            : '证件照、PPT、计划书等资料不解析成数据行，请选择 ZIP 资料包或按资料敏感程度分别上传。'"
          type="info"
          :closable="false"
          show-icon
          class="mb-16"
        >
          <template #default>
            <el-button link type="primary" @click="router.push('/files')">上传普通文件</el-button>
            <el-button link type="danger" @click="router.push('/sensitive')">管理证件等敏感资料</el-button>
          </template>
        </el-alert>
        <div class="template-guide">
          <div>
            <strong>{{ selectedModule === 'materials' ? '资料包清单模板' : `${IMPORT_MODULE_MAP[selectedModule]}导入模板` }}</strong>
            <span>{{ selectedModule === 'materials' ? '清单使用项目编号、团队编号和成员邮箱建立稳定关联。' : '跨表关联请使用项目编号和成员邮箱，避免数据库 ID 变化造成错位。' }}</span>
          </div>
          <el-button :loading="templateDownloading" @click="handleDownloadTemplate">下载模板</el-button>
        </div>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :on-change="handleFileChange"
          :limit="1"
          :accept="selectedModule === 'materials' ? '.zip' : '.xlsx,.xlsm,.csv'"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">{{ selectedModule === 'materials' ? '支持 ZIP + 根目录 manifest.json' : '支持 Excel (.xlsx、.xlsm) 和 CSV 文件' }}</div>
          </template>
        </el-upload>
        <div class="step-actions">
          <el-button @click="currentStep = 0">上一步</el-button>
          <el-button type="primary" :loading="previewing" :disabled="!selectedFile" @click="handlePreview">
            预览数据
          </el-button>
        </div>
      </div>

      <!-- 步骤3：字段映射 -->
      <div v-if="currentStep === 2 && selectedModule !== 'materials'" class="step-content">
        <p class="step-hint">请确认源文件字段与系统字段的映射关系：</p>
        <div class="table-scroll">
        <el-table :data="mappingRows" size="small" class="mapping-table">
          <el-table-column prop="sourceField" label="源文件字段" width="200" />
          <el-table-column label="系统字段" width="200">
            <template #default="{ row }">
              <el-select v-model="row.targetField" placeholder="选择字段" clearable>
                <el-option
                  v-for="field in systemFields"
                  :key="field.value"
                  :label="`${field.label}${field.required ? '（必填）' : ''}`"
                  :value="field.value"
                />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
        </div>
        <div class="step-actions">
          <el-button @click="currentStep = 1">上一步</el-button>
          <el-button type="primary" @click="handleConfirmMapping">确认映射</el-button>
        </div>
      </div>

      <!-- 步骤4：预览数据 -->
      <div v-if="currentStep === 3" class="step-content">
        <el-alert
          :title="`共 ${previewData.total_rows} 行数据，其中有效 ${previewData.valid_rows} 行，错误 ${previewData.error_rows} 行`"
          type="info"
          show-icon
          :closable="false"
          class="mb-16"
        />
        <div class="table-scroll">
        <el-table :data="previewRows" size="small" max-height="400" class="preview-table">
          <el-table-column prop="row_index" label="行号" width="60" />
          <el-table-column label="数据">
            <template #default="{ row }">
              <pre>{{ JSON.stringify(row.data, null, 0) }}</pre>
            </template>
          </el-table-column>
          <el-table-column prop="valid" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.valid ? 'success' : 'danger'" size="small">
                {{ row.valid ? '有效' : '无效' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="error" label="错误信息" width="200" show-overflow-tooltip />
        </el-table>
        </div>
        <div class="step-actions">
          <el-button @click="currentStep = 2">上一步</el-button>
          <el-button type="primary" :loading="importing" @click="handleConfirmImport">确认导入</el-button>
        </div>
      </div>

      <!-- 步骤5：导入完成 -->
      <div v-if="currentStep === 4" class="step-content">
        <el-result icon="success" title="导入成功" sub-title="数据已成功导入系统">
          <template #extra>
            <el-button type="primary" @click="handleReset">继续导入</el-button>
          </template>
        </el-result>
      </div>
    </section>

    <!-- 导入历史 -->
    <section class="surface-panel history-panel">
      <div class="section-bar">
        <h2>导入历史</h2>
        <span>共 {{ importTasks.length }} 条</span>
      </div>
      <el-table v-if="!isMobile" v-loading="historyLoading" :data="importTasks" size="small">
        <template #empty>
          <EmptyState text="暂无导入记录" :compact="true" />
        </template>
        <el-table-column prop="module" label="模块" width="100">
          <template #default="{ row }">{{ IMPORT_MODULE_MAP[row.module] || row.module }}</template>
        </el-table-column>
        <el-table-column prop="team_name" label="所属团队" min-width="130">
          <template #default="{ row }">{{ row.team_name || '历史未分组' }}</template>
        </el-table-column>
        <el-table-column prop="file_name" label="文件名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="IMPORT_TASK_STATUS_MAP[row.status]?.tagType as any" size="small">
              {{ IMPORT_TASK_STATUS_MAP[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_rows" label="总行数" width="80" align="center" />
        <el-table-column prop="valid_rows" label="成功" width="80" align="center" />
        <el-table-column prop="error_rows" label="失败" width="80" align="center" />
        <el-table-column prop="created_by_name" label="操作人" width="100" />
        <el-table-column prop="created_at" label="导入时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.can_rollback && row.status === 'confirmed'"
              type="danger"
              link
              @click="handleRollback(row as ImportTask)"
            >
              回滚
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else v-loading="historyLoading" class="mobile-history">
        <EmptyState v-if="importTasks.length === 0 && !historyLoading" text="暂无导入记录" :compact="true" />
        <article v-for="row in importTasks" :key="row.id" class="history-item">
          <div class="history-heading">
            <h3>{{ row.file_name }}</h3>
            <el-tag :type="IMPORT_TASK_STATUS_MAP[row.status]?.tagType as any" size="small">
              {{ IMPORT_TASK_STATUS_MAP[row.status]?.label || row.status }}
            </el-tag>
          </div>
          <div class="history-meta">
            <span>{{ IMPORT_MODULE_MAP[row.module] || row.module }}</span>
            <span>{{ row.created_by_name }}</span>
            <time>{{ formatDateTime(row.created_at) }}</time>
          </div>
          <div class="history-stats">
            <span>总计 <strong>{{ row.total_rows }}</strong></span>
            <span>成功 <strong class="success-number">{{ row.valid_rows }}</strong></span>
            <span>失败 <strong class="danger-number">{{ row.error_rows }}</strong></span>
          </div>
          <div v-if="row.can_rollback && row.status === 'confirmed'" class="history-actions">
            <el-button text type="danger" @click="handleRollback(row as ImportTask)">回滚</el-button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  previewImport,
  confirmImport,
  rollbackImport,
  getImportTasks,
  downloadImportTemplate,
  previewMaterialArchive,
} from '@/api/imports'
import { IMPORT_MODULE_MAP, IMPORT_TASK_STATUS_MAP } from '@/utils/constants'
import { downloadBlob, formatDateTime } from '@/utils/format'
import type { ImportModule, ImportPreviewResult, ImportTask, FieldMapping } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useDevice } from '@/composables/useDevice'
import { getTeams, type Team } from '@/api/teams'

const { isMobile } = useDevice()
const router = useRouter()

const stepTitles = ['选择模块', '上传文件', '字段映射', '预览数据', '确认导入']

const currentStep = ref(0)
const selectedModule = ref<ImportModule>('members')
const selectedTeamId = ref<number | undefined>()
const manageableTeams = ref<Team[]>([])
const selectedFile = ref<File | null>(null)
const previewing = ref(false)
const importing = ref(false)
const templateDownloading = ref(false)
const historyLoading = ref(false)
const previewData = ref<ImportPreviewResult>({
  task_id: 0,
  headers: [],
  field_mapping: {},
  preview_rows: [],
  total_rows: 0,
  valid_rows: 0,
  error_rows: 0,
  error_details: {},
  field_options: [],
})

// 系统可用字段（根据模块不同动态获取，这里用 headers + field_mapping 的 value 做候选）
const systemFields = ref<Array<{ value: string; label: string; required: boolean }>>([])

// 字段映射
const mappingRows = ref<{ sourceField: string; targetField: string }[]>([])

// 预览数据行（从 preview_rows 构建成 PreviewRow 格式）
const previewRows = ref<{ row_index: number; data: Record<string, any>; valid: boolean; error?: string }[]>([])

// 导入历史
const importTasks = ref<ImportTask[]>([])

// 文件选择
function handleFileChange(file: UploadFile): void {
  selectedFile.value = file.raw || null
}

// 预览数据
async function handlePreview(): Promise<void> {
  if (!selectedFile.value) return
  if (selectedModule.value === 'materials' && !selectedTeamId.value) {
    ElMessage.warning('导入资料包前请选择所属总团队')
    return
  }
  previewing.value = true
  try {
    const result = selectedModule.value === 'materials'
      ? await previewMaterialArchive(selectedFile.value, selectedTeamId.value as number)
      : await previewImport(
        selectedFile.value,
        selectedModule.value,
        undefined,
        selectedTeamId.value,
      )
    previewData.value = result
    // 初始化映射行（后端返回 field_mapping: { sourceField: targetField }）
    const mapping = result.field_mapping || {}
    mappingRows.value = (result.headers || []).map((sourceField) => ({
      sourceField,
      targetField: mapping[sourceField] || '',
    }))
    systemFields.value = result.field_options || []
    // 构建预览数据行
    const rawRows = result.preview_rows || []
    const errorDetails = result.error_details || {}
    previewRows.value = rawRows.map((row: any, idx: number) => {
      if (selectedModule.value === 'materials') {
        return {
          row_index: row.row_index || idx + 1,
          data: row,
          valid: Boolean(row.valid),
          error: Array.isArray(row.errors) ? row.errors.join('；') : '',
        }
      }
      const rowIndex = idx + 1
      const errorInfo = errorDetails[String(rowIndex)] || errorDetails[rowIndex]
      return {
        row_index: rowIndex,
        data: typeof row === 'object' && !Array.isArray(row) ? row : { value: String(row) },
        valid: !errorInfo,
        error: errorInfo ? (typeof errorInfo === 'string' ? errorInfo : JSON.stringify(errorInfo)) : '',
      }
    })
    currentStep.value = selectedModule.value === 'materials' ? 3 : 2
  } catch {
    // 已处理
  } finally {
    previewing.value = false
  }
}

// 确认字段映射
function handleConfirmMapping(): void {
  const selectedTargets = new Set(
    mappingRows.value.map((row) => row.targetField).filter(Boolean),
  )
  const missing = systemFields.value
    .filter((field) => field.required && !selectedTargets.has(field.value))
    .map((field) => field.label)
  if (missing.length) {
    ElMessage.warning(`请先映射必填字段：${missing.join('、')}`)
    return
  }
  currentStep.value = 3
}

// 确认导入
async function handleConfirmImport(): Promise<void> {
  importing.value = true
  try {
    // 构建最终字段映射
    const fieldMapping: FieldMapping = {}
    mappingRows.value.forEach((row) => {
      if (row.targetField) {
        fieldMapping[row.sourceField] = row.targetField
      }
    })

    const result = await confirmImport(previewData.value.task_id, fieldMapping)
    currentStep.value = 4
    ElMessage.success(
      result.error_count
        ? `导入完成：成功 ${result.created_count} 条，失败 ${result.error_count} 条`
        : `成功导入 ${result.created_count} 条数据`,
    )
    loadImportTasks()
  } catch {
    // 已处理
  } finally {
    importing.value = false
  }
}

// 回滚
async function handleRollback(task: ImportTask): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要回滚此导入操作吗？回滚后相关数据将被删除。', '提示', {
      type: 'warning',
    })
    await rollbackImport(task.id)
    ElMessage.success('回滚成功')
    loadImportTasks()
  } catch {
    // 取消
  }
}

// 重置
function handleReset(): void {
  currentStep.value = 0
  selectedFile.value = null
  selectedModule.value = 'members'
  selectedTeamId.value = manageableTeams.value.length === 1 ? manageableTeams.value[0].id : undefined
  previewData.value = {
    task_id: 0,
    headers: [],
    field_mapping: {},
    preview_rows: [],
    total_rows: 0,
    valid_rows: 0,
    error_rows: 0,
    error_details: {},
    field_options: [],
  }
  mappingRows.value = []
  previewRows.value = []
  systemFields.value = []
}

async function handleDownloadTemplate(): Promise<void> {
  templateDownloading.value = true
  try {
    if (selectedModule.value === 'materials') {
      const example = {
        version: 1,
        items: [
          {
            path: '普通资料/答辩PPT.pptx',
            project_code: 'PROJECT-001',
            level: 'internal',
            visibility: 'competition',
            competition_entry_id: 1,
            title: '比赛答辩PPT',
          },
          {
            path: '敏感资料/张三身份证.jpg',
            project_code: 'PROJECT-001',
            team_code: 'TEAM-001',
            level: 'sensitive',
            visibility: 'team',
            data_type: 'id_card',
            subject_email: 'member@example.com',
            title: '张三身份证扫描件',
          },
        ],
      }
      downloadBlob(
        new Blob([JSON.stringify(example, null, 2)], { type: 'application/json;charset=utf-8' }),
        'manifest.json',
      )
      return
    }
    const blob = await downloadImportTemplate(selectedModule.value)
    downloadBlob(blob, `${IMPORT_MODULE_MAP[selectedModule.value]}导入模板.xlsx`)
  } catch {
    // 请求层统一处理错误。
  } finally {
    templateDownloading.value = false
  }
}

// 加载导入历史
async function loadImportTasks(): Promise<void> {
  historyLoading.value = true
  try {
    const res = await getImportTasks()
    importTasks.value = res.results
  } catch {
    // 忽略
  } finally {
    historyLoading.value = false
  }
}

onMounted(() => {
  loadImportTasks()
  getTeams()
    .then((response) => {
      manageableTeams.value = response.results.filter((team) => team.can_manage)
      if (manageableTeams.value.length === 1) selectedTeamId.value = manageableTeams.value[0].id
    })
    .catch(() => {
      manageableTeams.value = []
    })
})
</script>

<style lang="scss" scoped>
.import-workspace {
  padding: 18px;
}

.mb-16 { margin-bottom: 16px; }

.import-steps {
  padding: 2px 8px 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.mobile-step-indicator {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light);

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  strong {
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
  }
}

.step-content {
  min-height: 220px;
  padding-top: 20px;

  .module-group {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .step-hint {
    font-size: 14px;
    color: var(--color-text-regular);
    margin-bottom: 16px;
  }

  .step-actions {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
}

.template-guide {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 14px;
  margin-bottom: 14px;
  background: var(--color-primary-soft);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);

  > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 3px;
  }

  strong {
    color: var(--color-text);
    font-size: 13px;
  }

  span {
    color: var(--color-text-muted);
    font-size: 12px;
    line-height: 1.5;
  }
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.mapping-table { min-width: 440px; }
.preview-table { min-width: 620px; }

pre {
  margin: 0;
  color: var(--color-text-regular);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.history-panel {
  padding: 0;
  margin-top: var(--space-4);
  overflow: hidden;
}

.section-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 52px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border-light);

  h2 {
    margin: 0;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
  }

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.mobile-history {
  min-height: 160px;
  padding: 0 12px;
}

.history-item {
  padding: 13px 0 8px;
  border-bottom: 1px solid var(--color-border-light);

  &:last-child { border-bottom: 0; }
}

.history-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;

  h3 {
    min-width: 0;
    margin: 0;
    overflow: hidden;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 1.45;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.history-meta,
.history-stats {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.history-stats {
  padding: 7px 9px;
  background: var(--color-surface-subtle);
  border-radius: var(--radius-xs);

  strong {
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }

  .success-number { color: var(--color-success); }
  .danger-number { color: var(--color-danger); }
}

.history-actions {
  display: flex;
  justify-content: flex-end;
}

@media screen and (max-width: 768px) {
  .import-workspace {
    padding: 14px 12px;
  }

  .step-content {
    min-height: 180px;
    padding-top: 16px;

    .module-group {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      width: 100%;

      :deep(.el-radio-button__inner) {
        width: 100%;
      }
    }

    .step-actions {
      position: sticky;
      bottom: 0;
      z-index: 3;
      padding: 10px 0 max(0px, env(safe-area-inset-bottom));
      margin-top: 14px;
      background: var(--color-surface);
    }
  }

  .template-guide {
    align-items: stretch;
    flex-direction: column;
  }

  :deep(.el-upload),
  :deep(.el-upload-dragger) {
    width: 100%;
  }
}
</style>
