<template>
  <div class="page-container">
    <PageHeader title="团队灵活工作时间" subtitle="查看所有成员最新灵活工时" />

    <!-- PC端表格 -->
    <div v-if="!isMobile" class="card mt-16">
      <el-table v-loading="loading" :data="scheduleList" border stripe>
        <el-table-column prop="user_name" label="姓名" width="110" />
        <el-table-column prop="grade" label="年级" width="100">
          <template #default="{ row }">{{ row.grade || '-' }}</template>
        </el-table-column>
        <el-table-column prop="major" label="专业" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.major || '-' }}</template>
        </el-table-column>
        <el-table-column prop="available_hours" label="本期工时" width="100" align="center" />
        <el-table-column prop="can_offline" label="能否线下" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.can_offline ? 'success' : 'info' as any" size="small">
              {{ row.can_offline ? '能' : '不能' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="can_urgent" label="能否紧急" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.can_urgent ? 'success' : 'info' as any" size="small">
              {{ row.can_urgent ? '能' : '不能' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_saturated" label="是否饱和" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_saturated ? 'danger' : 'success' as any" size="small">
              {{ row.is_saturated ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="填写时间" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 移动端卡片列表 -->
    <div v-else v-loading="loading" class="mobile-list">
      <el-empty v-if="scheduleList.length === 0" description="暂无数据" />
      <el-card v-for="item in scheduleList" :key="item.id" class="mobile-card" shadow="hover">
        <div class="mobile-card-header">
          <span class="mobile-card-title">{{ item.user_name }}</span>
          <el-tag :type="item.is_saturated ? 'danger' : 'success' as any" size="small">
            {{ item.is_saturated ? '饱和' : '未饱和' }}
          </el-tag>
        </div>
        <div class="mobile-card-body">
          <div class="mobile-card-row">
            <span class="label">年级专业：</span>
            <span>{{ item.grade || '-' }} {{ item.major || '' }}</span>
          </div>
          <div class="mobile-card-row">
            <span class="label">本期工时：</span>
            <span>{{ item.available_hours }} 小时</span>
          </div>
          <div class="mobile-card-row">
            <span class="label">线下/紧急：</span>
            <span>{{ item.can_offline ? '能线下' : '不能线下' }} / {{ item.can_urgent ? '能紧急' : '不能紧急' }}</span>
          </div>
          <div class="mobile-card-row" v-if="item.remark">
            <span class="label">备注：</span><span>{{ item.remark }}</span>
          </div>
          <div class="mobile-card-row">
            <span class="label">填写时间：</span><span>{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAllLatestSchedules } from '@/api/members'
import { formatDate } from '@/utils/format'
import { useDevice } from '@/composables/useDevice'
import PageHeader from '@/components/PageHeader.vue'
import type { FlexibleWorkSchedule } from '@/types'

const { isMobile } = useDevice()

const loading = ref(false)
const scheduleList = ref<any[]>([])

// 加载数据
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getAllLatestSchedules()
    scheduleList.value = Array.isArray(res) ? res : (res.results || [])
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

/* 移动端样式 */
.mobile-list {
  .mobile-card {
    margin-bottom: 12px;

    .mobile-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;

      .mobile-card-title {
        font-size: 15px;
        font-weight: 600;
        color: #303133;
      }
    }

    .mobile-card-body {
      .mobile-card-row {
        font-size: 13px;
        color: #606266;
        margin-bottom: 4px;

        .label {
          color: #909399;
        }
      }
    }
  }
}
</style>
