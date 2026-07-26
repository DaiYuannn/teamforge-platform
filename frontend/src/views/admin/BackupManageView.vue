<template>
  <div class="page-container backup-page">
    <PageHeader title="演示数据备份" subtitle="生成、下载并校验恢复当前演示环境的数据包">
      <template #actions>
        <el-button type="primary" :icon="Box" :loading="creating" @click="createBackup">
          生成备份包
        </el-button>
      </template>
    </PageHeader>

    <el-alert type="warning" :closable="false" show-icon class="mode-alert">
      <template #title>这是演示数据恢复工具，不替代生产数据库备份</template>
      恢复前会自动生成回滚包；恢复会重建全部 @demo.com 账号、业务数据和实际附件，并要求重新登录。
    </el-alert>

    <section class="surface-panel backup-panel">
      <div class="panel-heading">
        <div>
          <h2>可用数据包</h2>
          <p>{{ description || '每个 ZIP 均包含业务快照、清单、SHA-256 校验和与演示附件。' }}</p>
        </div>
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
      </div>

      <el-table v-loading="loading" :data="backups">
        <template #empty>
          <EmptyState text="尚未生成备份包" description="点击右上角生成第一个演示数据包。" icon="Box" />
        </template>
        <el-table-column prop="backup_id" label="备份编号" min-width="190">
          <template #default="{ row }">
            <div class="backup-name">
              <strong>{{ row.backup_id }}</strong>
              <el-tag :type="row.status === 'ready' ? 'success' : 'danger'" size="small">
                {{ row.status === 'ready' ? '校验就绪' : '包已损坏' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" min-width="165">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建账户" min-width="180" show-overflow-tooltip />
        <el-table-column prop="entry_count" label="包内文件" width="100" align="right" />
        <el-table-column prop="size" label="大小" width="110" align="right">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="sha256" label="校验摘要" min-width="150" show-overflow-tooltip>
          <template #default="{ row }"><code>{{ row.sha256?.slice(0, 16) }}…</code></template>
        </el-table-column>
        <el-table-column label="操作" width="170" align="right" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="row.status !== 'ready'" @click="downloadBackup(row as any)">
              下载
            </el-button>
            <el-button link type="danger" :disabled="row.status !== 'ready'" @click="confirmRestore(row as any)">
              恢复
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Box, Refresh } from '@element-plus/icons-vue'
import {
  createDemoBackup,
  downloadDemoBackup,
  getDemoBackups,
  restoreDemoBackup,
  type DemoBackup,
} from '@/api/backup'
import { downloadBlob, formatDateTime } from '@/utils/format'
import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const backups = ref<DemoBackup[]>([])
const loading = ref(false)
const creating = ref(false)
const description = ref('')

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const response = await getDemoBackups()
    backups.value = response.backups
    description.value = response.message
  } finally {
    loading.value = false
  }
}

async function createBackup(): Promise<void> {
  creating.value = true
  try {
    await createDemoBackup()
    ElMessage.success('演示数据备份包已生成')
    await loadData()
  } finally {
    creating.value = false
  }
}

async function downloadBackup(backup: DemoBackup): Promise<void> {
  const blob = await downloadDemoBackup(backup.backup_id)
  downloadBlob(blob, `${backup.backup_id}.zip`)
}

async function confirmRestore(backup: DemoBackup): Promise<void> {
  await ElMessageBox.confirm(
    `将从 ${backup.backup_id} 恢复演示环境。系统会先自动创建回滚包，随后重建演示账号、业务数据和附件；完成后需要重新登录。`,
    '确认恢复演示数据',
    {
      type: 'warning',
      confirmButtonText: '恢复并重新登录',
      cancelButtonText: '取消',
      distinguishCancelAndClose: true,
    },
  )
  const result = await restoreDemoBackup(backup.backup_id)
  ElMessage.success(`恢复完成，回滚包：${result.rollback_backup_id}`)
  await userStore.logout()
  await router.replace('/login')
}

function formatSize(size: number): string {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.mode-alert {
  margin-bottom: var(--space-4);
}

.backup-panel {
  padding: 0;
  overflow: hidden;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border-light);

  h2 { margin: 0; color: var(--color-text); font-size: 15px; }
  p { margin: 4px 0 0; color: var(--color-text-muted); font-size: 12px; }
}

.backup-name {
  display: flex;
  align-items: center;
  gap: 8px;
  strong { color: var(--color-text); font-size: 13px; font-variant-numeric: tabular-nums; }
}

code {
  color: var(--color-text-regular);
  font-size: 11px;
}

@media screen and (max-width: 768px) {
  .panel-heading {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
