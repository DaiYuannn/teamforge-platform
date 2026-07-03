<template>
  <div class="page-container">
    <!-- 返回按钮 -->
    <div class="detail-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      <h2 class="detail-title">成员详情</h2>
    </div>

    <div v-loading="loading">
      <!-- 基本信息 -->
      <div class="card">
        <div class="member-header">
          <el-avatar :size="64" :src="member?.avatar">
            {{ member?.name?.charAt(0) || 'U' }}
          </el-avatar>
          <div class="member-info">
            <h3>{{ member?.name }}</h3>
            <p>{{ member?.email }}</p>
          </div>
        </div>
        <el-descriptions :column="2" border class="mt-16">
          <el-descriptions-item label="角色">{{ member?.global_role_display || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="年级">{{ member?.grade || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="专业">{{ member?.major || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="联系方式">{{ member?.phone || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ member?.email || '暂无数据' }}</el-descriptions-item>
          <el-descriptions-item label="加入时间">{{ member?.date_joined ? formatDate(member.date_joined) : '暂无数据' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 参与项目 -->
      <div class="card mt-16">
        <h3 class="section-title">参与项目</h3>
        <el-table :data="member?.projects || []" border size="small">
          <el-table-column prop="project_name" label="项目名称" min-width="200" />
          <el-table-column prop="role_in_project_display" label="项目角色" width="150" />
        </el-table>
        <el-empty v-if="!member?.projects?.length" description="暂无参与项目" :image-size="60" />
      </div>

      <!-- 统计信息 -->
      <div class="card mt-16">
        <h3 class="section-title">统计信息</h3>
        <el-row :gutter="16">
          <el-col :span="8">
            <div class="task-stat-card">
              <div class="stat-value">{{ member?.project_count ?? '暂无数据' }}</div>
              <div class="stat-label">参与项目数</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="task-stat-card">
              <div class="stat-value">{{ member?.is_student ? '是' : '否' }}</div>
              <div class="stat-label">是否学生</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="task-stat-card">
              <div class="stat-value">{{ member?.date_joined ? formatDate(member.date_joined) : '暂无数据' }}</div>
              <div class="stat-label">加入时间</div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getMember } from '@/api/members'
import { formatDate } from '@/utils/format'
import type { Member } from '@/types'

const route = useRoute()
const memberId = Number(route.params.id)

const loading = ref(false)
const member = ref<Member | null>(null)

async function loadData(): Promise<void> {
  loading.value = true
  try {
    member.value = await getMember(memberId)
  } catch {
    // 已处理
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;

  .detail-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.mt-16 { margin-top: 16px; }

.member-header {
  display: flex;
  align-items: center;
  gap: 16px;

  .member-info {
    h3 {
      font-size: 20px;
      color: #303133;
      margin: 0 0 4px 0;
    }
    p {
      font-size: 14px;
      color: #909399;
      margin: 0;
    }
  }
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.task-stat-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 24px;
  text-align: center;

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #409eff;
  }
  .stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 4px;
  }
}
</style>
