<template>
  <div class="login-view">
    <div class="login-container">
      <div class="login-left">
        <div class="brand">
          <el-icon size="48" color="#fff" aria-hidden="true"><Monitor /></el-icon>
          <h1>团队管理软件</h1>
          <p>高校竞赛团队全流程管理平台</p>
        </div>
      </div>
      <div class="login-right">
        <div class="login-form-wrapper">
          <h2 class="login-title">欢迎登录</h2>
          <p class="login-subtitle">请输入您的账号信息</p>

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
                placeholder="邮箱地址…"
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
                placeholder="密码…"
                name="password"
                autocomplete="current-password"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-form-item>
              <div class="form-options">
                <el-checkbox v-model="rememberMe">记住我</el-checkbox>
                <el-link type="primary" :underline="false" @click="handleForgotPassword">忘记密码？</el-link>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                class="login-btn"
                :loading="loading"
                @click="handleLogin"
              >
                登录
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Message, Lock } from '@element-plus/icons-vue'
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
      const redirect = (route.query.redirect as string) || '/dashboard'
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
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-brand);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      radial-gradient(circle at 20% 80%, rgba(54, 207, 201, 0.15) 0%, transparent 50%),
      radial-gradient(circle at 80% 20%, rgba(64, 158, 255, 0.2) 0%, transparent 50%);
    pointer-events: none;
  }
}

.login-container {
  width: 800px;
  max-width: 90%;
  height: 480px;
  display: flex;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 1;
  animation: login-entrance 0.5s ease-out;

  @keyframes login-entrance {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
}

.login-left {
  flex: 1;
  background: linear-gradient(160deg, #2b3a4d 0%, #1e40af 50%, #409eff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    width: 200%;
    height: 200%;
    top: -50%;
    left: -50%;
    background: radial-gradient(circle, rgba(54, 207, 201, 0.08) 0%, transparent 60%);
    animation: brand-glow 8s ease-in-out infinite;
  }

  @keyframes brand-glow {
    0%, 100% { transform: rotate(0deg); }
    50% { transform: rotate(180deg); }
  }

  .brand {
    text-align: center;
    color: #fff;
    position: relative;
    z-index: 1;

    h1 {
      font-size: 28px;
      font-weight: 700;
      margin: 16px 0 8px;
      letter-spacing: 1px;
    }

    p {
      font-size: 14px;
      opacity: 0.85;
      letter-spacing: 0.5px;
    }
  }
}

.login-right {
  flex: 1;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;

  .login-form-wrapper {
    width: 100%;
    max-width: 320px;

    .login-title {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 8px;
    }

    .login-subtitle {
      font-size: 14px;
      color: var(--text-secondary);
      margin-bottom: 32px;
    }

    .form-options {
      display: flex;
      justify-content: space-between;
      width: 100%;
    }

    .login-btn {
      width: 100%;
      height: 44px;
      font-size: 16px;
      font-weight: 600;
      border-radius: var(--radius-sm);
    }
  }
}

// 移动端响应式
@media screen and (max-width: 768px) {
  .login-container {
    width: 90%;
    height: auto;
    flex-direction: column;
  }

  .login-left {
    padding: 30px 20px;

    .brand h1 {
      font-size: 22px;
    }
  }

  .login-right {
    padding: 24px 20px;
  }
}

// 无障碍：降低动画
@media (prefers-reduced-motion: reduce) {
  .login-container {
    animation: none;
  }
  .login-left::before {
    animation: none;
  }
}
</style>
