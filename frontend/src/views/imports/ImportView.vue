<template>
  <div class="page-container">
    <PageHeader title="导入中心" subtitle="批量导入数据" />

    <!-- 导入步骤 -->
    <div class="card">
      <el-steps :active="currentStep" align-center finish-status="success">
        <el-step title="选择模块" />
        <el-step title="上传文件" />
        <el-step title="字段映射" />
        <el-step title="预览数据" />
        <el-step title="确认导入" />
      </el-steps>

      <!-- 步骤1：选择模块 -->
      <div v-if="currentStep === 0" class="step-content">
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
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :on-change="handleFileChange"
          :limit="1"
          accept=".xlsx,.xls,.csv"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 Excel (.xlsx, .xls) 和 CSV 文件</div>
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
      <div v-if="currentStep === 2" class="step-content">
        <p class="step-hint">请确认源文件字段与系统字段的映射关系：</p>
        <el-table :data="mappingRows" border size="small">
          <el-table-column prop="sourceField" label="源文件字段" width="200" />
          <el-table-column label="系统字段" width="200">
            <template #default="{ row }">
              <el-select v-model="row.targetField" placeholder="选择字段" clearable>
                <el-option
                  v-for="field in systemFields"
                  :key="field"
                  :label="field"
                  :value="field"
                />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
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
        <el-table :data="previewRows" border size="small" max-height="400">
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
    </div>

    <!-- 导入历史 -->
    <div class="card mt-16">
      <h3 class="card-title">导入历史</h3>
      <el-table :data="importTasks" border size="small">
        <el-table-column prop="module" label="模块" width="100">
          <template #default="{ row }">{{ IMPORT_MODULE_MAP[row.module] || row.module }}</template>
        </el-table-column>
        <el-table-column prop="file_name" label="文件名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="IMPORT_TASK_STATUS_MAP[row.status]?.tagType as any" size="small">
              {{ IMPORT_TASK_STATUS_MAP[row.status]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_rows" label="总行数" width="80" align="center" />
        <el-table-column prop="success_rows" label="成功" width="80" align="center" />
        <el-table-column prop="failed_rows" label="失败" width="80" align="center" />
        <el-table-column prop="operator_name" label="操作人" width="100" />
        <el-table-column prop="created_at" label="导入时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.can_rollback && row.status === 'completed'"
              type="danger"
              link
              @click="handleRollback(row as ImportTask)"
            >
              回滚
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { previewImport, confirmImport, rollbackImport, getImportTasks } from '@/api/imports'
import { IMPORT_MODULE_MAP, IMPORT_TASK_STATUS_MAP } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'
import type { ImportModule, ImportPreviewResult, ImportTask, FieldMapping } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const currentStep = ref(0)
const selectedModule = ref<ImportModule>('users')
const selectedFile = ref<File | null>(null)
const previewing = ref(false)
const importing = ref(false)
const previewData = ref<ImportPreviewResult>({
  task_id: '',
  headers: [],
  field_mapping: {},
  preview_rows: [],
  total_rows: 0,
  valid_rows: 0,
  error_rows: 0,
  error_details: {},
})

// 系统可用字段（根据模块不同动态获取，这里用 headers + field_mapping 的 value 做候选）
const systemFields = ref<string[]>([])

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
  previewing.value = true
  try {
    const result = await previewImport(selectedFile.value, selectedModule.value)
    previewData.value = result
    // 初始化映射行（后端返回 field_mapping: { sourceField: targetField }）
    const mapping = result.field_mapping || {}
    mappingRows.value = Object.entries(mapping).map(([sourceField, targetField]) => ({
      sourceField,
      targetField: targetField as string,
    }))
    // 系统字段候选列表：从 field_mapping 的 value 值中取
    systemFields.value = Array.from(new Set(Object.values(mapping))) as string[]
    // 构建预览数据行
    const rawRows = result.preview_rows || []
    const errorDetails = result.error_details || {}
    previewRows.value = rawRows.map((row: any, idx: number) => {
      const rowIndex = idx + 1
      const errorInfo = errorDetails[String(rowIndex)] || errorDetails[rowIndex]
      return {
        row_index: rowIndex,
        data: typeof row === 'object' && !Array.isArray(row) ? row : { value: String(row) },
        valid: !errorInfo,
        error: errorInfo ? (typeof errorInfo === 'string' ? errorInfo : JSON.stringify(errorInfo)) : '',
      }
    })
    currentStep.value = 2
  } catch {
    // 已处理
  } finally {
    previewing.value = false
  }
}

// 确认字段映射
function handleConfirmMapping(): void {
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

    await confirmImport(previewData.value.task_id, fieldMapping)
    currentStep.value = 4
    ElMessage.success('导入成功')
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
    await rollbackImport(String(task.id))
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
  selectedModule.value = 'users'
  previewData.value = {
    task_id: '',
    headers: [],
    field_mapping: {},
    preview_rows: [],
    total_rows: 0,
    valid_rows: 0,
    error_rows: 0,
    error_details: {},
  }
  mappingRows.value = []
  previewRows.value = []
  systemFields.value = []
}

// 加载导入历史
async function loadImportTasks(): Promise<void> {
  try {
    const res = await getImportTasks()
    importTasks.value = res.results
  } catch {
    // 忽略
  }
}

onMounted(() => {
  loadImportTasks()
})
</script>

<style lang="scss" scoped>
.card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .card-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }
}

.mt-16 { margin-top: 16px; }
.mb-16 { margin-bottom: 16px; }

.step-content {
  margin-top: 24px;
  min-height: 200px;

  .module-group {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .step-hint {
    font-size: 14px;
    color: #606266;
    margin-bottom: 16px;
  }

  .step-actions {
    margin-top: 24px;
    display: flex;
    justify-content: center;
    gap: 12px;
  }
}

pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
