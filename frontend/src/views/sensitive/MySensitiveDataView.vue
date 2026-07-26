<template>
  <div class="page-container sensitive-data-page">
    <PageHeader title="我的资料" subtitle="个人敏感信息与脱敏结果">
      <template #meta>
        <span class="page-meta">共 {{ dataList.length }} 项资料</span>
      </template>
    </PageHeader>

    <section class="data-surface">
      <div class="surface-heading">
        <h2>资料清单</h2>
        <el-tag type="info" effect="plain" size="small">脱敏展示</el-tag>
      </div>

      <el-table v-if="!isMobile" v-loading="loading" :data="dataList" stripe size="small">
        <el-table-column prop="title" label="名称" min-width="150">
          <template #default="{ row }">
            <span class="data-name">{{ row.title || row.label || '暂无名称' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="data_type" label="类型" width="140">
          <template #default="{ row }">
            <el-tag :type="SENSITIVE_DATA_TYPE_MAP[row.data_type]?.tagType as any" size="small" effect="plain">
              {{ row.data_type_display || SENSITIVE_DATA_TYPE_MAP[row.data_type]?.label || row.data_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="masked_value" label="脱敏值" min-width="200">
          <template #default="{ row }">
            <code class="masked-value">{{ row.masked_value || '-' }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="140">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无敏感资料" />
        </template>
      </el-table>

      <div v-else v-loading="loading" class="mobile-data-list">
        <article v-for="item in dataList" :key="item.id" class="mobile-data-item">
          <div class="mobile-item-heading">
            <div>
              <h3>{{ item.title || item.label || '暂无名称' }}</h3>
              <span>{{ formatDate(item.created_at) }}</span>
            </div>
            <el-tag :type="SENSITIVE_DATA_TYPE_MAP[item.data_type]?.tagType as any" size="small" effect="plain">
              {{ SENSITIVE_DATA_TYPE_MAP[item.data_type]?.label || item.data_type }}
            </el-tag>
          </div>
          <div class="masked-panel">
            <span>脱敏值</span>
            <code>{{ item.masked_value || '-' }}</code>
          </div>
        </article>
        <el-empty v-if="dataList.length === 0 && !loading" description="暂无敏感资料" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMySensitiveData } from '@/api/sensitive'
import { formatDate } from '@/utils/format'
import { SENSITIVE_DATA_TYPE_MAP } from '@/utils/constants'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import type { SensitiveData } from '@/types'

const { isMobile } = useDevice()
const loading = ref(false)
const dataList = ref<SensitiveData[]>([])

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getMySensitiveData()
    dataList.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.sensitive-data-page {
  padding-bottom: 32px;
}

.page-meta {
  display: inline-block;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.data-surface {
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.surface-heading {
  display: flex;
  min-height: 52px;
  padding: 12px 18px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.surface-heading h2 {
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
}

.data-name {
  color: var(--color-text);
  font-weight: 600;
}

.masked-value,
.masked-panel code {
  color: var(--color-text-regular);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
}

.mobile-data-list {
  display: flex;
  padding: 12px;
  flex-direction: column;
  gap: 10px;
}

.mobile-data-item {
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.mobile-item-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mobile-item-heading > div {
  min-width: 0;
}

.mobile-item-heading h3 {
  overflow: hidden;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-item-heading span {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.masked-panel {
  display: flex;
  margin-top: 12px;
  padding: 10px 12px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.masked-panel span {
  color: var(--color-text-muted);
  font-size: 11px;
}

@media screen and (max-width: 768px) {
  .sensitive-data-page {
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }

  .surface-heading {
    padding-right: 14px;
    padding-left: 14px;
  }
}
</style>
