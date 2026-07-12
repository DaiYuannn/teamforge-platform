<template>
  <div class="public-layout">
    <!-- 公共展示面板顶部导航栏 -->
    <div class="public-header">
      <div class="header-logo">
        <el-icon size="24" color="#667eea"><Trophy /></el-icon>
        <span class="logo-text">创新团队 · 成果展示</span>
      </div>
      <el-button type="primary" :icon="User" @click="goLogin">登录</el-button>
    </div>

    <!-- 主内容区 -->
    <div class="public-content">
      <router-view />
    </div>

    <!-- 底部版权信息 -->
    <div class="public-footer">
      <span>© {{ new Date().getFullYear() }} 创新团队管理软件 · 团队成果展示平台</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Trophy, User } from '@element-plus/icons-vue'

const router = useRouter()

/** 跳转登录页 */
function goLogin(): void {
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.public-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #f5f7fa;
}

.public-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  position: sticky;
  top: 0;
  z-index: 100;

  .header-logo {
    display: flex;
    align-items: center;
    gap: 8px;

    .logo-text {
      font-size: 18px;
      font-weight: 600;
      color: #303133;
    }
  }
}

.public-content {
  flex: 1;
  overflow-y: auto;
}

.public-footer {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-top: 1px solid #ebeef5;
  font-size: 13px;
  color: #909399;
}
</style>
