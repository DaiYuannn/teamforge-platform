<template>
  <div class="public-layout">
    <header class="public-header">
      <div class="public-header__inner">
        <router-link to="/public" class="brand" aria-label="返回团队成果首页">
          <span class="brand-mark"><el-icon><Trophy /></el-icon></span>
          <span class="brand-copy">
            <strong>创新团队</strong>
            <small>成果与协作</small>
          </span>
        </router-link>

        <nav class="public-nav" aria-label="门户导航">
          <a href="#projects">项目成果</a>
          <a href="#intellectual-property">知识产权</a>
          <a href="#team">团队成员</a>
        </nav>

        <el-button type="primary" :icon="User" @click="goLogin">进入工作台</el-button>
      </div>
    </header>

    <main class="public-content">
      <router-view />
    </main>

    <footer class="public-footer">
      <div class="public-footer__inner">
        <span>创新团队 · 让每一项投入都有记录</span>
        <span>© {{ new Date().getFullYear() }} 团队管理平台</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Trophy, User } from '@element-plus/icons-vue'

const router = useRouter()

function goLogin(): void {
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.public-layout {
  width: 100%;
  height: 100vh;
  height: 100dvh;
  min-height: 100vh;
  min-height: 100dvh;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--color-surface);
}

.public-header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 64px;
  background: color-mix(in srgb, var(--color-surface) 96%, transparent);
  border-bottom: 1px solid var(--color-border-light);
}

.public-header__inner,
.public-footer__inner {
  width: min(1200px, calc(100% - 48px));
  height: 100%;
  margin: 0 auto;
}

.public-header__inner {
  display: flex;
  align-items: center;
  gap: 28px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: var(--color-text);
}

.brand:hover {
  color: var(--color-text);
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  color: #fff;
  background: var(--color-primary-fill);
  border-radius: var(--radius-sm);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.brand-copy strong {
  font-size: 15px;
  font-weight: 650;
}

.brand-copy small {
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.public-nav {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-left: auto;
}

.public-nav a {
  color: var(--color-text-regular);
  font-size: 13px;
  font-weight: 500;
}

.public-nav a:hover {
  color: var(--color-primary);
}

.public-content {
  min-height: calc(100dvh - 64px);
}

.public-footer {
  min-height: 72px;
  color: rgba(255, 255, 255, 0.72);
  background: #17231f;
}

.public-footer__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 0;
  font-size: 12px;
}

@media screen and (max-width: 768px) {
  .public-header {
    height: 58px;
  }

  .public-header__inner,
  .public-footer__inner {
    width: calc(100% - 28px);
  }

  .brand-copy small,
  .public-nav {
    display: none;
  }

  .public-header__inner {
    gap: 12px;
  }

  .public-header__inner > .el-button {
    margin-left: auto;
  }

  .public-footer__inner {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>
