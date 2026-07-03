<template>
  <div class="public-layout">
    <!-- 公共展示面板头部 -->
    <div class="public-header">
      <div class="header-logo">
        <el-icon size="24" color="#409EFF"><DataBoard /></el-icon>
        <span class="logo-text">团队管理 - 公共展示面板</span>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="public-content">
      <router-view />
    </div>

    <!-- 底部信息 -->
    <div class="public-footer">
      <span>团队管理软件 - 公共展示面板</span>
    </div>
  </div>
</template>

<script setup lang="ts">
// 公共展示面板布局（架构预留）
// 未来用于大屏展示项目进度、比赛成绩等公共信息
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
  padding: 0 24px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);

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
  padding: 24px;
  overflow-y: auto;
}

.public-footer {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-top: 1px solid #ebeef5;
  font-size: 12px;
  color: #909399;
}
</style>
