<template>
  <div class="public-portal" v-loading="loading">
    <!-- ==================== 1. Hero 区域 ==================== -->
    <section class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <h1 class="hero-title">创新团队成果展示</h1>
        <p class="hero-subtitle">创新 · 协作 · 卓越 · 共赢</p>
        <div class="hero-stats">
          <div class="hero-stat-item">
            <div class="hero-stat-value">{{ portalData?.stats.total_projects ?? 0 }}</div>
            <div class="hero-stat-label">项目总数</div>
          </div>
          <div class="hero-stat-divider"></div>
          <div class="hero-stat-item">
            <div class="hero-stat-value">{{ portalData?.stats.awarded_projects ?? 0 }}</div>
            <div class="hero-stat-label">获奖项目</div>
          </div>
          <div class="hero-stat-divider"></div>
          <div class="hero-stat-item">
            <div class="hero-stat-value">{{ portalData?.stats.total_competitions ?? 0 }}</div>
            <div class="hero-stat-label">参赛比赛</div>
          </div>
          <div class="hero-stat-divider"></div>
          <div class="hero-stat-item">
            <div class="hero-stat-value">{{ portalData?.stats.total_ip ?? 0 }}</div>
            <div class="hero-stat-label">知识产权</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 2. 获奖项目展示区 ==================== -->
    <section class="content-section">
      <div class="section-header">
        <h2 class="section-title">
          <span class="title-bar"></span>
          获奖项目
        </h2>
        <p class="section-desc">团队在各大赛事中取得的优异成绩</p>
      </div>
      <el-row :gutter="20">
        <el-col
          v-for="project in portalData?.awarded_projects"
          :key="project.project_id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <div class="project-card">
            <div class="project-card-header">
              <div class="project-icon">
                <el-icon size="22"><Trophy /></el-icon>
              </div>
              <div class="project-code">{{ project.project_code }}</div>
            </div>
            <h3 class="project-name" :title="project.project_name">{{ project.project_name }}</h3>
            <div class="project-leader">
              <el-icon><User /></el-icon>
              <span>负责人：{{ project.leader_name }}</span>
            </div>
            <p class="project-intro">{{ project.intro || '暂无简介' }}</p>
            <div class="project-awards">
              <el-tag
                v-for="(award, idx) in project.awards"
                :key="idx"
                :type="getAwardTagType(award.level)"
                effect="dark"
                size="small"
                class="award-tag"
              >
                {{ award.competition_name }} · {{ award.award_level || award.level_display }}
              </el-tag>
            </div>
            <div v-if="project.start_date" class="project-date">
              启动时间：{{ formatDate(project.start_date) }}
            </div>
          </div>
        </el-col>
      </el-row>
      <el-empty
        v-if="!loading && !portalData?.awarded_projects?.length"
        description="暂无获奖项目"
        :image-size="80"
      />
    </section>

    <!-- ==================== 3. 知识产权成果区 ==================== -->
    <section class="content-section">
      <div class="section-header">
        <h2 class="section-title">
          <span class="title-bar"></span>
          知识产权成果
        </h2>
        <p class="section-desc">团队在知识产权领域的创新成果</p>
      </div>
      <div class="ip-table-wrapper">
        <el-table
          v-if="portalData?.ip_results?.length"
          :data="portalData.ip_results"
          border
          stripe
          size="default"
        >
          <el-table-column type="index" label="序号" width="70" align="center" />
          <el-table-column prop="title" label="成果名称" min-width="200" show-overflow-tooltip />
          <el-table-column label="类型" width="140" align="center">
            <template #default="{ row }">
              <el-tag :type="getIPTypeTagType(row.ip_type)" size="small" effect="light">
                {{ IP_TYPE_MAP[row.ip_type]?.label || row.ip_type_display || row.ip_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="application_code" label="申请编号" width="160" show-overflow-tooltip />
          <el-table-column label="授权日期" width="130" align="center">
            <template #default="{ row }">
              {{ row.authorized_date ? formatDate(row.authorized_date) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="intro" label="简介" min-width="200" show-overflow-tooltip />
        </el-table>
        <el-empty
          v-else-if="!loading"
          description="暂无知识产权成果"
          :image-size="80"
        />
      </div>
    </section>

    <!-- ==================== 4. 核心成员区 ==================== -->
    <section class="content-section">
      <div class="section-header">
        <h2 class="section-title">
          <span class="title-bar"></span>
          核心成员
        </h2>
        <p class="section-desc">团队中的核心骨干力量</p>
      </div>
      <el-row :gutter="20">
        <el-col
          v-for="member in portalData?.core_members"
          :key="member.user_id"
          :xs="12"
          :sm="8"
          :md="6"
          :lg="4"
        >
          <div class="member-card">
            <el-avatar :size="64" class="member-avatar">
              {{ member.name?.charAt(0) || 'U' }}
            </el-avatar>
            <div class="member-name">{{ member.name }}</div>
            <el-tag
              :type="getRoleTagType(member.global_role)"
              size="small"
              effect="light"
              class="member-role-tag"
            >
              {{ member.global_role_display || ROLE_MAP[member.global_role]?.label || '成员' }}
            </el-tag>
            <div class="member-info">
              <span v-if="member.grade">{{ member.grade }}</span>
              <span v-if="member.grade && member.major"> · </span>
              <span v-if="member.major">{{ member.major }}</span>
            </div>
            <div class="member-project-count">
              参与 {{ member.project_count }} 个项目
            </div>
          </div>
        </el-col>
      </el-row>
      <el-empty
        v-if="!loading && !portalData?.core_members?.length"
        description="暂无核心成员"
        :image-size="80"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Trophy, User } from '@element-plus/icons-vue'
import { getPublicPortal } from '@/api/dashboard'
import { formatDate } from '@/utils/format'
import { IP_TYPE_MAP, ROLE_MAP } from '@/utils/constants'
import type { PublicPortalData } from '@/api/dashboard'

const loading = ref(false)
const portalData = ref<PublicPortalData | null>(null)

/** 比赛级别 -> el-tag type 映射 */
function getAwardTagType(level: string): 'danger' | 'warning' | 'info' | 'success' | 'primary' | undefined {
  const map: Record<string, 'danger' | 'warning' | 'info' | 'success' | 'primary'> = {
    national: 'danger',
    provincial: 'warning',
    municipal: 'primary',
    school: 'info',
    enterprise: 'success',
  }
  return map[level] || 'info'
}

/** 知识产权类型 -> el-tag type */
function getIPTypeTagType(ipType: string): 'primary' | 'danger' | 'warning' | 'success' | 'info' {
  const color = IP_TYPE_MAP[ipType]?.color
  if (color === 'primary' || color === 'danger' || color === 'warning' || color === 'success' || color === 'info') {
    return color
  }
  return 'info'
}

/** 角色 -> el-tag type */
function getRoleTagType(role: string): 'danger' | 'warning' | 'success' | 'info' | 'primary' | undefined {
  const tagType = ROLE_MAP[role]?.tagType
  if (tagType === 'danger' || tagType === 'warning' || tagType === 'success' || tagType === 'info' || tagType === 'primary') {
    return tagType
  }
  return undefined
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    portalData.value = await getPublicPortal()
  } catch {
    // 公共接口错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.public-portal {
  min-height: 100vh;
}

/* ==================== Hero 区域 ==================== */
.hero-section {
  position: relative;
  padding: 60px 24px 48px;
  overflow: hidden;

  .hero-bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    z-index: 0;
  }

  .hero-content {
    position: relative;
    z-index: 1;
    max-width: 1200px;
    margin: 0 auto;
    text-align: center;
  }

  .hero-title {
    font-size: 42px;
    font-weight: 700;
    color: #fff;
    margin: 0 0 12px;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    letter-spacing: 2px;
  }

  .hero-subtitle {
    font-size: 18px;
    color: rgba(255, 255, 255, 0.85);
    margin: 0 0 40px;
    letter-spacing: 4px;
  }

  .hero-stats {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    flex-wrap: wrap;

    .hero-stat-item {
      padding: 0 32px;
      min-width: 120px;

      .hero-stat-value {
        font-size: 48px;
        font-weight: 700;
        color: #fff;
        line-height: 1.2;
        font-variant-numeric: tabular-nums;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      }

      .hero-stat-label {
        font-size: 15px;
        color: rgba(255, 255, 255, 0.8);
        margin-top: 8px;
      }
    }

    .hero-stat-divider {
      width: 1px;
      height: 60px;
      background: rgba(255, 255, 255, 0.25);
    }
  }
}

/* ==================== 内容区块 ==================== */
.content-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 24px;

  .section-header {
    margin-bottom: 24px;

    .section-title {
      font-size: 24px;
      font-weight: 700;
      color: #303133;
      margin: 0 0 8px;
      display: flex;
      align-items: center;

      .title-bar {
        width: 5px;
        height: 24px;
        background: linear-gradient(180deg, #667eea, #764ba2);
        border-radius: 3px;
        margin-right: 12px;
      }
    }

    .section-desc {
      font-size: 14px;
      color: #909399;
      margin: 0;
      padding-left: 17px;
    }
  }
}

/* ==================== 获奖项目卡片 ==================== */
.project-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  margin-bottom: 20px;
  height: calc(100% - 20px);
  display: flex;
  flex-direction: column;
  border-top: 3px solid transparent;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
    border-top-color: #667eea;
  }

  .project-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    .project-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, #f6d365, #fda085);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
    }

    .project-code {
      font-size: 12px;
      color: #c0c4cc;
      font-family: 'Courier New', monospace;
    }
  }

  .project-name {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .project-leader {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: #606266;
    margin-bottom: 10px;
  }

  .project-intro {
    font-size: 13px;
    color: #909399;
    margin: 0 0 12px;
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    flex: 1;
  }

  .project-awards {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;

    .award-tag {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .project-date {
    font-size: 12px;
    color: #c0c4cc;
    border-top: 1px dashed #ebeef5;
    padding-top: 8px;
  }
}

/* ==================== 知识产权表格 ==================== */
.ip-table-wrapper {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

/* ==================== 核心成员卡片 ==================== */
.member-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px 16px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  margin-bottom: 20px;
  height: calc(100% - 20px);

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
  }

  .member-avatar {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: #fff;
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 12px;
  }

  .member-name {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 8px;
  }

  .member-role-tag {
    margin-bottom: 10px;
  }

  .member-info {
    font-size: 13px;
    color: #909399;
    margin-bottom: 6px;
  }

  .member-project-count {
    font-size: 12px;
    color: #c0c4cc;
  }
}

/* ==================== 响应式适配 ==================== */
@media screen and (max-width: 768px) {
  .hero-section {
    padding: 40px 16px 32px;

    .hero-title {
      font-size: 28px;
    }

    .hero-subtitle {
      font-size: 14px;
      margin-bottom: 28px;
    }

    .hero-stats {
      .hero-stat-item {
        padding: 0 16px;
        min-width: 80px;

        .hero-stat-value {
          font-size: 32px;
        }

        .hero-stat-label {
          font-size: 12px;
        }
      }

      .hero-stat-divider {
        height: 40px;
      }
    }
  }

  .content-section {
    padding: 28px 16px;

    .section-header .section-title {
      font-size: 20px;
    }
  }
}
</style>
