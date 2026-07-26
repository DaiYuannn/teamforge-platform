<template>
  <div class="login-view">
    <img class="login-photo" src="/portal/photos/lst/团队合影2.jpg" alt="创新团队成员合影" />
    <div class="login-overlay" />

    <router-link to="/public" class="back-link">
      <el-icon><ArrowLeft /></el-icon>
      返回成果首页
    </router-link>

    <section class="login-context" aria-label="平台品牌">
      <div class="brand-mark"><el-icon><Trophy /></el-icon></div>
      <p class="brand-kicker">创新团队</p>
      <h1>团队管理平台</h1>
      <p>让项目进度、协作责任与团队成果保持清晰。</p>
    </section>

    <section class="login-panel">
      <header class="login-panel__header">
        <p>团队工作台</p>
        <h2>登录账户</h2>
        <span>使用团队分配的邮箱和密码继续</span>
      </header>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="email">
          <el-input
            v-model="loginForm.email"
            placeholder="邮箱地址"
            name="email"
            autocomplete="email"
            spellcheck="false"
            :prefix-icon="Message"
            clearable
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            name="password"
            autocomplete="current-password"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item class="options-item">
          <div class="form-options">
            <el-checkbox v-model="rememberMe">记住我</el-checkbox>
            <el-link type="primary" underline="never" @click="handleForgotPassword">忘记密码</el-link>
          </div>
        </el-form-item>
        <el-form-item class="submit-item">
          <el-button
            native-type="submit"
            type="primary"
            class="login-btn"
            :loading="loading"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, Lock, Message, Trophy } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import type { LoginParams } from '@/types'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loginFormRef = ref<FormInstance>()
const loading = ref(false)
const rememberMe = ref(false)

// 登录表单
const loginForm = reactive<LoginParams>({
  email: '',
  password: '',
})

// 表单验证规则
const loginRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
  ],
}

// 处理登录
async function handleLogin(): Promise<void> {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await userStore.login(loginForm)
      ElMessage.success('登录成功')
      const redirect = (route.query.redirect as string) || userStore.defaultLandingPath()
      router.push(redirect)
    } catch {
      ElMessage.error('登录失败，请检查邮箱和密码')
    } finally {
      loading.value = false
    }
  })
}

// 忘记密码提示
function handleForgotPassword(): void {
  ElMessage.info('请联系管理员重置密码')
}
</script>

<style lang="scss" scoped>
.login-view {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  align-items: center;
  gap: 72px;
  width: 100%;
  height: 100vh;
  height: 100dvh;
  padding: 72px max(48px, calc((100vw - 1200px) / 2));
  overflow: hidden;
  color: #fff;
  background: #17231f;
}

.login-photo,
.login-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.login-photo {
  object-fit: cover;
  object-position: center 42%;
}

.login-overlay {
  background: rgba(12, 26, 21, 0.62);
}

.back-link {
  position: absolute;
  top: 26px;
  left: max(24px, calc((100vw - 1200px) / 2));
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: rgba(255, 255, 255, 0.84);
  font-size: 13px;
}

.back-link:hover {
  color: #fff;
}

.login-context,
.login-panel {
  position: relative;
  z-index: 1;
}

.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  color: var(--color-primary);
  background: #fff;
  border-radius: var(--radius-sm);
  font-size: 22px;
}

.brand-kicker {
  margin-top: 22px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 13px;
  font-weight: 600;
}

.login-context h1 {
  margin-top: 8px;
  font-size: 42px;
  font-weight: 680;
  line-height: 1.2;
  letter-spacing: 0;
}

.login-context > p:last-child {
  max-width: 500px;
  margin-top: 16px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 16px;
  line-height: 1.7;
}

.login-panel {
  width: 100%;
  padding: 36px;
  color: var(--color-text);
  background: #fff;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
}

.login-panel__header {
  margin-bottom: 28px;
}

.login-panel__header > p {
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
}

.login-panel__header h2 {
  margin-top: 6px;
  font-size: 25px;
  font-weight: 650;
}

.login-panel__header span {
  display: block;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
}

.options-item {
  margin-top: -2px;
}

.submit-item {
  margin-bottom: 0;
}

@media screen and (max-width: 768px) {
  .login-view {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: 22px;
    padding: 72px 14px 18px;
  }

  .back-link {
    top: 20px;
    left: 18px;
  }

  .login-context {
    width: 100%;
    padding: 0 6px;
  }

  .brand-mark,
  .brand-kicker,
  .login-context > p:last-child {
    display: none;
  }

  .login-context h1 {
    font-size: 28px;
  }

  .login-panel {
    padding: 24px 20px;
  }

  .login-panel__header {
    margin-bottom: 22px;
  }
}

@media screen and (max-height: 680px) and (max-width: 768px) {
  .login-context {
    display: none;
  }

  .login-view {
    justify-content: center;
  }
}
</style>
