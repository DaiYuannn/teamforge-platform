<template>
  <main class="reset-page">
    <section class="reset-panel">
      <header>
        <el-icon><Lock /></el-icon>
        <h1>{{ t('重置密码') }}</h1>
        <p>{{ t('设置新的账户密码') }}</p>
      </header>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="submit">
        <el-form-item prop="new_password">
          <el-input
            v-model="form.new_password"
            type="password"
            autocomplete="new-password"
            :placeholder="t('新密码')"
            show-password
          />
        </el-form-item>
        <el-form-item prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            autocomplete="new-password"
            :placeholder="t('确认新密码')"
            show-password
          />
        </el-form-item>
        <el-button class="submit" type="primary" native-type="submit" :loading="loading">
          {{ t('确认重置') }}
        </el-button>
      </el-form>
      <router-link to="/login">{{ t('返回登录') }}</router-link>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { confirmPasswordReset } from '@/api/auth'
import { useI18n } from '@/i18n'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const { t } = useI18n()
const form = reactive({ new_password: '', confirm_password: '' })
const rules: FormRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  confirm_password: [{
    validator: (_rule, value, callback) => {
      if (!value) callback(new Error('请再次输入新密码'))
      else if (value !== form.new_password) callback(new Error('两次密码不一致'))
      else callback()
    },
    trigger: 'blur',
  }],
}

async function submit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  const uid = String(route.query.uid || '')
  const token = String(route.query.token || '')
  if (!uid || !token) {
    ElMessage.error('重置链接无效')
    return
  }
  loading.value = true
  try {
    await confirmPasswordReset({ uid, token, ...form })
    ElMessage.success('密码已重置，请重新登录')
    await router.replace('/login')
  } catch {
    ElMessage.error('链接已失效或密码不符合要求')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.reset-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 20px;
  background: var(--color-bg);
}

.reset-panel {
  width: min(400px, 100%);
  padding: 32px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
}

header {
  margin-bottom: 24px;
  text-align: center;
}

header .el-icon {
  color: var(--color-primary);
  font-size: 28px;
}

h1 {
  margin: 8px 0 4px;
  font-size: 24px;
}

p, a {
  color: var(--color-text-muted);
  font-size: 13px;
}

.submit {
  width: 100%;
  margin-bottom: 18px;
}
</style>
