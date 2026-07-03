<template>
  <div class="page-container">
    <PageHeader title="我的资料" subtitle="查看我的敏感资料（脱敏显示）" />

    <div class="card mt-16">
      <el-table v-loading="loading" :data="dataList" border stripe>
        <el-table-column prop="title" label="名称" min-width="150">
          <template #default="{ row }">{{ row.title || row.label || '暂无名称' }}</template>
        </el-table-column>
        <el-table-column prop="data_type" label="类型" width="140">
          <template #default="{ row }">
            <el-tag :type="SENSITIVE_DATA_TYPE_MAP[row.data_type]?.tagType as any" size="small">
              {{ row.data_type_display || SENSITIVE_DATA_TYPE_MAP[row.data_type]?.label || row.data_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="masked_value" label="脱敏值" min-width="200" />
        <el-table-column prop="created_at" label="创建时间" width="140">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMySensitiveData } from '@/api/sensitive'
import { formatDate } from '@/utils/format'
import { SENSITIVE_DATA_TYPE_MAP } from '@/utils/constants'
import PageHeader from '@/components/PageHeader.vue'
import type { SensitiveData } from '@/types'

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
.mt-16 {
  margin-top: 16px;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
</style>
